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

volatile u32 g_vblanks;
volatile u8  g_flipReq;
volatile u8  g_dispPage, g_bgHide;
volatile u32 g_lastFlip;
volatile u8  g_minFrames = 3;          // 20 fps
u8 g_quality;               // the detail level the governor chose (0 = full)
u32 g_profRaw;              // cycles the last render took
#ifdef DEV
u32 g_profFrame, g_profIrq;
EWRAM_BSS u32 g_irqParts[5];
volatile u32 g_govOff;      // test harness: hold the detail level fixed
#endif

extern int g_noteRequest, g_chapterRequest;

volatile u16 g_keyPressAcc;
static u16 s_keyPrevIrq;

EWRAM_BSS u32 g_irqStack[256] ALIGN4;      // the interrupt handlers' stack (crt0.s)
static inline u32 prof_read(void);
void irq_dispatch(u32 flags) {
    if (flags & IRQ_VBLANK) {
        DEV_ONLY(u32 ta = prof_read();)
        audio_vblank();
        g_vblanks++;
        u16 k = ~REG_KEYINPUT & KEY_MASK;
        g_keyPressAcc |= k & ~s_keyPrevIrq;
        s_keyPrevIrq = k;
        int flipped = 0;
        if (g_flipReq && g_vblanks - g_lastFlip >= g_minFrames) {
            g_dispPage ^= 1;
            g_bgHide = 0;
            g_flipReq = 0;
            g_lastFlip = g_vblanks;
            flipped = 1;
        }
        DEV_ONLY(u32 t1 = prof_read();)
        fx_vblank(flipped);
        DEV_ONLY(u32 t2 = prof_read();)
        hud_oam_commit();
        DEV_ONLY(u32 t3 = prof_read();)
        music_tick();
        DEV_ONLY(u32 t4 = prof_read();)
        audio_mix();
        DEV_ONLY(u32 tb = prof_read();
                 g_profIrq = (g_profIrq * 7 + (tb - ta)) >> 3;
                 g_irqParts[0] = t1 - ta; g_irqParts[1] = t2 - t1; g_irqParts[2] = t3 - t2; g_irqParts[3] = t4 - t3; g_irqParts[4] = tb - t4;)
    }
}

static inline void prof_start(void) {
    REG_TM2CNT_H = 0; REG_TM3CNT_H = 0;
    REG_TM2CNT_L = 0; REG_TM3CNT_L = 0;
    REG_TM3CNT_H = 0x84; REG_TM2CNT_H = 0x80;
}
// (the two halves are read one after the other: when the low one wraps in
// between, the high one read first is one short, 65,536 cycles in all)
static inline u32 prof_read(void) {
    u32 hi = REG_TM3CNT_L, lo = REG_TM2CNT_L, hi2 = REG_TM3CNT_L;
    if (hi2 != hi) lo = REG_TM2CNT_L;
    return (hi2 << 16) | lo;
}

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
u32 g_renderCount, g_profUpdate;
// the detail governor's state (render_frame)
static u8 s_q, s_hold, s_since = 255;
static u16 s_wait = 8, s_stale;
static u32 s_prevWork, s_tried, s_failed = 0xFFFFFFFF;       // the frame cost the last try up started from; the one that failed
static s32 s_failX, s_failY;                                 // ... and where the camera was
static u16 s_failA;
// a new scene (a level just loaded, a checkpoint restored): full detail
// until its frames prove too slow, which takes one frame per level
static void governor_reset(void) { s_q = 0; s_hold = 0; s_since = 255; s_wait = 8; s_prevWork = 0; s_failed = 0xFFFFFFFF; s_stale = 0; }

// Draws a frame and waits for it to be shown. The governor adds the time
// since the last prof_start() (the game update that led to this frame) to
// the time of the render: every caller starts the timer before its update,
// or just before the call when it renders without one.
static void render_frame(void) {
    g_profUpdate = prof_read();
    prof_start();
    game_render();
    g_renderCount++;
    g_profRaw = prof_read();
    DEV_ONLY(g_profFrame = (g_profFrame * 7 + g_profRaw) >> 3;)
    // detail governor for the 20 fps frame (3 vblanks = 842k cycles): when
    // a frame comes close to the deadline the far floor gets coarser, far
    // walls and far furniture drop to one sample per column pair and small
    // furniture faces are dropped sooner; near things keep full detail.
#ifdef DEV
    if (!g_govOff)
#endif
    {
        // levels, cheapest-looking first: the far floor coarser (split), far
        // furniture at one sample per column pair (hd, 1/4096 tile), far
        // walls at one sample per pair (whalf: walls shorter than this) and
        // everything at one sample per pair also one sample per two rows
        // (vh), small far faces dropped sooner (lod), then the sides of the
        // view outside a central band of full resolution
        static const struct { u8 band, split, vh, pad; u16 whalf, hd, lod; } q[] = {
            { 120,  0, 0, 0,   0, 0x2400, 256 },
            { 120, 20, 0, 0,   0, 0x2000, 256 },
            { 120, 26, 1, 0,  96, 0x1C00, 288 },
            { 120, 30, 1, 0, 128, 0x1800, 320 },
            { 120, 35, 1, 0, 192, 0x1400, 384 },
            {  90, 35, 1, 0, 256, 0x1000, 448 },
            {  60, 35, 1, 0, 320, 0x0C00, 512 },
            {   0, 35, 1, 0, 400, 0x0000, 768 },
        };
        // a frame has 842,688 cycles (3 vblanks); the work is measured from
        // the start of the game update to the end of the render, interrupts
        // included. Too slow: one level down at once. Comfortably fast for 8
        // frames: try one level up; if that level then proves too slow at
        // once, wait longer before the next try.
        // (Successive frames alternate in cost by 20-25k: going up is judged
        // on the mean of the last two, going down on each frame.)
        // (A frame whose update drew a line of text is no measure of the
        // scene: it counts as its predecessor did.)
        u32 work = g_profUpdate + g_profRaw;
        if (g_hudDrew) { g_hudDrew = 0; if (s_prevWork) work = s_prevWork; }
        u32 pair = (work + s_prevWork) >> 1;
        s_prevWork = work;
        if (s_since < 255) s_since++;
        if (work > 820000) {
            if (s_q < 7) {
                s_q++;
                if (s_since <= 2) {                 // the try failed
                    s_wait = s_wait < 240 ? s_wait * 2 : 240;
                    s_failed = s_tried;             // ... from frames this cheap, here: no use trying again as things are
                    s_failX = g_cam.x; s_failY = g_cam.y; s_failA = g_cam.angle;
                }
            }
            s_hold = 0;
        } else if (pair < 770000 && (pair < s_failed - (s_failed >> 5) || s_stale > 600 ||
                                     dist_approx(g_cam.x - s_failX, g_cam.y - s_failY) > 0x8000 ||
                                     (u16)(g_cam.angle - s_failA + 0x1000) > 0x2000)) {
            // (not while the view is the one in which the last try failed and
            // costs what it did: a try that fails is a frame dropped. Half a
            // tile or a sixteenth of a turn away, 3% cheaper, or half a minute
            // on, it is worth another.)
            if (++s_hold >= s_wait && s_q > 0) { s_q--; s_hold = 0; s_since = 0; s_tried = pair; s_stale = 0; }
        } else s_hold = 0;
        if (s_stale < 0xFFFF) s_stale++;
        if (s_since > 60 && s_wait > 8) { s_wait--; }
        extern u32 g_lodScale;
        extern s32 g_halfDist, g_floorSplit, g_wallHalfLh, g_fullC0, g_fullC1;
        extern u32 g_vhalf;
        g_vhalf = q[s_q].vh;
        g_floorSplit = q[s_q].split;
        g_wallHalfLh = q[s_q].whalf;
        g_halfDist = (s32)q[s_q].hd << 4;
        g_lodScale = q[s_q].lod;
        g_fullC0 = VIEW_W / 2 - q[s_q].band;
        g_fullC1 = VIEW_W / 2 + q[s_q].band;
        g_quality = s_q;
    }
    g_flipReq = 1;
    while (g_flipReq) bios_halt();
}

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
        g_flipReq = 1;
        while (g_flipReq) bios_halt();
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
        prof_start();
        game_update();
        render_frame();
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
    governor_reset();
    for (int i = 16; i >= 0; i -= 2) {
        g_fx.fade = i;
        prof_start();
        game_update();
        render_frame();
    }
    g_fx.fade = 0;
}

static void play(void) {
    g_keyPressAcc = 0;
    pal_bg_game();
    fade_in_game();
    u32 last = g_vblanks;
    while (1) {
        prof_start();
        u32 now = g_vblanks;
        int steps = now - last;
        last = now;
        if (steps < 1) steps = 1;
        if (steps > 4) steps = 4;
        for (int i = 0; i < steps; i++) {
            game_update();
            if (g_gameSignal || g_noteRequest >= 0 || g_chapterRequest >= 0) break;
        }
        if (g_noteRequest >= 0) {
            int id = g_noteRequest;
            g_noteRequest = -1;
            render_frame();
            ui_note(id);
            g_fx.mode3d = 1;
            g_keyPressAcc = 0;
            last = g_vblanks;
            continue;
        }
        if (g_chapterRequest >= 0) {
            g_chapterRequest = -1;
            last = g_vblanks;
        }
        switch (g_gameSignal) {
        case GS_PAUSE:
            g_gameSignal = GS_PLAY;
            if (ui_pause() == PAUSE_QUIT) { snd_stop_all(); return; }
            g_fx.mode3d = 1;
            g_keyPressAcc = 0;
            last = g_vblanks;
            prof_start();               // (the time spent away is not this frame's)
            break;
        case GS_MAP:
            g_gameSignal = GS_PLAY;
            ui_map();
            g_fx.mode3d = 1;
            for (int i = 16; i >= 0; i -= 2) { g_fx.fade = i; prof_start(); render_frame(); }   // back to the view, the game still held
            g_keyPressAcc = 0;
            last = g_vblanks;
            prof_start();               // (the time spent away is not this frame's)
            break;
        case GS_DEAD:
            death_sequence();
            game_restore_checkpoint();
            pal_bg_game();
            g_keyPressAcc = 0;          // nothing pressed during the death screens carries over
            fade_in_game();
            last = g_vblanks;
            prof_start();               // (the time spent away is not this frame's)
            break;
        case GS_EXIT:
            level_transition(g_nextLevel);
            if (g_gameSignal == GS_ENDING) break;
            pal_bg_game();
            g_keyPressAcc = 0;          // nor during the chapter card
            fade_in_game();
            last = g_vblanks;
            prof_start();               // (the time spent away is not this frame's)
            break;
        }
        if (g_gameSignal == GS_ENDING) {
            int all = 1;
            for (int i = 0; i < NUM_NOTES; i++) if (!((g_state.notesFound >> i) & 1)) all = 0;
            for (int i = 0; i <= 16; i++) { g_fx.fade = i; prof_start(); render_frame(); }
            save_erase();
            ui_ending(all);
            return;
        }
        render_frame();
    }
}

int main(void) {
    REG_WAITCNT = 0x4317;
    REG_DISPCNT = DCNT_MODE4 | DCNT_BG2 | DCNT_OBJ | DCNT_OBJ_1D;
    settings_load();
    g_brightness = g_settings.brightness;
    g_masterVol = 16 + g_settings.volume * 12;
    pal_bg_game();
    bios_lz77_wram(cmap_default, g_colormapSrc);
    render_init();
    // the flashlight's states the game jumps between: on, off, and the dip of a flicker (player.c)
    render_flash_warm(256); render_flash_warm(0); render_flash_warm(256 / 5);
    fx_init();
    hud_init();
    audio_init();
    REG_DISPSTAT = 8;
    REG_IE = IRQ_VBLANK;
    REG_IME = 1;

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
