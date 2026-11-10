// SPDX-License-Identifier: MIT
// fx table builder (per frame, ROM)
#include "fx.h"
#include "engine.h"
#include "fxint.h"

// sqrt(1 - t^2) * 256 for t = i/64
static const u8 s_circ[65] = {
    255,255,255,255,254,254,253,252,251,250,249,247,246,244,242,240,
    238,236,233,231,228,225,222,219,215,212,208,204,200,195,191,186,
    181,175,170,164,157,151,144,137,129,121,112,103, 93, 82, 70, 56,
     40,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 0 };


void fx_prepare(void) {
    int n = s_cur ^ 1;
    int d3 = g_fx.mode3d;
    // affine matrix in view space: rotation + zoom about the screen centre.
    // A screen pixel (sx, sy) shows view pixel (rx0 + pa sx + pb sy, ry0 + pc sx + pd sy).
    s32 z = g_fx.zoom > 16 ? g_fx.zoom : 16;
    // The 3D view has a few spare rows above and below the visible ones
    // (ROW0..VIS0, VIS1..ROW1) and the renderer's tables right beyond them:
    // no roll, zoom, shake or bob may bring those onto the screen.
    u16 roll = g_fx.roll;
    if (d3) {
        s16 r = (s16)roll;
        if (r > 330) r = 330; else if (r < -330) r = -330;      // 3.8 rows at the screen's edges
        roll = (u16)r;
        if (z < 256) z = 256;
    }
    s32 c = lu_cos(roll), s = lu_sin(roll);      // Q14
    s32 pa = (c * 256 / z) >> 6, pb = (s * 256 / z) >> 6;   // 8.8
    s32 pc = -pb, pd = pa;
    s32 ox = (120 << 8) + g_fx.offX, oy = (80 << 8) + g_fx.offY + g_fx.bobY;
    s32 rx0 = ox - pa * 120 - pb * 80;
    s32 ry0 = oy - pc * 120 - pd * 80;
    if (d3) {
        // the view rows at the four corners of what is shown; the wave moves
        // a line sideways by up to a few pixels, which a roll turns into a
        // fraction of a row: half a row of margin covers it
        s32 lo = ry0 + pd * VIS0, hi = ry0 + pd * (VIS1 - 1);
        s32 tilt = pc * 239;
        if (tilt < 0) lo += tilt; else hi += tilt;
        s32 top = (ROW0 << 8) + 128, bottom = (ROW1 << 8) - 129;
        if (hi > bottom) { ry0 -= hi - bottom; lo -= hi - bottom; }
        if (lo < top) ry0 += top - lo;
    }
    s_m[n][0] = pa; s_m[n][1] = pb; s_m[n][2] = pc; s_m[n][3] = pd;
    s_refX[n] = rx0; s_refY[n] = ry0;
    s32 amp = g_fx.wave;
    u16 ph = g_fx.wavePhase;
    s_hdma[n] = amp != 0;
    if (amp) {
        u32 *t = s_line[n];
        for (int y = 0; y < FX_LINES; y++) {
            s32 w = (lu_sin((u16)(ph + y * 900)) * amp) >> 10;                 // 1/256 px
            w += (lu_sin((u16)(ph * 3 + y * 2300)) * amp) >> 12;
            t[0] = rx0 + pb * y + ((w * pa) >> 8);
            t[1] = ry0 + pd * y + ((w * pc) >> 8);
            t += 2;
        }
    }
    // vignette window per line (ellipse), letterbox
    u16 *win = s_win[n];
    int lb = (g_fx.letterbox && d3) || g_fx.bars;      // menus and notes use the whole screen
    static u32 s_winKey[2] = { 0xFFFFFFFF, 0xFFFFFFFF };
    u32 wk = (u32)g_fx.vignette | ((u32)lb << 16) | ((u32)g_fx.slits << 24);
    if (wk == s_winKey[n]) { /* unchanged */ }
    else if ((s_winKey[n] = wk), g_fx.slits) {
        for (int y = 0; y < 160; y++) {
            int band = (y - 52) % 15;
            win[y] = (y >= 52 && y < 112 && band >= 3 && band < 12) ? 240 : 0;
        }
    } else if (g_fx.vignette > 0) {
        s32 rx = 70 + (g_fx.vignette * 110 >> 8);   // half width at centre
        s32 ry = 50 + (g_fx.vignette * 70 >> 8);
        s32 inv = (64 << 16) / ry;
        for (int y = 0; y < 160; y++) {
            if (lb && (y < VIS0 || y >= VIS1)) { win[y] = 0; continue; }
            s32 dy = y - 80; if (dy < 0) dy = -dy;
            s32 t = (dy * inv) >> 16;
            s32 hw = t >= 64 ? 0 : (rx * s_circ[t]) >> 8;
            s32 x1 = 120 - hw, x2 = 120 + hw;
            if (x1 < 0) x1 = 0;
            if (x2 > 240) x2 = 240;
            win[y] = hw ? (u16)((x1 << 8) | x2) : 0;
        }
    } else {
        for (int y = 0; y < 160; y++) win[y] = (lb && (y < VIS0 || y >= VIS1)) ? 0 : 240;
    }
    s_fxVig[n] = g_fx.vignette > 0;
    s_fxDark[n] = g_fx.vigDark;
    s_fxFade[n] = g_fx.fade;
    s_fxWhite[n] = g_fx.white;
    s_fxMosaic[n] = g_fx.mosaic;
    s_fx3d[n] = d3;
    s_fxSlits[n] = g_fx.slits;
    s_fxLb[n] = lb;
    s_ready = 1;
}
