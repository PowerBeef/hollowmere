// SPDX-License-Identifier: MIT
// Game glue: level state, update loop, rendering, checkpoints, fear
#include "game.h"
#include "render.h"
#include "world.h"
#include "audio.h"
#include "assets.h"
#include "hud.h"
#include "fx.h"
#include "gfx.h"
#include "objects.h"
#include "ui.h"
#include "dev.h"
#include <string.h>

EWRAM_BSS SaveState g_state;
EWRAM_BSS SaveState g_checkpoint;

// The test scripts read these by offset (game/tests/hm.py): moving a field
// means changing it there too.
#include <stddef.h>
_Static_assert(offsetof(SaveState, level) == 4 && offsetof(SaveState, objective) == 6 && offsetof(SaveState, keys) == 12 &&
               offsetof(SaveState, fuses) == 14 && offsetof(SaveState, fusesPlaced) == 15 && offsetof(SaveState, flashOn) == 20 &&
               offsetof(SaveState, deaths) == 22 && offsetof(SaveState, trigFired) == 56 && offsetof(SaveState, flags) == 144 &&
               offsetof(SaveState, lightLevel) == 152, "SaveState layout: update game/tests/hm.py");
_Static_assert(offsetof(Creature, x) == 4 && offsetof(Creature, y) == 8 && offsetof(Creature, timer) == 34, "Creature layout: update game/tests/hm.py");
_Static_assert(offsetof(Player, hiding) == 16 && offsetof(Player, frozen) == 37, "Player layout: update game/tests/hm.py");
_Static_assert(offsetof(FxState, slits) == 22, "FxState layout: update game/tests/hm.py");
_Static_assert(offsetof(Settings, controls) == 2, "Settings layout: update game/tests/hm.py");
_Static_assert(sizeof(Thing) == 16 && offsetof(Thing, flags) == 10 && MAX_THINGS == 112, "Thing layout: update game/tests/hm.py");
u8 g_hasCheckpoint;
EWRAM_BSS Thing g_things[MAX_THINGS];
int g_numThings;
u8 g_gameSignal;
u8 g_nextLevel;
u32 g_frame;

extern int g_shakeAmt, g_shakeT, g_flashT, g_blackoutT, g_fadeTarget, g_fadeSpeed, g_fadeAcc;
extern int g_lookX, g_lookY, g_ambience;

static int s_heartT;
static u32 s_trigInside;            // triggers the player stood in last tick
static u8 s_pendingEv[8];           // events waiting for a free script thread

// ------------------------------------------------------------- test hooks
// (the test ROM only: see dev.h and docs/TOOLS.md)
#ifdef DEV
volatile s32 g_debugCmd, g_debugA, g_debugB, g_debugC;
volatile u32 g_dbgFreeze;
EWRAM_BSS u32 g_benchOut[4];
EWRAM_BSS u32 g_pcSamples[4097];   // the sampling profiler's buffer (crt0.s)
EWRAM_BSS u32 g_profUpd[5], g_profParts[6];     // (the test ROM's counters stay out of the fast RAM the stack needs)

#define PNOW() PROF_T()
static void debug_hook(void) {
    s32 cmd = g_debugCmd;
    if (cmd <= 0) return;
    g_debugCmd = 0;
    switch (cmd) {
    case 1: {   // spawn the creature g_debugA/16 tiles in front of the player, state g_debugB
        s32 d = g_debugA << 12;
        s32 x = g_player.x + (s32)(((s64)lu_cos(g_player.angle) * d) >> 14);
        s32 y = g_player.y + (s32)(((s64)lu_sin(g_player.angle) * d) >> 14);
        creature_spawn(x, y, g_debugB);
        if (g_debugB == CR_CHASE) { g_cr.alert = 256; g_cr.lastX = g_player.x; g_cr.lastY = g_player.y; }
        break; }
    case 2:     // teleport to (A,B) in 1/256 tiles, angle C
        g_player.x = g_debugA << 8; g_player.y = g_debugB << 8; g_player.angle = g_debugC;
        break;
    case 3: g_state.keys = 0xFFFE; g_state.fuses = 3; break;
    case 4: g_nextLevel = g_debugA; g_gameSignal = GS_EXIT; break;
    case 5: creature_despawn(); g_cr.cooldown = 30000; break;
    case 6: script_start(g_debugA); break;
    case 8: {   // start the PC sampler (timer 1, every 1024 cycles)
        extern u32 g_pcSamples[4097];
        g_pcSamples[0] = 0;
        REG_TM1CNT_H = 0;
        REG_TM1CNT_L = 65536 - 1024;
        REG_TM1CNT_H = 0x00C0;          // enable, IRQ, prescaler 1
        REG_IE |= 0x10;
        break; }
    case 9:     // stop it
        REG_TM1CNT_H = 0;
        REG_IE &= ~0x10;
        break;
#ifdef VBENCH
    case 10: {  // micro benchmark: one synthetic prop face (rows A, columns B, C: full res)
        extern u32 vface_bench(u8 *fb, int rows, int cols, int full);
        u16 ime = REG_IME; REG_IME = 0;
        REG_TM2CNT_H = 0; REG_TM3CNT_H = 0; REG_TM2CNT_L = 0; REG_TM3CNT_L = 0;
        REG_TM3CNT_H = 0x84; REG_TM2CNT_H = 0x80;
        g_benchOut[0] = vface_bench(backbuf3d(), g_debugA, g_debugB, g_debugC);
        REG_IME = ime;
        break; }
#endif
    case 7: {   // micro benchmark: 100 column pairs of 128 rows into the back page
        extern u32 g_benchOut[4];
        u8 *dst = backbuf3d();
        const u8 *tex = walltex[3];
        u16 ime = REG_IME; REG_IME = 0;
        REG_TM2CNT_H = 0; REG_TM3CNT_H = 0; REG_TM2CNT_L = 0; REG_TM3CNT_L = 0;
        REG_TM3CNT_H = 0x84; REG_TM2CNT_H = 0x80;
        for (int i = 0; i < 100; i++) {
            ColPair cp;
            cp.p = dst + (i & 63) * 2; cp.a0 = 10; cp.a1 = 138; cp.b0 = 10; cp.b1 = 138;
            cp.texA = tex; cp.texB = tex + 128; cp.cmA = g_colormap + 31 * 256; cp.cmB = cp.cmA;
            cp.tpA = 0; cp.tpB = 0; cp.stA = 0x8000; cp.stB = 0x8000;
            cp.pmode = g_debugA == 2 ? 1 : 0; cp.ptex = tex + 10880;
            if (g_debugA == 0 || g_debugA == 2) col_pair(&cp);
            else wall_column(dst + 10 * 240 + (i & 63) * 2, tex, cp.cmA, 0, 0x8000, 128);
        }
        g_benchOut[0] = ((u32)REG_TM3CNT_L << 16) | REG_TM2CNT_L;
        REG_IME = ime;
        break; }
    }
}
#endif

// ------------------------------------------------------------- math
s32 isqrt32(u32 v) {
    u32 r = 0, b = 1u << 30;
    while (b > v) b >>= 2;
    while (b) {
        if (v >= r + b) { v -= r + b; r = (r >> 1) + b; }
        else r >>= 1;
        b >>= 2;
    }
    return r;
}

s32 dist_approx(s32 dx, s32 dy) {
    if (dx < 0) dx = -dx;
    if (dy < 0) dy = -dy;
    if (dx < 0x1000000 && dy < 0x1000000) {
        u32 a = dx >> 6, b = dy >> 6;
        return isqrt32(a * a + b * b) << 6;
    }
    if (dx < dy) { s32 t = dx; dx = dy; dy = t; }
    return dx + ((dy * 3) >> 3) + (dy >> 5);
}

u16 angle_to(s32 dx, s32 dy) {
    // octant-based atan2 approximation, 0..65535
    if (dx == 0 && dy == 0) return 0;
    s32 ax = dx < 0 ? -dx : dx, ay = dy < 0 ? -dy : dy;
    s32 a;
    if (ax >= ay) {
        s32 t = (s32)(((s64)ay << 15) / ax);          // tan in Q15 (0..1)
        a = (t * 8192 >> 15) + ((t * (32768 - t) >> 15) * 2289 >> 15);   // atan(t)/(2pi)*65536
    } else {
        s32 t = (s32)(((s64)ax << 15) / ay);
        a = 16384 - ((t * 8192 >> 15) + ((t * (32768 - t) >> 15) * 2289 >> 15));
    }
    if (dx < 0) a = 32768 - a;
    if (dy < 0) a = 65536 - a;
    return (u16)a;
}

// ------------------------------------------------------------- strings
const char *game_str(int id) { return (id >= 0 && id < NUM_STRINGS) ? str_table[id] : ""; }

void game_message(int str, int frames) { hud_message(game_str(str), frames); }

void game_set_objective(int str) {
    g_state.objective = str;
    hud_text(HL_TOP, game_str(str), 260, HC_GOLD);
}

void game_noise(s32 x, s32 y, s32 radius) { creature_hear(x, y, radius); }

// ------------------------------------------------------------- things
void things_load(const LevelDef *L) {
    g_numThings = L->numThings < MAX_THINGS ? L->numThings : MAX_THINGS;
    for (int i = 0; i < g_numThings; i++) {
        const ThingDef *d = &L->things[i];
        Thing *t = &g_things[i];
        t->x = d->x << 8; t->y = d->y << 8;
        t->type = d->type; t->param = d->param; t->event = d->event; t->z = d->z;
        t->flags = 0;
        if ((d->flags & TDF_HIDDEN) && !((g_state.thingShown[i >> 3] >> (i & 7)) & 1)) t->flags |= THF_HIDDEN;
        if ((g_state.thingTaken[i >> 3] >> (i & 7)) & 1) t->flags |= THF_TAKEN;
    }
}

int thing_take(int idx) {
    g_things[idx].flags |= THF_TAKEN;
    g_state.thingTaken[idx >> 3] |= 1 << (idx & 7);
    return 1;
}

// ------------------------------------------------------------- level
void game_new(void) {
    memset(&g_state, 0, sizeof g_state);
    g_state.magic = SAVE_MAGIC;
    g_state.level = 0;
    g_state.battery = 1000000;
    g_state.flashOn = 1;
    g_hasCheckpoint = 0;
}

static void reset_level_state(void) {
    memset(g_state.thingTaken, 0, sizeof g_state.thingTaken);
    memset(g_state.thingShown, 0, sizeof g_state.thingShown);
    memset(g_state.trigFired, 0, sizeof g_state.trigFired);
    memset(g_state.roomsSeen, 0, sizeof g_state.roomsSeen);
    memset(g_state.doorState, 0, sizeof g_state.doorState);
    memset(g_state.propHidden, 0, sizeof g_state.propHidden);
    memset(g_state.propSet, 0, sizeof g_state.propSet);
    for (int i = 0; i < 16; i++) g_state.lightLevel[i] = 16;
    g_state.fuses = 0; g_state.fusesPlaced = 0;
    g_state.keys = 0;
    g_state.objective = 0;
}

void game_load_level(int level, int fromCheckpoint) {
    const LevelDef *L = level_table[level];
    g_state.level = level;
    if (!fromCheckpoint) {
        reset_level_state();
        g_state.creatureMode = L->monsterMode;
    }
    snd_stop_all();
    music_stop();
    g_ambience = -1;
    world_load_level(L);
    things_load(L);
    // doors
    for (int i = 0; i < g_numDoors; i++) {
        if (g_state.doorState[i] & DS_OPEN) g_doors[i].open = 0xFFFF;
        else if (fromCheckpoint || !(g_doors[i].flags & DOORF_STARTOPEN)) g_doors[i].open = 0;
        if (!fromCheckpoint && (g_doors[i].flags & DOORF_STARTOPEN)) g_state.doorState[i] |= DS_OPEN;
    }
    // script-toggled furniture
    for (int i = 0; i < g_numProps; i++)
        if ((g_state.propSet[i >> 3] >> (i & 7)) & 1) {
            if ((g_state.propHidden[i >> 3] >> (i & 7)) & 1) g_props[i].flags |= PIF_HIDDEN;
            else g_props[i].flags &= ~PIF_HIDDEN;
        }
    // light groups
    for (int i = 0; i < g_numDLights; i++) {
        int gidx = g_dlights[i].def->group;
        if (gidx < 16) g_dlights[i].level = g_state.lightLevel[gidx] >= 15 ? 256 : g_state.lightLevel[gidx] * 16;
    }
    g_lightsDirty = 1;
    creature_init(g_state.creatureMode);
    script_reset();
    s_trigInside = 0;
    memset(s_pendingEv, 0, sizeof s_pendingEv);
    fx_reset();
    g_fx.mode3d = 1;
    g_fx.letterbox = 1;      // cinema bars: rows VIS0..VIS1 show the view
    g_fear = 0;
    s_heartT = 0;
    hud_init();
    if (fromCheckpoint) {
        player_init(g_state.px, g_state.py, g_state.pangle);
    } else {
        player_init(L->startX << 8, L->startY << 8, L->startAngle);
    }
    g_cam.x = g_player.x; g_cam.y = g_player.y; g_cam.angle = g_player.angle;
    camera_update(&g_cam);
    if (L->ambience) g_ambience = snd_play(L->ambience, 110, 0, 0, 255);
    g_gameSignal = GS_PLAY;
    if (!fromCheckpoint) {
        // (the checkpoint holds the start event at its first step: restoring
        // it plays the level's opening again)
        if (L->startEvent) script_start(L->startEvent);
        game_checkpoint();
    } else {
        // The scripts go on from where the checkpoint caught them. What a
        // checkpoint does not hold (the enemy, music) the level's "resume"
        // event puts back.
        script_load(&g_state.script);
        if (L->resumeEvent) script_start(L->resumeEvent);
        if (g_state.objective) hud_text(HL_TOP, game_str(g_state.objective), 200, HC_GOLD);
    }
}

void game_checkpoint(void) {
    g_state.px = g_player.x; g_state.py = g_player.y; g_state.pangle = g_player.angle;
    if (g_player.hiding) { g_state.px = g_player.outX; g_state.py = g_player.outY; }
    script_save(&g_state.script);
    memcpy(&g_checkpoint, &g_state, sizeof g_state);
    g_hasCheckpoint = 1;
    save_write(&g_checkpoint);
}

void game_restore_checkpoint(void) {
    u16 deaths = g_state.deaths;
    u32 frames = g_state.playFrames;
    u8 seenRooms[sizeof g_state.roomsSeen];
    memcpy(seenRooms, g_state.roomsSeen, sizeof seenRooms);
    memcpy(&g_state, &g_checkpoint, sizeof g_state);
    g_state.deaths = deaths;
    g_state.playFrames = frames;
    for (unsigned i = 0; i < sizeof seenRooms; i++) g_state.roomsSeen[i] |= seenRooms[i];   // the map stays learnt
    game_load_level(g_state.level, 1);
}

// ------------------------------------------------------------- update
// A trigger fires when the player steps into its cells: once ever, or (once
// = 0) on every entry. If no script thread is free it stays armed and fires
// when one is.
static void check_triggers(void) {
    int px = g_player.x >> 16, py = g_player.y >> 16;
    u32 inside = 0;
    for (int i = 0; i < g_level->numTrigs && i < 32; i++) {
        const TriggerDef *t = &g_level->trigs[i];
        if (px < t->x0 || px > t->x1 || py < t->y0 || py > t->y1) continue;
        if ((t->flags & TRIGF_ONCE) && ((g_state.trigFired[i >> 3] >> (i & 7)) & 1)) continue;
        if (t->needFlag && script_flag(t->needFlag - 1) == t->needNot) continue;   // not yet (or no longer)
        if ((s_trigInside >> i) & 1) { inside |= 1u << i; continue; }              // still standing in it
        if (!script_start(t->event)) continue;
        inside |= 1u << i;
        g_state.trigFired[i >> 3] |= 1 << (i & 7);
    }
    s_trigInside = inside;
}

// Start an event that must not be lost (an item was taken, a note read):
// when every script thread is busy it waits its turn.
void game_event(int ev) {
    if (!ev || script_start(ev)) return;
    for (unsigned i = 0; i < sizeof s_pendingEv; i++)
        if (!s_pendingEv[i]) { s_pendingEv[i] = ev; return; }
}
static void pending_events(void) {
    for (unsigned i = 0; i < sizeof s_pendingEv; i++)
        if (s_pendingEv[i] && script_start(s_pendingEv[i])) s_pendingEv[i] = 0;
}

static void update_fear(void) {
    s32 target = 0;
    if (g_cr.state != CR_OFF && g_cr.state != CR_SCRIPT) {
        s32 d = g_cr.dist >> 12;   // 1/16 tiles
        if (g_cr.state == CR_CHASE || g_cr.state == CR_KILL) target = 190 + (d < 96 ? (96 - d) * 2 / 3 : 0);
        else if (g_cr.hasLOS && d < 12 * 16) target = 70 + (12 * 16 - d) * 3 / 4;
        else if (d < 10 * 16) target = (10 * 16 - d) * 3 / 5;
    } else if (g_cr.state == CR_SCRIPT && g_cr.dist < (14 << 16)) target = 110;
    if (target > 256) target = 256;
    g_fear += (target - g_fear) / 12 + (target > g_fear ? 1 : (target < g_fear ? -1 : 0));
    if (g_fear < 0) g_fear = 0;
    if (g_fear > 256) g_fear = 256;
    // heartbeat
    if (g_fear > 70) {
        if (--s_heartT <= 0) {
            snd_play(SND_HEARTBEAT, 60 + g_fear / 2, 0, 0, 100);
            s_heartT = 78 - g_fear / 4;
        }
    } else s_heartT = 10;
}

static void update_fx(void) {
    FxState *f = &g_fx;
    f->vignette = 256 - g_fear * 3 / 5;
    f->vigDark = 3 + g_fear / 26;
    if (f->vigDark > 13) f->vigDark = 13;
    s32 wave = g_fear > 150 ? (g_fear - 150) / 3 : 0;
    if (g_cr.state == CR_KILL) wave = 80;
    f->wave = wave;
    f->wavePhase += 1300;
    // shake
    if (g_shakeT > 0) {
        g_shakeT--;
        s32 a = g_shakeAmt * 256;
        f->offX = (s32)(rng_next() % (2 * a + 1)) - a;
        f->offY = (s32)(rng_next() % (2 * a + 1)) - a;
    } else { f->offX = f->offY = 0; }
    // lightning
    if (g_flashT > 0) {
        g_flashT--;
        g_ambientBoost = g_flashT > 4 ? 14 : 0;
        f->white = g_flashT > 6 ? 8 : (g_flashT & 1) * 4;
    } else { g_ambientBoost = 0; f->white = 0; }
    // scripted fades
    if (g_fadeSpeed) {
        if (++g_fadeAcc >= g_fadeSpeed) {
            g_fadeAcc = 0;
            if (f->fade < g_fadeTarget) f->fade++;
            else if (f->fade > g_fadeTarget) f->fade--;
        }
    }
    if (g_blackoutT > 0) g_blackoutT--;
}

void game_update(void) {
    extern volatile u16 g_keyPressAcc;
    u16 keys = ~REG_KEYINPUT & KEY_MASK;
    REG_IME = 0;
    u16 pressed = g_keyPressAcc;
    g_keyPressAcc = 0;
    REG_IME = 1;
#ifdef DEV
    if (g_dbgFreeze) { debug_hook(); return; }     // test harness: the world stands still
#endif
    g_frame++;
    g_state.playFrames++;
    DEV_ONLY(debug_hook();)

    // scripted camera look
    if (g_lookX >= 0) {
        u16 want = angle_to(((g_lookX << 16) + 0x8000) - g_player.x, ((g_lookY << 16) + 0x8000) - g_player.y);
        s16 diff = (s16)(want - g_player.angle);
        g_player.angle += diff / 8;
    }
    DEV_ONLY(u32 q0 = PNOW();)
    player_update(keys, pressed);
    player_apply_flashlight();
    DEV_ONLY(u32 q1 = PNOW();)
    creature_update();
    DEV_ONLY(u32 q2 = PNOW();)
    pending_events();
    script_update();
    // a door never swings shut through someone standing in the doorway
    for (int i = 0; i < g_numDoors; i++) {
        Door *d = &g_doors[i];
        if (d->moving >= 0) continue;
        s32 mx = (d->x << 16) + (d->axis ? 0x8000 : 0), my = (d->y << 16) + (d->axis ? 0 : 0x8000);
        if (dist_approx(g_player.x - mx, g_player.y - my) < 0x9000 ||
            (g_cr.state != CR_OFF && dist_approx(g_cr.x - mx, g_cr.y - my) < 0xA000)) {
            d->moving = 1;
            g_state.doorState[i] |= DS_OPEN;
        }
    }
    world_update_doors();
    if (!g_player.hiding) check_triggers();
    map_track();
    DEV_ONLY(u32 q3 = PNOW();)
    update_fear();
    update_fx();
    hud_update();
    DEV_ONLY(u32 q4 = PNOW();)
    snd_update_3d(g_player.x, g_player.y, g_player.angle);
    DEV_ONLY(u32 q5 = PNOW(); g_profUpd[0] = q1 - q0; g_profUpd[1] = q2 - q1; g_profUpd[2] = q3 - q2; g_profUpd[3] = q4 - q3; g_profUpd[4] = q5 - q4;)
    // pause, unless this tick already ended the level or the player
    if ((pressed & KEY_START) && g_gameSignal == GS_PLAY) g_gameSignal = GS_PAUSE;
}

// ------------------------------------------------------------- render
void game_build_sprites(void) {
    int n = 0;
    s32 px = g_cam.x, py = g_cam.y;
    int glint = ((g_frame >> 3) & 15) == 0;
    for (int i = 0; i < g_numThings && n < MAX_SPRITES - 2; i++) {
        Thing *t = &g_things[i];
        if (t->flags & (THF_TAKEN | THF_HIDDEN)) continue;
        s32 dx = t->x - px, dy = t->y - py;
        if (dx > (20 << 16) || dx < -(20 << 16) || dy > (20 << 16) || dy < -(20 << 16)) continue;
        const ThingType *tt = &thing_types[t->type];
        RSprite *s = &g_sprites[n++];
        s->x = t->x; s->y = t->y;
        s->img = (glint && tt->glint && ((i + (g_frame >> 7)) & 1)) ? tt->glint : tt->img;
        s->worldW = tt->worldW; s->worldH = tt->worldH; s->zoff = tt->zoff + t->z;
        s->flags = (tt->flags & TT_FULLBRIGHT) ? SPR_FULLBRIGHT : 0;
        s->lightBoost = (tt->flags & TT_ITEM) ? 3 : 0;
    }
    if (creature_sprite(&g_sprites[n])) n++;
    g_numSprites = n;
}

void game_render(void) {
#ifdef DEV
    u32 t0 = PNOW();
    if (g_dbgFreeze) { g_frame = g_dbgFreeze; rng_seed(g_dbgFreeze); g_lightsDirty = 1; }  // test harness: repeatable frames
#endif
    g_cam.x = g_player.x; g_cam.y = g_player.y; g_cam.angle = g_player.angle;
    camera_update(&g_cam);
    world_update_lights(g_frame);
    DEV_ONLY(u32 t1 = PNOW();)
    creature_light();
    DEV_ONLY(u32 t2 = PNOW();)
    render_build_flash_tables();
    DEV_ONLY(u32 t3 = PNOW();)
    game_build_sprites();
    world_door_props();
    DEV_ONLY(u32 t4 = PNOW();)
    render_enter_3d();
    render_view(backbuf3d());
    DEV_ONLY(u32 t5 = PNOW();)
    fx_prepare();
    DEV_ONLY(u32 t6 = PNOW();
             g_profParts[0] = t1 - t0; g_profParts[1] = t2 - t1; g_profParts[2] = t3 - t2;
             g_profParts[3] = t4 - t3; g_profParts[4] = t6 - t5; g_profParts[5] = t5 - t4;)
}
