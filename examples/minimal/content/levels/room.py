# SPDX-License-Identifier: MIT
"""The example game's one level: a room, a closet behind a door, a key."""
from mapkit import Plan

NAME = 'room'
FLOOR = 'The room'

ROOMS = {
    'a': dict(name='Room', wall='plaster', mat=0),
    'b': dict(name='Closet', wall='plaster', mat=0),
}
MATERIALS = [('boards', 'ceiling')]

P = Plan(6, 4)
P.room('a', 0, 0, 3, 3).room('b', 4, 1, 5, 2)
P.door(4, 1, 'W')                       # the closet door, in the west edge of cell (4, 1)
MAP = P.render()

EDGES = {(4, 1, 'W'): dict(name='closet')}

START = (1.5, 1.5, 'E')
AMBIENT_LIGHT = 5                       # a floor under the lamps' light, 0..31
LIGHTS = [(2.0, 2.0, 22, 5.0), (5.0, 2.0, 24, 2.5, 'candle')]       # (x, y, brightness, radius[, mode[, group]])
THINGS = [dict(type='key', x=5.3, y=1.6, param=1, event='found', name='key')]
TRIGGERS = [(4, 1, 5, 2, 'closet')]

EVENTS = {
    'start': [('wait', 60), ('objective', 'Find the key.'), ('msg', 'A door. Press A to open it.', 240)],
    'closet': [('msg', 'Something glints on the floor.', 180)],
    'found': [('sound', 'chime', 200), ('objective', 'You have the key.'), ('msg', 'That is all there is to this game.', 300),
              ('wait', 120), ('door', 'closet', 'close')],
}
