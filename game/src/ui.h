#ifndef UI_H
#define UI_H
#include "gba.h"

enum { TITLE_NEW = 0, TITLE_CONTINUE };
enum { PAUSE_RESUME = 0, PAUSE_QUIT };

int  ui_title(void);
void ui_intro(void);
void ui_chapter(int strId, int numStr);
void ui_controls(void);
int  ui_pause(void);
void ui_note(int id);
void ui_death(void);
void ui_jumpscare(void);
void ui_ending(int allNotes);
void ui_options(int fromGame);
void ui_fade_out(int speed);
void ui_fade_in(int speed);
u16  ui_keys_pressed(void);
void ui_text_screen(const char *text, int typewriter);
void ui_map(void);                  // the floor plan (map.c)
void map_track(void);               // mark the player's room as seen

#endif
