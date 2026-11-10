// SPDX-License-Identifier: MIT
#ifndef HUD_H
#define HUD_H
#include "gba.h"

enum { HL_TOP = 0, HL_SUB1, HL_SUB2, HL_PROMPT, HL_COUNT };
enum { HC_WHITE = 1, HC_GREY = 3, HC_RED = 4, HC_GOLD = 5 };

extern OBJ_ATTR g_oam[128];
// OBJ tiles 784..799 are free for a game's own sprites (the HUD ends at 783,
// the 3D view keeps tables from tile 800 up)
#define OBJ_TILE_FREE 784

void hud_init(void);
void hud_text(int line, const char *s, int frames, int color);
void hud_message(const char *s, int frames);    // subtitle (auto wraps to 2 lines)
void hud_clear(int line);
void hud_update(void);
extern u8 g_hudDrew;                            // set when a line's pixels were drawn (about 90,000 cycles, once)
void hud_battery(int permille, int frames);
void hud_set_visible(int on);
int  hud_visible(void);
void hud_oam_commit(void);                      // VBlank
void hud_icon(int slot, int kind, int count, int frames);

#endif
