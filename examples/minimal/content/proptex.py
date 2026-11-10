# SPDX-License-Identifier: MIT
"""Textures for 3D models (furniture, door leaves): TEXTURES maps a name to a
function returning a 64 x 64 x 3 array of RGB in 0..1."""
import numpy as np

TEXTURES = {}


def leaf_panel():
    """A door leaf: hinge side at u = 0, handle near u = 63."""
    img = np.ones((64, 64, 3)) * np.array([0.34, 0.20, 0.11])
    for (y0, y1) in ((6, 28), (34, 58)):             # two sunk panels
        img[y0:y1, 8:56] *= 0.8
        img[y0, 8:56] *= 0.6
        img[y0:y1, 8] *= 0.6
    img[30:34, 54:58] = np.array([0.75, 0.62, 0.25])  # the handle
    return np.clip(img, 0, 1)


def wood_dark():
    return np.ones((64, 64, 3)) * np.array([0.20, 0.12, 0.07])


TEXTURES['leaf_panel'] = leaf_panel
TEXTURES['wood_dark'] = wood_dark
