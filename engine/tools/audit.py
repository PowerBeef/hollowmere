#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Layout audit for Hollowmere's levels: furniture through walls, blocked
doors and door leaves swinging into furniture, pictures hidden behind
furniture, pieces overlapping each other, items floating or sunk.

    python3 engine/tools/audit.py [level ...]

Prints one line per finding. Nothing is changed."""
import importlib
import paths
import math
import os
import sys

import levelc
import furniture
import props as sprites

from manifest import LEVELS
SPRITE_K = 0.75                     # sprite sizes were drawn for the old, larger tile


class Any(dict):
    def __missing__(self, k):
        return 1

    def __contains__(self, k):
        return True


def footprint(p, m):
    """World xy bounding rectangle of all of a prop's vertices, and its height."""
    a = p.get('angle', 0) * 2 * math.pi / 256
    c, s = math.cos(a), math.sin(a)
    xs, ys, zs = [p['x']], [p['y']], [0.0]       # (a marker model has no vertices)
    for (x, y, z) in m.verts:
        x, y = x / 256, y / 256
        xs.append(p['x'] + x * c - y * s)
        ys.append(p['y'] + x * s + y * c)
        zs.append(z / 256)
    return (min(xs), min(ys), max(xs), max(ys)), max(zs)


def boxes(p, m):
    a = p.get('angle', 0) * 2 * math.pi / 256
    c, s = math.cos(a), math.sin(a)
    out = []
    for (x0, y0, x1, y1) in m.boxes:
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        w = [(p['x'] + px * c - py * s, p['y'] + px * s + py * c) for px, py in pts]
        out.append((min(q[0] for q in w), min(q[1] for q in w), max(q[0] for q in w), max(q[1] for q in w)))
    return out


def top_at(p, m, x, y):
    """Height of the highest upward face of a prop over (x, y), or None."""
    a = p.get('angle', 0) * 2 * math.pi / 256
    c, s = math.cos(a), math.sin(a)
    dx, dy = x - p['x'], y - p['y']
    lx, ly = dx * c + dy * s, -dx * s + dy * c
    best = None
    for f in m.faces:
        if f['n'][2] <= 40:
            continue
        P = [m.verts[i] for i in f['v']]
        xs = [q[0] / 256 for q in P]; ys = [q[1] / 256 for q in P]
        if min(xs) - 0.01 <= lx <= max(xs) + 0.01 and min(ys) - 0.01 <= ly <= max(ys) + 0.01:
            z = max(q[2] for q in P) / 256
            best = (best or []) + [z]
    return best


def overlap(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def audit(ln, models):
    mod = importlib.import_module(ln)
    ids = dict(wall=Any(), flat=Any(), ptex=Any(), model={k: 0 for k in models}, thing=Any())
    L = levelc.parse(mod, ids, models)
    out = []

    def say(kind, msg):
        out.append(f"{ln:10s} {kind:10s} {msg}")

    def room(x, y):
        if 0 <= int(y) < 32 and 0 <= int(x) < 32:
            return L.cell[int(y)][int(x)]
        return ' '

    def edge(x, y, o):
        return L.edge_info.get((x, y, o))

    # every wall segment as (x0, y0, x1, y1) with its kind, for crossings
    segs = []
    for (x, y, o), info in L.edge_info.items():
        if o == 'W':
            segs.append(((x, y, x, y + 1), info, (x, y, o)))
        else:
            segs.append(((x, y, x + 1, y), info, (x, y, o)))

    P = []
    for i, p in enumerate(L.props):
        m = models[p['model']]
        fp, h = footprint(p, m)
        P.append((i, p, m, fp, h, boxes(p, m)))

    # ---- furniture into walls (the full shape, not just its collision box)
    for i, p, m, fp, h, bx in P:
        x0, y0, x1, y1 = fp
        for (sx0, sy0, sx1, sy1), info, key in segs:
            if sx0 == sx1:          # vertical wall at x = sx0, y in [sy0, sy1]
                if y1 <= sy0 + 0.02 or y0 >= sy1 - 0.02:
                    continue
                pen = min(x1 - sx0, sx0 - x0)
                if pen > 0.035:
                    say('wall', f"{p['model']} at ({p['x']:.2f},{p['y']:.2f}) crosses the wall x={sx0} (y {sy0}-{sy1}) by {pen:.2f} [{info}]")
            else:
                if x1 <= sx0 + 0.02 or x0 >= sx1 - 0.02:
                    continue
                pen = min(y1 - sy0, sy0 - y0)
                if pen > 0.035:
                    say('wall', f"{p['model']} at ({p['x']:.2f},{p['y']:.2f}) crosses the wall y={sy0} (x {sx0}-{sx1}) by {pen:.2f} [{info}]")
        hi = [v for v in m.verts if v[2] / 256 > 1.9]
        flue = hi and max(math.hypot(v[0], v[1]) for v in hi) / 256 < 0.6 and \
            max(v[0] for v in hi) - min(v[0] for v in hi) < 0.3 * 256
        if h > 1.95 and not flue:
            say('ceiling', f"{p['model']} at ({p['x']:.2f},{p['y']:.2f}) is {h:.2f} tall (room 2.0)")

    # ---- doors and arches: the doorway itself, and where an open leaf stands
    for di, d in enumerate(L.doors):
        x, y, axis = d['x'], d['y'], d['axis']
        P_ = d['panel'] / 64
        n = 2 if d['double'] else 1
        span = 1 - 2 * P_
        ln_ = span / n
        swing_hi = d['hingebits'] & 1
        hinge_hi = (d['hingebits'] >> 1) & 1
        # doorway clearance: 0.45 deep either side
        if axis == 0:
            zone = (x - 0.45, y + P_, x + 0.45, y + 1 - P_)
        else:
            zone = (x + P_, y - 0.45, x + 1 - P_, y + 0.45)
        for i, p, m, fp, h, bx in P:
            if not m.solid:
                continue
            for b in bx:
                if overlap(b, zone) > 0.01:
                    say('doorway', f"{p['model']} at ({p['x']:.2f},{p['y']:.2f}) stands in the doorway of door {di} ({x},{y},{'W' if axis == 0 else 'N'})")
                    break
        # open leaves
        leaves = []
        for k in range(n):
            hi_end = k if n == 2 else hinge_hi
            along = 1 - P_ if hi_end else P_
            sgn = 1 if swing_hi else -1
            if axis == 0:
                hx, hy = x, y + along
                leaves.append((min(hx, hx + sgn * ln_), hy - 0.04, max(hx, hx + sgn * ln_), hy + 0.04))
            else:
                hx, hy = x + along, y
                leaves.append((hx - 0.04, min(hy, hy + sgn * ln_), hx + 0.04, max(hy, hy + sgn * ln_)))
        for i, p, m, fp, h, bx in P:
            for lf in leaves:
                if overlap(fp, lf) > 0.0005:
                    say('leaf', f"door {di} ({x},{y},{'W' if axis == 0 else 'N'}) opens into {p['model']} at ({p['x']:.2f},{p['y']:.2f})")
                    break
        for (dx_, dy_, side, kind) in getattr(mod, 'DECOR', []):
            pass
    for (x, y, o), info in L.edge_info.items():
        if isinstance(info, tuple) and info[0] == 'arch':
            P_ = info[1] / 64
            zone = (x - 0.4, y + P_, x + 0.4, y + 1 - P_) if o == 'W' else (x + P_, y - 0.4, x + 1 - P_, y + 0.4)
            for i, p, m, fp, h, bx in P:
                if m.solid and any(overlap(b, zone) > 0.01 for b in bx):
                    say('doorway', f"{p['model']} at ({p['x']:.2f},{p['y']:.2f}) stands in the arch at ({x},{y},{o})")

    # ---- pictures, mirrors, sconces hidden behind furniture
    for (cx, cy, side, kind) in getattr(mod, 'DECOR', []):
        # the wall segment and the strip of room in front of it
        if side == 'N':
            strip = (cx + 0.15, cy, cx + 0.85, cy + 0.45)
        elif side == 'S':
            strip = (cx + 0.15, cy + 0.55, cx + 0.85, cy + 1)
        elif side == 'W':
            strip = (cx, cy + 0.15, cx + 0.45, cy + 0.85)
        else:
            strip = (cx + 0.55, cy + 0.15, cx + 1, cy + 0.85)
        low = 0.95 if kind not in ('sconce', 'sconce_off', 'crucifix') else 1.15
        for i, p, m, fp, h, bx in P:
            if overlap(fp, strip) > 0.02 and h > low:
                say('decor', f"{kind} on {side} wall of ({cx},{cy}) is behind {p['model']} ({h:.2f} tall) at ({p['x']:.2f},{p['y']:.2f})")
    # decor on a wall that also has a door or window? (the edge texture wins)
    for (cx, cy, side, kind) in getattr(mod, 'DECOR', []):
        key = {'N': (cx, cy, 'N'), 'S': (cx, cy + 1, 'N'), 'W': (cx, cy, 'W'), 'E': (cx + 1, cy, 'W')}[side]
        info = L.edge_info.get(key)
        if info != 'wall':
            say('decor', f"{kind} on {side} wall of ({cx},{cy}) is on a {info} edge")

    # ---- furniture overlapping furniture
    for a in range(len(P)):
        for b in range(a + 1, len(P)):
            ia, pa, ma, fa, ha, ba = P[a]
            ib, pb, mb, fb_, hb, bb = P[b]
            if not (ma.solid and mb.solid):
                continue
            ov = sum(overlap(x, y) for x in ba for y in bb)
            if ov > 0.01:
                say('overlap', f"{pa['model']} at ({pa['x']:.2f},{pa['y']:.2f}) and {pb['model']} at ({pb['x']:.2f},{pb['y']:.2f}) overlap by {ov:.3f}")

    # ---- items: resting on something at the right height, or on the floor clear of furniture
    for t in L.things:
        x, y, z = t['x'], t['y'], t.get('z', 0) / (256 if t.get('z', 0) > 4 else 1)
        sp = sprites.PROPS.get(t['type'])
        under = []
        for i, p, m, fp, h, bx in P:
            if fp[0] - 0.02 <= x <= fp[2] + 0.02 and fp[1] - 0.02 <= y <= fp[3] + 0.02:
                tz = top_at(p, m, x, y)
                if tz is not None:
                    under += [(z_, p['model']) for z_ in tz]
        if z > 0.02:
            if not under:
                say('item', f"{t['type']} at ({x:.2f},{y:.2f}) z={z:.2f} floats: nothing under it")
            else:
                tz, nm = min(under, key=lambda u: abs(u[0] - z))
                if abs(tz - z) > 0.03:
                    say('item', f"{t['type']} at ({x:.2f},{y:.2f}) z={z:.2f} but the top of {nm} there is {tz:.2f}")
        else:
            for tz, nm in under:
                if tz > 0.12:
                    say('item', f"{t['type']} on the floor at ({x:.2f},{y:.2f}) is inside/under {nm} (top {tz:.2f})")
        # sprite crossing a wall
        if sp:
            r = sp['ww'] * SPRITE_K / 2
            for (sx0, sy0, sx1, sy1), info, key in segs:
                if sx0 == sx1 and sy0 <= y <= sy1 and abs(x - sx0) < r * 0.8:
                    say('item', f"{t['type']} at ({x:.2f},{y:.2f}) is {abs(x - sx0):.2f} from the wall x={sx0} (half width {r:.2f})")
                if sy0 == sy1 and sx0 <= x <= sx1 and abs(y - sy0) < r * 0.8:
                    say('item', f"{t['type']} at ({x:.2f},{y:.2f}) is {abs(y - sy0):.2f} from the wall y={sy0} (half width {r:.2f})")

    # ---- items or props straddling rooms; start position
    for i, p, m, fp, h, bx in P:
        rs = {room(fp[0] + 0.05, fp[1] + 0.05), room(fp[2] - 0.05, fp[1] + 0.05),
              room(fp[0] + 0.05, fp[3] - 0.05), room(fp[2] - 0.05, fp[3] - 0.05)}
        if ' ' in rs:
            say('outside', f"{p['model']} at ({p['x']:.2f},{p['y']:.2f}) pokes outside the house")
    sx, sy = L.start
    for i, p, m, fp, h, bx in P:
        if any(b[0] - 0.15 < sx < b[2] + 0.15 and b[1] - 0.15 < sy < b[3] + 0.15 for b in bx) and m.solid:
            say('start', f"start ({sx},{sy}) is against {p['model']}")
    # lights inside furniture
    for lt in L.lights:
        lx, ly = lt[0], lt[1]
        for i, p, m, fp, h, bx in P:
            if m.solid and any(b[0] < lx < b[2] and b[1] < ly < b[3] for b in bx) and h > 0.9 \
                    and p['model'] not in ('lamp_standard', 'candlestand'):
                say('light', f"light at ({lx},{ly}) is inside {p['model']}")
    return out


def main():
    models = {n: fn() for n, fn in furniture.MODELS.items()}
    lv = sys.argv[1:] or LEVELS
    for ln in lv:
        for line in audit(ln, models):
            print(line)


if __name__ == '__main__':
    main()
