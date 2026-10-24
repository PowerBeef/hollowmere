"""Full-screen 240x160 images with their own 248-colour palettes:
title (the island at night), jumpscare (the Night Sister's face), dawn."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from noise import fbm, value_noise
import palette as P

W, H = 240, 160
FONT_SERIF = '/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrebonum-bold.otf'
IMAGES = {}


def image(name):
    def deco(fn):
        IMAGES[name] = fn
        return fn
    return deco


def grid():
    yy, xx = np.mgrid[0:H, 0:W]
    return yy.astype(float), xx.astype(float)


def poly_mask(pts, w=W, h=H, ss=4):
    im = Image.new('L', (w * ss, h * ss), 0)
    ImageDraw.Draw(im).polygon([(x * ss, y * ss) for x, y in pts], fill=255)
    im = im.resize((w, h), Image.LANCZOS)
    return np.asarray(im, float) / 255


def ellipse_mask(cx, cy, rx, ry, w=W, h=H, ss=4):
    im = Image.new('L', (w * ss, h * ss), 0)
    ImageDraw.Draw(im).ellipse([(cx - rx) * ss, (cy - ry) * ss, (cx + rx) * ss, (cy + ry) * ss], fill=255)
    im = im.resize((w, h), Image.LANCZOS)
    return np.asarray(im, float) / 255


def blend(img, mask, color):
    m = mask[..., None]
    return img * (1 - m) + np.asarray(color) * m


def building_silhouette(rng, base_y, x0, x1, scale=1.0):
    """Returns (mask, window list) for the sanatorium on the island."""
    pts = []
    sil = np.zeros((H, W))
    wins = []
    # main long block
    roof = base_y - 22 * scale
    sil = np.maximum(sil, poly_mask([(x0, base_y), (x0, roof), (x1, roof), (x1, base_y)]))
    # gabled wings
    for cx in (x0 + 10 * scale, x1 - 10 * scale):
        sil = np.maximum(sil, poly_mask([(cx - 11 * scale, roof), (cx, roof - 9 * scale), (cx + 11 * scale, roof)]))
    # chapel bell tower + spire (right side)
    tx = x1 - 26 * scale
    sil = np.maximum(sil, poly_mask([(tx - 5 * scale, roof), (tx - 5 * scale, roof - 22 * scale),
                                     (tx + 5 * scale, roof - 22 * scale), (tx + 5 * scale, roof)]))
    sil = np.maximum(sil, poly_mask([(tx - 6.5 * scale, roof - 22 * scale), (tx, roof - 40 * scale), (tx + 6.5 * scale, roof - 22 * scale)]))
    # central entrance block with cupola
    mx = (x0 + x1) / 2 - 6 * scale
    sil = np.maximum(sil, poly_mask([(mx - 9 * scale, roof), (mx - 9 * scale, roof - 8 * scale), (mx + 9 * scale, roof - 8 * scale), (mx + 9 * scale, roof)]))
    sil = np.maximum(sil, ellipse_mask(mx, roof - 8 * scale, 4 * scale, 4 * scale))
    # chimneys
    for cx in (x0 + 24 * scale, x0 + 48 * scale, x1 - 44 * scale):
        sil = np.maximum(sil, poly_mask([(cx, roof), (cx, roof - 7 * scale), (cx + 3 * scale, roof - 7 * scale), (cx + 3 * scale, roof)]))
    # windows grid
    for row in range(2):
        wy = roof + (5 + row * 9) * scale
        x = x0 + 4 * scale
        while x < x1 - 6 * scale:
            wins.append((x, wy, 3 * scale, 4 * scale))
            x += 7 * scale
    return sil, wins, tx, roof


@image('title')
def title():
    rng = np.random.default_rng(1958)
    yy, xx = grid()
    img = np.zeros((H, W, 3))
    special = np.zeros((H, W), bool)
    horizon = 96
    # sky
    t = yy / horizon
    sky = np.stack([0.02 + 0.07 * t, 0.03 + 0.09 * t, 0.06 + 0.12 * t], -1)
    clouds = fbm(H, W, 4, 5, rng, wrap=False, aspect=0.5)
    moon_x, moon_y = 196, 64
    md = np.hypot(xx - moon_x, (yy - moon_y) * 1.1)
    halo = np.exp(-md / 22) * 0.35 + np.exp(-md / 60) * 0.12
    sky = sky + halo[..., None] * np.array([0.55, 0.6, 0.65])
    cl = np.clip((clouds - 0.45) * 2.2, 0, 1)
    cloud_col = np.array([0.10, 0.11, 0.13]) + halo[..., None] * np.array([0.7, 0.7, 0.72])
    sky = sky * (1 - cl[..., None] * 0.85) + cloud_col * cl[..., None] * 0.85
    img[:] = sky
    moon = ellipse_mask(moon_x, moon_y, 9, 9)
    crater = fbm(H, W, 16, 3, rng, wrap=False)
    img = blend(img, moon * (1 - cl * 0.7), np.array([0.85, 0.86, 0.80])[None, None, :] * (0.85 + 0.15 * crater)[..., None])
    # distant shore and island
    shore = np.zeros(W)
    for x in range(W):
        shore[x] = horizon - 3 - 2.5 * np.sin(x * 0.05) - 1.5 * np.sin(x * 0.13 + 1)
    far = (yy > shore[None, :]) & (yy <= horizon)
    img[far] = np.array([0.03, 0.04, 0.05])
    # island mound
    island = poly_mask([(40, horizon + 1), (56, horizon - 8), (100, horizon - 12), (175, horizon - 11),
                        (205, horizon - 6), (222, horizon + 1)])
    img = blend(img, island, np.array([0.015, 0.02, 0.02]))
    sil, wins, tx, roof = building_silhouette(rng, horizon - 9, 70, 190, 1.0)
    img = blend(img, sil, np.array([0.012, 0.014, 0.018]))
    # moon rim light on the right edges of the building
    rim = np.clip(sil - np.roll(sil, -1, axis=1), 0, 1) * 0.6
    img = blend(img, rim, np.array([0.10, 0.11, 0.13]))
    # windows: all dark but one
    lit_idx = 9
    for i, (wx, wy, ww, wh) in enumerate(wins):
        m = poly_mask([(wx, wy), (wx + ww, wy), (wx + ww, wy + wh), (wx, wy + wh)])
        if i == lit_idx:
            special |= m > 0.5
            glow = np.exp(-np.hypot(xx - wx - ww / 2, yy - wy - wh / 2) / 6)
            img = img + glow[..., None] * np.array([0.25, 0.16, 0.05])
            lit_pos = (wx + ww / 2, wy + wh / 2)
        else:
            img = blend(img, m * 0.6, np.array([0.035, 0.04, 0.05]))
    # pines on the island
    for k in range(26):
        px = rng.uniform(42, 222)
        if 66 < px < 194 and rng.random() < 0.7:
            continue
        h = rng.uniform(10, 22)
        base = horizon - 2 - (6 if 55 < px < 205 else 0)
        pts = [(px - h * 0.28, base), (px, base - h), (px + h * 0.28, base)]
        img = blend(img, poly_mask(pts), np.array([0.01, 0.015, 0.015]))
    # lake with reflections
    water = yy > horizon
    depth = np.clip((yy - horizon) / (H - horizon), 0, 1)
    ripple = fbm(H, W, 8, 4, rng, wrap=False, aspect=0.12)
    lake = np.stack([0.015 + 0.03 * depth, 0.02 + 0.035 * depth, 0.03 + 0.05 * depth], -1)
    img[water] = lake[water]
    # mirrored sky/building reflection, broken by ripples
    for y in range(horizon + 1, H):
        src = 2 * horizon - y
        if src < 0:
            continue
        off = (ripple[y] - 0.5) * 10 * (y - horizon) / 30
        xs = np.clip((np.arange(W) + off).astype(int), 0, W - 1)
        refl = img[src, xs] * (0.45 - 0.25 * (y - horizon) / (H - horizon))
        img[y] = img[y] * 0.6 + refl
    # moon glitter column
    glit = np.exp(-np.abs(xx - moon_x) / 8) * (ripple > 0.55) * water * (1 - depth * 0.5)
    img = img + glit[..., None] * np.array([0.35, 0.37, 0.38])
    # lit window reflection streak
    lx, ly = lit_pos
    ry = 2 * horizon - ly
    streak = np.exp(-np.abs(xx - lx) / 1.5) * np.exp(-np.abs(yy - ry) / 14) * water * (ripple > 0.45)
    img = img + streak[..., None] * np.array([0.35, 0.22, 0.06])
    # vignette
    v = 1 - 0.55 * (((xx - 120) / 140) ** 2 + ((yy - 80) / 110) ** 2)
    img = img * np.clip(v, 0.25, 1)[..., None]
    # title text
    font = ImageFont.truetype(FONT_SERIF, 30)
    tim = Image.new('L', (W * 4, 60 * 4), 0)
    d = ImageDraw.Draw(tim)
    f4 = ImageFont.truetype(FONT_SERIF, 23 * 4)
    text = "HOLLOWMERE"
    tw = d.textlength(text, font=f4)
    # letter spacing
    x = (W * 4 - tw * 1.10) / 2
    for ch in text:
        d.text((x, 6 * 4), ch, font=f4, fill=255)
        x += d.textlength(ch, font=f4) * 1.10
    tm = np.asarray(tim.resize((W, 60), Image.LANCZOS), float) / 255
    # drips
    drip = np.zeros_like(tm)
    for col in range(W):
        if tm[26:32, col].max() > 0.6 and rng.random() < 0.18:
            L = int(rng.uniform(3, 12))
            for k in range(L):
                if 30 + k < 60:
                    drip[30 + k, col] = max(drip[30 + k, col], 1 - k / L)
    tm = np.clip(tm + drip * 0.8, 0, 1)
    grit = fbm(60, W, 24, 3, rng, wrap=False)
    tm = tm * (0.75 + 0.35 * grit)
    tmask = np.zeros((H, W)); tmask[4:64] = tm
    shadow = np.zeros((H, W)); shadow[6:66, 2:] = tm[:, :-2]
    img = img * (1 - shadow[..., None] * 0.8)
    tcol = np.array([0.78, 0.74, 0.66]) * (0.8 + 0.2 * (1 - (yy - 4) / 60))[..., None]
    img = img * (1 - tmask[..., None]) + tcol * tmask[..., None]
    # subtitle line
    sub = Image.new('L', (W * 4, 14 * 4), 0)
    f2 = ImageFont.truetype(FONT_SERIF, 8 * 4)
    s = "~ a house on the lake ~"
    sw = ImageDraw.Draw(sub).textlength(s, font=f2)
    ImageDraw.Draw(sub).text(((W * 4 - sw) / 2, 0), s, font=f2, fill=255)
    sm = np.asarray(sub.resize((W, 14), Image.LANCZOS), float) / 255
    smask = np.zeros((H, W)); smask[40:54] = sm
    img = blend(img, smask * 0.8, np.array([0.45, 0.10, 0.08]))
    return np.clip(img, 0, 1), special


@image('jumpscare')
def jumpscare():
    """The Night Sister's face in the flashlight, from the same model as her
    in-game sprites (rendered by game/content/sister/make.py --jumpscare)."""
    import os
    rng = np.random.default_rng(666)
    yy, xx = grid()
    z = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'sister_jumpscare.npz'))
    rgb, a = z['rgb'].astype(float), z['alpha'].astype(float)
    # behind her: black, a faint warm haze from the lantern
    haze = np.exp(-np.hypot(xx - 200, yy - 150) / 90)[..., None] * np.array([0.10, 0.05, 0.02])
    img = haze * (1 - a[..., None]) + rgb * a[..., None]
    # harsh contrast, vignette, grain, red cast at the edges
    img = np.clip((img - 0.03) * 1.12, 0, 1)
    v = np.clip(1.25 - np.hypot((xx - 120) / 150, (yy - 80) / 110), 0, 1)
    img = img * v[..., None]
    img = img + rng.normal(0, 0.025, (H, W, 1))
    img = img + ((1 - v) * 0.15)[..., None] * np.array([0.6, 0.0, 0.0])
    return np.clip(img, 0, 1), None


@image('dawn')
def dawn():
    rng = np.random.default_rng(1959)
    yy, xx = grid()
    horizon = 92
    t = yy / horizon
    sky = np.stack([0.42 - 0.18 * (1 - t) + 0.10 * t, 0.42 - 0.15 * (1 - t), 0.48 - 0.08 * (1 - t)], -1)
    sun = np.exp(-np.hypot(xx - 70, (yy - horizon) * 2) / 50)
    sky = sky + sun[..., None] * np.array([0.35, 0.20, 0.10])
    clouds = fbm(H, W, 4, 5, rng, wrap=False, aspect=0.3)
    cl = np.clip((clouds - 0.5) * 2, 0, 1)
    sky = sky * (1 - cl[..., None] * 0.35) + cl[..., None] * np.array([0.30, 0.28, 0.32]) * 0.35
    img = np.zeros((H, W, 3)); img[:] = sky
    island = poly_mask([(150, horizon + 1), (160, horizon - 5), (200, horizon - 7), (226, horizon - 4), (236, horizon + 1)])
    img = blend(img, island, np.array([0.12, 0.13, 0.15]))
    sil, wins, tx, roof = building_silhouette(rng, horizon - 5, 164, 226, 0.5)
    img = blend(img, sil, np.array([0.13, 0.14, 0.16]))
    wx, wy, ww, wh = wins[5]
    img = blend(img, poly_mask([(wx, wy), (wx + ww, wy), (wx + ww, wy + wh), (wx, wy + wh)]), np.array([0.85, 0.55, 0.20]))
    water = yy > horizon
    ripple = fbm(H, W, 10, 4, rng, wrap=False, aspect=0.1)
    for y in range(horizon + 1, H):
        src = 2 * horizon - y
        off = (ripple[y] - 0.5) * 8
        xs = np.clip((np.arange(W) + off).astype(int), 0, W - 1)
        img[y] = img[max(0, src), xs] * 0.7 + np.array([0.05, 0.06, 0.07])
    # mist
    mist = np.exp(-np.abs(yy - horizon) / 9) * (0.6 + 0.4 * fbm(H, W, 6, 3, rng, wrap=False))
    img = img * (1 - mist[..., None] * 0.5) + mist[..., None] * np.array([0.55, 0.55, 0.58]) * 0.5
    # rowboat in the foreground
    boat = poly_mask([(30, 128), (130, 124), (118, 142), (44, 145)])
    img = blend(img, boat, np.array([0.08, 0.06, 0.05]))
    img = blend(img, poly_mask([(60, 126), (64, 108), (67, 108), (64, 126)]), np.array([0.06, 0.05, 0.04]))
    img = blend(img, poly_mask([(84, 124), (88, 112), (91, 112), (88, 124)]), np.array([0.06, 0.05, 0.04]))
    img = blend(img, poly_mask([(118, 128), (160, 150), (163, 148), (121, 126)]), np.array([0.07, 0.05, 0.04]))
    v = 1 - 0.4 * (((xx - 120) / 150) ** 2 + ((yy - 80) / 110) ** 2)
    img = img * np.clip(v, 0.3, 1)[..., None]
    return np.clip(img, 0, 1), None


def render(fn, game_pal):
    """Quantize an image to its own palette: 0..246 k-means, 247 special, 248..255 UI."""
    img, special = fn()
    rng = np.random.default_rng(0)
    if special is None:
        special = np.zeros((H, W), bool)
    px = img[~special].reshape(-1, 3)
    lab = P.srgb_to_lab(px)
    sel = rng.choice(len(lab), min(len(lab), 20000), replace=False)
    cent = P.kmeans(lab[sel], np.ones(len(sel)), 247, iters=20)
    # back to rgb by averaging members
    d = ((lab[sel][:, None, :] - cent[None]) ** 2).sum(-1).argmin(1)
    rgb = np.zeros((247, 3))
    cnt = np.bincount(d, minlength=247)
    for ch in range(3):
        rgb[:, ch] = np.bincount(d, px[sel][:, ch], minlength=247) / np.maximum(cnt, 1)
    pal = np.zeros((256, 3))
    pal[:247] = P.q5(rgb)
    pal[247] = special_color = np.array([1.0, 0.72, 0.30]) if special.any() else pal[0]
    pal[248:] = game_pal[248:]
    # ordered dither then nearest
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.47
    yy, xx = np.mgrid[0:H, 0:W]
    dimg = np.clip(img + bayer[yy % 4, xx % 4][..., None] / 40, 0, 1)
    idx = P.nearest(dimg, pal, 0, 247)
    idx[special] = 247
    return idx.astype(np.uint8), pal


if __name__ == '__main__':
    import sys
    import pickle
    out = []
    for nm, fn in IMAGES.items():
        img, sp = fn()
        out.append(Image.fromarray((img * 255).astype(np.uint8)))
    sheet = Image.new('RGB', (W * len(out) + 8 * len(out), H))
    for i, im in enumerate(out):
        sheet.paste(im, (i * (W + 8), 0))
    sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(sys.argv[1])
