# SPDX-License-Identifier: MIT
"""Chapter IV: the attic chapel. Take the Night Sister's lantern.

The way through: a woman's voice counting, from the far end of the attic;
follow it along the passage to the chapel, where she kneels at the altar with
her back to you. Off the path: the box room's rocking horse, the maid's
scratched boards, the vestry."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engine', 'tools'))   # mapkit
from mapkit import Plan, on_n, on_s, on_w, on_e, at

NAME = "The Chapel"
FLOOR = "ATTIC"           # the map screen's heading
AMBIENCE = 'amb_chapel'
MONSTER_MODE = 3
START = (0.9, 5.4, 'N')

MATERIALS = [('floor_boards', 'ceil_beams'),        # attic rooms
             ('floor_boards', 'ceil_wood'),         # servants' rooms
             ('floor_carpet', 'ceil_beams'),        # chapel aisle
             ('floor_stone', 'ceil_stone')]         # vestry

ROOMS = {
    'S': dict(name='Box room', wall='attic_boards', mat=0),
    'R': dict(name="Maid's room", wall='paper_floral', mat=1),
    'W': dict(name='Cistern room', wall='attic_boards', mat=0),
    'A': dict(name='Stairhead', wall='attic_boards', mat=0),
    'C': dict(name='Attic passage', wall='attic_boards', mat=0),
    'Q': dict(name="Cook's room", wall='paper_stripe', mat=1),
    'L': dict(name='Linen press', wall='plaster', mat=1),
    'V': dict(name='Vestry', wall='chapel_wall', mat=3),
    'P': dict(name='Chapel', wall='chapel_wall', mat=2),
}

P = Plan(13, 9)
P.room('S', 0, 0, 4, 3).room('R', 5, 0, 6, 3).room('W', 7, 0, 8, 3)
P.room('A', 0, 4, 1, 5).room('C', 2, 4, 8, 4)
P.room('Q', 2, 5, 4, 8)
P.room('L', 5, 5, 6, 8).room('V', 7, 5, 8, 8)
P.room('P', 9, 0, 12, 8)
P.room('A', 0, 6, 1, 8)
P.door(1, 4, 'N').door(2, 4, 'W', 'a').door(5, 4, 'N').door(8, 4, 'N')
P.door(3, 5, 'N').door(5, 5, 'N').door(8, 5, 'N')
P.door(9, 4, 'W', 'D').door(9, 7, 'W')
P.door(0, 8, 'S', 'x')                     # the stair back down
for (x, y, o) in [(12, 2, 'E'), (12, 5, 'E'), (10, 8, 'S'), (11, 8, 'S'), (2, 0, 'N'), (6, 0, 'N')]:
    P.door(x, y, o, 'w')
MAP = P.render()

EDGES = {
    (0, 9, 'N'): dict(sign="The attic stair, back down to the wards. Not without Thomas.", leaf='leaf_panel'),
}

DECOR = [
    (10, 0, 'N', 'crucifix'), (12, 0, 'N', 'sconce'), (9, 0, 'N', 'sconce'),
    (9, 3, 'W', 'portrait'), (12, 4, 'E', 'crucifix'), (12, 7, 'E', 'portrait'),
    (8, 8, 'S', 'crucifix'), (3, 8, 'S', 'mirror'), (5, 1, 'W', 'crucifix'),
]

PROPS = [
    # chapel: altar at the north end, pews in two rows either side of the aisle
    at('altar', 10.8, 0.45, 'S'),
    # (a cross aisle between the second and third rows, in front of the side doors)
    at('pew', 9.75, 2.45, 'N'), at('pew', 12.2, 2.45, 'N'),
    at('pew', 9.75, 3.6, 'N'), at('pew', 12.2, 3.6, 'N'),
    at('pew', 9.75, 5.3, 'N'), at('pew', 12.2, 5.3, 'N'),
    at('candlestand', 9.85, 0.5), at('candlestand', 11.75, 0.5),
    # vestry
    on_w('wardrobe', 7.0, 6.9, inter=('locker',)), at('chest', 8.5, 8.78, 'N'), at('dressform', 7.4, 5.6),   # (the wardrobe clear of the door from the passage)
    # box room
    at('crates', 0.6, 0.6), at('covered', 2.0, 1.0), at('covered_tall', 3.6, 0.6), at('chest', 1.2, 2.6, 'E'),
    at('dressform', 4.45, 3.45), on_e('wardrobe', 5.0, 2.2, inter=('locker',)), at('crate', 2.6, 3.4),   # (the form in the corner, not before the wardrobe)
    # maid's room
    on_n('bed_iron', 5.5, 0.0), on_e('washstand', 7.0, 2.6),
    # cistern room
    at('cistern', 8.7, 1.75, 'W'), at('barrel', 7.5, 0.6), at('barrel', 8.4, 0.6), at('crates', 7.4, 3.3),
    # cook's room
    on_s('bed_iron', 2.6, 9.0),
    on_e('wardrobe', 5.0, 7.0, inter=('locker',)), at('chair', 4.3, 5.6, 'S'),
    # linen press
    on_e('shelves_linen', 7.0, 6.6), at('chest', 5.6, 8.4, 'N'),
    # stairhead
    at('crate', 0.5, 6.6), at('covered', 1.3, 8.4),
]

THINGS = [
    dict(x=5.9, y=2.2, type='note', param=11),                    # scratched into the maid's room boards
    dict(x=1.0, y=7.5, type='battery'),
    dict(x=8.4, y=3.4, type='battery'),
    dict(x=10.4, y=0.5, z=0.62, type='candles'), dict(x=11.4, y=0.5, z=0.62, type='candles'),
    dict(x=8.5, y=8.75, z=0.32, type='candles'),
    dict(x=9.85, y=0.5, z=1.03, type='candles'), dict(x=11.75, y=0.5, z=1.03, type='candles'),
    dict(x=3.0, y=2.0, type='rockinghorse'), dict(x=0.8, y=1.6, type='doll'),
]

LIGHTS = [
    (10.4, 0.6, 16, 3.6, 'candle'), (11.4, 0.6, 16, 3.6, 'candle'),
    (9.5, 0.3, 13, 2.8, 'candle'), (12.5, 0.3, 13, 2.8, 'candle'),
    (8.5, 8.5, 11, 2.6, 'candle'),
    (12.7, 2.5, 8, 3.0), (12.7, 5.5, 8, 3.0), (10.5, 8.7, 8, 3.0), (2.5, 0.3, 7, 2.6), (6.5, 0.3, 7, 2.6),  # moonlight
]

TRIGGERS = [
    (9, 3, 12, 8, 'nave'),
    (5, 0, 6, 3, 'maid'),
    (0, 0, 4, 3, 'boxroom'),
    (7, 5, 8, 8, 'vestry'),
]
PATROL = [(10, 2), (11, 6), (5, 4), (2, 2), (3, 7), (8, 7), (1, 5), (7, 1)]

EVENTS = {
    'start': [
        ('creature', 'pray', 10, 1),
        ('creature', 'face', 192),
        ('wait', 40),
        ('msg', "The attic. Somewhere ahead, under the eaves, a woman's voice is counting.", 250),
        ('start', 'counting'),
        ('wait', 220),
        ('if_flag', 'l4_nave', 'done'),
        ('objective', "Follow the counting voice."),
        ('music', 'lullaby', 80),
        ('wait', 3000),
        ('if_flag', 'l4_nave', 'done'),
        ('objective', "Follow the counting east, to the chapel."),
        ('label', 'done'),
    ],
    # after a checkpoint is restored the scripts carry on by themselves, but
    # she has to be put back at her prayers
    'resume': [
        ('creature', 'pray', 10, 1),
        ('creature', 'face', 192),
    ],
    # her murmured counting, from the altar
    'counting': [
        ('label', 'top'),
        ('if_flag', 'l4_nave', 'stop'),
        ('sound3d', 'whisper', 10, 1, 255),
        ('wait', 330),
        ('jmp', 'top'),
        ('label', 'stop'),
    ],
    'boxroom': [
        ('wait', 40),
        ('sound3d', 'creak', 3, 2, 200),
        ('wait', 45),
        ('sound3d', 'creak', 3, 2, 170),
        ('wait', 45),
        ('sound3d', 'creak', 3, 2, 140),
        ('wait', 20),
        ('msg', "In the corner, the rocking horse is rocking. There's nobody on it.", 230),
        ('fear', 30),
    ],
    'vestry': [
        ('wait', 30),
        ('msg', "Her room, if she has one: a folded habit, a hairbrush, a bowl of black water that doesn't ripple.", 280),
    ],
    'lantern': [
        ('freeze', 1),
        ('hudoff', 1),
        ('musicstop',),
        ('stopsounds',),
        ('sound', 'cscream', 255, -5),
        ('shake', 3, 90),
        ('flash', 40),
        ('wait', 50),
        ('creature', 'despawn'),
        ('sound', 'bell', 255),
        ('fade', 16, 3),
        ('wait', 80),
        ('ending',),
    ],
    'maid': [
        ('wait', 30),
        ('msg', "Something has been scratched into the boards here, over and over.", 220),
    ],
    'nave': [
        ('flag', 'l4_nave'),
        ('msg', "There. Kneeling at the altar, the lantern on the step beside her. Her back is to me.", 270),
        ('objective', "Take her lantern. Quietly, and with no light."),
        ('checkpoint',),
    ],
}
