"""Textures for 3D props: 64x64, stored column-major in ROM.
Tiled materials repeat every 64 texels (one tile). "Decal" textures cover a
whole face (u 0..64 across, v 0..64 down)."""
import numpy as np
from noise import *
import textures as T

S = 64
TEXTURES = {}


def tex(name):
    def deco(fn):
        TEXTURES[name] = fn
        return fn
    return deco


def wood(color, rng, aspect=0.12, contrast=0.45, planks=0):
    """Wood with the grain running along u: fine fibres, growth rings bent by
    a slow wobble, thin dark figure lines; optional plank seams."""
    fib = fbm(S, S, 2, 2, rng, aspect=24)                 # fine fibres along u
    wob = fbm(S, S, 3, 3, rng, aspect=max(0.34, aspect * 5))
    v = np.arange(S)[:, None] / S
    rings = 0.5 + 0.5 * np.sin(2 * np.pi * (7 * v + 1.5 * wob))
    figure = np.clip((rings - 0.86) / 0.1, 0, 1)
    img = shade(rgb(S, S, color), 0.82 + contrast * 1.1 * (fib - 0.5) + 0.14 * (rings - 0.5))
    img = shade(img, 1 - 0.28 * figure)
    if planks:
        for y in range(0, S, S // planks):
            hline(img, y, 0, S, np.array(color) * 0.4)
            hline(img, (y + 1) % S, 0, S, np.array(color) * 1.25)
    wear = blotches(S, S, rng, base=4, threshold=0.7, softness=0.1)
    img = lerp(img, img * 1.25, wear * 0.4)
    return img


def wood_v(color, rng, contrast=0.45):
    """Grain running vertically (for upright faces)."""
    return np.transpose(wood(color, rng, contrast=contrast), (1, 0, 2)).copy()


@tex('wood_dark')
def wood_dark(seed=201):
    return np.clip(wood([0.24, 0.12, 0.06], np.random.default_rng(seed)), 0, 1)


@tex('wood_oak')
def wood_oak(seed=202):
    return np.clip(wood([0.38, 0.24, 0.12], np.random.default_rng(seed)), 0, 1)


@tex('wood_darkv')
def wood_darkv(seed=203):
    return np.clip(wood_v([0.24, 0.12, 0.06], np.random.default_rng(seed)), 0, 1)


@tex('wood_painted')
def wood_painted(seed=204):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.62, 0.60, 0.52])
    img = shade(img, 0.88 + 0.18 * fbm(S, S, 6, 3, rng))
    chip = blotches(S, S, rng, base=6, threshold=0.66, softness=0.05)
    img = lerp(img, np.array([0.30, 0.20, 0.12]), chip * 0.8)
    return np.clip(img, 0, 1)


def grime(img, rng, amount=0.2):
    n = fbm(S, S, 4, 4, rng)
    return shade(img, 1 - amount + amount * 2 * n * 0.9)


def tufted(color, rng, step=16):
    """Button-tufted upholstery: diamond creases with a button at each node."""
    img = rgb(S, S, color)
    img = shade(img, 0.8 + 0.3 * fbm(S, S, 6, 4, rng))
    yy, xx = np.mgrid[0:S, 0:S].astype(float)
    h = step / 2
    u = ((xx + yy) % step) - h
    v = ((xx - yy) % step) - h
    crease = np.exp(-(np.minimum(np.abs(np.abs(u) - h), np.abs(np.abs(v) - h)) / 0.9) ** 2)
    puff = (1 - (np.abs(u) + np.abs(v)) / step) ** 0.5
    img = shade(img, 0.78 + 0.32 * puff - 0.3 * crease)
    for y in range(0, S, int(h)):
        for x in range(0 if (y // int(h)) % 2 == 0 else int(h), S, step):
            img = lerp(img, np.array(color) * 0.35, disc(S, S, y, x, 1.1))
    return img


@tex('velvet_red')
def velvet_red(seed=205):
    rng = np.random.default_rng(seed)
    return np.clip(tufted([0.40, 0.08, 0.09], rng), 0, 1)


@tex('velvet_green')
def velvet_green(seed=206):
    rng = np.random.default_rng(seed)
    return np.clip(tufted([0.14, 0.26, 0.17], rng), 0, 1)


def seat_front(color, rng, cushions=1):
    """Front of an upholstered seat (u across, v down its height): the seat
    cushions' piped fronts, the frame below with a pleated skirt, the shadow
    under the chair."""
    c = np.array(color)
    img = rgb(S, S, c)
    img = shade(img, 0.86 + 0.22 * fbm(S, S, 8, 3, rng))
    u = np.arange(S)
    cw = S // cushions
    for k in range(cushions):                        # cushion fronts: rows 0-26
        x0, x1 = k * cw, (k + 1) * cw
        prof = 0.72 + 0.48 * np.sin(np.linspace(0.15, np.pi - 0.15, x1 - x0)) ** 0.6
        img[0:26, x0:x1] = img[0:26, x0:x1] * prof[None, :, None]
        img[0:26, x0] *= 0.45
        img[0:26, x1 - 1] *= 0.55
    img[0:2] = np.clip(img[0:2] * 1.55, 0, 1)        # piping catching the light
    img[24:27] *= 0.45                               # the crease under the cushions
    img[27:29] = np.clip(img[27:29] * 1.35, 0, 1)    # the frame's rolled edge
    pleat = 0.80 + 0.28 * np.abs(np.sin(u * np.pi / 6))[None, :]
    img[44:58] = shade(img[44:58], pleat[:, :, None] if pleat.ndim == 2 else pleat)
    img[43] *= 0.6
    img[56:58] *= 0.65                               # the skirt's hem
    img[58:64] = c * 0.18                            # shadow under the seat
    return img


def seat_back(color, rng, step=16):
    """Inside of an upholstered back: deep buttoned tufting under a rolled top."""
    img = tufted(color, rng, step=step)
    v = np.arange(S)
    roll = np.clip(1.25 - 0.9 * ((v - 6) / 7.0) ** 2, 0.55, 1.4)
    img[0:13] = shade(img[0:13], roll[0:13, None])
    img[13:15] *= 0.5                                # under the roll
    img[58:64] = shade(img[58:64], np.linspace(0.85, 0.45, 6)[:, None])
    return img


@tex('seat_front_red')
def seat_front_red(seed=250):
    return np.clip(seat_front([0.40, 0.08, 0.09], np.random.default_rng(seed)), 0, 1)


@tex('seat_front_green')
def seat_front_green(seed=251):
    return np.clip(seat_front([0.14, 0.26, 0.17], np.random.default_rng(seed), cushions=3), 0, 1)


@tex('seat_back_red')
def seat_back_red(seed=252):
    return np.clip(seat_back([0.40, 0.08, 0.09], np.random.default_rng(seed)), 0, 1)


@tex('seat_back_green')
def seat_back_green(seed=253):
    return np.clip(seat_back([0.14, 0.26, 0.17], np.random.default_rng(seed)), 0, 1)


@tex('pew_end')
def pew_end(seed=254):
    """A pew's end board (u along the pew's depth, v down): a scrolled top,
    a raised border round a sunk panel with a carved quatrefoil."""
    rng = np.random.default_rng(seed)
    img = wood_v([0.22, 0.12, 0.06], rng, contrast=0.35)
    yy, xx = np.mgrid[0:S, 0:S].astype(float)
    # the top scroll: a darker crescent cut into the upper corners
    scroll = np.clip(1 - np.abs(np.hypot(yy - 2, xx - 32) - 26) / 2.5, 0, 1) * (yy < 14)
    img = lerp(img, img * 0.45, scroll * 0.9)
    img = lerp(img, img * 1.35, np.clip(1 - np.abs(np.hypot(yy - 1, xx - 32) - 23) / 1.5, 0, 1)[..., None] * (yy < 12)[..., None] * 0.7)
    bevel(img, 14, 4, 62, 60, 1.35, 0.55)
    bevel(img, 19, 9, 57, 55, 0.6, 1.3)
    for cy, cx in ((32, 26), (32, 38), (26, 32), (38, 32)):
        img = lerp(img, img * 0.55, disc(S, S, cy, cx, 5.2)[..., None] * 0.8)
        img = lerp(img, img * 1.3, disc(S, S, cy, cx, 3.2)[..., None] * 0.6)
    img = lerp(img, img * 1.5, disc(S, S, 32, 32, 2.6)[..., None])
    return np.clip(img, 0, 1)


@tex('pew_back')
def pew_back(seed=255):
    """The back of a pew as the next row sees it (u along it, one tile per
    64 texels): a moulded top rail and two sunk panels per half tile."""
    rng = np.random.default_rng(seed)
    img = wood([0.22, 0.12, 0.06], rng, contrast=0.35)
    img[0:6] = np.clip(img[0:6] * np.array([1.5, 1.35, 1.2, 1.0, 0.8, 0.55])[:, None, None], 0, 1)
    for x0 in (2, 34):
        bevel(img, 9, x0, 60, x0 + 28, 1.3, 0.55)
        bevel(img, 13, x0 + 4, 56, x0 + 24, 0.6, 1.25)
    img[60:64] *= 0.6
    img = grime(img, rng, 0.12)
    return np.clip(img, 0, 1)


@tex('linen')
def linen(seed=207):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.66, 0.64, 0.58])
    img = shade(img, 0.85 + 0.2 * fbm(S, S, 3, 4, rng, aspect=0.5))
    folds = 0.5 + 0.5 * np.sin(np.linspace(0, 9, S)[None, :] + 3 * fbm(S, S, 2, 3, rng))
    img = shade(img, 0.85 + 0.2 * folds)
    stain = blotches(S, S, rng, base=3, threshold=0.68, softness=0.1)
    img = lerp(img, img * np.array([0.8, 0.72, 0.5]), stain * 0.6)
    return np.clip(img, 0, 1)


@tex('quilt')
def quilt(seed=208):
    rng = np.random.default_rng(seed)
    img = np.zeros((S, S, 3))
    cols = [[0.46, 0.16, 0.14], [0.30, 0.34, 0.22], [0.56, 0.50, 0.36], [0.22, 0.24, 0.36], [0.50, 0.30, 0.18]]
    for y in range(0, S, 8):
        for x in range(0, S, 8):
            rect(img, y, x, y + 8, x + 8, np.array(cols[int(rng.integers(0, len(cols)))]) * (0.85 + 0.25 * rng.random()))
            bevel(img, y, x, y + 8, x + 8, 1.18, 0.72)
    for k in range(0, S, 2):        # stitching
        img[k, ::8] *= 0.7
    img = shade(img, 0.82 + 0.28 * fbm(S, S, 4, 3, rng))
    return np.clip(img, 0, 1)


@tex('ticking')
def ticking(seed=209):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.62, 0.60, 0.54])
    for x in range(0, S, 8):
        rect(img, 0, x, S, x + 2, [0.30, 0.32, 0.40])
    img = shade(img, 0.8 + 0.25 * fbm(S, S, 4, 3, rng))
    stain = blotches(S, S, rng, base=3, threshold=0.62, softness=0.1)
    img = lerp(img, img * np.array([0.7, 0.6, 0.4]), stain * 0.7)
    return np.clip(img, 0, 1)


@tex('brass')
def brass(seed=210):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.62, 0.48, 0.20])
    img = shade(img, 0.7 + 0.45 * fbm(S, S, 3, 3, rng, aspect=4))
    tarn = blotches(S, S, rng, base=5, threshold=0.55, softness=0.15)
    img = lerp(img, img * np.array([0.5, 0.6, 0.45]), tarn * 0.6)
    return np.clip(img, 0, 1)


@tex('iron')
def iron(seed=211):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.16, 0.16, 0.16])
    img = shade(img, 0.75 + 0.45 * fbm(S, S, 5, 4, rng))
    rust = blotches(S, S, rng, base=6, threshold=0.6, softness=0.12)
    img = lerp(img, np.array([0.34, 0.16, 0.08]), rust * 0.6)
    return np.clip(img, 0, 1)


@tex('marble')
def marble(seed=212):
    rng = np.random.default_rng(seed)
    n = fbm(S, S, 3, 5, rng)
    veins = np.abs(np.sin((np.linspace(0, 6, S)[None, :] + np.linspace(0, 3, S)[:, None] + n * 6)))
    img = rgb(S, S, [0.70, 0.68, 0.64])
    img = lerp(img, np.array([0.34, 0.34, 0.36]), (1 - veins) ** 6 * 0.8)
    return np.clip(shade(img, 0.9 + 0.12 * n), 0, 1)


@tex('enamel')
def enamel(seed=213):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.70, 0.70, 0.66])
    img = shade(img, 0.9 + 0.12 * fbm(S, S, 4, 3, rng))
    rust = drip_streaks(S, S, rng, count=4, length=(10, 40), width=(1, 3))
    img = lerp(img, np.array([0.40, 0.26, 0.14]), rust * 0.5)
    return np.clip(img, 0, 1)


@tex('books')
def books(seed=214):
    """Two shelves of book spines (a bookcase front repeats this per tile)."""
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.10, 0.06, 0.04])
    for shelf in range(2):
        y0, y1 = shelf * 32 + 3, shelf * 32 + 29
        x = 1
        while x < S - 1:
            w = int(rng.integers(3, 7))
            top = y0 + int(rng.integers(0, 7))
            c = np.array([[0.40, 0.10, 0.08], [0.12, 0.22, 0.14], [0.30, 0.22, 0.10], [0.14, 0.14, 0.26],
                          [0.36, 0.30, 0.20], [0.20, 0.08, 0.10]][int(rng.integers(0, 6))])
            c = c * (0.7 + 0.5 * rng.random())
            rect(img, top, x, y1, min(S - 1, x + w), c)
            if rng.random() < 0.6:
                hline(img, top + 3, x, min(S - 1, x + w), [0.65, 0.52, 0.22], 0.7)
                hline(img, y1 - 4, x, min(S - 1, x + w), [0.65, 0.52, 0.22], 0.7)
            vline(img, min(S - 1, x + w), top, y1, [0.04, 0.03, 0.02])
            x += w + 1
        rect(img, y1, 0, y1 + 3, S, [0.24, 0.13, 0.06])
        hline(img, y1, 0, S, [0.36, 0.22, 0.12])
    return np.clip(img, 0, 1)


def panel_front(rng, color, rows, cols, handles=True, knob=(0.70, 0.56, 0.24)):
    img = wood_v(color, rng, contrast=0.35)
    bevel(img, 0, 0, S, S, 1.3, 0.55)
    ph, pw = (S - 4) // rows, (S - 4) // cols
    for r in range(rows):
        for c in range(cols):
            y0, x0 = 2 + r * ph, 2 + c * pw
            bevel(img, y0 + 1, x0 + 1, y0 + ph - 1, x0 + pw - 1, 1.25, 0.6)
            if handles:
                img = lerp(img, np.array(knob), disc(S, S, y0 + ph // 2, x0 + pw // 2, 1.6))
    return img


@tex('wardrobe_front')
def wardrobe_front(seed=215):
    rng = np.random.default_rng(seed)
    img = wood_v([0.24, 0.12, 0.06], rng, 0.35)
    bevel(img, 0, 0, S, S, 1.3, 0.55)
    for x0 in (3, 33):
        bevel(img, 3, x0, 50, x0 + 28, 1.25, 0.6)
        bevel(img, 7, x0 + 4, 30, x0 + 24, 0.7, 1.25)      # carved upper panel
        bevel(img, 33, x0 + 4, 46, x0 + 24, 0.7, 1.25)
    vline(img, 31, 3, 50, [0.08, 0.04, 0.02]); vline(img, 32, 3, 50, [0.08, 0.04, 0.02])
    for x in (28, 36):
        img = lerp(img, np.array([0.70, 0.56, 0.24]), disc(S, S, 27, x, 1.4))
    bevel(img, 52, 3, 62, 61, 1.25, 0.6)                    # drawer
    img = lerp(img, np.array([0.70, 0.56, 0.24]), disc(S, S, 57, 32, 1.6))
    return np.clip(img, 0, 1)


@tex('dresser_front')
def dresser_front(seed=216):
    rng = np.random.default_rng(seed)
    img = wood([0.30, 0.16, 0.08], rng, contrast=0.35)
    bevel(img, 0, 0, S, S, 1.3, 0.55)
    for k in range(4):
        y0 = 3 + k * 15
        bevel(img, y0, 3, y0 + 13, 61, 1.25, 0.6)
        for x in (16, 48):
            rect(img, y0 + 5, x - 3, y0 + 8, x + 3, [0.62, 0.48, 0.20])
    return np.clip(img, 0, 1)


@tex('clock_front')
def clock_front(seed=217):
    rng = np.random.default_rng(seed)
    img = wood_v([0.26, 0.13, 0.06], rng, 0.35)
    bevel(img, 0, 0, S, S, 1.3, 0.55)
    # face
    img = lerp(img, np.array([0.62, 0.48, 0.20]), disc(S, S, 12, 32, 11))
    img = lerp(img, np.array([0.70, 0.66, 0.56]), disc(S, S, 12, 32, 9))
    for k in range(12):
        a = k * np.pi / 6
        y, x = 12 - 7.5 * np.cos(a), 32 + 7.5 * np.sin(a)
        img[int(round(y)), int(round(x))] = [0.08, 0.06, 0.04]
    for (dy, dx) in ((-1, 0), (-2, 0), (-3, 0), (-4, 1), (0, 1), (1, 2), (2, 3)):
        img[12 + dy, 32 + dx] = [0.06, 0.05, 0.04]
    # pendulum window
    rect(img, 28, 22, 58, 42, [0.05, 0.05, 0.06])
    bevel(img, 27, 21, 59, 43, 0.6, 1.3)
    vline(img, 32, 29, 50, [0.40, 0.32, 0.14])
    img = lerp(img, np.array([0.66, 0.52, 0.22]), disc(S, S, 50, 32, 4))
    return np.clip(img, 0, 1)


@tex('piano_front')
def piano_front(seed=218):
    rng = np.random.default_rng(seed)
    img = wood([0.10, 0.06, 0.04], rng, contrast=0.3)
    bevel(img, 0, 0, S, S, 1.25, 0.6)
    for x0 in (4, 24, 44):
        bevel(img, 4, x0, 26, x0 + 16, 1.25, 0.6)
    # keyboard band
    rect(img, 30, 0, 40, S, [0.70, 0.68, 0.60])
    for x in range(0, S, 3):
        vline(img, x, 30, 40, [0.30, 0.28, 0.24])
    for x in range(1, S, 3):
        if (x // 3) % 7 not in (2, 6):
            rect(img, 30, x, 36, x + 2, [0.05, 0.04, 0.04])
    bevel(img, 42, 4, 62, 60, 1.25, 0.6)
    return np.clip(img, 0, 1)


@tex('fireplace_front')
def fireplace_front(seed=219):
    rng = np.random.default_rng(seed)
    img = marble(seed + 1).copy() * np.array([0.62, 0.60, 0.58])
    bevel(img, 0, 0, S, S, 1.3, 0.55)
    # firebox opening with dying embers
    rect(img, 22, 14, 64, 50, [0.03, 0.02, 0.02])
    emb = blotches(S, S, rng, base=8, threshold=0.6, softness=0.1)
    emb[:56] = 0
    img = lerp(img, np.array([0.55, 0.14, 0.04]), emb * 0.9)
    for x in range(16, 48, 6):
        vline(img, x, 44, 58, [0.18, 0.18, 0.18])           # grate bars
    hline(img, 44, 16, 48, [0.2, 0.2, 0.2])
    bevel(img, 20, 12, 64, 52, 0.55, 1.3)
    rect(img, 0, 0, 6, S, [0.50, 0.48, 0.46])                 # mantel edge
    return np.clip(img, 0, 1)


@tex('stove_front')
def stove_front(seed=220):
    rng = np.random.default_rng(seed)
    img = iron(seed + 1).copy()
    bevel(img, 0, 0, S, S, 1.3, 0.55)
    for (y0, x0) in ((8, 4), (8, 34), (36, 4), (36, 34)):
        bevel(img, y0, x0, y0 + 24, x0 + 26, 1.35, 0.5)
        rect(img, y0 + 10, x0 + 18, y0 + 13, x0 + 24, [0.55, 0.50, 0.40])
    return np.clip(img, 0, 1)


def painting(seed, palette):
    rng = np.random.default_rng(seed)
    img = np.zeros((S, S, 3))
    rect(img, 0, 0, S, S, [0.48, 0.36, 0.14])
    bevel(img, 0, 0, S, S, 1.4, 0.45)
    bevel(img, 3, 3, S - 3, S - 3, 0.6, 1.35)
    n = fbm(S - 12, S - 12, 3, 4, rng, wrap=False)
    canvas = np.zeros((S - 12, S - 12, 3))
    c0, c1, c2 = (np.array(c) for c in palette)
    canvas[:] = lerp(c0, c1, n[..., None])
    img[6:S - 6, 6:S - 6] = canvas
    return img, rng


@tex('portrait')
def portrait(seed=221):
    img, rng = painting(seed, [[0.08, 0.06, 0.05], [0.18, 0.12, 0.08], [0, 0, 0]])
    # a pale face and dark coat, eyes that follow you
    img = lerp(img, np.array([0.58, 0.46, 0.36]), ellipse(S, S, 24, 32, 9, 7))
    img = lerp(img, np.array([0.06, 0.05, 0.05]), ellipse(S, S, 50, 32, 14, 16) * (np.arange(S)[:, None] > 34))
    for x in (29, 35):
        img[23, x] = [0.05, 0.03, 0.03]
    img = lerp(img, np.array([0.30, 0.22, 0.18]), ellipse(S, S, 15, 32, 6, 8) * 0.8)     # hair
    return np.clip(img, 0, 1)


@tex('landscape')
def landscape(seed=222):
    img, rng = painting(seed, [[0.14, 0.18, 0.20], [0.30, 0.30, 0.26], [0, 0, 0]])
    yy = np.arange(S)[:, None]
    lake = (yy > 36) & (yy < S - 6)
    img = np.where(lake[..., None] & (np.arange(S)[None, :, None] > 5) & (np.arange(S)[None, :, None] < S - 6),
                   img * np.array([0.4, 0.45, 0.55]), img)
    # the house on its island, one lit window
    rect(img, 26, 26, 36, 40, [0.05, 0.05, 0.06])
    rect(img, 22, 30, 26, 36, [0.05, 0.05, 0.06])
    img[30, 33] = [0.8, 0.6, 0.2]
    return np.clip(img, 0, 1)


@tex('mirror')
def mirror(seed=223):
    img, rng = painting(seed, [[0.10, 0.11, 0.12], [0.22, 0.24, 0.26], [0, 0, 0]])
    streak = fbm(S, S, 2, 3, rng, aspect=3)
    img[6:S - 6, 6:S - 6] = lerp(img[6:S - 6, 6:S - 6], np.array([0.40, 0.42, 0.44]),
                                 (streak[6:S - 6, 6:S - 6] > 0.6)[..., None] * 0.4)
    crack = cracks(S, S, rng, 2, (14, 30))
    crack[:6] = 0; crack[-6:] = 0; crack[:, :6] = 0; crack[:, -6:] = 0
    img = lerp(img, np.array([0.7, 0.7, 0.72]), crack[..., None] * 0.6)
    return np.clip(img, 0, 1)


@tex('rug')
def rug(seed=224):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.30, 0.08, 0.08])
    yy, xx = np.mgrid[0:S, 0:S]
    d = np.maximum(np.abs(yy - 31.5), np.abs(xx - 31.5))
    img = np.where(((d > 26) & (d < 29))[..., None], np.array([0.50, 0.38, 0.16]), img)
    img = np.where(((d > 22) & (d < 24))[..., None], np.array([0.10, 0.12, 0.22]), img)
    med = (np.abs(yy - 31.5) + np.abs(xx - 31.5)) < 14
    img = np.where(med[..., None], np.array([0.12, 0.16, 0.26]), img)
    med2 = (np.abs(yy - 31.5) + np.abs(xx - 31.5)) < 7
    img = np.where(med2[..., None], np.array([0.52, 0.40, 0.18]), img)
    img = shade(img, 0.8 + 0.3 * fbm(S, S, 6, 3, rng))
    wear = blotches(S, S, rng, base=3, threshold=0.62, softness=0.12)
    img = lerp(img, img * 0.6, wear)
    return np.clip(img, 0, 1)


@tex('tablecloth')
def tablecloth(seed=225):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.66, 0.64, 0.58])
    yy, xx = np.mgrid[0:S, 0:S]
    lace = ((np.sin(xx * 0.8) * np.sin(yy * 0.8)) > 0.6)
    img = np.where(lace[..., None], img * 0.82, img)
    stain = blotches(S, S, rng, base=3, threshold=0.66, softness=0.08)
    img = lerp(img, np.array([0.40, 0.18, 0.14]), stain * 0.7)     # wine
    return np.clip(img, 0, 1)


@tex('sheet')
def sheet(seed=226):
    """Dust sheet over furniture: deep folds hanging down (across u), finer
    creases between them, grey dust settled in the hollows, old stains."""
    rng = np.random.default_rng(seed)
    u = np.arange(S)[None, :] / S
    v = np.arange(S)[:, None] / S
    bend = fbm(S, S, 2, 3, rng, aspect=1.0)
    folds = np.sin(2 * np.pi * (3 * u + 0.35 * bend + 0.15 * v))
    creases = np.sin(2 * np.pi * (8 * u + 0.6 * bend))
    light = 0.80 + 0.26 * folds + 0.07 * creases
    img = shade(rgb(S, S, [0.62, 0.61, 0.56]), light)
    hollow = np.clip(-folds, 0, 1) ** 2
    img = lerp(img, img * np.array([0.78, 0.76, 0.70]), hollow * 0.6)
    img = shade(img, 0.90 + 0.14 * fbm(S, S, 6, 3, rng))
    stain = blotches(S, S, rng, base=3, threshold=0.70, softness=0.08)
    img = lerp(img, img * np.array([0.82, 0.74, 0.55]), stain * 0.55)
    return np.clip(img, 0, 1)


@tex('leather')
def leather(seed=227):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.26, 0.14, 0.08])
    img = shade(img, 0.75 + 0.4 * fbm(S, S, 6, 4, rng))
    for y in (8, 56):
        rect(img, y, 0, y + 4, S, [0.50, 0.40, 0.18])
    return np.clip(img, 0, 1)


@tex('crate')
def crate(seed=228):
    rng = np.random.default_rng(seed)
    img = wood([0.36, 0.28, 0.16], rng, contrast=0.4)
    for y in range(0, S, 16):
        hline(img, y, 0, S, [0.12, 0.09, 0.05])
    bevel(img, 0, 0, S, S, 1.3, 0.5)
    for x in (4, 59):
        rect(img, 0, x - 2, S, x + 2, [0.30, 0.22, 0.12])
    return np.clip(img, 0, 1)


@tex('wine_rack')
def wine_rack(seed=229):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.06, 0.04, 0.03])
    for y in range(4, S, 12):
        for x in range(4, S, 12):
            img = lerp(img, np.array([0.10, 0.16, 0.10]), disc(S, S, y, x, 4.2))
            img = lerp(img, np.array([0.30, 0.36, 0.28]), disc(S, S, y - 1, x - 1, 1.2))
    for k in range(0, S, 12):
        vline(img, k, 0, S, [0.26, 0.16, 0.08]); hline(img, k, 0, S, [0.26, 0.16, 0.08])
    # a fine bloom of dust on the necks, not big blotches
    dust = fbm(S, S, 16, 2, rng)
    img = lerp(img, np.array([0.34, 0.34, 0.32]), np.clip((dust - 0.6) / 0.15, 0, 1)[..., None] * 0.35)
    return np.clip(img, 0, 1)


def leaf(seed, color, glazed=False, metal=False, planks=False):
    """Door leaf face: hinge at u=0, handle near u=63."""
    rng = np.random.default_rng(seed)
    if metal:
        img = T.leaf_metal()[:, :40]
        img = np.array([[img[y, x * 40 // 64] for x in range(64)] for y in range(64)])
        return np.clip(img, 0, 1)
    img = wood_v(color, rng, 0.35)
    bevel(img, 0, 0, S, S, 1.3, 0.55)
    if planks:
        for x in range(0, S, 10):
            vline(img, x, 0, S, np.array(color) * 0.4)
        for y in (8, 54):
            rect(img, y, 2, y + 5, S - 2, np.array(color) * 0.8)
            bevel(img, y, 2, y + 5, S - 2, 1.2, 0.6)
        rect(img, 32, 54, 36, 62, [0.20, 0.20, 0.20])
        return np.clip(img, 0, 1)
    if glazed:
        rect(img, 5, 8, 30, 56, [0.06, 0.07, 0.09])
        for x in (8, 24, 40, 55):
            vline(img, x, 5, 30, np.array(color))
        for y in (5, 17, 29):
            hline(img, y, 8, 56, np.array(color))
        bevel(img, 4, 7, 31, 57, 0.6, 1.3)
    else:
        bevel(img, 4, 8, 28, 56, 1.25, 0.6)
        bevel(img, 7, 12, 25, 52, 0.75, 1.2)
    bevel(img, 34, 8, 60, 56, 1.25, 0.6)
    bevel(img, 37, 12, 57, 52, 0.75, 1.2)
    # brass knob and keyhole near the free edge
    img = lerp(img, np.array([0.40, 0.30, 0.12]), ellipse(S, S, 33, 58, 4, 2))
    img = lerp(img, np.array([0.74, 0.60, 0.26]), disc(S, S, 31, 58, 1.7))
    img[35, 58] = [0.03, 0.02, 0.01]
    for y in (8, 52):
        rect(img, y, 0, y + 4, 2, [0.50, 0.40, 0.18])
    return np.clip(img, 0, 1)


@tex('leaf_panel')
def leaf_panel():
    return leaf(230, [0.26, 0.14, 0.07])


@tex('leaf_double')
def leaf_double():
    return leaf(231, [0.28, 0.16, 0.08], glazed=True)


@tex('leaf_cellar')
def leaf_cellar():
    return leaf(232, [0.30, 0.22, 0.13], planks=True)


@tex('leaf_metal')
def leaf_metal():
    return leaf(233, [0, 0, 0], metal=True)


@tex('leaf_nursery')
def leaf_nursery():
    return leaf(234, [0.56, 0.54, 0.46])


@tex('machine')
def machine():
    return T.machine()


@tex('fusebox')
def fusebox():
    return T.fusebox()


@tex('generator')
def generator():
    return T.generator()


@tex('wax')
def wax(seed=235):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.70, 0.64, 0.50])
    drip = drip_streaks(S, S, rng, count=6, length=(10, 40), width=(2, 4))
    return np.clip(shade(img, 0.85 + 0.2 * drip), 0, 1)


@tex('altar_cloth')
def altar_cloth(seed=236):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.40, 0.05, 0.06])
    img = shade(img, 0.75 + 0.35 * fbm(S, S, 4, 3, rng, aspect=0.4))
    for y in (4, 8):
        hline(img, y, 0, S, [0.60, 0.46, 0.18])
    yy, xx = np.mgrid[0:S, 0:S]
    cross = ((np.abs(xx - 32) < 2) & (yy > 16) & (yy < 50)) | ((np.abs(yy - 26) < 2) & (np.abs(xx - 32) < 9))
    img = np.where(cross[..., None], np.array([0.62, 0.50, 0.20]), img)
    return np.clip(img, 0, 1)


@tex('stone_block')
def stone_block(seed=237):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.36, 0.35, 0.32])
    img = shade(img, 0.75 + 0.4 * fbm(S, S, 6, 4, rng))
    for y in (0, 32):
        hline(img, y, 0, S, [0.15, 0.15, 0.14])
    vline(img, 0, 0, 32, [0.15, 0.15, 0.14]); vline(img, 32, 32, 64, [0.15, 0.15, 0.14])
    return np.clip(img, 0, 1)



@tex('iron_bars')
def iron_bars(seed=240):
    """Iron bed end: a frame and bars over the shadowed wall behind (opaque)."""
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.05, 0.05, 0.06])
    img = shade(img, 0.8 + 0.4 * fbm(S, S, 4, 3, rng))
    iron = np.array([0.30, 0.31, 0.32])
    for x in list(range(4, S, 9)) + [0, S - 3]:
        rect(img, 0, x, S, x + 3, iron * (0.9 + 0.2 * rng.random()))
        vline(img, x, 0, S, iron * 1.6)
    for y in (0, 30, S - 4):
        rect(img, y, 0, y + 4, S, iron * 1.1)
        hline(img, y, 0, S, iron * 1.7)
    for x in range(8, S, 18):          # brass knobs on the top rail
        img = lerp(img, np.array([0.62, 0.48, 0.20]), disc(S, S, 2, x, 2.0))
    rust = blotches(S, S, rng, 6, 4, 0.62, 0.1)
    img = lerp(img, img * np.array([1.2, 0.7, 0.4]), rust * 0.5)
    return np.clip(img, 0, 1)


@tex('cot_slats')
def cot_slats(seed=241):
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.08, 0.07, 0.06])
    paint = np.array([0.66, 0.64, 0.56])
    for x in range(2, S, 8):
        rect(img, 0, x, S, x + 4, paint * (0.9 + 0.15 * rng.random()))
        vline(img, x, 0, S, paint * 1.15)
    rect(img, 0, 0, 6, S, paint); rect(img, S - 6, 0, S, S, paint)
    hline(img, 5, 0, S, paint * 0.6)
    chip = blotches(S, S, rng, base=6, threshold=0.68, softness=0.05)
    img = lerp(img, np.array([0.30, 0.20, 0.12]), chip * 0.7)
    return np.clip(img, 0, 1)


# ------------------------------------------------------------ the grand stair
RUNNER = [0.42, 0.06, 0.07]        # deep red stair carpet
GOLD = [0.78, 0.60, 0.24]
OAK_LIGHT = [0.50, 0.34, 0.18]


def runner_band(img, u0, u1, rng, vertical=True):
    """A carpet runner between texel columns u0..u1: red pile, a gold border
    and a small repeating lozenge."""
    S_ = img.shape[0]
    pile = 0.82 + 0.3 * fbm(S_, S_, 8, 3, rng)
    run = np.array(RUNNER)[None, None, :] * pile[..., None]
    img[:, u0:u1] = run[:, u0:u1]
    for x in (u0, u0 + 1, u1 - 2, u1 - 1):
        img[:, x] = np.array(GOLD) * (0.85 + 0.2 * pile[:, x:x + 1])
    for x in (u0 + 3, u1 - 4):
        img[:, x] = np.array([0.16, 0.12, 0.20])
    yy = np.arange(S_)
    cx = (u0 + u1 - 1) / 2
    for y0 in range(4, S_, 16):
        for x in range(u0 + 5, u1 - 5):
            for y in range(y0, y0 + 9):
                if abs(x - cx) / 6 + abs(y - (y0 + 4)) / 4.5 < 1.0:
                    img[y, x] = np.array(GOLD) * 0.8 if abs(x - cx) / 6 + abs(y - (y0 + 4)) / 4.5 > 0.55 else \
                        np.array([0.12, 0.10, 0.22])
    return img


@tex('stair_tread')
def stair_tread(seed=240):
    """Tread seen from above: u across the stair, v from the nosing (0) back
    to the next riser (64). Pale worn oak either side of the runner, a bright
    nosing edge and a brass stair rod at the back."""
    rng = np.random.default_rng(seed)
    img = wood(OAK_LIGHT, rng, contrast=0.35)
    img = runner_band(img, 15, 49, rng)
    # wear down the middle of the runner
    wear = np.exp(-((np.arange(S) - 32) / 9.0) ** 2)[None, :] * (0.25 + 0.2 * fbm(S, S, 4, 3, rng))
    img = shade(img, 1 - 0.35 * wear[..., None] * (np.arange(S)[None, :, None] > 14) * (np.arange(S)[None, :, None] < 49))
    # nosing: a rounded edge catching the light
    for y, f in ((0, 1.55), (1, 1.35), (2, 1.15), (3, 0.75)):
        img[y] = np.clip(img[y] * f, 0, 1)
    # brass rod holding the runner into the angle of the step
    for y, f in ((56, 0.55), (57, 1.0), (58, 1.25), (59, 0.9), (60, 0.5)):
        img[y, 13:51] = np.array([0.74, 0.58, 0.24]) * f
    img[57:60, 12] = img[57:60, 50] = np.array([0.45, 0.36, 0.16])
    return np.clip(img, 0, 1)


@tex('stair_riser')
def stair_riser(seed=241):
    """Riser: the runner falling over dark stained wood, shadowed under the
    nosing. A riser is a thin strip on screen, so it maps only 8 texel rows
    (v 0..8, repeated down the texture): its mips stay sharp and it can be
    drawn as rows."""
    rng = np.random.default_rng(seed)
    full = wood([0.18, 0.09, 0.05], rng, contrast=0.3)
    full = runner_band(full, 15, 49, rng)
    band = full[20:28].copy()
    shadow = np.array([0.42, 0.55, 0.68, 0.80, 0.90, 0.97, 1.0, 1.0])
    band = band * shadow[:, None, None]
    return np.clip(np.tile(band, (S // 8, 1, 1)), 0, 1)


@tex('stair_steps')
def stair_steps(seed=247):
    """The flight seen from afar as one slope (the staircase's far model):
    every 16 rows, top down, one tread (the brass rod at the back, the
    nosing catching the light) and the riser below it."""
    tr, ri = stair_tread(), stair_riser()
    img = np.zeros((S, S, 3))
    for p0 in range(0, S, 16):
        for r in range(7):
            img[p0 + r] = tr[(6 - r) * 9 + 4] * 1.12
        img[p0 + 7] = np.clip(tr[1] * 1.7, 0, 1)            # the nosing
        for r in range(8):
            img[p0 + 8 + r] = ri[r] * (0.75 + 0.05 * r)
    return np.clip(img, 0, 1)


@tex('stair_string')
def stair_string(seed=242):
    """The closed string along the open side: polished mahogany, a bead
    moulding along each edge."""
    rng = np.random.default_rng(seed)
    img = wood([0.30, 0.11, 0.06], rng, contrast=0.4, aspect=0.08)
    img = shade(img, 0.95 + 0.25 * np.sin(np.linspace(0, np.pi, S))[:, None, None])
    for y, f in ((0, 1.6), (1, 1.3), (5, 0.6), (6, 1.35), (57, 1.35), (58, 0.6), (62, 1.3), (63, 0.7)):
        img[y] = np.clip(img[y] * f, 0, 1)
    return np.clip(img, 0, 1)


@tex('stair_panel')
def stair_panel(seed=243):
    """The panelled spandrel under the stair, a shade lighter than the hall's
    wainscot so the staircase stands out from the walls."""
    rng = np.random.default_rng(seed)
    img = wood_v([0.34, 0.20, 0.10], rng, contrast=0.35)
    bevel(img, 0, 0, S, S, 1.3, 0.55)
    for x0 in (4, 34):
        bevel(img, 5, x0, 59, x0 + 26, 1.35, 0.5)
        bevel(img, 9, x0 + 4, 55, x0 + 22, 0.62, 1.3)
    img = grime(img, rng, 0.15)
    return np.clip(img, 0, 1)


@tex('stair_cupboard')
def stair_cupboard(seed=248):
    """The cupboard under the stairs: a low panelled door in the spandrel
    under the half landing (the whole face), a brass knob and keyhole."""
    rng = np.random.default_rng(seed)
    img = wood_v([0.34, 0.20, 0.10], rng, contrast=0.35)
    bevel(img, 0, 0, S, S, 1.3, 0.55)
    dark = np.array([0.05, 0.03, 0.02])
    rect(img, 6, 8, 7, 56, dark); rect(img, 6, 8, 64, 9, dark); rect(img, 6, 55, 64, 56, dark)   # the door's gap
    door = wood_v([0.30, 0.17, 0.08], rng, contrast=0.4)
    img[7:64, 9:55] = door[7:64, 9:55]
    bevel(img, 7, 9, 64, 55, 1.25, 0.6)
    bevel(img, 12, 14, 34, 50, 0.65, 1.3)
    bevel(img, 39, 14, 60, 50, 0.65, 1.3)
    img = lerp(img, np.array([0.72, 0.58, 0.26]), disc(S, S, 36, 47, 2.0))     # knob
    rect(img, 40, 46, 43, 48, dark)                                              # keyhole
    img = grime(img, rng, 0.15)
    return np.clip(img, 0, 1)


@tex('baluster')
def baluster(seed=244):
    """Painted turned baluster on a flat quad (v from the handrail down to
    the tread): the full width shaded as a cylinder, the turnings as rings of
    light and shadow along it (prop faces have no see-through texels)."""
    rng = np.random.default_rng(seed)
    base = np.array([0.66, 0.62, 0.53])         # old ivory paint, darkened with age
    u = (np.arange(S) + 0.5) / S * 2 - 1
    cyl = 0.62 + 0.55 * np.sqrt(np.clip(1 - u ** 2, 0, 1)) - 0.12 * u
    v = np.arange(S) / (S - 1)
    band = np.ones(S)
    for c, w, f in ((0.03, 0.03, 0.55), (0.09, 0.02, 1.25), (0.13, 0.015, 0.5), (0.62, 0.12, 1.18),
                    (0.80, 0.015, 0.45), (0.84, 0.02, 1.25), (0.88, 0.015, 0.5), (0.96, 0.04, 0.7)):
        band = band * (1 + (f - 1) * np.exp(-((v - c) / w) ** 2))
    img = base[None, None, :] * cyl[None, :, None] * band[:, None, None]
    chips = blotches(S, S, rng, base=6, threshold=0.75, softness=0.05)
    img = lerp(img, img * np.array([0.55, 0.45, 0.35]), chips[..., None] * 0.7)
    return np.clip(img, 0, 1)


@tex('handrail')
def handrail(seed=245):
    """Polished mahogany handrail rounded on top (v down its height)."""
    rng = np.random.default_rng(seed)
    img = wood([0.28, 0.10, 0.05], rng, contrast=0.35, aspect=0.06)
    prof = np.array([1.9, 1.6, 1.35, 1.15, 1.0] + [0.9] * (S - 10) + [0.7, 0.6, 0.5, 0.45, 0.4])
    img = shade(img, prof[:S, None, None])
    return np.clip(img, 0, 1)


@tex('newel')
def newel(seed=246):
    """Newel post side: a sunk panel with a carved rosette."""
    rng = np.random.default_rng(seed)
    img = wood_v([0.26, 0.10, 0.05], rng, contrast=0.35)
    bevel(img, 0, 0, S, S, 1.4, 0.5)
    bevel(img, 6, 10, 58, 54, 0.6, 1.35)
    img = lerp(img, img * 1.5, disc(S, S, 18, 32, 6.5)[..., None] * 0.8)
    img = lerp(img, img * 0.6, disc(S, S, 18, 32, 3.0)[..., None] * 0.8)
    return np.clip(img, 0, 1)


def pole_tex(base, rng, rings, spec=0.35):
    """A slim turned pole drawn on a flat quad (Mesh.pole): u across it shaded
    as a cylinder with a highlight, v down it with turned rings."""
    base = np.array(base)
    u = (np.arange(S) + 0.5) / S * 2 - 1
    cyl = 0.45 + 0.6 * np.sqrt(np.clip(1 - u ** 2, 0, 1)) - 0.12 * u + spec * np.exp(-((u + 0.32) / 0.14) ** 2)
    v = np.arange(S) / (S - 1)
    band = np.ones(S)
    for c, w, f in rings:
        band = band * (1 + (f - 1) * np.exp(-((v - c) / w) ** 2))
    img = base[None, None, :] * cyl[None, :, None] * band[:, None, None]
    img = shade(img, 0.9 + 0.2 * fbm(S, S, 2, 3, rng, aspect=4))
    return img


@tex('pole_brass')
def pole_brass(seed=260):
    """The standard lamp's stem: tarnished brass, a collar at each end and a
    turned knop part way up."""
    rng = np.random.default_rng(seed)
    img = pole_tex([0.62, 0.47, 0.20], rng, ((0.02, 0.02, 1.35), (0.05, 0.012, 0.55), (0.40, 0.025, 1.4),
                                              (0.43, 0.012, 0.5), (0.37, 0.012, 0.6), (0.95, 0.03, 1.3)), spec=0.5)
    tarn = blotches(S, S, rng, base=5, threshold=0.6, softness=0.15)
    img = lerp(img, img * np.array([0.55, 0.62, 0.48]), tarn[..., None] * 0.5)
    return np.clip(img, 0, 1)


@tex('pole_wood')
def pole_wood(seed=261):
    """The coat stand's turned mahogany post."""
    rng = np.random.default_rng(seed)
    img = pole_tex([0.34, 0.16, 0.08], rng, ((0.04, 0.03, 1.35), (0.08, 0.012, 0.55), (0.62, 0.03, 1.3),
                                              (0.66, 0.012, 0.55), (0.93, 0.04, 1.3)), spec=0.3)
    return np.clip(img, 0, 1)


@tex('coat_wool')
def coat_wool(seed=262):
    """A long dark overcoat hanging from its collar loop, wrapped once round
    the coat (u), collar at the top (v 0) to the hem (v 64). The front (u 16)
    has the lapels, a row of horn buttons and the pocket flaps; the back
    (u 48) has the vent. Charcoal against the warm panelling, its folds catching
    the light so it reads as cloth even in the dark."""
    rng = np.random.default_rng(seed)
    base = np.array([0.19, 0.17, 0.17])
    img = rgb(S, S, base)
    img = shade(img, 0.85 + 0.25 * fbm(S, S, 8, 3, rng))            # wool
    uu = np.arange(S)[None, :] / S
    vv = np.arange(S)[:, None] / S
    wob = fbm(S, S, 2, 2, rng, aspect=0.5)
    # long folds falling from the hook, deeper towards the hem
    folds = np.sin(2 * np.pi * (5 * uu + 0.4 * wob))
    img = shade(img, (1 + (0.2 + 0.35 * vv) * folds)[..., None])
    # collar band and the shadow under it
    img[0:3] *= 0.6
    img[3] *= 1.35
    img[4:6] *= 0.75
    # lapels: two bright edges meeting at the top button, dark gap between
    for y in range(4, 22):
        t = (y - 4) / 17
        for side in (-1, 1):
            x = int(round(16 + side * (8 - 7.5 * t)))
            img[y, x] = np.clip(img[y, x] * 1.6, 0, 1)
            x2 = x - side
            img[y, x2] = img[y, x2] * 0.55
        lo, hi = int(round(16 - (8 - 7.5 * t))) + 1, int(round(16 + (8 - 7.5 * t)))
        if hi > lo:
            img[y, lo:hi] = img[y, lo:hi] * 0.5 + np.array([0.10, 0.09, 0.08]) * 0.5   # the dark inside
    # closure line down the front and its buttons
    img[22:62, 16] *= 0.5
    img[22:62, 17] *= 1.25
    for y in (24, 33, 42, 51):
        b = disc(S, S, y, 14, 1.3)[..., None]
        img = lerp(img, np.array([0.42, 0.34, 0.24]), b)
        img[y - 1, 14] = np.array([0.58, 0.48, 0.34])
    # pocket flaps
    for x0 in (4, 22):
        img[40, x0:x0 + 7] = img[40, x0:x0 + 7] * 1.45
        img[41:43, x0:x0 + 7] *= 0.55
    # back vent
    img[46:62, 48] *= 0.45
    img[46:62, 49] *= 1.3
    # hem: a turned edge and the shadow below it
    img[60] *= 1.35
    img[61:] *= 0.55
    dust = blotches(S, S, rng, base=4, threshold=0.7, softness=0.15)
    img = lerp(img, img * np.array([1.25, 1.2, 1.1]), dust[..., None] * 0.5)
    return np.clip(img, 0, 1)


@tex('felt_hat')
def felt_hat(seed=263):
    """A bowler: black-brown felt, a grosgrain band round the foot of the
    crown (v 46..58), the curl of the brim at the bottom."""
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.27, 0.20, 0.14])
    img = shade(img, 0.85 + 0.3 * fbm(S, S, 6, 3, rng))
    v = np.arange(S) / S
    img = shade(img, (1.25 - 0.5 * v)[:, None, None])
    img[46:58] = img[46:58] * 0.55
    img[46] = img[46] * 2.2
    img[57] = img[57] * 1.6
    img[60:] = img[60:] * 1.5
    return np.clip(img, 0, 1)


@tex('lampshade')
def lampshade(seed=264):
    """Pleated silk shade, yellowed and lit from inside: pleats round it (u),
    a braided trim at the top and a fringe of tassels along the bottom."""
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.80, 0.66, 0.42])
    img = shade(img, 0.88 + 0.2 * fbm(S, S, 4, 3, rng, aspect=0.4))
    u = np.arange(S)
    pleat = 0.82 + 0.3 * (0.5 + 0.5 * np.cos(2 * np.pi * u / 4))
    img = shade(img, pleat[None, :, None])
    v = np.arange(S) / S
    img = shade(img, (0.85 + 0.35 * v)[:, None, None])            # brighter towards the bulb
    trim = np.array([0.52, 0.36, 0.16])
    img[0:3] = trim[None, None, :] * np.array([1.2, 0.8, 1.1])[:, None, None]
    img[50:53] = trim[None, None, :] * np.array([1.2, 0.75, 1.0])[:, None, None]
    for x in range(S):                                            # tassels
        L = 8 + (x * 7 % 5)
        img[53:53 + L, x] = trim * (0.6 if x % 2 else 1.05)
    img[53 + 11:, 1::2] = img[53 + 11:, 1::2] * 0.6
    stain = blotches(S, S, rng, base=3, threshold=0.66, softness=0.12)
    img = lerp(img, img * np.array([0.75, 0.62, 0.42]), stain[..., None] * 0.6)
    return np.clip(img, 0, 1)


def _shelf_bands():
    """Rows of the shelf-contents panel (z 0..1.10 mapped to v 0..64): for
    each shelf the row its items stand on and the row of the board above."""
    row = lambda z: int(round((1.10 - z) / 1.10 * 64))
    return [(row(0.73), 0), (row(0.33), row(0.70)), (64, row(0.30))]


def _shelf_back(rng):
    img = wood_v([0.13, 0.085, 0.05], rng, 0.3)
    img = shade(img, 0.55)
    for floor, ceil in _shelf_bands():                       # shadow under each board
        for k in range(6):
            img[ceil + k] *= 0.45 + 0.09 * k
    return img


@tex('shelf_pantry')
def shelf_pantry(seed=270):
    """Pantry shelving seen from the front: preserving jars, stoneware crocks,
    tins and bottles on two shelves, a sack and a basket on the floor."""
    rng = np.random.default_rng(seed)
    img = _shelf_back(rng)
    bands = _shelf_bands()

    def jar(x, base, w, h, fill):
        glass = np.array([0.20, 0.26, 0.20])
        rect(img, base - h, x, base, x + w, glass)
        rect(img, base - h + 3, x + 1, base, x + w - 1, fill)
        vline(img, x + 1, base - h + 2, base - 1, [0.55, 0.62, 0.55], 0.7)        # glint
        rect(img, base - h - 2, x, base - h, x + w, [0.62, 0.58, 0.48])            # muslin cover
        hline(img, base - h, x, x + w, [0.30, 0.20, 0.10])                        # string
        img[base - 1, x:x + w] *= 0.6

    def crock(x, base, w, h):
        top = np.array([0.66, 0.60, 0.46]); bot = np.array([0.36, 0.22, 0.12])
        for k in range(h):
            c = top if k < h * 0.45 else bot
            inset = 1 if k in (0, h - 1) else 0
            img[base - h + k, x + inset:x + w - inset] = c * (0.8 + 0.3 * (1 - abs(k / h - 0.4)))
        vline(img, x + 1, base - h + 1, base - 1, [0.85, 0.80, 0.66], 0.6)
        img[base - h, x + 1:x + w - 1] *= 0.5

    def tin(x, base, w, h):
        body = np.array([0.30, 0.30, 0.32]) * (0.8 + 0.4 * rng.random())
        rect(img, base - h, x, base, x + w, body)
        rect(img, base - h + 2, x, base - 2, x + w, [[0.50, 0.14, 0.10], [0.16, 0.26, 0.40], [0.56, 0.46, 0.18]][int(rng.integers(0, 3))])
        vline(img, x + 1, base - h, base, [0.62, 0.62, 0.64], 0.6)

    def bottle(x, base, h, col):
        rect(img, base - h + 4, x, base, x + 3, col)
        rect(img, base - h, x + 1, base - h + 4, x + 2, col * 0.8)
        vline(img, x, base - h + 5, base - 1, col * 2.2, 0.5)
        rect(img, base - h + 7, x, base - h + 10, x + 3, [0.70, 0.64, 0.50], 0.8)   # label

    fills = [np.array(c) for c in ([0.42, 0.10, 0.08], [0.46, 0.30, 0.06], [0.22, 0.26, 0.08], [0.30, 0.08, 0.16], [0.50, 0.38, 0.20])]
    for floor, ceil in bands[:2]:
        x = 2
        while x < S - 4:
            k = rng.random()
            room = floor - ceil - 3
            if k < 0.42:
                w = int(rng.integers(6, 9)); h = min(room, int(rng.integers(9, 14)))
                if x + w > S - 2: break
                jar(x, floor, w, h, fills[int(rng.integers(0, len(fills)))])
            elif k < 0.62:
                w = int(rng.integers(7, 10)); h = min(room, int(rng.integers(8, 12)))
                if x + w > S - 2: break
                crock(x, floor, w, h)
            elif k < 0.8:
                w = 5; h = min(room, int(rng.integers(7, 10)))
                if x + w > S - 2: break
                tin(x, floor, w, h)
            else:
                w = 3; bottle(x, floor, min(room, int(rng.integers(13, 17))), np.array([0.10, 0.20, 0.12]) * (0.8 + 0.5 * rng.random()))
            x += w + int(rng.integers(1, 4))
    floor, ceil = bands[2]
    # a hessian sack slumped on the floor and a wicker basket
    sack = ellipse(S, S, floor - 6, 16, 8, 12)
    img = lerp(img, np.array([0.46, 0.38, 0.24]) * (0.85 + 0.25 * fbm(S, S, 8, 2, rng))[..., None], sack)
    for y in range(floor - 10, floor):
        for x in range(36, 58):
            img[y, x] = np.array([0.40, 0.28, 0.14]) * (0.75 + 0.35 * ((x + 2 * y) % 4 < 2))
    hline(img, floor - 10, 36, 58, [0.52, 0.38, 0.20])
    img = shade(img, 0.9 + 0.15 * fbm(S, S, 6, 3, rng))
    return np.clip(img, 0, 1)


@tex('shelf_linen')
def shelf_linen(seed=271):
    """Linen press shelving: stacks of folded sheets, pillow cases and
    ticking, the odd stain; a wicker laundry basket on the floor."""
    rng = np.random.default_rng(seed)
    img = _shelf_back(rng)
    bands = _shelf_bands()
    cols = [np.array(c) for c in ([0.74, 0.72, 0.66], [0.70, 0.68, 0.62], [0.62, 0.60, 0.54], [0.56, 0.58, 0.62], [0.66, 0.56, 0.52])]
    for floor, ceil in bands:
        if floor == 64:
            continue
        x = 2
        while x < S - 8:
            w = int(rng.integers(11, 16))
            if x + w > S - 1: break
            y = floor
            top = ceil + int(rng.integers(3, 7))
            while y - 3 > top:
                c = cols[int(rng.integers(0, len(cols)))] * (0.85 + 0.25 * rng.random())
                t = int(rng.integers(2, 4))
                off = int(rng.integers(-1, 2))
                rect(img, y - t, x + off, y, x + w + off, c)
                hline(img, y - t, x + off, x + w + off, c * 1.18)                       # fold edge
                hline(img, y - 1, x + off, x + w + off, c * 0.62)
                if np.array_equal(c, cols[3]) or rng.random() < 0.15:                   # ticking stripes
                    for sx in range(x + off + 1, x + w + off, 3):
                        vline(img, sx, y - t, y, [0.30, 0.32, 0.42], 0.6)
                y -= t
            img[ceil + 6:floor, x - 1] *= 0.5
            x += w + int(rng.integers(2, 4))
    floor, ceil = bands[2]
    for y in range(floor - 13, floor):
        for x in range(8, 40):
            img[y, x] = np.array([0.42, 0.30, 0.15]) * (0.7 + 0.4 * ((x + 2 * y) % 4 < 2))
    rect(img, floor - 16, 11, floor - 13, 37, [0.72, 0.70, 0.64])                      # sheets heaped in it
    hline(img, floor - 13, 8, 40, [0.55, 0.40, 0.22])
    stain = blotches(S, S, rng, base=4, threshold=0.70, softness=0.08)
    img = lerp(img, img * np.array([0.78, 0.66, 0.46]), stain * 0.6)
    return np.clip(img, 0, 1)


@tex('dress_jersey')
def dress_jersey(seed=272):
    """A tailor's dummy's cover: tan jersey over the padding, dark seams down
    the front (u 16), the princess seams either side and the back (u 48), a
    tape round the waist; rubbed pale where it has been handled."""
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.44, 0.37, 0.27])
    img = shade(img, 0.85 + 0.25 * fbm(S, S, 6, 3, rng, aspect=0.5))
    for x in (16, 48):
        vline(img, x, 0, S, [0.20, 0.15, 0.10])
    for x in (9, 23, 41, 55):
        vline(img, x, 6, S, [0.30, 0.24, 0.17])
    rect(img, 38, 0, 41, S, [0.20, 0.17, 0.13])                     # waist tape
    hline(img, 38, 0, S, [0.30, 0.25, 0.18])
    rub = blotches(S, S, rng, base=4, threshold=0.64, softness=0.12)
    img = lerp(img, img * np.array([1.25, 1.2, 1.1]), rub * 0.5)
    stain = blotches(S, S, rng, base=3, threshold=0.70, softness=0.08)
    img = lerp(img, img * np.array([0.62, 0.50, 0.38]), stain * 0.7)
    return np.clip(img, 0, 1)


@tex('boiler_plate')
def boiler_plate(seed=273):
    """Riveted boiler shell plates: soot-black iron, lap seams (a dark edge
    and a row of rivet heads) round it every half tile and along it at u 0,
    rust weeping down from the seams and blooming over the plates."""
    rng = np.random.default_rng(seed)
    img = rgb(S, S, [0.12, 0.11, 0.10])
    img = shade(img, 0.8 + 0.4 * fbm(S, S, 5, 4, rng))
    rust = np.zeros((S, S))
    for y in (2, 34):
        hline(img, y + 2, 0, S, [0.04, 0.04, 0.04])
        for x in range(2, S, 5):
            img = lerp(img, np.array([0.26, 0.24, 0.22]), disc(S, S, y, x, 0.9))
            if rng.random() < 0.55:
                L = int(rng.integers(4, 20))
                seg = rust[y + 2:y + 2 + L, x]
                rust[y + 2:y + 2 + L, x] = np.linspace(1, 0.2, len(seg))
    vline(img, 3, 0, S, [0.04, 0.04, 0.04])
    for y in range(4, S, 5):
        img = lerp(img, np.array([0.26, 0.24, 0.22]), disc(S, S, y, 1, 0.9))
    img = lerp(img, np.array([0.40, 0.17, 0.07]), np.clip(rust, 0, 1) * 0.8)
    blot = blotches(S, S, rng, base=5, threshold=0.58, softness=0.14)
    img = lerp(img, np.array([0.33, 0.15, 0.07]) * (0.8 + 0.4 * fbm(S, S, 10, 2, rng))[..., None], blot * 0.7)
    return np.clip(img, 0, 1)
