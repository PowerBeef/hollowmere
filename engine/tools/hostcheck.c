// SPDX-License-Identifier: MIT
// Checks of the engine's pure functions, compiled for the build machine and
// run by engine/tools/hostcheck.py. Each check prints a line when it fails;
// the exit status is the number of failures.
#include <stdio.h>
#include "objects.h"
#include "flow.h"

static int failures;
#define CHECK(cond, ...) do { if (!(cond)) { failures++; printf("hostcheck: " __VA_ARGS__); printf("\n"); } } while (0)

// the faces of a prop sort by mean depth whatever their vertex count
static void sort_keys(void) {
    const s32 T = 0x10000;                     // one tile, 16.16
    for (s32 d = T / 4; d < 30 * T; d += T / 7) {
        s32 quad = face_sort_key(4 * d, 4), tri = face_sort_key(3 * d, 3);
        CHECK(quad - tri >= -1 && quad - tri <= 1, "a triangle and a quad at %d/65536 tiles get keys %d and %d", (int)d, (int)tri, (int)quad);
        s32 nearer = face_sort_key(3 * (d - T / 8), 3), farther = face_sort_key(3 * (d + T / 8), 3);
        CHECK(nearer < quad && quad < farther, "a triangle 1/8 tile nearer or farther than a quad at %d/65536 does not sort that way (%d, %d, %d)",
              (int)d, (int)nearer, (int)quad, (int)farther);
    }
    CHECK(face_sort_key(0x7FFFFFFF, 4) == 32767 && face_sort_key(-0x7FFFFFFF, 4) == -32768, "the key is not held to 16 bits");
}

// the flow field: every cell of an open 31 x 31 map reached (961 cells, more
// than the 512 the old byte queue held), at its true distance; a walled-off
// cell not reached; the search in slices gives the same field
static int open31(int cell, int dir) {
    static const int dx[4] = { 0, 1, 0, -1 }, dy[4] = { -1, 0, 1, 0 };
    int x = (cell & (MAP_W - 1)) + dx[dir], y = (cell >> MAP_SHIFT) + dy[dir];
    if (x < 0 || y < 0 || x > 30 || y > 30) return 0;                       // the map's edge
    if (x == 20 && y == 20) return 0;                                       // a pillar
    return 1;
}
static void flow_fields(void) {
    static u8 dist[FLOW_CELLS], sliced[FLOW_CELLS];
    static u16 queue[FLOW_CELLS + 8];
    for (int i = 0; i < 8; i++) queue[FLOW_CELLS + i] = 0xBEEF;
    Flow f;
    int target = (15 << MAP_SHIFT) | 15, steps = 0;
    flow_begin(&f, dist, queue, target);
    while (!flow_run(&f, FLOW_CELLS, open31)) steps++;
    CHECK(steps == 0, "a whole-map budget did not finish the field in one call");
    int reached = 0, wrong = 0;
    for (int y = 0; y < MAP_H; y++)
        for (int x = 0; x < MAP_W; x++) {
            int d = dist[(y << MAP_SHIFT) | x];
            int in = x <= 30 && y <= 30 && !(x == 20 && y == 20);
            int want = (x > 15 ? x - 15 : 15 - x) + (y > 15 ? y - 15 : 15 - y);
            if (in) { reached += d != FLOW_FAR; wrong += d != want; }
            else CHECK(d == FLOW_FAR, "cell (%d, %d) outside the map has distance %d", x, y, d);
        }
    CHECK(reached == 960, "%d of 960 open cells reached", reached);
    CHECK(wrong == 0, "%d cells at the wrong distance", wrong);
    CHECK(f.tail <= FLOW_CELLS, "the queue ran to %d entries", f.tail);
    for (int i = 0; i < 8; i++) CHECK(queue[FLOW_CELLS + i] == 0xBEEF, "the search wrote past its queue");
    flow_begin(&f, sliced, queue, target);
    int calls = 1;
    while (!flow_run(&f, 50, open31)) calls++;
    int differ = 0;
    for (int i = 0; i < FLOW_CELLS; i++) differ += dist[i] != sliced[i];
    CHECK(differ == 0 && calls >= 19, "the search in slices of 50 cells took %d calls and differs in %d cells", calls, differ);
    flow_begin(&f, dist, queue, -1);
    CHECK(f.done && dist[target] == FLOW_FAR, "a target off the map is not an empty field");
}

int main(void) {
    sort_keys();
    flow_fields();
    if (!failures) printf("hostcheck: OK\n");
    return failures;
}
