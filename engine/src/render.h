// SPDX-License-Identifier: MIT
// Renderer internals shared by render.iwram.c and objects.iwram.c
#ifndef RENDER_H
#define RENDER_H
#include "engine.h"

// column fillers (rasm.s). The page is 240 bytes per row; p is a byte address.
extern void flat_column(u8 *pf, u8 *pc, const u32 *tbl, const FlatCtx *ctx, s32 rdx, s32 rdy);
extern void flat_floor(u8 *pf, const u32 *tbl, const FlatCtx *ctx, s32 rdx, s32 rdy);
// one sample per 4x2 pixels (far floor; pf, pc 4-byte aligned)
extern void flat_column2(u8 *pf, u8 *pc, const u32 *tbl, const FlatCtx *ctx, s32 rdx, s32 rdy);
extern void flat_floor2(u8 *pf, const u32 *tbl, const FlatCtx *ctx, s32 rdx, s32 rdy);
// detail knobs (set by the frame governor, main.c)
extern s32 g_floorSplit;      // floor/ceiling row pairs nearer the eye line than this: one sample per 4x2
extern s32 g_wallHalfLh;      // walls shorter than this (far): one sample per column pair
extern s32 g_fullC0, g_fullC1; // full-resolution band of columns; outside it one sample per pair
// both columns of a pair the same (p even): the halfword is the pixel twice
extern void wall_column(u8 *p, const u8 *texcol, const u8 *cmap, u32 tp, u32 step, int n);
extern void wall_column2(u8 *p, const u8 *texcol, const u8 *cmap, u32 tp, u32 step, int n);
// two columns with their own rows and texture coordinates (see rasm.s)
// (each A field is followed by its B field)
// pmode 1: the rows both columns cover read their two texels with one 16-bit
// read at ptex + 2 * (tpA >> 16) (A low byte, B high byte; A's rows and
// texture position stand for both); pmode 2: the same with A in the high byte
typedef struct {
    u8 *p; s32 a0, b0, a1, b1;
    const u8 *texA, *texB, *cmA, *cmB;
    u32 tpA, tpB, stA, stB;
    const u8 *ptex; u32 pmode;
} ColPair;
// wall texture blob (build_assets.py): 64x128 and mips 32x64, 16x32, 8x16,
// column-major, then each level as column pairs (P0: 2k|2k+1, P1: 2k+1|2k+2)
#define WT_CM0 0
#define WT_CM1 8192
#define WT_CM2 10240
#define WT_CM3 10752
extern void col_pair(ColPair *s);
typedef struct {
    u8 *p; s32 a0, b0, a1, b1;
    const u8 *tex, *cmA, *cmB;
    u32 uvA, uvB, duvA, duvB;
} ColPairUV;
extern void col_pair_uv(ColPairUV *s);
extern void col_uv2(u8 *p, int n, const u8 *tex, const u8 *cm, u32 uv, u32 duv);
// one column, merged into its pair
extern void col_one(u8 *p, int n, const u8 *tex, const u8 *cm, u32 tp, u32 step);

extern s16 g_camX[VIEW_W];
extern u8  g_coneOf[VIEW_W];
extern u8  g_flashW[NCONE][256];
extern s32 g_clipDepth[VIEW_W];
extern s16 g_clipTop[VIEW_W];

void draw_objects(u8 *fb);
void occluders_prepass(void);

struct PropInst_;
IWRAM_CODE void draw_sprite(u8 *fb, RSprite *s);

// 1/x for x in 16.16 (x >= 1/256): returns 16.16
extern const u32 rcp_tab[4096];
static inline u32 rcp16(u32 x) {
    if (x < 0x10000) return rcp_tab[x >> 4] << 4;
    if (x < 0x100000) return rcp_tab[x >> 8];
    if (x < 0x1000000) return rcp_tab[x >> 12] >> 4;
    return rcp_tab[x >> 16] >> 8;
}

#endif
