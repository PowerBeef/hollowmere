// SPDX-License-Identifier: MIT
// Flow field: the number of steps from every cell of the map to a target
// cell, by breadth-first search. An enemy walks downhill on it.
//
//   Flow f;  flow_begin(&f, dist, queue, target);
//   while (!flow_run(&f, 64, can_step)) ;     // or a slice of it per tick
//
// dist[cell] is 255 where the target cannot be reached (or the search has
// not got there yet). can_step(cell, dir) says whether one can walk from
// cell to its neighbour in direction dir (0 north, 1 east, 2 south, 3 west):
// the edge between them is passable and the neighbour is a cell to stand in.
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
static inline int flow_run(Flow *f, int cells, FlowStep can_step) {
    while (f->head < f->tail && cells-- > 0) {
        int c = f->queue[f->head++];
        int d = f->dist[c] + 1;
        if (d >= FLOW_FAR) continue;                     // (farther than a byte counts)
        int x = c & (MAP_W - 1), y = c >> MAP_SHIFT;
        int nb[4] = { y > 0 ? c - MAP_W : -1, x < MAP_W - 1 ? c + 1 : -1, y < MAP_H - 1 ? c + MAP_W : -1, x > 0 ? c - 1 : -1 };
        for (int k = 0; k < 4; k++) {
            int n = nb[k];
            if (n < 0 || f->dist[n] != FLOW_FAR || !can_step(c, k)) continue;
            f->dist[n] = d;
            if (f->tail < FLOW_CELLS) f->queue[f->tail++] = n;
        }
    }
    if (f->head >= f->tail) f->done = 1;
    return f->done;
}

#endif
