# SPDX-License-Identifier: MIT
"""Regression tests: what the 3D view shows."""
import harness
import hm
import sweep

FREEZE = ["poke32 {g_dbgFreeze} 4000", "poke16 {g_minLight} 22"]


def differing(a, b, box=None):
    """Pixels that differ between two images (in a box)."""
    if box:
        a, b = a.crop(box), b.crop(box)
    return sum(1 for p, q in zip(a.tobytes()[::3], b.tobytes()[::3]) if p != q) if a.tobytes() != b.tobytes() else 0


def changed(a, b):
    """(count, bounding box) of the pixels that differ in any channel."""
    from PIL import ImageChops
    d = ImageChops.difference(a, b).convert('L').point(lambda v: 255 if v else 0)
    return d.histogram()[255], d.getbbox()


def test_staircase_close_up(t):
    """The hall staircase stays drawn when its origin is behind the viewer."""
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss()
    for i, y in enumerate((9.9, 9.6, 9.4)):
        L += ["poke32 {g_dbgFreeze} 0"] + hm.teleport(7.0, y, 290) + hm.dismiss() + harness.FULL_DETAIL + FREEZE
        L += ["run 24", f"shot {{out}}/lod_{i}.ppm", "poke32 {g_lodScale} 0", "run 24", f"shot {{out}}/all_{i}.ppm"]
    t.run(L)
    for i in range(3):
        n, box = changed(t.image(f"lod_{i}.ppm"), t.image(f"all_{i}.ppm"))
        t.check(n < 200, f"view {i}: {n} pixels differ from the view with every face drawn (box {box})")


def test_the_next_room_does_not_show_along_a_wall(t):
    """Nothing outside a shut room shows in its floor or ceiling. The drawing
    room is drawn twice, with every light cell outside it lit to the full and
    not lit at all: a pixel that differs was sampled beyond a wall. (The row
    of floor or ceiling left showing where a wall's edge fell inside a pair
    of rows was: a pale line of the corridor's plaster along the top of a
    wall, three rows of it at some distances.)"""
    views = [(2.0, 8.5, 270), (3.4, 7.5, 180), (0.6, 9.4, 0), (2.7, 6.5, 90), (6.5, 9.52, 270)]
    for level in (31, 0):
        L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + hm.HUD_OFF + harness.FULL_DETAIL
        for gy in range(64):
            for gx in range(0, 64, 4):
                if not (gx < 8 and 10 <= gy < 20):                  # the drawing room: tiles 0..3, 5..9
                    L.append(f"poke32 {{g_lightStatic+{gy * 64 + gx}}} {(level | 1 << 5) * 0x01010101}")
        L += ["poke8 {g_lightsDirty} 1", "run 20"]
        for i, (x, y, a) in enumerate(views[:4]):
            L += hm.teleport(x, y, a, settle=10) + [f"shot {{out}}/room{i}_{level}.ppm"]
        t.run(L)
    for i in range(4):
        n, box = changed(t.image(f"room{i}_31.ppm"), t.image(f"room{i}_0.ppm"))
        t.check(n < 60, f"drawing room, view {i}: {n} pixels of the floor and ceiling come from beyond the walls (box {box})")
    # and the hall as the game lights it, where it was seen: no plaster above
    # the wall around the archway (the hall's ceiling is dark beams)
    x, y, a = views[4]
    t.run(hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + hm.HUD_OFF + harness.FULL_DETAIL
          + hm.teleport(x, y, a, settle=12) + ["shot {out}/hall.ppm"])
    im = t.image('hall.ppm')
    pale = sum(1 for yy in range(26, 36) for xx in range(240)
               if (lambda r, g, b: r + g + b > 200 and b * 10 > r * 7)(*im.getpixel((xx, yy))))
    t.check(pale < 40, f"the hall, facing the corridor wall: {pale} pale pixels along the top of the wall")


def test_no_undrawn_pixels(t):
    """Views that had rectangles of stale pixels: every pixel is drawn."""
    for level, views in ((0, [(5.5, 1.5, 112.5), (4.23, 1.23, 326.25)]), (3, [(3.23, 1.77, 332.25), (9.5, 1.5, 270)])):
        L = hm.boot() + hm.dismiss() + (hm.load_level(level) if level else []) + ["run 300"] + hm.dismiss() + ["poke32 {g_dbgFreeze} 4000", "run 2"]
        for i, (x, y, a) in enumerate(views):
            for q in sweep.DETAIL:
                L += hm.teleport(x, y, a, settle=0) + sweep.knobs(q) + ["run 12"] + sweep.hole_check(f"{i}_{q}", f"{{out}}/hole_{level}_{i}_{q}.ppm")
        for name, c in t.run(L, name=f"level{level}").cmps().items():
            t.check(c[0] == 0, f"level {level} view {name}: {c[0]} pixels not drawn (box {c[1:]})")


def test_things_on_tables(t):
    """The ledger on the library table and the battery on the kitchen table
    are visible from every side one can stand on."""
    import math
    free = sweep.standable(0)
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + hm.HUD_OFF      # (no "Read note" prompt in the pictures)
    spots = []
    for name, (tx, ty) in (('ledger', (2.0, 1.8)), ('battery', (9.4, 2.0))):
        for k in range(8):
            for d in (1.4, 1.15, 1.7):
                x, y = tx + d * math.cos(k * math.pi / 4), ty + d * math.sin(k * math.pi / 4)
                if free(x, y):
                    spots.append((f"{name}_{k * 45}", x, y, math.degrees(math.atan2(ty - y, tx - x)) % 360))
                    break
    for which in ('with', 'without'):
        for tag, x, y, a in spots:
            L += ["poke32 {g_dbgFreeze} 0"] + hm.teleport(x, y, a) + hm.dismiss() + harness.FULL_DETAIL + FREEZE + ["run 24", f"shot {{out}}/{which}_{tag}.ppm"]
        L += hm.hide_things()
    t.run(L)
    t.check(len(spots) >= 12, f"only {len(spots)} places to look from")
    seen = {tag: changed(t.image(f"with_{tag}.ppm"), t.image(f"without_{tag}.ppm"))[0] for tag, *_ in spots}
    hidden = [f"{tag} ({n} pixels)" for tag, n in seen.items() if n < 20]
    t.check(not hidden, "not visible from: " + ', '.join(hidden))


def cellar_view(x, y, deg, tag, sister=None):
    L = ["poke32 {g_dbgFreeze} 0"] + hm.teleport(x, y, deg) + hm.dismiss()
    if sister:
        L += hm.spawn(sister, hm.CR_WAIT)
    return L + harness.FULL_DETAIL + ["poke32 {g_dbgFreeze} 77", "poke16 {g_minLight} 22", "run 24", f"shot {{out}}/{tag}.ppm"]


def test_sister_between_two_arches(t):
    """Seen through two cellar arches in a row, the Sister standing between
    them is cut by the near arch only, not by the far one behind her."""
    L = hm.boot() + hm.dismiss() + hm.load_level(1) + ["run 300"] + hm.dismiss() + ["run 600"] + hm.dismiss()
    L += cellar_view(7.5, 1.0, 90, 'empty') + cellar_view(7.5, 1.0, 90, 'sister', 1.5)
    t.run(L)
    from PIL import ImageChops
    d = ImageChops.difference(t.image('empty.ppm'), t.image('sister.ppm')).convert('L').crop((112, 18, 128, 134)).load()
    rows = [y + 18 for y in range(116) if sum(1 for x in range(16) if d[x, y]) >= 6]
    t.check(rows and rows[0] <= 53, f"her head starts at row {rows[0] if rows else None}: cut off at the far arch (row 58)")


def test_third_opening_keeps_its_lintel(t):
    """A view through three doorways in a row draws the wall over all three."""
    L = hm.boot() + hm.dismiss() + hm.load_level(1) + ["run 300"] + hm.dismiss() + ["run 600"] + hm.dismiss()
    L += [f"poke16 {{g_doors+{4 + 16 * i}}} 65535" for i in range(12)] + cellar_view(7.3, 1.7, 61.9, 'three')
    t.run(L)
    px = t.image('three.ppm').crop((10, 28, 21, 42)).tobytes()
    brick = sum(1 for i in range(0, len(px), 3) if px[i] > px[i + 2] * 1.4)
    t.check(brick >= 100, f"only {brick} of 154 pixels over the far doorway are brick")


def test_edges_of_faces_cut_at_the_near_plane(t):
    """Sliding sideways past a box that reaches behind the viewer: the bottom
    edge of its side (a wall-like face) and the far edge of its top (a
    polygon) stay within a row of where they belong. (The dining table is
    turned into the chapel's altar block for this: a plain box.)"""
    import furniture
    altar = list(furniture.MODELS).index('altar')
    half_len, half_wid, height = 0.6, 0.25, 0.62
    box = furniture.MODELS['altar']().boxes[0]
    t.check(box == (-half_len, -half_wid, half_len, half_wid), f"the altar model changed ({box}): update this test")
    TABLE, CHAIRS, X, Y = 14, range(15, 21), 11.5, 7.5          # the dining table and its chairs in g_props

    def prop(i, off):
        return f"{{g_props+{i * 16 + off}}}"                    # PropInst: x, y, z (s16 at 8), angle, model (12), flags (13)
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + hm.HUD_OFF
    L += [f"expects32 {prop(TABLE, 0)} == {int(X * 65536)} the dining table is prop {TABLE}",
          f"expects32 {prop(TABLE, 4)} == {int(Y * 65536)} the dining table is prop {TABLE}"]
    L += [f"poke8 {prop(i, 13)} 1" for i in CHAIRS] + [f"poke8 {prop(TABLE, 12)} {altar}"]
    cases = [('side', 180, l) for l in range(120, 200, 6)] + [('top', 0, l) for l in range(60, 80, 4)]
    for part, z, l in cases:
        L += ["poke32 {g_dbgFreeze} 0", f"poke16 {prop(TABLE, 8)} {z}", f"poke8 {prop(TABLE, 13)} 0"]
        L += hm.teleport(X - 0.5, Y + half_wid + l / 256, 0) + hm.dismiss() + harness.FULL_DETAIL + FREEZE
        L += ["run 24", f"shot {{out}}/{part}{l}.ppm", "peeks32 {g_cam}", "peeks32 {g_cam+4}",
              f"poke8 {prop(TABLE, 13)} 1", "run 24", f"shot {{out}}/{part}{l}_without.ppm"]
    v = t.run(L).values()
    worst = {'side': 0.0, 'top': 0.0}
    for k, (part, z, l) in enumerate(cases):
        cx, cy = v[2 * k] / 65536, v[2 * k + 1] / 65536
        lat = cy - (Y + half_wid)
        a, h = t.image(f"{part}{l}.ppm").load(), t.image(f"{part}{l}_without.ppm").load()
        for c in range(0, 119):
            ratio = (c + 0.5 - 120) / 160                       # tangent of the column's ray
            if part == 'side':      # the bottom edge of the near long side, at height z
                f, zrel, rule = -lat / ratio, z / 256 - 1.0, 0.0
            else:                   # the far long edge of the top
                f, zrel, rule = -(lat + 2 * half_wid) / ratio, height - 1.0, 0.0
            if not X - half_len - cx + 0.02 < f < X + half_len - cx - 0.02:
                continue
            exact = 68 - zrel * 160 / f
            if not 19 < exact < 132:
                continue
            rows = [y for y in range(18, 134) if a[c, y] != h[c, y]]
            if rows:
                drawn = max(rows) + 1 if part == 'side' else min(rows)
                worst[part] = max(worst[part], abs(drawn - exact - rule))
    t.check(worst['side'] <= 1.05, f"the side's bottom edge is up to {worst['side']:.1f} rows off")
    t.check(worst['top'] <= 1.0, f"the top's far edge is up to {worst['top']:.1f} rows off")


def test_dresser_does_not_show_through_the_wall(t):
    """From the hall, the dining-room dresser behind the corner of the wall
    does not leak a few pixels onto it."""
    import math
    DRESSER, at = 22, (9.6, 5.15)

    def prop(off):
        return f"{{g_props+{DRESSER * 16 + off}}}"
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + hm.HUD_OFF
    L += [f"expects32 {prop(0)} == {int(9.6015625 * 65536)} the dresser is prop {DRESSER}"]
    cams = [(4.5, 4.5), (5.5, 4.5), (6.5, 4.5), (7.2, 4.4), (7.8, 4.3), (5.5, 4.2), (6.5, 4.15)]
    for i, (x, y) in enumerate(cams):
        L += ["poke32 {g_dbgFreeze} 0", f"poke8 {prop(13)} 0"] + hm.teleport(x, y, math.degrees(math.atan2(at[1] - y, at[0] - x)) % 360)
        L += hm.dismiss() + harness.FULL_DETAIL + FREEZE + ["run 24", f"shot {{out}}/with{i}.ppm", f"poke8 {prop(13)} 1", "run 24", f"shot {{out}}/without{i}.ppm"]
    t.run(L)
    for i, cam in enumerate(cams):
        n, box = changed(t.image(f"with{i}.ppm"), t.image(f"without{i}.ppm"))
        t.check(n == 0, f"from {cam}: {n} pixels of the dresser show (box {box})")


def test_ray_exactly_along_an_axis(t):
    """Standing a hair from a cell boundary and looking exactly along it, the
    centre columns see the far wall (11.5 tiles), not a wall two tiles away."""
    L = hm.boot() + hm.dismiss() + hm.load_level(2) + hm.dismiss() + [f"poke16 {{g_doors+{4 + 16 * 6}}} 65535", "poke32 {g_dbgFreeze} 77"]
    L += ["poke32 {g_player} 163840", "poke32 {g_player+4} 327616", "poke16 {g_player+8} 33", "run 24"]       # (2.5, 4.999), 0.18 degrees
    L += [f"peek32 {{g_zbuf+{4 * c}}}" for c in range(112, 120)]           # (from column 120 on: the door's own jamb)
    v = t.run(L).values()
    bad = {112 + i: round(z / 65536, 2) for i, z in enumerate(v) if not 11.3 < z / 65536 < 11.7}
    t.check(not bad, f"wall distance by column: {bad} (the far wall is 11.5 tiles away)")


def test_walls_agree_with_the_camera_axes(t):
    """Turning in small steps in the library: the distance the walls' rays
    find to the flat north wall matches, column by column, the directions the
    floors and objects are drawn with (the camera's axes), to a quarter of a
    column."""
    import math
    X, Y = 2.0, 2.2                                      # the wall y = 0 is 2.2 tiles north
    headings = [int((235 + 1.9 * i) / 360 * 65536) + 7 * i for i in range(36)]
    cols = list(range(40, 200, 4))                       # the columns that get a ray of their own
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + ["poke32 {g_dbgFreeze} 4000", "run 4"]
    for a in headings:
        L += [f"poke32 {{g_player}} {int(X * 65536)}", f"poke32 {{g_player+4}} {int(Y * 65536)}", f"poke16 {{g_player+8}} {a & 0xFFFF}", "run 6"]
        L += ["peeks32 {g_cam+12}", "peeks32 {g_cam+16}", "peeks32 {g_cam+20}", "peeks32 {g_cam+24}"] + [f"peek32 {{g_zbuf+{4 * c}}}" for c in cols]
    v = t.run(L).values()
    n = 4 + len(cols)
    worst, used = 0.0, 0
    for i in range(len(headings)):
        dx, dy, px, py = (q / 16384 for q in v[i * n:i * n + 4])
        for c, z in zip(cols, v[i * n + 4:(i + 1) * n]):
            cx = (2 * c + 1) / 240 - 1                   # the column on the camera plane, -1..1
            rx, ry = dx + px * cx, dy + py * cx          # its ray: one tile along the view axis
            if ry > -0.3:
                continue
            want = -Y / ry                               # distance along the view axis to y = 0
            hit = X + rx * want
            if not 0.3 < hit < 3.7:
                continue                                 # (the side walls)
            # a ray turned by e sees the wall at want * (1 + e * tangent of its incidence)
            tangent = abs(rx / ry)
            if tangent < 0.5:
                continue
            e = (z / 65536 - want) / want / tangent      # radians
            worst = max(worst, abs(math.degrees(e)) / (74 / 240))
            used += 1
    t.check(used > 150, f"only {used} columns measured")
    t.check(worst <= 0.25, f"walls and camera axes disagree by up to {worst:.2f} columns")


def test_half_resolution_keeps_the_odd_column(t):
    """Far polygons take one sample per column pair. Where the pair's even
    column has nothing of the polygon (a wall in front of it, or the outline
    starting there), the odd column is still drawn."""
    spots = [((12.23, 3.23, 146.25), 179, range(126, 134), 6), ((1.5, 3.5, 292.5), 153, range(110, 114), 3)]
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + hm.HUD_OFF + [f"poke16 {{g_doors+{4 + 16 * i}}} 65535" for i in range(20)]
    for i, ((x, y, a), col, rows, least) in enumerate(spots):
        L += ["poke32 {g_dbgFreeze} 0", "poke32 {g_noObjects} 0"] + hm.teleport(x, y, a) + hm.dismiss() + harness.FULL_DETAIL
        L += ["poke32 {g_halfDist} 0"] + FREEZE + ["run 24", f"shot {{out}}/half{i}.ppm", "poke32 {g_noObjects} 1", "run 24", f"shot {{out}}/empty{i}.ppm"]
    L += ["poke32 {g_noObjects} 0"]
    t.run(L)
    for i, (pose, col, rows, least) in enumerate(spots):
        a, b = t.image(f"half{i}.ppm").load(), t.image(f"empty{i}.ppm").load()
        n = sum(1 for y in rows if a[col, y] != b[col, y])
        t.check(n >= least, f"at {pose}: column {col} has {n} pixels of the furniture, expected {least} or more")


def test_paintings_stay_inside_their_frames(t):
    """The portrait's sitter was painted over the bottom edge of its gilt
    frame: a black blob on the frame of every portrait in the house. The
    frame of each framed texture must be the frame painting() drew."""
    import numpy as np
    import proptex
    blank, _ = proptex.painting(1, [[0, 0, 0], [0, 0, 0], [0, 0, 0]])
    frame = np.ones(blank.shape[:2], bool)
    frame[6:-6, 6:-6] = False                   # (the canvas is inside a 6-texel frame)
    for name in ('portrait', 'landscape', 'mirror'):
        painted = np.abs(proptex.TEXTURES[name]() - blank).sum(2) > 1e-6
        n = int(painted[frame].sum())
        t.check(n == 0, f"the {name}'s picture covers {n} texels of its frame")
