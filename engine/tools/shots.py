#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Screenshots from camera poses in the first level, with profile counters:
shots.py OUTDIR name x y deg [name x y deg ...]
Writes OUTDIR/sheet.png (a contact sheet, 2x) and prints a table: cycles for
the ray cast, floors and walls, the occluder pass and the objects, the whole
render, then props and faces drawn."""
import os
import sys
import paths
import harness
from PIL import Image, ImageDraw


def main():
    args = sys.argv[2:]
    if len(sys.argv) < 6 or len(args) % 4:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    poses = [(args[i], float(args[i + 1]), float(args[i + 2]), float(args[i + 3])) for i in range(0, len(args), 4)]
    L = harness.boot() + harness.dismiss()
    for n, x, y, d in poses:
        L += harness.teleport(x, y, d, settle=0) + ["run 40", f"shot {out}/{n}.ppm", f"echo {n}",
              "peek32 {g_profStage}", "peek32 {g_profStage+4}", "peek32 {g_profStage+8}", "peek32 {g_profStage+12}",
              "peek32 {g_profRaw}", "peek32 {g_objPub+4}", "peek32 {g_objPub+8}", "peek8 {g_quality}"]
    r = harness.run(L, out, 'shots')
    print(f"{'view':>10} {'cast':>7} {'fl+wl':>7} {'occ':>6} {'objs':>7} {'render':>7} {'props':>5} {'faces':>5} {'detail':>6}")
    for n, v in r.sections():
        if len(v) >= 8:
            print(f"{n:>10} {v[0]:7d} {v[1]:7d} {v[2]:6d} {v[3]:7d} {v[4]:7d} {v[5]:5d} {v[6]:5d} {v[7]:6d}")
    ims = [Image.open(f"{out}/{n}.ppm").resize((480, 320), Image.NEAREST) for n, *_ in poses]
    cols = 2 if len(ims) > 1 else 1
    sheet = Image.new('RGB', (480 * cols, 330 * ((len(ims) + cols - 1) // cols)), (40, 40, 40))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * 480, (i // cols) * 330))
        ImageDraw.Draw(sheet).text(((i % cols) * 480 + 4, (i // cols) * 330 + 2), poses[i][0], fill=(255, 255, 0))
    sheet.save(f"{out}/sheet.png")


if __name__ == '__main__':
    harness.main(main)
