# SPDX-License-Identifier: MIT
"""Palette, quantization and light colormaps.

Palette layout (game palette):
  0        pure black
  1..239   k-means colours trained on all textures/sprites at all light levels
  240..247 emissive colours (fullbright: colormap maps them to themselves)
  248..255 UI colours (fullbright)
"""
import numpy as np

NUM_LIGHT = 32
EMISSIVE_BASE = 240
UI_BASE = 248


def srgb_to_lab(c):
    c = np.asarray(c, dtype=np.float64)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ M.T
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], -1)


def q5(c):
    """Quantize float RGB to GBA 5-bit levels, returned as float."""
    return np.round(np.clip(c, 0, 1) * 31) / 31


def light_scale(l):
    """Display-space brightness multiplier for light level l (0..31)."""
    t = l / (NUM_LIGHT - 1)
    return (t ** 1.2) * 1.06


def light_tint(l):
    t = l / (NUM_LIGHT - 1)
    t = t * t * (3 - 2 * t)
    cold = np.array([0.78, 0.90, 1.18])
    warm = np.array([1.06, 1.00, 0.86])
    return cold + (warm - cold) * t


def lit(color, l, tint_override=None):
    tint = light_tint(l) if tint_override is None else tint_override(l)
    return np.clip(color * light_scale(l) * tint, 0, 1)


def kmeans(points, weights, k, iters=30, seed=0, init=None):
    rng = np.random.default_rng(seed)
    if init is None:
        idx = rng.choice(len(points), k, replace=False, p=weights / weights.sum())
        cent = points[idx].copy()
    else:
        cent = init.copy()
    for it in range(iters):
        # assign in batches
        lab = np.empty(len(points), dtype=np.int32)
        for s in range(0, len(points), 20000):
            p = points[s:s + 20000]
            d = ((p[:, None, :] - cent[None, :, :]) ** 2).sum(-1)
            lab[s:s + 20000] = d.argmin(1)
        new = np.zeros_like(cent)
        wsum = np.bincount(lab, weights, minlength=k)
        for ch in range(points.shape[1]):
            new[:, ch] = np.bincount(lab, weights * points[:, ch], minlength=k)
        empty = wsum == 0
        new[~empty] /= wsum[~empty, None]
        # reseed empty clusters at random points
        if empty.any():
            new[empty] = points[rng.choice(len(points), empty.sum())]
        shift = np.abs(new - cent).max()
        cent = new
        if shift < 1e-4:
            break
    return cent


def build_palette(images, emissive, ui, seed=0, samples_per_level=1500):
    """images: list of (H,W,3) float arrays (with optional alpha masks as None).
    Returns pal (256,3) float in 5-bit steps."""
    rng = np.random.default_rng(seed)
    allpix = np.concatenate([im.reshape(-1, 3) for im in images], 0)
    pts = []
    for l in range(1, NUM_LIGHT):
        sel = allpix[rng.integers(0, len(allpix), samples_per_level)]
        pts.append(lit(sel, l))
    pts = np.concatenate(pts, 0)
    # extra weight to full brightness so textures look right up close
    full = allpix[rng.integers(0, len(allpix), samples_per_level * 4)]
    pts = np.concatenate([pts, full], 0)
    lab = srgb_to_lab(pts)
    w = np.ones(len(lab))
    ncol = EMISSIVE_BASE - 1
    cent = kmeans(lab, w, ncol, iters=25, seed=seed)
    # convert centroids back to rgb: pick mean rgb of members
    assign = np.empty(len(lab), dtype=np.int32)
    for s in range(0, len(lab), 20000):
        d = ((lab[s:s + 20000, None, :] - cent[None]) ** 2).sum(-1)
        assign[s:s + 20000] = d.argmin(1)
    rgbc = np.zeros((ncol, 3))
    cnt = np.bincount(assign, minlength=ncol)
    for ch in range(3):
        rgbc[:, ch] = np.bincount(assign, pts[:, ch], minlength=ncol) / np.maximum(cnt, 1)
    rgbc = q5(rgbc)
    # dedupe: replace duplicates with evenly spaced greys/darks
    uniq = []
    seen = set()
    for c in rgbc:
        key = tuple((c * 31).astype(int))
        if key in seen or key == (0, 0, 0):
            continue
        seen.add(key); uniq.append(c)
    if len(uniq) < ncol:
        # fill free slots greedily with the sample colours worst served so far
        cand = np.unique(np.round(np.clip(pts, 0, 1) * 31).astype(int), axis=0)
        cand = [c for c in cand if tuple(c) not in seen and tuple(c) != (0, 0, 0)]
        cand = np.array(cand, dtype=float) / 31
        clab = srgb_to_lab(cand)
        cur = srgb_to_lab(np.array(uniq))
        dmin = ((clab[:, None, :] - cur[None]) ** 2).sum(-1).min(1)
        while len(uniq) < ncol and len(cand):
            i = int(dmin.argmax())
            uniq.append(cand[i])
            d = ((clab - clab[i]) ** 2).sum(-1)
            dmin = np.minimum(dmin, d)
            dmin[i] = -1
    pal = np.zeros((256, 3))
    pal[1:EMISSIVE_BASE] = np.array(uniq[:ncol])
    # sort the k-means block by luminance (nicer for debugging)
    blk = pal[1:EMISSIVE_BASE]
    order = np.argsort(srgb_to_lab(blk)[:, 0], kind='stable')
    pal[1:EMISSIVE_BASE] = blk[order]
    for i, c in enumerate(emissive[:8]):
        pal[EMISSIVE_BASE + i] = q5(np.array(c))
    for i, c in enumerate(ui[:8]):
        pal[UI_BASE + i] = q5(np.array(c))
    return pal


def nearest(colors, pal, lo=0, hi=EMISSIVE_BASE):
    """Index of nearest palette entry (in [lo,hi)) for each colour, Lab metric."""
    shape = colors.shape[:-1]
    c = srgb_to_lab(colors.reshape(-1, 3))
    p = srgb_to_lab(pal[lo:hi])
    out = np.empty(len(c), dtype=np.int32)
    for s in range(0, len(c), 8192):
        d = ((c[s:s + 8192, None, :] - p[None]) ** 2).sum(-1)
        out[s:s + 8192] = d.argmin(1) + lo
    return out.reshape(shape)


def quantize(img, pal, mask=None, emissive=None, dither=0.0, seed=0):
    """img (H,W,3) -> indices. mask: bool (H,W) opaque. Transparent -> 0.
    Opaque pixels never map to 0 (reserved for transparency in sprites).
    emissive: bool mask of pixels to map into the emissive range."""
    h, w, _ = img.shape
    src = img.copy()
    if dither > 0:
        bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.47
        src = src + dither * bayer[np.arange(h)[:, None] % 4, np.arange(w)[None, :] % 4][..., None] / 31
    idx = nearest(np.clip(src, 0, 1), pal, 1, EMISSIVE_BASE)
    if emissive is not None and emissive.any():
        e = nearest(img[emissive], pal, EMISSIVE_BASE, UI_BASE)
        idx[emissive] = e
    if mask is not None:
        idx[~mask] = 0
    return idx.astype(np.uint8)


def build_colormap(pal, tint=None):
    """Returns (NUM_LIGHT, 256) uint8. Emissive and UI entries are fixed."""
    cm = np.zeros((NUM_LIGHT, 256), dtype=np.uint8)
    for l in range(NUM_LIGHT):
        target = lit(pal, l, tint)
        if l == 0:
            cm[l, :] = 0
        else:
            cm[l, :] = nearest(target, pal, 0, EMISSIVE_BASE)
        cm[l, 0] = 0
        cm[l, EMISSIVE_BASE:] = np.arange(EMISSIVE_BASE, 256)
    return cm


def to_bgr555(pal):
    p = np.round(np.clip(pal, 0, 1) * 31).astype(np.uint16)
    return p[:, 0] | (p[:, 1] << 5) | (p[:, 2] << 10)
