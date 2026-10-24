"""Mansion wall textures: 64 wide x 128 tall (one tile wide, two tall),
column-major in ROM. Row 0 is the ceiling line, row 128 the floor; a height
of h tiles is row 128 - 64h. Generated composites:

  window:<wall>                      window with curtains set in the wall
  dframe:<wall>:<style>:<panel>:<lintel>   door surround (opening left black)
  dclosed:<wall>:<leaf>:<L|R|D>      closed door in its frame
  archf:<wall>:<panel>:<lintel>      cased opening between rooms
"""
import numpy as np
from noise import *

W, H = 64, 128
TEXTURES = {}


def tex(name):
    def deco(fn):
        TEXTURES[name] = fn
        return fn
    return deco


def row_of(h):
    return int(round(H - 64 * h))


def grime(img, rng, amount=0.2, base=4):
    n = fbm(H, W, base, 4, rng)
    return shade(img, 1 - amount + amount * 2 * n * 0.9)


def bottom_dirt(img, start=0.75, amount=0.35):
    t = np.clip((np.arange(H) / H - start) / (1 - start), 0, 1) ** 1.5
    return shade(img, (1 - amount * t)[:, None].repeat(W, 1))


def age(img, rng, stains=0.5, streaks=5):
    st = drip_streaks(H, W, rng, count=streaks, length=(20, 70), width=(2, 5))
    img = shade(img, 1 - 0.30 * st)
    blot = blotches(H, W, rng, base=3, threshold=0.6, softness=0.15)
    img = lerp(img, img * np.array([0.72, 0.64, 0.48]), blot * stains)
    return img


# ------------------------------------------------------------- components
def _motif_damask(mw, mh):
    """A symmetric damask medallion drawn from simple shapes (0..1 coverage)."""
    yy, xx = np.mgrid[0:mh, 0:mw].astype(float)
    cx, cy = (mw - 1) / 2, mh / 2
    ax = np.abs(xx - cx)
    m = np.zeros((mh, mw))
    def ell(y0, x0, ry, rx, rot=0.0):
        c, s_ = np.cos(rot), np.sin(rot)
        dy, dx = yy - y0, ax - x0
        u = (dx * c + dy * s_) / rx
        v = (-dx * s_ + dy * c) / ry
        return np.clip(1.5 - 1.5 * (u * u + v * v), 0, 1)
    # spine bud, side leaves curling out, a crown and a pendant drop
    m = np.maximum(m, ell(cy, 0, mh * 0.30, mw * 0.08))
    m = np.maximum(m, ell(cy - mh * 0.05, mw * 0.20, mh * 0.20, mw * 0.10, 0.6))
    m = np.maximum(m, ell(cy + mh * 0.14, mw * 0.24, mh * 0.13, mw * 0.08, -0.7))
    m = np.maximum(m, ell(cy - mh * 0.30, mw * 0.10, mh * 0.07, mw * 0.07))
    m = np.maximum(m, ell(cy - mh * 0.36, 0, mh * 0.06, mw * 0.06))
    m = np.maximum(m, ell(cy + mh * 0.36, 0, mh * 0.09, mw * 0.045))
    # hollow centre gives it the woven look
    m = np.where(ell(cy, 0, mh * 0.13, mw * 0.035) > 0.5, 0.0, m)
    # lozenge trellis between the medallions
    loz = np.abs(np.abs(yy - cy) / (mh / 2) + ax / (mw / 2) - 1.0)
    m = np.maximum(m, np.clip(1 - loz * mw / 2.2, 0, 1) * 0.9)
    return np.clip(m, 0, 1)


def damask(color_bg, color_fg, rng, motif_w=32, motif_h=44, density=0.5):
    """Two-tone damask wallpaper with an outline tone, half-drop repeat."""
    mot = _motif_damask(motif_w, motif_h)
    pat = np.zeros((H, W))
    for ty in range(-1, H // motif_h + 2):
        for tx in range(-1, W // motif_w + 2):
            oy = ty * motif_h + (motif_h // 2 if tx % 2 else 0)
            ox = tx * motif_w
            ys = slice(max(0, oy), min(H, oy + motif_h))
            xs = slice(max(0, ox), min(W, ox + motif_w))
            if ys.start >= ys.stop or xs.start >= xs.stop:
                continue
            pat[ys, xs] = np.maximum(pat[ys, xs], mot[ys.start - oy:ys.stop - oy, xs.start - ox:xs.stop - ox])
    fill = (pat > density).astype(float)
    edge = ((pat > density - 0.22) & (pat <= density)).astype(float)
    img = rgb(H, W, color_bg)
    img = shade(img, 0.92 + 0.12 * fbm(H, W, 8, 3, rng))
    fg = np.array(color_fg)
    img = lerp(img, img * 0 + fg, fill * 0.9)
    img = lerp(img, img * 0 + (np.array(color_bg) * 0.6 + fg * 0.4) * 0.8, edge * 0.8)
    return img


def floral(color_bg, color_flower, color_leaf, rng, step=16):
    """Small sprigs on a diagonal grid with a faint pinstripe (bedrooms)."""
    img = rgb(H, W, color_bg)
    img = shade(img, 0.93 + 0.1 * fbm(H, W, 8, 3, rng))
    for x in range(0, W, 8):
        vline(img, x, 0, H, np.array(color_bg) * 0.88)
    for gy in range(-1, H // step + 2):
        for gx in range(0, W // step + 1):
            cy = gy * step + (step // 2 if gx % 2 else 0) + 4
            cx = gx * step + 4
            for (dy, dx, c) in ((2, -2, color_leaf), (3, 1, color_leaf), (4, -1, color_leaf), (5, 0, color_leaf)):
                y, x = cy + dy, (cx + dx) % W
                if 0 <= y < H:
                    img[y, x] = c
            for (dy, dx) in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                y, x = cy + dy, (cx + dx) % W
                if 0 <= y < H:
                    img[y, x] = np.array(color_flower) * (1.15 if (dy, dx) == (0, 0) else 1.0)
    return img


def stripes(c1, c2, rng, widths=(6, 2, 8, 2)):
    img = rgb(H, W, c1)
    x = 0; k = 0
    cols = [c1, c2, c1, c2]
    while x < W:
        w = widths[k % len(widths)]
        rect(img, 0, x, H, min(W, x + w), cols[k % 4])
        x += w; k += 1
    return shade(img, 0.9 + 0.15 * fbm(H, W, 8, 3, rng))


def wainscot(img, rng, top_h=0.62, wood=(0.26, 0.15, 0.08), panels=2):
    """Dado rail, raised panels below, skirting board."""
    r_top = row_of(top_h)
    grain = fbm(H, W, 3, 4, rng, aspect=0.2)
    wood_img = shade(rgb(H, W, wood), 0.72 + 0.45 * grain)
    img[r_top:] = wood_img[r_top:]
    pw = W // panels
    for k in range(panels):
        x0 = k * pw + 4
        bevel(img, r_top + 6, x0, H - 10, x0 + pw - 8, 1.25, 0.6)
        bevel(img, r_top + 9, x0 + 3, H - 13, x0 + pw - 11, 0.75, 1.2)
    # chair rail
    rect(img, r_top - 3, 0, r_top + 2, W, np.array(wood) * 1.15)
    hline(img, r_top - 3, 0, W, np.array(wood) * 1.6)
    hline(img, r_top + 1, 0, W, np.array(wood) * 0.5)
    # skirting
    rect(img, H - 8, 0, H, W, np.array(wood) * 0.75)
    hline(img, H - 8, 0, W, np.array(wood) * 1.4)
    return img


def cornice(img, color=(0.62, 0.58, 0.48), depth=7):
    rect(img, 0, 0, depth, W, color)
    hline(img, depth - 1, 0, W, np.array(color) * 0.45)
    hline(img, depth - 3, 0, W, np.array(color) * 1.2)
    hline(img, 2, 0, W, np.array(color) * 0.7)
    for x in range(0, W, 8):     # dentils
        rect(img, depth - 3, x, depth - 1, x + 4, np.array(color) * 0.8)
    return img


def picture_rail(img, h=1.72, wood=(0.24, 0.14, 0.07)):
    r = row_of(h)
    rect(img, r, 0, r + 2, W, wood)
    hline(img, r, 0, W, np.array(wood) * 1.6)
    return img


# ------------------------------------------------------------- materials
@tex('paper_green')
def paper_green(seed=101):
    rng = np.random.default_rng(seed)
    img = damask([0.20, 0.30, 0.22], [0.30, 0.40, 0.28], rng)
    img = cornice(img)
    img = picture_rail(img)
    img = wainscot(img, rng)
    img = age(img, rng, 0.55, 6)
    return np.clip(grime(bottom_dirt(img), rng, 0.15), 0, 1)


@tex('paper_red')
def paper_red(seed=102):
    rng = np.random.default_rng(seed)
    img = damask([0.36, 0.10, 0.10], [0.50, 0.20, 0.14], rng, density=0.58)
    img = cornice(img, (0.58, 0.52, 0.42))
    img = picture_rail(img)
    img = wainscot(img, rng, wood=(0.22, 0.12, 0.07))
    img = age(img, rng, 0.45, 5)
    return np.clip(grime(bottom_dirt(img), rng, 0.15), 0, 1)


@tex('paper_stripe')
def paper_stripe(seed=103):
    rng = np.random.default_rng(seed)
    img = stripes([0.52, 0.46, 0.34], [0.38, 0.30, 0.22], rng, widths=(9, 2, 3, 2))
    img = cornice(img, (0.64, 0.60, 0.50))
    img = picture_rail(img, 1.75)
    img = wainscot(img, rng, top_h=0.6, wood=(0.30, 0.19, 0.10))
    img = age(img, rng, 0.6, 7)
    c = cracks(H, W, rng, 2, (20, 50))
    img = shade(img, 1 - 0.4 * c)
    return np.clip(grime(bottom_dirt(img), rng, 0.15), 0, 1)


@tex('paper_nursery')
def paper_nursery(seed=104):
    """Pale stripes with rows of little ducks and stars."""
    rng = np.random.default_rng(seed)
    img = stripes([0.66, 0.66, 0.56], [0.58, 0.62, 0.58], rng, widths=(8, 8, 8, 8))
    duck = ["..XX....", ".XXXX...", ".XoXX..O", "..XXXXX.", ".XXXXXX.", "..XXXX.."]
    cols = {'X': [0.80, 0.66, 0.30], 'o': [0.10, 0.08, 0.06], 'O': [0.72, 0.42, 0.20]}
    for row, y0 in enumerate(range(14, 110, 22)):
        for k in range(2):
            x0 = (k * 32 + (row % 2) * 16 + 4) % W
            for dy, line in enumerate(duck):
                for dx, ch in enumerate(line):
                    if ch in cols:
                        img[y0 + dy, (x0 + dx) % W] = cols[ch]
            sx, sy = (x0 + 20) % W, y0 + 12
            for (dy, dx) in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                img[sy + dy, (sx + dx) % W] = [0.86, 0.80, 0.56]
    img = cornice(img, (0.72, 0.70, 0.62))
    img = wainscot(img, rng, top_h=0.55, wood=(0.56, 0.52, 0.46))
    img = age(img, rng, 0.75, 9)
    c = cracks(H, W, rng, 2, (20, 40))
    img = shade(img, 1 - 0.35 * c)
    return np.clip(grime(bottom_dirt(img), rng, 0.15), 0, 1)


@tex('paper_floral')
def paper_floral(seed=113):
    rng = np.random.default_rng(seed)
    img = floral([0.56, 0.50, 0.40], [0.62, 0.26, 0.26], [0.26, 0.36, 0.22], rng)
    img = cornice(img, (0.66, 0.62, 0.52))
    img = picture_rail(img, 1.74)
    img = wainscot(img, rng, top_h=0.58, wood=(0.32, 0.20, 0.11))
    img = age(img, rng, 0.6, 7)
    return np.clip(grime(bottom_dirt(img), rng, 0.15), 0, 1)


@tex('paper_study')
def paper_study(seed=114):
    """Bottle-green paper with gold pinstripes over dark oak (the doctor's rooms)."""
    rng = np.random.default_rng(seed)
    img = stripes([0.14, 0.22, 0.16], [0.36, 0.30, 0.14], rng, widths=(15, 1, 15, 1))
    img = cornice(img, (0.34, 0.24, 0.12), 8)
    img = picture_rail(img, 1.72, (0.30, 0.20, 0.10))
    img = wainscot(img, rng, top_h=0.66, wood=(0.20, 0.11, 0.06))
    img = age(img, rng, 0.3, 4)
    return np.clip(grime(bottom_dirt(img), rng, 0.12), 0, 1)


@tex('library_shelves')
def library_shelves(seed=115):
    """Floor-to-cornice bookshelves set into the wall."""
    rng = np.random.default_rng(seed)
    wood = np.array([0.24, 0.13, 0.07])
    img = shade(rgb(H, W, wood), 0.7 + 0.4 * fbm(H, W, 3, 4, rng, aspect=0.2))
    img = cornice(img, (0.28, 0.16, 0.08), 7)
    shelves = [10, 33, 56, 79, 102]
    spines = [[0.42, 0.10, 0.08], [0.12, 0.22, 0.14], [0.14, 0.14, 0.30], [0.50, 0.36, 0.16],
              [0.30, 0.18, 0.10], [0.20, 0.08, 0.10], [0.36, 0.32, 0.26]]
    for i, y0 in enumerate(shelves):
        y1 = (shelves[i + 1] if i + 1 < len(shelves) else H - 9) - 3
        rect(img, y0, 3, y1, 61, wood * 0.35)                 # shadowed back
        x = 4
        while x < 60:
            w = int(rng.integers(2, 5))
            h = int(rng.integers(int((y1 - y0) * 0.65), y1 - y0))
            c = np.array(spines[int(rng.integers(len(spines)))]) * (0.8 + 0.4 * rng.random())
            if rng.random() < 0.08:          # a gap or a leaning book
                x += w; continue
            rect(img, y1 - h, x, y1, min(60, x + w), c)
            vline(img, x, y1 - h, y1, c * 1.35)
            if h > 10 and rng.random() < 0.6:
                hline(img, y1 - h + 3, x, min(60, x + w), [0.62, 0.50, 0.24])   # gilt band
            x += w
        rect(img, y1, 1, y1 + 3, 63, wood * 1.25)              # shelf board
        hline(img, y1, 1, 63, wood * 1.8)
    vline(img, 1, 8, H, wood * 1.4); vline(img, 2, 8, H, wood * 0.9)
    vline(img, 62, 8, H, wood * 0.6)
    rect(img, H - 8, 0, H, W, wood * 0.75)
    img = age(img, rng, 0.2, 2)
    return np.clip(grime(img, rng, 0.12), 0, 1)


@tex('tile_bath')
def tile_bath(seed=116):
    """Black-and-white tiles to shoulder height, plaster above."""
    rng = np.random.default_rng(seed)
    img = rgb(H, W, [0.62, 0.62, 0.56])
    img = shade(img, 0.88 + 0.2 * fbm(H, W, 8, 3, rng))
    img = cornice(img, (0.70, 0.70, 0.64), 5)
    r0 = row_of(1.05)
    for y in range(r0, H - 4, 8):
        for x in range(0, W, 8):
            dark = ((x // 8) + (y - r0) // 8) % 2 == 0 and y < r0 + 9
            c = np.array([0.16, 0.18, 0.18]) if dark else np.array([0.78, 0.78, 0.74]) * (0.92 + 0.1 * rng.random())
            rect(img, y, x, y + 7, x + 7, c)
        hline(img, y + 7, 0, W, [0.36, 0.36, 0.32])
    for x in range(0, W, 8):
        vline(img, x + 7, r0, H - 4, [0.36, 0.36, 0.32])
    rect(img, H - 4, 0, H, W, [0.12, 0.13, 0.13])
    img = age(img, rng, 0.55, 7)
    return np.clip(grime(bottom_dirt(img), rng, 0.15), 0, 1)


@tex('pipes_cellar')
def pipes_cellar(seed=117):
    """Brick with lagged pipes and a valve wheel (boiler and generator rooms)."""
    img = brick_cellar(seed)
    rng = np.random.default_rng(seed)
    for (y, r, c) in ((20, 3, [0.36, 0.30, 0.24]), (30, 2, [0.40, 0.26, 0.16]), (84, 4, [0.44, 0.44, 0.40])):
        for dy in range(-r, r + 1):
            t = 1 - (dy / (r + 0.5)) ** 2
            hline(img, y + dy, 0, W, np.array(c) * (0.55 + 0.6 * t))
        for x in range(6, W, 22):
            rect(img, y - r - 1, x, y + r + 2, x + 3, np.array(c) * 0.7)
    for k in range(12):                       # valve wheel
        a = k * np.pi / 6
        img[int(60 + 6 * np.sin(a)), int(40 + 6 * np.cos(a))] = [0.60, 0.16, 0.10]
    rect(img, 34, 39, 84, 42, [0.40, 0.40, 0.36])
    rust = blotches(H, W, rng, 6, 4, 0.6, 0.12)
    img = lerp(img, img * np.array([1.1, 0.6, 0.3]), rust * 0.4)
    return np.clip(img, 0, 1)


@tex('stone_well')
def stone_well(seed=118):
    """Wet black stone of the spring chamber."""
    img = stone_cellar(seed)
    rng = np.random.default_rng(seed)
    img = img * np.array([0.62, 0.70, 0.74])
    st = drip_streaks(H, W, rng, count=14, length=(40, 120), width=(1, 3))
    img = lerp(img, np.array([0.30, 0.36, 0.38]), st * 0.5)
    t = np.clip((np.arange(H) / H - 0.8) / 0.2, 0, 1)[:, None, None]
    img = img * (1 - 0.6 * t) + np.array([0.04, 0.06, 0.07]) * 0.6 * t
    return np.clip(img, 0, 1)


@tex('chapel_wall')
def chapel_wall(seed=119):
    """Whitewashed attic boards under the eaves, soot above the candles."""
    rng = np.random.default_rng(seed)
    img = attic_boards(seed)
    img = lerp(img, np.array([0.66, 0.64, 0.56]), 0.6)
    img = shade(img, 0.85 + 0.25 * fbm(H, W, 6, 3, rng))
    soot = np.exp(-((np.arange(H)[:, None] - 20) / 22.0) ** 2) * (0.6 + 0.4 * fbm(H, W, 4, 3, rng))
    img = shade(img, 1 - 0.5 * soot)
    img = age(img, rng, 0.5, 8)
    return np.clip(bottom_dirt(img, 0.7, 0.3), 0, 1)


@tex('larder')
def larder(seed=120):
    """Pantry shelves over plaster: round-shouldered preserving jars with
    metal lids and paper labels, squat tins and a few tall bottles, each
    shaded as a cylinder so they read as jars and not as book spines."""
    rng = np.random.default_rng(seed)
    img = plaster(seed)
    wood = np.array([0.40, 0.30, 0.18])

    def cyl(i, w):                      # brightness across a cylinder
        return 0.62 + 0.55 * np.sin(np.pi * (i + 0.5) / w) - (0.12 if i == 0 else 0.0)

    def jar(x, y, w, h, c, label):
        for i in range(w):
            k = cyl(i, w)
            top = y - h + (1 if i in (0, w - 1) else 0)          # round shoulders
            vline(img, x + i, top, y, np.array(c) * k)
            if label and i not in (0, w - 1):
                vline(img, x + i, y - h // 2 - 1, y - h // 2 + 2, np.array([0.70, 0.64, 0.50]) * k)
        lid = np.array([0.52, 0.50, 0.44]) if rng.random() < 0.6 else np.array([0.46, 0.20, 0.14])
        for i in range(1, w - 1):
            vline(img, x + i, y - h - 2, y - h, lid * cyl(i - 1, w - 2))
        img[y - h + 1, x + 1] = np.array([0.80, 0.78, 0.70])           # a glint on the glass

    def tin(x, y, w, h, c):
        for i in range(w):
            k = cyl(i, w)
            vline(img, x + i, y - h, y, np.array(c) * k)
            img[y - h, x + i] = np.array([0.62, 0.62, 0.58]) * k      # rims
            img[y - 1, x + i] = np.array([0.50, 0.50, 0.46]) * k

    def bottle(x, y, h, c):
        for i in range(3):
            vline(img, x + i, y - h + 4, y, np.array(c) * cyl(i, 3))
        vline(img, x + 1, y - h, y - h + 4, np.array(c) * 1.1)
        img[y - h, x + 1] = np.array([0.30, 0.22, 0.12])            # cork

    jars = [[0.55, 0.30, 0.12], [0.42, 0.40, 0.18], [0.50, 0.14, 0.12], [0.58, 0.46, 0.20], [0.36, 0.34, 0.26]]
    tins = [[0.40, 0.42, 0.44], [0.48, 0.16, 0.12], [0.20, 0.26, 0.36]]
    for y in (30, 54, 78):
        x = 2 + int(rng.integers(0, 3))
        while x < 58:
            r = rng.random()
            if r < 0.12:
                x += int(rng.integers(3, 6))                         # a gap
                continue
            if r < 0.62:
                w = int(rng.integers(6, 9)); h = int(rng.integers(8, 12))
                if x + w > 62: break
                jar(x, y, w, h, jars[int(rng.integers(len(jars)))], rng.random() < 0.6)
            elif r < 0.86:
                w = int(rng.integers(6, 8)); h = int(rng.integers(5, 8))
                if x + w > 62: break
                tin(x, y, w, h, tins[int(rng.integers(len(tins)))])
            else:
                w = 3; h = int(rng.integers(13, 17))
                if x + w > 62: break
                bottle(x, y, h, [[0.16, 0.26, 0.14], [0.30, 0.18, 0.08]][int(rng.integers(2))])
            x += w + int(rng.integers(1, 3))
        rect(img, y, 1, y + 3, 63, wood)
        hline(img, y, 1, 63, wood * 1.5)
        rect(img, y + 3, 1, y + 4, 63, wood * 0.45)                 # its shadow on the wall
    return np.clip(img, 0, 1)


@tex('panel_oak')
def panel_oak(seed=105):
    """Full-height oak panelling (hall, library, study)."""
    rng = np.random.default_rng(seed)
    wood = np.array([0.27, 0.16, 0.08])
    grain = fbm(H, W, 3, 4, rng, aspect=0.15)
    img = shade(rgb(H, W, wood), 0.72 + 0.45 * grain)
    img = cornice(img, (0.30, 0.19, 0.10), 8)
    for (y0, y1) in ((12, 76), (82, 120)):
        for x0 in (3, 35):
            bevel(img, y0, x0, y1, x0 + 26, 1.3, 0.55)
            bevel(img, y0 + 3, x0 + 3, y1 - 3, x0 + 23, 0.7, 1.25)
    hline(img, 79, 0, W, wood * 1.6)
    rect(img, H - 8, 0, H, W, wood * 0.7)
    img = age(img, rng, 0.25, 3)
    return np.clip(grime(bottom_dirt(img, 0.8, 0.3), rng, 0.12), 0, 1)


@tex('panel_oak_deep')
def panel_oak_deep():
    """The oak panelling of the stairwell, falling away into the dark below
    the gallery: the lower half fades to black, so the walls seem to go on
    down past where the floor would be."""
    img = panel_oak()
    t = np.clip((np.arange(H) - 70) / 40, 0, 1) ** 1.3
    return np.clip(img * (1 - 0.97 * t)[:, None, None], 0, 1)


@tex('plaster')
def plaster(seed=106):
    rng = np.random.default_rng(seed)
    img = rgb(H, W, [0.60, 0.56, 0.46])
    img = shade(img, 0.88 + 0.2 * fbm(H, W, 8, 3, rng))
    img = cornice(img, (0.64, 0.60, 0.50), 5)
    img = wainscot(img, rng, top_h=0.5, wood=(0.32, 0.30, 0.24))
    img = age(img, rng, 0.8, 9)
    c = cracks(H, W, rng, 3, (20, 60))
    img = shade(img, 1 - 0.45 * c)
    return np.clip(grime(bottom_dirt(img), rng, 0.2), 0, 1)


@tex('tile_kitchen')
def tile_kitchen(seed=107):
    rng = np.random.default_rng(seed)
    img = rgb(H, W, [0.58, 0.55, 0.46])
    img = shade(img, 0.88 + 0.2 * fbm(H, W, 8, 3, rng))
    r0 = row_of(1.0)
    for y in range(r0, H - 6, 8):
        for x in range(0, W, 8):
            c = np.array([0.72, 0.72, 0.66]) * (0.92 + 0.12 * rng.random())
            rect(img, y, x, y + 7, x + 7, c)
        hline(img, y + 7, 0, W, [0.30, 0.30, 0.26])
    for x in range(0, W, 8):
        vline(img, x + 7, r0, H - 6, [0.30, 0.30, 0.26])
    rect(img, r0 - 3, 0, r0, W, [0.22, 0.30, 0.26])          # green border tiles
    rect(img, H - 6, 0, H, W, [0.16, 0.16, 0.14])
    img = age(img, rng, 0.5, 6)
    return np.clip(grime(bottom_dirt(img), rng, 0.18), 0, 1)


@tex('stone_cellar')
def stone_cellar(seed=108):
    rng = np.random.default_rng(seed)
    img = rgb(H, W, [0.30, 0.29, 0.26])
    img = shade(img, 0.75 + 0.45 * fbm(H, W, 6, 4, rng))
    y = 0
    k = 0
    while y < H:
        h = int(rng.integers(11, 17))
        off = int(rng.integers(0, 32)) if k % 2 else 0
        x = -off
        while x < W:
            w = int(rng.integers(18, 30))
            c = 0.8 + 0.35 * rng.random()
            x0, x1 = max(0, x + 1), min(W, x + w - 1)
            if x1 > x0:
                img[y + 1:min(H, y + h - 1), x0:x1] *= c
                bevel(img, y + 1, x0, min(H, y + h - 1), x1, 1.2, 0.7)
            x += w
        hline(img, min(H - 1, y + h - 1), 0, W, [0.10, 0.10, 0.09]) if y + h - 1 < H else None
        y += h; k += 1
    st = drip_streaks(H, W, rng, count=8, length=(30, 90), width=(2, 4))
    img = lerp(img, img * np.array([0.6, 0.65, 0.55]), st * 0.6)
    moss = blotches(H, W, rng, base=4, threshold=0.62, softness=0.1)
    img = lerp(img, img * np.array([0.6, 0.9, 0.55]), moss * 0.5)
    return np.clip(bottom_dirt(img, 0.6, 0.4), 0, 1)


@tex('brick_cellar')
def brick_cellar(seed=109):
    rng = np.random.default_rng(seed)
    img = rgb(H, W, [0.20, 0.17, 0.15])
    for row in range(0, H, 8):
        off = 8 if (row // 8) % 2 else 0
        for x in range(-off, W, 16):
            c = np.array([0.42, 0.20, 0.14]) * (0.75 + 0.4 * rng.random())
            x0, x1 = max(0, x), min(W, x + 15)
            if x1 > x0:
                rect(img, row, x0, row + 7, x1, c)
    img = shade(img, 0.75 + 0.4 * fbm(H, W, 6, 4, rng))
    salt = blotches(H, W, rng, base=4, threshold=0.6, softness=0.1)
    img = lerp(img, np.array([0.55, 0.52, 0.48]), salt * 0.45 * (np.arange(H)[:, None] / H))
    return np.clip(bottom_dirt(img, 0.5, 0.45), 0, 1)


@tex('attic_boards')
def attic_boards(seed=110):
    rng = np.random.default_rng(seed)
    img = np.zeros((H, W, 3))
    x = 0
    while x < W:
        w = int(rng.integers(7, 12))
        c = np.array([0.33, 0.24, 0.15]) * (0.7 + 0.45 * rng.random())
        grain = fbm(H, W, 2, 4, rng, aspect=6)
        sl = shade(rgb(H, W, c), 0.7 + 0.5 * grain)
        img[:, x:min(W, x + w)] = sl[:, x:min(W, x + w)]
        vline(img, min(W - 1, x + w - 1), 0, H, [0.07, 0.05, 0.03])
        x += w
    for y in (20, 100):
        for xx in range(3, W, 10):
            img[y, xx] = [0.15, 0.13, 0.12]
    st = drip_streaks(H, W, rng, count=4, length=(30, 80), width=(2, 4))
    img = shade(img, 1 - 0.35 * st)
    return np.clip(bottom_dirt(img, 0.7, 0.3), 0, 1)


@tex('padded_cell')
def padded_cell(seed=111):
    rng = np.random.default_rng(seed)
    img = rgb(H, W, [0.62, 0.60, 0.52])
    img = shade(img, 0.85 + 0.2 * fbm(H, W, 6, 3, rng))
    for y in range(0, H, 16):
        hline(img, y, 0, W, [0.40, 0.38, 0.32])
    for x in range(0, W, 16):
        vline(img, x, 0, H, [0.40, 0.38, 0.32])
    for y in range(0, H, 16):
        for x in range(0, W, 16):
            img[y, x] = [0.25, 0.24, 0.20]
    img = age(img, rng, 0.9, 10)
    scr = np.zeros((H, W))
    for _ in range(6):
        x0 = int(rng.integers(5, 58)); y0 = int(rng.integers(40, 110))
        for k in range(14):
            scr[min(H - 1, y0 + k), min(W - 1, x0 + k // 4)] = 1
    img = lerp(img, np.array([0.25, 0.10, 0.07]), scr * 0.7)
    return np.clip(grime(img, rng, 0.2), 0, 1)


@tex('lift_gate')
def lift_gate(seed=112):
    rng = np.random.default_rng(seed)
    img = brick_cellar(seed + 3) if False else stone_cellar(seed + 5)
    rect(img, 22, 6, H, 58, [0.04, 0.04, 0.04])
    for k in range(8):
        x = 8 + k * 6
        for y in range(24, H):
            off = ((y // 6) % 2) * 3
            xx = x + (off if (y % 6) < 3 else 3 - off)
            if 6 <= xx < 58:
                img[y, xx] = [0.48, 0.45, 0.40]
    for y in (24, 70, 124):
        hline(img, y, 6, 58, [0.52, 0.50, 0.44])
    rect(img, 18, 3, H, 6, [0.28, 0.27, 0.25]); rect(img, 18, 58, H, 61, [0.28, 0.27, 0.25])
    rect(img, 16, 3, 22, 61, [0.28, 0.27, 0.25])
    img = lerp(img, np.array([0.8, 0.2, 0.1]), disc(H, W, 50, 62, 1.6))     # call button
    rust = blotches(H, W, rng, 6, 4, 0.58, 0.12)
    img = lerp(img, img * np.array([1.1, 0.6, 0.3]), rust * 0.5)
    return np.clip(img, 0, 1)


# ------------------------------------------------------------- composites
def make_window(wall):
    img = TEXTURES[wall]().copy()
    rng = np.random.default_rng(len(wall) * 13)
    top, sill = row_of(1.78), row_of(0.62)
    x0, x1 = 12, 52
    # night sky with rain through the panes
    t = np.linspace(0, 1, H)[:, None, None]
    sky = np.array([0.05, 0.06, 0.10]) * (1 - t) + np.array([0.02, 0.03, 0.05]) * t
    sky = np.repeat(sky, W, axis=1)
    rain = drip_streaks(H, W, rng, count=14, length=(6, 20), width=(1, 2), from_top=False)
    sky = lerp(sky, np.array([0.20, 0.24, 0.32]), rain * 0.6)
    img[top:sill, x0:x1] = sky[top:sill, x0:x1]
    frame = np.array([0.50, 0.48, 0.42])
    for x in (x0, (x0 + x1) // 2, x1 - 2):
        rect(img, top, x, sill, x + 2, frame)
    for y in range(top, sill, 18):
        hline(img, y, x0, x1, frame)
    rect(img, top - 3, x0 - 3, top, x1 + 3, frame * 0.8)
    rect(img, sill, x0 - 5, sill + 4, x1 + 5, frame * 0.9)        # sill
    hline(img, sill, x0 - 5, x1 + 5, frame * 1.3)
    # heavy curtains either side
    drape = np.array([0.32, 0.07, 0.08])
    for (a, b) in ((x0 - 8, x0 + 5), (x1 - 5, x1 + 8)):
        for x in range(max(0, a), min(W, b)):
            fold = 0.7 + 0.35 * np.sin((x - a) * 1.3)
            img[top - 8:sill + 14, x] = drape * fold * (0.9 + 0.2 * rng.random())
    rect(img, top - 10, x0 - 10, top - 7, x1 + 10, [0.30, 0.22, 0.10])  # rail
    return np.clip(img, 0, 1)


def make_frame(wall, style, panel, lintel):
    img = TEXTURES[wall]().copy()
    top = H - 2 * lintel
    a, b = panel, W - panel
    if style == 'metal':
        col = np.array([0.33, 0.34, 0.33])
    else:
        col = np.array([0.26, 0.15, 0.08])
    cw = 4
    # casing: jambs and head
    rect(img, top - cw, a - cw, H, a, col)
    rect(img, top - cw, b, H, b + cw, col)
    rect(img, top - cw, a - cw, top, b + cw, col)
    vline(img, a - cw, top - cw, H, col * 1.5)
    vline(img, b + cw - 1, top - cw, H, col * 0.6)
    hline(img, top - cw, a - cw, b + cw, col * 1.5)
    vline(img, a - 1, top, H, col * 0.5)
    vline(img, b, top, H, col * 0.5)
    rect(img, top - cw - 3, a - cw - 2, top - cw, b + cw + 2, col * 1.1)    # pediment
    hline(img, top - cw - 3, a - cw - 2, b + cw + 2, col * 1.6)
    img[top:, a:b] = 0.02
    return np.clip(img, 0, 1)


def make_closed(wall, leaf, variant):
    import proptex
    double = variant == 'D'
    geom = (4, 48) if double else (13, 45)
    if leaf.startswith('leaf_'):
        style = 'metal' if leaf == 'leaf_metal' else 'wood'
    img = make_frame(wall, style, *geom)
    panel, lintel = geom
    top = H - 2 * lintel
    a, b = panel, W - panel
    lf = proptex.TEXTURES[leaf]()            # 64x64, hinge at u=0, handle at u=63
    hgt = H - top
    def put(x0, x1, mirror):
        ys = (np.arange(hgt) * 64 // hgt).clip(0, 63)
        xs = (np.arange(x1 - x0) * 64 // (x1 - x0)).clip(0, 63)
        if mirror:
            xs = 63 - xs
        img[top:, x0:x1] = lf[ys][:, xs]
    if double:
        m = (a + b) // 2
        put(a, m, False)
        put(m, b, True)
    else:
        put(a, b, variant == 'R')
    return np.clip(img, 0, 1)


def make_arch(wall, panel, lintel):
    img = make_frame(wall, 'wood', panel, lintel)
    return img


def make_deco(wall, kind):
    """Wall decor painted into the wall texture: framed pictures, mirrors,
    sconces. Costs nothing to draw, unlike a 3D prop."""
    import proptex
    img = TEXTURES[wall]().copy()
    gilt = np.array([0.56, 0.42, 0.16])
    def frame(y0, x0, y1, x1, content, fw=3):
        rect(img, y0 - fw, x0 - fw, y1 + fw, x1 + fw, gilt * 0.8)
        hline(img, y0 - fw, x0 - fw, x1 + fw, gilt * 1.4)
        vline(img, x0 - fw, y0 - fw, y1 + fw, gilt * 1.25)
        hline(img, y1 + fw - 1, x0 - fw, x1 + fw, gilt * 0.45)
        vline(img, x1 + fw - 1, y0 - fw, y1 + fw, gilt * 0.5)
        rect(img, y0 - 1, x0 - 1, y1 + 1, x1 + 1, gilt * 0.35)
        hh, ww = y1 - y0, x1 - x0
        ys = (np.arange(hh) * content.shape[0] // hh).clip(0, content.shape[0] - 1)
        xs = (np.arange(ww) * content.shape[1] // ww).clip(0, content.shape[1] - 1)
        img[y0:y1, x0:x1] = content[ys][:, xs]
        # drop shadow under the frame
        rect(img, y1 + fw, x0 - fw + 2, y1 + fw + 2, x1 + fw + 2, img[min(H - 1, y1 + fw + 3), x0] * 0.55)
    if kind == 'portrait':
        frame(row_of(1.62), 20, row_of(0.98), 44, proptex.TEXTURES['portrait']())
    elif kind == 'landscape':
        frame(row_of(1.5), 10, row_of(1.06), 54, proptex.TEXTURES['landscape']())
    elif kind == 'mirror':
        glass = proptex.TEXTURES['mirror']()
        y0, y1 = row_of(1.62), row_of(0.98)
        yy, xx = np.mgrid[0:H, 0:W]
        ov = ((yy - (y0 + y1) / 2) / ((y1 - y0) / 2)) ** 2 + ((xx - 32) / 13.0) ** 2
        ring = (ov <= 1.35) & (ov > 1.0)
        inner = ov <= 1.0
        gy = ((yy - y0) * 64 // max(1, y1 - y0)).clip(0, 63)
        gx = ((xx - 19) * 64 // 26).clip(0, 63)
        img[inner] = glass[gy[inner], gx[inner]]
        img[ring] = gilt[None, :] * (0.7 + 0.5 * ((yy[ring] - y0) < (y1 - y0) / 3))[:, None]
    elif kind in ('sconce', 'sconce_off'):
        lit = kind == 'sconce'
        y = row_of(1.42)
        brass = np.array([0.52, 0.40, 0.18])
        rect(img, y + 4, 30, y + 12, 34, brass * 0.7)          # back plate
        rect(img, y + 8, 27, y + 10, 37, brass)                 # arm
        glow = np.array([1.0, 0.86, 0.50]) if lit else np.array([0.34, 0.32, 0.26])
        for dy in range(0, 9):
            half = 2 + dy // 3
            hline(img, y - 2 + dy, 32 - half, 32 + half, glow * (1.0 - 0.04 * dy))
        hline(img, y + 7, 28, 36, brass * 1.3)
        if lit:   # halo on the paper around the lamp
            yy, xx = np.mgrid[0:H, 0:W]
            d = np.sqrt(((yy - y - 2) / 1.3) ** 2 + (xx - 32) ** 2)
            halo = np.clip(1 - d / 22.0, 0, 1) ** 2
            img = img * (1 + 0.9 * halo[..., None]) + np.array([0.16, 0.11, 0.04]) * halo[..., None]
    elif kind == 'crucifix':
        y = row_of(1.6)
        wood = np.array([0.26, 0.15, 0.08])
        rect(img, y, 30, y + 26, 34, wood); rect(img, y + 6, 24, y + 10, 40, wood)
        rect(img, y + 8, 31, y + 18, 33, [0.70, 0.62, 0.48])
    elif kind == 'clock':
        y0 = row_of(1.62)
        wood = np.array([0.30, 0.17, 0.09])
        rect(img, y0, 22, y0 + 40, 42, wood)
        bevel(img, y0, 22, y0 + 40, 42, 1.3, 0.6)
        yy, xx = np.mgrid[0:H, 0:W]
        face = ((yy - y0 - 12) ** 2 + (xx - 32) ** 2) <= 64
        img[face] = [0.80, 0.76, 0.62]
        img[y0 + 12, 32:38] = [0.1, 0.08, 0.06]; img[y0 + 6:y0 + 13, 32] = [0.1, 0.08, 0.06]
        rect(img, y0 + 24, 30, y0 + 36, 34, [0.56, 0.44, 0.18])          # pendulum
    else:
        raise KeyError(kind)
    return np.clip(img, 0, 1)


def ensure(name):
    if name in TEXTURES:
        return
    p = name.split(':')
    if p[0] == 'window':
        TEXTURES[name] = lambda w=p[1]: make_window(w)
    elif p[0] == 'dframe':
        TEXTURES[name] = lambda w=p[1], s=p[2], pa=int(p[3]), li=int(p[4]): make_frame(w, s, pa, li)
    elif p[0] == 'dclosed':
        TEXTURES[name] = lambda w=p[1], l=p[2], v=p[3]: make_closed(w, l, v)
    elif p[0] == 'deco':
        TEXTURES[name] = lambda w=p[1], k=p[2]: make_deco(w, k)
    elif p[0] == 'archf':
        TEXTURES[name] = lambda w=p[1], pa=int(p[2]), li=int(p[3]): make_arch(w, pa, li)
    else:
        raise KeyError(f"unknown wall texture {name}")
