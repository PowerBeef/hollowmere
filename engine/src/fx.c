// Hardware display effects
#include "fx.h"
#include "engine.h"
#include "gfx.h"

FxState g_fx;

#include "fxint.h"
EWRAM_BSS u32 s_line[2][FX_LINES * 2];
EWRAM_BSS u16 s_win[2][160];
u8 s_cur;                   // table set currently displayed
u8 s_ready;                 // next set prepared
s16 s_m[2][4];
s32 s_refX[2], s_refY[2];
u8 s_hdma[2];
u8 s_fxVig[2], s_fxDark[2], s_fxFade[2], s_fxWhite[2], s_fxMosaic[2], s_fx3d[2], s_fxSlits[2], s_fxLb[2];

void fx_reset(void) {
    g_fx.bobY = 0; g_fx.offX = 0; g_fx.offY = 0; g_fx.roll = 0; g_fx.zoom = 256;
    g_fx.wave = 0; g_fx.vignette = 0; g_fx.vigDark = 0; g_fx.fade = 0; g_fx.white = 0;
    g_fx.mosaic = 0; g_fx.letterbox = 0;
}

void fx_init(void) {
    fx_reset();
    g_fx.mode3d = 0;
    s_cur = 0; s_ready = 0;
    for (int i = 0; i < 2; i++) { s_m[i][0] = 256; s_m[i][3] = 256; s_m[i][1] = 0; s_m[i][2] = 0; }
}

void fx_vblank(int flipped) {
    if (s_ready && (flipped || !s_fx3d[s_cur ^ 1])) { s_cur ^= 1; s_ready = 0; }
    int c = s_cur;
    int d3 = s_fx3d[c];
    REG_DMA0CNT = 0;
    REG_DMA3CNT = 0;
    REG_BG2PA = s_m[c][0]; REG_BG2PB = s_m[c][1]; REG_BG2PC = s_m[c][2]; REG_BG2PD = s_m[c][3];
    REG_BG2X = s_refX[c]; REG_BG2Y = s_refY[c];
    if (s_hdma[c]) {
        // per-line reference points (wave distortion)
        REG_DMA3SAD = (u32)&s_line[c][2];
        REG_DMA3DAD = (u32)&REG_BG2X;
        REG_DMA3CNT = 2 | DMA_32 | DMA_AT_HBLANK | DMA_REPEAT | DMA_DST_RELOAD | DMA_ENABLE;
    }
    REG_WIN0H = s_win[c][0];
    REG_WIN0V = 160;          // y1 = 0, y2 = 160
    REG_DMA0SAD = (u32)&s_win[c][1];
    REG_DMA0DAD = (u32)&REG_WIN0H;
    REG_DMA0CNT = 1 | DMA_16 | DMA_AT_HBLANK | DMA_REPEAT | DMA_DST_RELOAD | DMA_ENABLE;

    (void)d3;
    u16 bgm = 0x04;                               // BG2 bit in window and blend masks
    u16 dc = DCNT_MODE4 | (g_dispPage ? DCNT_PAGE : 0) | DCNT_OBJ | DCNT_OBJ_1D;
    if (!g_bgHide) dc |= DCNT_BG2;
    int fade = s_fxFade[c], white = s_fxWhite[c];
    if (white) {
        REG_BLDCNT = 0x3F | (2 << 6);           // brighten all layers + backdrop
        REG_BLDY = white;
        dc |= DCNT_WIN0;
        REG_WININ = 0x3F; REG_WINOUT = 0x10;    // keep letterbox: outside = OBJ only
    } else if (fade) {
        REG_BLDCNT = 0x3F | (3 << 6);           // darken all
        REG_BLDY = fade;
        dc |= DCNT_WIN0;
        REG_WININ = 0x3F; REG_WINOUT = 0x10;
    } else if (s_fxSlits[c]) {
        REG_BLDCNT = 0;
        REG_WININ = 0x10 | bgm;
        REG_WINOUT = 0x10;
        dc |= DCNT_WIN0;
    } else if (s_fxVig[c]) {
        // inside window 0: BG + OBJ, no effects; outside: BG + OBJ + darken
        REG_BLDCNT = bgm | 0x20 | (3 << 6) | (bgm << 8);   // target1 BG + backdrop, darken, target2 BG (for OBJ alpha)
        REG_BLDY = s_fxDark[c];
        // win0 (the ellipse): BG + OBJ; win1 (the view between the cinema
        // bars): BG + OBJ + darkening; outside both (the bars): OBJ only
        REG_WININ = (0x10 | bgm) | ((0x30 | bgm) << 8);
        REG_WINOUT = 0x10;
        REG_WIN1H = 240;
        REG_WIN1V = s_fxLb[c] ? ((VIS0 << 8) | VIS1) : 160;
        dc |= DCNT_WIN0 | DCNT_WIN1;
    } else {
        REG_BLDCNT = (bgm << 8);                // only OBJ alpha against the BG
        REG_BLDY = 0;
        REG_WININ = 0x3F; REG_WINOUT = 0x10;
        dc |= DCNT_WIN0;
    }
    REG_DISPCNT = dc;
    int m = s_fxMosaic[c];
    REG_MOSAIC = m | (m << 4);
    REG_BG2CNT = m ? 0x0040 : 0;
}
