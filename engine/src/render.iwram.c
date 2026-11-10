// SPDX-License-Identifier: MIT
// Hollowmere world renderer: thin-wall raycaster with see-through doorways,
// per-room floor/ceiling materials and colormap lighting, full resolution.
// Compiled as ARM code and placed in IWRAM.
//
// A frame: mark the wall rows that big furniture faces will hide; cast all
// 240 rays; fill floors and ceilings; draw walls and lintels; then the
// objects (3D furniture, door leaves, sprites; objects.iwram.c) far to near.
#include "engine.h"
#include "assets.h"
#include "render.h"
#include "dev.h"

// ---------------------------------------------------------------- state
// g_colormap (32 light levels x 256 colours) lives in VRAM, see gba.ld
#ifdef PIXCNT
u32 g_castStat[8];
#endif
// g_zbuf: perpendicular distance of each column's solid wall (VRAM, see gba.ld)
// g_zmax8, g_zmin8, g_cdmin8: per block of 8 columns (VRAM, see gba.ld)
extern s32 g_zmax8[VIEW_W / 8], g_zmin8[VIEW_W / 8], g_cdmin8[VIEW_W / 8];
EWRAM_BSS u8 g_edges[MAP_W * MAP_H * 2] ALIGN4;
const EdgeType *g_edgeTypes;

#define MAXOV 2      // see-through openings remembered per column (nearest first)

// for objects: anything farther than clipDepth is hidden above row clipTop
// g_clipTop / g_clipDepth live in VRAM (see gba.ld)

// tables (filled by render_init / render_build_flash_tables)
// g_camX (Q14 camera-plane coordinate per column), g_coneOf (flashlight cone
// class per column, 0 = centre) and g_rowDist2 (floor pair distance, 8.8
// tiles) live in VRAM (see gba.ld; rebuilt by render_enter_3d)
EWRAM_BSS u8 g_flashW[NCONE][256];      // wall light by cone class and dist (1/16 tile)
// g_flatTbl / g_flatTblF (per-pair d<<16 | lc<<8 | lf, 0 ends) live in VRAM, see gba.ld
extern u32 g_flatTbl[NCONE][NPAIR_C + 1];
extern u32 g_flatTblF[NCONE][NPAIR_F - NPAIR_C + 1];
FlatCtx g_flatCtx;
s32 g_floorSplit = 0;
s32 g_wallHalfLh = 0;
// g_fullC0, g_fullC1: the full-resolution band of columns (the rest: one
// sample per pair); defined next to each other in propasm.s (read as a pair)

typedef struct { u32 sdx, sdy, ddx, ddy; const u8 *p; s32 stepXb, stepYb, ex, ey; } DDAE;
extern u32 dda_edge(DDAE *d);

// Occluders: rows of the wall that big opaque prop faces in front of it will
// cover anyway (filled by the object pre-pass; covF = depth of the face).
// In spare VRAM (see gba.ld).
extern s16 g_covT[VIEW_W], g_covB[VIEW_W];
extern s32 g_covF[VIEW_W];

typedef struct {
    s32 dist;
    u32 lh;
    const u8 *tcol;
    u8 light, nov, pad[2];
    s32 ovDist[MAXOV];
    const u8 *ovTex[MAXOV];
    u8 ovLight[MAXOV], ovLintel[MAXOV];
    // for interpolating the column between two hits on the same plain wall
    u32 key;            // edge cell << 1 | side; 0 = not a plain wall
    const u8 *tex;      // texture of the face hit
    u16 f;              // hit position along the edge (16-bit fraction)
    u8 flip, gl;        // texture read right to left; light grid level
} ColHit;

typedef struct {
    s32 px, py, dirX, dirY, plX, plY;
    const u8 *edges, *start;
    const EdgeType *types;
    u32 fracX, fracY;
    u16 camA;
} CastCtx;

// cast the ray of one column through the thin-wall map
IWRAM_CODE static void cast_column(const CastCtx *k, int col, ColHit *h) {
    u32 ai = ((u16)(k->camA + ray_angle[col])) >> 4;        // 0..4095
    s32 rc = sin4096[(ai + 1024) & 4095];                   // cos, Q14
    s32 rs = sin4096[ai];                                   // sin, Q14
    u32 ddx = sec4096[ai];                                  // |1/cos| 16.16
    u32 ddy = sec4096[(ai + 3072) & 4095];                  // |1/sin|
    s32 fish = ray_fishcos[col];
    const s32 px = k->px, py = k->py;
    DDAE dd;
    int stepX, stepY;
    dd.ddx = ddx; dd.ddy = ddy;
    if (rc < 0) { stepX = -1; dd.sdx = (u32)(((u64)k->fracX * ddx) >> 16); }
    else        { stepX = 1;  dd.sdx = (u32)(((u64)(0x10000 - k->fracX) * ddx) >> 16); }
    if (rs < 0) { stepY = -1; dd.sdy = (u32)(((u64)k->fracY * ddy) >> 16); }
    else        { stepY = 1;  dd.sdy = (u32)(((u64)(0x10000 - k->fracY) * ddy) >> 16); }
    dd.p = k->start;
    dd.stepXb = stepX * 2; dd.stepYb = stepY * (MAP_W * 2);
    dd.ex = stepX > 0 ? 0 : 2;
    dd.ey = stepY > 0 ? 1 : MAP_W * 2 + 1;
    const u8 *edges = k->edges;
    const EdgeType *types = k->types;

#ifdef PIXCNT
    g_castStat[0]++;
#endif
    int nov = 0;
    s32 e = 0x80000;
    const u8 *tex = walltex[0];
    u32 texx = 0, ff = 0, flip = 0, key = 0;
    int side = 0, gx = 0, gy = 0;
    for (int guard = 0; guard < 24; guard++) {
        u32 r = dda_edge(&dd);
        const EdgeType *et = &types[r & 0xFF];
        side = r >> 8;
        s32 w;
        int low;            // viewer on the low-coordinate side of the edge
        if (side == 0) { e = (s32)(dd.sdx - ddx); w = py + (s32)(((s64)e * rs) >> 14); low = stepX > 0; }
        else           { e = (s32)(dd.sdy - ddy); w = px + (s32)(((s64)e * rc) >> 14); low = stepY > 0; }
        u32 f = w & 0xFFFF;
        u32 tx = f >> 10;
        u32 fl = side == 0 ? stepX < 0 : stepY > 0;
        if (fl) tx = 63 - tx;      // read left to right
        int fi = low ? 0 : 1;
        u32 tid = et->tex[fi];
        // light: the half cell just in front of the edge, on the viewer's side
        int cell = (dd.p - edges) >> 1;
        if (side == 0) {
            int bx = (cell & (MAP_W - 1)) + (stepX < 0);
            gx = 2 * bx - (stepX > 0); gy = w >> 15;
        } else {
            int by = (cell >> MAP_SHIFT) + (stepY < 0);
            gy = 2 * by - (stepY > 0); gx = w >> 15;
        }
        if (et->kind != EK_WALL) {
            u32 pw = (u32)et->panel << 10;
            if (f >= pw && f < 0x10000 - pw) {
                int closed = et->kind == EK_DOOR && g_doors[et->param].open == 0;
                if (closed) tid = et->alt[fi];
                else {
                    // see-through: remember the lintel above the opening, keep going
                    if (nov < MAXOV) {
                        h->ovDist[nov] = (s32)(((s64)e * fish) >> 14);
                        h->ovTex[nov] = walltex[tid] + (tx << 7);
                        h->ovLight[nov] = g_lightgrid[((gy & 63) << 6) | (gx & 63)] & LG_LIGHT;
                        h->ovLintel[nov] = et->lintel;
                        nov++;
                    }
                    continue;
                }
            }
        }
        tex = walltex[tid];
        texx = tx;
        ff = f; flip = fl;
        if (et->kind == EK_WALL) key = ((u32)(dd.p - edges) << 1) | side | 0x80000000u;
        break;
    }
    h->nov = nov;
#ifdef PIXCNT
    if (nov) g_castStat[2]++;
    if (!key) g_castStat[3]++;
#endif
    s32 dist = (s32)(((s64)e * fish) >> 14);
    if (dist < 0x1000) dist = 0x1000;
    h->dist = dist;
    g_zbuf[col] = dist;
    u32 lh;
    if (dist < (8 << 16)) lh = lh_near[dist >> 6];
    else { u32 i = dist >> 9; lh = i < 8192 ? lh_far[i] : 2; }
    h->lh = lh;
    h->tcol = tex + (texx << 7);
    u32 di = dist >> 12; if (di > 255) di = 255;
    u32 l = g_flashW[g_coneOf[col]][di];
    u32 gl = g_lightgrid[((gy & 63) << 6) | (gx & 63)] & LG_LIGHT;
    h->key = nov ? 0 : key;
    h->tex = tex; h->f = ff; h->flip = flip; h->gl = gl;
    if (gl > l) l = gl;
    if (side && l > 1) l--;   // subtle axis shading
    h->light = l;
}

// The column between two columns that hit the same plain wall hits it too:
// on a plane 1/z and u/z are linear across the screen, so its distance and
// texture coordinate follow from the neighbours' without a ray.
IWRAM_CODE static void lerp_column(int col, const ColHit *a, const ColHit *c, ColHit *h) {
#ifdef PIXCNT
    g_castStat[1]++;
#endif
    s32 wa = (s32)rcp16((u32)a->dist), wc = (s32)rcp16((u32)c->dist);
    u32 rs = rcp16((u32)(wa + wc));
    s32 dist = (s32)(rs << 1);
    if (dist < 0x1000) dist = 0x1000;
    s32 t = (s32)(((u64)(u32)wc * rs) >> 16);              // weight of c (16.16)
    s32 f = a->f + (s32)(((s64)((s32)c->f - (s32)a->f) * t) >> 16);
    u32 tx = (u32)f >> 10;
    if (a->flip) tx = 63 - tx;
    h->nov = 0;
    h->dist = dist;
    g_zbuf[col] = dist;
    u32 lh;
    if (dist < (8 << 16)) lh = lh_near[dist >> 6];
    else { u32 i = dist >> 9; lh = i < 8192 ? lh_far[i] : 2; }
    h->lh = lh;
    h->tex = a->tex;
    h->tcol = a->tex + (tx << 7);
    h->key = a->key; h->f = f; h->flip = a->flip;
    u32 gl = ((u32)f >> 15) == ((u32)a->f >> 15) ? a->gl : c->gl;
    h->gl = gl;
    u32 di = dist >> 12; if (di > 255) di = 255;
    u32 l = g_flashW[g_coneOf[col]][di];
    if (gl > l) l = gl;
    if ((a->key & 1) && l > 1) l--;
    h->light = l;
}

// ------------------------------------------------------------ walls
typedef struct { s32 y0, y1, top; u32 step; } WallSpan;

static inline void wall_span(const ColHit *h, WallSpan *w) {
    int top = HORIZON - (int)(h->lh >> 1);
    int y0 = top, y1 = top + (int)h->lh;
    if (y0 < ROW0) y0 = ROW0;
    if (y1 > ROW1) y1 = ROW1;
    w->top = top; w->y0 = y0; w->y1 = y1;
    w->step = (u32)(((u64)h->dist * 26214) >> 16);     // 128 texels / lh rows = 0.4 * dist
}

// what a column's openings hide of the objects behind them: anything
// farther than the nearest opening is cut off above its lintel
__attribute__((optimize("Os"))) IWRAM_CODE static void lintel_clip(int col, const ColHit *h) {
    s32 cd = 0x7FFFFFFF;
    int ct = ROW0;
    for (int k = 0; k < h->nov; k++) {
        s32 od = h->ovDist[k];
        if (od < 0x1000) od = 0x1000;
        u32 olh = od < (8 << 16) ? lh_near[od >> 6] : lh_far[od >> 9];
        int otop = HORIZON - (int)(olh >> 1);
        int obot = otop + (int)((olh * (u32)(WALL_H * 32 - h->ovLintel[k])) >> 6);
        if (od < cd) cd = od;
        if (obot > ct) ct = obot;
    }
    g_clipDepth[col] = cd;
    g_clipTop[col] = ct;
}

// lintels over the openings a column looks through, far to near
__attribute__((optimize("Os"))) IWRAM_CODE static void draw_lintels(u8 *fb, int col, const ColHit *h) {
    int cone = g_coneOf[col];
    for (int k = h->nov - 1; k >= 0; k--) {
        s32 od = h->ovDist[k];
        if (od < 0x1000) od = 0x1000;
        u32 olh = od < (8 << 16) ? lh_near[od >> 6] : lh_far[od >> 9];
        int otop = HORIZON - (int)(olh >> 1);
        // the lintel covers the wall above the opening height
        int obot = otop + (int)((olh * (u32)(WALL_H * 32 - h->ovLintel[k])) >> 6);
        int a = otop < ROW0 ? ROW0 : otop, b = obot > ROW1 ? ROW1 : obot;
        if (b <= a) continue;
        u32 ostep = (u32)(((u64)od * 26214) >> 16);
        u32 ol = g_flashW[cone][od >> 12 > 255 ? 255 : od >> 12];
        if (h->ovLight[k] > ol) ol = h->ovLight[k];
        col_one(fb + a * 240 + col, b - a, h->ovTex[k], g_colormap + (ol << 8), (u32)(a - otop) * ostep, ostep);
    }
}

// the rows of a column's wall that a big prop face in front of it will hide
static inline void occ_rows(int col, s32 dist, s32 *sT, s32 *sB) {
    if (g_covF[col] < dist) { *sT = g_covT[col]; *sB = g_covB[col]; }
    else { *sT = *sB = ROW1; }
}

// the walls of a column pair (rasm.s)
extern void wall_pair(u8 *fb, int col, const ColHit *ha, const ColHit *hb);

// four columns of one plain wall at once (rasm.s)
typedef struct {
    u8 *p0; s32 ra, rb, Y0, Y1; s32 y0[4], y1[4];
    const u8 *qtex; u32 tp, st; const u8 *cm[4]; u32 flip, hmax;
} QuadArgs;
extern void quad_span(QuadArgs *q);

// The four columns of a group on one plain wall, at a level where its
// texels are about one per column: drawn together, each row from one read
// of four neighbouring texels (the quad's texels may stand one off from each
// column's own, and column 1's rows stand for all four). Returns 0 when they
// do not qualify (the pairs draw them then). (rasm.s)
extern int wall_quad(u8 *fb, int col, const ColHit *h);

// ------------------------------------------------------------- the frame
#ifdef DEV
u32 g_profStage[4];          // cycles: ray casting, floors + walls, occluder pass, objects
u32 g_profNoIrq;             // bench: render with interrupts off
volatile u32 g_noObjects;    // bench: skip the objects
#endif

IWRAM_CODE void render_view(u8 *fb) {
#ifdef DEV
    u16 ime = REG_IME;
    if (g_profNoIrq) REG_IME = 0;
#endif
#ifdef PIXCNT
    { volatile u32 *pc = (volatile u32 *)0x02037000; for (int i = 0; i < 20; i++) pc[i] = 0; }
    for (int i = 0; i < 4; i++) g_castStat[i] = 0;
#endif
    DEV_ONLY(u32 t0 = PROF_T();)
    occluders_prepass();
    DEV_ONLY(u32 t1 = PROF_T();)
    CastCtx k;
    k.px = g_cam.x; k.py = g_cam.y;
    k.dirX = g_cam.dirX; k.dirY = g_cam.dirY;
    k.plX = g_cam.planeX; k.plY = g_cam.planeY;
    k.edges = g_edges;
    k.types = g_edgeTypes;
    k.fracX = k.px & 0xFFFF; k.fracY = k.py & 0xFFFF;
    k.camA = g_cam.angle;
    k.start = k.edges + ((((k.py >> 16) << MAP_SHIFT) | (k.px >> 16)) << 1);
    g_flatCtx.px64 = k.px << 6;
    g_flatCtx.py64 = k.py << 6;
    int js = g_floorSplit;
    DEV_ONLY(u32 tc = 0;)
    // The view in groups of four columns, left to right. Rays: every even
    // column, the odd ones in between mostly interpolated on plain walls
    // (a ring of the last few hits, in IWRAM).
    ColHit ring[8];
    #define H(c) (&ring[(c) & 7])
    DEV_ONLY(u32 tq = PROF_T();)
    cast_column(&k, 0, H(0));
    DEV_ONLY(tc += PROF_T() - tq;)
    for (int col = 0; col < VIEW_W; col += 4) {
        DEV_ONLY(tq = PROF_T();)
        // every fourth column is cast; the one between two hits on the same
        // plain wall is interpolated, then the odd ones the same way
        if (col + 4 < VIEW_W) {
            cast_column(&k, col + 4, H(col + 4));
            if (H(col)->key && H(col)->key == H(col + 4)->key) lerp_column(col + 2, H(col), H(col + 4), H(col + 2));
            else cast_column(&k, col + 2, H(col + 2));
        } else cast_column(&k, col + 2, H(col + 2));
        if (g_fullC0 >= g_fullC1 && g_wallHalfLh > 320) {
            // everything at half resolution: the odd columns repeat the even ones
            for (int o = col + 1; o < col + 4; o += 2) { *H(o) = *H(o - 1); g_zbuf[o] = g_zbuf[o - 1]; }
        } else for (int o = col + 1; o < col + 4; o += 2) {
            ColHit *a = H(o - 1), *c = H(o + 1);
            if (o + 1 < VIEW_W && a->key && a->key == c->key) lerp_column(o, a, c, H(o));
            else cast_column(&k, o, H(o));
        }
        for (int c = col; c < col + 4; c++) {
            if (H(c)->nov) lintel_clip(c, H(c));
            else { g_clipDepth[c] = 0x7FFFFFFF; g_clipTop[c] = ROW0; }
        }
        {   // the farthest and nearest wall and the nearest lintel in each
            // block of 8 columns (prop culling, depth tests skipped)
            s32 mx = g_zbuf[col], mn = mx, cd = g_clipDepth[col];
            for (int c = col + 1; c < col + 4; c++) {
                s32 z = g_zbuf[c];
                if (z > mx) mx = z;
                if (z < mn) mn = z;
                if (g_clipDepth[c] < cd) cd = g_clipDepth[c];
            }
            int b = col >> 3;
            if (col & 4) {
                if (g_zmax8[b] > mx) mx = g_zmax8[b];
                if (g_zmin8[b] < mn) mn = g_zmin8[b];
                if (g_cdmin8[b] < cd) cd = g_cdmin8[b];
            }
            g_zmax8[b] = mx; g_zmin8[b] = mn; g_cdmin8[b] = cd;
        }
        DEV_ONLY(tc += PROF_T() - tq;)
        // floors and ceilings: one sample per 2x2 pixels near the viewer, per
        // 4x2 beyond g_floorSplit (far, small and dim), along the ray between
        // the columns sampled
        const ColHit *h0 = H(col), *h1 = H(col + 1), *h2 = H(col + 2), *h3 = H(col + 3);
        u32 m0 = h0->lh < h1->lh ? h0->lh : h1->lh;
        u32 m1 = h2->lh < h3->lh ? h2->lh : h3->lh;
        int jg = (int)((m0 < m1 ? m0 : m1) >> 2);   // row pairs from the eye line to the lowest wall foot
        if (jg < js) {
            int cone = g_coneOf[col + 1];
            s32 cx = (g_camX[col + 1] + g_camX[col + 2]) >> 1;
            s32 rdx = k.dirX + ((k.plX * cx) >> 14), rdy = k.dirY + ((k.plY * cx) >> 14);
            int j = jg;
            if (j < NPAIR_C) {
                int e = js < NPAIR_C ? js : NPAIR_C;
                u32 *t = &g_flatTbl[cone][e], keep = *t;
                *t = 0;
                flat_column2(fb + (HORIZON + 2 * j) * 240 + col, fb + (HORIZON - 1 - 2 * j) * 240 + col,
                             &g_flatTbl[cone][j], &g_flatCtx, rdx, rdy);
                *t = keep;
                j = e;
            }
            if (j < js && j >= NPAIR_C) {
                u32 *t = &g_flatTblF[cone][js - NPAIR_C], keep = *t;
                *t = 0;
                flat_floor2(fb + (HORIZON + 2 * j) * 240 + col, &g_flatTblF[cone][j - NPAIR_C], &g_flatCtx, rdx, rdy);
                *t = keep;
            }
        }
        for (int pc = col; pc < col + 4; pc += 2) {
            const ColHit *ha = H(pc), *hb = H(pc + 1);
            s32 cx = (g_camX[pc] + g_camX[pc + 1]) >> 1;
            s32 rdx = k.dirX + ((k.plX * cx) >> 14);
            s32 rdy = k.dirY + ((k.plY * cx) >> 14);
            u32 lhm = ha->lh < hb->lh ? ha->lh : hb->lh;
            int j = (int)(lhm >> 2);
            if (j < js) j = js;
            if (j < NPAIR_F) {
                int cone = g_coneOf[pc];
                if (j < NPAIR_C) {
                    flat_column(fb + (HORIZON + 2 * j) * 240 + pc, fb + (HORIZON - 1 - 2 * j) * 240 + pc,
                                &g_flatTbl[cone][j], &g_flatCtx, rdx, rdy);
                    j = NPAIR_C;
                }
                flat_floor(fb + (HORIZON + 2 * j) * 240 + pc, &g_flatTblF[cone][j - NPAIR_C], &g_flatCtx, rdx, rdy);
            }
        }
        // walls and lintels (skipping rows big furniture faces will hide)
        if (!wall_quad(fb, col, H(col))) {
#ifdef PIXCNT
            ((volatile u32 *)0x02037000)[11]++;
#endif
            wall_pair(fb, col, H(col), H(col + 1));
            wall_pair(fb, col + 2, H(col + 2), H(col + 3));
        }
        for (int c = col; c < col + 4; c++) if (H(c)->nov) draw_lintels(fb, c, H(c));
    }
    #undef H
    DEV_ONLY(u32 t2 = PROF_T();)
#ifdef PIXCNT
    { volatile u32 *pc = (volatile u32 *)0x02037000; for (int i = 0; i < 20; i++) pc[64 + i] = pc[i]; }
#endif
    // objects, far to near
#ifdef DEV
    if (!g_noObjects)
#endif
    draw_objects(fb);
    DEV_ONLY(u32 t3 = PROF_T();)
#ifdef PIXCNT
    { volatile u32 *pc = (volatile u32 *)0x02037000; for (int i = 0; i < 20; i++) { pc[32 + i] = pc[i]; pc[96 + i] = pc[64 + i]; }
      for (int i = 0; i < 4; i++) pc[124 + i] = g_castStat[i]; }
#endif
#ifdef DEV
    g_profStage[0] = tc; g_profStage[1] = t2 - t1 - tc; g_profStage[2] = t1 - t0; g_profStage[3] = t3 - t2;
    REG_IME = ime;
#endif
}
