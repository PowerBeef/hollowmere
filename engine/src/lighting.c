// SPDX-License-Identifier: MIT
// Render tables and flashlight light tables (ROM, thumb)
#include "engine.h"
#include "assets.h"
#include "gfx.h"
#include "fx.h"

extern s16 g_camX[VIEW_W];
extern u16 g_rowDist2[NPAIR_F];
extern u8  g_coneOf[VIEW_W];
extern u8  (*g_flashW)[256];
extern u32 g_flatTbl[NCONE][NPAIR_C + 1];
extern u32 g_flatTblF[NCONE][NPAIR_F - NPAIR_C + 1];

u8  g_flashOn = 1;
s16 g_flashPower = 256;
s16 g_ambientBoost = 0;
s16 g_minLight = 0;


// the per-column tables in VRAM (16-bit writes only; menus overwrite them)
static void render_column_tables(void) {
    for (int c = 0; c < VIEW_W; c += 2) {
        u16 cls2 = 0;
        for (int k = 0; k < 2; k++) {
            s32 cx = ((2 * (c + k) + 1) * 16384) / VIEW_W - 16384;
            g_camX[c + k] = cx;
            s32 a = cx < 0 ? -cx : cx;
            int cls = (a * NCONE) >> 14;
            cls2 |= (cls > NCONE - 1 ? NCONE - 1 : cls) << (8 * k);
        }
        *(vu16 *)&g_coneOf[c] = cls2;
    }
    // floor distance of row pair j: eye height (1 tile) * FOCAL / (2j+1), in 8.8
    for (int j = 0; j < NPAIR_F; j++) g_rowDist2[j] = (FOCAL * 256 + j) / (2 * j + 1);
}

EWRAM_BSS u8 g_colormapSrc[8192] ALIGN4;

// Menu screens use whole mode-4 pages, including the rows the 3D view keeps
// its colour map in (see gba.ld): put it back before the next 3D frame.
void render_enter_3d(void) {
    if (g_vram3d) return;
    // The page on screen was drawn by a menu at full height, and the tables
    // go into rows of it: close the cinema bars over it first (one vblank).
    FxState keep = g_fx;
    g_fx.mode3d = 0; g_fx.bars = 1;
    g_fx.bobY = g_fx.offX = g_fx.offY = 0; g_fx.roll = 0; g_fx.zoom = 256; g_fx.wave = 0; g_fx.vignette = 0; g_fx.slits = 0;
    fx_prepare();
    vsync();
    g_fx = keep;
    bios_cpufastset(g_colormapSrc, g_colormap, 8192 / 4);
    render_column_tables();
    g_vram3d = 1;
}

// ------------------------------------------------------ flashlight tables
// What the flashlight adds to walls (by cone class and distance) and to
// floors and ceilings (by cone class and row pair) depends on its power.
// Working a set of tables out takes 0.36 million cycles, close to half a
// frame, and the power changes all the time: the beam flickers when the
// battery is low or the enemy is near, and fades with the battery. So the
// sets are kept: one per power step (16 steps), a handful of them, the
// least recently used making room. A set that is not there yet is worked
// out one cone class per frame while the nearest one stands in; the game
// has the ones it switches between without warning made in advance
// (render_flash_warm). A light floor (lightning, a script's ambient boost)
// has a set of its own, worked out on the spot.
#define FLASH_SETS 5
typedef struct {
    u8  wall[NCONE][256];
    u32 flatC[NCONE][NPAIR_C + 1];
    u32 flatF[NCONE][NPAIR_F - NPAIR_C + 1];
} FlashSet;
EWRAM_BSS static FlashSet s_set[FLASH_SETS + 1];        // the last one: the set with a light floor
static s8  s_step[FLASH_SETS] = { -1, -1, -1, -1, -1 }; // the power step each holds (power / 16)
static u8  s_used[FLASH_SETS];                           // a clock value: when it was last the one in use
static u8  s_clock;
static s8  s_cur = -1;                                   // the set whose tables the renderer has
static s8  s_making = -1;                                // the set being worked out, s_makeCone cones done
static u8  s_makeCone, s_makeStep;
static s16 s_floorPower = -1, s_floorLevel = -1;         // what the floor set was made for
static u16 s_rowDist[NPAIR_F];                           // the row pairs' floor distances (as g_rowDist2, which menus overwrite)

static void flash_cone(FlashSet *t, int c, s32 p, s32 floor) {
    const u8 *bw = beam_wall + c * 256;
    u8 *dw = t->wall[c];
    for (int d = 0; d < 256; d++) {
        s32 l = (bw[d] * p) >> 11;
        s32 nv = nv_wall[d];
        if (nv > l) l = nv;
        if (floor > l) l = floor;
        dw[d] = l > 31 ? 31 : l;
    }
    const u8 *bf = beam_floor + c * NPAIR_F, *bc = beam_ceil + c * NPAIR_F;
    for (int j = 0; j < NPAIR_F; j++) {
        s32 lf = (bf[j] * p) >> 11, lc = (bc[j] * p) >> 11;
        s32 nv = nv_floor[j];
        if (nv > lf) lf = nv;
        if (nv > lc) lc = nv;
        if (floor > lf) lf = floor;
        if (floor > lc) lc = floor;
        if (lf > 31) lf = 31;
        if (lc > 31) lc = 31;
        u32 w = ((u32)s_rowDist[j] << 16) | (lc << 8) | lf;
        if (j < NPAIR_C) t->flatC[c][j] = w;
        else t->flatF[c][j - NPAIR_C] = w;
    }
    t->flatC[c][NPAIR_C] = 0;
    t->flatF[c][NPAIR_F - NPAIR_C] = 0;
}

// hand a set to the renderer: the wall table by pointer, the floor tables
// copied into their place in video memory
static void flash_use(int i) {
    if (i < FLASH_SETS) s_used[i] = ++s_clock;
    if (i == s_cur) return;
    s_cur = i;
    g_flashW = s_set[i].wall;
    bios_cpufastset(s_set[i].flatC, g_flatTbl, sizeof s_set[i].flatC / 4);
    bios_cpufastset(s_set[i].flatF, g_flatTblF, sizeof s_set[i].flatF / 4);
}

static int flash_find(int step) {
    for (int i = 0; i < FLASH_SETS; i++) if (s_step[i] == step) return i;
    return -1;
}

// the set to give up: an empty one, else the one unused for longest (never
// the one in use)
static int flash_victim(void) {
    int best = -1, age = -1;
    for (int i = 0; i < FLASH_SETS; i++) {
        if (i == s_cur) continue;
        if (s_step[i] < 0) return i;
        int a = (u8)(s_clock - s_used[i]);
        if (a > age) { age = a; best = i; }
    }
    return best;
}

void render_flash_warm(int power) {
    int step = (power + 8) >> 4;
    if (flash_find(step) >= 0) return;
    int i = flash_victim();
    if (i == s_making) s_making = -1;
    for (int c = 0; c < NCONE; c++) flash_cone(&s_set[i], c, step << 4, 0);
    s_step[i] = step;
    s_used[i] = ++s_clock;
}

void render_build_flash_tables(void) {
    s32 p = g_flashOn ? g_flashPower : 0;
    s32 floor = g_ambientBoost > g_minLight ? g_ambientBoost : g_minLight;
    if (p < 0) p = 0;
    if (p > 256) p = 256;
    if (floor > 0) {
        if (p != s_floorPower || floor != s_floorLevel || s_cur != FLASH_SETS) {
            if (p != s_floorPower || floor != s_floorLevel)
                for (int c = 0; c < NCONE; c++) flash_cone(&s_set[FLASH_SETS], c, p, floor);
            s_floorPower = p; s_floorLevel = floor;
            s_cur = -1;
            flash_use(FLASH_SETS);
        }
        return;
    }
    int step = (p + 8) >> 4;
    int i = flash_find(step);
    if (i < 0) {
        int any = 0;
        for (int k = 0; k < FLASH_SETS; k++) any |= s_step[k] >= 0;
        if (!any) {
            render_flash_warm(p);                  // nothing to stand in: at once
            i = flash_find(step);
        } else {
            // one cone class a frame, into the set that can best be spared
            if (s_making < 0 || s_makeStep != step) { s_making = flash_victim(); s_makeStep = step; s_makeCone = 0; s_step[s_making] = -1; }
            flash_cone(&s_set[s_making], s_makeCone, step << 4, 0);
            if (++s_makeCone == NCONE) { i = s_making; s_step[i] = step; s_making = -1; }
        }
    }
    if (i < 0) {
        // not ready: the set nearest in power stands in
        int best = -1, gap = 99;
        for (int k = 0; k < FLASH_SETS; k++) {
            if (s_step[k] < 0) continue;
            int g = s_step[k] > step ? s_step[k] - step : step - s_step[k];
            if (g < gap) { gap = g; best = k; }
        }
        i = best;
    }
    flash_use(i);
}

void render_init(void) {
    render_column_tables();
    for (int j = 0; j < NPAIR_F; j++) s_rowDist[j] = (FOCAL * 256 + j) / (2 * j + 1);
    s_cur = -1;
    render_build_flash_tables();
}

void camera_update(Camera *c) {
    c->dirX = lu_cos4(c->angle);
    c->dirY = lu_sin4(c->angle);
    c->planeX = -(c->dirY * PLANE_Q14) >> 14;
    c->planeY = (c->dirX * PLANE_Q14) >> 14;
}
