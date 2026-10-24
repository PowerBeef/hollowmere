"""Cameras and output for the Night Sister renders."""
import math
import time
import numpy as np
from core import render

# the sprite: 112 x 224 texels over 0.685 x 1.37 tiles (1.03 x 2.06 m)
TILE = 1.5
SPR_W, SPR_H = 112, 224
PLANE_H = 1.37 * TILE
PLANE_W = PLANE_H * SPR_W / SPR_H
EYE = 1.0 * TILE


def camera(view_deg, dist, eye=EYE, plane_bottom=0.0, plane_w=PLANE_W, plane_h=PLANE_H, center=(0.0, 0.0)):
    """Camera dist metres from her origin, view_deg clockwise (seen from
    above) from straight in front of her; the image is the sprite rectangle
    standing at her position, facing the camera."""
    th = math.radians(view_deg)
    c = np.array([math.sin(th), math.cos(th), 0.0])          # from her to the camera
    cam = np.array([center[0], center[1], 0.0]) + c * dist + np.array([0, 0, eye])
    right = np.array([-math.cos(th), math.sin(th), 0.0])
    up = np.array([0.0, 0.0, 1.0])
    plane0 = np.array([center[0], center[1], plane_bottom]) - right * plane_w / 2
    return cam, right, up, plane0, plane_w, plane_h


def shoot(pose, view_deg, dist=4.5, W=SPR_W, H=SPR_H, ss=3, fill=None, **camkw):
    J, R, S = pose.build()
    cam, right, up, plane0, pw, ph = camera(view_deg, dist, **camkw)
    if fill is None:
        # cold light from the viewer's side, a little above; ambient; rim
        f = cam - np.array([0, 0, 0.3]) - np.array([0, 0, 1.4])
        f = f / np.linalg.norm(f)
        fill = np.array([f[0], f[1], f[2], 0.30, 0.09, 0.12])
    rgb = np.zeros((H * ss, W * ss, 3))
    a = np.zeros((H * ss, W * ss))
    em = np.zeros((H * ss, W * ss))
    render(W, H, ss, cam, right, up, plane0, pw, ph, J, R, S, fill, rgb, a, em)
    return down(rgb, a, em, ss)


def down(rgb, a, em, ss):
    H, W = a.shape[0] // ss, a.shape[1] // ss
    A = a.reshape(H, ss, W, ss).mean((1, 3))
    C = (rgb * a[..., None]).reshape(H, ss, W, ss, 3).sum((1, 3)) / np.maximum(a.reshape(H, ss, W, ss).sum((1, 3)), 1e-9)[..., None]
    E = em.reshape(H, ss, W, ss).mean((1, 3))
    return C, A, E


def sheet(frames, path, scale=2, bg=(34, 30, 30)):
    from PIL import Image
    ims = []
    for rgb, a, em in frames:
        h, w = a.shape
        im = np.zeros((h, w, 3))
        im[:] = np.array(bg) / 255
        im = im * (1 - a[..., None]) + rgb * a[..., None]
        ims.append((np.clip(im, 0, 1) * 255).astype(np.uint8))
    h = max(i.shape[0] for i in ims)
    W = sum(i.shape[1] + 4 for i in ims)
    out = Image.new('RGB', (W, h), bg)
    x = 0
    for i in ims:
        out.paste(Image.fromarray(i), (x, h - i.shape[0]))
        x += i.shape[1] + 4
    out = out.resize((W * scale, h * scale), Image.NEAREST)
    out.save(path)
