#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Screenshots at chosen spots: shot.py OUTDIR LEVEL:X:Y:DEG[:name] ...  (full detail, 3x PNG)"""
import os
import sys
import paths
import harness
from PIL import Image


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    L = harness.boot() + harness.dismiss()
    level = 0
    names = []
    for i, a in enumerate(sys.argv[2:]):
        p = a.split(':')
        lv, x, y, d = int(p[0]), float(p[1]), float(p[2]), float(p[3])
        n = p[4] if len(p) > 4 else f"s{i}"
        if lv != level:
            L += harness.load_level(lv) + harness.dismiss()
            level = lv
        L += harness.teleport(x, y, d) + harness.dismiss(0) + harness.FULL_DETAIL + ["run 24", f"shot {out}/{n}.ppm"]
        names.append(n)
    harness.run(L, out, 'shot')
    for n in names:
        Image.open(f"{out}/{n}.ppm").resize((720, 480), Image.NEAREST).save(f"{out}/{n}.png")
    print(' '.join(f"{out}/{n}.png" for n in names))


if __name__ == '__main__':
    harness.main(main)
