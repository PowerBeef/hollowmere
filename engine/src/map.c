// SPDX-License-Identifier: MIT
// The map screen, after the old survival-horror blueprints: the rooms of
// this floor you have been in, red while they still hold something to take
// and blue once they are cleared, the room you are in blinking, the doors
// (locked ones red, gold once you carry the key), the stairs out, and an
// arrow where you stand. Opened from the pause menu or with SELECT.
#include "game.h"
#include "gfx.h"
#include "ui.h"
#include "hud.h"
#include "audio.h"
#include "fx.h"
#include "assets.h"
#include "world.h"
#include <string.h>

// palette entries 1..23 while the map is up (the game palette comes back after)
enum {
    M_BG = 1, M_GRID, M_GRID2, M_FRAME, M_BLUE, M_BLUE_HI, M_RED, M_RED_HI, M_WALL,
    M_DOOR, M_LOCK, M_KEY, M_WIN, M_EXIT, M_SEAL, M_YOU, M_YOUSH, M_VOID,
    M_BLUE_LT, M_RED_LT, M_BLUE_HI_LT, M_RED_HI_LT, M_TEXT, M_COUNT
};
static const u16 s_pal[M_COUNT] = {
    0,
    RGB15(1, 2, 4),     RGB15(3, 4, 8),     RGB15(4, 6, 11),    RGB15(10, 12, 17),
    RGB15(4, 8, 17),    RGB15(8, 14, 26),   RGB15(15, 3, 3),    RGB15(25, 7, 6),
    RGB15(25, 28, 31),
    RGB15(29, 26, 18),  RGB15(31, 6, 5),    RGB15(31, 23, 3),   RGB15(12, 21, 29),
    RGB15(10, 27, 12),  RGB15(15, 15, 16),  RGB15(31, 31, 22),  RGB15(1, 1, 2),
    RGB15(6, 7, 11),
    RGB15(7, 12, 23),   RGB15(21, 6, 5),    RGB15(13, 20, 31),  RGB15(31, 13, 11),
    RGB15(22, 24, 28),
};

static const MapDef *mapdef(void) { return g_level ? g_level->map : 0; }

static int room_at(const MapDef *M, s32 x, s32 y) {
    int cx = (x >> 16) - M->x0, cy = (y >> 16) - M->y0;
    if (cx < 0 || cy < 0 || cx >= M->w || cy >= M->h) return 0xFF;
    return M->room[cy * M->w + cx];
}

static int seen(int r) { return r < 32 && ((g_state.roomsSeen[r >> 3] >> (r & 7)) & 1); }

// once a logic step: the room the player is in counts as seen
void map_track(void) {
    const MapDef *M = mapdef();
    if (!M) return;
    int r = room_at(M, g_player.x, g_player.y);
    if (r < 32) g_state.roomsSeen[r >> 3] |= 1 << (r & 7);
}

// ---------------------------------------------------------------- drawing
static void hl(int x, int y, int w, u8 c) { canvas_rect(x, y, w, 1, c); }
static void vl(int x, int y, int h, u8 c) { canvas_rect(x, y, 1, h, c); }

// filled triangle (pixel centres inside all three edges)
static void tri(s32 ax, s32 ay, s32 bx, s32 by, s32 cx, s32 cy, u8 c) {   // 8.8 fixed
    s32 x0 = ax, x1 = ax, y0 = ay, y1 = ay;
    if (bx < x0) x0 = bx;
    if (bx > x1) x1 = bx;
    if (cx < x0) x0 = cx;
    if (cx > x1) x1 = cx;
    if (by < y0) y0 = by;
    if (by > y1) y1 = by;
    if (cy < y0) y0 = cy;
    if (cy > y1) y1 = cy;
    s32 area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
    if (area == 0) return;
    for (int y = y0 >> 8; y <= (y1 >> 8); y++)
        for (int x = x0 >> 8; x <= (x1 >> 8); x++) {
            s32 px = (x << 8) + 128, py = (y << 8) + 128;
            s32 e0 = (bx - ax) * (py - ay) - (by - ay) * (px - ax);
            s32 e1 = (cx - bx) * (py - by) - (cy - by) * (px - bx);
            s32 e2 = (ax - cx) * (py - cy) - (ay - cy) * (px - cx);
            if (area > 0 ? (e0 >= 0 && e1 >= 0 && e2 >= 0) : (e0 <= 0 && e1 <= 0 && e2 <= 0))
                if ((unsigned)x < 240 && (unsigned)y < 160) g_canvas[y * 240 + x] = c;
        }
}

// an arrow centred on (cx, cy) pointing along angle, R from the centre to the tip (8.8)
static void arrow(s32 cx, s32 cy, u16 angle, s32 R, u8 col) {
    s32 c = lu_cos(angle), sn = lu_sin(angle);            // 1.14
    s32 tx = cx + ((c * R) >> 14), ty = cy + ((sn * R) >> 14);
    s32 bx = cx - ((c * R * 3 / 5) >> 14), by = cy - ((sn * R * 3 / 5) >> 14);
    s32 wx = (-sn * R * 7 / 10) >> 14, wy = (c * R * 7 / 10) >> 14;
    tri(tx, ty, bx + wx, by + wy, bx - wx, by - wy, col);
}

static int door_at(int x, int y, int axis) {
    for (int i = 0; i < g_level->numDoors; i++) {
        const DoorDef *d = &g_level->doors[i];
        if (d->x == x && d->y == y && d->axis == axis) return i;
    }
    return -1;
}

static u8 door_colour(int di) {
    if (di < 0) return M_DOOR;
    const DoorDef *d = &g_level->doors[di];
    u8 ds = g_state.doorState[di];
    int locked = (ds & DS_LOCKED) || ((d->flags & DOORF_SCRIPTED) && !(ds & DS_OPEN)) ||
                 (d->lock && !(ds & DS_UNLOCKED));
    if (!locked) return M_DOOR;
    if (d->lock && !(ds & DS_LOCKED) && (g_state.keys & (1 << d->lock))) return M_KEY;
    return M_LOCK;
}

typedef struct {
    const MapDef *M;
    int s, ox, oy;
    u32 vis;               // rooms drawn
    u32 items;             // rooms with something left to take
    int here;              // the player's room
} MapView;

static int cell_room(const MapView *v, int cx, int cy) {
    const MapDef *M = v->M;
    if (cx < 0 || cy < 0 || cx >= M->w || cy >= M->h) return 0xFF;
    return M->room[cy * M->w + cx];
}
static int cell_vis(const MapView *v, int cx, int cy) {
    int r = cell_room(v, cx, cy);
    return r < 32 && ((v->vis >> r) & 1);
}

// one edge: from (x, y) along +y (vertical) or +x (horizontal), s pixels;
// `out` is the side away from the house for the exit arrow
static void draw_edge(const MapView *v, int kind, int px, int py, int vert, int lx, int ly, int axis, int outSign) {
    int s = v->s;
    // the doorway: the middle of the edge
    int g0 = s / 4, g1 = s - s / 4;
    if (g1 - g0 < 3) { g0 = s / 2 - 1; g1 = g0 + 3; }
    #define SEG(a, b, c) do { if (vert) vl(px, py + (a), (b) - (a), c); else hl(px + (a), py, (b) - (a), c); } while (0)
    #define BAR(a, b, c) do { if (vert) canvas_rect(px - 1, py + (a), 3, (b) - (a), c); else canvas_rect(px + (a), py - 1, (b) - (a), 3, c); } while (0)
    switch (kind) {
    case MAPE_WALL:
        SEG(0, s + 1, M_WALL);
        break;
    case MAPE_WINDOW:
        // the plan's window: a pair of thin lines in the wall
        SEG(0, s + 1, M_WALL);
        BAR(g0, g1, M_WIN);
        SEG(g0, g1, M_BG);
        break;
    case MAPE_ARCH:
        SEG(0, s / 8 + 1, M_WALL);
        SEG(s - s / 8, s + 1, M_WALL);
        break;
    case MAPE_DOOR: {
        int di = door_at(lx, ly, axis);
        u8 c = door_colour(di);
        SEG(0, g0, M_WALL);
        SEG(g1, s + 1, M_WALL);
        BAR(g0, g1, c);
        break; }
    case MAPE_EXIT:
    case MAPE_SEALED: {
        u8 c = kind == MAPE_EXIT ? M_EXIT : M_SEAL;
        SEG(0, g0, M_WALL);
        SEG(g1, s + 1, M_WALL);
        BAR(g0, g1, c);
        if (kind == MAPE_EXIT) {
            // a chevron outside the house pointing away from it
            s32 m = ((g0 + g1) << 7);
            s32 d = outSign * (s < 10 ? 4 : 5) << 8;
            s32 w = (s < 10 ? 3 : 4) << 8;
            if (vert) tri((px << 8) + 128 + outSign * 768, (py << 8) + m - w, (px << 8) + 128 + outSign * 768, (py << 8) + m + w,
                          (px << 8) + 128 + outSign * 768 + d, (py << 8) + m, M_EXIT);
            else tri((px << 8) + m - w, (py << 8) + 128 + outSign * 768, (px << 8) + m + w, (py << 8) + 128 + outSign * 768,
                     (px << 8) + m, (py << 8) + 128 + outSign * 768 + d, M_EXIT);
        }
        break; }
    default:
        break;
    }
    #undef SEG
    #undef BAR
}

static void legend_box(int *x, int y, u8 fill, u8 edge, int strId) {
    canvas_rect(*x, y + 1, 7, 7, fill);
    canvas_frame(*x, y + 1, 7, 7, edge);
    *x = text_draw(*x + 10, y, game_str(strId), C_LGREY, 0) + 10;
}

static void draw_map(const MapView *v, int phase) {
    const MapDef *M = v->M;
    int s = v->s, ox = v->ox, oy = v->oy;
    canvas_clear(M_BG);
    // blueprint grid over the plan area
    int gx0 = 8, gx1 = 232, gy0 = 19, gy1 = 132;
    for (int x = ox % s; x < 240; x += s) if (x >= gx0 && x < gx1) vl(x, gy0, gy1 - gy0, ((x - ox) / s) % 4 ? M_GRID : M_GRID2);
    for (int y = oy - ((oy - gy0) / s) * s; y < gy1; y += s) if (y >= gy0) hl(gx0, y, gx1 - gx0, ((y - oy) / s) % 4 ? M_GRID : M_GRID2);
    // rooms
    for (int cy = 0; cy < M->h; cy++)
        for (int cx = 0; cx < M->w; cx++) {
            int r = cell_room(v, cx, cy);
            if (r >= 32 || !((v->vis >> r) & 1)) continue;
            int x = ox + cx * s, y = oy + cy * s;
            if (M->roomFlags[r] & MAPR_VOID) {
                // the drop: a dark hatch
                for (int j = 0; j < s; j++)
                    for (int i = 0; i < s; i++)
                        if (((x + i) + (y + j)) % 4 == 0) g_canvas[(y + j) * 240 + x + i] = M_VOID;
                continue;
            }
            int red = (v->items >> r) & 1, hi = r == v->here && phase;
            u8 fill = red ? (hi ? M_RED_HI : M_RED) : (hi ? M_BLUE_HI : M_BLUE);
            u8 lite = red ? (hi ? M_RED_HI_LT : M_RED_LT) : (hi ? M_BLUE_HI_LT : M_BLUE_LT);
            canvas_rect(x, y, s, s, fill);
            // a lighter rim inside the room's outline (top and left), for depth
            if (cell_room(v, cx, cy - 1) != r) hl(x + 1, y + 1, s - 1, lite);
            if (cell_room(v, cx - 1, cy) != r) vl(x + 1, y + 1, s - 1, lite);
        }
    // edges of the rooms that are drawn
    for (int ey = 0; ey <= M->h; ey++)
        for (int ex = 0; ex <= M->w; ex++) {
            u8 e = M->edge[ey * (M->w + 1) + ex];
            // west edge: cells (ex-1, ey) | (ex, ey)
            if (ey < M->h) {
                int a = cell_vis(v, ex - 1, ey), b = cell_vis(v, ex, ey);
                int k = e & 15;
                if ((a || b) && k != MAPE_OPEN) {
                    int out = cell_room(v, ex, ey) == 0xFF ? 1 : (cell_room(v, ex - 1, ey) == 0xFF ? -1 : (b ? -1 : 1));
                    draw_edge(v, k, ox + ex * s, oy + ey * s, 1, M->x0 + ex, M->y0 + ey, 0, out);
                }
            }
            if (ex < M->w) {
                int a = cell_vis(v, ex, ey - 1), b = cell_vis(v, ex, ey);
                int k = e >> 4;
                if ((a || b) && k != MAPE_OPEN) {
                    int out = cell_room(v, ex, ey) == 0xFF ? 1 : (cell_room(v, ex, ey - 1) == 0xFF ? -1 : (b ? -1 : 1));
                    draw_edge(v, k, ox + ex * s, oy + ey * s, 0, M->x0 + ex, M->y0 + ey, 1, out);
                }
            }
        }
    // you: an arrow with a dark rim, pulsing
    {
        s32 cx = (ox << 8) + (((g_player.x - (M->x0 << 16)) * s) >> 8);     // 8.8 px
        s32 cy = (oy << 8) + (((g_player.y - (M->y0 << 16)) * s) >> 8);
        s32 R = (s < 10 ? 4 : 5) << 8;
        arrow(cx, cy, g_player.angle, R + 384, M_YOUSH);
        arrow(cx, cy, g_player.angle, R, phase ? M_YOU : M_KEY);
    }
    // heading: the floor, and the room you are in
    text_draw(10, 4, M->floorName, C_RED, 0);
    if (v->here < 32) {
        const char *nm = M->roomName[v->here];
        text_draw(230 - text_width(nm), 4, nm, C_WHITE, 0);
    }
    hl(8, 16, 224, M_FRAME);
    // what to do next, under the plan
    if (g_state.objective) text_draw_center(134, game_str(g_state.objective), C_PAPER, 0);
    hl(8, 145, 224, M_FRAME);
    // legend
    {
        static const int ids[3] = { STR_MAP_ITEMS, STR_MAP_CLEAR, STR_MAP_LOCKED };
        int w = 0;
        for (int i = 0; i < 3; i++) w += 10 + text_width(game_str(ids[i])) + 10;
        w += 10 + text_width(game_str(STR_MAP_YOU));
        int x = 120 - w / 2, y = 149;
        legend_box(&x, y, M_RED, M_RED_LT, STR_MAP_ITEMS);
        legend_box(&x, y, M_BLUE, M_BLUE_LT, STR_MAP_CLEAR);
        canvas_rect(x, y + 3, 7, 3, M_LOCK);
        x = text_draw(x + 10, y, game_str(STR_MAP_LOCKED), C_LGREY, 0) + 10;
        tri((x << 8) + 128, (y + 1) << 8, (x << 8) + 128, (y + 8) << 8, (x + 7) << 8, ((y + 1) << 8) + 896, M_YOU);
        text_draw(x + 10, y, game_str(STR_MAP_YOU), C_LGREY, 0);
    }
}

void ui_map(void) {
    const MapDef *M = mapdef();
    if (!M) return;
    map_track();
    MapView v;
    v.M = M;
    v.s = 224 / M->w;
    if (113 / M->h < v.s) v.s = 113 / M->h;
    if (v.s > 14) v.s = 14;
    v.ox = 8 + (224 - v.s * M->w) / 2;
    v.oy = 19 + (113 - v.s * M->h) / 2;
    v.here = room_at(M, g_player.x, g_player.y);
    // rooms seen, and the drops beside them
    v.vis = 0;
    for (int r = 0; r < M->numRooms && r < 32; r++) if (seen(r)) v.vis |= 1u << r;
    for (int cy = 0; cy < M->h; cy++)
        for (int cx = 0; cx < M->w; cx++) {
            int r = M->room[cy * M->w + cx];
            if (r >= 32 || !(M->roomFlags[r] & MAPR_VOID) || ((v.vis >> r) & 1)) continue;
            u8 e = M->edge[cy * (M->w + 1) + cx], e2 = M->edge[(cy + 1) * (M->w + 1) + cx], e3 = M->edge[cy * (M->w + 1) + cx + 1];
            int n[4] = { cell_room(&v, cx, cy - 1), cell_room(&v, cx - 1, cy), cell_room(&v, cx, cy + 1), cell_room(&v, cx + 1, cy) };
            int open[4] = { (e >> 4) == MAPE_OPEN, (e & 15) == MAPE_OPEN, (e2 >> 4) == MAPE_OPEN, (e3 & 15) == MAPE_OPEN };
            for (int k = 0; k < 4; k++)
                if (open[k] && n[k] < 32 && n[k] != r && seen(n[k])) v.vis |= 1u << r;
        }
    // what is still to be found, room by room
    v.items = 0;
    for (int i = 0; i < g_numThings; i++) {
        const Thing *t = &g_things[i];
        if (t->flags & (THF_TAKEN | THF_HIDDEN)) continue;
        if (!(thing_types[t->type].flags & TT_ITEM)) continue;
        int r = room_at(M, t->x, t->y);
        if (r < 32) v.items |= 1u << r;
    }

    hud_set_visible(0); hud_update();
    snd_play(SND_PAPER, 90, 0, 4200, 120);
    // fade whatever is showing (the view keeps its cinema bars: the rows
    // outside them hold the renderer's tables)
    while (g_fx.fade < 16) { vsync(); g_fx.fade++; fx_prepare(); }
    g_fx.mode3d = 0;
    g_fx.vignette = 0; g_fx.wave = 0; g_fx.bobY = 0; g_fx.offX = g_fx.offY = 0; g_fx.slits = 0;
    g_fx.roll = 0; g_fx.mosaic = 0; g_fx.white = 0;
    pal_bg(s_pal, M_COUNT);
    int phase = 1;
    draw_map(&v, phase);
    canvas_present();
    ui_fade_in(1);
    ui_keys_pressed();
    for (int t = 0;; t++) {
        u16 p = ui_keys_pressed();
        if (p & (KEY_A | KEY_B | KEY_START | KEY_SELECT)) break;
        int ph = ((t >> 4) & 3) != 0;          // the room you are in: 3/4 lit, 1/4 dim
        if (ph != phase) { phase = ph; draw_map(&v, phase); canvas_present(); }
    }
    snd_play(SND_UI_BACK, 70, 0, 0, 100);
    ui_fade_out(1);
    pal_bg_game();
    hud_set_visible(1);
}
