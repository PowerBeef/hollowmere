# SPDX-License-Identifier: MIT
"""Wall textures: 64 wide, 128 tall (one tile wide, two tall; row 0 is the
ceiling line). TEXTURES maps a name to a function returning a 128 x 64 x 3
array of RGB in 0..1.

The level compiler also asks for textures it composes from a wall and an
opening, by name; ensure(name) must add them to TEXTURES:
    dframe:<wall>:<style>:<panel>:<lintel>   the surround of an open doorway
    dclosed:<wall>:<leaf>:<L|R|D>            the door closed in its frame
    archf:<wall>:<panel>:<lintel>            an archway's surround
    window:<wall>   deco:<wall>:<kind>       (not used by this game)
panel is the width of wall left either side of the opening, in texels;
lintel the height of the opening in half texels (the opening spans rows
128 - 2 * lintel to 128)."""
import numpy as np

W, H = 64, 128
TEXTURES = {}


def plaster():
    rng = np.random.default_rng(3)
    img = np.ones((H, W, 3)) * np.array([0.62, 0.60, 0.52]) * (0.92 + 0.08 * rng.random((H, W, 1)))
    img[H - 10:] = np.array([0.24, 0.15, 0.09])      # a skirting board
    img[H - 11] *= 0.6
    return np.clip(img, 0, 1)


TEXTURES['plaster'] = plaster


def frame(wall, panel, lintel):
    """The wall with a cased opening cut into it (the opening is left black:
    the engine draws what is behind it)."""
    img = TEXTURES[wall]().copy()
    top, a, b = H - 2 * lintel, panel, W - panel
    wood = np.array([0.26, 0.15, 0.08])
    img[top - 4:, a - 4:b + 4] = wood
    img[top:, a:b] = 0.02
    return img


def closed(wall, leaf, variant):
    """The same doorway with its door shut: the leaf's texture in the opening."""
    import proptex
    double = variant == 'D'
    panel, lintel = (4, 48) if double else (13, 45)          # levelc.DOOR_GEOM
    img = frame(wall, panel, lintel)
    top, a, b = H - 2 * lintel, panel, W - panel
    lf = proptex.TEXTURES[leaf]()                            # 64 x 64, hinge at u = 0
    ys = np.arange(H - top) * 64 // (H - top)
    xs = np.arange(b - a) * 64 // (b - a)
    if variant == 'R':
        xs = 63 - xs
    img[top:, a:b] = lf[ys][:, xs]
    return img


def ensure(name):
    if name in TEXTURES:
        return
    p = name.split(':')
    if p[0] == 'dframe':
        TEXTURES[name] = lambda: frame(p[1], int(p[3]), int(p[4]))
    elif p[0] == 'archf':
        TEXTURES[name] = lambda: frame(p[1], int(p[2]), int(p[3]))
    elif p[0] == 'dclosed':
        TEXTURES[name] = lambda: closed(p[1], p[2], p[3])
    else:
        raise KeyError(f"this game has no wall texture {name!r}")
