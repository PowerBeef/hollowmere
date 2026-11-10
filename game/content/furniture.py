# SPDX-License-Identifier: MIT
"""Hollowmere's furniture library: low-poly 3D models for the manor.

Conventions: units are tiles (1 tile = 1.5 m, rooms are 2 tiles tall).
Wall-standing pieces have their back on y = 0 and face +y (their front);
free-standing pieces are centred on the origin. Placement angles in the
level files turn the front toward the room.
"""
import math
from meshkit import Mesh

MODELS = {}


def model(name):
    def deco(fn):
        MODELS[name] = fn
        return fn
    return deco


def legs(m, pts, r, z0, z1, tex='wood_dark', n=4):
    """Thin legs as single two-sided quads turned to face outward from the
    piece's centre: one face each instead of four, and LOD drops them first."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    for (x, y) in pts:
        dx, dy = x - cx, y - cy
        L = math.hypot(dx, dy) or 1.0
        tx, ty = -dy / L * r * 1.2, dx / L * r * 1.2       # across the diagonal
        m.wall((x - tx, y - ty), (x + tx, y + ty), z0, z1, tex, (dx, dy), u0=0, u1=4, two_sided=True)


# ------------------------------------------------------------- bedrooms
@model('bed')
def bed():
    m = Mesh('bed')
    W, L = 0.46, 1.32
    m.box(-W - 0.02, 0, 0, W + 0.02, 0.07, 0.95, 'wood_dark', top='wood_dark', skip='nb')            # headboard
    m.box(-W - 0.02, L - 0.07, 0, W + 0.02, L, 0.55, 'wood_dark', skip='b')                           # footboard
    m.box(-W, 0.07, 0.12, W, L - 0.07, 0.3, 'wood_dark', skip='tbn')                                  # frame
    m.box(-W + 0.01, 0.08, 0.3, W - 0.01, 0.44, 0.4, 'ticking', top='linen', skip='bns')               # mattress (the head end: the blanket covers the rest)
    m.box(-W - 0.02, 0.42, 0.24, W + 0.02, L - 0.07, 0.44, 'quilt', top='quilt', skip='bn')            # blanket
    m.box(-0.4, 0.1, 0.4, -0.04, 0.3, 0.48, 'linen', skip='bn')                                       # pillows
    m.box(0.04, 0.1, 0.4, 0.4, 0.3, 0.48, 'linen', skip='bn')
    m.boxes = [(-W - 0.02, 0, W + 0.02, L)]
    return m


@model('bed_iron')
def bed_iron():
    """Hospital bed: painted iron ends as solid panels (thin bars would vanish to LOD)."""
    m = Mesh('bed_iron')
    W, L = 0.34, 1.3
    m.wall((W, 0.02), (-W, 0.02), 0, 0.75, 'iron_bars', (0, -1), u0=0, u1=64, v_top=0, v_bot=64, two_sided=True)
    m.wall((-W, L - 0.02), (W, L - 0.02), 0, 0.55, 'iron_bars', (0, 1), u0=0, u1=64, v_top=0, v_bot=64, two_sided=True)
    m.box(-W + 0.02, 0.04, 0.22, W - 0.02, 0.42, 0.32, 'ticking', top='linen', skip='bns')      # (the quilt covers the rest)
    m.box(-W + 0.03, 0.06, 0.32, W - 0.03, 0.24, 0.38, 'linen', skip='bn')
    m.box(-W - 0.01, 0.4, 0.18, W + 0.01, L - 0.06, 0.35, 'quilt', top='quilt', skip='bn')
    m.boxes = [(-W, 0, W, L)]
    return m


@model('cot')
def cot():
    m = Mesh('cot')
    W, L = 0.24, 0.55
    m.box(-W, -L / 2, 0.15, W, L / 2, 0.30, 'wood_painted', top='linen', decal='t', skip='b')
    for (a, b, n) in (((W, -L / 2), (-W, -L / 2), (0, -1)), ((-W, L / 2), (W, L / 2), (0, 1)),
                      ((-W, -L / 2), (-W, L / 2), (-1, 0)), ((W, L / 2), (W, -L / 2), (1, 0))):
        m.wall(a, b, 0.0, 0.62, 'cot_slats', n, u0=0, u1=64, v_top=0, v_bot=64, two_sided=True)
    m.boxes = [(-W, -L / 2, W, L / 2)]
    return m


@model('wardrobe')
def wardrobe():
    m = Mesh('wardrobe')
    m.box(-0.42, 0, 0, 0.42, 0.38, 1.36, 'wood_darkv', front='wardrobe_front', decal='s', skip='bnt')   # (top under the cornice)
    m.box(-0.45, 0, 1.36, 0.45, 0.41, 1.44, 'wood_dark', skip='bn')       # cornice
    m.box(-0.44, 0, 0, 0.44, 0.40, 0.06, 'wood_dark', skip='btn')          # plinth
    return m


@model('dresser')
def dresser():
    m = Mesh('dresser')
    m.box(-0.36, 0, 0, 0.36, 0.3, 0.58, 'wood_dark', front='dresser_front', decal='s', skip='btn')
    m.box(-0.38, 0, 0.58, 0.38, 0.33, 0.62, 'marble', skip='bn')
    m.box(-0.26, 0.0, 0.62, 0.26, 0.04, 1.2, 'wood_dark', front='mirror', decal='s', skip='bn')
    return m


@model('nightstand')
def nightstand():
    m = Mesh('nightstand')
    m.box(-0.16, 0, 0.05, 0.16, 0.28, 0.42, 'wood_dark', front='dresser_front', decal='s', skip='bn')
    legs(m, [(-0.14, 0.03), (0.14, 0.03), (-0.14, 0.25), (0.14, 0.25)], 0.015, 0, 0.05)
    return m


@model('washstand')
def washstand():
    m = Mesh('washstand')
    m.box(-0.3, 0, 0.0, 0.3, 0.3, 0.5, 'wood_dark', front='dresser_front', decal='s', skip='bnt')
    m.box(-0.32, 0, 0.5, 0.32, 0.32, 0.53, 'marble', skip='bn')
    m.frustum(0, 0.16, 0.12, 0.16, 0.53, 0.6, 8, 'enamel', top='wax')
    m.box(-0.3, 0, 0.53, 0.3, 0.03, 0.75, 'marble', skip='bn')
    return m


# ------------------------------------------------------------- seating
@model('chair')
def chair():
    """Lean dining chair: single-quad legs, a seat box and a two-faced back."""
    m = Mesh('chair')
    s = 0.15
    for (x, y) in [(-s + 0.02, -s + 0.02), (s - 0.02, -s + 0.02), (-s + 0.02, s - 0.02), (s - 0.02, s - 0.02)]:
        d = 0.02
        m.wall((x - d, y - d), (x + d, y + d), 0, 0.29, 'wood_dark', (1, -1), u0=0, u1=4, two_sided=True)
    m.box(-s, -s, 0.28, s, s, 0.32, 'wood_dark', top='velvet_red', skip='b')
    m.wall((-s, -s + 0.03), (s, -s + 0.03), 0.32, 0.72, 'velvet_red', (0, 1), u0=4, u1=60, v_top=6, v_bot=58)
    m.wall((s, -s), (-s, -s), 0.32, 0.72, 'wood_dark', (0, -1), u0=0, u1=40)
    m.boxes = [(-s, -s, s, s)]
    return m


@model('armchair')
def armchair():
    """A button-back armchair: the seat cushion's piped front and a pleated
    skirt below it, the tufted back rolled over at the top, low arms."""
    m = Mesh('armchair')
    W, D = 0.3, 0.3
    m.box(-W, -D, 0.0, W, D, 0.28, 'velvet_red', front='seat_front_red', decal='s', skip='bt')
    m.flat([(-W + 0.08, -D + 0.12), (W - 0.08, -D + 0.12), (W - 0.08, D), (-W + 0.08, D)], 0.28, 'velvet_red', shade=1)
    m.box(-W, -D, 0.28, W, -D + 0.12, 0.72, 'velvet_red', front='seat_back_red', decal='s', skip='b')
    m.box(-W, -D + 0.12, 0.28, -W + 0.08, D, 0.44, 'velvet_red', skip='b')
    m.box(W - 0.08, -D + 0.12, 0.28, W, D, 0.44, 'velvet_red', skip='b')
    m.boxes = [(-W, -D, W, D)]
    return m


@model('sofa')
def sofa():
    """A three-seat sofa: three cushions over a pleated skirt, a long tufted
    back rolled over at the top."""
    m = Mesh('sofa')
    W, D = 0.72, 0.3
    m.box(-W, -D, 0.0, W, D, 0.27, 'velvet_green', front='seat_front_green', decal='s', skip='bt')
    m.flat([(-W + 0.1, -D + 0.12), (W - 0.1, -D + 0.12), (W - 0.1, D), (-W + 0.1, D)], 0.27, 'velvet_green', shade=1)
    m.box(-W, -D, 0.27, W, -D + 0.12, 0.66, 'velvet_green', front='seat_back_green', vfit='s', skip='b')
    m.box(-W, -D + 0.12, 0.27, -W + 0.1, D, 0.45, 'velvet_green', skip='b')
    m.box(W - 0.1, -D + 0.12, 0.27, W, D, 0.45, 'velvet_green', skip='b')
    m.boxes = [(-W, -D, W, D)]
    return m


@model('pew')
def pew():
    """A chapel pew: carved end boards, the seat, the panelled back the row
    behind looks at."""
    m = Mesh('pew')
    W, D = 0.75, 0.18
    m.box(-W, -D, 0.27, W, D, 0.31, 'wood_dark', skip='b')
    m.box(-W, -D, 0.31, W, -D + 0.04, 0.68, 'wood_dark', back='pew_back', vfit='n', skip='b')
    for x in (-W, W - 0.04):
        m.box(x, -D, 0, x + 0.04, D, 0.5, 'wood_dark', sides='pew_end', decal='we', skip='b')
    m.boxes = [(-W, -D, W, D)]
    return m


@model('stool')
def stool():
    m = Mesh('stool')
    m.box(-0.18, -0.12, 0.28, 0.18, 0.12, 0.33, 'wood_dark', top='velvet_red', skip='b')
    legs(m, [(-0.15, -0.09), (0.15, -0.09), (-0.15, 0.09), (0.15, 0.09)], 0.016, 0, 0.28)
    return m


# ------------------------------------------------------------- tables
@model('table_dining')
def table_dining():
    m = Mesh('table_dining')
    W, D = 0.9, 0.34
    m.box(-W, -D, 0.44, W, D, 0.5, 'linen', top='tablecloth', skip='b')
    legs(m, [(-W + 0.06, -D + 0.06), (W - 0.06, -D + 0.06), (-W + 0.06, D - 0.06), (W - 0.06, D - 0.06)], 0.035, 0, 0.44)
    m.boxes = [(-W, -D, W, D)]
    return m


@model('table_kitchen')
def table_kitchen():
    m = Mesh('table_kitchen')
    W, D = 0.55, 0.32
    m.box(-W, -D, 0.44, W, D, 0.5, 'wood_oak', top='wood_oak', skip='b')
    legs(m, [(-W + 0.05, -D + 0.05), (W - 0.05, -D + 0.05), (-W + 0.05, D - 0.05), (W - 0.05, D - 0.05)], 0.035, 0, 0.44, 'wood_oak')
    m.boxes = [(-W, -D, W, D)]
    return m


@model('table_round')
def table_round():
    """Small round occasional table under a linen cloth (pale, so it reads
    against a dark floor), on a turned pedestal and a round foot."""
    m = Mesh('table_round')
    m.prism(0, 0, 0.26, 0.33, 0.48, 8, 'linen', top='linen', rot=math.pi / 8)
    m.prism(0, 0, 0.04, 0.06, 0.33, 4, 'wood_dark')
    m.frustum(0, 0, 0.16, 0.05, 0, 0.08, 6, 'wood_dark')
    m.boxes = [(-0.22, -0.22, 0.22, 0.22)]
    return m


@model('desk')
def desk():
    m = Mesh('desk')
    W, D = 0.5, 0.3
    m.box(-W, 0, 0.48, W, D, 0.52, 'wood_dark', top='leather', skip='bn')
    m.box(-W, 0.02, 0, -W + 0.26, D - 0.02, 0.48, 'wood_dark', front='dresser_front', decal='s', skip='btn')
    m.box(W - 0.26, 0.02, 0, W, D - 0.02, 0.48, 'wood_dark', front='dresser_front', decal='s', skip='btn')
    m.box(-W + 0.26, 0.02, 0.2, W - 0.26, 0.05, 0.48, 'wood_dark', skip='btn')
    m.boxes = [(-W, 0, W, D)]
    return m


@model('table_surgery')
def table_surgery():
    m = Mesh('table_surgery')
    W, D = 0.62, 0.22
    m.box(-W, -D, 0.48, W, D, 0.53, 'enamel', top='linen', skip='b')
    legs(m, [(-W + 0.05, -D + 0.05), (W - 0.05, -D + 0.05), (-W + 0.05, D - 0.05), (W - 0.05, D - 0.05)], 0.025, 0, 0.48, 'iron')
    for x in (-0.3, 0.25):
        m.box(x, -D - 0.01, 0.5, x + 0.06, D + 0.01, 0.55, 'leather', skip='b')
    m.boxes = [(-W, -D, W, D)]
    return m


# ------------------------------------------------------------- storage
@model('bookcase')
def bookcase():
    m = Mesh('bookcase')
    W, D, Hh = 0.45, 0.24, 1.45
    m.box(-W, 0, 0, W, D, Hh, 'wood_darkv', top='wood_dark', skip='bns')
    for (z0, z1) in ((0.05, 0.75), (0.75, 1.38)):
        m.wall((-W + 0.03, D), (W - 0.03, D), z0, z1, 'books', (0, 1), u0=0, u1=58, v_top=0, v_bot=64)
    m.box(-W, D - 0.02, 0, W, D + 0.02, 0.05, 'wood_dark', skip='bn')
    m.box(-W - 0.02, 0, Hh - 0.07, W + 0.02, D + 0.03, Hh, 'wood_dark', skip='bn')
    for x in (-W, W - 0.03):
        m.box(x, D - 0.02, 0.05, x + 0.03, D + 0.02, Hh - 0.07, 'wood_dark', skip='bn')
    m.boxes = [(-W, 0, W, D)]
    return m


def _shelves(name, contents):
    """Open shelving: three boards on uprights, the shelf contents (jars and
    crocks, or folded linen) painted on a panel set back between them."""
    m = Mesh(name)
    W, D = 0.45, 0.22
    m.wall((-W + 0.03, 0.10), (W - 0.03, 0.10), 0.0, 1.10, contents, (0, 1), u0=0, u1=64, v_top=0, v_bot=64)
    for z in (0.3, 0.7, 1.1):
        m.box(-W, 0, z, W, D, z + 0.03, 'wood_oak', skip='bn')
    for x in (-W, W - 0.03):
        m.box(x, 0, 0, x + 0.03, D, 1.15, 'wood_oak', skip='bn')
    m.boxes = [(-W, 0, W, D)]
    return m


@model('shelves')
def shelves():
    return _shelves('shelves', 'shelf_pantry')


@model('shelves_linen')
def shelves_linen():
    return _shelves('shelves_linen', 'shelf_linen')


@model('wine_rack')
def wine_rack():
    m = Mesh('wine_rack')
    W, D = 0.45, 0.28
    m.box(-W, 0, 0, W, D, 1.3, 'wood_oak', top='wood_oak', skip='bns')
    m.wall((-W, D), (W, D), 0, 0.65, 'wine_rack', (0, 1), u0=0, u1=64, v_top=0, v_bot=64)
    m.wall((-W, D), (W, D), 0.65, 1.3, 'wine_rack', (0, 1), u0=0, u1=64, v_top=0, v_bot=64)
    m.boxes = [(-W, 0, W, D)]
    return m


@model('chest')
def chest():
    m = Mesh('chest')
    W, D = 0.3, 0.18
    m.box(-W, -D, 0, W, D, 0.26, 'leather', skip='bt')           # (top under the lid)
    m.box(-W - 0.01, -D - 0.01, 0.26, W + 0.01, D + 0.01, 0.32, 'leather', top='leather', skip='b')
    m.boxes = [(-W, -D, W, D)]
    return m


@model('crate')
def crate():
    m = Mesh('crate')
    m.box(-0.22, -0.22, 0, 0.22, 0.22, 0.44, 'crate', top='crate', skip='b', decal='swen')
    return m


@model('crates')
def crates():
    m = Mesh('crates')
    m.box(-0.24, -0.2, 0, 0.2, 0.24, 0.44, 'crate', top='crate', skip='b', decal='swen')
    m.box(0.22, -0.26, 0, 0.6, 0.12, 0.38, 'crate', top='crate', skip='b', decal='swen')
    m.box(-0.14, -0.14, 0.44, 0.18, 0.18, 0.76, 'crate', top='crate', skip='b', decal='swen')
    return m


@model('barrel')
def barrel():
    m = Mesh('barrel')
    m.frustum(0, 0, 0.18, 0.22, 0, 0.3, 8, 'crate')
    m.frustum(0, 0, 0.22, 0.18, 0.3, 0.6, 8, 'crate', top='wood_oak')
    m.boxes = [(-0.2, -0.2, 0.2, 0.2)]
    return m


# ------------------------------------------------------------- fixtures
@model('fireplace')
def fireplace():
    m = Mesh('fireplace')
    m.box(-0.55, 0, 0, 0.55, 0.2, 0.72, 'marble', front='fireplace_front', decal='s', skip='btn')
    m.box(-0.62, 0, 0.72, 0.62, 0.28, 0.77, 'marble', skip='bn')
    m.box(-0.5, 0.2, 0, 0.5, 0.36, 0.02, 'stone_block', skip='bn')       # hearth
    m.boxes = [(-0.55, 0, 0.55, 0.3)]
    return m


@model('piano')
def piano():
    m = Mesh('piano')
    W, D = 0.5, 0.32
    m.box(-W, 0, 0, W, D, 0.86, 'wood_dark', front='piano_front', top='wood_dark', decal='s', skip='bn')
    m.box(-W, D, 0.46, W, D + 0.12, 0.5, 'wood_dark', top='piano_front', skip='bn',
          decal='t')
    m.boxes = [(-W, 0, W, D + 0.12)]
    return m


@model('clock')
def clock():
    m = Mesh('clock')
    m.box(-0.17, 0, 0, 0.17, 0.2, 0.32, 'wood_darkv', skip='bn')
    m.box(-0.14, 0.01, 0.32, 0.14, 0.18, 1.18, 'wood_darkv', front='clock_front', decal='s', skip='bnt')
    m.box(-0.18, 0, 1.18, 0.18, 0.22, 1.36, 'wood_darkv', top='wood_dark', skip='bn')
    m.boxes = [(-0.17, 0, 0.17, 0.2)]
    return m


@model('stove')
def stove():
    m = Mesh('stove')
    m.box(-0.42, 0, 0, 0.42, 0.42, 0.58, 'iron', front='stove_front', top='iron', decal='s', skip='bn')
    m.box(-0.44, 0, 0.58, 0.44, 0.08, 0.8, 'iron', skip='bn')
    m.prism(0.25, 0.08, 0.06, 0.8, 2.0, 6, 'iron')
    return m


@model('sink')
def sink():
    m = Mesh('sink')
    m.box(-0.35, 0, 0, 0.35, 0.34, 0.5, 'wood_painted', front='dresser_front', decal='s', skip='bn')
    m.box(-0.33, 0.02, 0.5, 0.33, 0.32, 0.58, 'enamel', top='wax', skip='bn')
    m.prism(0, 0.06, 0.02, 0.58, 0.75, 4, 'brass')
    return m


@model('bathtub')
def bathtub():
    m = Mesh('bathtub')
    n = 8
    rx, ry = 0.34, 0.62
    pts_o = [(rx * math.cos(2 * math.pi * k / n + math.pi / 8), ry * math.sin(2 * math.pi * k / n + math.pi / 8)) for k in range(n)]
    for k in range(n):
        a, b = pts_o[k], pts_o[(k + 1) % n]
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        m.wall(b, a, 0.1, 0.5, 'enamel', (mx, my))
    # a rolled rim and the inside of the basin, seen from above: a bath,
    # not a drum with a lid of water
    pts_i = [(x * 0.84, y * 0.9) for x, y in pts_o]
    for k in range(n):
        a, b = pts_o[k], pts_o[(k + 1) % n]
        ia, ib = pts_i[k], pts_i[(k + 1) % n]
        m.flat([a, b, ib, ia], 0.5, 'enamel', True)
        mx, my = (ia[0] + ib[0]) / 2, (ia[1] + ib[1]) / 2
        m.wall(ia, ib, 0.34, 0.5, 'enamel', (-mx, -my), shade=-2)
    m.flat(pts_i, 0.34, 'iron', True, shade=-4)     # dark water
    for (x, y) in ((-0.22, -0.45), (0.22, -0.45), (-0.22, 0.45), (0.22, 0.45)):
        m.prism(x, y, 0.03, 0, 0.1, 4, 'brass')
    m.boxes = [(-rx, -ry, rx, ry)]
    return m


@model('painting')
def painting():
    m = Mesh('painting')
    m.box(-0.24, 0, 0, 0.24, 0.03, 0.56, 'brass', front='portrait', decal='s', skip='bn')
    m.solid = False
    m.boxes = []
    return m


@model('painting_wide')
def painting_wide():
    m = Mesh('painting_wide')
    m.box(-0.36, 0, 0, 0.36, 0.03, 0.42, 'brass', front='landscape', decal='s', skip='bn')
    m.solid = False
    m.boxes = []
    return m


@model('mirror')
def mirror_():
    m = Mesh('mirror')
    m.box(-0.2, 0, 0, 0.2, 0.03, 0.6, 'brass', front='mirror', decal='s', skip='bn')
    m.solid = False
    m.boxes = []
    return m


@model('rug')
def rug():
    m = Mesh('rug')
    m.flat([(-0.7, -0.45), (0.7, -0.45), (0.7, 0.45), (-0.7, 0.45)], 0.006, 'rug',
           uv=[(0, 0), (64, 0), (64, 64), (0, 64)])
    m.solid = False
    m.half = True        # a soft pattern under the feet: one sample per column pair
    return m


@model('generator')
def generator():
    m = Mesh('generator')
    m.box(-0.9, -0.32, 0, 0.9, 0.32, 0.8, 'machine', top='iron', skip='b', decal='s')
    m.box(-0.25, 0.32, 0.25, 0.25, 0.36, 0.75, 'iron', front='generator', decal='s', skip='bnt')
    m.prism(0.6, 0, 0.1, 0.8, 1.2, 6, 'iron', top='iron')
    m.boxes = [(-0.9, -0.32, 0.9, 0.36)]
    return m


@model('fusebox')
def fusebox():
    m = Mesh('fusebox')
    m.box(-0.2, 0, 0.55, 0.2, 0.1, 1.05, 'iron', front='fusebox', decal='s', skip='bn')
    m.solid = False
    m.boxes = []
    return m


@model('boiler')
def boiler():
    """A horizontal riveted boiler (front +y) on two brick saddles: the
    firebox door in its front plate, a steam dome on top and the flue
    rising from the back to the ceiling."""
    m = Mesh('boiler')
    R, zc, y0, y1, n = 0.36, 0.52, -0.60, 0.42, 8
    ang = [math.pi / 8 + 2 * math.pi * k / n for k in range(n)]
    P = [(R * math.cos(a), zc + R * math.sin(a)) for a in ang]
    step = 2 * math.pi * R / n * 64
    for k in range(n):
        (xa, za), (xb, zb) = P[k], P[(k + 1) % n]
        mid = ang[k] + math.pi / n
        # seen from outside with "up" towards the back (-y): right runs to lower angles
        m.face([(xb, y1, zb), (xa, y1, za), (xa, y0, za), (xb, y0, zb)], 'boiler_plate',
               [(step * (n - 1 - k), 64), (step * (n - k), 64), (step * (n - k), 0), (step * (n - 1 - k), 0)],
               (math.cos(mid), 0, math.sin(mid)))
    def cap(y, sgn):
        pts = [(x, y, z) for (x, z) in (P if sgn > 0 else P[::-1])]
        uv = [((sgn * x + R) / (2 * R) * 64, (zc + R - z) / (2 * R) * 64) for (x, y_, z) in pts]
        m.face(pts, 'boiler_plate', uv, (0, sgn, 0))
    cap(y1, 1)
    cap(y0, -1)
    m.box(-0.16, y1, 0.22, 0.16, y1 + 0.04, 0.52, 'iron', front='stove_front', decal='s', skip='bn', collide=False)
    m.frustum(0, -0.05, 0.13, 0.10, zc + R * 0.92, 0.98, 6, 'boiler_plate', top='iron')
    m.prism(0, -0.42, 0.09, zc + R * 0.8, 2.0, 6, 'iron')
    for yc in (-0.38, 0.22):
        m.box(-0.30, yc - 0.08, 0, 0.30, yc + 0.08, zc - R * 0.92, 'stone_block', skip='bt', collide=False)
    m.boxes = [(-R, y0, R, y1 + 0.04)]
    return m


@model('cistern')
def cistern():
    """The attic's water cistern against a wall (front +y): a riveted iron
    tank on two timber bearers, the feed pipe running up into the roof."""
    m = Mesh('cistern')
    W, D = 0.6, 0.7
    for x in (-0.48, 0.38):
        m.box(x, 0.02, 0, x + 0.10, D - 0.02, 0.12, 'wood_oak', skip='bnt', collide=False)
    m.box(-W, 0, 0.12, W, D, 0.80, 'boiler_plate', top='iron', skip='bn')
    m.prism(W - 0.14, 0.14, 0.035, 0.80, 2.0, 4, 'iron')
    m.boxes = [(-W, 0, W, D)]
    return m


@model('altar')
def altar():
    m = Mesh('altar')
    m.box(-0.6, -0.25, 0, 0.6, 0.25, 0.62, 'stone_block', front='altar_cloth', top='altar_cloth', decal='st', skip='b')
    m.boxes = [(-0.6, -0.25, 0.6, 0.25)]
    return m


@model('dressform')
def dressform():
    """Tailor's dummy: a padded jersey torso (hips, a taped waist, bust and
    square shoulders) capped with a turned wooden knob, on a slim pole (it
    stays drawn, so the torso never floats) and three splayed feet."""
    m = Mesh('dressform')
    m.loft([(0, 0, 0.116, 0.59, 62), (0, 0, 0.080, 0.77, 40), (0, 0, 0.124, 0.95, 10),
            (0, 0, 0.050, 1.005, 2)], 6, 'dress_jersey', ax=1.2, ay=0.85)
    m.frustum(0, 0, 0.036, 0.028, 1.0, 1.06, 4, 'wood_dark', top='wood_dark')
    m.pole(0, 0, 0.03, 0.06, 0.60, 'pole_wood')
    for k in range(3):
        a = math.pi / 2 + 2 * math.pi * (k + 0.5) / 3
        c, s_ = math.cos(a), math.sin(a)
        m.vquad((0.17 * c, 0.17 * s_), (0.02 * c, 0.02 * s_), 0.0, 0.04, 0.05, 0.09, 'wood_dark', (-s_, c),
                u0=0, u1=16, v_top=0, v_bot=12, two_sided=True)
    m.boxes = [(-0.12, -0.12, 0.12, 0.12)]
    return m


@model('covered')
def covered():
    """An armchair under a dust sheet: the sheet falls from the seat to the
    floor, rides over the two arms and the rounded back behind."""
    m = Mesh('covered')
    m.prism(0, 0.03, 0.51, 0, 0.46, 4, 'sheet', top='sheet', rot=math.pi / 4)
    for sx in (-1, 1):
        rg = [(sx * 0.26, 0.04, 0.078, 0.46, 64), (sx * 0.265, 0.05, 0.06, 0.62, 0)]
        m.loft(rg, 6, 'sheet', ax=1.0, ay=4.0)
        top = [(sx * 0.265 + 0.06 * math.cos(2 * math.pi * k / 6), 0.05 + 0.24 * math.sin(2 * math.pi * k / 6)) for k in range(6)]
        m.flat(top, 0.62, 'sheet', True)
    m.loft([(0, -0.24, 0.10, 0.46, 64), (0, -0.26, 0.078, 0.90, 0)], 6, 'sheet', ax=3.4, ay=1.0)
    m.flat([(3.4 * 0.078 * math.cos(2 * math.pi * k / 6), -0.26 + 0.078 * math.sin(2 * math.pi * k / 6)) for k in range(6)],
           0.90, 'sheet', True)
    m.boxes = [(-0.38, -0.36, 0.38, 0.4)]
    return m


@model('covered_tall')
def covered_tall():
    m = Mesh('covered_tall')
    m.frustum(0, 0, 0.3, 0.24, 0, 1.2, 5, 'sheet', top='sheet', rot=0.2)
    m.boxes = [(-0.28, -0.28, 0.28, 0.28)]
    return m


@model('lamp_standard')
def lamp_standard():
    """Standard lamp: a weighted brass foot, a slim stem (a pole: it stays
    drawn at any distance, so the shade never floats) and a pleated silk
    shade with a fringe."""
    m = Mesh('lamp_standard')
    m.frustum(0, 0, 0.14, 0.05, 0, 0.06, 6, 'brass')
    m.pole(0, 0, 0.035, 0.06, 1.0, 'pole_brass')
    m.frustum(0, 0, 0.19, 0.11, 0.98, 1.2, 6, 'lampshade')
    m.boxes = [(-0.1, -0.1, 0.1, 0.1)]
    return m


@model('candlestand')
def candlestand():
    """Brass pricket stand for a church: three feet, a tall slim stem with a
    knop half way, a drip pan on top (its lit candles are a sprite)."""
    m = Mesh('candlestand')
    for k in range(3):
        a = math.pi / 2 + 2 * math.pi * (k + 0.5) / 3
        c, s_ = math.cos(a), math.sin(a)
        m.vquad((0.15 * c, 0.15 * s_), (0.02 * c, 0.02 * s_), 0.0, 0.03, 0.06, 0.12, 'brass', (-s_, c),
                u0=0, u1=16, v_top=0, v_bot=12, two_sided=True)
    m.pole(0, 0, 0.03, 0.06, 1.0, 'pole_brass')
    m.prism(0, 0, 0.045, 0.50, 0.56, 4, 'brass')
    m.prism(0, 0, 0.10, 0.98, 1.03, 6, 'brass', top='brass')
    m.boxes = [(-0.08, -0.08, 0.08, 0.08)]
    return m


@model('coatstand')
def coatstand():
    """Coat stand on three splayed legs, a long dark overcoat hanging by its
    collar from the front hook (the coat faces +y), sleeves hanging at its
    sides, a bowler on the top and two empty hooks."""
    m = Mesh('coatstand')
    for k in range(3):
        a = math.pi / 2 + 2 * math.pi * (k + 0.5) / 3
        c, s_ = math.cos(a), math.sin(a)
        m.vquad((0.21 * c, 0.21 * s_), (0.02 * c, 0.02 * s_), 0.0, 0.05, 0.2, 0.3, 'wood_dark', (-s_, c),
                u0=0, u1=16, v_top=0, v_bot=12, two_sided=True)
    m.pole(0, 0, 0.045, 0.0, 1.27, 'pole_wood')
    # the coat: hem, waist, shoulders, the collar on the hook
    m.loft([(0, 0.10, 0.155, 0.36, 64), (0, 0.08, 0.12, 0.78, 26), (0, 0.07, 0.13, 1.06, 8),
            (0, 0.045, 0.045, 1.19, 0)], 6, 'coat_wool', ax=1.25, ay=0.8)
    # sleeves, hanging straight down from the shoulders
    for sx in (-1, 1):
        x0, x1 = sx * 0.145, sx * 0.205
        a_, b_ = ((x0, 0.075), (x1, 0.075)) if sx < 0 else ((x1, 0.075), (x0, 0.075))
        m.vquad(b_, a_, 0.60, 1.04, 0.62, 1.05, 'coat_wool', (0, 1), u0=54, u1=62, v_top=10, v_bot=50,
                two_sided=True)
    # empty hooks (blackened iron: brass ones caught the light like eyes)
    for sx in (-1, 1):
        m.vquad((sx * 0.1, 0), (sx * 0.02, 0), 1.17, 1.20, 1.14, 1.17, 'iron', (0, 1) if sx < 0 else (0, -1),
                u0=0, u1=8, v_top=0, v_bot=4, two_sided=True)
    # bowler hat
    m.flat([(0.115 * math.cos(2 * math.pi * k / 6), 0.115 * math.sin(2 * math.pi * k / 6)) for k in range(6)],
           1.27, 'felt_hat', True, uv=[(32 + 30 * math.cos(2 * math.pi * k / 6), 60) for k in range(6)], two_sided=True)
    m.frustum(0, 0, 0.07, 0.06, 1.27, 1.37, 6, 'felt_hat', top='felt_hat')
    m.boxes = [(-0.14, -0.12, 0.14, 0.2)]
    return m


# the hall's grand staircase: nine steps rising along +y, the open side at
# +x (the wall side is never seen). Two models placed together so that each
# stays within the renderer's per-model limits.
ST_W, ST_N, ST_RUN, ST_RISE = 0.48, 9, 0.22, 0.12


def st_nosing(y):
    """Height of the line through the step nosings at y."""
    return ST_RISE + y * ST_RISE / ST_RUN


@model('stairs_grand')
def stairs_grand():
    """The steps, the closed string and panelled spandrel on the open side,
    the half landing and the splintered ends of the flight that fell in.
    Beyond a few tiles the far model takes over (the steps as one slope)."""
    m = Mesh('stairs_grand')
    W, N, run, rise = ST_W, ST_N, ST_RUN, ST_RISE
    for k in range(N):
        y0, y1, z0, z1 = k * run, (k + 1) * run, k * rise, (k + 1) * rise
        m.wall((W, y0), (-W, y0), z0, z1, 'stair_riser', (0, -1), u0=0, u1=64, v_top=0, v_bot=8)
        m.flat([(-W, y0), (W, y0), (W, y1), (-W, y1)], z1, 'stair_tread', True,
               uv=[(0, 0), (64, 0), (64, 64), (0, 64)])
    stairs_sides(m)
    m.far, m.far_dist = 'stairs_grand_far', 2.0
    return m


def stairs_sides(m, near=True):
    """What both staircase models share: the string, the spandrel, the half
    landing closed by a panelled back, and what is left of the upper flight
    (it carried on north from the landing): the stubs of its strings and its
    first riser, snapped off, and its wreckage on the floor behind."""
    W, N, run, rise = ST_W, ST_N, ST_RUN, ST_RISE
    L, top = N * run, N * rise
    Lb = L + 0.35                       # the back of the landing
    pitch = rise / run
    # closed string: a board following the nosings, its foot on the floor
    xs = W + 0.06
    def sb(y):
        return max(0.0, st_nosing(y) - 0.16)
    m.vquad((xs, L), (xs, 0.0), sb(L), st_nosing(L) + 0.06, sb(0.0), st_nosing(0.0) + 0.06,
            'stair_string', (1, 0), u0=0, u1=L * 64, v_top=0, v_bot=64)
    # panelled spandrel below it, and under the landing
    xp = W + 0.05
    m.vquad((xp, L), (xp, 0.3), 0.0, sb(L), 0.0, sb(0.3), 'stair_panel', (1, 0),
            u0=0, u1=(L - 0.3) * 48, v_top=0, v_bot=64)
    m.wall((xp, Lb), (xp, L), 0.0, top - 0.12, 'stair_cupboard', (1, 0), u0=0, u1=64, v_top=0, v_bot=64)   # (a hiding place)
    # the half landing: a moulded fascia round its edge, panelling below
    m.box(-W - 0.02, L, top - 0.12, W + 0.06, Lb, top, 'stair_string', top='stair_tread',
          skip='bnw', decal='t', vfit=('s', 'e'))
    m.wall((-W - 0.02, Lb), (W + 0.06, Lb), 0.0, top - 0.12, 'stair_panel', (0, 1), u0=0, u1=96, v_top=0, v_bot=64)
    # the upper flight, snapped off: the stubs of its two strings,
    # splintered to a point
    def nos(y):                         # the upper flight's nosing line
        return top + rise + (y - Lb) * pitch
    for x, reach, tip in ((W + 0.06, 0.20, 0.07), (-W - 0.02, 0.32, 0.05)):
        y1 = Lb + reach
        m.vquad((x, y1), (x, Lb - 0.02), nos(y1) + 0.06 - tip, nos(y1) + 0.06, nos(Lb) - 0.2, nos(Lb) + 0.06,
                'stair_string', (1, 0), u0=0, u1=reach * 64, v_top=0, v_bot=64, two_sided=True)
    # its wreckage behind the landing: a length of string on the floor
    if near:
        m.vquad((-0.42, Lb + 0.50), (0.46, Lb + 0.12), 0.0, 0.07, 0.0, 0.15, 'stair_string', (0.4, 0.9),
                u0=0, u1=60, v_top=0, v_bot=64)
    m.boxes = [(-W - 0.05, 0, W + 0.08, Lb), (-0.45, Lb, W + 0.08, Lb + 0.5)]


@model('stairs_grand_far')
def stairs_grand_far():
    """stairs_grand from a distance: the nine steps as one textured slope."""
    m = Mesh('stairs_grand_far')
    W, N, run, rise = ST_W, ST_N, ST_RUN, ST_RISE
    L, top = N * run, N * rise
    m.slope([(-W, L, top), (W, L, top), (W, 0.0, rise * 0.5), (-W, 0.0, rise * 0.5)], 'stair_steps',
            (0, -(top - rise * 0.5), L), uv=[(0, 0), (64, 0), (64, 16 * N), (0, 16 * N)])
    stairs_sides(m, near=False)
    return m


def balustrade(m, crossed):
    """Painted balusters on the string (crossed pairs of quads near: a slim
    turned post from any side; single quads facing the open side far), the
    mahogany handrail, the newel posts at the foot and at both corners of
    the landing, and the rail of the upper flight snapped off above it."""
    W, N, run, rise = ST_W, ST_N, ST_RUN, ST_RISE
    L, top = N * run, N * rise
    Lb = L + 0.35
    pitch = rise / run
    xb, d = W + 0.03, 0.018
    def post(y, z0, z1):
        # (thin: they stay drawn at any distance, like the gallery railing's,
        # rather than leaving the handrail floating over the string)
        m.wall((xb, y + d), (xb, y - d), z0, z1, 'baluster', (1, 0), u0=0, u1=64, v_top=0, v_bot=64, two_sided=True,
               thin=True)
        if crossed:
            m.wall((xb - d, y), (xb + d, y), z0, z1, 'baluster', (0, 1), u0=0, u1=64, v_top=0, v_bot=64, two_sided=True)
    for k in range(N):
        y = (k + 0.5) * run
        post(y, st_nosing(y) + 0.06, st_nosing(y) + 0.52)
    # handrail: one upright face, its rounded top shaded into the texture
    y0, y1 = -0.03, L + 0.02
    m.vquad((xb, y1), (xb, y0), st_nosing(y1) + 0.52, st_nosing(y1) + 0.61, st_nosing(y0) + 0.52,
            st_nosing(y0) + 0.61, 'handrail', (1, 0), u0=0, u1=(y1 - y0) * 64, v_top=0, v_bot=64, two_sided=True)
    # along the landing: a level rail and one baluster
    zr = top + 0.56
    m.wall((xb, Lb - 0.08), (xb, L + 0.08), zr, zr + 0.09, 'handrail', (1, 0), u0=0, u1=16, v_top=0, v_bot=64,
           two_sided=True)
    post((L + Lb) / 2, top, zr)
    # the upper flight's rail, broken off a little way up (near only)
    zu = top + rise + 0.52
    if crossed:
        m.vquad((xb, Lb + 0.22), (xb, Lb - 0.02), zu + 0.22 * pitch + 0.03, zu + 0.22 * pitch + 0.08,
                zu - 0.01, zu + 0.08, 'handrail', (1, 0), u0=0, u1=16, v_top=0, v_bot=64, two_sided=True)
    # newel posts: at the foot, with a moulded cap, and at each corner of the landing
    m.box(xb - 0.05, -0.10, 0.0, xb + 0.05, 0.0, 0.86, 'newel', skip='b', decal='nswe')
    m.box(xb - 0.065, -0.115, 0.86, xb + 0.065, 0.015, 0.92, 'handrail', skip='b')
    m.box(xb - 0.05, L - 0.02, 0.0, xb + 0.05, L + 0.08, top + 0.66, 'newel', top='handrail', skip='b',
          decal='nswe')
    m.box(xb - 0.05, Lb - 0.10, top - 0.12, xb + 0.05, Lb, top + 0.74, 'newel', top='handrail', skip='b',
          decal='nswe')
    m.solid = False
    m.boxes = []


@model('stairs_balustrade')
def stairs_balustrade():
    m = Mesh('stairs_balustrade')
    balustrade(m, True)
    m.shift(*BAL_SHIFT)
    m.far, m.far_dist = 'stairs_balustrade_far', 2.0
    return m


@model('stairs_balustrade_far')
def stairs_balustrade_far():
    m = Mesh('stairs_balustrade_far')
    balustrade(m, False)
    m.shift(*BAL_SHIFT)
    return m


# Props are drawn far to near by the depth of their origins. The balustrade's
# origin sits off the staircase's, towards the foot and the open side
# (place it at the staircase's origin + BAL_ORIGIN, its geometry moved back
# by as much): seen from the hall it is the nearer of the two and is drawn
# over the steps and the spandrel; seen from behind the landing it is the
# farther, and the landing's panelled back hides the rail beyond it.
BAL_ORIGIN = (77, -38)                                  # 1/256 tile, model axes
BAL_SHIFT = (-BAL_ORIGIN[0], -BAL_ORIGIN[1])


@model('hide_spot')
def hide_spot():
    """Nothing to draw: marks a hiding place built into something else (the
    cupboard under the hall stairs), so it can carry the hide interaction."""
    m = Mesh('hide_spot')
    m.solid = False
    m.boxes = []
    return m


@model('railing')
def railing():
    """One tile of the landing's gallery balustrade over the fallen stairwell,
    in the hall stair's style: a mahogany handrail on painted turned
    balusters (posts: they stay drawn at any distance) and a plinth rail."""
    m = Mesh('railing')
    d = 0.02
    for k in range(5):
        x = -0.4 + k * 0.2
        m.wall((x - d, 0), (x + d, 0), 0.05, 0.56, 'baluster', (0, 1), u0=0, u1=64, v_top=0, v_bot=64,
               two_sided=True, thin=True)
    m.wall((-0.5, 0), (0.5, 0), 0.56, 0.65, 'handrail', (0, 1), u0=0, u1=64, v_top=0, v_bot=64, two_sided=True)
    m.wall((-0.5, 0), (0.5, 0), 0.0, 0.05, 'wood_dark', (0, 1), two_sided=True)
    m.boxes = [(-0.5, -0.04, 0.5, 0.04)]
    return m


# ------------------------------------------------------------- door leaves
def door_leaf(name, width, height):
    """Hinge on the model's y axis at x=0; the leaf extends along +x."""
    m = Mesh(name)
    t = 0.02
    m.wall((0, -t), (width, -t), 0, height, 255, (0, -1), u0=64, u1=0, v_top=0, v_bot=64)
    m.wall((width, t), (0, t), 0, height, 255, (0, 1), u0=0, u1=64, v_top=0, v_bot=64)
    m.wall((width, -t), (width, t), 0, height, 'wood_dark', (1, 0), u0=0, u1=4, v_top=0, v_bot=64)
    m.wall((0, t), (0, -t), 0, height, 'wood_dark', (-1, 0), u0=0, u1=4, v_top=0, v_bot=64)
    m.flat([(0, -t), (width, -t), (width, t), (0, t)], height, 'wood_dark', True)
    m.solid = False
    m.boxes = []
    return m


@model('leaf_single')
def leaf_single():
    return door_leaf('leaf_single', 38 / 64, 45 / 32)


@model('leaf_half')
def leaf_half():
    return door_leaf('leaf_half', 28 / 64, 48 / 32)


def build_all():
    out = {}
    for name, fn in MODELS.items():
        m = fn()
        m.name = name
        out[name] = m
    return out


if __name__ == '__main__':
    for n, m in build_all().items():
        print(m.stats())
