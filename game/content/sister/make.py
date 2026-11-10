#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render every frame of the Night Sister to game/assets/sister.npz.

    python3 game/content/sister/make.py [--ss 4] [--only walk,chase,...] [--preview]

Frames (the engine's CRF_* layout follows this order):
  walk   8 views x 8 phases     112 x 224
  chase  8 views x 8 phases     160 x 224
  idle   8 views                112 x 224
  search 8 views                112 x 224
  kneel  8 views                112 x 224
  attack 3 frames, seen from 0.75 tiles away, 160 x 224
Views are 45 degrees apart, clockwise (seen from above) from straight in
front of her. Needs numba."""
import os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import anim
from view import shoot, sheet, TILE, PLANE_H, SPR_H

OUT = os.path.join(HERE, '..', '..', 'assets', 'sister.npz')
WIDE = 160
VIEWS = 8


def frame_list():
    L = []
    for v in range(VIEWS):
        for k in range(8):
            L.append(('walk', v, k))
    for v in range(VIEWS):
        for k in range(8):
            L.append(('chase', v, k))
    for kind in ('idle', 'search', 'kneel'):
        for v in range(VIEWS):
            L.append((kind, v, 0))
    for k in range(3):
        L.append(('attack', 0, k))
    return L


def render_one(kind, v, k, ss):
    view = v * 360.0 / VIEWS
    if kind == 'walk':
        return shoot(anim.walk(k / 8), view, ss=ss)
    if kind == 'chase':
        return shoot(anim.chase(k / 8), view, ss=ss, W=WIDE, plane_w=PLANE_H * WIDE / SPR_H)
    if kind == 'idle':
        return shoot(anim.idle(), view, ss=ss)
    if kind == 'search':
        return shoot(anim.search(), view, ss=ss)
    if kind == 'kneel':
        return shoot(anim.kneel(), view, ss=ss)
    if kind == 'attack':
        return shoot(anim.attack(k), 0.0, dist=0.75 * TILE, ss=ss, W=WIDE, plane_w=PLANE_H * WIDE / SPR_H)


def main():
    a = sys.argv[1:]
    ss = int(a[a.index('--ss') + 1]) if '--ss' in a else 4
    only = a[a.index('--only') + 1].split(',') if '--only' in a else None
    frames = frame_list()
    old = {}
    if only and os.path.exists(OUT):
        z = np.load(OUT, allow_pickle=True)
        for i, n in enumerate(z['names']):
            old[str(n)] = (z['rgb'][i], z['alpha'][i], z['em'][i])
    names, rgbs, alphas, ems = [], [], [], []
    t0 = time.time()
    for n, (kind, v, k) in enumerate(frames):
        name = f'{kind}_{v}_{k}'
        if only and kind not in only and name in old:
            rgb8, a8, e8 = old[name]
        else:
            rgb, al, em = render_one(kind, v, k, ss)
            rgb8 = (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)
            a8 = (np.clip(al, 0, 1) * 255 + 0.5).astype(np.uint8)
            e8 = (np.clip(em, 0, 1) * 255 + 0.5).astype(np.uint8)
            print(f'{n + 1}/{len(frames)} {name} {time.time() - t0:.0f}s', flush=True)
        # pad every frame to the wide size so they stack (w kept in 'widths')
        H, W = a8.shape
        R = np.zeros((SPR_H, WIDE, 3), np.uint8); A = np.zeros((SPR_H, WIDE), np.uint8); E = np.zeros((SPR_H, WIDE), np.uint8)
        R[:, :W] = rgb8; A[:, :W] = a8; E[:, :W] = e8
        names.append(name); rgbs.append(R); alphas.append(A); ems.append(E)
    widths = np.array([WIDE if n.startswith(('chase', 'attack')) else 112 for n in names])
    np.savez_compressed(OUT, names=np.array(names), rgb=np.stack(rgbs), alpha=np.stack(alphas), em=np.stack(ems),
                        widths=widths)
    print('wrote', OUT, f'{time.time() - t0:.0f}s')


if __name__ == '__main__' and '--jumpscare' not in sys.argv:
    main()


JUMP_OUT = os.path.join(HERE, '..', '..', 'assets', 'sister_jumpscare.npz')


def jumpscare_pose():
    from rig import Pose
    from core import HEAD
    kw = dict(
        pelvis=(0.0, 0.16, None), dip=-0.14,
        foot_r=(0.12, 0.30, 0.0), foot_l=(-0.12, -0.15, 0.0),
        lean=30, chest_lean=10, neck_lean=6, head_pitch=-40, head_roll=-13, head_yaw=-6,
        elbow_pole_r=(0.9, -0.2, 0.6), hand_r_up=(0.0, 0.3, 1.0),
        palm_r=(-1.0, 0.2, 0.0), curl_r=(85, 90, 90, 90, 50), lantern_swing=(-12, 6),
        elbow_pole_l=(-0.9, 0.2, 1.0), hand_l_up=(0.3, 1.0, 0.2),
        palm_l=(0.3, -0.6, -1.0), curl_l=(26, 18, 14, 20, 6), spread_l=38,
        jaw=1.25, sway=(0.0, -0.06), seed=7, eyeglow=0.0, light=3.2,
    )
    J, R, S = Pose(hand_r=(0.3, 0.4, 1.2), hand_l=(-0.3, 0.6, 1.5), **kw).build()
    h = J[HEAD]
    # the lantern low at her right (the viewer's left), lighting her from
    # below; her left hand coming at you past her face
    kw['hand_r'] = (h[0] + 0.15, h[1] + 0.06, h[2] - 0.30)
    kw['hand_l'] = (h[0] - 0.24, h[1] + 0.02, h[2] - 0.34)
    return Pose(**kw)


def render_jumpscare(ss=3):
    """Her face filling the screen, lunging into the flashlight."""
    pose = jumpscare_pose()
    J, R, S = pose.build()
    from core import HEAD
    hx, hy, hz = J[HEAD]
    W, H = 240, 160
    # the screen zooms in on it (up to 1.7x): the eye and the mouth near the middle
    pw = 0.43
    ph = pw * H / W
    f = np.array([0.05, 1.0, 0.35]); f /= np.linalg.norm(f)
    fill = np.array([f[0], f[1], f[2], 0.70, 0.03, 0.05])
    rgb, a, em = shoot(pose, 0.0, dist=0.40, W=W, H=H, ss=ss, fill=fill, eye=hz - 0.03,
                       plane_bottom=hz - 0.050 - ph * 0.5, plane_w=pw, plane_h=ph, center=(hx - 0.004, hy))
    np.savez_compressed(JUMP_OUT, rgb=rgb.astype(np.float32), alpha=a.astype(np.float32), em=em.astype(np.float32))
    print('wrote', JUMP_OUT)
    return rgb, a, em


if __name__ == '__main__' and '--jumpscare' in sys.argv:
    render_jumpscare()
