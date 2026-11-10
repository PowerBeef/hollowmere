// SPDX-License-Identifier: MIT
// The Night Sister: perception, pathfinding and behaviour
#include "game.h"
#include "world.h"
#include "flow.h"
#include "audio.h"
#include "assets.h"
#include "hud.h"
#include <string.h>

Creature g_cr;
s16 g_fear;

#define SPD_PATROL  1100
#define SPD_INVEST  1600
#define SPD_CHASE   2450
#define SPD_SEARCH  1300
#define SPD_SCRIPT  1000
#define CATCH_DIST  0xA000     // 0.625 tiles

EWRAM_BSS static u8  s_field[FLOW_CELLS];
EWRAM_BSS static u16 s_queue[FLOW_CELLS];
static Flow s_flow;
static int s_fieldTarget = -1;
static u8  s_fieldDoors;         // g_doorEpoch when the field was built
static u8 s_vis[9][9];
static int s_visTile = -1;
static u32 s_rngState = 99;

static u32 rnd(void) { s_rngState = s_rngState * 1103515245u + 12345u; return (s_rngState >> 16) & 0x7FFF; }

// ------------------------------------------------------------- pathing
// cells she can stand in: inside the house, not filled by furniture
static int cell_free(int cell) {
    return (g_cellFlags[cell] & (CELLF_INSIDE | CELLF_BLOCKED)) == CELLF_INSIDE;
}

// can she get through this edge? open, arch, or a door she is able to open
static int edge_ok(u8 e) {
    if (!e) return 1;
    const EdgeType *t = &g_edgeTypes[e];
    if (t->kind == EK_ARCH) return 1;
    if (t->kind != EK_DOOR) return 0;
    int i = t->param;
    Door *d = &g_doors[i];
    u8 ds = g_state.doorState[i];
    if (d->flags & DOORF_NOMONSTER) return 0;
    if (d->open > 0xC000) return 1;
    if (ds & DS_LOCKED) return 0;
    if (d->flags & DOORF_SCRIPTED) return 0;
    if (d->lock && !(ds & DS_UNLOCKED)) return 0;
    return 1;
}

static int step_ok(int c, int dir) {
    int x = c & 31, y = c >> 5;
    return edge_ok(world_edge_dir(x, y, dir));
}

// one step of the flow field (engine/src/flow.h): through an edge she can
// pass, into a cell she can stand in
static int field_step(int c, int dir) {
    static const s8 to[4] = { -MAP_W, 1, MAP_W, -1 };
    return step_ok(c, dir) && cell_free(c + to[dir]);
}

static void build_field(int target) {
    flow_begin(&s_flow, s_field, s_queue, world_inside(target & 31, target >> 5) ? target : -1);
    while (!flow_run(&s_flow, FLOW_CELLS, field_step)) { }
    s_fieldTarget = target;
    s_fieldDoors = g_doorEpoch;
}

static int cell_of(s32 x, s32 y) { return ((y >> 16) << 5) | (x >> 16); }

// pick the next waypoint toward the field target. Returns cell or -1.
static int next_cell(int c) {
    int x = c & 31, y = c >> 5;
    int best = -1, bd = s_field[c];
    // N E S W, then diagonals NW NE SW SE
    static const s8 dx8[8] = { 0, 1, 0, -1, -1, 1, -1, 1 }, dy8[8] = { -1, 0, 1, 0, -1, -1, 1, 1 };
    for (int k = 0; k < 8; k++) {
        int nx = x + dx8[k], ny = y + dy8[k];
        if ((unsigned)nx >= 32 || (unsigned)ny >= 32) continue;
        int n = (ny << 5) | nx;
        if (s_field[n] >= bd) continue;
        if (k < 4) { if (!step_ok(c, k)) continue; }
        else {
            // diagonal: both L-shaped routes must be open, with no door on them
            int a = (y << 5) | nx, b = (ny << 5) | x;
            int dh = dx8[k] > 0 ? 1 : 3, dv = dy8[k] > 0 ? 2 : 0;
            if (s_field[a] == 255 || s_field[b] == 255) continue;
            if (world_edge_dir(x, y, dh) || world_edge_dir(x, y, dv) ||
                world_edge_dir(nx, ny, dh ^ 2) || world_edge_dir(nx, ny, dv ^ 2)) continue;
        }
        if (s_field[n] < bd || best < 0) { bd = s_field[n]; best = n; }
    }
    return best;
}

// ------------------------------------------------------------- helpers
static void set_goal(s32 x, s32 y) {
    g_cr.goalX = x; g_cr.goalY = y;
    int t = cell_of(x, y);
    // (a door locked, unlocked or shut since the field was built changes the ways through)
    if (t != s_fieldTarget || s_fieldDoors != g_doorEpoch) { build_field(t); g_cr.pathAge = 0; }
}

static int pick_patrol_node(int far) {
    const LevelDef *L = g_level;
    if (!L->numPatrol) return -1;
    int best = -1; s32 bestD = far ? -1 : 0x7FFFFFFF;
    for (int tries = 0; tries < 8; tries++) {
        int i = rnd() % L->numPatrol;
        s32 nx = (L->patrol[i].x << 16) + 0x8000, ny = (L->patrol[i].y << 16) + 0x8000;
        s32 d = dist_approx(nx - g_player.x, ny - g_player.y);
        if (far) { if (d > bestD) { bestD = d; best = i; } }
        else {
            s32 dc = dist_approx(nx - g_cr.x, ny - g_cr.y);
            if (dc > 0x30000) { best = i; break; }
            best = i;
        }
    }
    return best;
}

static void face_toward(s32 dx, s32 dy, int rate) {
    u16 want = angle_to(dx, dy);
    s16 diff = (s16)(want - g_cr.angle);
    if (diff > rate) diff = rate;
    if (diff < -rate) diff = -rate;
    g_cr.angle += diff;
}

// ------------------------------------------------------------- lifecycle
void creature_init(int mode) {
    memset(&g_cr, 0, sizeof g_cr);
    g_cr.state = CR_OFF;
    g_cr.mode = mode;
    g_cr.breath = g_cr.lantern = -1;
    g_cr.cooldown = mode >= 1 ? 60 * 25 : 0;
    s_fieldTarget = -1;
    s_visTile = -1;
    s_rngState ^= g_frame * 2654435761u;
}

void creature_spawn(s32 x, s32 y, int state) {
    // never inside furniture: move to the nearest free cell
    int c0 = cell_of(x, y);
    if (!cell_free(c0) || world_point_blocked(x, y)) {
        int bx = x >> 16, by = y >> 16, best = -1, bd = 99;
        for (int dy = -2; dy <= 2; dy++)
            for (int dx = -2; dx <= 2; dx++) {
                int cx = bx + dx, cy = by + dy;
                if ((unsigned)cx >= 32 || (unsigned)cy >= 32) continue;
                int c = (cy << 5) | cx;
                int d = (dx < 0 ? -dx : dx) + (dy < 0 ? -dy : dy);
                if (cell_free(c) && d < bd && world_los(x, y, (cx << 16) + 0x8000, (cy << 16) + 0x8000)) { bd = d; best = c; }
            }
        if (best >= 0) { x = ((best & 31) << 16) + 0x8000; y = ((best >> 5) << 16) + 0x8000; }
    }
    g_cr.x = x; g_cr.y = y;
    g_cr.state = state;
    g_cr.goalX = x; g_cr.goalY = y;
    g_cr.alert = 0;
    g_cr.timer = 0;
    g_cr.lostTimer = 0;
    g_cr.knowsHiding = 0;
    g_cr.screamed = 0;
    g_cr.angle = angle_to(g_player.x - x, g_player.y - y);
    s_fieldTarget = -1;
    s_visTile = -1;
    if (g_cr.breath < 0 || !snd_active(g_cr.breath)) g_cr.breath = snd_play3d(SND_CBREATH, x, y, 120, 0, 140);
    if (state == CR_PATROL) g_cr.timer = 30;
    if (state == CR_PRAY) {
        g_cr.timer = 600; g_cr.prayTurn = 0;
        g_cr.prayX = x; g_cr.prayY = y;
        if (!g_cr.prayAngle) g_cr.prayAngle = 49152;
        g_cr.lookAngle = g_cr.prayAngle; g_cr.angle = g_cr.prayAngle;
    }
}

void creature_despawn(void) {
    g_cr.state = CR_OFF;
    if (g_cr.breath >= 0) { snd_fade(g_cr.breath, 6); g_cr.breath = -1; }
    g_cr.cooldown = g_cr.mode == 2 ? 60 * (14 + rnd() % 12) : 60 * (35 + rnd() % 25);
}

void creature_goto(s32 x, s32 y) {
    set_goal(x, y);
    g_cr.timer = 0;
}

void creature_hear(s32 x, s32 y, s32 radius) {
    if (g_cr.state == CR_OFF || g_cr.state == CR_SCRIPT || g_cr.state == CR_KILL) return;
    s32 d = dist_approx(x - g_cr.x, y - g_cr.y);
    if (!world_los(g_cr.x, g_cr.y, x, y)) radius = radius * 5 / 8;
    if (d > radius) return;
    if (g_cr.state == CR_CHASE) { g_cr.lastX = x; g_cr.lastY = y; g_cr.lostTimer = 0; return; }
    if (g_cr.state == CR_PRAY) {
        if (radius < (5 << 16)) return;
        g_cr.state = CR_INVESTIGATE;
    }
    // close loud noises trigger a chase immediately
    if (d < (4 << 16) && radius >= (6 << 16) && !g_player.hiding) {
        g_cr.state = CR_CHASE; g_cr.alert = 256; g_cr.lastX = x; g_cr.lastY = y; g_cr.lostTimer = 0;
        return;
    }
    g_cr.state = CR_INVESTIGATE;
    g_cr.timer = 0;
    set_goal(x, y);
}

// ------------------------------------------------------------- perception
static int perceive(void) {
    Player *p = &g_player;
    if (p->hiding && !g_cr.knowsHiding) { g_cr.hasLOS = 0; return 0; }
    s32 d = g_cr.dist;
    if (d > (18 << 16)) { g_cr.hasLOS = 0; return 0; }
    if ((g_frame & 1) == 0) g_cr.hasLOS = world_los(g_cr.x, g_cr.y, p->x, p->y);
    if (!g_cr.hasLOS) return 0;
    s16 diff = (s16)(angle_to(p->x - g_cr.x, p->y - g_cr.y) - g_cr.angle);
    if (diff < 0) diff = -diff;
    int inFront = diff < 13600;               // ~75 degrees
    int dt = d >> 12;                          // 1/16 tiles
    if (g_cr.state == CR_PRAY && !g_cr.prayTurn) {
        // kneeling with her back turned: only the glow of a lamp or a running step gives you away
        int r = (g_flashOn && dt < 12 * 16) ? 6 : 0;
        if (p->running && dt < 6 * 16) r += 12;
        return r;
    }
    int rate = 0;
    if (g_flashOn) {
        if (dt < 16 * 16) rate = inFront ? (16 * 16 - dt) / 10 : (dt < 5 * 16 ? 8 : 0);
        // the beam is pointed at her face
        s16 pd = (s16)(angle_to(g_cr.x - p->x, g_cr.y - p->y) - p->angle);
        if (pd < 0) pd = -pd;
        if (pd < 4000 && inFront) rate = rate * 2;
    } else {
        // in the dark she sees movement, not shapes: keep still and she may pass you by
        int still = p->speed < 400 && !p->running;
        if (still && dt >= 24) return 0;
        if (dt < 56 && inFront) rate = 18;
        else if (dt < 26) rate = 26;
        int gx = (p->x >> 15) & 63, gy = (p->y >> 15) & 63;
        int lit = g_lightgrid[(gy << 6) | gx] & LG_LIGHT;
        if (lit > 11 && dt < 9 * 16 && inFront) rate += (lit - 11) * 2;
    }
    if (p->running && dt < 6 * 16) rate += 10;
    if (dt < 16) rate = 256;
    if (g_cr.state == CR_SCRIPT) rate = 0;
    return rate;
}

// ------------------------------------------------------------- light
EWRAM_BSS static u16 s_litIdx[160];
EWRAM_BSS static u8  s_litFall[160];
static int s_litN, s_litKey = -1;
void creature_light(void) {
    if (g_cr.state == CR_OFF) return;
    int tx = g_cr.x >> 16, ty = g_cr.y >> 16;
    int tile = (ty << 5) | tx;
    int cx = g_cr.x >> 15, cy = g_cr.y >> 15;
    int key = (cy << 6) | cx;
    if (tile != s_visTile) {
        s_visTile = tile;
        s_litKey = -1;
        for (int j = -4; j <= 4; j++)
            for (int i = -4; i <= 4; i++) {
                int x = tx + i, y = ty + j;
                if ((unsigned)x >= 32 || (unsigned)y >= 32) { s_vis[j + 4][i + 4] = 0; continue; }
                s_vis[j + 4][i + 4] = world_inside(x, y) &&
                                      world_los(g_cr.x, g_cr.y, (x << 16) + 0x8000, (y << 16) + 0x8000);
            }
    }
    if (key != s_litKey) {
        // rebuild the list of lit light-grid cells around the lantern
        static const u8 fall[50] = {
            26,26,25,25,24,23,22,22,21,20,19,18,17,16,15,14,13,12,11,10,10,9,8,7,7,6,5,5,4,4,3,3,
            2,2,2,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0 };
        s_litKey = key;
        int n = 0;
        for (int j = -7; j <= 7; j++) {
            int gy = cy + j;
            if ((unsigned)gy >= 64) continue;
            for (int i = -7; i <= 7; i++) {
                int gx = cx + i;
                if ((unsigned)gx >= 64) continue;
                int d2 = i * i + j * j;
                if (d2 >= 50 || !fall[d2]) continue;
                int vt = (gx >> 1) - tx, vy = (gy >> 1) - ty;
                if (vt < -4 || vt > 4 || vy < -4 || vy > 4 || !s_vis[vy + 4][vt + 4]) continue;
                if (n < 160) { s_litIdx[n] = (gy << 6) | gx; s_litFall[n] = fall[d2]; n++; }
            }
        }
        s_litN = n;
    }
    int flick = 200 + (rng_next() & 55);
    if (g_cr.state == CR_KILL) flick = 256;
    world_light_guest(cx - 7, cy - 7, 15, 15);      // (the grid gets these cells back when she has moved on)
    u8 *grid = g_lightgrid;
    for (int k = 0; k < s_litN; k++) {
        u32 v = (s_litFall[k] * flick) >> 8;
        u8 *g = &grid[s_litIdx[k]];
        if (v > (u32)(*g & LG_LIGHT)) *g = (*g & ~LG_LIGHT) | v;
    }
}

// ------------------------------------------------------------- movement
static int move_toward_goal(s32 speed) {
    int c = cell_of(g_cr.x, g_cr.y);
    int goalCell = cell_of(g_cr.goalX, g_cr.goalY);
    s32 tx, ty;
    if (c == goalCell || s_field[c] == 255) {
        tx = g_cr.goalX; ty = g_cr.goalY;
        if (s_field[c] == 255 && c != goalCell) return 2;    // unreachable
    } else {
        int n = next_cell(c);
        if (n < 0) return 2;
        // a closed door between here and there: open it and wait
        int ddx = (n & 31) - (c & 31), ddy = (n >> 5) - (c >> 5);
        if (ddx == 0 || ddy == 0) {
            int dir = ddy < 0 ? 0 : ddx > 0 ? 1 : ddy > 0 ? 2 : 3;
            u8 e = world_edge_dir(c & 31, c >> 5, dir);
            Door *d = world_door_on(e);
            if (d && d->open < 0xC000) {
                // locked since she chose this way: not hers to open; she looks for another
                if (!edge_ok(e)) { build_field(goalCell); g_cr.moving = 0; return 0; }
                if (!d->moving) {
                    d->moving = 1;
                    g_state.doorState[d - g_doors] |= DS_OPEN;
                    s32 mx = (d->x << 16) + (d->axis ? 0x8000 : 0), my = (d->y << 16) + (d->axis ? 0 : 0x8000);
                    snd_play3d(SND_DOOR_OPEN, mx, my, 200, 3300, 130);
                }
                g_cr.moving = 0;
                face_toward(((n & 31) << 16) + 0x8000 - g_cr.x, ((n >> 5) << 16) + 0x8000 - g_cr.y, 1200);
                return 0;
            }
        }
        tx = ((n & 31) << 16) + 0x8000; ty = ((n >> 5) << 16) + 0x8000;
    }
    s32 dx = tx - g_cr.x, dy = ty - g_cr.y;
    s32 d = dist_approx(dx, dy);
    if (c == goalCell && d < 0x2000) { g_cr.moving = 0; return 1; }
    if (d < 1) return 1;
    s32 step = speed < d ? speed : d;
    g_cr.x += (s32)(((s64)dx * step) / d);
    g_cr.y += (s32)(((s64)dy * step) / d);
    g_cr.moving = 1;
    g_cr.anim += step;
    g_cr.strideAcc += step;
    face_toward(dx, dy, 1100);
    return 0;
}

static void footstep(void) {
    // one footfall per step of the animation: walk 0.375 tiles, chase 0.5
    s32 step = g_cr.state == CR_CHASE ? 0x8000 : 0x6000;
    if (g_cr.strideAcc < (u32)step) return;
    g_cr.strideAcc -= step;
    int vol = g_cr.state == CR_CHASE ? 255 : 190;
    if (!g_cr.hasLOS) vol = vol * 3 / 4;
    snd_play3d((rnd() & 3) ? SND_CSTEP0 : SND_CSTEP1, g_cr.x, g_cr.y, vol, 3600 + (rnd() & 1023), 130);
}

// ------------------------------------------------------------- update
static void to_chase(void) {
    if (g_cr.state != CR_CHASE) {
        if (!g_cr.screamed || g_cr.timer < -600) {
            snd_play3d(SND_CSCREAM, g_cr.x, g_cr.y, 255, 0, 250);
            g_cr.screamed = 1;
        }
        g_cr.state = CR_CHASE;
    }
    g_cr.lostTimer = 0;
    g_cr.lastX = g_player.x; g_cr.lastY = g_player.y;
}

void creature_update(void) {
    Player *p = &g_player;
    if (g_cr.state == CR_OFF) {
        // roaming modes: she comes back on patrol after a while (mode 3, at
        // prayer, is placed by the level's scripts and nowhere else)
        if ((g_cr.mode == 1 || g_cr.mode == 2) && g_level->numPatrol) {
            if (g_cr.cooldown > 0) g_cr.cooldown--;
            else {
                int n = pick_patrol_node(1);
                if (n >= 0) {
                    s32 x = (g_level->patrol[n].x << 16) + 0x8000, y = (g_level->patrol[n].y << 16) + 0x8000;
                    if (dist_approx(x - p->x, y - p->y) > (8 << 16) && !world_los(x, y, p->x, p->y))
                        creature_spawn(x, y, CR_PATROL);
                    else g_cr.cooldown = 120;
                }
            }
        }
        return;
    }
    g_cr.dist = dist_approx(g_cr.x - p->x, g_cr.y - p->y);
    if (g_cr.state == CR_KILL) { g_cr.moving = 0; return; }

    // perception -> alert (a script holding the player still for a scene
    // holds her too: she neither notices nor catches)
    int held = p->frozen;
    int rate = held ? 0 : perceive();
    if (rate) {
        g_cr.alert += rate;
        if (g_cr.alert > 300) g_cr.alert = 300;
    } else if (g_cr.alert > 0) {
        g_cr.alert -= 2;
    }
    if (g_cr.alert >= 256 && g_cr.state != CR_SCRIPT) to_chase();
    else if (rate && g_cr.alert > 110 && (g_cr.state == CR_PATROL || g_cr.state == CR_SEARCH || g_cr.state == CR_LEAVE || g_cr.state == CR_RETURN)) {
        // something caught her eye: turn and approach
        g_cr.state = CR_INVESTIGATE;
        g_cr.timer = 0;
        set_goal(p->x, p->y);
    }
    if (g_cr.state == CR_CHASE && g_cr.hasLOS && (!p->hiding || g_cr.knowsHiding)) {
        g_cr.lastX = p->x; g_cr.lastY = p->y; g_cr.lostTimer = 0;
    }

    g_cr.pathAge++;
    s32 speed = SPD_PATROL;
    switch (g_cr.state) {
    case CR_SCRIPT:
        speed = SPD_SCRIPT;
        if (move_toward_goal(speed)) g_cr.moving = 0;
        break;
    case CR_PATROL:
        if (g_cr.timer > 0) {
            g_cr.timer--; g_cr.moving = 0;
            if ((g_cr.timer & 63) == 0) g_cr.lookAngle = rnd() << 1;
            face_toward(lu_cos(g_cr.lookAngle), lu_sin(g_cr.lookAngle), 300);
            if (g_cr.timer == 0) {
                int n = pick_patrol_node(0);
                if (n >= 0) set_goal((g_level->patrol[n].x << 16) + 0x8000, (g_level->patrol[n].y << 16) + 0x8000);
            }
        } else if (move_toward_goal(SPD_PATROL)) {
            g_cr.timer = 90 + rnd() % 150;
        }
        break;
    case CR_INVESTIGATE:
        speed = SPD_INVEST;
        if (g_cr.timer > 0) {
            g_cr.moving = 0;
            if ((g_cr.timer & 31) == 0) g_cr.lookAngle = g_cr.angle + (rnd() & 0x7FFF) - 0x4000;
            face_toward(lu_cos(g_cr.lookAngle), lu_sin(g_cr.lookAngle), 500);
            if (--g_cr.timer == 0) {
                if (g_cr.mode == 3) { g_cr.state = CR_RETURN; set_goal(g_cr.prayX, g_cr.prayY); }
                else { g_cr.state = CR_PATROL; g_cr.timer = 1; }
            }
        } else {
            int r = move_toward_goal(speed);
            if (r) g_cr.timer = 150 + rnd() % 90;
        }
        break;
    case CR_CHASE: {
        speed = SPD_CHASE;
        g_cr.lostTimer++;
        if (g_cr.lostTimer < 80 && (!p->hiding || g_cr.knowsHiding)) set_goal(p->x, p->y);    // she still tracks you briefly
        else set_goal(g_cr.lastX, g_cr.lastY);
        int r = move_toward_goal(speed);
        if (g_cr.lostTimer > 80 && r) {
            g_cr.state = CR_SEARCH;
            g_cr.timer = 700;
            g_cr.alert = 120;
        }
        if (g_cr.lostTimer > 600) { g_cr.state = CR_SEARCH; g_cr.timer = 500; }
        // caught?
        if (!held && ((g_cr.dist < CATCH_DIST && (!p->hiding || g_cr.knowsHiding)) ||
                      (p->hiding && g_cr.knowsHiding && g_cr.dist < 0x10000))) {
            g_cr.state = CR_KILL;
            g_gameSignal = GS_DEAD;
        }
        break; }
    case CR_SEARCH:
        speed = SPD_SEARCH;
        if (--g_cr.timer <= 0) {
            if (g_cr.mode == 3) { g_cr.state = CR_RETURN; set_goal(g_cr.prayX, g_cr.prayY); }
            else if (g_cr.mode >= 1) { g_cr.state = CR_LEAVE; int n = pick_patrol_node(1); if (n >= 0) set_goal((g_level->patrol[n].x << 16) + 0x8000, (g_level->patrol[n].y << 16) + 0x8000); }
            else { g_cr.state = CR_PATROL; g_cr.timer = 1; }
            break;
        }
        if (g_cr.lookTimer > 0) {
            g_cr.lookTimer--; g_cr.moving = 0;
            face_toward(lu_cos(g_cr.lookAngle), lu_sin(g_cr.lookAngle), 400);
        } else if (move_toward_goal(speed)) {
            g_cr.lookTimer = 40 + rnd() % 60;
            g_cr.lookAngle = rnd() << 1;
            // wander near the last known position
            for (int k = 0; k < 6; k++) {
                int x = (g_cr.lastX >> 16) + (int)(rnd() % 9) - 4, y = (g_cr.lastY >> 16) + (int)(rnd() % 9) - 4;
                if ((unsigned)x < 32 && (unsigned)y < 32 && cell_free((y << 5) | x)) {
                    set_goal((x << 16) + 0x8000, (y << 16) + 0x8000);
                    break;
                }
            }
        }
        break;
    case CR_LEAVE:
        speed = SPD_SEARCH;
        if (move_toward_goal(speed) || (g_cr.dist > (11 << 16) && !g_cr.hasLOS)) creature_despawn();
        break;
    case CR_RETURN:
        set_goal(g_cr.prayX, g_cr.prayY);
        if (move_toward_goal(SPD_PATROL)) {
            g_cr.state = CR_PRAY;
            g_cr.timer = 500; g_cr.prayTurn = 0;
            g_cr.lookAngle = g_cr.prayAngle;
            g_cr.alert = 0;
        }
        break;
    case CR_PRAY:
        g_cr.moving = 0;
        if (held) break;                 // (her prayer waits out the scene too)
        if (!g_cr.prayTurn && g_cr.timer == 120) {
            snd_play3d(SND_WHISPER, g_cr.x, g_cr.y, 190, 3600, 120);   // she stirs before turning
            if (!script_flag(63)) { script_set_flag(63, 1); game_message(STR_M_STIRRING, 200); }
        }
        if (g_cr.timer > 0) g_cr.timer--;
        if (g_cr.timer == 0) {
            if (!g_cr.prayTurn) { g_cr.prayTurn = 1; g_cr.timer = 170; snd_play3d(SND_CSTEP1, g_cr.x, g_cr.y, 160, 3000, 130); }
            else { g_cr.prayTurn = 0; g_cr.timer = 480 + rnd() % 300; }
        }
        {
            u16 want = g_cr.prayTurn ? g_cr.lookAngle + 32768 : g_cr.lookAngle;
            s16 diff = (s16)(want - g_cr.angle);
            if (diff > 900) diff = 900;
            if (diff < -900) diff = -900;
            g_cr.angle += diff;
        }
        break;
    }
    if (g_cr.state == CR_CHASE && g_cr.timer > -2000) g_cr.timer--;
    footstep();

    // sound follows her
    if (g_cr.breath >= 0) {
        snd_set_pos(g_cr.breath, g_cr.x, g_cr.y);
        snd_set_vol(g_cr.breath, g_cr.state == CR_CHASE ? 210 : (g_cr.hasLOS ? 150 : 100), 0);
    }
}

// The Night Sister is drawn from one of 8 view angles (45 degrees apart,
// clockwise from in front of her) at one of 4 sizes picked by distance, so
// her texels stay about one per pixel (see game/content/sister).
#define CR_WORLD_H  351            // 1.37 tiles
#define CR_WORLD_W  175            // 112 texels wide
#define CR_WORLD_WW 251            // 160 texels wide (chase, attack)
#define CR_LIGHT_FLOOR 20
int creature_sprite(RSprite *s) {
    if (g_cr.state == CR_OFF) return 0;
    s->x = g_cr.x; s->y = g_cr.y;
    s->worldW = CR_WORLD_W; s->worldH = CR_WORLD_H; s->zoff = 0;
    // she carries her own light: never darker than her lantern makes her,
    // brighter in the flashlight
    s->flags = SPR_OWNLIGHT;
    s->lightBoost = CR_LIGHT_FLOOR;
    // which side of her the camera is on
    u16 diff = (u16)(angle_to(g_cam.x - g_cr.x, g_cam.y - g_cr.y) - g_cr.angle);
    int view = (u16)(diff + 4096) >> 13;
    int f;
    if (g_cr.state == CR_KILL) {
        f = CRF_ATTACK + (g_cr.frame < 9 ? 0 : g_cr.frame < 19 ? 1 : 2);
        s->worldW = CR_WORLD_WW;
    } else if (g_cr.state == CR_PRAY && !g_cr.prayTurn) {
        f = CRF_KNEEL + view;
    } else if (!g_cr.moving) {
        f = (g_cr.state == CR_INVESTIGATE || g_cr.state == CR_SEARCH ? CRF_SEARCH : CRF_IDLE) + view;
    } else if (g_cr.state == CR_CHASE) {
        f = CRF_CHASE + view * 8 + ((g_cr.anim >> 13) & 7);           // a tile a stride pair
        s->worldW = CR_WORLD_WW;
    } else {
        f = CRF_WALK + view * 8 + (g_cr.anim % 49152) / 6144;          // three quarters of a tile
    }
    // size: about one texel per pixel at this distance
    s32 d = dist_approx(g_cr.x - g_cam.x, g_cr.y - g_cam.y);
    int lv = d < 0x17800 ? 0 : d < 0x2F000 ? 1 : d < 0x5E000 ? 2 : 3;
    s->img = creature_frames[lv][f];
    return 1;
}
