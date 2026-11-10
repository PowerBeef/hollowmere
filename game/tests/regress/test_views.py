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
