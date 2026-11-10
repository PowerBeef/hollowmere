# SPDX-License-Identifier: MIT
"""3D models: MODELS maps a name to a function returning a meshkit.Mesh, and
build_all() returns them all built. The engine needs two whatever else a
game has: the leaf it hangs in a single door and one half of a double door
(the manifest's DOOR_MODELS; these names are its default)."""
from meshkit import Mesh

MODELS = {}


def door_leaf(name, width, height):
    """Hinge on the model's y axis at x = 0, the leaf along +x. Texture 255
    stands for the door's own leaf texture (leaf= in the level's EDGES)."""
    m = Mesh(name)
    t = 0.02
    m.wall((0, -t), (width, -t), 0, height, 255, (0, -1), u0=64, u1=0, v_top=0, v_bot=64)
    m.wall((width, t), (0, t), 0, height, 255, (0, 1), u0=0, u1=64, v_top=0, v_bot=64)
    m.wall((width, -t), (width, t), 0, height, 'wood_dark', (1, 0), u0=0, u1=4, v_top=0, v_bot=64)
    m.wall((0, t), (0, -t), 0, height, 'wood_dark', (-1, 0), u0=0, u1=4, v_top=0, v_bot=64)
    m.flat([(0, -t), (width, -t), (width, t), (0, t)], height, 'wood_dark', True)
    m.solid = False
    m.boxes = []
    return m


MODELS['leaf_single'] = lambda: door_leaf('leaf_single', 38 / 64, 45 / 32)      # (the opening of levelc.DOOR_GEOM['single'])
MODELS['leaf_half'] = lambda: door_leaf('leaf_half', 28 / 64, 48 / 32)


def build_all():
    out = {}
    for name, fn in MODELS.items():
        out[name] = fn()
        out[name].name = name
    return out
