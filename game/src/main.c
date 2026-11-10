// SPDX-License-Identifier: MIT
// Hollowmere - main loop and game state machine
#include "gba.h"
#include "engine.h"
#include "world.h"
#include "assets.h"
#include "audio.h"
#include "gfx.h"
#include "fx.h"
#include "hud.h"
#include "game.h"
#include "ui.h"
#include "dev.h"

extern volatile u16 g_keyPressAcc;      // key presses caught by the vblank interrupt (engine_keys_pressed takes them)

// --------------------------------------------------------------- splash
static void splash(void) {
    fx_reset();
    g_fx.mode3d = 0;
    g_fx.fade = 16;
    pal_bg_game();
    canvas_clear(0);
    text_draw_center(58, game_str(STR_SPLASH_0), C_LGREY, 0);
    text_draw_center(74, game_str(STR_SPLASH_1), C_GREY, 0);
    text_draw_center(86, game_str(STR_SPLASH_2), C_GREY, 0);
    canvas_present();
    ui_fade_in(3);
    for (int i = 0; i < 150; i++) { if (ui_keys_pressed() & (KEY_A | KEY_START)) break; }
    ui_fade_out(3);
}

// --------------------------------------------------------------- play
static void death_sequence(void) {
    Player *p = &g_player;
    p->frozen = 1;
    if (p->hiding) player_hide_exit();
    for (int l = 0; l < HL_COUNT; l++) hud_clear(l);
    hud_update();
    snd_play3d(SND_CSCREAM, g_cr.x, g_cr.y, 255, 4600, 255);
    u16 want = angle_to(g_cr.x - p->x, g_cr.y - p->y);
    for (int t = 0; t < 30; t++) {
        s16 diff = (s16)(want - p->angle);
        p->angle += diff / 4;
        s32 cx = lu_cos(p->angle), cy = lu_sin(p->angle);
        s32 tx = p->x + cx * 3, ty = p->y + cy * 3;      // 0.75 tiles
        g_cr.x += (tx - g_cr.x) / 3; g_cr.y += (ty - g_cr.y) / 3;
        g_cr.angle = angle_to(p->x - g_cr.x, p->y - g_cr.y);
        g_cr.state = CR_KILL;
        g_cr.frame = t;                 // the lunge: rearing, reaching, on you
        g_fx.wave = 60 + t * 3;
        g_fx.wavePhase += 2000;
        g_fx.offX = (s32)(rng_next() % 1025) - 512;
        g_fx.offY = (s32)(rng_next() % 1025) - 512;
        g_fx.vignette = 150; g_fx.vigDark = 10;
        g_fx.roll = (u16)((s32)(rng_next() % 801) - 400);
        g_state.flashOn = 1;
        g_flashOn = 1; g_flashPower = (t & 2) ? 256 : 60;
        g_cam.x = p->x; g_cam.y = p->y; g_cam.angle = p->angle;
        camera_update(&g_cam);
        world_update_lights(g_frame);
        creature_light();
        render_build_flash_tables();
        game_build_sprites();
        render_enter_3d();
        render_view(backbuf3d());
        fx_prepare();
        engine_present();
    }
    hud_set_visible(0); hud_update();
    ui_jumpscare();
    g_state.deaths++;
    snd_stop_all();
    ui_death();
}

static void level_transition(int next) {
    for (int i = 0; i <= 16; i += 2) {
        g_fx.fade = i;
        engine_frame_start();
        game_update();
        engine_frame();
    }
    snd_stop_all();
    if (next >= NUM_LEVELS) { g_gameSignal = GS_ENDING; return; }
    snd_play(SND_STAIRS, 160, 0, 0, 200);
    g_state.level = next;
    ui_chapter(STR_CHAPTER_0 + next, STR_CHNUM_0 + next);
    game_load_level(next, 0);
}

static void fade_in_game(void) {
    g_fx.mode3d = 1;
    engine_frame_reset();
    for (int i = 16; i >= 0; i -= 2) {
        g_fx.fade = i;
        engine_frame_start();
        game_update();
        engine_frame();
    }
    g_fx.fade = 0;
}

static void play(void) {
    g_keyPressAcc = 0;
    pal_bg_game();
    fade_in_game();
    u32 last = g_vblanks;
    while (1) {
        engine_frame_start();
        u32 now = g_vblanks;
        int steps = now - last;
        last = now;
        if (steps < 1) steps = 1;
        if (steps > 4) steps = 4;
        for (int i = 0; i < steps; i++) {
            game_update();
            if (g_gameSignal || g_noteRequest >= 0) break;
        }
        if (g_noteRequest >= 0) {
            int id = g_noteRequest;
            g_noteRequest = -1;
            engine_frame();
            ui_note(id);
            g_fx.mode3d = 1;
            g_keyPressAcc = 0;
            last = g_vblanks;
            continue;
        }
        switch (g_gameSignal) {
        case GS_PAUSE:
            g_gameSignal = GS_PLAY;
            if (ui_pause() == PAUSE_QUIT) { snd_stop_all(); return; }
            g_fx.mode3d = 1;
            g_keyPressAcc = 0;
            last = g_vblanks;
            engine_frame_start();               // (the time spent away is not this frame's)
            break;
        case GS_MAP:
            g_gameSignal = GS_PLAY;
            ui_map();
            g_fx.mode3d = 1;
            for (int i = 16; i >= 0; i -= 2) { g_fx.fade = i; engine_frame_start(); engine_frame(); }   // back to the view, the game still held
            g_keyPressAcc = 0;
            last = g_vblanks;
            engine_frame_start();               // (the time spent away is not this frame's)
            break;
        case GS_DEAD:
            death_sequence();
            game_restore_checkpoint();
            pal_bg_game();
            g_keyPressAcc = 0;          // nothing pressed during the death screens carries over
            fade_in_game();
            last = g_vblanks;
            engine_frame_start();               // (the time spent away is not this frame's)
            break;
        case GS_EXIT:
            level_transition(g_nextLevel);
            if (g_gameSignal == GS_ENDING) break;
            pal_bg_game();
            g_keyPressAcc = 0;          // nor during the chapter card
            fade_in_game();
            last = g_vblanks;
            engine_frame_start();               // (the time spent away is not this frame's)
            break;
        }
        if (g_gameSignal == GS_ENDING) {
            int all = 1;
            for (int i = 0; i < NUM_NOTES; i++) if (!((g_state.notesFound >> i) & 1)) all = 0;
            for (int i = 0; i <= 16; i++) { g_fx.fade = i; engine_frame_start(); engine_frame(); }
            save_erase();
            ui_ending(all);
            return;
        }
        engine_frame();
    }
}

int main(void) {
    settings_load();
    g_brightness = g_settings.brightness;
    g_masterVol = 16 + g_settings.volume * 12;
    engine_init();
    // the flashlight's states the game jumps between: on, off, and the dip of a flicker (player.c)
    render_flash_warm(256); render_flash_warm(0); render_flash_warm(256 / 5);

    splash();
    while (1) {
        int choice = ui_title();
        int saved = choice == TITLE_CONTINUE ? save_read(&g_checkpoint) : SAVE_NONE;
        if (saved != SAVE_NONE) {
            g_state = g_checkpoint;
            ui_chapter(STR_CHAPTER_0 + g_state.level, STR_CHNUM_0 + g_state.level);
            if (saved == SAVE_OK) { g_hasCheckpoint = 1; game_restore_checkpoint(); }
            else { g_hasCheckpoint = 0; game_load_level(g_state.level, 0); }      // a version 1.0 save: its chapter from the start
        } else {
            game_new();
            ui_intro();
            ui_controls();
            ui_chapter(STR_CHAPTER_0, STR_CHNUM_0);
            game_load_level(0, 0);
        }
        play();
    }
}
