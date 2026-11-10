// SPDX-License-Identifier: MIT
// World: level loading, thin walls and doors, collision, line of sight,
// dynamic lights.
#include "game_api.h"
#include "assets.h"
#include "world.h"
#include "objects.h"
#include <string.h>

EWRAM_BSS Thing g_things[MAX_THINGS];       // the level's things: the game fills and draws them
int g_numThings;
EWRAM_BSS Door g_doors[MAX_DOORS];
int  g_numDoors;
EWRAM_BSS u8 g_lightStatic[GRID_W * GRID_W] ALIGN4;
Camera g_cam;
EWRAM_BSS RSprite g_sprites[MAX_SPRITES];
int g_numSprites;
const LevelDef *g_level;
const u8 *g_cellFlags;

EWRAM_BSS static u8 s_visbuf[MAX_LIGHT_BYTES] ALIGN4;
EWRAM_BSS static u8 s_flatTmp[2][4096] ALIGN4;

EWRAM_BSS DynLight g_dlights[MAX_DLIGHTS];
int g_numDLights;

static void lz_decomp(const u8 *src, void *dst) { bios_lz77_wram(src, dst); }

void world_load_level(const LevelDef *L) {
    g_level = L;
    memcpy(g_edges, L->edges, sizeof g_edges);
    g_edgeTypes = (const EdgeType *)L->edgeTypes;
    g_cellFlags = L->cells;
    // floor/ceiling materials: interleave floor | ceil << 8 into the bank
    for (int m = 0; m < 4; m++) {
        lz_decomp(tex_lz[L->flatTex[2 * m]], s_flatTmp[0]);
        lz_decomp(tex_lz[L->flatTex[2 * m + 1]], s_flatTmp[1]);
        u16 *dst = g_flatBank + m * 4096;
        for (int i = 0; i < 4096; i++) dst[i] = s_flatTmp[0][i] | (s_flatTmp[1][i] << 8);
    }
    g_flatCtx.tex = g_flatBank;
    g_flatCtx.cmap = g_colormap;
    // doors
    g_numDoors = L->numDoors < MAX_DOORS ? L->numDoors : MAX_DOORS;
    for (int i = 0; i < g_numDoors; i++) {
        const DoorDef *d = &L->doors[i];
        Door *o = &g_doors[i];
        memset(o, 0, sizeof *o);
        o->x = d->x; o->y = d->y; o->axis = d->axis; o->kind = d->kind;
        o->lock = d->lock; o->flags = d->flags; o->hinge = d->hinge;
        o->edgeType = d->edgeType; o->leafTex = d->leafTex;
        if (d->flags & DOORF_STARTOPEN) o->open = 0xFFFF;
    }
    // props
    g_numProps = L->numProps < MAX_PROPS ? L->numProps : MAX_PROPS;
    for (int i = 0; i < g_numProps; i++) {
        const PropDef *d = &L->props[i];
        PropInst *p = &g_props[i];
        p->x = d->x << 8; p->y = d->y << 8; p->z = d->z;
        p->angle = d->angle << 8; p->model = d->model; p->flags = d->flags;
        p->tex = d->tex; p->light = d->light;
    }
    g_numDynProps = 0;
    // light
    lz_decomp(L->lightLZ, g_lightStatic);
    lz_decomp(L->visLZ, s_visbuf);
    g_numDLights = 0;
    const u8 *vp = s_visbuf;
    for (int i = 0; i < L->numLights && i < MAX_DLIGHTS; i++) {
        DynLight *dl = &g_dlights[g_numDLights++];
        dl->def = &L->lights[i];
        dl->x0 = vp[0]; dl->y0 = vp[1]; dl->w = vp[2]; dl->h = vp[3];
        dl->patch = vp + 4;
        vp += 4 + dl->w * dl->h;
        dl->level = 256;
        dl->on = 1;
    }
    memcpy(g_lightgrid, g_lightStatic, GRID_W * GRID_W);
    g_lightsDirty = 1;
    // camera
    g_cam.x = L->startX << 8;
    g_cam.y = L->startY << 8;
    g_cam.angle = L->startAngle;
    camera_update(&g_cam);
}

// ------------------------------------------------------------- lights
static u32 s_rng = 0x1234567;
u32 rng_next(void) { s_rng = s_rng * 1664525u + 1013904223u; return s_rng >> 8; }
void rng_seed(u32 v) { s_rng = v; }

extern void light_patch(u8 *dst, const u8 *src, int w, int h, int lvl);
// Base layer = baked static light + steady script-controlled lights. It is
// rebuilt only when a script changes a light group; each frame the base is
// copied to the grid and only the flickering/buzzing/candle lights are added.
EWRAM_BSS static u8 s_lightBase[GRID_W * GRID_W] ALIGN4;
u8 g_lightsDirty = 1;
u8 g_doorEpoch;
// Lights further than this (half tiles) from the camera stop flickering and
// are baked into the base layer at their average brightness.
#define LIGHT_NEAR 14
static const u16 s_avgLevel[5] = { 256, 236, 228, 150, 228 };   // by LIGHT_* mode
static u32 s_nearMask;
static u32 s_lightTick;         // the logic tick of the last flicker step
// A rectangle of the grid that someone else has lit on top of this module's
// lights (the enemy's lantern): put back to the base the next time the
// lights are refreshed, so nothing of it stays behind when it moves or goes.
static u8 s_guest[4];           // x0, y0, w, h in light cells; w = 0: none
void world_light_guest(int x0, int y0, int w, int h) {
    if (x0 < 0) { w += x0; x0 = 0; }
    if (y0 < 0) { h += y0; y0 = 0; }
    if (x0 + w > GRID_W) w = GRID_W - x0;
    if (y0 + h > GRID_W) h = GRID_W - y0;
    if (w <= 0 || h <= 0) return;
    if (s_guest[2]) {           // one not yet put back: cover both
        int x1 = x0 + w, y1 = y0 + h, gx1 = s_guest[0] + s_guest[2], gy1 = s_guest[1] + s_guest[3];
        if (s_guest[0] < x0) x0 = s_guest[0];
        if (s_guest[1] < y0) y0 = s_guest[1];
        w = (x1 > gx1 ? x1 : gx1) - x0; h = (y1 > gy1 ? y1 : gy1) - y0;
    }
    s_guest[0] = x0; s_guest[1] = y0; s_guest[2] = w; s_guest[3] = h;
}

static u8 s_fullCopy = 1;
void world_update_lights(int frame) {
    int gx = g_cam.x >> 15, gy = g_cam.y >> 15;
    u32 nearMask = 0;
    for (int i = 0; i < g_numDLights; i++) {
        DynLight *dl = &g_dlights[i];
        if (dl->def->mode == LIGHT_STEADY) continue;
        int dx = dl->x0 - gx, dx2 = gx - (dl->x0 + dl->w - 1);
        int dy = dl->y0 - gy, dy2 = gy - (dl->y0 + dl->h - 1);
        if (dx2 > dx) dx = dx2;
        if (dy2 > dy) dy = dy2;
        if (dx <= LIGHT_NEAR && dy <= LIGHT_NEAR) nearMask |= 1u << i;
    }
    if (nearMask != s_nearMask) { s_nearMask = nearMask; g_lightsDirty = 1; }
    // The lights flicker ten times a second whatever the frame rate: a step
    // every six logic ticks (frame counts those, 60 a second). Between
    // steps nothing is touched unless something changed.
    u32 since = (u32)frame - s_lightTick;
    if (!g_lightsDirty && since < 6) return;
    s_lightTick = since < 24 ? s_lightTick + 6 : (u32)frame;
    if (g_lightsDirty == 2) { g_lightsDirty = 1; }
    if (g_lightsDirty) {
        g_lightsDirty = 0;
        s_fullCopy = 1;
        bios_cpufastset(g_lightStatic, s_lightBase, (GRID_W * GRID_W) / 4);
        for (int i = 0; i < g_numDLights; i++) {
            DynLight *dl = &g_dlights[i];
            if (!dl->on || !dl->w || !dl->h || (nearMask & (1u << i))) continue;
            int lvl = (s_avgLevel[dl->def->mode] * dl->level) >> 8;
            if (lvl <= 4) continue;
            light_patch(&s_lightBase[(dl->y0 << 6) + dl->x0], dl->patch, dl->w, dl->h, lvl);
        }
    }
    // the full grid is only rebuilt when something changed; otherwise just the
    // rectangles of the flickering lights near the camera are restored and
    // re-lit (restore them all first: their patches can overlap)
    if (s_fullCopy) {
        s_fullCopy = 0;
        bios_cpufastset(s_lightBase, g_lightgrid, (GRID_W * GRID_W) / 4);
    } else {
        for (int y = 0; y < s_guest[3]; y++) {
            int o = ((s_guest[1] + y) << 6) + s_guest[0];
            memcpy(&g_lightgrid[o], &s_lightBase[o], s_guest[2]);
        }
        for (int i = 0; i < g_numDLights; i++) {
            DynLight *dl = &g_dlights[i];
            if (!(nearMask & (1u << i)) || !dl->w || !dl->h) continue;
            for (int y = 0; y < dl->h; y++) {
                int o = ((dl->y0 + y) << 6) + dl->x0;
                memcpy(&g_lightgrid[o], &s_lightBase[o], dl->w);
            }
        }
    }
    s_guest[2] = 0;
    for (int i = 0; i < g_numDLights; i++) {
        DynLight *dl = &g_dlights[i];
        if (!dl->on || !(nearMask & (1u << i))) continue;
        int lvl;
        switch (dl->def->mode) {
        case LIGHT_FLICKER:
            if ((rng_next() & 31) == 0) dl->flick = (rng_next() & 7) + 2;
            lvl = dl->flick ? (dl->flick--, (rng_next() & 1) ? 60 : 0) : 256;
            break;
        case LIGHT_BUZZ:
            lvl = 200 + (rng_next() & 63);
            if ((rng_next() & 63) == 0) lvl = 40;
            break;
        case LIGHT_PULSE: {
            int t = frame & 127; t = t < 64 ? t : 127 - t;
            lvl = 96 + t * 2 + t / 2;
            break; }
        case LIGHT_CANDLE:
            lvl = 200 + (rng_next() & 55);
            break;
        default: lvl = 256;
        }
        lvl = (lvl * dl->level) >> 8;
        if (lvl <= 4) continue;
        if (dl->w && dl->h)
            light_patch(&g_lightgrid[(dl->y0 << 6) + dl->x0], dl->patch, dl->w, dl->h, lvl);
    }
}

// ------------------------------------------------------------- edges
u8 world_edge(int x, int y, int north) {
    if ((unsigned)x >= MAP_W || (unsigned)y >= MAP_H) return 1;
    return g_edges[((((y << MAP_SHIFT) | x)) << 1) + north];
}

// the edge crossed when moving from cell (x,y) in direction dir (0 N, 1 E, 2 S, 3 W)
u8 world_edge_dir(int x, int y, int dir) {
    switch (dir) {
    case 0: return world_edge(x, y, 1);
    case 1: return world_edge(x + 1, y, 0);
    case 2: return world_edge(x, y + 1, 1);
    default: return world_edge(x, y, 0);
    }
}

// walkable through this edge right now? (open, archway, open door)
int world_edge_pass(u8 et) {
    if (!et) return 1;
    const EdgeType *t = &g_edgeTypes[et];
    if (t->kind == EK_ARCH) return 1;
    if (t->kind == EK_DOOR) return g_doors[t->param].open >= 0xC000;
    return 0;
}

static int edge_sight(u8 et) {
    if (!et) return 1;
    const EdgeType *t = &g_edgeTypes[et];
    if (t->kind == EK_ARCH) return 1;
    if (t->kind == EK_DOOR) return g_doors[t->param].open >= 0x6000;
    return 0;
}

Door *world_door_on(u8 et) {
    if (!et) return 0;
    const EdgeType *t = &g_edgeTypes[et];
    return t->kind == EK_DOOR ? &g_doors[t->param] : 0;
}

int world_inside(int x, int y) {
    if ((unsigned)x >= MAP_W || (unsigned)y >= MAP_H) return 0;
    return g_cellFlags[(y << MAP_SHIFT) | x] & 1;
}

// ------------------------------------------------------------- doors
void world_update_doors(void) {
    for (int i = 0; i < g_numDoors; i++) {
        Door *d = &g_doors[i];
        if (d->moving > 0) {
            u32 o = d->open + 1200;
            if (o >= 0xFFFF) { o = 0xFFFF; d->moving = 0; }
            d->open = o;
        } else if (d->moving < 0) {
            s32 o = (s32)d->open - 1200;
            if (o <= 0) { o = 0; d->moving = 0; }
            d->open = o;
        }
    }
}

// Leaf geometry: hinge position, closed direction and current direction.
typedef struct { s32 hx, hy; u16 ang; s32 len; } LeafPose;

static int door_leaves(const Door *d, LeafPose *out) {
    const EdgeType *et = &g_edgeTypes[d->edgeType];
    s32 P = et->panel << 10;
    u32 x = d->open >> 6;
    u32 th = (x * x * (3072 - 2 * x)) >> 20;      // eased 0..1023 (= 90 degrees)
    s32 swing = th << 4;                            // 0..16384
    int n = d->kind == DOOR_DOUBLE ? 2 : 1;
    s32 span = 0x10000 - 2 * P;
    s32 len = n == 2 ? span / 2 : span;
    for (int k = 0; k < n; k++) {
        int hiEnd = n == 2 ? k : (d->hinge & DOORH_HINGEHI) != 0;
        s32 along = hiEnd ? 0x10000 - P : P;
        u16 closed, sw;
        LeafPose *o = &out[k];
        if (d->axis == 0) {             // wall line x = d->x, along y
            o->hx = d->x << 16; o->hy = (d->y << 16) + along;
            closed = hiEnd ? 49152 : 16384;
            sw = (d->hinge & DOORH_SWINGHI) ? 0 : 32768;
        } else {                        // wall line y = d->y, along x
            o->hx = (d->x << 16) + along; o->hy = d->y << 16;
            closed = hiEnd ? 32768 : 0;
            sw = (d->hinge & DOORH_SWINGHI) ? 16384 : 49152;
        }
        int dir = ((u16)(sw - closed) == 16384) ? 1 : -1;
        o->ang = (u16)(closed + dir * swing);
        o->len = len;
    }
    return n;
}

// door leaves as 3D props, rebuilt every frame
void world_door_props(void) {
    int n = 0;
    for (int i = 0; i < g_numDoors && n < MAX_DYNPROPS - 1; i++) {
        const Door *d = &g_doors[i];
        if (d->open == 0) continue;
        LeafPose lp[2];
        int k = door_leaves(d, lp);
        for (int j = 0; j < k; j++) {
            PropInst *p = &g_dynProps[n++];
            p->x = lp[j].hx; p->y = lp[j].hy; p->z = 0;
            p->angle = lp[j].ang;
            p->model = d->kind == DOOR_DOUBLE ? DOOR_MODEL_HALF : DOOR_MODEL_SINGLE;      // (the manifest's DOOR_MODELS)
            p->flags = 0;
            p->tex = d->leafTex;
            p->light = 0;
        }
    }
    g_numDynProps = n;
}

// ------------------------------------------------------------- collision

// push a circle out of an axis-aligned segment: vertical segments lie at
// x = c for y in [a0, a1], horizontal ones at y = c for x in [a0, a1]
static void push_seg(s32 *px, s32 *py, s32 r, int vert, s32 c, s32 a0, s32 a1, s32 oc) {
    s32 u = vert ? *py : *px;
    s32 v = vert ? *px : *py;
    s32 ku = u < a0 ? a0 : (u > a1 ? a1 : u);
    s32 du = u - ku, dv = v - c;
    if (du == 0) {
        if (dv >= r || dv <= -r) return;
        v = (dv > 0 || (dv == 0 && oc >= c)) ? c + r : c - r;
    } else {
        s32 adu = du < 0 ? -du : du, adv = dv < 0 ? -dv : dv;
        if (adu >= r || adv >= r) return;
        u32 d = isqrt32((u32)(adu * adu + adv * adv));
        if (d == 0 || d >= (u32)r) return;
        u = ku + (s32)(((s64)du * r) / (s32)d);
        v = c + (s32)(((s64)dv * r) / (s32)d);
    }
    if (vert) { *px = v; *py = u; } else { *px = u; *py = v; }
}

// one edge (west edge of cell when north == 0, north edge otherwise)
static void collide_edge(s32 *px, s32 *py, s32 r, int x, int y, int north, s32 ox, s32 oy) {
    u8 e = world_edge(x, y, north);
    if (!e) return;
    const EdgeType *t = &g_edgeTypes[e];
    s32 base = north ? (y << 16) : (x << 16);       // the wall line
    s32 a = north ? (x << 16) : (y << 16);          // span start
    int vert = !north;
    s32 oc = vert ? ox : oy;
    if (t->kind == EK_WALL) { push_seg(px, py, r, vert, base, a, a + 0x10000, oc); return; }
    s32 P = t->panel << 10;
    if (P) {
        push_seg(px, py, r, vert, base, a, a + P, oc);
        push_seg(px, py, r, vert, base, a + 0x10000 - P, a + 0x10000, oc);
    }
    if (t->kind == EK_DOOR) {
        Door *d = &g_doors[t->param];
        if (d->open < 0xC000) push_seg(px, py, r, vert, base, a + P, a + 0x10000 - P, oc);
        else {
            // the open leaf stands in the room, perpendicular to the wall
            LeafPose lp[2];
            int k = door_leaves(d, lp);
            for (int j = 0; j < k; j++) {
                s32 ex = lp[j].hx + ((lu_cos(lp[j].ang) * (lp[j].len >> 2)) >> 12);
                s32 ey = lp[j].hy + ((lu_sin(lp[j].ang) * (lp[j].len >> 2)) >> 12);
                if (d->axis == 0)   // leaf runs along x at y = hy
                    push_seg(px, py, r, 0, lp[j].hy, lp[j].hx < ex ? lp[j].hx : ex, lp[j].hx < ex ? ex : lp[j].hx, oy);
                else
                    push_seg(px, py, r, 1, lp[j].hx, lp[j].hy < ey ? lp[j].hy : ey, lp[j].hy < ey ? ey : lp[j].hy, ox);
            }
        }
    }
}

// circle against an axis-aligned box
static void collide_box(s32 *px, s32 *py, s32 r, const CollBox *b) {
    s32 x0 = b->x0 << 8, y0 = b->y0 << 8, x1 = b->x1 << 8, y1 = b->y1 << 8;
    s32 cx = *px < x0 ? x0 : (*px > x1 ? x1 : *px);
    s32 cy = *py < y0 ? y0 : (*py > y1 ? y1 : *py);
    s32 dx = *px - cx, dy = *py - cy;
    if (dx == 0 && dy == 0) {
        // centre inside: leave through the nearest side
        s32 l = *px - x0, rr = x1 - *px, t = *py - y0, bb = y1 - *py;
        s32 m = l; int s = 0;
        if (rr < m) { m = rr; s = 1; }
        if (t < m) { m = t; s = 2; }
        if (bb < m) { m = bb; s = 3; }
        if (s == 0) *px = x0 - r; else if (s == 1) *px = x1 + r; else if (s == 2) *py = y0 - r; else *py = y1 + r;
        return;
    }
    s32 adx = dx < 0 ? -dx : dx, ady = dy < 0 ? -dy : dy;
    if (adx >= r || ady >= r) return;
    u32 d = isqrt32((u32)(adx * adx + ady * ady));
    if (d >= (u32)r || d == 0) return;
    *px = cx + (s32)(((s64)dx * r) / (s32)d);
    *py = cy + (s32)(((s64)dy * r) / (s32)d);
}

// Walking mostly straight into a doorway slides the player into line with it.
static void door_assist(s32 *px, s32 *py, s32 dx, s32 dy, s32 r) {
    int tx = *px >> 16, ty = *py >> 16;
    for (int y = ty - 1; y <= ty + 1; y++)
        for (int x = tx - 1; x <= tx + 1; x++)
            for (int north = 0; north < 2; north++) {
                u8 e = world_edge(x, y, north);
                if (!e || !world_edge_pass(e)) continue;
                const EdgeType *t = &g_edgeTypes[e];
                s32 P = t->panel << 10;
                if (!P) continue;
                int ax = !north;       // passage along x through a west edge
                s32 plane = ax ? (x << 16) : (y << 16);
                s32 centre = (ax ? (y << 16) : (x << 16)) + 0x8000;
                s32 hw = 0x8000 - P;
                s32 pa = ax ? *px : *py, pl = ax ? *py : *px;
                s32 ma = ax ? dx : dy, ml = ax ? dy : dx;
                s32 dist = plane - pa;
                if (dist > r + 0x2000 || dist < -(r + 0x2000)) continue;
                if (ma == 0 || (dist > 0) != (ma > 0)) continue;
                s32 ama = ma < 0 ? -ma : ma, aml = ml < 0 ? -ml : ml;
                if (aml * 2 > ama) continue;
                s32 off = pl - centre, aoff = off < 0 ? -off : off;
                s32 lim = hw - r - 0x300;
                if (lim < 0) lim = 0;
                if (aoff <= lim || aoff > hw + r + 0x1800) continue;
                s32 corr = aoff - lim, step = ama + 0x200;
                if (corr > step) corr = step;
                pl += off > 0 ? -corr : corr;
                if (ax) *py = pl; else *px = pl;
            }
}

// Move a circle of radius r (16.16) by (dx,dy), sliding along walls, door
// frames, open leaves and furniture.
void world_move(s32 *px, s32 *py, s32 dx, s32 dy, s32 r) {
    if (!dx && !dy) return;            // standing still: nothing new to bump into
    door_assist(px, py, dx, dy, r);
    const s32 ox = *px, oy = *py;
    *px += dx; *py += dy;
    for (int pass = 0; pass < 2; pass++) {
        s32 sx = *px, sy = *py;
        if (pass && sx == ox + dx && sy == oy + dy) break;     // the first pass touched nothing
        int tx = *px >> 16, ty = *py >> 16;
        // only the edges the circle's bounding box can touch
        int x0 = (*px - r) >> 16, x1 = (*px + r) >> 16, y0 = (*py - r) >> 16, y1 = (*py + r) >> 16;
        for (int y = y0; y <= y1; y++)
            for (int x = x0; x <= x1 + 1; x++)
                if ((unsigned)x < MAP_W && (unsigned)y < MAP_H) collide_edge(px, py, r, x, y, 0, ox, oy);
        for (int y = y0; y <= y1 + 1; y++)
            for (int x = x0; x <= x1; x++)
                if ((unsigned)x < MAP_W && (unsigned)y < MAP_H) collide_edge(px, py, r, x, y, 1, ox, oy);
        // open door leaves stand out into the room, away from their edge
        for (int i = 0; i < g_numDoors; i++) {
            Door *d = &g_doors[i];
            if (d->open < 0xC000) continue;
            s32 ddx = *px - (d->x << 16), ddy = *py - (d->y << 16);
            if (ddx > 0x1C000 || ddx < -0x1C000 || ddy > 0x1C000 || ddy < -0x1C000) continue;
            int ex = d->x, ey = d->y;
            if (ex >= x0 && ex <= x1 + 1 && ey >= y0 && ey <= y1 + 1) continue;   // already done
            collide_edge(px, py, r, ex, ey, d->axis, ox, oy);
        }
        // furniture
        if ((unsigned)tx < MAP_W && (unsigned)ty < MAP_H) {
            const u8 *lst = g_level->boxList + g_level->cellBox[(ty << MAP_SHIFT) | tx];
            for (; *lst != 255; lst++) collide_box(px, py, r, &g_level->boxes[*lst]);
        }
    }
}

// is a point inside any furniture footprint? (for placing the creature)
int world_point_blocked(s32 x, s32 y) {
    int tx = x >> 16, ty = y >> 16;
    if ((unsigned)tx >= MAP_W || (unsigned)ty >= MAP_H) return 1;
    const u8 *lst = g_level->boxList + g_level->cellBox[(ty << MAP_SHIFT) | tx];
    for (; *lst != 255; lst++) {
        const CollBox *b = &g_level->boxes[*lst];
        if (x > (b->x0 << 8) && x < (b->x1 << 8) && y > (b->y0 << 8) && y < (b->y1 << 8)) return 1;
    }
    return 0;
}

// ------------------------------------------------------------- sight
// Line of sight between two points: walls and closed doors block.
int world_los(s32 x0, s32 y0, s32 x1, s32 y1) {
    s32 dx = x1 - x0, dy = y1 - y0;
    int mx = x0 >> 16, my = y0 >> 16, ex = x1 >> 16, ey = y1 >> 16;
    int sx = dx > 0 ? 1 : -1, sy = dy > 0 ? 1 : -1;
    s32 adx = dx < 0 ? -dx : dx, ady = dy < 0 ? -dy : dy;
    // parametric distances to the next x / y boundary (in units where the segment is 1)
    s64 tx = adx ? (s64)((sx > 0 ? ((mx + 1) << 16) - x0 : x0 - (mx << 16))) * ady : 0x7FFFFFFFFFFFll;
    s64 ty = ady ? (s64)((sy > 0 ? ((my + 1) << 16) - y0 : y0 - (my << 16))) * adx : 0x7FFFFFFFFFFFll;
    s64 stepx = (s64)ady << 16, stepy = (s64)adx << 16;
    for (int guard = 0; guard < 64; guard++) {
        if (mx == ex && my == ey) return 1;
        if (tx <= ty && adx) {
            u8 e = sx > 0 ? world_edge(mx + 1, my, 0) : world_edge(mx, my, 0);
            if (!edge_sight(e)) return 0;
            mx += sx; tx += stepx;
        } else if (ady) {
            u8 e = sy > 0 ? world_edge(mx, my + 1, 1) : world_edge(mx, my, 1);
            if (!edge_sight(e)) return 0;
            my += sy; ty += stepy;
        } else return 1;
    }
    return 1;
}

// ---------------------------------------------------------------- maths
s32 isqrt32(u32 v) {
    u32 r = 0, b = 1u << 30;
    while (b > v) b >>= 2;
    while (b) {
        if (v >= r + b) { v -= r + b; r = (r >> 1) + b; }
        else r >>= 1;
        b >>= 2;
    }
    return r;
}

s32 dist_approx(s32 dx, s32 dy) {
    if (dx < 0) dx = -dx;
    if (dy < 0) dy = -dy;
    if (dx < 0x1000000 && dy < 0x1000000) {
        u32 a = dx >> 6, b = dy >> 6;
        return isqrt32(a * a + b * b) << 6;
    }
    if (dx < dy) { s32 t = dx; dx = dy; dy = t; }
    return dx + ((dy * 3) >> 3) + (dy >> 5);
}

u16 angle_to(s32 dx, s32 dy) {
    // octant-based atan2 approximation, 0..65535
    if (dx == 0 && dy == 0) return 0;
    s32 ax = dx < 0 ? -dx : dx, ay = dy < 0 ? -dy : dy;
    while ((ax | ay) >= 0x10000) { ax >>= 1; ay >>= 1; }     // (the quotient in 32 bits; 15 good bits left)
    s32 a;
    if (ax >= ay) {
        s32 t = (ay << 15) / ax;                      // tan in Q15 (0..1)
        a = (t * 8192 >> 15) + ((t * (32768 - t) >> 15) * 2289 >> 15);   // atan(t)/(2pi)*65536
    } else {
        s32 t = (ax << 15) / ay;
        a = 16384 - ((t * 8192 >> 15) + ((t * (32768 - t) >> 15) * 2289 >> 15));
    }
    if (dx < 0) a = 32768 - a;
    if (dy < 0) a = 65536 - a;
    return (u16)a;
}
