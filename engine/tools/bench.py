#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixed-view benchmark: bench.py OUTDIR [--lod N] [--only name,name] [--split N] [--whalf N] [--hd TILES] [--band N] [--vhalf N]
Prints, for each of the game's benchmark views (tests/views.py), the cycles
each render stage takes with the world frozen and interrupts off, and writes
OUTDIR/bench.png. 20 fps is 3 vblanks: 842,688 cycles a frame, less the
interrupts and the game's update."""
import os
import sys
import paths
import harness
from PIL import Image, ImageDraw
from views import VIEWS

RUNF = int(os.environ.get("RUNF", "30"))


def script(views, lod=256, knobs=(), noirq=1):
    """The harness script visiting the views; echoes each view's name before its counters."""
    L = harness.boot() + harness.dismiss()
    level = 0
    for lv, n, x, y, d in views:
        if lv != level:
            L += harness.load_level(lv) + harness.dismiss()
            level = lv
        L += harness.teleport(x, y, d, settle=0)
        L += ["poke32 {g_govOff} 1", f"poke32 {{g_lodScale}} {lod}", f"poke32 {{g_profNoIrq}} {noirq}",
              "poke32 {g_floorSplit} 0", "poke32 {g_wallHalfLh} 0", f"poke32 {{g_halfDist}} {0x24000}",
              "poke32 {g_fullC0} 0", "poke32 {g_fullC1} 240", "poke32 {g_vhalf} 0"] + list(knobs)
        L += [f"run {RUNF}", f"shot {{out}}/{n}.ppm", f"echo {n}",
              "peek32 {g_profStage}", "peek32 {g_profStage+4}", "peek32 {g_profStage+8}", "peek32 {g_profStage+12}",
              "peek32 {g_profRaw}", "peek32 {g_profUpdate}", "peek32 {g_profIrq}",
              "peek32 {g_objPub+4}", "peek32 {g_objPub+8}", "peek32 {g_objPub+12}", "peek32 {g_lodScale}"]
    return L


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    lod, only, knobs = 256, None, []
    a = sys.argv[2:]
    while a:
        if a[0] == '--lod': lod = int(a[1])
        elif a[0] == '--only': only = a[1].split(',')
        elif a[0] == '--split': knobs.append(f"poke32 {{g_floorSplit}} {int(a[1])}")
        elif a[0] == '--whalf': knobs.append(f"poke32 {{g_wallHalfLh}} {int(a[1])}")
        elif a[0] == '--hd': knobs.append(f"poke32 {{g_halfDist}} {int(float(a[1]) * 65536)}")
        elif a[0] == '--band': knobs += [f"poke32 {{g_fullC0}} {120 - int(a[1])}", f"poke32 {{g_fullC1}} {120 + int(a[1])}"]
        elif a[0] == '--vhalf': knobs.append(f"poke32 {{g_vhalf}} {int(a[1])}")
        else: sys.exit(f"bench.py: unknown option {a[0]}\n{__doc__}")
        a = a[2:]
    views = [v for v in VIEWS if not only or v[1] in only]
    if not views:
        sys.exit("bench.py: no such view")
    L = [l.replace('{out}', out) for l in script(views, lod, knobs)]
    r = harness.run(L, out, 'bench', timeout=600)
    print(f"{'view':>10} {'cast':>6} {'fl+wl':>6} {'occ':>6} {'objs':>6} {'3d':>7} {'render':>7} {'update':>6} {'irq':>5} {'props':>5} {'faces':>5} {'cols':>5} {'lod':>4}")
    tot = [0] * 6
    k = 0
    for n, v in r.sections():
        if len(v) < 11: continue
        cast, flo, wal, objs, rend, upd, irq, props, faces, cols, lodv = v[:11]
        v3 = cast + flo + wal + objs
        for i, q in enumerate((cast, flo, wal, objs, v3, rend)): tot[i] += q
        k += 1
        print(f"{n:>10} {cast:6d} {flo:6d} {wal:6d} {objs:6d} {v3:7d} {rend:7d} {upd:6d} {irq:5d} {props:5d} {faces:5d} {cols:5d} {lodv:4d}")
    if k != len(views):
        print(f"bench.py: {len(views) - k} views gave no numbers", file=sys.stderr)
        return 1
    print(f"{'mean':>10} " + ' '.join(f"{t // k:6d}" for t in tot[:4]) + f" {tot[4] // k:7d} {tot[5] // k:7d}")
    ims = [(n, Image.open(f"{out}/{n}.ppm").resize((480, 320), Image.NEAREST)) for _, n, *_ in views]
    cols = 2
    sheet = Image.new('RGB', (480 * cols, 330 * ((len(ims) + 1) // 2)), (40, 40, 40))
    for i, (n, im) in enumerate(ims):
        sheet.paste(im, ((i % cols) * 480, (i // cols) * 330))
        ImageDraw.Draw(sheet).text(((i % cols) * 480 + 4, (i // cols) * 330 + 2), n, fill=(255, 255, 0))
    sheet.save(f"{out}/bench.png")


if __name__ == '__main__':
    harness.main(main)
