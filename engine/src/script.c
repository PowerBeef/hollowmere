// SPDX-License-Identifier: MIT
// Level event scripts: a tiny bytecode VM with a few concurrent threads
#include "game.h"
#include "world.h"
#include "audio.h"
#include "assets.h"
#include "hud.h"
#include "fx.h"
#include "objects.h"

enum {
    OP_END = 0, OP_WAIT, OP_SOUND, OP_SOUND3D, OP_MSG, OP_OBJECTIVE, OP_DOOR, OP_LIGHT,
    OP_CREATURE, OP_SHAKE, OP_FLASH, OP_FLAG, OP_JNF, OP_JF, OP_JMP, OP_GIVE, OP_CHECKPOINT,
    OP_ENDLEVEL, OP_FEAR, OP_BLACKOUT, OP_MUSIC, OP_MUSICSTOP, OP_AMBIENCE, OP_THING, OP_ENDING,
    OP_INTER, OP_JNKEY, OP_FADE, OP_TELEPORT, OP_JFUSESLT, OP_PROP, OP_FREEZE, OP_LOOKAT,
    OP_NOTE, OP_START, OP_PLACEFUSES, OP_STOPSOUNDS, OP_JRAND, OP_CHAPTER, OP_HUDOFF, OP_JKEY
};

typedef struct { const u8 *base, *pc; s16 wait; u8 active, ev; } Thread;
_Static_assert(sizeof(Thread) == 12 && MAX_THREADS == 8, "Thread layout: update game/tests/hm.py");
EWRAM_BSS static Thread s_th[MAX_THREADS];

int  g_shakeAmt, g_shakeT;
int  g_flashT;
int  g_blackoutT;
int  g_fadeTarget = 0, g_fadeSpeed = 0, g_fadeAcc;
int  g_lookX = -1, g_lookY = -1;
int  g_ambience = -1;
int  g_noteRequest = -1;
int  g_chapterRequest = -1;

void script_reset(void) {
    for (int i = 0; i < MAX_THREADS; i++) s_th[i].active = 0;
    g_shakeAmt = g_shakeT = g_flashT = g_blackoutT = 0;
    g_fadeTarget = 0; g_fadeSpeed = 0;
    g_lookX = g_lookY = -1;
    g_noteRequest = -1;
    g_chapterRequest = -1;
}

int script_flag(int f) { return (g_state.flags[f >> 3] >> (f & 7)) & 1; }
void script_set_flag(int f, int v) {
    if (v) g_state.flags[f >> 3] |= 1 << (f & 7);
    else g_state.flags[f >> 3] &= ~(1 << (f & 7));
}

// Start an event on a free thread. Returns 0 when there is none (or no such
// event): the caller decides whether to try again later.
int script_start(int ev) {
    if (!g_level || ev <= 0 || ev >= g_level->numEvents) return 0;
    for (int i = 0; i < MAX_THREADS; i++)
        if (!s_th[i].active) {
            s_th[i].base = s_th[i].pc = g_level->events[ev];
            s_th[i].wait = 0;
            s_th[i].active = 1;
            s_th[i].ev = ev;
            return 1;
        }
    return 0;
}

int script_running(int ev) {
    for (int i = 0; i < MAX_THREADS; i++)
        if (s_th[i].active && s_th[i].ev == ev) return 1;
    return 0;
}

// The threads as a checkpoint keeps them, and back. (An event number or an
// offset that does not belong to this level leaves its thread empty.)
void script_save(ScriptSave *out) {
    for (int i = 0; i < MAX_THREADS; i++) {
        const Thread *t = &s_th[i];
        out->ev[i] = t->active ? t->ev : 0;
        out->pc[i] = t->active ? (u16)(t->pc - t->base) : 0;
        out->wait[i] = t->active ? t->wait : 0;
    }
}

void script_load(const ScriptSave *in) {
    for (int i = 0; i < MAX_THREADS; i++) {
        Thread *t = &s_th[i];
        int ev = in->ev[i];
        t->active = 0;
        if (!g_level || ev <= 0 || ev >= g_level->numEvents || in->pc[i] >= g_level->eventLen[ev]) continue;
        t->base = g_level->events[ev];
        t->pc = t->base + in->pc[i];
        t->wait = in->wait[i] < 0 ? 0 : in->wait[i];
        t->ev = ev;
        t->active = 1;
    }
}

static inline u16 rd16(const u8 *p) { return p[0] | (p[1] << 8); }
static inline s32 cellc(int c) { return (c << 16) + 0x8000; }

static void door_op(int idx, int op) {
    if (idx >= g_numDoors) return;
    Door *d = &g_doors[idx];
    switch (op) {
    case 0: d->moving = -1; g_state.doorState[idx] &= ~DS_OPEN; break;
    case 1: d->moving = 1; g_state.doorState[idx] |= DS_OPEN; break;
    case 2: g_state.doorState[idx] |= DS_LOCKED; break;
    case 3: g_state.doorState[idx] &= ~DS_LOCKED; g_state.doorState[idx] |= DS_UNLOCKED; break;
    case 4: d->open = 0; d->moving = 0; g_state.doorState[idx] &= ~DS_OPEN; break;
    }
    g_doorEpoch++;
}

static int run_one(Thread *t) {
    const u8 *p = t->pc;
    u8 op = *p++;
    switch (op) {
    case OP_END: t->active = 0; return 0;
    case OP_WAIT: t->wait = rd16(p); t->pc = p + 2; return 0;
    case OP_SOUND: {
        s8 semis = (s8)p[2];
        u16 pitch = semis ? note_pitch(72 + semis) : 0;
        snd_play(p[0], p[1], 0, pitch, 150); p += 3; break; }
    case OP_SOUND3D: snd_play3d(p[0], cellc(p[1]), cellc(p[2]), p[3], 0, 150); p += 4; break;
    case OP_MSG: game_message(rd16(p), rd16(p + 2)); p += 4; break;
    case OP_OBJECTIVE: game_set_objective(rd16(p)); p += 2; break;
    case OP_DOOR: door_op(p[0], p[1]); p += 2; break;
    case OP_LIGHT:
        for (int i = 0; i < g_numDLights; i++)
            if (g_dlights[i].def->group == p[0]) g_dlights[i].level = p[1] + (p[1] >> 7);
        g_lightsDirty = 1;
        if (p[0] < 16) g_state.lightLevel[p[0]] = p[1] >> 4;
        p += 2; break;
    case OP_CREATURE:
        switch (p[0]) {
        case 0: creature_despawn(); break;
        case 1: creature_spawn(cellc(p[1]), cellc(p[2]), CR_PATROL); break;
        case 2: creature_spawn(cellc(p[1]), cellc(p[2]), CR_SCRIPT); break;
        case 3: creature_goto(cellc(p[1]), cellc(p[2])); break;
        case 4: g_cr.mode = p[1]; g_state.creatureMode = p[1]; break;
        case 5: if (g_cr.state != CR_OFF) { g_cr.state = CR_CHASE; g_cr.alert = 256; g_cr.lostTimer = 0; } break;
        case 6: creature_spawn(cellc(p[1]), cellc(p[2]), CR_PRAY); break;
        case 7: if (g_cr.state != CR_OFF) creature_hear(cellc(p[1]), cellc(p[2]), 64 << 16); break;
        case 8: g_cr.angle = g_cr.lookAngle = g_cr.prayAngle = p[1] << 8; break;
        }
        p += 3; break;
    case OP_SHAKE: g_shakeAmt = p[0]; g_shakeT = p[1]; p += 2; break;
    case OP_FLASH: g_flashT = p[0]; p += 1; break;
    case OP_FLAG: script_set_flag(p[0], p[1]); p += 2; break;
    case OP_JNF: p = script_flag(p[0]) ? p + 3 : t->base + rd16(p + 1); break;
    case OP_JF: p = script_flag(p[0]) ? t->base + rd16(p + 1) : p + 3; break;
    case OP_JMP: p = t->base + rd16(p); break;
    case OP_GIVE:
        if (p[0] == 0) g_state.keys |= 1 << p[1];
        else if (p[0] == 1) g_state.fuses += p[1];
        else if (p[0] == 2) { g_state.battery += p[1] * 10000; if (g_state.battery > 1000000) g_state.battery = 1000000; }
        else if (p[0] == 3) g_state.keys &= ~(1 << p[1]);
        p += 2; break;
    case OP_CHECKPOINT: t->pc = p; game_checkpoint(); break;      // (kept as going on from after this step)
    case OP_ENDLEVEL: g_nextLevel = p[0]; g_gameSignal = GS_EXIT; t->pc = p + 1; t->active = 0; return 0;
    case OP_FEAR: g_fear += p[0]; if (g_fear > 256) g_fear = 256; p += 1; break;
    case OP_BLACKOUT: g_blackoutT = rd16(p); p += 2; break;
    case OP_MUSIC:
        if (p[0] == 0) music_play(mus_lullaby, MUS_LULLABY_LEN, SND_MUSICBOX, MUS_LULLABY_FRAMES, p[1]);
        else if (p[0] == 1) music_play(mus_fragment, MUS_FRAGMENT_LEN, SND_MUSICBOX, 0, p[1]);
        else if (p[0] == 2) music_play(mus_ending, MUS_ENDING_LEN, SND_PIANO, 0, p[1]);
        p += 2; break;
    case OP_MUSICSTOP: music_stop(); break;
    case OP_AMBIENCE:
        if (g_ambience >= 0) snd_fade(g_ambience, 4);
        g_ambience = p[1] ? snd_play(p[0], p[1], 0, 0, 255) : -1;
        p += 2; break;
    case OP_THING:
        if (p[0] < g_numThings) {
            if (p[1]) { g_things[p[0]].flags &= ~THF_HIDDEN; g_state.thingShown[p[0] >> 3] |= 1 << (p[0] & 7); }
            else g_things[p[0]].flags |= THF_HIDDEN;
        }
        p += 2; break;
    case OP_ENDING: g_gameSignal = GS_ENDING; t->active = 0; return 0;
    case OP_INTER: p += 2; break;
    case OP_JNKEY: p = (g_state.keys >> p[0]) & 1 ? p + 3 : t->base + rd16(p + 1); break;
    case OP_JKEY: p = (g_state.keys >> p[0]) & 1 ? t->base + rd16(p + 1) : p + 3; break;
    case OP_FADE: g_fadeTarget = p[0]; g_fadeSpeed = p[1]; p += 2; break;
    case OP_TELEPORT:
        g_player.x = cellc(p[0]); g_player.y = cellc(p[1]); g_player.angle = p[2] << 14;
        g_cam.x = g_player.x; g_cam.y = g_player.y; g_cam.angle = g_player.angle;
        p += 3; break;
    case OP_JFUSESLT: p = (g_state.fusesPlaced < p[0]) ? t->base + rd16(p + 1) : p + 3; break;
    case OP_PROP:
        if (p[0] < g_numProps) {
            if (p[1]) { g_props[p[0]].flags &= ~PIF_HIDDEN; g_state.propHidden[p[0] >> 3] &= ~(1 << (p[0] & 7)); }
            else { g_props[p[0]].flags |= PIF_HIDDEN; g_state.propHidden[p[0] >> 3] |= 1 << (p[0] & 7); }
            g_state.propSet[p[0] >> 3] |= 1 << (p[0] & 7);
        }
        p += 2; break;
    case OP_FREEZE: g_player.frozen = p[0]; p += 1; break;
    case OP_LOOKAT: g_lookX = p[0]; g_lookY = p[1]; if (p[0] == 255) g_lookX = -1; p += 2; break;
    case OP_NOTE: g_noteRequest = p[0]; p += 1; break;
    case OP_START: t->pc = p + 1; script_start(p[0]); return 1;
    case OP_PLACEFUSES: g_state.fusesPlaced += g_state.fuses; g_state.fuses = 0; break;
    case OP_STOPSOUNDS: snd_stop_all(); g_ambience = -1; break;
    case OP_JRAND: p = ((rng_next() & 255) < p[0]) ? t->base + rd16(p + 1) : p + 3; break;
    case OP_CHAPTER: g_chapterRequest = rd16(p); p += 2; break;
    case OP_HUDOFF: hud_set_visible(!p[0]); p += 1; break;
    default: t->active = 0; return 0;
    }
    t->pc = p;
    return 1;
}

void script_update(void) {
    for (int i = 0; i < MAX_THREADS; i++) {
        Thread *t = &s_th[i];
        if (!t->active) continue;
        if (t->wait > 0) { t->wait--; continue; }
        int guard = 64;
        while (t->active && t->wait == 0 && guard-- > 0) {
            if (!run_one(t)) break;
            if (g_noteRequest >= 0 || g_chapterRequest >= 0) break;
        }
    }
}
