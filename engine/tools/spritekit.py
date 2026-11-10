# SPDX-License-Identifier: MIT
"""Supersampled sprite drawing toolkit. Draw at SS x resolution with
shaded primitives, then downsample to a binary-alpha sprite."""
import numpy as np
from PIL import Image, ImageDraw
from noise import fbm, value_noise

SS = 4


class Canvas:
    def __init__(self, w, h, seed=0):
        self.w, self.h = w, h
        self.W, self.H = w * SS, h * SS
        self.rgb = np.zeros((self.H, self.W, 3))
        self.a = np.zeros((self.H, self.W))
        self.em = np.zeros((self.H, self.W))     # emissive mask
        self.rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:self.H, 0:self.W]
        self.yy = yy / SS
        self.xx = xx / SS

    # -- masks --------------------------------------------------------
    def mask_poly(self, pts):
        im = Image.new('L', (self.W, self.H), 0)
        ImageDraw.Draw(im).polygon([(x * SS, y * SS) for x, y in pts], fill=255)
        return np.asarray(im, dtype=float) / 255

    def mask_ellipse(self, cx, cy, rx, ry):
        im = Image.new('L', (self.W, self.H), 0)
        ImageDraw.Draw(im).ellipse([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], fill=255)
        return np.asarray(im, dtype=float) / 255

    def mask_line(self, pts, width):
        im = Image.new('L', (self.W, self.H), 0)
        d = ImageDraw.Draw(im)
        sp = [(x * SS, y * SS) for x, y in pts]
        d.line(sp, fill=255, width=max(1, int(round(width * SS))), joint='curve')
        r = width * SS / 2
        for (x, y) in sp:
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        return np.asarray(im, dtype=float) / 255

    def mask_tapered(self, pts, widths):
        """Polyline with per-point widths (limb)."""
        m = np.zeros((self.H, self.W))
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            w0, w1 = widths[i], widths[i + 1]
            dx, dy = x1 - x0, y1 - y0
            L = max(1e-6, np.hypot(dx, dy))
            nx, ny = -dy / L, dx / L
            poly = [(x0 + nx * w0 / 2, y0 + ny * w0 / 2), (x1 + nx * w1 / 2, y1 + ny * w1 / 2),
                    (x1 - nx * w1 / 2, y1 - ny * w1 / 2), (x0 - nx * w0 / 2, y0 - ny * w0 / 2)]
            m = np.maximum(m, self.mask_poly(poly))
            m = np.maximum(m, self.mask_ellipse(x1, y1, w1 / 2, w1 / 2))
        m = np.maximum(m, self.mask_ellipse(pts[0][0], pts[0][1], widths[0] / 2, widths[0] / 2))
        return m

    # -- painting ------------------------------------------------------
    def paint(self, mask, color, shade=None, alpha=1.0, emissive=False):
        """color: rgb tuple or (H,W,3) array; shade: (H,W) multiplier."""
        c = np.broadcast_to(np.asarray(color, dtype=float), (self.H, self.W, 3)) if np.ndim(color) == 1 else color
        if shade is not None:
            c = c * shade[..., None]
        m = mask * alpha
        self.rgb = self.rgb * (1 - m[..., None]) + c * m[..., None]
        self.a = np.maximum(self.a, mask * (1.0 if alpha >= 1 else alpha))
        if emissive:
            self.em = np.maximum(self.em, mask)
        else:
            self.em = self.em * (1 - mask)

    def darken(self, mask, amount):
        self.rgb *= (1 - mask * amount)[..., None]

    def lighten(self, mask, color, amount):
        self.rgb = self.rgb * (1 - mask[..., None] * amount) + np.asarray(color) * (mask[..., None] * amount)

    # -- shading helpers -----------------------------------------------
    def grad_x(self, x0, x1, v0, v1):
        t = np.clip((self.xx - x0) / max(1e-6, x1 - x0), 0, 1)
        return v0 + (v1 - v0) * t

    def grad_y(self, y0, y1, v0, v1):
        t = np.clip((self.yy - y0) / max(1e-6, y1 - y0), 0, 1)
        return v0 + (v1 - v0) * t

    def radial(self, cx, cy, r, v0, v1):
        d = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2) / r
        return v0 + (v1 - v0) * np.clip(d, 0, 1)

    def tex(self, base=8, octaves=4, lo=0.8, hi=1.15, aspect=1.0):
        n = fbm(self.H, self.W, base, octaves, self.rng, wrap=False, aspect=aspect)
        return lo + (hi - lo) * n

    # -- output --------------------------------------------------------
    def result(self, edge_dark=0.35, threshold=0.45):
        """Downsample to (h,w,3) rgb, (h,w) bool mask, (h,w) bool emissive."""
        A = self.a.reshape(self.h, SS, self.w, SS)
        RGB = (self.rgb * self.a[..., None]).reshape(self.h, SS, self.w, SS, 3)
        EM = self.em.reshape(self.h, SS, self.w, SS)
        asum = A.sum((1, 3))
        rgb = RGB.sum((1, 3)) / np.maximum(asum[..., None], 1e-6)
        alpha = asum / (SS * SS)
        mask = alpha > threshold
        em = (EM.mean((1, 3)) > 0.5) & mask
        # darken silhouette edges for readability
        if edge_dark:
            m = mask.astype(float)
            nb = np.zeros_like(m)
            nb[1:] += m[:-1]; nb[:-1] += m[1:]; nb[:, 1:] += m[:, :-1]; nb[:, :-1] += m[:, 1:]
            edge = mask & (nb < 4)
            rgb[edge & ~em] *= (1 - edge_dark)
        return np.clip(rgb, 0, 1), mask, em


def preview(frames, path, scale=3, bg=(40, 40, 50)):
    """frames: list of (rgb, mask, em)."""
    ws = sum(f[0].shape[1] for f in frames) + 4 * len(frames)
    hs = max(f[0].shape[0] for f in frames)
    sheet = Image.new('RGB', (ws, hs), bg)
    x = 0
    for rgb, mask, em in frames:
        im = Image.fromarray((rgb * 255).astype(np.uint8))
        mk = Image.fromarray((mask * 255).astype(np.uint8))
        sheet.paste(im, (x, hs - rgb.shape[0]), mk)
        x += rgb.shape[1] + 4
    sheet = sheet.resize((ws * scale, hs * scale), Image.NEAREST)
    sheet.save(path)
