// SPDX-License-Identifier: MIT
#include <string.h>
// Canvas, text and palette helpers
#include "gfx.h"
#include "engine.h"
#include "assets.h"
#include "fx.h"

EWRAM_BSS u8 g_canvas[240 * 160] ALIGN4;
u8 g_brightness = 1;

static const u8 s_gamma[3][32] = {
    // 0: dark (gamma 0.92), 1: normal (0.78: lifts the shadows so shapes read), 2: bright (0.64)
    {0,1,2,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,24,25,26,27,28,29,30,31},
    {0,2,4,5,6,7,9,10,11,12,13,14,15,16,17,18,19,19,20,21,22,23,24,25,25,26,27,28,29,29,30,31},
    {0,3,5,7,8,10,11,12,13,14,15,16,17,18,19,19,20,21,22,23,23,24,25,26,26,27,28,28,29,30,30,31},
};

u16 pal_bright(u16 c) {
    const u8 *g = s_gamma[g_brightness > 2 ? 2 : g_brightness];
    return g[c & 31] | (g[(c >> 5) & 31] << 5) | (g[(c >> 10) & 31] << 10);
}

void pal_bg(const u16 *pal, int count) {
    for (int i = 0; i < count; i++) MEM_PAL[i] = pal_bright(pal[i]);
}

void pal_bg_game(void) { pal_bg(pal_game, 256); }

void pal_obj(const u16 *pal, int start, int count) {
    for (int i = 0; i < count; i++) MEM_PAL_OBJ[start + i] = pal_bright(pal[i]);
}

// ------------------------------------------------------------- frames
u16 *backbuf(void)  { return g_dispPage ? (u16 *)0x06000000 : (u16 *)0x0600A000; }
u16 *frontbuf(void) { return g_dispPage ? (u16 *)0x0600A000 : (u16 *)0x06000000; }
u8 *backbuf3d(void)  { return (u8 *)backbuf(); }
u8 g_vram3d;
void vram_leave_3d(void) { g_vram3d = 0; }

void vsync(void) {
    u32 v = g_vblanks;
    while (g_vblanks == v) bios_halt();
}

void flip_and_wait(void) {
    g_flipReq = 1;
    while (g_flipReq) bios_halt();
}

// ------------------------------------------------------------- canvas
void canvas_clear(u8 c) {
    u32 v = c * 0x01010101u;
    bios_cpufastset(&v, g_canvas, (240 * 160 / 4) | (1 << 24));
}

void canvas_rect(int x, int y, int w, int h, u8 c) {
    if (x < 0) { w += x; x = 0; }
    if (y < 0) { h += y; y = 0; }
    if (x + w > 240) w = 240 - x;
    if (y + h > 160) h = 160 - y;
    for (int j = 0; j < h; j++) {
        u8 *p = &g_canvas[(y + j) * 240 + x];
        for (int i = 0; i < w; i++) p[i] = c;
    }
}

void canvas_frame(int x, int y, int w, int h, u8 c) {
    canvas_rect(x, y, w, 1, c); canvas_rect(x, y + h - 1, w, 1, c);
    canvas_rect(x, y, 1, h, c); canvas_rect(x + w - 1, y, 1, h, c);
}

void canvas_from_screen(int darkLevel) {
    const u8 *cm = g_colormapSrc + (darkLevel << 8);
    const u16 *src = frontbuf();
    bios_cpufastset(src, g_canvas, 240 * 160 / 4);
    u32 *p = (u32 *)g_canvas;
    // only the view between the cinema bars is a picture; the rest of the
    // page is scratch
    memset(g_canvas, 0, VIS0 * 240);
    memset(g_canvas + VIS1 * 240, 0, (160 - VIS1) * 240);
    for (int i = 0; i < 240 * 160 / 4; i++) {
        u32 v = p[i];
        p[i] = cm[v & 255] | (cm[(v >> 8) & 255] << 8) | (cm[(v >> 16) & 255] << 16) | (cm[v >> 24] << 24);
    }
}

void canvas_paper(int x, int y, int w, int h) {
    // aged paper with darker edges and sparse specks (deterministic)
    u32 r = 0x9E3779B9u;
    for (int j = 0; j < h; j++) {
        u8 *p = &g_canvas[(y + j) * 240 + x];
        for (int i = 0; i < w; i++) {
            r ^= r << 13; r ^= r >> 17; r ^= r << 5;
            p[i] = (r & 63) ? C_PAPER : C_PAPERD;
        }
        p[0] = p[1] = p[w - 2] = p[w - 1] = C_PAPERD;
    }
    canvas_rect(x, y, w, 2, C_PAPERD);
    canvas_rect(x, y + h - 2, w, 2, C_PAPERD);
    canvas_frame(x, y, w, h, C_INK);
}

void canvas_present(void) {
    vram_leave_3d();
    u16 *dst = backbuf();
    bios_cpufastset(g_canvas, dst, 240 * 160 / 4);
    fx_prepare();
    flip_and_wait();
}

void canvas_blit_lz(const u8 *lz) { bios_lz77_wram(lz, g_canvas); }

// --------------------------------------------------------------- text
int text_width(const char *s) {
    int w = 0, best = 0;
    for (; *s; s++) {
        if (*s == '\n') { if (w > best) best = w; w = 0; continue; }
        w += font_width[(u8)*s & 127] + 1;
    }
    if (w > best) best = w;
    return best ? best - 1 : 0;
}

static inline void glyph(int x, int y, u8 ch, u8 color) {
    const u8 *rows = &font_rows[(ch & 127) * FONT_H];
    int w = font_width[ch & 127];
    for (int r = 0; r < FONT_H; r++) {
        int yy = y + r;
        if ((unsigned)yy >= 160) continue;
        u32 bits = rows[r];
        u8 *p = &g_canvas[yy * 240];
        for (int i = 0; i < w; i++)
            if ((bits >> i) & 1) { int xx = x + i; if ((unsigned)xx < 240) p[xx] = color; }
    }
}

int text_draw(int x, int y, const char *s, u8 color, u8 shadow) {
    int x0 = x;
    for (; *s; s++) {
        u8 ch = *s;
        if (ch == '\n') { x = x0; y += 11; continue; }
        if (shadow) glyph(x + 1, y + 1, ch, shadow);
        glyph(x, y, ch, color);
        x += font_width[ch & 127] + 1;
    }
    return x;
}

int text_draw_center(int y, const char *s, u8 color, u8 shadow) {
    return text_draw(120 - text_width(s) / 2, y, s, color, shadow);
}

// word-wrapped text; returns number of lines drawn/needed
static int wrap_impl(int x, int y, int w, int lineh, const char *s, u8 color, u8 shadow, int maxLines, int skip, int draw) {
    int line = 0;
    const char *p = s;
    char buf[64];
    while (*p) {
        // build one line
        int lw = 0, n = 0, lastSpace = -1, lastSpaceW = 0;
        const char *q = p;
        while (*q && *q != '\n') {
            int cw = font_width[(u8)*q & 127] + 1;
            if (lw + cw - 1 > w && n > 0) break;
            if (*q == ' ') { lastSpace = n; lastSpaceW = lw; }
            if (n < 63) buf[n++] = *q;
            lw += cw;
            q++;
        }
        if (*q && *q != '\n' && lastSpace > 0) {
            n = lastSpace;
            q = p + lastSpace + 1;
            (void)lastSpaceW;
        } else if (*q == '\n') {
            q++;
        }
        buf[n] = 0;
        if (draw && line >= skip && line - skip < maxLines)
            text_draw(x, y + (line - skip) * lineh, buf, color, shadow);
        line++;
        p = q;
    }
    return line;
}

int text_wrap(int x, int y, int w, int lineh, const char *s, u8 color, u8 shadow, int maxLines, int skipLines) {
    return wrap_impl(x, y, w, lineh, s, color, shadow, maxLines, skipLines, 1);
}

int text_count_lines(int w, const char *s) { return wrap_impl(0, 0, w, 0, s, 0, 0, 0, 0, 0); }

// centred block of explicit lines (split on '\n'), clipped to the screen
void text_lines_center(int y, int lineh, const char *s, u8 color) {
    char buf[64];
    while (*s) {
        int n = 0;
        while (*s && *s != '\n' && n < 63) buf[n++] = *s++;
        buf[n] = 0;
        if (*s == '\n') s++;
        if (y > -12 && y < 160) text_draw_center(y, buf, color, 0);
        y += lineh;
    }
}

int text_draw_big(int x, int y, const char *s, u8 color, u8 shadow, int scale) {
    for (; *s; s++) {
        u8 ch = *s & 127;
        const u8 *rows = &font_rows[ch * FONT_H];
        int w = font_width[ch];
        for (int r = 0; r < FONT_H; r++)
            for (int i = 0; i < w; i++)
                if ((rows[r] >> i) & 1) {
                    if (shadow) canvas_rect(x + i * scale + 1, y + r * scale + 1, scale, scale, shadow);
                    canvas_rect(x + i * scale, y + r * scale, scale, scale, color);
                }
        x += (w + 1) * scale;
    }
    return x;
}
