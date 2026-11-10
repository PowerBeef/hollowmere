// SPDX-License-Identifier: MIT
// Player: movement, flashlight, stamina, interaction, hiding
#include "game.h"
#include "world.h"
#include "audio.h"
#include "assets.h"
#include "hud.h"
#include "fx.h"

Player g_player;
Target g_target;

#define RADIUS     0x3400      // 0.2 tiles
#define WALK_SPEED 1600        // tiles/frame 16.16 (~1.45 t/s, 2.2 m/s)
#define RUN_SPEED  2750        // ~2.5 t/s
#define BACK_SPEED 1150
#define STRAFE_SPEED 1300
#define TURN_MAX   470
#define STAMINA_MAX 320
#define RUN_NOISE  (5 << 16)   // how far a running step is heard (16.16 tiles)

extern int g_blackoutT;
extern int g_noteRequest;

// SELECT on the default controls: a tap works the light (on release), a
// hold opens the map
static u8 s_selHeld, s_selUsed;

void player_init(s32 x, s32 y, u16 angle) {
    Player *p = &g_player;
    s_selHeld = s_selUsed = 0;
    g_listenerMuffle = 256;
    p->x = x; p->y = y; p->angle = angle;
    p->turnVel = 0;
    p->stamina = STAMINA_MAX;
    p->running = p->exhausted = 0;
    p->hiding = 0;
    p->stride = 0; p->stepIdx = 0;
    p->frozen = 0;
    p->bob = 0; p->bobPhase = 0; p->speed = 0;
    p->breathHandle = -1;
    p->flickerT = 0;
    g_target.kind = TGT_NONE;
}

// ------------------------------------------------------------ helpers
static int thing_blocks(s32 x, s32 y, s32 r, s32 *pushX, s32 *pushY) {
    int hit = 0;
    for (int i = 0; i < g_numThings; i++) {
        Thing *t = &g_things[i];
        if (t->flags & (THF_TAKEN | THF_HIDDEN)) continue;
        if (!(thing_types[t->type].flags & TT_SOLID)) continue;
        s32 dx = x - t->x, dy = y - t->y;
        s32 rr = r + 0x4000;   // decor radius 0.25
        if (dx > rr || dx < -rr || dy > rr || dy < -rr) continue;
        s32 d = dist_approx(dx, dy);
        if (d < rr && d > 0) {
            s32 pen = rr - d;
            *pushX += (s32)(((s64)dx * pen) / d);
            *pushY += (s32)(((s64)dy * pen) / d);
            hit = 1;
        }
    }
    return hit;
}

static const char *key_name(int k) { return game_str(STR_KEY_BASE + k); }

// ------------------------------------------------------------ targeting
static void update_target(void) {
    Player *p = &g_player;
    g_target.kind = TGT_NONE;
    s32 dx = lu_cos(p->angle), dy = lu_sin(p->angle);
    // items in front
    s32 best = 0x16000;
    for (int i = 0; i < g_numThings; i++) {
        Thing *t = &g_things[i];
        if (t->flags & (THF_TAKEN | THF_HIDDEN)) continue;
        if (!(thing_types[t->type].flags & TT_ITEM)) continue;
        s32 ox = t->x - p->x, oy = t->y - p->y;
        if (ox > 0x18000 || ox < -0x18000 || oy > 0x18000 || oy < -0x18000) continue;
        s32 d = dist_approx(ox, oy);
        if (d > best || d < 1) continue;
        s32 dot = (s32)(((s64)ox * dx + (s64)oy * dy) >> 14);
        if (dot * 1000 < d * 840 && d > 0x6000) continue;   // ~33 deg cone (always if very close)
        if (!world_los(p->x, p->y, t->x, t->y)) continue;
        best = d;
        g_target.kind = TGT_THING; g_target.idx = i;
    }
    if (g_target.kind) return;
    // creature (finale: take the lantern)
    if (g_cr.state == CR_PRAY && g_cr.dist < 0xE000) {
        s32 ox = g_cr.x - p->x, oy = g_cr.y - p->y;
        s32 dot = (s32)(((s64)ox * dx + (s64)oy * dy) >> 14);
        if (dot * 1000 > g_cr.dist * 700) { g_target.kind = TGT_CREATURE; return; }
    }
    // fixtures (wardrobes, panels, exits...) in front, used from their facing side
    s32 bestI = 0x15000;
    int bi = -1;
    for (int k = 0; k < g_level->numInters; k++) {
        const InterDef *it = &g_level->inters[k];
        s32 ix = it->x << 8, iy = it->y << 8;
        s32 ox = ix - p->x, oy = iy - p->y;
        if (ox > 0x18000 || ox < -0x18000 || oy > 0x18000 || oy < -0x18000) continue;
        s32 d = dist_approx(ox, oy);
        if (d > bestI) continue;
        if (it->nx * -ox + it->ny * -oy <= 0) continue;               // behind it
        s32 dot = (s32)(((s64)ox * dx + (s64)oy * dy) >> 14);
        if (dot * 1000 < d * 760 && d > 0x5000) continue;
        if (!world_los(p->x, p->y, ix + it->nx * 64, iy + it->ny * 64)) continue;   // a step out from the wall
        bestI = d; bi = k;
    }
    // doors along the view ray (1.6 tiles)
    s32 x = p->x, y = p->y;
    s32 sx = dx >> 2, sy = dy >> 2;          // 1/16 tile steps (Q14 -> 16.16 /16)
    int cx = x >> 16, cy = y >> 16;
    for (int i = 0; i < 26; i++) {
        x += sx; y += sy;
        int nx = x >> 16, ny = y >> 16;
        if (nx == cx && ny == cy) continue;
        u8 e = 0;
        if (nx != cx) e = world_edge(nx > cx ? nx : cx, cy, 0);
        if (!e && ny != cy) e = world_edge(nx, ny > cy ? ny : cy, 1);
        cx = nx; cy = ny;
        if (!e) continue;
        Door *d = world_door_on(e);
        if (d) {
            s32 dd = (i + 1) << 12;
            if (bi >= 0 && bestI < dd) break;
            g_target.kind = TGT_DOOR; g_target.idx = d - g_doors; return;
        }
        if (!world_edge_pass(e)) break;
    }
    if (bi >= 0) { g_target.kind = TGT_INTER; g_target.idx = bi; }
}

static const char *prompt_text(void) {
    switch (g_target.kind) {
    case TGT_THING: {
        Thing *t = &g_things[g_target.idx];
        switch (t->type) {
        case THING_BATTERY: return game_str(STR_P_BATTERY);
        case THING_FUSE: return game_str(STR_P_FUSE);
        case THING_KEY: return game_str(STR_P_KEY);
        case THING_NOTE: return game_str(STR_P_NOTE);
        default: return game_str(STR_P_TAKE);
        }
    }
    case TGT_DOOR: {
        Door *d = &g_doors[g_target.idx];
        if (d->moving) return 0;
        return d->open > 0x8000 ? game_str(STR_P_CLOSE) : game_str(STR_P_OPEN);
    }
    case TGT_INTER: {
        const InterDef *it = &g_level->inters[g_target.idx];
        switch (it->type) {
        case INTER_LOCKER: return game_str(STR_P_HIDE);
        case INTER_FUSEBOX: return game_str(STR_P_FUSEBOX);
        case INTER_GENERATOR: return game_str(STR_P_GENERATOR);
        case INTER_EXIT: return game_str(STR_P_EXIT);
        case INTER_SIGN: return game_str(STR_P_EXAMINE);
        case INTER_EVENT: return game_str(STR_P_EXAMINE);
        }
        return 0;
    }
    case TGT_CREATURE: return game_str(STR_P_LANTERN);
    }
    return 0;
}

// ------------------------------------------------------------ hiding
static void hide_enter(int interIdx) {
    Player *p = &g_player;
    const InterDef *it = &g_level->inters[interIdx];
    p->outX = p->x; p->outY = p->y;
    p->outAngle = p->angle;
    p->hiding = 1;
    p->hideIdx = interIdx;
    // inside the wardrobe, looking out through the gap in its doors
    p->hideBaseAngle = (u16)(16384 + (it->hangle << 8));
    p->x = it->hx << 8;
    p->y = it->hy << 8;
    p->angle = p->hideBaseAngle;
    snd_play(SND_LOCKER_OPEN, 160, 0, 0, 120);
    game_noise(p->x, p->y, 4 << 16);
    // did she see us get in?
    g_cr.knowsHiding = (g_cr.state == CR_CHASE && g_cr.hasLOS) ? 1 : 0;
    g_listenerMuffle = 170;
    hud_clear(HL_PROMPT);
}

void player_hide_exit(void) {
    Player *p = &g_player;
    if (!p->hiding) return;
    p->hiding = 0;
    p->x = p->outX; p->y = p->outY;
    p->angle = p->outAngle;
    snd_play(SND_LOCKER_CLOSE, 150, 0, 0, 120);
    game_noise(p->x, p->y, 4 << 16);
    g_listenerMuffle = 256;
    g_fx.slits = 0;
}

// ------------------------------------------------------------ interact
static void interact(void) {
    Player *p = &g_player;
    switch (g_target.kind) {
    case TGT_THING: {
        int idx = g_target.idx;
        Thing *t = &g_things[idx];
        thing_take(idx);
        switch (t->type) {
        case THING_BATTERY:
            g_state.battery += 450000;
            if (g_state.battery > 1000000) g_state.battery = 1000000;
            snd_play(SND_PICKUP, 150, 0, 0, 160);
            game_message(STR_M_BATTERY, 150);
            hud_battery(g_state.battery / 1000, 180);
            break;
        case THING_FUSE:
            g_state.fuses++;
            snd_play(SND_PICKUP, 150, 0, 0, 160);
            game_message(g_state.fuses + g_state.fusesPlaced >= 3 ? STR_M_FUSE3 : (g_state.fuses + g_state.fusesPlaced == 2 ? STR_M_FUSE2 : STR_M_FUSE1), 160);
            break;
        case THING_KEY: {
            g_state.keys |= 1 << t->param;
            snd_play(SND_PICKUP, 150, 0, 0, 160);
            static char buf[48];
            const char *a = game_str(STR_M_TOOK), *b = key_name(t->param);
            int n = 0;
            while (*a && n < 40) buf[n++] = *a++;
            while (*b && n < 46) buf[n++] = *b++;
            buf[n++] = '.'; buf[n] = 0;
            hud_message(buf, 160);
            break; }
        case THING_NOTE:
            g_state.notesFound |= 1u << t->param;
            snd_play(SND_PAPER, 170, 0, 0, 160);
            g_noteRequest = t->param;
            break;
        default:
            snd_play(SND_PICKUP, 150, 0, 0, 160);
        }
        game_event(t->event);
        break; }
    case TGT_DOOR: {
        int idx = g_target.idx;
        Door *d = &g_doors[idx];
        if (d->moving) break;
        s32 dx = (d->x << 16) + (d->axis ? 0x8000 : 0), dy = (d->y << 16) + (d->axis ? 0 : 0x8000);
        if (d->open > 0x8000) {
            // don't close on anyone standing in its swing
            if (dist_approx(p->x - dx, p->y - dy) < 0x9000) break;
            if (g_cr.state != CR_OFF && dist_approx(g_cr.x - dx, g_cr.y - dy) < 0xA000) break;
            d->moving = -1;
            g_state.doorState[idx] &= ~DS_OPEN;
            snd_play3d(SND_DOOR_CLOSE, dx, dy, 170, 0, 120);
            game_noise(dx, dy, 5 << 16);
        } else {
            u8 ds = g_state.doorState[idx];
            if ((ds & DS_LOCKED) || (d->flags & DOORF_SCRIPTED)) {
                snd_play3d(SND_DOOR_LOCKED, dx, dy, 180, 0, 120);
                game_message(STR_M_STUCK, 120);
                game_noise(dx, dy, 3 << 16);
                break;
            }
            if (d->lock && !(ds & DS_UNLOCKED)) {
                if (g_state.keys & (1 << d->lock)) {
                    g_state.doorState[idx] |= DS_UNLOCKED;
                    g_doorEpoch++;
                    static char buf[56];
                    const char *a = game_str(STR_M_UNLOCKED), *b = key_name(d->lock);
                    int n = 0;
                    while (*a && n < 40) buf[n++] = *a++;
                    while (*b && n < 54) buf[n++] = *b++;
                    buf[n++] = '.'; buf[n] = 0;
                    hud_message(buf, 150);
                } else {
                    snd_play3d(SND_DOOR_LOCKED, dx, dy, 180, 0, 120);
                    game_message(STR_LOCKHINT_BASE + d->lock, 150);
                    game_noise(dx, dy, 3 << 16);
                    break;
                }
            }
            d->moving = 1;
            g_state.doorState[idx] |= DS_OPEN;
            snd_play3d(SND_DOOR_OPEN, dx, dy, 170, 3800 + (rng_next() & 511), 120);
            game_noise(dx, dy, 6 << 16);
        }
        break; }
    case TGT_INTER: {
        const InterDef *it = &g_level->inters[g_target.idx];
        switch (it->type) {
        case INTER_LOCKER: hide_enter(g_target.idx); break;
        case INTER_SIGN: game_message(it->param | (it->strHi << 8), 220); break;
        default: if (!script_running(it->param)) script_start(it->param); break;     // (not twice at once)
        }
        break; }
    case TGT_CREATURE:
        // the finale event follows the start event
        if (!script_running(g_level->startEvent + 1)) script_start(g_level->startEvent + 1);
        break;
    }
}

// ------------------------------------------------------------ flashlight
void player_apply_flashlight(void) {
    Player *p = &g_player;
    int on = g_state.flashOn && g_state.battery > 0 && g_blackoutT <= 0;
    s32 power = 256;
    u32 b = g_state.battery;
    if (b < 200000) power = 150 + (s32)(b * 106 / 200000);
    // flicker: low battery, or the creature's presence
    if (p->flickerT > 0) { p->flickerT--; if ((p->flickerT & 3) < 2) power = power / 5; }
    else {
        u32 r = rng_next();
        int chance = 0;
        if (b < 200000) chance += 2;
        if (b < 60000) chance += 6;
        if (g_cr.state != CR_OFF && g_cr.dist < (7 << 16)) chance += (7 << 16) / (g_cr.dist + 0x8000) * 2;
        if ((int)(r & 1023) < chance) p->flickerT = 6 + (r >> 12) % 18;
    }
    g_flashOn = on;
    g_flashPower = power;
}

// ------------------------------------------------------------ update
void player_update(u16 keys, u16 pressed) {
    Player *p = &g_player;
    const u16 K_RUN = g_settings.controls ? KEY_R : KEY_B;
    // the flashlight, and the map: SELECT opens it, or with SELECT on the
    // light, holding SELECT does (a tap still works the light, on release)
    int light = 0;
    if (g_settings.controls) {
        light = (pressed & KEY_B) != 0;
        if ((pressed & KEY_SELECT) && !p->frozen) g_gameSignal = GS_MAP;
    } else {
        // the press comes from the interrupt's accumulator: a tap shorter than
        // a logic step still counts
        if (pressed & KEY_SELECT) { s_selHeld = 1; s_selUsed = 0; }
        else if (s_selHeld && (keys & KEY_SELECT) && s_selHeld < 255) s_selHeld++;
        if (s_selHeld == 18 && !s_selUsed && !p->frozen) { g_gameSignal = GS_MAP; s_selUsed = 1; }
        if (s_selHeld && !(keys & KEY_SELECT)) {
            light = s_selHeld < 18 && !s_selUsed;
            s_selHeld = 0; s_selUsed = 0;
        }
    }

    if (light && !p->frozen) {
        if (g_state.battery > 0) {
            g_state.flashOn ^= 1;
            snd_play(SND_CLICK, 140, 0, 0, 200);
            hud_battery(g_state.battery / 1000, 120);
        } else {
            snd_play(SND_CLICK, 140, 0, 0, 200);
            game_message(STR_M_DEADBATT, 120);
        }
    }
    // battery drain
    if (g_state.flashOn && g_state.battery > 0) {
        u32 drain = 46;
        if (g_state.battery > drain) g_state.battery -= drain; else { g_state.battery = 0; g_state.flashOn = 0; game_message(STR_M_DEADBATT, 160); }
        if (g_state.battery < 150000 && (g_frame & 1023) == 0) hud_battery(g_state.battery / 1000, 120);
    }

    if (p->hiding) {
        // limited look around, exit with A or B
        s16 t = 0;
        if (keys & KEY_LEFT) t = -220;
        if (keys & KEY_RIGHT) t = 220;
        s32 a = (s16)(p->angle - p->hideBaseAngle) + t;
        if (a > 5500) a = 5500;
        if (a < -5500) a = -5500;
        p->angle = p->hideBaseAngle + a;
        g_fx.slits = 1;
        // out with A, or B where B is not the light
        if ((pressed & (g_settings.controls ? KEY_A : (KEY_A | KEY_B))) && !p->frozen) player_hide_exit();
        hud_text(HL_PROMPT, game_str(STR_P_LEAVE), 2, HC_GREY);
        return;
    }

    if (p->frozen) {
        p->speed = 0;
        p->turnVel = 0;
        hud_clear(HL_PROMPT);
        return;
    }

    // turning with a little acceleration
    s16 want = 0;
    int strafeL = 0, strafeR = 0;
    if (g_settings.controls) {
        if (keys & KEY_L) { if (keys & KEY_LEFT) strafeL = 1; if (keys & KEY_RIGHT) strafeR = 1; }
        else { if (keys & KEY_LEFT) want = -TURN_MAX; if (keys & KEY_RIGHT) want = TURN_MAX; }
    } else {
        if (keys & KEY_LEFT) want = -TURN_MAX;
        if (keys & KEY_RIGHT) want = TURN_MAX;
        strafeL = (keys & KEY_L) != 0; strafeR = (keys & KEY_R) != 0;
    }
    if (p->turnVel < want) { p->turnVel += 90; if (p->turnVel > want) p->turnVel = want; }
    if (p->turnVel > want) { p->turnVel -= 90; if (p->turnVel < want) p->turnVel = want; }
    p->angle += p->turnVel;

    s32 cx = lu_cos(p->angle), cy = lu_sin(p->angle);
    s32 mx = 0, my = 0;
    int fwd = (keys & KEY_UP) != 0, back = (keys & KEY_DOWN) != 0;
    int moving = fwd || back || strafeL || strafeR;
    p->running = fwd && (keys & K_RUN) && !p->exhausted && p->stamina > 0;
    s32 sp = p->running ? RUN_SPEED : WALK_SPEED;
    if (fwd) { mx += (cx * sp) >> 14; my += (cy * sp) >> 14; }
    if (back) { mx -= (cx * BACK_SPEED) >> 14; my -= (cy * BACK_SPEED) >> 14; }
    if (strafeL) { mx += (cy * STRAFE_SPEED) >> 14; my -= (cx * STRAFE_SPEED) >> 14; }
    if (strafeR) { mx -= (cy * STRAFE_SPEED) >> 14; my += (cx * STRAFE_SPEED) >> 14; }
    s32 ox = p->x, oy = p->y;
    world_move(&p->x, &p->y, mx, my, RADIUS);
    s32 px = 0, py = 0;
    if (thing_blocks(p->x, p->y, RADIUS, &px, &py)) world_move(&p->x, &p->y, px, py, RADIUS);
    s32 moved = dist_approx(p->x - ox, p->y - oy);
    p->speed = moved;

    // stamina
    if (p->running && moved > 1000) {
        p->stamina -= 1;
        if (p->stamina <= 0) {
            p->stamina = 0; p->exhausted = 1;
            if (p->breathHandle < 0 || !snd_active(p->breathHandle)) p->breathHandle = snd_play(SND_PBREATH, 130, 0, 0, 90);
        }
    } else {
        p->stamina += moving ? 1 : 2;
        if (p->stamina > STAMINA_MAX) p->stamina = STAMINA_MAX;
        if (p->exhausted && p->stamina > STAMINA_MAX / 2) {
            p->exhausted = 0;
            if (p->breathHandle >= 0) { snd_fade(p->breathHandle, 3); p->breathHandle = -1; }
        }
    }

    // footsteps, bob and noise
    if (moved > 400) {
        p->stride += moved;
        p->bobPhase += p->running ? moved * 2 / 3 : moved * 5 / 6;
        u32 strideLen = p->running ? 0xC000 : 0x9C00;
        if (p->stride >= strideLen) {
            p->stride -= strideLen;
            p->stepIdx++;
            int vol = p->running ? 120 : 62;
            snd_play(SND_STEP0 + (p->stepIdx % 3), vol, (p->stepIdx & 1) ? -20 : 20, 3900 + (rng_next() & 511), 60);
            // a running footfall carries: she hears it five tiles off, three
            // through a wall (walking is quiet)
            if (p->running) game_noise(p->x, p->y, RUN_NOISE);
        }
    }
    s32 amp = p->running ? 640 : 380;
    s32 target = moved > 400 ? (lu_sin((u16)(p->bobPhase * 2)) * amp) >> 14 : 0;
    p->bob += (target - p->bob) >> 2;
    g_fx.bobY = p->bob;

    // what's under the crosshair: every other tick is plenty
    if ((g_frame & 1) || (pressed & KEY_A)) {
        update_target();
        const char *pt = prompt_text();
        if (pt) hud_text(HL_PROMPT, pt, 4, HC_GREY); else hud_clear(HL_PROMPT);
    }
    if (pressed & KEY_A) interact();
}
