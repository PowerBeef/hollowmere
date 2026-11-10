# SPDX-License-Identifier: MIT
"""Floor and ceiling textures: TEXTURES maps a name to a function returning a
64 x 64 x 3 array of RGB in 0..1. They tile in both directions."""
import numpy as np

TEXTURES = {}


def boards():
    img = np.zeros((64, 64, 3))
    rng = np.random.default_rng(1)
    for x0 in range(0, 64, 16):                      # four planks
        tone = 0.75 + 0.25 * rng.random()
        img[:, x0:x0 + 16] = np.array([0.36, 0.22, 0.12]) * tone
        img[:, x0] *= 0.5                            # the seam
    img *= (0.9 + 0.1 * rng.random((64, 1, 1)))      # a little grain along the planks
    return np.clip(img, 0, 1)


def ceiling():
    rng = np.random.default_rng(2)
    return np.clip(np.array([0.55, 0.53, 0.48]) * (0.94 + 0.06 * rng.random((64, 64, 1))), 0, 1)


TEXTURES['boards'] = boards
TEXTURES['ceiling'] = ceiling
