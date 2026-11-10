// SPDX-License-Identifier: MIT
// HUD drawn with hardware sprites (text rendered into 4bpp OBJ tiles)
#include "hud.h"
#include "gfx.h"
#include "assets.h"
#include <string.h>

EWRAM_BSS OBJ_ATTR g_oam[128] ALIGN4;

#define OBJ_TILES ((u32 *)0x06014000)       // tile 512
#define LINE_TILES 64
#define TILE_BATT (512 + HL_COUNT * LINE_TILES)
#define TILE_ICONS (TILE_BATT + 8)

// objective in the top bar (VIS0 rows), centred in it and clear of the
// screen's edge; subtitles in the bottom bar, prompts just above it
static const s16 s_lineY[HL_COUNT] = { 2, 134, 145, 118 };
EWRAM_BSS static u32 s_buf[LINE_TILES * 8];
static s16 s_timer[HL_COUNT];
static u8  s_width[HL_COUNT];
static u8  s_x0[HL_COUNT];
static u8  s_on[HL_COUNT];
#define HUD_LINE_MAX 127                   // characters a line remembers (it draws 236 px at most)
EWRAM_BSS static char s_last[HL_COUNT][HUD_LINE_MAX + 1];
static u8  s_lastColor[HL_COUNT];
static s16 s_battTimer;
static u8  s_visible = 1;
static s16 s_iconTimer[2];
static u8  s_iconKind[2];

static const u16 s_objpal[16] = {
    0, RGB15(29, 28, 26), RGB15(1, 1, 1), RGB15(17, 17, 16), RGB15(26, 5, 4), RGB15(30, 25, 12),
    RGB15(8, 8, 8), RGB15(20, 22, 20), RGB15(12, 26, 10), RGB15(28, 22, 6), RGB15(27, 8, 6),
    RGB15(24, 18, 9), RGB15(14, 10, 5), RGB15(22, 22, 24), RGB15(5, 5, 6), RGB15(31, 31, 31)
};

static inline void px(int x, int y, int c) {
    if ((unsigned)x >= 240 || (unsigned)y >= 16) return;
    int t = (x >> 5) * 8 + (y >> 3) * 4 + ((x & 31) >> 3);
    u32 *w = &s_buf[t * 8 + (y & 7)];
    int sh = (x & 7) * 4;
    *w = (*w & ~(15u << sh)) | ((u32)c << sh);
}

static int render_line(const char *s, int color) {
    memset(s_buf, 0, sizeof s_buf);
    int w = text_width(s);
    if (w > 236) w = 236;
    int x0 = 120 - w / 2;
    int x = x0;
    for (const char *p = s; *p; p++) {
        u8 ch = *p & 127;
        const u8 *rows = &font_rows[ch * FONT_H];
        int gw = font_width[ch];
        for (int r = 0; r < FONT_H; r++)
            for (int i = 0; i < gw; i++)
                if ((rows[r] >> i) & 1)
                    for (int dy = -1; dy <= 1; dy++)
                        for (int dx = -1; dx <= 1; dx++)
                            px(x + i + dx, r + 3 + dy, 2);
        for (int r = 0; r < FONT_H; r++)
            for (int i = 0; i < gw; i++)
                if ((rows[r] >> i) & 1) px(x + i, r + 3, color);
        x += gw + 1;
        if (x > 238) break;
    }
    return x0;
}

void hud_init(void) {
    memset(g_oam, 0, sizeof g_oam);
    for (int i = 0; i < 128; i++) g_oam[i].attr0 = ATTR0_HIDE;
    for (int l = 0; l < HL_COUNT; l++) { s_timer[l] = 0; s_on[l] = 0; s_last[l][0] = 0; }
    s_visible = 1;
    s_battTimer = 0;
    s_iconTimer[0] = s_iconTimer[1] = 0;
    pal_obj(s_objpal, 0, 16);
}

void hud_text(int line, const char *s, int frames, int color) {
    if (!s || !*s) { hud_clear(line); return; }
    if (s_on[line] && s_lastColor[line] == color && !strncmp(s_last[line], s, HUD_LINE_MAX)) {
        if (s_timer[line] < frames || frames == 0) s_timer[line] = frames;
        return;
    }
    strncpy(s_last[line], s, HUD_LINE_MAX); s_last[line][HUD_LINE_MAX] = 0;
    s_lastColor[line] = color;
    int x0 = render_line(s, color);
    bios_cpufastset(s_buf, OBJ_TILES + (line * LINE_TILES) * 8, LINE_TILES * 8);
    s_width[line] = (x0 >> 5);
    s_x0[line] = x0;
    s_timer[line] = frames;
    s_on[line] = 1;
}

// A subtitle: one line, or two split at the space nearest the middle when it
// is wider than 224 px, whatever its length (engine/tools/textcheck.py
// applies the same rule to every message at build time and fails on one
// whose halves do not fit).
void hud_message(const char *s, int frames) {
    EWRAM_BSS static char half[2][HUD_LINE_MAX + 1];
    int n = strlen(s);
    if (text_width(s) <= 224 || n < 3) {
        hud_text(HL_SUB1, s, frames, HC_WHITE);
        hud_clear(HL_SUB2);
        return;
    }
    int best = -1;
    for (int i = n / 2, j = n / 2; i > 0 || j < n; i--, j++) {
        if (j < n && s[j] == ' ') { best = j; break; }
        if (i > 0 && s[i] == ' ') { best = i; break; }
    }
    int skip = best >= 0;                    // the space itself is dropped
    if (best < 0) best = n / 2;
    int la = best < HUD_LINE_MAX ? best : HUD_LINE_MAX;
    memcpy(half[0], s, la); half[0][la] = 0;
    strncpy(half[1], s + best + skip, HUD_LINE_MAX); half[1][HUD_LINE_MAX] = 0;
    hud_text(HL_SUB1, half[0], frames, HC_WHITE);
    hud_text(HL_SUB2, half[1], frames, HC_WHITE);
}

void hud_clear(int line) { s_on[line] = 0; s_timer[line] = 0; s_last[line][0] = 0; }

void hud_set_visible(int on) { s_visible = on; }

void hud_battery(int permille, int frames) {
    // 32x16 icon: battery outline with 5 bars
    memset(s_buf, 0, 8 * 32);
    #define BPX(x, y, c) do { int t_ = ((y) >> 3) * 4 + ((x) >> 3); u32 *w_ = &s_buf[t_ * 8 + ((y) & 7)]; int sh_ = ((x) & 7) * 4; *w_ = (*w_ & ~(15u << sh_)) | ((u32)(c) << sh_); } while (0)
    for (int x = 2; x < 26; x++) { BPX(x, 4, 7); BPX(x, 12, 7); }
    for (int y = 4; y <= 12; y++) { BPX(2, y, 7); BPX(25, y, 7); }
    for (int y = 6; y <= 10; y++) { BPX(26, y, 7); BPX(27, y, 7); }
    int bars = (permille + 199) / 200;
    int col = permille > 400 ? 8 : (permille > 200 ? 9 : 10);
    for (int b = 0; b < bars && b < 5; b++)
        for (int x = 0; x < 3; x++)
            for (int y = 6; y <= 10; y++) BPX(4 + b * 4 + x, y, col);
    #undef BPX
    bios_cpufastset(s_buf, OBJ_TILES + (TILE_BATT - 512) * 8, 8 * 8);
    s_battTimer = frames;
}

void hud_icon(int slot, int kind, int count, int frames) {
    (void)count;
    s_iconKind[slot] = kind;
    s_iconTimer[slot] = frames;
}

void hud_update(void) {
    int o = 0;
    for (int l = 0; l < HL_COUNT; l++) {
        if (s_on[l] && s_timer[l] > 0 && --s_timer[l] == 0) s_on[l] = 0;
        if (!s_on[l] || !s_visible) continue;
        int first = s_width[l];
        for (int k = first; k < 8 - first; k++) {
            OBJ_ATTR *a = &g_oam[o++];
            a->attr0 = (s_lineY[l] & 255) | ATTR0_WIDE;
            a->attr1 = (k * 32) | ATTR1_SIZE_32;
            a->attr2 = (512 + l * LINE_TILES + k * 8) | ATTR2_PRIO(0) | ATTR2_PAL(0);
        }
    }
    if (s_battTimer > 0 && s_visible) {
        s_battTimer--;
        OBJ_ATTR *a = &g_oam[o++];
        // in the top bar level with the objective, or just inside the view
        // under it when a long objective would run into the icon
        int y = (s_on[HL_TOP] && 240 - s_x0[HL_TOP] > 203) ? 18 : 1;
        a->attr0 = y | ATTR0_WIDE;
        a->attr1 = 204 | ATTR1_SIZE_32;
        a->attr2 = TILE_BATT | ATTR2_PAL(0);
    }
    while (o < 128) g_oam[o++].attr0 = ATTR0_HIDE;
}

void hud_oam_commit(void) {
    bios_cpufastset(g_oam, (void *)0x07000000, 256);
}
