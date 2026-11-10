// SPDX-License-Identifier: MIT
// Hardware display effects: affine BG2 (bob/shake/roll/zoom), HDMA wave
// distortion, window vignette, fades, mosaic.
#ifndef FX_H
#define FX_H
#include "gba.h"

typedef struct {
    s16 bobY;        // vertical offset, 1/256 px
    s16 offX;        // horizontal offset, 1/256 px (shake)
    s16 offY;
    u16 roll;        // rotation angle (0..65535)
    s16 zoom;        // 256 = 1.0 (>256 zooms in)
    s16 wave;        // wave amplitude in 1/16 px
    u16 wavePhase;
    s16 vignette;    // 0 = off, 1..256 ellipse size (256 = widest)
    u8  vigDark;     // 0..16 darkening outside the ellipse
    u8  fade;        // 0..16 fade to black
    u8  white;       // 0..16 fade to white (overrides fade)
    u8  mosaic;      // 0..15
    u8  letterbox;   // rows hidden at top/bottom
    u8  mode3d;      // 1 = gameplay view (HDMA active)
    u8  slits;       // hiding-in-locker view
} FxState;

extern FxState g_fx;

void fx_init(void);
void fx_reset(void);
void fx_prepare(void);   // build tables for the next presented frame (main loop)
void fx_vblank(int flipped); // in VBlank IRQ

#endif
