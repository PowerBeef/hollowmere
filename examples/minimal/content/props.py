# SPDX-License-Identifier: MIT
"""Things: the sprites a level places with THINGS. PROPS maps a type name to
    fn          a function returning (rgb h x w x 3 in 0..1, opaque mask h x w, emissive mask h x w)
    ww, wh      its size in the world, in tiles
    zoff        how far its foot is above the floor, in tiles
    solid       the player cannot walk through it
    fullbright  drawn at full light whatever the room's
    glint       it sparkles now and then (the module then needs add_glint)"""
import numpy as np

PROPS = {}


def key():
    h, w = 12, 24
    yy, xx = np.mgrid[0:h, 0:w]
    ring = (np.hypot(xx - 5, yy - 6) < 5) & (np.hypot(xx - 5, yy - 6) > 2.2)
    shaft = (xx >= 9) & (xx < 22) & (abs(yy - 6) < 1.5)
    teeth = ((xx == 17) | (xx == 20)) & (yy >= 6) & (yy < 10)
    mask = ring | shaft | teeth
    rgb = np.ones((h, w, 3)) * np.array([0.85, 0.68, 0.22]) * (1.1 - 0.4 * yy[..., None] / h)
    return np.clip(rgb, 0, 1), mask, np.zeros((h, w), bool)


PROPS['key'] = dict(fn=key, w=24, h=12, ww=0.25, wh=0.125, zoff=0.0, solid=False, fullbright=False, glint=False)
