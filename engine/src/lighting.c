// SPDX-License-Identifier: MIT
// Render tables and flashlight light tables (ROM, thumb)
#include "engine.h"
#include "assets.h"
#include "gfx.h"
#include "fx.h"

extern s16 g_camX[VIEW_W];
extern u16 g_rowDist2[NPAIR_F];
extern u8  g_coneOf[VIEW_W];
extern u8  g_flashW[NCONE][256];
extern u32 g_flatTbl[NCONE][NPAIR_C + 1];
extern u32 g_flatTblF[NCONE][NPAIR_F - NPAIR_C + 1];

u8  g_flashOn = 1;
s16 g_flashPower = 256;
s16 g_ambientBoost = 0;
s16 g_minLight = 0;

static s16 s_lastPower = -1, s_lastBoost = -1, s_lastOn = -1, s_lastMin = -1;

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

void render_init(void) {
    render_column_tables();
    s_lastPower = -1;
    render_build_flash_tables();
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

void render_build_flash_tables(void) {
    s32 p = g_flashOn ? g_flashPower : 0;
    if (p == s_lastPower && g_ambientBoost == s_lastBoost && g_flashOn == s_lastOn && g_minLight == s_lastMin) return;
    s_lastPower = p; s_lastBoost = g_ambientBoost; s_lastOn = g_flashOn; s_lastMin = g_minLight;
    s32 floor = g_ambientBoost > g_minLight ? g_ambientBoost : g_minLight;
    for (int c = 0; c < NCONE; c++) {
        const u8 *bw = beam_wall + c * 256;
        u8 *dw = g_flashW[c];
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
            u32 w = ((u32)g_rowDist2[j] << 16) | (lc << 8) | lf;
            if (j < NPAIR_C) g_flatTbl[c][j] = w;
            else g_flatTblF[c][j - NPAIR_C] = w;
        }
        g_flatTbl[c][NPAIR_C] = 0;
        g_flatTblF[c][NPAIR_F - NPAIR_C] = 0;
    }
}

void camera_update(Camera *c) {
    c->dirX = lu_cos4(c->angle);
    c->dirY = lu_sin4(c->angle);
    c->planeX = -(c->dirY * PLANE_Q14) >> 14;
    c->planeY = (c->dirX * PLANE_Q14) >> 14;
}
