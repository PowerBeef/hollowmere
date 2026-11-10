// SPDX-License-Identifier: MIT
// Flow field: the number of steps from every cell of the map to a target
// cell, by breadth-first search. An enemy walks downhill on it.
//
//   Flow f;  flow_begin(&f, dist, queue, target);
//   while (!flow_run(&f, 64, pass, door_ok)) ;     // or a slice of it per tick
//
// dist[cell] is 255 where the target cannot be reached (or the search has
// not got there yet). pass[cell] says where one can walk from a cell, a bit
// per direction (0 north, 1 east, 2 south, 3 west): bit dir set = always
// (the edge is open and the neighbour a cell to stand in), bit 4 + dir set =
// ask door_ok(cell, dir) (a door that may be locked just now). The map does
// not change, so a game works pass[] out once per level and a search costs
// a few instructions a step.
// Every cell enters the queue at most once, so a queue of MAP_W * MAP_H
// entries cannot overflow; pushes are bounded all the same.
#ifndef FLOW_H
#define FLOW_H
#include "engine.h"

#define FLOW_CELLS (MAP_W * MAP_H)
#define FLOW_FAR   255          // not reached
typedef struct {
    u8  *dist;                  // FLOW_CELLS entries
    u16 *queue;                 // FLOW_CELLS entries
    u16 head, tail;
    s16 target;                 // -1: nothing built
    u8  done;
} Flow;
typedef int (*FlowStep)(int cell, int dir);

static inline void flow_begin(Flow *f, u8 *dist, u16 *queue, int target) {
    f->dist = dist; f->queue = queue;
    for (int i = 0; i < FLOW_CELLS; i++) dist[i] = FLOW_FAR;
    f->head = f->tail = 0;
    f->target = target;
    f->done = 0;
    if ((unsigned)target >= FLOW_CELLS) { f->done = 1; return; }
    dist[target] = 0;
    queue[f->tail++] = target;
}

// expands up to `cells` cells; returns 1 when the field is complete
static inline int flow_run(Flow *f, int cells, const u8 *pass, FlowStep door_ok) {
    static const s8 to[4] = { -MAP_W, 1, MAP_W, -1 };
    u8 *dist = f->dist;
    u16 *queue = f->queue;
    unsigned head = f->head, tail = f->tail;
    while (head < tail && cells-- > 0) {
        int c = queue[head++];
        int d = dist[c] + 1;
        if (d >= FLOW_FAR) continue;                     // (farther than a byte counts)
        unsigned m = pass[c];
        int x = c & (MAP_W - 1), y = c >> MAP_SHIFT;
        if (y == 0) m &= ~0x11u;                         // (whatever pass[] says, not off the map)
        if (x == MAP_W - 1) m &= ~0x22u;
        if (y == MAP_H - 1) m &= ~0x44u;
        if (x == 0) m &= ~0x88u;
        for (int k = 0; k < 4 && m; k++, m >>= 1) {
            if (!(m & 0x11)) continue;
            int n = c + to[k];
            if (dist[n] != FLOW_FAR) continue;
            if (!(m & 1) && !door_ok(c, k)) continue;
            dist[n] = d;
            if (tail < FLOW_CELLS) queue[tail++] = n;
        }
    }
    f->head = head; f->tail = tail;
    if (head >= tail) f->done = 1;
    return f->done;
}

#endif
