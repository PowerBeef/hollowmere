# SPDX-License-Identifier: MIT
"""Chapter III: the upper floor, the family bedrooms turned into wards.

The way through: the lift opens into the linen room; stepping into the gallery,
Thomas's door at its far end swings open. His letter there sends you to Ashby's
study for the attic key, and the Sister starts her rounds. The doctor's suite
is locked; standing at its door, a music box starts up in the nursery, where
the suite key lies. Then the study, the attic key, and the run back along the
gallery to the attic door with her hunting."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engine', 'tools'))   # mapkit
from mapkit import Plan, on_n, on_s, on_w, on_e, at

NAME = "The Wards"
FLOOR = "UPPER FLOOR"           # the map screen's heading
AMBIENCE = 'amb_ward'
MONSTER_MODE = 1
START = (12.5, 0.6, 'S')

MATERIALS = [('floor_carpet', 'ceil_plaster'),      # bedrooms, gallery
             ('floor_boards', 'ceil_plaster'),      # service rooms, nursery
             ('floor_tiles_bw', 'ceil_tiles'),      # bathroom
             ('floor_void', 'ceil_plaster')]        # the stairwell beyond the gallery rail

ROOMS = {
    'T': dict(name="Thomas's room", wall='paper_floral', mat=0),
    'U': dict(name='East ward', wall='paper_stripe', mat=0),
    'V': dict(name='West ward', wall='paper_stripe', mat=0),
    'R': dict(name='Bathroom', wall='tile_bath', mat=2),
    'X': dict(name='Linen room', wall='plaster', mat=1),
    'N': dict(name="Night sister's room", wall='plaster', mat=1),
    'C': dict(name='Gallery', wall='paper_red', mat=0),
    'Y': dict(name='Nursery', wall='paper_nursery', mat=1),
    'H': dict(name='Landing', wall='panel_oak', mat=0),
    'W': dict(name='Stairwell', wall='panel_oak_deep', mat=3, map='void'),
    'A': dict(name="Doctor's bedroom", wall='paper_study', mat=0),
    'D': dict(name="Doctor's study", wall='library_shelves', mat=0),
}

P = Plan(14, 10)
P.room('T', 0, 0, 2, 3).room('V', 3, 0, 5, 3).room('U', 6, 0, 8, 3).room('R', 9, 0, 10, 3)
P.room('X', 11, 0, 13, 1).room('N', 11, 2, 13, 3)
P.room('C', 0, 4, 13, 4)
P.room('Y', 0, 5, 3, 9).room('H', 4, 5, 8, 7).room('W', 4, 8, 8, 9).room('A', 9, 5, 11, 9).room('D', 12, 5, 13, 9)
for x in range(4, 9):
    P.door(x, 8, 'N', ' ')                 # open: the gallery looks over the stairwell
P.door(1, 4, 'N').door(4, 4, 'N').door(7, 4, 'N').door(9, 4, 'N').door(12, 4, 'N')
P.door(12, 2, 'N')                         # linen room <-> sister's room
P.door(2, 5, 'N').door(6, 5, 'N', 'a').door(10, 5, 'N', 'l')
P.door(12, 7, 'W')                         # bedroom <-> study
P.door(0, 4, 'W', 'x')                     # attic stair door
for (x, y, o) in [(0, 1, 'W'), (4, 0, 'N'), (7, 0, 'N'), (2, 0, 'N'), (0, 7, 'W'), (6, 9, 'S'),
                  (11, 9, 'S'), (13, 8, 'E'), (13, 5, 'E')]:
    P.door(x, y, o, 'w')
MAP = P.render()

EDGES = {
    (10, 5, 'N'): dict(lock=3, name='suite'),
    (0, 4, 'W'): dict(exit='attic', leaf='leaf_panel'),
    (1, 4, 'N'): dict(name='thomas'),
    (12, 0, 'N'): dict(tex_high='lift_gate', sign="The lift that brought me up. I'm not going back down without Thomas."),
}

DECOR = [
    (3, 4, 'N', 'sconce'), (8, 4, 'N', 'sconce'), (11, 4, 'S', 'sconce'), (5, 4, 'S', 'portrait'),
    (11, 4, 'N', 'mirror'), (1, 4, 'S', 'landscape'),
    (4, 7, 'W', 'portrait'), (8, 7, 'E', 'portrait'), (5, 5, 'N', 'sconce'),
    (11, 9, 'E', 'portrait'), (9, 8, 'W', 'mirror'),
    (0, 2, 'W', 'crucifix'), (5, 1, 'E', 'crucifix'), (8, 1, 'E', 'crucifix'),
    (13, 3, 'E', 'crucifix'), (9, 2, 'W', 'mirror'),
]

PROPS = [
    # Thomas's room
    on_w('bed_iron', 0.0, 1.5), on_n('nightstand', 2.2, 0.0), on_e('wardrobe', 3.0, 2.6, inter=('locker',)),
    at('chair', 0.5, 3.4, 'E'),
    # west ward
    on_n('bed_iron', 3.7, 0.0), on_n('bed_iron', 5.0, 0.0), at('nightstand', 4.35, 0.25, 'S'),
    on_w('wardrobe', 3.0, 3.0, inter=('locker',)),
    # east ward
    on_n('bed_iron', 6.6, 0.0), on_n('bed_iron', 8.3, 0.0), at('dressform', 6.45, 3.45),
    on_e('washstand', 9.0, 2.6),
    # bathroom
    at('bathtub', 9.5, 1.0, 'S'), at('stool', 10.2, 0.8, 'W'), on_e('sink', 11.0, 2.8),
    # linen room and the sister's room
    on_w('shelves_linen', 11.0, 0.6), on_e('shelves_linen', 14.0, 1.0),
    on_s('bed_iron', 13.4, 4.0),                 # her bed, under her crucifix
    on_w('dresser', 11.0, 3.2), at('chair', 12.0, 2.6, 'E'),
    # gallery
    at('covered_tall', 13.5, 4.5),
    # nursery
    at('cot', 1.0, 6.2, 'S'), at('cot', 3.45, 6.2, 'S'), at('dressform', 3.4, 9.3),   # (the doorway clear between the cots)
    on_w('wardrobe', 0.0, 8.4, inter=('locker',)), at('chest', 1.8, 9.5, 'N'), at('stool', 2.3, 8.0),
    # landing: the gallery rail over the fallen stairs
    at('railing', 4.5, 7.96, 'S'), at('railing', 5.5, 7.96, 'S'), at('railing', 6.5, 7.96, 'S'),
    at('railing', 7.5, 7.96, 'S'), at('railing', 8.5, 7.96, 'S'),
    at('covered', 4.55, 5.6, 'E'), at('lamp_standard', 8.5, 5.4),
    # doctor's bedroom
    on_s('bed', 10.0, 10.0),
    at('nightstand', 9.25, 9.65, 'N'), on_w('wardrobe', 9.0, 6.4, inter=('locker',)),
    at('armchair', 11.4, 6.2, 160),
    # doctor's study
    on_n('desk', 12.9, 5.0), at('chair', 12.9, 5.55, 'N'), on_e('bookcase', 14.0, 7.6),
    at('lamp_standard', 12.4, 9.5),
]

THINGS = [
    dict(x=12.6, y=0.9, type='battery'),
    dict(x=11.2, y=3.2, z=0.62, type='note', param=7),           # sister's diary, on the dresser
    dict(x=2.0, y=9.5, z=0.32, type='note', param=8),           # child's drawing, on the toy chest
    dict(x=2.2, y=8.0, z=0.33, type='key', param=3, event='suitekey'),   # on the nursery stool
    dict(x=12.7, y=5.2, z=0.52, type='note', param=9),          # Ashby's journal on the desk
    dict(x=13.1, y=5.2, z=0.52, type='key', param=4, event='attic_key'),
    dict(x=2.2, y=0.3, z=0.42, type='note', param=10, event='tomletter'),   # Thomas's letter on his nightstand
    dict(x=4.3, y=0.3, z=0.42, type='battery'),
    dict(x=7.5, y=6.0, type='battery'),
    dict(x=1.25, y=6.75, type='doll'), dict(x=3.45, y=6.75, type='bear'), dict(x=0.6, y=9.4, type='rockinghorse'),
    dict(x=10.2, y=0.8, z=0.33, type='candles'),           # on the stool by the bath
]

LIGHTS = [
    (3.5, 4.2, 14, 2.8, 'flicker'), (8.5, 4.2, 14, 2.8), (11.5, 4.8, 13, 2.8, 'buzz'),
    (5.5, 5.2, 13, 2.8),
    (1.5, 0.3, 8, 3.0), (7.5, 0.3, 8, 3.0), (6.5, 9.7, 9, 3.0), (13.7, 5.5, 8, 2.6),   # moonlight
    (12.4, 9.4, 14, 3.0, 'steady'), (10.2, 0.8, 12, 2.6, 'candle'),
    (1.8, 7.5, 9, 3.0, 'pulse', 3),                               # nursery night-light
]

TRIGGERS = [
    (0, 5, 3, 9, 'nursery'),
    (0, 0, 2, 3, 'thomas'),
    (4, 5, 8, 7, 'landing'),
    (11, 4, 12, 4, 'gallery'),
    (10, 4, 10, 4, 'suite', 1, 'l3_letter'),       # at Ashby's door, once Thomas's letter is read
    (9, 0, 10, 3, 'bathroom'),
    (11, 2, 13, 3, 'sisterroom', 1, 'l3_intro'),
]
PATROL = [(1, 4), (6, 4), (12, 4), (4, 2), (7, 2), (1, 2), (2, 7), (6, 6), (10, 7), (12, 3)]

EVENTS = {
    'start': [
        ('wait', 40),
        ('msg', "The lift opens into a linen room. Upstairs. The wards. Thomas slept somewhere on this floor.", 280),
        ('start', 'ambient'),
        ('wait', 200),
        ('flag', 'l3_intro'),
        ('if_flag', 'l3_room', 'skip'),
        ('objective', "Find Thomas's room."),
        ('label', 'skip'),
    ],
    # stepping into the gallery: his door, at the far end, swings open
    'gallery': [
        ('wait', 40),
        ('door', 'thomas', 'open'),
        ('sound3d', 'creak', 1, 4, 230),
        ('wait', 50),
        ('if_flag', 'l3_room', 'done'),
        ('msg', "At the far end of the gallery, a door is swinging slowly open.", 220),
        ('label', 'done'),
    ],
    'tomletter': [
        ('wait', 10),
        ('flag', 'l3_letter'),
        ('if_key', 4, 'done'),
        ('objective', "The attic key: in Dr. Ashby's study."),
        ('wait', 160),
        ('creature', 'mode', 1),
        ('creature', 'spawn', 12, 4),
        ('sound3d', 'door_close', 12, 3, 200),
        ('wait', 60),
        ('msg', "Out in the gallery a door closed. Then slow steps, and the creak of a lantern handle.", 260),
        ('fear', 40),
        ('label', 'done'),
    ],
    # locked out of the suite: a music box starts up across the landing
    'suite': [
        ('if_key', 3, 'done'),
        ('wait', 150),
        ('flag', 'l3_box'),
        ('start', 'musicbox'),
        ('wait', 60),
        ('msg', "Somewhere past the landing, very faintly, a music box has started to play.", 240),
        ('objective', "Find the key to Dr. Ashby's rooms."),
        ('label', 'done'),
    ],
    'musicbox': [
        ('label', 'top'),
        ('if_flag', 'l3_nursery', 'stop'),
        ('sound3d', 'musicbox_phrase', 2, 7, 240),
        ('wait', 960),
        ('jmp', 'top'),
        ('label', 'stop'),
    ],
    'bathroom': [
        ('wait', 30),
        ('msg', "The bath is full to the brim with black water. Someone lit candles for it.", 230),
    ],
    'sisterroom': [
        ('wait', 30),
        ('msg', "A narrow bed, made so tight a coin would bounce on it. Her room, before.", 220),
    ],
    'suitekey': [
        ('wait', 30),
        ('musicstop',),
        ('light', 3, 0),
        ('sound', 'click', 150),
        ('wait', 40),
        ('sound3d', 'creak', 1, 6, 220),
        ('fear', 50),
        ('wait', 30),
        ('msg', "The night-light went out. One of the cots creaked, as if someone small had just climbed out.", 270),
        ('creature', 'hear', 2, 7),
        ('objective', "Dr. Ashby's rooms, across the gallery."),
    ],
    'ambient': [
        ('label', 'top'),
        ('wait', 400),
        ('jrand', 128, 'b'),
        ('sound3d', 'creak', 6, 2, 160),
        ('jmp', 'top'),
        ('label', 'b'),
        ('sound3d', 'whisper', 1, 7, 120),
        ('jmp', 'top'),
    ],
    'thomas': [
        ('flag', 'l3_room'),
        ('wait', 30),
        ('msg', "His bed. His things. The sheets are still turned back, as if he got up in the night.", 260),
        ('objective', "Find where Thomas went."),
    ],
    'nursery': [
        ('flag', 'l3_nursery'),
        ('wait', 40),
        ('music', 'lullaby', 70),
        ('msg', "A nursery, though there were never children in this house. The night-light is still on.", 260),
        ('wait', 400),
        ('musicstop',),
    ],
    'landing': [
        ('msg', "The landing. Below the rail, the staircase is a pit of splintered wood.", 230),
    ],
    'attic_key': [
        ('objective', "The attic door, at the far end of the gallery."),
        ('wait', 30),
        ('creature', 'mode', 2),
        ('creature', 'hear', 10, 6),
        ('sound3d', 'slam', 1, 4, 220),
        ('fear', 50),
        ('checkpoint',),
    ],
    'attic': [
        ('ifnot_key', 4, 'locked'),
        ('freeze', 1),
        ('sound', 'door_open', 220),
        ('wait', 30),
        ('sound', 'stairs', 200),
        ('wait', 60),
        ('endlevel', 3),
        ('end',),
        ('label', 'locked'),
        ('msg', "Locked: ATTIC. Thomas, are you up there?", 220),
        ('objective', "Find the attic key."),
    ],
}
