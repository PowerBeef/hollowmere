// SPDX-License-Identifier: MIT
// Menus, notes, title, intro, chapter cards, death and ending screens
#include "ui.h"
#include "gfx.h"
#include "fx.h"
#include "game.h"
#include "audio.h"
#include "assets.h"
#include "hud.h"
#include "world.h"
#include <string.h>

static u16 s_prev = 0xFFFF;
EWRAM_BSS u8 g_scene[240 * 160] ALIGN4;
u8 g_sceneValid;
static u16 s_held;
static int s_repeat;

extern volatile u16 g_keyPressAcc;

u16 ui_keys_pressed(void) {
    vsync();
    u16 k = ~REG_KEYINPUT & KEY_MASK;
    REG_IME = 0;
    u16 p = g_keyPressAcc;
    g_keyPressAcc = 0;
    REG_IME = 1;
    // auto-repeat for d-pad
    if (k & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
        if (k == s_held) { if (++s_repeat > 22 && (s_repeat & 3) == 0) p |= k & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT); }
        else { s_held = k; s_repeat = 0; }
    } else s_repeat = 0;
    s_prev = k;
    return p;
}

static void present2d(void) {
    g_fx.mode3d = 0;
    canvas_present();
}

void ui_fade_out(int speed) {
    g_fx.mode3d = 0;
    while (g_fx.fade < 16) {
        for (int i = 0; i < speed; i++) vsync();
        g_fx.fade++;
        fx_prepare();
    }
    vsync();            // the last step is on screen: the caller may change the palette
}

void ui_fade_in(int speed) {
    g_fx.mode3d = 0;
    while (g_fx.fade > 0) {
        for (int i = 0; i < speed; i++) vsync();
        g_fx.fade--;
        fx_prepare();
    }
}

static void wait_frames(int n) { while (n--) vsync(); }

// a plain 2D screen: none of the 3D view's movement or framing
void ui_plain_fx(void) {
    g_fx.mode3d = 0;
    g_fx.vignette = 0; g_fx.wave = 0; g_fx.bobY = 0; g_fx.offX = g_fx.offY = 0; g_fx.roll = 0; g_fx.zoom = 256;
    g_fx.slits = 0; g_fx.bars = 0;
}

// --------------------------------------------------------------- text
// draws a full-screen text page with optional typewriter reveal
void ui_text_screen(const char *text, int typewriter) {
    EWRAM_BSS static char buf[600];
    int n = strlen(text);
    if (n > 599) n = 599;
    int lines = text_count_lines(200, text);
    int y0 = 80 - lines * 6;
    if (y0 < 8) y0 = 8;
    if (!typewriter) {
        canvas_clear(0);
        text_wrap(20, y0, 200, 12, text, C_LGREY, 0, 13, 0);
        present2d();
        return;
    }
    int shown = 0;
    while (shown < n) {
        u16 p = ui_keys_pressed();
        if (p & (KEY_A | KEY_START)) shown = n;
        else if ((g_vblanks & 1) == 0) {
            shown++;
            if (text[shown - 1] != ' ' && text[shown - 1] != '\n' && (shown & 1)) snd_play(SND_UI_MOVE, 22, 0, 2000 + (rng_next() & 1023), 10);
            if (text[shown - 1] == '.' || text[shown - 1] == '\n') wait_frames(10);
        }
        memcpy(buf, text, shown); buf[shown] = 0;
        canvas_clear(0);
        text_wrap(20, y0, 200, 12, buf, C_LGREY, 0, 13, 0);
        present2d();
    }
    // wait for confirmation, blinking prompt
    for (int t = 0;; t++) {
        canvas_rect(222, 148, 14, 10, 0);
        if ((t >> 5) & 1) text_draw(226, 148, "\x01", C_GREY, 0);
        present2d();
        if (ui_keys_pressed() & (KEY_A | KEY_START)) break;
    }
    snd_play(SND_UI_SELECT, 90, 0, 0, 200);
}

// --------------------------------------------------------------- title
typedef struct { s16 x, y, vy; } Drop;

int ui_title(void) {
    fx_reset();
    g_fx.mode3d = 0;
    g_fx.fade = 16;
    hud_init();
    pal_bg(pal_title, 248);
    for (int i = 248; i < 256; i++) MEM_PAL[i] = pal_bright(pal_game[i]);
    music_play(mus_lullaby, MUS_LULLABY_LEN, SND_MUSICBOX, MUS_LULLABY_FRAMES, 200);
    int rainH = snd_play(SND_RAIN, 70, 0, 0, 100);
    int hasSave = save_exists();
    int sel = hasSave ? 1 : 0;
    const char *items[3] = { "NEW GAME", "CONTINUE", "OPTIONS" };
    // rain drops as sprites: one 8x8 streak tile
    u32 *tile = (u32 *)(0x06010000 + OBJ_TILE_FREE * 32);
    for (int r = 0; r < 8; r++) tile[r] = (r < 6) ? (0x7u << ((r & 1) * 4)) : 0;
    static const u16 rpal[16] = { 0, 0, 0, 0, 0, 0, 0, RGB15(10, 12, 15) };
    pal_obj(rpal, 16, 16);
    Drop drops[40];
    for (int i = 0; i < 40; i++) { drops[i].x = rng_next() % 240; drops[i].y = rng_next() % 160; drops[i].vy = 5 + rng_next() % 4; }
    int t = 0, flash = 0, nextBolt = 300;
    int result = -1;
    while (result < 0) {
        canvas_blit_lz(img_title);
        // flickering lit window in the asylum (palette entry animated below)
        int y = hasSave ? 108 : 114;
        for (int i = 0; i < 3; i++) {
            if (i == 1 && !hasSave) continue;      // no gap where CONTINUE would be
            int c = (i == sel) ? C_WHITE : C_GREY;
            int w = text_width(items[i]);
            text_draw(120 - w / 2, y, items[i], c, C_INK);
            if (i == sel) { text_draw(120 - w / 2 - 12, y, "-", C_RED, 0); text_draw(120 + w / 2 + 6, y, "-", C_RED, 0); }
            y += 13;
        }
        text_draw(240 - text_width("v1.0") - 4, 150, "v1.0", C_DGREY, 0);
        present2d();
        if (g_fx.fade > 0 && (t & 3) == 0) { g_fx.fade--; fx_prepare(); }
        // lightning
        if (--nextBolt <= 0) {
            flash = 14; nextBolt = 400 + rng_next() % 700;
            snd_play(SND_THUNDER, 140, 0, 0, 120);
        }
        if (flash > 0) { flash--; g_fx.white = flash > 8 ? 9 : (flash & 2) * 2; fx_prepare(); }
        else if (g_fx.white) { g_fx.white = 0; fx_prepare(); }
        // rain sprites
        for (int i = 0; i < 40; i++) {
            Drop *d = &drops[i];
            d->y += d->vy; d->x -= 1;
            if (d->y > 160) { d->y = -8; d->x = rng_next() % 260; }
            if (d->x < -8) d->x += 248;
            g_oam[i].attr0 = (d->y & 255) | ATTR0_SQUARE | ATTR0_BLEND;
            g_oam[i].attr1 = (d->x & 511) | ATTR1_SIZE_8;
            g_oam[i].attr2 = OBJ_TILE_FREE | ATTR2_PAL(1) | ATTR2_PRIO(0);
        }
        // the window light flickers (palette index 247 is its glow)
        MEM_PAL[247] = pal_bright(((t >> 3) % 23 == 0 || (t % 97) < 3) ? RGB15(8, 6, 2) : pal_title[247]);
        REG_BLDALPHA = 6 | (16 << 8);
        u16 p = ui_keys_pressed();
        t++;
        if (p & KEY_UP) { do { sel = (sel + 2) % 3; } while (sel == 1 && !hasSave); snd_play(SND_UI_MOVE, 80, 0, 0, 200); }
        if (p & KEY_DOWN) { do { sel = (sel + 1) % 3; } while (sel == 1 && !hasSave); snd_play(SND_UI_MOVE, 80, 0, 0, 200); }
        if (p & (KEY_A | KEY_START)) {
            snd_play(SND_UI_SELECT, 110, 0, 0, 200);
            if (sel == 2) {
                for (int i = 0; i < 40; i++) g_oam[i].attr0 = ATTR0_HIDE;       // no rain over the options box
                ui_options(0);
                pal_bg(pal_title, 248);
                continue;
            }
            result = sel == 0 ? TITLE_NEW : TITLE_CONTINUE;
        }
    }
    for (int i = 0; i < 40; i++) g_oam[i].attr0 = ATTR0_HIDE;
    g_fx.white = 0;
    ui_fade_out(2);
    music_stop();
    snd_fade(rainH, 3);
    return result;
}

// --------------------------------------------------------------- intro
void ui_intro(void) {
    fx_reset();
    g_fx.mode3d = 0;
    pal_bg_game();
    canvas_clear(0);
    present2d();
    g_fx.fade = 0; fx_prepare();
    snd_play(SND_AMB_WARD, 60, 0, 0, 100);
    for (int page = 0; page < NUM_INTRO_PAGES; page++) {
        ui_text_screen(game_str(STR_INTRO_0 + page), 1);
        ui_fade_out(1);
        canvas_clear(0); present2d();
        g_fx.fade = 0; fx_prepare();
    }
    snd_stop_all();
}

void ui_controls(void) {
    fx_reset();
    g_fx.mode3d = 0;
    g_fx.fade = 16;
    pal_bg_game();
    canvas_clear(0);
    text_draw_center(12, game_str(STR_CTRL_TITLE), C_RED, 0);
    canvas_rect(60, 25, 120, 1, C_DGREY);
    static const int rows[8][2] = {
        { STR_CTRL_K0, STR_CTRL_V0 }, { STR_CTRL_K1, STR_CTRL_V1 }, { STR_CTRL_K2, STR_CTRL_V2 },
        { STR_CTRL_K3, STR_CTRL_V3 }, { STR_CTRL_K4, STR_CTRL_V4 }, { STR_CTRL_K5, STR_CTRL_V5 },
        { STR_CTRL_K7, STR_CTRL_V7 }, { STR_CTRL_K6, STR_CTRL_V6 } };
    for (int i = 0; i < 8; i++) {
        int k = rows[i][0];
        if (g_settings.controls && i == 4) k = STR_CTRL_K4B;
        if (g_settings.controls && i == 5) k = STR_CTRL_K5B;
        if (g_settings.controls && i == 6) k = STR_CTRL_K7B;
        int y = 31 + i * 11;
        text_draw(102 - text_width(game_str(k)), y, game_str(k), C_PAPER, 0);
        text_draw(111, y, game_str(rows[i][1]), C_LGREY, 0);
    }
    canvas_rect(60, 121, 120, 1, C_DGREY);
    text_lines_center(127, 11, game_str(STR_CTRL_TIP), C_GREY);
    canvas_present();
    ui_fade_in(2);
    for (int t = 0;; t++) {
        canvas_rect(222, 148, 14, 10, 0);
        if ((t >> 5) & 1) text_draw(226, 148, "\x01", C_GREY, 0);
        canvas_present();
        if (ui_keys_pressed() & (KEY_A | KEY_START)) break;
    }
    snd_play(SND_UI_SELECT, 90, 0, 0, 200);
    ui_fade_out(2);
}

void ui_chapter(int strId, int numStr) {
    fx_reset();
    g_fx.mode3d = 0;
    g_fx.fade = 16;
    pal_bg_game();
    canvas_clear(0);
    const char *s = game_str(strId);
    const char *n = game_str(numStr);
    int w = text_width(n) * 2;
    text_draw_big(120 - w / 2, 56, n, C_RED, 0, 2);
    text_draw_center(86, s, C_LGREY, 0);
    present2d();
    snd_play(SND_BELL, 150, 0, 0, 200);
    ui_fade_in(3);
    wait_frames(140);
    ui_fade_out(3);
}

// --------------------------------------------------------------- notes
void ui_note(int id) {
    u8 *scene = g_scene;
    if (!g_sceneValid) { canvas_from_screen(5); memcpy(scene, g_canvas, 240 * 160); }
    const char *title = game_str(STR_NOTE_TITLE_0 + id);
    const char *body = game_str(STR_NOTE_0 + id);
    int lines = text_count_lines(184, body);
    int perPage = 10;
    int pages = (lines + perPage - 1) / perPage;
    int page = 0;
    FxState fxWas = g_fx;
    int hudWas = hud_visible();
    ui_plain_fx();
    hud_set_visible(0); hud_update();
    int dirty = 1;
    while (1) {
      if (dirty) {
        dirty = 0;
        memcpy(g_canvas, scene, 240 * 160);
        canvas_paper(16, 6, 208, 148);
        text_draw(26, 13, title, C_INK, 0);
        canvas_rect(26, 24, 188, 1, C_PAPERD);
        text_wrap(26, 30, 184, 11, body, C_INK, 0, perPage, page * perPage);
        if (pages > 1) {
            char pg[16];
            pg[0] = '0' + page + 1; pg[1] = '/'; pg[2] = '0' + pages; pg[3] = 0;
            text_draw(198, 142, pg, C_PAPERD, 0);
            if (page < pages - 1) text_draw(26, 142, "\x01 next", C_PAPERD, 0);
        }
        present2d();
      }
        u16 p = ui_keys_pressed();
        if (p & (KEY_A | KEY_RIGHT | KEY_DOWN)) {
            if (page < pages - 1) { page++; dirty = 1; snd_play(SND_PAPER, 80, 0, 4600, 100); }
            else if (p & KEY_A) break;
        }
        if ((p & (KEY_LEFT | KEY_UP)) && page > 0) { page--; dirty = 1; snd_play(SND_PAPER, 80, 0, 4600, 100); }
        if (p & (KEY_B | KEY_START)) break;
    }
    snd_play(SND_PAPER, 70, 0, 5000, 100);
    g_fx = fxWas;
    hud_set_visible(hudWas);
}

static void notes_journal(void) {
    int sel = 0;
    u8 *scene = g_scene;
    int dirty = 1;
    while (1) {
      if (dirty) {
        dirty = 0;
        memcpy(g_canvas, scene, 240 * 160);
        canvas_rect(14, 10, 212, 140, C_INK);
        canvas_frame(14, 10, 212, 140, C_DGREY);
        text_draw_center(16, game_str(STR_UI_JOURNAL), C_WHITE, 0);
        int count = 0;
        for (int i = 0; i < NUM_NOTES; i++) {
            int have = (g_state.notesFound >> i) & 1;
            int y = 32 + i * 9;
            const char *t = have ? game_str(STR_NOTE_TITLE_0 + i) : "- - -";
            int c = i == sel ? C_WHITE : (have ? C_GREY : C_DGREY);
            if (i == sel) text_draw(22, y, ">", C_RED, 0);
            text_draw(30, y, t, c, 0);
            count += have;
        }
        char buf[24];
        int n = 0;
        const char *a = game_str(STR_UI_FOUND);
        while (*a) buf[n++] = *a++;
        if (count >= 10) buf[n++] = '0' + count / 10;
        buf[n++] = '0' + count % 10; buf[n++] = '/';
        buf[n++] = '0' + NUM_NOTES / 10; buf[n++] = '0' + NUM_NOTES % 10; buf[n] = 0;
        text_draw(30, 140, buf, C_GREY, 0);
        present2d();
      }
        u16 p = ui_keys_pressed();
        if (p & KEY_UP) { sel = (sel + NUM_NOTES - 1) % NUM_NOTES; dirty = 1; snd_play(SND_UI_MOVE, 60, 0, 0, 100); }
        if (p & KEY_DOWN) { sel = (sel + 1) % NUM_NOTES; dirty = 1; snd_play(SND_UI_MOVE, 60, 0, 0, 100); }
        if ((p & KEY_A) && ((g_state.notesFound >> sel) & 1)) {
            ui_note(sel);
            dirty = 1;
        }
        if (p & (KEY_B | KEY_START)) { snd_play(SND_UI_BACK, 70, 0, 0, 100); break; }
    }
}

void ui_options(int fromGame) {
    int sel = 0;
    u8 *scene = g_scene;
    static const char *bright[3] = { "DARK", "NORMAL", "BRIGHT" };
    static const char *ctl[2] = { "B RUN / SELECT LIGHT", "R RUN / B LIGHT" };
    int dirty = 1;
    while (1) {
      if (dirty) {
        dirty = 0;
        if (fromGame) memcpy(g_canvas, scene, 240 * 160); else canvas_clear(0);
        canvas_rect(20, 30, 200, 100, C_INK);
        canvas_frame(20, 30, 200, 100, C_DGREY);
        text_draw_center(38, game_str(STR_UI_OPTIONS), C_WHITE, 0);
        char vol[8] = "-----";
        for (int i = 0; i < 5; i++) vol[i] = i <= g_settings.volume ? '#' : '-';
        const char *labels[4] = { "BRIGHTNESS", "VOLUME", "CONTROLS", "BACK" };
        const char *vals[4] = { bright[g_settings.brightness], vol, ctl[g_settings.controls], "" };
        for (int i = 0; i < 4; i++) {
            int y = 56 + i * 16;
            int c = i == sel ? C_WHITE : C_GREY;
            if (i == sel) text_draw(28, y, ">", C_RED, 0);
            text_draw(36, y, labels[i], c, 0);
            text_draw(212 - text_width(vals[i]), y, vals[i], c, 0);
        }
        // brightness preview bar
        for (int i = 0; i < 8; i++) canvas_rect(36 + i * 20, 120, 18, 4, 1 + i * 8);
        present2d();
      }
        u16 p = ui_keys_pressed();
        if (p) dirty = 1;
        if (p & KEY_UP) { sel = (sel + 3) % 4; snd_play(SND_UI_MOVE, 60, 0, 0, 100); }
        if (p & KEY_DOWN) { sel = (sel + 1) % 4; snd_play(SND_UI_MOVE, 60, 0, 0, 100); }
        int d = (p & KEY_RIGHT) ? 1 : ((p & KEY_LEFT) ? -1 : 0);
        if ((p & KEY_A) && sel < 3) d = 1;
        if (d) {
            if (sel == 0) { g_settings.brightness = (g_settings.brightness + 3 + d) % 3; g_brightness = g_settings.brightness; pal_bg_game(); }
            if (sel == 1) { int v = g_settings.volume + d; if (v < 0) v = 0; if (v > 4) v = 4; g_settings.volume = v; g_masterVol = (16 + v * 12) >> (fromGame ? 1 : 0); }
            if (sel == 2) g_settings.controls ^= 1;
            snd_play(SND_UI_SELECT, 70, 0, 0, 100);
        }
        if ((p & KEY_A) && sel == 3) break;
        if (p & KEY_B) break;
    }
    settings_save();
    snd_play(SND_UI_BACK, 70, 0, 0, 100);
}

int ui_pause(void) {
    snd_play(SND_UI_SELECT, 80, 0, 0, 200);
    g_masterVol >>= 1;
    canvas_from_screen(6);
    u8 *scene = g_scene;
    memcpy(scene, g_canvas, 240 * 160);
    g_sceneValid = 1;
    // the menu is a plain screen: the view's effects (the wardrobe slats, a
    // fade or flash in progress, the fear wobble) wait until it closes
    FxState fxWas = g_fx;
    int hudWas = hud_visible();
    ui_plain_fx();
    g_fx.fade = 0; g_fx.white = 0; g_fx.mosaic = 0;
    hud_set_visible(0); hud_update();
    int sel = 0;
    static const int items[5] = { STR_UI_RESUME, STR_UI_MAP, STR_UI_JOURNAL, STR_UI_OPTIONS, STR_UI_QUIT };
    int fadeIn = 0;
    int result = -1;
    int dirty = 1;
    while (result < 0) {
      if (dirty) {
        dirty = 0;
        memcpy(g_canvas, scene, 240 * 160);
        text_draw_center(26, game_str(STR_UI_PAUSED), C_WHITE, C_INK);
        // objective
        text_draw_center(40, game_str(g_state.objective ? g_state.objective : STR_UI_NOOBJ), C_LGREY, C_INK);
        for (int i = 0; i < 5; i++) {
            int y = 60 + i * 13;
            const char *s = game_str(items[i]);
            int w = text_width(s);
            text_draw(120 - w / 2, y, s, i == sel ? C_WHITE : C_GREY, C_INK);
            if (i == sel) text_draw(120 - w / 2 - 10, y, "-", C_RED, 0);
        }
        // inventory line
        char inv[48]; int n = 0;
        const char *a = game_str(STR_UI_BATTERY);
        while (*a) inv[n++] = *a++;
        int b = g_state.battery / 10000;
        if (b >= 100) inv[n++] = '1';
        if (b >= 10) inv[n++] = '0' + (b / 10) % 10;
        inv[n++] = '0' + b % 10; inv[n++] = '%';
        if (g_state.fuses || g_state.fusesPlaced) {
            const char *f = game_str(STR_UI_FUSES);
            inv[n++] = ' '; inv[n++] = ' ';
            while (*f) inv[n++] = *f++;
            inv[n++] = '0' + g_state.fuses;
        }
        inv[n] = 0;
        text_draw_center(130, inv, C_GREY, C_INK);
        // keys
        int kx = 0, kw = 0;
        for (int k = 1; k < 8; k++) if ((g_state.keys >> k) & 1) kw += text_width(game_str(STR_KEY_BASE + k)) + 8;
        kx = 120 - kw / 2;
        for (int k = 1; k < 8; k++) if ((g_state.keys >> k) & 1) kx = text_draw(kx, 142, game_str(STR_KEY_BASE + k), C_PAPER, C_INK) + 8;
        present2d();
        if (fadeIn) { fadeIn = 0; ui_fade_in(1); }
      }
        u16 p = ui_keys_pressed();
        if (p) dirty = 1;
        if (p & KEY_UP) { sel = (sel + 4) % 5; snd_play(SND_UI_MOVE, 60, 0, 0, 100); }
        if (p & KEY_DOWN) { sel = (sel + 1) % 5; snd_play(SND_UI_MOVE, 60, 0, 0, 100); }
        if (p & KEY_START) result = PAUSE_RESUME;
        if (p & KEY_B) result = PAUSE_RESUME;
        if (p & KEY_A) {
            snd_play(SND_UI_SELECT, 80, 0, 0, 200);
            if (sel == 0) result = PAUSE_RESUME;
            else if (sel == 1) { ui_map(); fadeIn = 1; }
            else if (sel == 2) { memcpy(g_canvas, scene, 240 * 160); notes_journal(); }
            else if (sel == 3) { memcpy(g_canvas, scene, 240 * 160); ui_options(1); }
            else if (sel == 4) result = PAUSE_QUIT;
        }
    }
    g_masterVol = 16 + g_settings.volume * 12;
    if (result == PAUSE_QUIT) ui_fade_out(2);      // (as the plain screen it is)
    g_fx = fxWas;
    if (result == PAUSE_QUIT) g_fx.fade = 16;
    hud_set_visible(hudWas);
    g_sceneValid = 0;
    return result;
}

// --------------------------------------------------------------- death
void ui_jumpscare(void) {
    snd_stop_all();
    snd_play(SND_JUMPSCARE, 255, 0, 0, 255);
    snd_play(SND_STINGER, 200, 0, 0, 254);
    canvas_blit_lz(img_jumpscare);
    fx_reset();
    g_fx.mode3d = 0;
    g_fx.white = 16;            // the first frame is pure white: the palette changes behind it
    vram_leave_3d();
    u16 *dst = backbuf();
    bios_cpufastset(g_canvas, dst, 240 * 160 / 4);
    fx_prepare();
    flip_and_wait();
    pal_bg(pal_jumpscare, 248);
    for (int t = 0; t < 72; t++) {
        g_fx.zoom = 256 + t * 2 + (t < 10 ? t * 4 : 40);
        g_fx.offX = (s32)(rng_next() % 1537) - 768;
        g_fx.offY = (s32)(rng_next() % 1537) - 768;
        g_fx.white = t < 6 ? 12 - t * 2 : 0;
        g_fx.mosaic = (t > 50) ? (t - 50) / 3 : 0;
        if (t > 60) g_fx.fade = (t - 60) + 4;
        fx_prepare();
        vsync();
    }
    fx_reset();
    g_fx.fade = 16;
    fx_prepare();
    vsync();
    pal_bg_game();
}

void ui_death(void) {
    g_fx.mode3d = 0;
    canvas_clear(0);
    present2d();
    g_fx.fade = 16; fx_prepare();
    wait_frames(40);
    canvas_clear(0);
    const char *msg = game_str(STR_DEATH_0 + (g_state.deaths % NUM_DEATH_MSGS));
    text_draw_center(64, msg, C_RED, 0);
    present2d();
    snd_play(SND_BRAAM, 140, 0, 0, 200);
    ui_fade_in(4);
    wait_frames(60);
    ui_keys_pressed();          // nothing pressed before now counts
    for (int t = 0;; t++) {
        canvas_rect(0, 100, 240, 12, 0);
        if ((t >> 5) & 1) text_draw_center(100, game_str(STR_UI_CONTINUE), C_GREY, 0);
        present2d();
        if (ui_keys_pressed() & (KEY_A | KEY_START)) break;
    }
    snd_play(SND_UI_SELECT, 90, 0, 0, 200);
    ui_fade_out(2);
}

// --------------------------------------------------------------- ending
void ui_ending(int allNotes) {
    snd_stop_all();
    fx_reset();
    g_fx.mode3d = 0;
    g_fx.fade = 16;
    hud_init();
    pal_bg_game();
    canvas_clear(0);
    present2d();
    music_play(mus_ending, MUS_ENDING_LEN, SND_PIANO, 0, 220);
    g_fx.fade = 0; fx_prepare();
    for (int i = 0; i < NUM_ENDING_PAGES; i++) {
        ui_text_screen(game_str(STR_ENDING_0 + i), 1);
        ui_fade_out(2);
        canvas_clear(0); present2d();
        g_fx.fade = 0; fx_prepare();
    }
    if (allNotes) {
        ui_text_screen(game_str(STR_ENDING_TRUE), 1);
        ui_fade_out(2);
        canvas_clear(0); present2d();
        g_fx.fade = 0; fx_prepare();
    }
    // dawn image
    pal_bg(pal_dawn, 248);
    canvas_blit_lz(img_dawn);
    g_fx.fade = 16;
    present2d();
    ui_fade_in(6);
    wait_frames(240);
    ui_fade_out(6);
    pal_bg_game();
    // credits roll
    canvas_clear(0); present2d();
    g_fx.fade = 0; fx_prepare();
    music_play(mus_lullaby, MUS_LULLABY_LEN, SND_MUSICBOX, MUS_LULLABY_FRAMES, 160);
    const char *cr = game_str(STR_CREDITS);
    int lines = 1;
    for (const char *q = cr; *q; q++) if (*q == '\n') lines++;
    for (int off = -160; off < lines * 12 + 20; off++) {
        canvas_clear(0);
        text_lines_center(-off, 12, cr, C_LGREY);
        present2d();
        u16 p = ui_keys_pressed();
        if (p & KEY_START) break;
        if (!(p & KEY_A) && !(~REG_KEYINPUT & KEY_A)) { vsync(); }
    }
    // stats
    canvas_clear(0);
    text_draw_center(40, game_str(STR_UI_THEEND), C_WHITE, 0);
    char buf[48]; int n = 0;
    const char *a = game_str(STR_UI_NOTES);
    int cnt = 0;
    for (int i = 0; i < NUM_NOTES; i++) cnt += (g_state.notesFound >> i) & 1;
    while (*a) buf[n++] = *a++;
    if (cnt >= 10) buf[n++] = '0' + cnt / 10;
    buf[n++] = '0' + cnt % 10; buf[n++] = '/'; buf[n++] = '0' + NUM_NOTES / 10; buf[n++] = '0' + NUM_NOTES % 10; buf[n] = 0;
    text_draw_center(70, buf, C_GREY, 0);
    n = 0; a = game_str(STR_UI_DEATHS);
    while (*a) buf[n++] = *a++;
    int dd = g_state.deaths;
    if (dd >= 100) buf[n++] = '0' + dd / 100 % 10;
    if (dd >= 10) buf[n++] = '0' + dd / 10 % 10;
    buf[n++] = '0' + dd % 10; buf[n] = 0;
    text_draw_center(84, buf, C_GREY, 0);
    n = 0; a = game_str(STR_UI_TIME);
    while (*a) buf[n++] = *a++;
    u32 secs = g_state.playFrames / 60;
    u32 h = secs / 3600, m = (secs / 60) % 60, s = secs % 60;
    if (h > 99) h = 99;
    if (h >= 10) buf[n++] = '0' + h / 10;
    buf[n++] = '0' + h % 10; buf[n++] = ':'; buf[n++] = '0' + m / 10; buf[n++] = '0' + m % 10;
    buf[n++] = ':'; buf[n++] = '0' + s / 10; buf[n++] = '0' + s % 10; buf[n] = 0;
    text_draw_center(98, buf, C_GREY, 0);
    present2d();
    while (!(ui_keys_pressed() & (KEY_A | KEY_START))) {}
    ui_fade_out(3);
    music_stop();
}
