# SPDX-License-Identifier: MIT
"""Chapter I: the ground floor of Hollowmere House.

The way through: a music box plays under the floor, and following it leads to
the cellar door in the kitchen (locked; its hook on the key board is empty).
Trying it, a door creaks open down the corridor: the library, where the
housekeeper's ledger says she shut the key in the hall clock. Reading it, the
stopped clock strikes. With the key the lamps die and the Sister walks the
corridor between you and the kitchen, until a telephone rings in the study and
draws her off. Off the path: Thomas's letter in the study, the butler's advice
in his pantry, a place laid for Thomas at the dining table."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engine', 'tools'))   # mapkit
from mapkit import Plan, on_n, on_s, on_w, on_e, at

NAME = "The House"
FLOOR = "GROUND FLOOR"           # the map screen's heading
AMBIENCE = 'amb_ward'
MONSTER_MODE = 0
START = (6.5, 10.35, 'N')

MATERIALS = [('floor_parquet', 'ceil_ornate'),      # reception rooms
             ('floor_boards', 'ceil_plaster'),      # corridor, library, study
             ('floor_tiles_bw', 'ceil_plaster'),    # kitchen, pantries
             ('floor_flagstone', 'ceil_beams')]     # hall

ROOMS = {
    'L': dict(name='Library', wall='library_shelves', mat=1),
    'S': dict(name='Study', wall='paper_study', mat=1),
    'K': dict(name='Kitchen', wall='tile_kitchen', mat=2),
    'P': dict(name='Larder', wall='larder', mat=2),
    'B': dict(name="Butler's pantry", wall='plaster', mat=2),
    'C': dict(name='Corridor', wall='paper_stripe', mat=1),
    'R': dict(name='Drawing room', wall='paper_green', mat=0),
    'H': dict(name='Hall', wall='panel_oak', mat=3),
    'G': dict(name='Dining room', wall='paper_red', mat=0),
}

P = Plan(14, 11)
P.room('L', 0, 0, 3, 3).room('S', 4, 0, 6, 3).room('K', 7, 0, 11, 3)
P.room('P', 12, 0, 13, 1).room('B', 12, 2, 13, 3)
P.room('C', 0, 4, 13, 4)
P.room('R', 0, 5, 3, 9).room('H', 4, 5, 8, 10).room('G', 9, 5, 13, 9)
# doors
P.door(1, 4, 'N').door(5, 4, 'N').door(9, 4, 'N')
P.door(12, 3, 'W').door(12, 2, 'N')
P.door(2, 5, 'N').door(6, 5, 'N', 'a').door(11, 5, 'N')
P.door(4, 7, 'W', 'D').door(9, 6, 'W', 'D')
P.door(6, 10, 'S', 'x')          # front door
P.door(8, 0, 'N', 'x')           # cellar door
# windows
for (x, y, o) in [(0, 1, 'W'), (0, 2, 'W'), (0, 5, 'W'), (0, 9, 'W'), (13, 6, 'E'), (13, 8, 'E'),
                  (5, 10, 'S'), (7, 10, 'S'), (11, 0, 'N'), (2, 9, 'S'), (11, 9, 'S')]:
    P.door(x, y, o, 'w')
MAP = P.render()

EDGES = {
    (6, 11, 'N'): dict(sign="The front door. It slammed behind me and the lock won't turn. Not that I'd leave without him."),
    (8, 0, 'N'): dict(exit='cellar', leaf='leaf_cellar'),
    (9, 6, 'W'): dict(name='dining'),
    (1, 4, 'N'): dict(name='library'),
}

DECOR = [
    (5, 4, 'S', 'sconce'), (9, 4, 'S', 'sconce'), (1, 4, 'S', 'landscape'), (10, 4, 'S', 'portrait'),
    (3, 4, 'N', 'sconce'), (13, 4, 'E', 'mirror'),
    (4, 8, 'W', 'portrait'), (8, 5, 'N', 'sconce'), (4, 9, 'W', 'landscape'),
    (1, 5, 'N', 'portrait'), (3, 9, 'E', 'mirror'),
    (10, 5, 'N', 'portrait'), (12, 5, 'N', 'portrait'), (9, 9, 'W', 'landscape'),
    (6, 0, 'E', 'clock'), (4, 3, 'S', 'portrait'),
]

PROPS = [
    # hall: the staircase rises along the east wall to a broken landing
    at('stairs_grand', 8.35, 9.95, 'N', inter=('sign', "Nine steps, then nothing: the upper flight has fallen in. There's no way up from here."), front=-0.3),
    at('stairs_balustrade', 8.35 - 77 / 256, 9.95 + 38 / 256, 'N'),   # see furniture.BAL_ORIGIN
    at('hide_spot', 8.12, 7.8, 'W', inter=('locker',), front=0.42),   # the cupboard under the stairs
    on_w('clock', 4.0, 6.5, inter=('event', 'clock'), front=0.35),   # the housekeeper hid the cellar key in it
    at('coatstand', 4.42, 10.5, 160),             # the coat turned to the room
    at('rug', 6.2, 7.6, 'S'),
    at('lamp_standard', 4.4, 5.4),
    at('chest', 7.3, 10.78, 'N'),                # under the window
    # drawing room
    on_w('fireplace', 0.0, 7.5, inter=('hearth', 12), tex='fire_cold'),
    at('sofa', 1.75, 7.5, 'W'),
    at('armchair', 1.0, 6.2, 176),
    at('armchair', 1.0, 8.8, 80),
    at('table_round', 1.75, 6.35),               # lamp table at the end of the sofa
    on_e('piano', 4.0, 9.1),
    # dining room
    at('table_dining', 11.5, 7.5, 'S', inter=('sign', "A place card at the head of the table, in a careful hand: MR. T. MARSH."), front=0.5),
    at('chair', 10.85, 6.95, 'S'), at('chair', 11.5, 6.9, 'S'), at('chair', 12.15, 6.95, 'S'),
    at('chair', 10.85, 8.05, 'N'), at('chair', 11.5, 8.1, 'N'), at('chair', 12.2, 8.15, 132),
    on_e('fireplace', 14.0, 7.5, inter=('hearth', 13), tex='fire_cold'),
    on_n('dresser', 9.6, 5.0),
    # library
    at('table_round', 2.0, 1.8), at('armchair', 1.33, 1.33, 224), at('armchair', 2.6, 2.4, 96),
    at('lamp_standard', 3.55, 0.45),
    # study
    on_n('desk', 5.4, 0.0), at('chair', 5.4, 0.62, 'N'),
    on_w('fireplace', 4.0, 2.2, inter=('hearth', 14), tex='fire_cold'),
    on_e('bookcase', 7.0, 1.6),
    at('armchair', 6.4, 3.3, 112),
    # kitchen
    on_n('stove', 10.2, 0.0),
    at('table_kitchen', 9.5, 2.1, 'S'),
    at('chair', 9.0, 1.55, 'S'), at('chair', 10.0, 2.65, 'N'),
    on_e('sink', 12.0, 0.6),
    on_s('shelves', 7.7, 4.0),
    at('barrel', 10.9, 3.5),
    # larder and butler's pantry
    at('crates', 12.4, 0.5), at('barrel', 13.5, 1.5),
    on_e('shelves', 14.0, 2.6), at('chest', 13.4, 3.55, 'N'),
    # corridor
    at('covered_tall', 0.45, 4.5), at('chair', 7.4, 4.82, 'N'), at('covered', 13.4, 4.5),
]

THINGS = [
    dict(x=2.0, y=1.8, z=0.48, type='note', param=0, event='ledger'),   # library table: housekeeper's ledger
    dict(x=5.25, y=0.2, z=0.52, type='note', param=1),         # study desk: Thomas's letter
    dict(x=1.75, y=6.35, z=0.48, type='candles'),
    dict(x=11.5, y=7.5, z=0.5, type='candles'),
    dict(x=13.80, y=2.6, z=0.73, type='battery'),               # butler's pantry shelf
    dict(x=9.4, y=2.0, z=0.5, type='battery'),
    dict(x=5.68, y=0.2, z=0.52, type='telephone'),              # study desk (its line is cut)
    dict(x=0.45, y=9.55, type='battery'),                      # drawing room, in the corner under the window
    dict(x=13.4, y=3.55, z=0.32, type='note', param=2),        # butler's chest: the wardrobe note
    # (new things go last: a save keeps what was taken by its place in this list)
    dict(x=9.95, y=0.27, z=0.58, type='matches'),               # on the kitchen stove
]

LIGHTS = [
    (6.5, 7.5, 17, 4.2, 'steady', 1),            # hall lamp (dies when she comes)
    (5.5, 4.8, 15, 3.0, 'flicker', 1), (9.5, 4.8, 15, 3.0, 'steady', 1),     # corridor sconces
    (3.5, 4.2, 14, 2.8, 'steady', 1), (8.5, 5.2, 14, 2.8, 'steady', 1),
    (1.75, 6.35, 13, 2.8, 'candle'),             # drawing-room candles
    (0.6, 7.5, 25, 5.0, 'fire', 12),             # the drawing-room fire (the hearths' lights: dark until lit, game/src/hearth.c)
    (11.5, 7.5, 14, 3.2, 'candle'),              # dining candles
    (13.4, 7.5, 25, 5.0, 'fire', 13),            # the dining-room fire
    (10.2, 0.6, 12, 2.6, 'candle'),              # stove embers
    (0.3, 1.5, 8, 2.8), (13.7, 7.0, 8, 3.0), (6.5, 10.6, 9, 3.0), (0.3, 7.0, 8, 3.0),   # moonlight
    (3.55, 0.5, 14, 3.0, 'steady', 1),           # library reading lamp
    (4.4, 5.4, 14, 3.0, 'steady', 1),            # hall standard lamp
    (4.6, 2.2, 24, 4.5, 'fire', 14),             # the study fire
]

TRIGGERS = [
    (0, 5, 3, 9, 'drawing'),
    (9, 5, 13, 9, 'dining'),
    (0, 0, 3, 3, 'library'),
    (7, 0, 11, 3, 'kitchen'),
    (4, 0, 6, 3, 'study'),
]
PATROL = [(1, 4), (6, 4), (12, 4), (6, 7), (3, 7), (12, 9), (9, 3), (2, 3), (5, 2), (12, 3)]

EVENTS = {
    'start': [
        ('wait', 30),
        ('sound', 'slam', 220),
        ('shake', 2, 16),
        ('wait', 50),
        ('msg', "The door slammed behind me. Somewhere under the floor, a music box is playing.", 260),
        ('start', 'ambient'),
        ('start', 'musicbox'),
        ('wait', 220),
        ('if_flag', 'l1_tried', 'done'),
        ('if_flag', 'l1_ledger', 'done'),
        ('objective', "Follow the music."),
        ('label', 'done'),
    ],
    'ambient': [
        ('label', 'top'),
        ('wait', 360),
        ('jrand', 128, 'b'),
        ('sound3d', 'creak', 8, 2, 150),
        ('jmp', 'top'),
        ('label', 'b'),
        ('sound3d', 'wind_gust', 0, 7, 140),
        ('jmp', 'top'),
    ],
    # the lullaby from behind the cellar door, over and over, until the lamps die
    'musicbox': [
        ('label', 'top'),
        ('if_flag', 'l1_key', 'stop'),
        ('sound3d', 'musicbox_phrase', 8, 0, 240),
        ('wait', 960),
        ('jmp', 'top'),
        ('label', 'stop'),
    ],
    'drawing': [
        ('wait', 40),
        ('sound3d', 'piano', 3, 9, 170),
        ('fear', 25),
        ('wait', 90),
        ('msg', "A single piano key, somewhere in the dark. Nobody is at the piano.", 220),
    ],
    'dining': [
        ('wait', 20),
        ('msg', "The table is laid for twelve. The food has been rotting for months.", 220),
    ],
    'library': [
        ('wait', 60),
        ('sound3d', 'bang', 0, 0, 160),
        ('msg', "A book fell from a high shelf.", 160),
    ],
    'study': [
        ('wait', 30),
        ('if_flag', 'l1_rang', 'rang'),
        ('msg', "A telephone on the desk. I lift the receiver: nothing. The cord has been cut.", 240),
        ('end',),
        ('label', 'rang'),
        ('msg', "The telephone. Its cord is cut clean through. It was ringing.", 220),
    ],
    'kitchen': [
        ('wait', 30),
        ('if_flag', 'l1_key', 'done'),
        ('msg', "The music is loudest here. It's coming up through the cellar door.", 220),
        ('label', 'done'),
    ],
    'cellar': [
        ('ifnot_key', 1, 'locked'),
        ('freeze', 1),
        ('sound', 'door_open', 220),
        ('wait', 40),
        ('endlevel', 1),
        ('end',),
        ('label', 'locked'),
        ('msg', "Locked, and the music is right behind it. On the key board, the hook marked CELLAR is empty.", 260),
        ('if_flag', 'l1_tried', 'done'),
        ('flag', 'l1_tried'),
        ('if_flag', 'l1_ledger', 'done'),
        ('objective', "Find the cellar key."),
        ('start', 'lure'),
        ('label', 'done'),
    ],
    # a door creaks open at the far end of the corridor: the library
    'lure': [
        ('wait', 300),
        ('if_flag', 'l1_ledger', 'done'),
        ('door', 'library', 'open'),
        ('sound3d', 'creak', 1, 4, 230),
        ('wait', 50),
        ('msg', "Down the corridor, a door has just creaked open on its own.", 220),
        ('wait', 2400),
        ('if_flag', 'l1_ledger', 'done'),
        ('objective', "Find the cellar key. The housekeeper kept the books."),
        ('label', 'done'),
    ],
    'ledger': [
        ('wait', 10),
        ('flag', 'l1_ledger'),
        ('if_flag', 'l1_key', 'done'),
        ('objective', "The cellar key: inside the clock in the hall."),
        ('wait', 120),
        ('sound3d', 'clock_strike', 4, 6, 255),
        ('wait', 150),
        ('sound3d', 'clock_strike', 4, 6, 255),
        ('wait', 90),
        ('msg', "Out in the hall, the stopped clock just struck two.", 200),
        ('label', 'done'),
    ],
    'clock': [
        ('if_flag', 'l1_key', 'empty'),
        ('ifnot_flag', 'l1_ledger', 'shut'),
        ('sound', 'locker_open', 200),
        ('wait', 30),
        ('msg', "The case swings open. Hooked over the still pendulum: a key on a tag marked CELLAR.", 260),
        ('give', 'key', 1),
        ('sound', 'pickup', 160),
        ('start', 'got_key'),
        ('end',),
        ('label', 'shut'),
        ('msg', "A tall clock, stopped at ten past two. The case is shut.", 200),
        ('end',),
        ('label', 'empty'),
        ('msg', "Still ten past two.", 140),
    ],
    'got_key': [
        ('flag', 'l1_key'),
        ('objective', "Back to the cellar door, in the kitchen."),
        ('wait', 200),
        ('light', 1, 120),
        ('sound', 'fuse', 170),
        ('wait', 8),
        ('light', 1, 0),
        ('sound3d', 'distant_scream', 1, 4, 200),
        ('fear', 60),
        ('wait', 40),
        ('msg', "Every lamp in the house just died. Something is walking in the corridor, with a lantern.", 280),
        ('creature', 'mode', 1),
        ('creature', 'spawn', 13, 4),
        ('creature', 'goto', 6, 4),
        ('checkpoint',),
        ('wait', 290),
        ('msg', "She'll see my flashlight. Turn it off, and get out of sight.", 220),
        ('wait', 330),
        ('start', 'phone'),
    ],
    # a telephone rings in the study (its line is cut) and draws her off the corridor
    'phone': [
        ('flag', 'l1_rang'),
        ('sound3d', 'phone_ring', 5, 1, 255),
        ('creature', 'hear', 5, 1),
        ('wait', 70),
        ('msg', "A telephone is ringing in the study. Her light swings toward it.", 220),
        ('wait', 290),
        ('sound3d', 'phone_ring', 5, 1, 255),
        ('creature', 'hear', 5, 1),
        ('wait', 360),
        ('sound3d', 'phone_ring', 5, 1, 255),
        ('creature', 'hear', 5, 1),
        ('wait', 360),
        ('sound3d', 'phone_ring', 5, 1, 230),
    ],
}
