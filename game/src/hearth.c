// SPDX-License-Identifier: MIT
// The hearths: fires the player lights with matches and puts out, and the
// Night Sister kneels to until they are cold.
//
// A hearth is a fireplace with the fixture ('hearth', group) in the level:
// group is the light group of the fire's light. Its state is that group's
// level in the save (HS_*), so a checkpoint keeps it with no field of its
// own, and a save from before there were fires reads as "laid, never lit".
// What shows of it follows from the state here: the fireplace's front
// (its instance texture), the brightness of its light, its sound.
#include "game.h"
#include "world.h"
#include "objects.h"
#include "audio.h"
#include "assets.h"

EWRAM_BSS Hearth g_hearths[MAX_HEARTHS];
EWRAM_BSS int g_numHearths;
EWRAM_BSS static int s_fireSnd; // the crackle of the fire nearest the player (-1: none; set when a level loads)
EWRAM_BSS static s8  s_fireAt;  // ... which hearth that is

#define NOTICE_BASE  150        // ticks a fire burns before she can notice it,
#define NOTICE_TILE  24         // and more for every tile she is away

// (a fireplace beyond the MAX_HEARTHS a level can have is no hearth: cold for good)
int hearth_state(int h) { return h < 0 ? HS_DEAD : g_state.lightLevel[g_hearths[h].group]; }

int hearth_of_inter(int inter) {
    for (int i = 0; i < g_numHearths; i++) if (g_hearths[i].inter == inter) return i;
    return -1;
}

int hearth_burning(void) {
    for (int i = 0; i < g_numHearths; i++) if (hearth_state(i) == HS_BURNING) return 1;
    return 0;
}

// Its looks for the state it is in and how bright it is now: the picture on
// the fireplace's front, how far it is lit by itself, its lights' level.
// Called when one of those changes, not every tick (with three hearths cold
// this module must cost next to nothing: it runs sixty times a second).
static void show(Hearth *h) {
    static const u8 flames[3] = { PT_FIRE_A, PT_FIRE_B, PT_FIRE_C };
    int st = g_state.lightLevel[h->group];
    PropInst *p = &g_props[h->prop];
    p->tex = h->glow > 90 ? flames[h->pic] : st == HS_DEAD ? PT_FIRE_DEAD : PT_FIRE_COLD;
    p->light = h->glow >> 5;                    // up to 8 levels over what falls on it
    for (int k = 0; k < 2; k++) {
        if (h->dl[k] == 0xFF) continue;
        DynLight *d = &g_dlights[h->dl[k]];
        if (d->level != h->glow) { d->level = h->glow; g_lightsDirty = 1; }
    }
    h->shown = st;
}

void hearths_load(void) {
    g_numHearths = 0;
    s_fireSnd = -1; s_fireAt = -1;
    for (int k = 0; k < g_level->numInters && g_numHearths < MAX_HEARTHS; k++) {
        const InterDef *it = &g_level->inters[k];
        if (it->type != INTER_HEARTH || it->prop >= g_numProps || it->param >= MAX_LIGHT_GROUPS) continue;
        Hearth *h = &g_hearths[g_numHearths++];
        h->inter = k; h->prop = it->prop; h->group = it->param;
        h->x = it->x << 8; h->y = it->y << 8;
        h->sx = h->x + it->nx * 0x155; h->sy = h->y + it->ny * 0x155;      // a third of a tile further into the room (nx, ny: x64)
        u8 *st = &g_state.lightLevel[h->group];
        if (*st != HS_BURNING && *st != HS_DEAD) *st = HS_LAID;
        h->glow = *st == HS_BURNING ? 256 : 0;
        h->age = 0; h->ignored = 0; h->pic = 0;
        h->dl[0] = h->dl[1] = 0xFF;
        for (int i = 0, n = 0; i < g_numDLights && n < 2; i++)
            if (g_dlights[i].def->group == h->group) h->dl[n++] = i;
        show(h);
    }
}

void hearths_update(void) {
    int alight = 0;
    for (int i = 0; i < g_numHearths; i++) {
        Hearth *h = &g_hearths[i];
        int st = g_state.lightLevel[h->group];
        if (st != HS_BURNING && h->glow == 0) {             // cold: nothing of it moves
            if (h->shown != st) show(h);                    // (but she may have raked out what the player had put out)
            if (h->ignored && (g_frame & 63) == 0) h->ignored--;
            continue;
        }
        alight = 1;
        if (st == HS_BURNING && h->age < 60000) h->age++;
        if (h->ignored && (g_frame & 63) == 0) h->ignored--;
        int target = st == HS_BURNING ? 256 : 0;
        if ((g_frame & 3) == 0 && h->glow != target) {      // it takes in two thirds of a second, and sinks in twice that
            if (h->glow < target) { h->glow += 24; if (h->glow > target) h->glow = target; }
            else { h->glow -= 12; if (h->glow < target) h->glow = target; }
            show(h);
        } else if ((g_frame & 7) == 0) {                    // another picture of the flames, seven or eight times a second
            h->pic += 1 + (rng_next() & 1);
            if (h->pic >= 3) h->pic -= 3;
            show(h);
        }
    }
    // one voice for fire: the nearest that burns (looked at four times a second)
    if (!alight && s_fireAt < 0) return;
    if (g_frame & 15) return;
    int near = -1; s32 nd = 0x7FFFFFFF;
    for (int i = 0; i < g_numHearths; i++) {
        Hearth *h = &g_hearths[i];
        if (h->glow <= 0) continue;
        s32 d = dist_approx(h->x - g_player.x, h->y - g_player.y);
        if (d < nd) { nd = d; near = i; }
    }
    if (near != s_fireAt || (near >= 0 && !snd_active(s_fireSnd))) {
        if (s_fireSnd >= 0 && snd_active(s_fireSnd)) snd_fade(s_fireSnd, 6);
        s_fireSnd = near >= 0 ? snd_play3d(SND_FIRE, g_hearths[near].x, g_hearths[near].y, 150, 0, 110) : -1;
        s_fireAt = near;
    }
}

void hearth_use(int i) {
    if (i < 0) { game_message(STR_M_FIRE_DEAD, 170); return; }
    Hearth *h = &g_hearths[i];
    u8 *st = &g_state.lightLevel[h->group];
    if (*st == HS_BURNING) {
        *st = HS_LAID;                          // raked apart, not spent: it can be lit again
        snd_play3d(SND_FIRE_OUT, h->x, h->y, 170, 0, 130);
        game_message(STR_M_FIRE_OUT, 150);
    } else if (*st == HS_DEAD) {
        game_message(STR_M_FIRE_DEAD, 170);
    } else if (!((g_state.keys >> KEY_MATCHES) & 1)) {
        game_message(STR_M_FIRE_NOMATCH, 200);
    } else {
        *st = HS_BURNING;
        h->age = 0; h->ignored = 0;
        snd_play3d(SND_MATCH, h->x, h->y, 190, 0, 140);
        game_noise(h->x, h->y, 2 << 16);        // a match struck: she hears it from the next cell, no further
        game_message(STR_M_FIRE_LIT, 200);
    }
}

void hearth_smother(int i) {
    Hearth *h = &g_hearths[i];
    u8 *st = &g_state.lightLevel[h->group];
    if (*st == HS_BURNING || h->glow > 0) snd_play3d(SND_FIRE_OUT, h->x, h->y, 210, 0, 140);
    *st = HS_DEAD;
}

int hearth_calling(s32 x, s32 y) {
    int best = -1; s32 bd = 0x7FFFFFFF;
    for (int i = 0; i < g_numHearths; i++) {
        Hearth *h = &g_hearths[i];
        if (hearth_state(i) != HS_BURNING || h->ignored) continue;
        s32 d = dist_approx(h->x - x, h->y - y);
        if (h->age < NOTICE_BASE + (d >> 16) * NOTICE_TILE) continue;
        if (d < bd) { bd = d; best = i; }
    }
    return best;
}
