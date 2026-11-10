#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Looks for pixels the renderer leaves undrawn, from every place the player
can stand: sweep.py OUTDIR [--every N] [--level L] [--views FILE] [--keep] [--rom ROM]

In every free quarter of every cell of every level (centre and four corners),
8 to 16 headings each, at three detail levels with the frame-rate governor
held: the 3D view is flooded with one colour, a frame is rendered, flooded
with another, rendered again. A pixel that differs between the two frames was
written by neither. --every N takes one view in N (the quick check); --level
limits it to one level; --views FILE to the view numbers in a JSON list;
--keep saves an image of every view with holes; --rom runs another test ROM
(its .elf beside it). Writes holes.json:
{level: {view number: [x, y, heading, {detail: pixels}]}}. Exits 1 when any
view has an undrawn pixel.

The view numbers of a level stay the same as long as its map does."""
import importlib
import json
import os
import sys

import paths
import harness
import audit
import levelc
sys.path.insert(0, paths.CONTENT)
import furniture  # noqa: E402
from manifest import LEVELS  # noqa: E402

R = 0.22            # the player's collision radius, with a little room
DETAIL = {  # governor level: full band half-width, floor split, vertical halving, wall half height, half distance, LOD scale
    0: (120, 0, 0, 0, 0x2400, 256),
    4: (120, 35, 1, 192, 0x1400, 384),
    7: (0, 35, 1, 400, 0, 768),
}
P0, P1, LEN = 0x06000000 + 2400, 0x0600A000 + 2400, 128 * 240      # the view's rows of both pages


def knobs(q):
    band, split, vh, whalf, hd, lod = DETAIL[q]
    return ["poke32 {g_govOff} 1", f"poke32 {{g_lodScale}} {lod}", f"poke32 {{g_floorSplit}} {split}",
            f"poke32 {{g_wallHalfLh}} {whalf}", f"poke32 {{g_halfDist}} {hd << 4}", f"poke32 {{g_fullC0}} {120 - band}",
            f"poke32 {{g_fullC1}} {120 + band}", f"poke32 {{g_vhalf}} {vh}"]


def flood(c):
    return [f"fill {P0:#x} {LEN} {c}", f"fill {P1:#x} {LEN} {c}"]


def hole_check(name, image=None):
    """Script lines: count the pixels of the current view that no frame writes
    (reported by the harness as CMP name count x0 y0 x1 y1). The game must be
    frozen (g_dbgFreeze) so that both frames show the same thing."""
    return flood(247) + ["run 24", "snap"] + flood(225) + ["run 24", f"cmp {name}" + (f" {image}" if image else "")]


def parsed(level):
    """(the compiled layout of a level index: cells, collision boxes; the room letters that are only a drop)"""
    mod = importlib.import_module(LEVELS[level])
    models = {n: fn() for n, fn in furniture.MODELS.items()}
    ids = dict(wall=audit.Any(), flat=audit.Any(), ptex=audit.Any(), model={k: 0 for k in models}, thing=audit.Any())
    return levelc.parse(mod, ids, models), {r for r, d in mod.ROOMS.items() if d.get('map') == 'void'}


def standable(level):
    """A function (x, y) -> can the player stand there, for a level index."""
    L, void = parsed(level)

    def free(x, y):
        cx, cy = int(x), int(y)
        if not (0 <= cx < L.W and 0 <= cy < L.H) or L.cell[cy][cx] == ' ' or L.cell[cy][cx] in void:
            return False
        return not any(x0 - R < x < x1 + R and y0 - R < y < y1 + R for (x0, y0, x1, y1) in L.boxes)
    free.size = (L.W, L.H)
    return free


def views_of(level):
    """[(number, x, y, heading)] for a level index."""
    free = standable(level)
    W, H = free.size
    out = []
    for cy in range(H):
        for cx in range(W):
            for k, (ox, oy) in enumerate([(0.5, 0.5), (0.23, 0.23), (0.77, 0.77), (0.23, 0.77), (0.77, 0.23)]):
                x, y = cx + ox, cy + oy
                if not free(x, y):
                    continue
                angs = [i * 22.5 for i in range(16)] if k == 0 else [11.25 + i * 45 + (k - 1) * 3 for i in range(8)]
                out += [(x, y, a) for a in angs]
    return [(i, x, y, a) for i, (x, y, a) in enumerate(out)]


def sweep(level, views, out, keep=False, rom=None, elf=None):
    """{view number: [x, y, heading, {detail: undrawn pixels}]} for the views with holes."""
    S = harness.boot() + harness.dismiss()
    if level:
        S += harness.load_level(level)
    S += ["run 300"] + harness.dismiss() + ["run 600"] + harness.dismiss()      # let the opening lines pass
    S += ["poke32 {g_dbgFreeze} 4000", "run 2"]
    for i, x, y, a in views:
        for q in DETAIL:
            S += harness.teleport(x, y, a, settle=0) + knobs(q) + ["run 12"]
            S += hole_check(f"{i}_{q}", f"{out}/L{level}_{i}_{q}.ppm" if keep else None)
    kw = dict(rom=rom, elf=elf) if rom else {}
    r = harness.run(S, out, f"L{level}", timeout=7200, **kw)
    pos = {i: (x, y, a) for i, x, y, a in views}
    bad = {}
    for name, c in r.cmps().items():
        if c[0]:
            i, q = (int(v) for v in name.split('_'))
            bad.setdefault(i, [*pos[i], {}])[3][q] = c[0]
    return bad


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    os.makedirs(out, exist_ok=True)

    def opt(name, default=None):
        return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
    every = int(opt('--every', 1))
    only = opt('--level')
    pick = set(json.load(open(opt('--views')))) if opt('--views') else None
    total, nviews, result = 0, 0, {}
    for lv in range(len(LEVELS)):
        if only is not None and lv != int(only):
            continue
        views = views_of(lv)
        if pick is not None:
            views = [v for v in views if v[0] in pick]
        views = views[::every]
        rom = opt('--rom')
        bad = sweep(lv, views, out, keep='--keep' in sys.argv, rom=rom, elf=rom[:-4] + '.elf' if rom else None)
        result[lv] = bad
        nviews += len(views)
        total += len(bad)
        worst = max((max(v[3].values()) for v in bad.values()), default=0)
        print(f"level {lv}: {len(views)} views, {len(bad)} with undrawn pixels" + (f" (worst {worst} pixels)" if bad else ""))
        for i, (x, y, a, d) in sorted(bad.items())[:12]:
            print(f"   view {i}: ({x:.2f}, {y:.2f}) heading {a:g}: " + ', '.join(f"detail {q}: {n}" for q, n in sorted(d.items())))
    json.dump(result, open(os.path.join(out, 'holes.json'), 'w'), indent=1)
    print(f"sweep: {nviews} views x {len(DETAIL)} detail levels, {total} with undrawn pixels")
    return 1 if total else 0


if __name__ == '__main__':
    harness.main(main)
