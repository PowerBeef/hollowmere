// internal fx tables shared between fx.c and fxprep.c
#ifndef FXINT_H
#define FXINT_H
#include "gba.h"
// One table set per presented frame (double buffered, switched at the flip).
// With the wave effect on, a per-line table feeds BG2's reference point by
// HDMA (2 words per line: BG2X, BG2Y).
#define FX_LINES 161
extern u32 s_line[2][FX_LINES * 2];
extern s16 s_m[2][4];
extern s32 s_refX[2], s_refY[2];
extern u8 s_cur, s_ready;
extern u8 s_hdma[2];
extern u16 s_win[2][160];
extern u8 s_fxVig[2], s_fxDark[2], s_fxFade[2], s_fxWhite[2], s_fxMosaic[2], s_fx3d[2], s_fxSlits[2], s_fxLb[2];
#endif
