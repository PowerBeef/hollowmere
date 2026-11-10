// SPDX-License-Identifier: MIT
// The smallest game the engine builds: a room, a closet behind a door, a key
// to pick up. Everything a game owes the engine (engine/src/game_api.h) is in
// this file: the hooks, the level set-up, a player and the frame loop.
//
//   make GAME=examples/minimal assets all        ->  build/minimal/minimal.gba
//
// D-pad: walk and turn. L/R: step sideways. A: open or close the door ahead.
#include "game_api.h"
#include "world.h"
#include "objects.h"
#include "audio.h"
#include "gfx.h"
#include "fx.h"
#include "hud.h"
#include "assets.h"         // generated from content/: the levels, STR_*, SND_*, THING_*
#include <string.h>

// ------------------------------------------------------------------ hooks
const GameInfo game_info = { 0x314E494Du, { 'M', 'I', 'N', 'S' } };     // "MIN1": saves are not used, but the tags are a game's own

static s32 s_x, s_y;        // the player, 16.16 tiles
static u16 s_angle;
static u8  s_frozen;
static u32 s_tick;
static u32 s_inside;        // triggers the player stood in at the last step

const char *game_str(int id) { return (id >= 0 && id < NUM_STRINGS) ? str_table[id] : ""; }
void game_message(int str, int frames) { hud_message(game_str(str), frames); }
void game_set_objective(int str) { g_state.objective = str; hud_text(HL_TOP, game_str(str), 300, HC_GOLD); }
void game_checkpoint(void) {}                                            // nothing is saved
int  game_state_valid(const SaveState *s) { (void)s; return 0; }
int  game_save_import(SaveState *out) { (void)out; return 0; }

void game_script(int what, int a, int b, int c) {
    switch (what) {
    case GSC_TELEPORT: s_x = (a << 16) + 0x8000; s_y = (b << 16) + 0x8000; s_angle = c << 14; break;
    case GSC_FREEZE: s_frozen = a; break;
    default: break;         // no enemy, one level, no ending: the other operations mean nothing here
    }
}

// One frame of the view: the camera, the lights, the things as sprites, the
// doors' leaves as props, then the renderer.
void game_render(void) {
    g_cam.x = s_x; g_cam.y = s_y; g_cam.angle = s_angle;
    camera_update(&g_cam);
    world_update_lights(s_tick);
    render_build_flash_tables();
    int n = 0;
    for (int i = 0; i < g_numThings && n < MAX_SPRITES - 2; i++) {
        const Thing *t = &g_things[i];
        if (t->flags & (THF_TAKEN | THF_HIDDEN)) continue;
        const ThingType *tt = &thing_types[t->type];
        RSprite *s = &g_sprites[n++];
        s->x = t->x; s->y = t->y; s->img = tt->img;
        s->worldW = tt->worldW; s->worldH = tt->worldH; s->zoff = tt->zoff + t->z;
        s->flags = 0; s->lightBoost = 3;
    }
    g_numSprites = n;
    world_door_props();
    render_enter_3d();
    render_view(backbuf3d());
    fx_prepare();
}

// ------------------------------------------------------------------ level
static void load_level(int index) {
    const LevelDef *L = level_table[index];
    memset(&g_state, 0, sizeof g_state);
    g_state.level = index;
    for (int i = 0; i < MAX_LIGHT_GROUPS; i++) g_state.lightLevel[i] = 16;
    world_load_level(L);
    g_numThings = L->numThings < MAX_THINGS ? L->numThings : MAX_THINGS;
    for (int i = 0; i < g_numThings; i++) {
        const ThingDef *d = &L->things[i];
        Thing *t = &g_things[i];
        t->x = d->x << 8; t->y = d->y << 8; t->z = d->z;
        t->type = d->type; t->param = d->param; t->event = d->event;
        t->flags = (d->flags & TDF_HIDDEN) ? THF_HIDDEN : 0;
    }
    script_reset();
    fx_reset();
    g_fx.mode3d = 1;
    g_fx.letterbox = 1;                 // the view's cinema bars
    hud_init();
    g_flashOn = 0;                      // no flashlight: the level's own lamps (LIGHTS) light it
    s_x = L->startX << 8; s_y = L->startY << 8; s_angle = L->startAngle;
    s_inside = 0;
    engine_frame_reset();
    if (L->startEvent) script_start(L->startEvent);
}

// ----------------------------------------------------------------- player
// the door within reach along the view, or 0
static Door *door_ahead(void) {
    s32 x = s_x, y = s_y, sx = lu_cos(s_angle) >> 2, sy = lu_sin(s_angle) >> 2;   // 1/16 tile steps
    int cx = x >> 16, cy = y >> 16;
    for (int i = 0; i < 20; i++) {
        x += sx; y += sy;
        int nx = x >> 16, ny = y >> 16;
        if (nx == cx && ny == cy) continue;
        u8 e = 0;
        if (nx != cx) e = world_edge(nx > cx ? nx : cx, cy, 0);
        if (!e && ny != cy) e = world_edge(nx, ny > cy ? ny : cy, 1);
        cx = nx; cy = ny;
        if (!e) continue;
        Door *d = world_door_on(e);
        if (d) return d;
        if (!world_edge_pass(e)) return 0;
    }
    return 0;
}

static void update(void) {
    u16 keys = ~REG_KEYINPUT & KEY_MASK, pressed = engine_keys_pressed();
    s_tick++;
    if (!s_frozen) {
        if (keys & KEY_LEFT) s_angle -= 500;
        if (keys & KEY_RIGHT) s_angle += 500;
        s32 fx = lu_cos(s_angle), fy = lu_sin(s_angle), dx = 0, dy = 0;       // Q14
        if (keys & KEY_UP) { dx += fx; dy += fy; }
        if (keys & KEY_DOWN) { dx -= fx; dy -= fy; }
        if (keys & KEY_R) { dx -= fy; dy += fx; }
        if (keys & KEY_L) { dx += fy; dy -= fx; }
        if (dx | dy) {
            world_move(&s_x, &s_y, dx / 9, dy / 9, 0x3400);                   // about 1.8 tiles a second; radius 0.2
            if ((s_tick & 31) == 0) snd_play(SND_STEP, 90, 0, 0, 50);
        }
        // the door ahead
        Door *d = door_ahead();
        if (d && !d->moving) {
            int idx = d - g_doors, open = d->open > 0x8000;
            hud_text(HL_PROMPT, game_str(open ? STR_CLOSE : STR_OPEN), 4, HC_WHITE);
            if (pressed & KEY_A) {
                if (!open && d->lock && !((g_state.keys >> d->lock) & 1)) game_message(STR_LOCKED, 120);
                else {
                    d->moving = open ? -1 : 1;
                    if (open) g_state.doorState[idx] &= ~DS_OPEN; else g_state.doorState[idx] |= DS_OPEN;
                    snd_play(SND_DOOR, 160, 0, 0, 100);
                }
            }
        }
        // things are taken by walking into them
        for (int i = 0; i < g_numThings; i++) {
            Thing *t = &g_things[i];
            if ((t->flags & (THF_TAKEN | THF_HIDDEN)) || dist_approx(t->x - s_x, t->y - s_y) > 0x6000) continue;
            t->flags |= THF_TAKEN;
            g_state.thingTaken[i >> 3] |= 1 << (i & 7);
            if (t->type == THING_KEY) g_state.keys |= 1 << t->param;
            script_start(t->event);
        }
    }
    // triggers: an event starts when the player walks into its cells
    int px = s_x >> 16, py = s_y >> 16;
    u32 inside = 0;
    for (int i = 0; i < g_level->numTrigs && i < MAX_TRIGGERS; i++) {
        const TriggerDef *t = &g_level->trigs[i];
        if (px < t->x0 || px > t->x1 || py < t->y0 || py > t->y1) continue;
        inside |= 1u << i;
        if ((s_inside >> i) & 1) continue;
        if ((t->flags & TRIGF_ONCE) && ((g_state.trigFired[i >> 3] >> (i & 7)) & 1)) continue;
        if (script_start(t->event)) g_state.trigFired[i >> 3] |= 1 << (i & 7);
    }
    s_inside = inside;
    script_update();
    world_update_doors();
    hud_update();
    snd_update_3d(s_x, s_y, s_angle);
}

int main(void) {
    engine_init();
    load_level(0);
    engine_ticks();
    for (;;) {
        engine_frame_start();
        for (int n = engine_ticks(); n > 0; n--) update();
        engine_frame();
    }
}
