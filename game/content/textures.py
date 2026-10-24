"""Procedural 64x64 textures for Hollowmere. Each generator returns an
(64, 64, 3) float RGB array in [0,1]. Walls tile horizontally, floors and
ceilings tile in both directions."""
import numpy as np
from noise import *

S = 64
TEXTURES = {}


def tex(name):
    def deco(fn):
        TEXTURES[name] = fn
        return fn
    return deco


def grime(img, rng, amount=0.25, base=4):
    n = fbm(S, S, base, 4, rng)
    return shade(img, 1 - amount + amount * 2 * n * 0.9)


def bottom_dirt(img, start=0.6, amount=0.35):
    h, w = img.shape[:2]
    t = np.clip((np.arange(h) / h - start) / (1 - start), 0, 1) ** 1.5
    return shade(img, (1 - amount * t)[:, None].repeat(w, 1))


# ----------------------------------------------------------------- walls --

@tex('plaster_green')
def plaster_green(seed=1):
    rng = np.random.default_rng(seed)
    cream = np.array([0.70, 0.66, 0.52])
    green = np.array([0.30, 0.42, 0.34])
    img = rgb(S, S, cream)
    img = shade(img, 0.9 + 0.2 * fbm(S, S, 8, 3, rng))
    lower = 36
    img[lower:] = green
    img[lower:] = shade(img[lower:], 0.85 + 0.25 * fbm(S - lower, S, 6, 3, rng, wrap=False)[..., None][:, :, 0])
    # dado rail
    rect(img, lower - 3, 0, lower, S, [0.28, 0.20, 0.12])
    hline(img, lower - 3, 0, S, [0.42, 0.31, 0.19])
    hline(img, lower - 1, 0, S, [0.15, 0.10, 0.06])
    # baseboard
    rect(img, 58, 0, 64, S, [0.16, 0.13, 0.10])
    hline(img, 58, 0, S, [0.26, 0.21, 0.16])
    # peeling paint on green: patches showing plaster
    peel = blotches(S, S, rng, base=6, threshold=0.68, softness=0.04)
    peel[:lower] = 0; peel[57:] = 0
    img = lerp(img, img * 0 + np.array([0.55, 0.52, 0.42]), peel * 0.9)
    # water stains from the top
    st = drip_streaks(S, S, rng, count=5, length=(15, 45), width=(2, 5))
    img = shade(img, 1 - 0.35 * st)
    stain = blotches(S, S, rng, base=3, threshold=0.62, softness=0.15)
    img = lerp(img, img * np.array([0.75, 0.68, 0.5]), stain * 0.6)
    img = bottom_dirt(img, 0.55, 0.3)
    c = cracks(S, S, rng, 2, (10, 25))
    img = shade(img, 1 - 0.45 * c)
    return grime(img, rng, 0.15)


@tex('plaster_damaged')
def plaster_damaged(seed=2):
    img = plaster_green(seed + 10)
    rng = np.random.default_rng(seed)
    # big hole revealing lath/brick
    hole = blotches(S, S, rng, base=3, threshold=0.66, softness=0.03)
    hole[:6] = 0; hole[56:] = 0
    lath = rgb(S, S, [0.30, 0.22, 0.14])
    for y in range(0, S, 4):
        lath[y:y + 1] *= 0.4
    lath = shade(lath, 0.7 + 0.3 * fbm(S, S, 16, 2, rng))
    img = lerp(img, lath, hole)
    edge = np.clip(hole * (1 - hole) * 4, 0, 1)
    img = shade(img, 1 - 0.5 * edge)
    # mold
    mold = blotches(S, S, rng, base=8, threshold=0.65, softness=0.1)
    img = lerp(img, img * np.array([0.45, 0.5, 0.35]), mold * 0.7)
    return img


@tex('tile_white')
def tile_white(seed=3, blood=False):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.74, 0.76, 0.72])
    T = 8
    for ty in range(S // T):
        for tx in range(S // T):
            v = rng.uniform(0.86, 1.04)
            tint = np.array([1, 1, 1]) * v + rng.normal(0, 0.015, 3)
            img[ty * T:(ty + 1) * T, tx * T:(tx + 1) * T] *= tint
            # glaze highlight
            img[ty * T + 1, tx * T + 1:tx * T + 4] *= 1.08
    img = np.clip(img, 0, 1)
    grout = np.zeros((S, S))
    grout[::T, :] = 1; grout[:, ::T] = 1
    gn = fbm(S, S, 8, 3, rng)
    img = lerp(img, np.array([0.30, 0.30, 0.26]) * (0.6 + 0.6 * gn)[..., None], grout)
    # chipped tiles
    for _ in range(4):
        y, x = rng.integers(0, S - 4), rng.integers(0, S - 4)
        ch = disc(S, S, y + 2, x + 2, rng.uniform(1.2, 2.6))
        img = lerp(img, np.array([0.45, 0.42, 0.36]), ch * 0.8)
    st = drip_streaks(S, S, rng, count=4, length=(20, 60), width=(1, 3))
    img = shade(img, 1 - 0.3 * st)
    img = lerp(img, img * np.array([0.8, 0.72, 0.55]), blotches(S, S, rng, 3, 4, 0.6, 0.2) * 0.5)
    img = bottom_dirt(img, 0.5, 0.45)
    img = shade(img, 1 - 0.6 * cracks(S, S, rng, 2, (12, 30)))
    if blood:
        b = blotches(S, S, rng, base=4, threshold=0.62, softness=0.05)
        b[:20] *= 0.2
        smear = drip_streaks(S, S, rng, count=7, length=(10, 30), width=(2, 4), from_top=False)
        mask = np.clip(b + smear * 0.8, 0, 1)
        img = lerp(img, np.array([0.30, 0.03, 0.02]) * (0.7 + 0.5 * fbm(S, S, 16, 2, rng))[..., None], mask * 0.92)
        # handprint
        hp = np.zeros((S, S))
        cy, cx = 28, 22
        hp += ellipse(S, S, cy, cx, 5, 4)
        for i, (dy, dx) in enumerate([(-9, -5), (-11, -1), (-11, 3), (-9, 6), (-2, 8)]):
            for k in range(5):
                hp += disc(S, S, cy + dy * (0.55 + k * 0.12), cx + dx * (0.55 + k * 0.12), 1.3)
        hp = np.clip(hp, 0, 1)
        img = lerp(img, np.array([0.25, 0.02, 0.02]), hp * 0.85)
    return grime(img, rng, 0.12)


@tex('tile_blood')
def tile_blood(seed=4):
    return tile_white(seed, blood=True)


@tex('wood_panel')
def wood_panel(seed=5):
    rng = np.random.default_rng(seed)
    base = np.array([0.33, 0.20, 0.11])
    grain = fbm(S, S, 2, 4, rng, aspect=6)
    img = rgb(S, S, base)
    img = shade(img, 0.75 + 0.5 * grain)
    # panels: 2 panels per 64 px horizontally, upper wallpaper section
    wp = rgb(24, S, [0.42, 0.36, 0.26])
    pat = np.zeros((24, S))
    for y in range(24):
        for x in range(S):
            if (x % 8 == 4 and y % 12 in (2, 3, 4)) or ((x + 4) % 8 == 4 and y % 12 in (8, 9, 10)):
                pat[y, x] = 1
    wp = lerp(wp, np.array([0.30, 0.24, 0.17]), pat * 0.8)
    wp = shade(wp, 0.85 + 0.25 * fbm(24, S, 8, 3, rng, wrap=False))
    img[:24] = wp
    rect(img, 24, 0, 27, S, [0.22, 0.13, 0.07]); hline(img, 24, 0, S, [0.45, 0.30, 0.18])
    for px in (0, 32):
        y0, x0, y1, x1 = 31, px + 3, 58, px + 29
        img[y0:y1, x0:x1] = shade(img[y0:y1, x0:x1], 1.1)
        bevel(img, y0, x0, y1, x1, 0.6, 1.4)
        bevel(img, y0 + 1, x0 + 1, y1 - 1, x1 - 1, 1.25, 0.65)
    rect(img, 59, 0, 64, S, [0.14, 0.08, 0.05])
    st = drip_streaks(S, S, rng, count=3, length=(10, 30), width=(2, 4))
    img = shade(img, 1 - 0.3 * st)
    return grime(img, rng, 0.15)


@tex('brick')
def brick(seed=6):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.40, 0.20, 0.14])
    mortar = np.zeros((S, S))
    BH, BW = 8, 16
    for row in range(S // BH):
        off = (BW // 2) * (row % 2)
        mortar[row * BH, :] = 1
        for bx in range(0, S, BW):
            x = (bx + off) % S
            mortar[row * BH:(row + 1) * BH, x] = 1
            v = rng.uniform(0.7, 1.15)
            tint = np.array([v, v * rng.uniform(0.85, 1.05), v * rng.uniform(0.8, 1.0)])
            xs = [(x + i) % S for i in range(1, BW)]
            img[row * BH + 1:(row + 1) * BH, xs] *= tint
    img = shade(img, 0.75 + 0.45 * fbm(S, S, 16, 3, rng))
    img = lerp(img, np.array([0.28, 0.26, 0.22]) * (0.7 + 0.4 * fbm(S, S, 8, 2, rng))[..., None], mortar)
    # efflorescence (white salt) and damp
    salt = blotches(S, S, rng, 4, 4, 0.63, 0.1)
    img = lerp(img, np.array([0.55, 0.53, 0.48]), salt * 0.45)
    damp = vertical_gradient(S, S, 0.0, 1.0) ** 2
    img = shade(img, 1 - 0.4 * damp)
    return img


@tex('concrete')
def concrete(seed=7):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.40, 0.40, 0.37])
    img = shade(img, 0.8 + 0.35 * fbm(S, S, 4, 5, rng))
    # form-work lines
    for y in (21, 43):
        hline(img, y, 0, S, [0.25, 0.25, 0.23])
        hline(img, y + 1, 0, S, [0.50, 0.50, 0.46], 0.5)
    pits = (rng.random((S, S)) > 0.985).astype(float)
    img = shade(img, 1 - 0.4 * pits)
    st = drip_streaks(S, S, rng, count=6, length=(20, 64), width=(1, 4))
    img = lerp(img, img * np.array([0.6, 0.45, 0.3]), st * 0.6)   # rust run-off
    img = bottom_dirt(img, 0.4, 0.5)
    img = shade(img, 1 - 0.5 * cracks(S, S, rng, 3, (10, 40)))
    return img


@tex('pipes')
def pipes(seed=8):
    rng = np.random.default_rng(seed)
    img = concrete(seed + 3)
    def pipe(y0, r, col):
        nonlocal img
        for y in range(y0 - r, y0 + r + 1):
            t = (y - y0) / r
            l = np.sqrt(max(0, 1 - t * t))
            c = np.array(col) * (0.35 + 0.8 * l * (1 - 0.4 * t))
            img[y, :] = c
        # flanges
        for x in (10, 42):
            img[y0 - r - 1:y0 + r + 2, x:x + 3] = np.array(col) * 0.7
            img[y0 - r - 1:y0 + r + 2, x] = np.array(col) * 1.1
    pipe(12, 4, [0.45, 0.30, 0.20])
    pipe(24, 2, [0.35, 0.36, 0.34])
    pipe(48, 6, [0.38, 0.30, 0.22])
    rust = blotches(S, S, rng, 8, 3, 0.55, 0.15)
    img = lerp(img, img * np.array([0.9, 0.55, 0.3]), rust * 0.6)
    # valve wheel
    vw = disc(S, S, 36, 26, 5) - disc(S, S, 36, 26, 3.5) + disc(S, S, 36, 26, 1.2)
    img = lerp(img, np.array([0.5, 0.12, 0.08]), np.clip(vw, 0, 1))
    vline(img, 26, 31, 41, [0.5, 0.12, 0.08]); hline(img, 36, 21, 32, [0.5, 0.12, 0.08])
    return np.clip(img, 0, 1)


@tex('padded')
def padded(seed=9):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.62, 0.60, 0.52])
    yy, xx = np.mgrid[0:S, 0:S]
    # diamond quilting
    u = ((xx + yy) % 16) / 16.0; v = ((xx - yy) % 16) / 16.0
    puff = np.sin(u * np.pi) * np.sin(v * np.pi)
    img = shade(img, 0.55 + 0.55 * puff)
    buttons = ((xx + yy) % 16 == 0) & ((xx - yy) % 16 == 0)
    img[buttons] = [0.25, 0.22, 0.18]
    stain = blotches(S, S, rng, 3, 4, 0.58, 0.2)
    img = lerp(img, img * np.array([0.7, 0.6, 0.4]), stain * 0.7)
    scratches = np.zeros((S, S))
    for i in range(4):
        x = 18 + i * 4 + rng.integers(-1, 2)
        for y in range(20 + rng.integers(0, 5), 52):
            scratches[y, (x + (y // 9)) % S] = 1
    img = lerp(img, np.array([0.3, 0.1, 0.07]), scratches * 0.7)
    return grime(img, rng, 0.2)


@tex('door_double')
def door_double(seed=10):
    """Hospital double doors (split sliding). Left/right halves."""
    rng = np.random.default_rng(seed)
    col = np.array([0.36, 0.45, 0.40])
    img = rgb(S, S, col)
    img = shade(img, 0.85 + 0.25 * fbm(S, S, 6, 3, rng))
    for x0 in (0, 32):
        bevel(img, 0, x0, S, x0 + 32, 1.25, 0.55)
        # porthole window
        cy, cx = 18, x0 + 16
        ring = disc(S, S, cy, cx, 8) - disc(S, S, cy, cx, 6.5)
        glass = disc(S, S, cy, cx, 6.5)
        img = lerp(img, np.array([0.06, 0.07, 0.09]), glass)
        glint = disc(S, S, cy - 3, cx - 3, 2.0) * glass
        img = lerp(img, np.array([0.30, 0.34, 0.40]), glint * 0.6)
        img = lerp(img, np.array([0.55, 0.55, 0.50]), np.clip(ring, 0, 1))
        # kick plate
        rect(img, 50, x0 + 3, 61, x0 + 29, [0.42, 0.40, 0.36])
        bevel(img, 50, x0 + 3, 61, x0 + 29)
        # push plate
        rect(img, 30, x0 + (24 if x0 == 0 else 3), 40, x0 + (29 if x0 == 0 else 8), [0.55, 0.53, 0.47])
    vline(img, 31, 0, S, [0.05, 0.05, 0.05]); vline(img, 32, 0, S, [0.05, 0.05, 0.05])
    st = drip_streaks(S, S, rng, count=3, length=(8, 25), width=(1, 3), from_top=False)
    img = shade(img, 1 - 0.35 * st)
    img = bottom_dirt(img, 0.6, 0.3)
    return grime(img, rng, 0.12)


@tex('door_wood')
def door_wood(seed=11):
    rng = np.random.default_rng(seed)
    wall = plaster_green(seed + 30)
    img = wall.copy()
    # door occupies x 14..50, y 6..64
    x0, x1, y0 = 14, 50, 6
    grain = fbm(S, S, 3, 4, rng, aspect=0.15)
    door = shade(rgb(S, S, [0.36, 0.23, 0.13]), 0.7 + 0.5 * grain)
    img[y0:, x0:x1] = door[y0:, x0:x1]
    # frame
    rect(img, y0 - 3, x0 - 3, S, x0, [0.22, 0.14, 0.08]); rect(img, y0 - 3, x1, S, x1 + 3, [0.22, 0.14, 0.08])
    rect(img, y0 - 3, x0 - 3, y0, x1 + 3, [0.22, 0.14, 0.08])
    bevel(img, y0 - 3, x0 - 3, S, x1 + 3, 1.3, 0.6)
    # frosted window
    rect(img, 12, x0 + 6, 30, x1 - 6, [0.30, 0.32, 0.30])
    fr = fbm(18, x1 - x0 - 12, 4, 3, rng, wrap=False)
    img[12:30, x0 + 6:x1 - 6] *= (0.7 + 0.4 * fr)[..., None]
    bevel(img, 11, x0 + 5, 31, x1 - 5, 0.6, 1.3)
    # lower panel
    bevel(img, 36, x0 + 5, 58, x1 - 5, 0.65, 1.3)
    # knob
    img = lerp(img, np.array([0.70, 0.58, 0.30]), disc(S, S, 38, x1 - 5, 1.8))
    # number plate
    rect(img, 8, 29, 10, 35, [0.6, 0.5, 0.25])
    return np.clip(img, 0, 1)


@tex('door_metal')
def door_metal(seed=12):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.36, 0.37, 0.36])
    img = shade(img, 0.8 + 0.3 * fbm(S, S, 6, 4, rng))
    for x0 in (0, 32):
        bevel(img, 0, x0, S, x0 + 32, 1.2, 0.5)
        for y in (4, 30, 58):
            for x in range(x0 + 4, x0 + 30, 6):
                img[y:y + 2, x:x + 2] = [0.55, 0.55, 0.52]
                img[y + 1, x + 1] = [0.15, 0.15, 0.15]
        rect(img, 10, x0 + 8, 22, x0 + 24, [0.12, 0.12, 0.12])  # vent
        for y in range(11, 22, 2):
            hline(img, y, x0 + 9, x0 + 23, [0.30, 0.30, 0.30])
    rust = blotches(S, S, rng, 6, 4, 0.55, 0.12)
    img = lerp(img, img * np.array([1.1, 0.6, 0.3]), rust * 0.75)
    st = drip_streaks(S, S, rng, count=6, length=(10, 40), width=(1, 3))
    img = lerp(img, img * np.array([0.8, 0.45, 0.25]), st * 0.6)
    vline(img, 31, 0, S, [0.04, 0.04, 0.04]); vline(img, 32, 0, S, [0.04, 0.04, 0.04])
    return np.clip(img, 0, 1)


@tex('jamb')
def jamb(seed=13):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.24, 0.16, 0.10])
    img = shade(img, 0.75 + 0.4 * fbm(S, S, 2, 4, rng, aspect=6))
    vline(img, 0, 0, S, [0.4, 0.28, 0.17]); vline(img, 63, 0, S, [0.10, 0.06, 0.03])
    for x in (8, 56):
        vline(img, x, 0, S, [0.14, 0.09, 0.05])
    return img


@tex('locker')
def locker(seed=14):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.30, 0.38, 0.40])
    img = shade(img, 0.85 + 0.25 * fbm(S, S, 6, 3, rng))
    for x0 in (2, 22, 42):
        rect(img, 2, x0, 60, x0 + 20, img[30, x0 + 10] * 1.0)
        bevel(img, 2, x0, 60, x0 + 20, 1.3, 0.5)
        for y in range(8, 20, 3):
            hline(img, y, x0 + 4, x0 + 16, [0.03, 0.03, 0.03])
            hline(img, y + 1, x0 + 4, x0 + 16, [0.45, 0.52, 0.55])
        for y in range(44, 54, 3):
            hline(img, y, x0 + 4, x0 + 16, [0.03, 0.03, 0.03])
        rect(img, 28, x0 + 15, 34, x0 + 17, [0.6, 0.6, 0.55])
        img[24:27, x0 + 3:x0 + 9] = [0.65, 0.62, 0.50]   # name card
    rect(img, 0, 0, 2, S, [0.15, 0.18, 0.19]); rect(img, 60, 0, 64, S, [0.12, 0.13, 0.13])
    dents = blotches(S, S, rng, 8, 3, 0.7, 0.05)
    img = shade(img, 1 - 0.25 * dents)
    rust = blotches(S, S, rng, 5, 4, 0.6, 0.1)
    img = lerp(img, img * np.array([1.0, 0.6, 0.35]), rust * 0.6)
    return np.clip(img, 0, 1)


@tex('window')
def window(seed=15):
    rng = np.random.default_rng(seed)
    img = plaster_green(seed + 40)
    x0, x1, y0, y1 = 10, 54, 6, 44
    sky = vertical_gradient(y1 - y0, x1 - x0, 0.0, 1.0)
    sky = np.stack([0.10 + 0.08 * sky, 0.13 + 0.10 * sky, 0.22 + 0.10 * sky], -1)
    clouds = fbm(y1 - y0, x1 - x0, 3, 4, rng, wrap=False)
    sky = shade(sky, 0.7 + 0.7 * clouds)
    # far trees silhouette
    for x in range(x1 - x0):
        h = int(8 + 5 * np.sin(x * 0.5) + rng.integers(0, 4))
        sky[-h:, x] = [0.03, 0.04, 0.05]
    img[y0:y1, x0:x1] = sky
    # rain streaks on glass
    for _ in range(25):
        x = rng.integers(x0, x1); y = rng.integers(y0, y1 - 4); L = rng.integers(2, 6)
        img[y:y + L, x] = img[y:y + L, x] * 1.4 + 0.03
    # mullions & bars
    for x in (x0 + 14, x0 + 29):
        vline(img, x, y0, y1, [0.15, 0.13, 0.10])
    hline(img, y0 + 18, x0, x1, [0.15, 0.13, 0.10])
    for x in range(x0 + 4, x1, 6):
        vline(img, x, y0, y1, [0.08, 0.08, 0.08])
        vline(img, x + 1, y0, y1, [0.20, 0.20, 0.20])
    # frame + sill
    rect(img, y0 - 2, x0 - 2, y0, x1 + 2, [0.30, 0.25, 0.20]); rect(img, y0, x0 - 2, y1, x0, [0.30, 0.25, 0.20])
    rect(img, y0, x1, y1, x1 + 2, [0.25, 0.20, 0.16]); rect(img, y1, x0 - 4, y1 + 3, x1 + 4, [0.45, 0.42, 0.36])
    return np.clip(img, 0, 1)


@tex('stairs_chained')
def stairs_chained(seed=16):
    rng = np.random.default_rng(seed)
    img = plaster_green(seed + 50)
    # dark stairwell opening with receding steps
    x0, x1, y0 = 6, 58, 4
    img[y0:, x0:x1] = [0.03, 0.03, 0.035]
    for k in range(9):
        y = 63 - k * 5
        inset = k * 2
        rect(img, y - 2, x0 + inset, y, x1 - inset, np.array([0.30, 0.20, 0.12]) * (1 - k * 0.09))
        hline(img, y - 2, x0 + inset, x1 - inset, np.array([0.42, 0.30, 0.18]) * (1 - k * 0.09))
    # banisters
    for x in (x0, x1 - 2):
        rect(img, y0, x, 64, x + 2, [0.28, 0.17, 0.09])
    for k in range(6):
        y = 60 - k * 8
        vline(img, x0 + 3 + k, y - 6, y, [0.25, 0.15, 0.08])
        vline(img, x1 - 4 - k, y - 6, y, [0.25, 0.15, 0.08])
    # chains crossing
    for (a, b) in (((x0, 14), (x1, 44)), ((x0, 44), (x1, 14)), ((x0, 30), (x1, 30))):
        n = 40
        for i in range(n):
            t = i / (n - 1)
            x = int(a[0] + (b[0] - a[0]) * t); y = int(a[1] + (b[1] - a[1]) * t + 4 * np.sin(np.pi * t))
            c = [0.55, 0.53, 0.48] if i % 2 else [0.30, 0.29, 0.27]
            img[y:y + 2, x:x + 2] = c
    # sign board
    rect(img, 24, 20, 36, 44, [0.80, 0.76, 0.62])
    bevel(img, 24, 20, 36, 44, 1.1, 0.6)
    for y in (27, 30, 33):
        hline(img, y, 23, 41, [0.25, 0.10, 0.08])
    return np.clip(img, 0, 1)


@tex('boiler')
def boiler(seed=17):
    rng = np.random.default_rng(seed)
    img = brick(seed + 3) * 0.7
    # big riveted boiler drum
    yy, xx = np.mgrid[0:S, 0:S]
    drum = (np.abs(xx - 32) < 26) & (yy > 6) & (yy < 60)
    t = np.clip(1 - ((xx - 32) / 26.0) ** 2, 0, 1) ** 0.5
    body = np.array([0.30, 0.20, 0.13]) * (0.35 + 0.85 * t)[..., None]
    body = shade(body, 0.8 + 0.3 * fbm(S, S, 8, 3, rng))
    img = np.where(drum[..., None], body, img)
    for y in (12, 34, 56):
        for x in range(8, 58, 4):
            img[y, x] = img[y, x] * 1.8 + 0.05
        hline(img, y + 1, 6, 58, [0.12, 0.08, 0.05])
    # gauge
    g = disc(S, S, 22, 22, 5)
    img = lerp(img, np.array([0.75, 0.72, 0.62]), g)
    img = lerp(img, np.array([0.1, 0.1, 0.1]), disc(S, S, 22, 22, 5) - disc(S, S, 22, 22, 4.2))
    for i in range(6):
        img[22 - int(3 * np.cos(i)), 22 + int(3 * np.sin(i))] = [0.2, 0.2, 0.2]
    vline(img, 22, 19, 23, [0.6, 0.1, 0.05])
    # firebox door glowing faintly
    rect(img, 40, 36, 52, 52, [0.12, 0.08, 0.06])
    bevel(img, 40, 36, 52, 52, 1.3, 0.5)
    for x in range(38, 51, 3):
        vline(img, x, 43, 50, [0.35, 0.10, 0.03])
    rust = blotches(S, S, rng, 6, 4, 0.55, 0.12)
    img = lerp(img, img * np.array([1.2, 0.6, 0.3]), rust * drum * 0.6)
    return np.clip(img, 0, 1)


@tex('morgue')
def morgue(seed=18):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.48, 0.50, 0.50])
    img = shade(img, 0.85 + 0.2 * fbm(S, S, 6, 3, rng))
    for r in range(3):
        for c in range(2):
            y0, x0 = 2 + r * 21, 2 + c * 31
            rect(img, y0, x0, y0 + 19, x0 + 29, [0.56, 0.58, 0.57])
            bevel(img, y0, x0, y0 + 19, x0 + 29, 1.25, 0.5)
            rect(img, y0 + 8, x0 + 10, y0 + 11, x0 + 19, [0.7, 0.7, 0.68])
            rect(img, y0 + 3, x0 + 3, y0 + 6, x0 + 9, [0.85, 0.82, 0.70])   # card holder
    # one drawer ajar: dark gap
    rect(img, 23, 33, 25, 62, [0.02, 0.02, 0.02])
    st = drip_streaks(S, S, rng, 4, (10, 30), from_top=False)
    img = lerp(img, img * np.array([0.6, 0.35, 0.25]), st * 0.6)
    return grime(img, rng, 0.15)


@tex('fusebox')
def fusebox(seed=19):
    rng = np.random.default_rng(seed)
    img = concrete(seed + 5)
    rect(img, 8, 12, 56, 52, [0.32, 0.36, 0.33])
    bevel(img, 8, 12, 56, 52, 1.3, 0.5)
    rect(img, 12, 16, 52, 48, [0.10, 0.10, 0.10])
    for i, x in enumerate((20, 30, 40)):
        rect(img, 18, x - 3, 40, x + 3, [0.22, 0.22, 0.20])
        vline(img, x, 18, 40, [0.4, 0.4, 0.38])
    rect(img, 44, 20, 50, 44, [0.80, 0.76, 0.60])     # label
    for x in range(22, 42, 3):
        img[46:48, x] = [0.3, 0.1, 0.05]
    # warning stripe
    for x in range(12, 52):
        img[57:60, x] = [0.75, 0.6, 0.1] if (x // 4) % 2 else [0.08, 0.08, 0.08]
    # conduit going up
    rect(img, 0, 30, 8, 34, [0.35, 0.36, 0.35])
    return np.clip(img, 0, 1)


@tex('generator')
def generator(seed=20):
    rng = np.random.default_rng(seed)
    img = concrete(seed + 6) * 0.8
    rect(img, 14, 2, 64, 62, [0.25, 0.32, 0.26])
    img[14:64, 2:62] = shade(img[14:64, 2:62], 0.8 + 0.3 * fbm(50, 60, 6, 3, rng, wrap=False))
    bevel(img, 14, 2, 64, 62, 1.3, 0.5)
    for y in range(20, 40, 3):
        hline(img, y, 6, 40, [0.10, 0.12, 0.10])
    # lever
    rect(img, 22, 48, 44, 56, [0.15, 0.15, 0.15])
    vline(img, 52, 8, 30, [0.6, 0.6, 0.55]); vline(img, 53, 8, 30, [0.4, 0.4, 0.38])
    img = lerp(img, np.array([0.7, 0.12, 0.08]), disc(S, S, 8, 52.5, 3.2))
    # plate
    rect(img, 44, 8, 52, 30, [0.72, 0.62, 0.30])
    for x in range(10, 28, 2):
        img[47:49, x] = [0.25, 0.20, 0.10]
    rust = blotches(S, S, rng, 6, 4, 0.55, 0.12)
    img = lerp(img, img * np.array([1.1, 0.6, 0.3]), rust * 0.5)
    return np.clip(img, 0, 1)


@tex('lift')
def lift(seed=21):
    rng = np.random.default_rng(seed)
    img = concrete(seed + 7)
    rect(img, 2, 6, 64, 58, [0.06, 0.06, 0.06])
    # scissor gate
    for k in range(8):
        x = 8 + k * 6
        for y in range(4, 64):
            off = ((y // 6) % 2) * 3
            xx = x + (off if (y % 6) < 3 else 3 - off)
            if 6 <= xx < 58:
                img[y, xx] = [0.5, 0.48, 0.42]
    for y in (4, 34, 62):
        hline(img, y, 6, 58, [0.55, 0.52, 0.45])
    rect(img, 0, 4, 64, 6, [0.30, 0.30, 0.28]); rect(img, 0, 58, 64, 60, [0.30, 0.30, 0.28])
    rust = blotches(S, S, rng, 6, 4, 0.58, 0.12)
    img = lerp(img, img * np.array([1.1, 0.6, 0.3]), rust * 0.5)
    return np.clip(img, 0, 1)


@tex('wallpaper')
def wallpaper(seed=22):
    """Faded nursery wallpaper: stripes and little ducks, peeling."""
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.66, 0.60, 0.48])
    yy, xx = np.mgrid[0:S, 0:S]
    stripes = ((xx // 8) % 2).astype(float)
    img = lerp(img, np.array([0.55, 0.62, 0.58]), stripes * 0.6)
    for (cy, cx) in ((12, 4), (12, 36), (40, 20), (40, 52)):
        duck = ellipse(S, S, cy, cx, 3, 4) + disc(S, S, cy - 3, cx + 3, 2.2)
        img = lerp(img, np.array([0.80, 0.68, 0.30]), np.clip(duck, 0, 1) * 0.8)
        img[int(cy) - 3, int(cx) + 4] = [0.2, 0.15, 0.1]
    img = shade(img, 0.85 + 0.25 * fbm(S, S, 6, 4, rng))
    peel = blotches(S, S, rng, 4, 4, 0.66, 0.05)
    img = lerp(img, np.array([0.45, 0.42, 0.35]), peel * 0.9)
    st = drip_streaks(S, S, rng, 6, (20, 60), width=(2, 4))
    img = lerp(img, img * np.array([0.6, 0.5, 0.35]), st * 0.7)
    rect(img, 56, 0, 64, S, [0.30, 0.22, 0.15])
    hline(img, 56, 0, S, [0.42, 0.32, 0.22])
    # child's scribbles
    sc = np.zeros((S, S))
    x, y = 10.0, 48.0
    for i in range(60):
        x += rng.uniform(0.2, 1.2); y += rng.normal(0, 1.4)
        sc[int(np.clip(y, 30, 55)), int(x) % S] = 1
    img = lerp(img, np.array([0.45, 0.08, 0.08]), sc * 0.8)
    return np.clip(img, 0, 1)


@tex('stone')
def stone(seed=23):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.40, 0.39, 0.36])
    mortar = np.zeros((S, S))
    rows = [0, 14, 30, 46, 64]
    for r in range(4):
        y0, y1 = rows[r], rows[r + 1]
        x = (r * 13) % 24
        widths = []
        while x < S + 24:
            w = rng.integers(16, 26)
            widths.append((x, w)); x += w
        for (x0, w) in widths:
            v = rng.uniform(0.75, 1.2)
            for xx in range(x0, x0 + w):
                img[y0:y1, xx % S] *= v
                mortar[y0:y1, x0 % S] = 1
        mortar[y0, :] = 1
    img = shade(img, 0.75 + 0.4 * fbm(S, S, 8, 4, rng))
    img = lerp(img, np.array([0.16, 0.16, 0.15]), mortar * 0.9)
    moss = blotches(S, S, rng, 4, 4, 0.6, 0.15)
    img = lerp(img, img * np.array([0.55, 0.75, 0.45]), moss * 0.6)
    wet = vertical_gradient(S, S, 0.0, 1.0) ** 3
    img = shade(img, 1 - 0.45 * wet)
    return np.clip(img, 0, 1)


@tex('crypt')
def crypt(seed=24):
    rng = np.random.default_rng(seed)
    img = stone(seed + 1)
    # burial niche with a skull and bones
    rect(img, 18, 10, 44, 54, [0.04, 0.04, 0.04])
    bevel(img, 18, 10, 44, 54, 0.6, 1.3)
    sk = ellipse(S, S, 34, 24, 5, 6)
    img = lerp(img, np.array([0.62, 0.58, 0.48]), sk)
    for ex in (21, 27):
        img = lerp(img, np.array([0.05, 0.05, 0.05]), disc(S, S, 33, ex, 1.6))
    for (y, x0, x1) in ((40, 30, 50), (38, 32, 48)):
        hline(img, y, x0, x1, [0.55, 0.52, 0.44])
    # carved letters above
    for x in range(14, 50, 5):
        rect(img, 10, x, 14, x + 3, [0.22, 0.21, 0.19])
    return np.clip(img, 0, 1)


@tex('stained')
def stained(seed=25):
    rng = np.random.default_rng(seed)
    img = stone(seed + 2)
    yy, xx = np.mgrid[0:S, 0:S]
    # pointed arch window
    arch = (np.abs(xx - 32) < 18) & (yy > 6) & (yy < 60)
    tip = (yy < 22) & (np.hypot(xx - 32 + np.sign(xx - 32) * 6, yy - 22) > 18)
    win = arch & ~tip
    cols = [np.array([0.55, 0.08, 0.08]), np.array([0.10, 0.20, 0.55]), np.array([0.70, 0.55, 0.12]),
            np.array([0.15, 0.40, 0.18]), np.array([0.45, 0.15, 0.45])]
    cell = ((xx // 6) * 7 + (yy // 7) * 3) % len(cols)
    glass = np.zeros((S, S, 3))
    for i, c in enumerate(cols):
        glass[cell == i] = c
    glass = shade(glass, 0.7 + 0.5 * fbm(S, S, 8, 2, rng))
    lead = ((xx % 6 == 0) | (yy % 7 == 0)).astype(float)
    glass = lerp(glass, np.array([0.05, 0.05, 0.05]), lead)
    # a figure with a lantern in the centre panel
    fig = ellipse(S, S, 30, 32, 14, 4.5) + disc(S, S, 15, 32, 3)
    glass = lerp(glass, np.array([0.80, 0.78, 0.70]), np.clip(fig, 0, 1) * 0.8)
    glass = lerp(glass, np.array([0.95, 0.75, 0.25]), disc(S, S, 36, 39, 2.5))
    img = np.where(win[..., None], glass, img)
    border = win & ~np.roll(win, 1, 0) | win & ~np.roll(win, -1, 1) | win & ~np.roll(win, 1, 1)
    img[border] = [0.18, 0.17, 0.15]
    return np.clip(img, 0, 1)


@tex('confessional')
def confessional(seed=26):
    rng = np.random.default_rng(seed)
    img = wood_panel(seed + 4)
    rect(img, 6, 14, 60, 50, [0.20, 0.12, 0.06])
    bevel(img, 6, 14, 60, 50, 1.3, 0.5)
    # lattice window
    rect(img, 14, 22, 34, 42, [0.03, 0.02, 0.02])
    for k in range(-20, 21, 4):
        for i in range(20):
            x, y = 22 + i, 14 + ((i + k) % 20)
            if 22 <= x < 42 and 14 <= y < 34:
                img[y, x] = [0.32, 0.20, 0.10]
    # small cross
    rect(img, 8, 31, 12, 33, [0.70, 0.58, 0.30]); rect(img, 9, 29, 10, 35, [0.70, 0.58, 0.30])
    img = lerp(img, np.array([0.65, 0.52, 0.25]), disc(S, S, 44, 45, 1.6))
    return np.clip(img, 0, 1)


@tex('bookshelf')
def bookshelf(seed=27):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.22, 0.13, 0.07])
    for y0 in (2, 22, 42):
        x = 2
        while x < 62:
            w = int(rng.integers(2, 5)); h = int(rng.integers(12, 18))
            col = np.array(rng.choice([[0.45, 0.10, 0.08], [0.15, 0.25, 0.15], [0.35, 0.30, 0.20],
                                       [0.12, 0.15, 0.30], [0.40, 0.35, 0.28]]))
            rect(img, y0 + 18 - h, x, y0 + 18, x + w, col * rng.uniform(0.7, 1.1))
            vline(img, x, y0 + 18 - h, y0 + 18, col * 1.3)
            x += w + (1 if rng.random() < 0.2 else 0)
        rect(img, y0 + 18, 0, y0 + 20, S, [0.30, 0.18, 0.09])
    img = shade(img, 0.85 + 0.25 * fbm(S, S, 6, 3, rng))
    return np.clip(img, 0, 1)


@tex('door_chapel')
def door_chapel(seed=28):
    return _arched_single(stone(seed + 3), seed)


@tex('door_chapel_plaster')
def door_chapel_plaster(seed=28):
    return _arched_single(plaster_green(seed + 5), seed)


def _arched_single(bg, seed):
    rng = np.random.default_rng(seed)
    img = bg.copy()
    yy, xx = np.mgrid[0:S, 0:S]
    arch = (np.abs(xx - 32) < 22) & (yy > 4)
    tip = (yy < 26) & (np.hypot(xx - 32 + np.sign(xx - 32) * 8, yy - 26) > 22)
    door = arch & ~tip
    wood = shade(rgb(S, S, [0.30, 0.18, 0.09]), 0.7 + 0.5 * fbm(S, S, 3, 4, rng, aspect=0.15))
    for x in range(10, 56, 7):
        wood[:, x] *= 0.55
    img = np.where(door[..., None], wood, img)
    for y in (16, 40):
        hline(img, y, 11, 53, [0.12, 0.12, 0.12]); hline(img, y + 1, 11, 53, [0.22, 0.22, 0.22])
    img = lerp(img, np.array([0.55, 0.50, 0.40]), disc(S, S, 34, 44, 2.6) - disc(S, S, 34, 44, 1.5))
    return np.clip(img, 0, 1)


# ---------------------------------------------------------- hinged doors --
# Geometry shared with the renderer (render.iwram.c): a single doorway has a
# static wall panel of FRAME_A/64 tile on each side of its front face and a
# leaf LEAF_W/64 tile wide hinged at a panel edge. A double doorway has two
# leaves of 32/64. Leaf textures occupy columns [0, width) with the hinge at
# column 0 and the free (handle) edge at width-1, drawn at true proportions.
FRAME_A = 12
LEAF_W = S - 2 * FRAME_A          # 40
LEAF_W2 = 32


def _pad_leaf(leaf):
    """Place a narrow leaf image into a 64-wide texture (unused columns repeat)."""
    w = leaf.shape[1]
    img = np.zeros((S, S, 3))
    img[:, :w] = leaf
    img[:, w:] = leaf[:, :S - w] if S - w <= w else leaf[:, :1]
    return np.clip(img, 0, 1)


def _hinges(img, x, rows=(7, 53)):
    for y in rows:
        rect(img, y, x, y + 4, x + 2, [0.16, 0.15, 0.13])
        hline(img, y, x, x + 2, [0.40, 0.38, 0.33])


@tex('leaf_wood')
def leaf_wood(seed=50):
    """Single wooden ward-room door: glazed upper half, raised lower panel."""
    rng = np.random.default_rng(seed)
    W = LEAF_W
    grain = fbm(S, W, 3, 4, rng, wrap=False, aspect=0.15)
    img = shade(rgb(S, W, [0.37, 0.24, 0.13]), 0.72 + 0.45 * grain)
    # stiles and rails read as one frame; panels inset
    bevel(img, 0, 0, S, W, 1.25, 0.55)
    # frosted glass
    rect(img, 6, 6, 28, W - 6, [0.33, 0.35, 0.32])
    fr = fbm(22, W - 12, 4, 3, rng, wrap=False)
    img[6:28, 6:W - 6] *= (0.72 + 0.4 * fr)[..., None]
    for x in range(8, W - 6, 6):            # wired glass
        vline(img, x, 6, 28, [0.22, 0.23, 0.21], 0.5)
    for y in range(9, 28, 6):
        hline(img, y, 6, W - 6, [0.22, 0.23, 0.21], 0.5)
    bevel(img, 5, 5, 29, W - 5, 0.55, 1.3)
    # lower raised panel
    bevel(img, 35, 6, 57, W - 6, 0.6, 1.3)
    bevel(img, 37, 8, 55, W - 8, 1.2, 0.7)
    # kick rail
    hline(img, 59, 1, W - 1, [0.20, 0.13, 0.07])
    # brass knob and escutcheon near the free edge
    rect(img, 33, W - 6, 42, W - 3, [0.42, 0.34, 0.16])
    img = lerp(img, np.array([0.80, 0.66, 0.32]), disc(S, W, 36.5, W - 4.5, 1.9))
    img[39, W - 5] = [0.08, 0.06, 0.03]
    # room number plate
    rect(img, 1, 16, 4, 24, [0.62, 0.52, 0.26])
    hline(img, 2, 18, 22, [0.25, 0.20, 0.10])
    _hinges(img, 0)
    img = bottom_dirt(img, 0.65, 0.35)
    st = drip_streaks(S, W, rng, count=3, length=(10, 30), width=(1, 2))
    img = shade(img, 1 - 0.3 * st)
    return _pad_leaf(img)


@tex('leaf_metal')
def leaf_metal(seed=51):
    """Single riveted steel door with a wired vision panel and push bar."""
    rng = np.random.default_rng(seed)
    W = LEAF_W
    img = shade(rgb(S, W, [0.37, 0.38, 0.37]), 0.8 + 0.3 * fbm(S, W, 6, 4, rng, wrap=False))
    bevel(img, 0, 0, S, W, 1.3, 0.5)
    bevel(img, 3, 3, S - 3, W - 3, 0.75, 1.2)
    # vision panel
    rect(img, 8, 11, 24, 29, [0.07, 0.08, 0.09])
    for x in range(13, 29, 4):
        vline(img, x, 8, 24, [0.24, 0.24, 0.24], 0.7)
    for y in range(10, 24, 4):
        hline(img, y, 11, 29, [0.24, 0.24, 0.24], 0.7)
    img[10:12, 13:15] = [0.30, 0.33, 0.38]
    bevel(img, 7, 10, 25, 30, 0.6, 1.3)
    # rivets
    for y in (5, 32, 58):
        for x in range(6, W - 4, 7):
            img[y:y + 2, x:x + 2] = [0.58, 0.58, 0.55]
            img[y + 1, x + 1] = [0.15, 0.15, 0.15]
    # vent
    rect(img, 44, 10, 54, 30, [0.11, 0.11, 0.11])
    for y in range(45, 54, 2):
        hline(img, y, 11, 29, [0.33, 0.33, 0.32])
    # handle near the free edge
    rect(img, 30, W - 7, 40, W - 4, [0.20, 0.20, 0.19])
    vline(img, W - 6, 31, 39, [0.62, 0.60, 0.55])
    _hinges(img, 0)
    rust = blotches(S, W, rng, 6, 4, 0.55, 0.12)
    img = lerp(img, img * np.array([1.1, 0.6, 0.3]), rust * 0.75)
    st = drip_streaks(S, W, rng, count=5, length=(10, 40), width=(1, 3))
    img = lerp(img, img * np.array([0.8, 0.45, 0.25]), st * 0.6)
    return _pad_leaf(img)


@tex('leaf_ward')
def leaf_ward(seed=52):
    """One leaf of the green ward double doors: porthole, push and kick plates."""
    rng = np.random.default_rng(seed)
    W = LEAF_W2
    img = shade(rgb(S, W, [0.36, 0.45, 0.40]), 0.85 + 0.25 * fbm(S, W, 6, 3, rng, wrap=False))
    bevel(img, 0, 0, S, W, 1.25, 0.55)
    cy, cx = 18, 15.5
    ring = disc(S, W, cy, cx, 8) - disc(S, W, cy, cx, 6.5)
    glass = disc(S, W, cy, cx, 6.5)
    img = lerp(img, np.array([0.06, 0.07, 0.09]), glass)
    img = lerp(img, np.array([0.30, 0.34, 0.40]), disc(S, W, cy - 3, cx - 3, 2.0) * glass * 0.6)
    img = lerp(img, np.array([0.55, 0.55, 0.50]), np.clip(ring, 0, 1))
    rect(img, 50, 3, 61, W - 3, [0.42, 0.40, 0.36])          # kick plate
    bevel(img, 50, 3, 61, W - 3)
    rect(img, 30, W - 8, 41, W - 3, [0.56, 0.54, 0.48])      # push plate
    bevel(img, 30, W - 8, 41, W - 3)
    _hinges(img, 0)
    st = drip_streaks(S, W, rng, count=2, length=(8, 25), width=(1, 3), from_top=False)
    img = shade(img, 1 - 0.35 * st)
    img = bottom_dirt(img, 0.6, 0.3)
    return _pad_leaf(img)


def make_frame(wall, casing):
    """Static door surround: the wall's own surface with a casing at the
    opening edges. Only columns [0, A) and [64-A, 64) are ever shown."""
    img = TEXTURES[wall]().copy()
    A = FRAME_A
    rng = np.random.default_rng(len(wall) * 7 + len(casing))
    if casing == 'metal':
        col = np.array([0.33, 0.34, 0.33])
        for x0 in (A - 3, S - A):
            rect(img, 0, x0, S, x0 + 3, col)
            for y in range(4, S, 9):
                img[y, x0 + 1] = [0.55, 0.55, 0.52]
        rust = blotches(S, S, rng, 6, 4, 0.6, 0.12)
        mask = np.zeros((S, S)); mask[:, A - 3:A] = 1; mask[:, S - A:S - A + 3] = 1
        img = lerp(img, img * np.array([1.1, 0.6, 0.3]), rust * mask * 0.6)
    else:
        col = np.array([0.30, 0.20, 0.11])
        grain = fbm(S, S, 3, 3, rng, aspect=0.15)
        wood = shade(rgb(S, S, col), 0.75 + 0.4 * grain)
        img[:, A - 3:A] = wood[:, A - 3:A]
        img[:, S - A:S - A + 3] = wood[:, S - A:S - A + 3]
    # casing bevels: outer edge catches light, the reveal edge is in shadow
    vline(img, A - 3, 0, S, img[:, A - 3].mean(0) * 1.35)
    vline(img, A - 1, 0, S, img[:, A - 1].mean(0) * 0.55)
    vline(img, S - A, 0, S, img[:, S - A].mean(0) * 0.55)
    vline(img, S - A + 2, 0, S, img[:, S - A + 2].mean(0) * 1.35)
    img[:, A:S - A] = 0.05
    return np.clip(img, 0, 1)


def make_closed_door(wall, leaf):
    """A door that never opens (exits, signs): frame and leaf as one surface."""
    casing = 'metal' if leaf == 'leaf_metal' else 'wood'
    img = make_frame(wall, casing)
    lf = TEXTURES[leaf]()
    img[:, FRAME_A:S - FRAME_A] = lf[:, :LEAF_W]
    return np.clip(img, 0, 1)


def ensure(name):
    """Register a generated texture on demand: 'frame:<wall>:<casing>' or
    'closed:<wall>:<leaf>'."""
    if name in TEXTURES:
        return
    parts = name.split(':')
    if parts[0] == 'frame' and len(parts) == 3:
        TEXTURES[name] = lambda w=parts[1], c=parts[2]: make_frame(w, c)
    elif parts[0] == 'closed' and len(parts) == 3:
        TEXTURES[name] = lambda w=parts[1], l=parts[2]: make_closed_door(w, l)
    else:
        raise KeyError(f"unknown texture {name}")


def _entrance_half():
    """Left half of the main entrance: tall glazed oak leaf, frame at left."""
    rng = np.random.default_rng(53)
    img = plaster_green(31).copy()
    grain = fbm(S, S, 3, 4, rng, aspect=0.15)
    wood = shade(rgb(S, S, [0.30, 0.19, 0.10]), 0.72 + 0.45 * grain)
    img[:, 6:] = wood[:, 6:]
    rect(img, 0, 3, S, 6, [0.24, 0.15, 0.08])
    bevel(img, 0, 3, S, 6, 1.3, 0.6)
    bevel(img, 0, 6, S, S, 1.2, 0.6)
    # fanlight across the top
    rect(img, 3, 9, 11, S - 2, [0.05, 0.06, 0.09])
    for x in range(14, S - 2, 8):
        vline(img, x, 3, 11, [0.25, 0.17, 0.09])
    # glazed upper panel showing the night
    rect(img, 15, 12, 33, S - 6, [0.05, 0.06, 0.10])
    img[16:20, 14:18] = [0.16, 0.18, 0.24]
    vline(img, (12 + S - 6) // 2, 15, 33, [0.25, 0.17, 0.09])
    bevel(img, 14, 11, 34, S - 5, 0.55, 1.3)
    bevel(img, 38, 12, 58, S - 6, 1.2, 0.65)
    # brass pull handle at the meeting edge
    rect(img, 30, S - 4, 44, S - 2, [0.72, 0.60, 0.30])
    vline(img, S - 4, 30, 44, [0.40, 0.32, 0.15])
    img = bottom_dirt(img, 0.62, 0.35)
    return np.clip(grime(img, rng, 0.12), 0, 1)


@tex('entrance_l')
def entrance_l():
    return _entrance_half()


@tex('entrance_r')
def entrance_r():
    return _entrance_half()[:, ::-1].copy()


def _arched_double():
    """128-wide pointed-arch double door in stone (split into halves)."""
    rng = np.random.default_rng(54)
    W = 2 * S
    img = np.concatenate([stone(57), stone(58)], axis=1)
    yy, xx = np.mgrid[0:S, 0:W]
    cx = W / 2
    arch = (np.abs(xx - cx) < 50) & (yy > 3)
    tip = (yy < 30) & (np.hypot(np.abs(xx - cx) + 22, yy - 30) > 72)
    door = arch & ~tip
    wood = shade(rgb(S, W, [0.29, 0.17, 0.09]), 0.7 + 0.5 * fbm(S, W, 3, 4, rng, aspect=0.15))
    for x in range(int(cx - 48), int(cx + 50), 8):
        wood[:, x] *= 0.55
    img = np.where(door[..., None], wood, img)
    for y in (18, 44):
        band = door[y]
        img[y][band] = [0.13, 0.13, 0.13]
        img[y + 1][band] = [0.22, 0.22, 0.22]
    img[:, int(cx) - 1:int(cx) + 1][door[:, int(cx) - 1:int(cx) + 1]] = [0.08, 0.05, 0.03]
    for hx in (cx - 6, cx + 6):
        ring = disc(S, W, 34, hx, 3.0) - disc(S, W, 34, hx, 1.8)
        img = lerp(img, np.array([0.52, 0.48, 0.40]), np.clip(ring, 0, 1))
    return np.clip(img, 0, 1)


@tex('arch_l')
def arch_l():
    return _arched_double()[:, :S].copy()


@tex('arch_r')
def arch_r():
    return _arched_double()[:, S:].copy()


@tex('machine')
def machine(seed=55):
    """Generator casing: painted steel panels, bolts, a feed pipe, grilles."""
    rng = np.random.default_rng(seed)
    img = shade(rgb(S, S, [0.22, 0.28, 0.23]), 0.78 + 0.32 * fbm(S, S, 6, 3, rng))
    for y in (1, 22, 43):
        bevel(img, y, 1, y + 20, S - 1, 1.25, 0.55)
        for x in (4, S - 6):
            img[y + 2:y + 4, x:x + 2] = [0.48, 0.50, 0.45]
            img[y + 16:y + 18, x:x + 2] = [0.48, 0.50, 0.45]
    # feed pipe
    rect(img, 9, 0, 14, S, [0.45, 0.32, 0.20])
    hline(img, 9, 0, S, [0.62, 0.46, 0.30]); hline(img, 13, 0, S, [0.22, 0.15, 0.09])
    for x in (16, 48):
        rect(img, 8, x, 15, x + 3, [0.30, 0.30, 0.28])
    # cooling grille
    rect(img, 28, 10, 42, 54, [0.08, 0.09, 0.08])
    for x in range(11, 54, 3):
        vline(img, x, 29, 41, [0.30, 0.34, 0.30])
    # hazard stripe at the base
    for x in range(0, S, 8):
        rect(img, 58, x, 62, x + 4, [0.62, 0.52, 0.12])
        rect(img, 58, x + 4, 62, x + 8, [0.08, 0.08, 0.06])
    rust = blotches(S, S, rng, 6, 4, 0.55, 0.12)
    img = lerp(img, img * np.array([1.1, 0.6, 0.3]), rust * 0.6)
    st = drip_streaks(S, S, rng, count=5, length=(8, 30), width=(1, 3), from_top=False)
    img = shade(img, 1 - 0.35 * st)
    return np.clip(bottom_dirt(img, 0.6, 0.3), 0, 1)


# --------------------------------------------------------------- floors --

@tex('floor_checker')
def floor_checker(seed=20):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:S, 0:S]
    chk = ((xx // 16 + yy // 16) % 2).astype(float)
    a = np.array([0.55, 0.53, 0.45]); b = np.array([0.20, 0.26, 0.22])
    img = lerp(np.broadcast_to(a, (S, S, 3)).copy(), b, chk)
    img = shade(img, 0.8 + 0.35 * fbm(S, S, 4, 5, rng))
    wear = blotches(S, S, rng, 3, 4, 0.55, 0.25)
    img = lerp(img, np.array([0.30, 0.28, 0.24]), wear * 0.35)
    seams = ((xx % 16 == 0) | (yy % 16 == 0)).astype(float)
    img = shade(img, 1 - 0.3 * seams)
    scratches = np.zeros((S, S))
    for _ in range(10):
        y, x = rng.integers(0, S), rng.integers(0, S)
        L = rng.integers(4, 14); d = rng.choice([-1, 1])
        for i in range(L):
            scratches[(y + i * d // 3) % S, (x + i) % S] = 1
    img = shade(img, 1 - 0.2 * scratches)
    img = shade(img, 1 - 0.4 * cracks(S, S, rng, 2, (8, 20)))
    return img


@tex('floor_wood')
def floor_wood(seed=21):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.34, 0.22, 0.13])
    grain = fbm(S, S, 4, 4, rng, aspect=0.12)
    img = shade(img, 0.65 + 0.6 * grain)
    for x in range(0, S, 8):
        vline(img, x, 0, S, [0.10, 0.06, 0.03])
        v = rng.uniform(0.8, 1.15)
        img[:, x + 1:x + 8] *= v
        yj = rng.integers(0, S)
        hline(img, yj, x, x + 8, [0.12, 0.07, 0.04])
    img = np.clip(img, 0, 1)
    stain = blotches(S, S, rng, 3, 4, 0.62, 0.15)
    img = lerp(img, img * 0.55, stain * 0.7)
    return img


@tex('floor_concrete')
def floor_concrete(seed=22):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.33, 0.33, 0.31])
    img = shade(img, 0.75 + 0.4 * fbm(S, S, 4, 5, rng))
    wet = blotches(S, S, rng, 3, 4, 0.55, 0.12)
    img = lerp(img, img * np.array([0.45, 0.5, 0.55]), wet * 0.8)
    yy, xx = np.mgrid[0:S, 0:S]
    joint = ((xx % 32 == 0) | (yy % 32 == 0)).astype(float)
    img = shade(img, 1 - 0.45 * joint)
    img = shade(img, 1 - 0.5 * cracks(S, S, rng, 4, (10, 30)))
    drain = disc(S, S, 48, 48, 5)
    img = lerp(img, np.array([0.12, 0.12, 0.12]), drain * 0.0)
    return img


@tex('floor_stone')
def floor_stone(seed=23):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.36, 0.34, 0.32])
    for row in range(4):
        off = 8 * (row % 2)
        for bx in range(0, S, 16 if row % 2 else 32):
            v = rng.uniform(0.75, 1.15)
            ys = slice(row * 16, row * 16 + 16)
            xs = [(bx + off + i) % S for i in range(16 if row % 2 else 32)]
            img[ys, xs] *= v
            for i in range(16):
                img[row * 16 + i, (bx + off) % S] = [0.12, 0.12, 0.11]
        img[row * 16, :] = [0.12, 0.12, 0.11]
    img = shade(img, 0.75 + 0.4 * fbm(S, S, 8, 4, rng))
    moss = blotches(S, S, rng, 4, 4, 0.6, 0.15)
    img = lerp(img, img * np.array([0.6, 0.8, 0.5]), moss * 0.5)
    return np.clip(img, 0, 1)


@tex('ceil_tiles')
def ceil_tiles(seed=30):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.58, 0.57, 0.52])
    img = shade(img, 0.88 + 0.18 * fbm(S, S, 8, 3, rng))
    yy, xx = np.mgrid[0:S, 0:S]
    holes = ((xx % 4 == 1) & (yy % 4 == 1) & (rng.random((S, S)) > 0.3)).astype(float)
    img = shade(img, 1 - 0.25 * holes)
    grid = ((xx % 32 <= 1) | (yy % 32 <= 1)).astype(float)
    img = lerp(img, np.array([0.30, 0.29, 0.26]), grid)
    stain = blotches(S, S, rng, 3, 4, 0.55, 0.2)
    ring = np.clip(stain * (1 - stain) * 4, 0, 1)
    img = lerp(img, img * np.array([0.75, 0.62, 0.42]), stain * 0.6)
    img = shade(img, 1 - 0.3 * ring)
    # one missing tile showing darkness
    img[34:62, 2:30] = shade(img[34:62, 2:30], 0.15 + 0.1 * fbm(28, 28, 4, 2, rng, wrap=False))
    return img


@tex('ceil_plaster')
def ceil_plaster(seed=31):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.55, 0.53, 0.47])
    img = shade(img, 0.8 + 0.3 * fbm(S, S, 4, 5, rng))
    stain = blotches(S, S, rng, 2, 4, 0.55, 0.25)
    img = lerp(img, img * np.array([0.7, 0.6, 0.4]), stain * 0.6)
    img = shade(img, 1 - 0.5 * cracks(S, S, rng, 4, (15, 40)))
    mold = blotches(S, S, rng, 8, 3, 0.66, 0.1)
    img = lerp(img, np.array([0.15, 0.17, 0.12]), mold * 0.6)
    return img


@tex('ceil_concrete')
def ceil_concrete(seed=32):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.30, 0.30, 0.29])
    img = shade(img, 0.7 + 0.4 * fbm(S, S, 4, 5, rng))
    # beams
    for x in (0, 1, 2, 3, 32, 33, 34, 35):
        img[:, x] *= 0.55
    img = shade(img, 1 - 0.4 * cracks(S, S, rng, 3, (10, 30)))
    return img


@tex('ceil_wood')
def ceil_wood(seed=33):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.22, 0.15, 0.10])
    img = shade(img, 0.7 + 0.5 * fbm(S, S, 3, 4, rng, aspect=0.15))
    for x in range(0, S, 16):
        img[:, x:x + 3] = shade(img[:, x:x + 3], 0.5)
    return img


@tex('floor_water')
def floor_water(seed=40):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:S, 0:S]
    base = rgb(S, S, [0.07, 0.10, 0.11])
    rip = np.sin((xx + 3 * np.sin(yy * 2 * np.pi / 32)) * 2 * np.pi / 16) * np.sin((yy + 2 * np.sin(xx * 2 * np.pi / 64)) * 2 * np.pi / 21)
    img = shade(base, 0.8 + 0.35 * rip + 0.3 * fbm(S, S, 4, 4, rng))
    glint = (fbm(S, S, 8, 3, rng) > 0.7).astype(float) * (rip > 0.4)
    img = lerp(img, np.array([0.30, 0.36, 0.38]), glint * 0.6)
    scum = blotches(S, S, rng, 3, 4, 0.62, 0.12)
    img = lerp(img, np.array([0.14, 0.17, 0.10]), scum * 0.7)
    return np.clip(img, 0, 1)


@tex('floor_hex')
def floor_hex(seed=41):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.62, 0.62, 0.58])
    yy, xx = np.mgrid[0:S, 0:S]
    # small hexagonal-ish tiles: offset bricks of 8x7
    row = yy // 8
    col = (xx + (row % 2) * 4) // 8
    v = (np.sin(row * 12.9898 + col * 78.233) * 43758.5453) % 1
    img = shade(img, 0.85 + 0.2 * v)
    grout = ((yy % 8) == 0) | (((xx + (row % 2) * 4) % 8) == 0)
    img = lerp(img, np.array([0.25, 0.24, 0.22]), grout.astype(float) * 0.9)
    img = shade(img, 0.8 + 0.3 * fbm(S, S, 4, 4, rng))
    stain = blotches(S, S, rng, 3, 4, 0.58, 0.2)
    img = lerp(img, img * np.array([0.7, 0.62, 0.45]), stain * 0.7)
    blood = blotches(S, S, rng, 5, 4, 0.7, 0.06)
    img = lerp(img, np.array([0.30, 0.05, 0.03]), blood * 0.8)
    return np.clip(img, 0, 1)


@tex('ceil_stone')
def ceil_stone(seed=42):
    rng = np.random.default_rng(seed)
    img = floor_stone(seed + 1) * 0.75
    drip = blotches(S, S, rng, 6, 3, 0.62, 0.1)
    img = lerp(img, img * np.array([0.5, 0.65, 0.45]), drip * 0.6)
    return np.clip(img, 0, 1)


# ------------------------------------------------------- manor floors --
@tex('floor_parquet')
def floor_parquet(seed=60):
    """Herringbone-ish oak parquet, dark with age."""
    rng = np.random.default_rng(seed)
    img = np.zeros((S, S, 3))
    for by in range(0, S, 16):
        for bx in range(0, S, 16):
            horiz = ((bx // 16) + (by // 16)) % 2 == 0
            c = np.array([0.30, 0.18, 0.09]) * (0.75 + 0.4 * rng.random())
            g = fbm(16, 16, 2, 3, rng, wrap=False, aspect=4 if horiz else 0.25)
            blk = shade(rgb(16, 16, c), 0.75 + 0.45 * g)
            for k in range(0, 16, 4):
                if horiz:
                    blk[k, :] *= 0.55
                else:
                    blk[:, k] *= 0.55
            img[by:by + 16, bx:bx + 16] = blk
    wear = blotches(S, S, rng, base=3, threshold=0.6, softness=0.15)
    img = lerp(img, img * 1.25, wear * 0.5)
    return np.clip(img, 0, 1)


@tex('floor_carpet')
def floor_carpet(seed=61):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.26, 0.07, 0.07])
    yy, xx = np.mgrid[0:S, 0:S]
    m = ((np.abs((xx % 32) - 16) + np.abs((yy % 32) - 16)) < 6)
    img = np.where(m[..., None], np.array([0.42, 0.30, 0.12]), img)
    m2 = ((xx % 32 == 0) | (yy % 32 == 0))
    img = np.where(m2[..., None], np.array([0.14, 0.06, 0.08]), img)
    img = shade(img, 0.75 + 0.35 * fbm(S, S, 8, 3, rng))
    wear = blotches(S, S, rng, base=3, threshold=0.58, softness=0.15)
    img = lerp(img, img * np.array([1.2, 1.1, 0.9]), wear * 0.5)
    return np.clip(img, 0, 1)


@tex('floor_flagstone')
def floor_flagstone(seed=62):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.28, 0.27, 0.25])
    img = shade(img, 0.75 + 0.4 * fbm(S, S, 6, 4, rng))
    for (y0, x0, y1, x1) in ((0, 0, 26, 30), (0, 30, 20, 64), (26, 0, 64, 22), (20, 30, 44, 64),
                             (26, 22, 64, 40), (44, 40, 64, 64)):
        img[y0:y1, x0:x1] *= 0.82 + 0.3 * rng.random()
        bevel(img, y0, x0, y1, x1, 1.15, 0.6)
    wet = blotches(S, S, rng, base=3, threshold=0.6, softness=0.12)
    img = lerp(img, img * np.array([0.6, 0.65, 0.75]), wet * 0.6)
    return np.clip(img, 0, 1)


@tex('floor_void')
def floor_void(seed=48):
    """The open stairwell where the upper flight fell in: no floor, only the
    dark, a faint grey of dust and splinters far below."""
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.018, 0.015, 0.013])
    img = shade(img, 0.6 + 0.8 * fbm(S, S, 4, 3, rng))
    return np.clip(img, 0, 1)


@tex('floor_boards')
def floor_boards(seed=63):
    rng = np.random.default_rng(seed)
    img = np.zeros((S, S, 3))
    for y in range(0, S, 8):
        c = np.array([0.30, 0.22, 0.14]) * (0.7 + 0.45 * rng.random())
        g = fbm(8, S, 1, 4, rng, wrap=False, aspect=0.1)
        img[y:y + 8] = shade(rgb(8, S, c), 0.75 + 0.45 * g)
        hline(img, y + 7, 0, S, [0.06, 0.04, 0.03])
        cut = int(rng.integers(0, S))
        vline(img, cut, y, y + 7, [0.06, 0.04, 0.03])
        img[y + 3, (cut + 3) % S] = [0.12, 0.12, 0.12]
    dust = blotches(S, S, rng, base=4, threshold=0.6, softness=0.2)
    img = lerp(img, np.array([0.40, 0.38, 0.34]), dust * 0.4)
    return np.clip(img, 0, 1)


@tex('floor_tiles_bw')
def floor_tiles_bw(seed=64):
    rng = np.random.default_rng(seed)
    img = np.zeros((S, S, 3))
    for y in range(0, S, 16):
        for x in range(0, S, 16):
            c = [0.64, 0.62, 0.56] if ((x + y) // 16) % 2 == 0 else [0.10, 0.10, 0.11]
            rect(img, y, x, y + 16, x + 16, c)
            hline(img, y, x, x + 16, [0.30, 0.30, 0.28]); vline(img, x, y, y + 16, [0.30, 0.30, 0.28])
    img = shade(img, 0.85 + 0.2 * fbm(S, S, 6, 3, rng))
    c = cracks(S, S, rng, 3, (8, 24))
    img = shade(img, 1 - 0.5 * c)
    return np.clip(img, 0, 1)


@tex('ceil_ornate')
def ceil_ornate(seed=65):
    """Moulded plaster ceiling, a coffer per tile."""
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.56, 0.53, 0.45])
    img = shade(img, 0.85 + 0.2 * fbm(S, S, 6, 3, rng))
    bevel(img, 2, 2, 62, 62, 1.2, 0.6)
    bevel(img, 6, 6, 58, 58, 0.7, 1.2)
    rose = disc(S, S, 32, 32, 9) - disc(S, S, 32, 32, 6)
    img = shade(img, 1 - 0.25 * np.clip(rose, 0, 1))
    stain = blotches(S, S, rng, base=3, threshold=0.6, softness=0.15)
    img = lerp(img, img * np.array([0.7, 0.62, 0.45]), stain * 0.6)
    return np.clip(img, 0, 1)


@tex('ceil_beams')
def ceil_beams(seed=66):
    """Attic rafters and boards."""
    rng = np.random.default_rng(seed)
    img = ceil_wood(seed + 1).copy() * 0.8
    for x in (0, 32):
        rect(img, 0, x, S, x + 9, [0.20, 0.13, 0.07])
        vline(img, x, 0, S, [0.32, 0.22, 0.12]); vline(img, x + 8, 0, S, [0.08, 0.05, 0.03])
    web = cracks(S, S, rng, 3, (10, 30))
    img = lerp(img, np.array([0.55, 0.55, 0.52]), web * 0.35)
    return np.clip(img, 0, 1)


@tex('ceil_vault')
def ceil_vault(seed=67):
    """Cellar brick vault."""
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.18, 0.15, 0.13])
    for row in range(0, S, 8):
        off = 8 if (row // 8) % 2 else 0
        for x in range(-off, S, 16):
            c = np.array([0.36, 0.19, 0.13]) * (0.7 + 0.4 * rng.random())
            x0, x1 = max(0, x), min(S, x + 15)
            if x1 > x0:
                rect(img, row, x0, row + 7, x1, c)
    img = shade(img, 0.7 + 0.4 * fbm(S, S, 5, 4, rng))
    damp = blotches(S, S, rng, base=3, threshold=0.55, softness=0.15)
    img = lerp(img, img * np.array([0.5, 0.6, 0.5]), damp * 0.6)
    return np.clip(img, 0, 1)
