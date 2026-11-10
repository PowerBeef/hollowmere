# SPDX-License-Identifier: MIT
"""Tileable procedural noise and drawing helpers for texture generation.
All images are float numpy arrays in [0,1], shape (H, W) or (H, W, 3)."""
import numpy as np


def _smooth(t):
    return t * t * (3 - 2 * t)


def value_noise(h, w, cy, cx, rng, wrap=True):
    """Periodic value noise with cy x cx lattice cells."""
    g = rng.random((cy + 1, cx + 1))
    if wrap:
        g[-1, :] = g[0, :]
        g[:, -1] = g[:, 0]
    ys = np.linspace(0, cy, h, endpoint=False)
    xs = np.linspace(0, cx, w, endpoint=False)
    y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int)
    fy = _smooth(ys - y0)[:, None]; fx = _smooth(xs - x0)[None, :]
    a = g[y0][:, x0]; b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]; d = g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(h, w, base, octaves, rng, persistence=0.5, wrap=True, aspect=1.0):
    total = np.zeros((h, w)); amp = 1.0; norm = 0.0
    cells = base
    for _ in range(octaves):
        cy = max(1, int(round(cells * aspect)))
        total += amp * value_noise(h, w, cy, cells, rng, wrap)
        norm += amp; amp *= persistence; cells *= 2
    return total / norm


def blotches(h, w, rng, base=4, octaves=4, threshold=0.6, softness=0.08):
    n = fbm(h, w, base, octaves, rng)
    return np.clip((n - threshold) / softness, 0, 1)


def lerp(a, b, t):
    t = np.asarray(t)
    if t.ndim == 2 and np.ndim(a) == 3 or (np.ndim(b) == 3 and t.ndim == 2):
        t = t[..., None]
    return a + (b - a) * t


def rgb(h, w, color):
    img = np.zeros((h, w, 3)); img[:] = color; return img


def shade(img, f):
    f = np.asarray(f)
    if f.ndim == 2:
        f = f[..., None]
    return np.clip(img * f, 0, 1)


def drip_streaks(h, w, rng, count=6, length=(10, 40), from_top=True, width=(1, 3)):
    """Vertical grime/water streaks. Returns mask [0,1]."""
    m = np.zeros((h, w))
    for _ in range(count):
        x = rng.integers(0, w)
        L = rng.integers(*length)
        wd = rng.integers(*width)
        y0 = 0 if from_top else rng.integers(0, h - L)
        strength = rng.uniform(0.4, 1.0)
        for y in range(y0, min(h, y0 + L)):
            t = (y - y0) / L
            x += rng.choice([-1, 0, 0, 0, 1]) if rng.random() < 0.15 else 0
            for dx in range(wd):
                m[y, (x + dx) % w] = max(m[y, (x + dx) % w], strength * (1 - t) ** 0.7)
    return m


def cracks(h, w, rng, count=3, length=(8, 30), wrap=True):
    m = np.zeros((h, w))
    for _ in range(count):
        y, x = rng.integers(0, h), rng.integers(0, w)
        ang = rng.uniform(0, 2 * np.pi)
        for _ in range(rng.integers(*length)):
            ang += rng.normal(0, 0.5)
            y += np.sin(ang); x += np.cos(ang)
            yi, xi = int(round(y)) % h, int(round(x)) % w
            m[yi, xi] = 1
            if rng.random() < 0.08:  # branch
                by, bx, ba = y, x, ang + rng.choice([-1, 1]) * 1.0
                for _ in range(rng.integers(3, 8)):
                    ba += rng.normal(0, 0.4)
                    by += np.sin(ba); bx += np.cos(ba)
                    m[int(round(by)) % h, int(round(bx)) % w] = 0.8
    return m


def rect(img, y0, x0, y1, x1, color, alpha=1.0):
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - alpha) + np.array(color) * alpha


def hline(img, y, x0, x1, color, alpha=1.0):
    rect(img, y, x0, y + 1, x1, color, alpha)


def vline(img, x, y0, y1, color, alpha=1.0):
    rect(img, y0, x, y1, x + 1, color, alpha)


def bevel(img, y0, x0, y1, x1, light=1.15, dark=0.7):
    """Raised panel edges: top/left lighter, bottom/right darker."""
    img[y0, x0:x1] *= light
    img[y0:y1, x0] *= light
    img[y1 - 1, x0:x1] *= dark
    img[y0:y1, x1 - 1] *= dark
    np.clip(img, 0, 1, out=img)


def vertical_gradient(h, w, top, bottom):
    t = np.linspace(0, 1, h)[:, None]
    return np.repeat(top + (bottom - top) * t, w, axis=1)


def disc(h, w, cy, cx, r, soft=1.0):
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    return np.clip((r - d) / soft + 0.5, 0, 1)


def ellipse(h, w, cy, cx, ry, rx, soft=1.0):
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2)
    return np.clip((1 - d) * min(ry, rx) / soft + 0.5, 0, 1)
