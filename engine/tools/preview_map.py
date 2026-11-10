#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Top-down plan of a level: rooms, walls, doors, arches and windows, the
furniture's footprints, items, lights, triggers, the patrol route and the start.

    python3 engine/tools/preview_map.py l1_ground out.png
"""
import sys
import importlib
import paths  # noqa: F401  (puts the game's content and levels on the path)
from PIL import Image, ImageDraw

import audit
import furniture
import levelc

S = 32                                   # pixels per cell
mod = importlib.import_module(sys.argv[1])
models = {n: fn() for n, fn in furniture.MODELS.items()}
ids = dict(wall=audit.Any(), flat=audit.Any(), ptex=audit.Any(), model={k: 0 for k in models}, thing=audit.Any())
L = levelc.parse(mod, ids, models)

im = Image.new('RGB', ((L.W + 1) * S, (L.H + 1) * S), (16, 16, 20))
d = ImageDraw.Draw(im)
O = S // 2                               # margin
X = lambda v: O + v * S                  # noqa: E731
rooms = sorted({L.cell[y][x] for y in range(L.H) for x in range(L.W)} - {' '})
tint = {r: (50 + 37 * i % 60, 48 + 53 * i % 50, 56 + 29 * i % 40) for i, r in enumerate(rooms)}
for y in range(L.H):
    for x in range(L.W):
        if L.cell[y][x] != ' ':
            d.rectangle([X(x), X(y), X(x + 1) - 1, X(y + 1) - 1], fill=tint[L.cell[y][x]])
# triggers under everything else
for t in L.triggers:
    x0, y0, x1, y1, ev = t[:5]
    d.rectangle([X(x0) + 2, X(y0) + 2, X(x1 + 1) - 3, X(y1 + 1) - 3], outline=(150, 60, 120))
    d.text((X(x0) + 4, X(y0) + 3), str(ev)[:12], fill=(200, 90, 170))
# furniture footprints
for p in L.props:
    m = models[p['model']]
    if not m.verts or m.verts == [(0, 0, 0)]:
        continue
    (x0, y0, x1, y1), h = audit.footprint(p, m)
    d.rectangle([X(x0), X(y0), X(x1), X(y1)], fill=(110, 84, 60) if m.solid else None, outline=(170, 130, 90))
# edges
COL = {'wall': (225, 225, 215), 'window': (110, 170, 255), 'door': (240, 170, 60),
       'exit': (90, 230, 120), 'sealed': (140, 140, 140), 'arch': (240, 170, 60)}
for (x, y, o), kind in L.map_kind.items():
    if kind == 'open':
        continue
    a, b = ((X(x), X(y)), (X(x), X(y + 1))) if o == 'W' else ((X(x), X(y)), (X(x + 1), X(y)))
    w = 2 if kind == 'arch' else 3
    d.line([a, b], fill=COL.get(kind, (255, 0, 255)), width=w)
for di, dr in enumerate(L.doors):
    if dr.get('lock'):
        x, y = dr['x'], dr['y']
        cx, cy = (X(x), X(y) + S // 2) if dr['axis'] == 0 else (X(x) + S // 2, X(y))
        d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=(220, 60, 50))
# lights, items, patrol, start
for (x, y, inten, radius, mode, group) in L.lights:
    r = radius * S
    d.ellipse([X(x) - r, X(y) - r, X(x) + r, X(y) + r], outline=(90, 80, 30))
    d.ellipse([X(x) - 3, X(y) - 3, X(x) + 3, X(y) + 3], fill=(255, 220, 90))
for t in L.things:
    d.rectangle([X(t['x']) - 3, X(t['y']) - 3, X(t['x']) + 3, X(t['y']) + 3], fill=(90, 220, 255))
pts = [(X(x + 0.5), X(y + 0.5)) for (x, y) in L.patrol]
if len(pts) > 1:
    d.line(pts + [pts[0]], fill=(200, 40, 40), width=1)
sx, sy = L.start
d.polygon([(X(sx) - 7, X(sy) + 7), (X(sx) + 7, X(sy) + 7), (X(sx), X(sy) - 9)], fill=(60, 255, 90))
im.save(sys.argv[2])
print(f"{L.name}: {L.W}x{L.H} cells, {len(L.doors)} doors, {len(L.props)} props, "
      f"{len(L.things)} items, {len(L.lights)} lights -> {sys.argv[2]}")
