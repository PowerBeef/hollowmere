#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Deterministic screenshots for A/B renderer comparisons:
abshot.py ROM ELF OUTDIR [--only a,b] [poke lines with @ for spaces...]
The game logic is frozen (g_dbgFreeze) after each level loads, so each view
is a pure function of the level's start state, the camera and the knobs.
Views: the game's benchmark views, or ABVIEWS="level,name,x,y,deg;..."."""
import os
import sys
import paths
import harness
from views import VIEWS


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    views = VIEWS
    if os.environ.get('ABVIEWS'):
        views = [(int(a), b, float(c), float(d), float(e)) for a, b, c, d, e in
                 (v.split(',') for v in os.environ['ABVIEWS'].split(';'))]
    rom, elf, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
    a = sys.argv[4:]
    only = None
    if '--only' in a:
        i = a.index('--only'); only = a[i + 1].split(','); a = a[:i] + a[i + 2:]
    extra = [e.replace('@', ' ') for e in a]
    L = harness.boot() + harness.dismiss()
    level = -1
    for lv, n, x, y, d in views:
        if only and n not in only: continue
        if lv != level:
            L += ["poke32 {g_dbgFreeze} 0", "run 4"] + harness.load_level(lv) + harness.dismiss() + ["poke32 {g_dbgFreeze} 4000", "run 4"]
            level = lv
        L += harness.teleport(x, y, d, settle=0) + harness.FULL_DETAIL + ["poke32 {g_profNoIrq} 0"] + extra + ["run 12", f"shot {out}/{n}.ppm"]
    harness.run(L, out, 'ab', rom=rom, elf=elf)


if __name__ == '__main__':
    harness.main(main)
