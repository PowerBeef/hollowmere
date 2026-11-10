// SPDX-License-Identifier: MIT
// Checks of the engine's pure functions, compiled for the build machine and
// run by engine/tools/hostcheck.py. Each check prints a line when it fails;
// the exit status is the number of failures.
#include <stdio.h>
#include "objects.h"

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

int main(void) {
    sort_keys();
    if (!failures) printf("hostcheck: OK\n");
    return failures;
}
