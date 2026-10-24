// 2D graphics: canvas (Mode 4 8bpp), text, palettes, display effects
#ifndef GFX_H
#define GFX_H
#include "gba.h"

// UI palette entries (fullbright in the game palette)
#define C_WHITE  248
#define C_LGREY  249
#define C_GREY   250
#define C_DGREY  251
#define C_RED    252
#define C_PAPER  253
#define C_PAPERD 254
#define C_INK    255

extern u8 g_canvas[240 * 160];
extern u8 g_brightness;           // 0..2 option

// display pages (mode 4), flipped in the VBlank interrupt
extern volatile u8 g_dispPage;    // page on screen
extern volatile u8 g_bgHide;      // background hidden until the next flip
extern u8 g_vram3d;
u8 *backbuf3d(void);
void vram_leave_3d(void);

// canvas
void canvas_clear(u8 c);
void canvas_rect(int x, int y, int w, int h, u8 c);
void canvas_frame(int x, int y, int w, int h, u8 c);
void canvas_from_screen(int darkLevel);   // grab displayed page, darken via colormap
void canvas_paper(int x, int y, int w, int h);
void canvas_present(void);                // copy to back page and flip (waits)
void canvas_blit_lz(const u8 *lz);       // decompress full-screen image into canvas

// text
int  text_width(const char *s);
int  text_draw(int x, int y, const char *s, u8 color, u8 shadow);
int  text_draw_center(int y, const char *s, u8 color, u8 shadow);
int  text_wrap(int x, int y, int w, int lineh, const char *s, u8 color, u8 shadow, int maxLines, int skipLines);
int  text_count_lines(int w, const char *s);
void text_lines_center(int y, int lineh, const char *s, u8 color);
int  text_draw_big(int x, int y, const char *s, u8 color, u8 shadow, int scale);

// palettes
void pal_bg(const u16 *pal, int count);   // with brightness curve
void pal_bg_game(void);
void pal_obj(const u16 *pal, int start, int count);
u16  pal_bright(u16 c);

// frame sync
extern volatile u32 g_vblanks;
extern volatile u8 g_flipReq;
void vsync(void);
void flip_and_wait(void);
u16 *backbuf(void);
u16 *frontbuf(void);

#endif
