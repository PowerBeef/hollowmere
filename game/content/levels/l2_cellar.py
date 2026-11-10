# SPDX-License-Identifier: MIT
"""Chapter II: the cellars. Three fuses for the generator, then the service lift."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engine', 'tools'))   # mapkit
from mapkit import Plan, on_n, on_s, on_w, on_e, at

NAME = "Beneath"
FLOOR = "CELLARS"           # the map screen's heading
AMBIENCE = 'amb_basement'
MONSTER_MODE = 0
START = (7.5, 1.3, 'S')

MATERIALS = [('floor_flagstone', 'ceil_vault'),     # stone cellars
             ('floor_concrete', 'ceil_concrete'),   # plant rooms
             ('floor_hex', 'ceil_tiles'),           # laundry, cold room
             ('floor_water', 'ceil_stone')]         # the spring

ROOMS = {
    'A': dict(name='Cellar stair', wall='stone_cellar', mat=0),
    'C': dict(name='Passage', wall='stone_cellar', mat=0),
    'W': dict(name='Wine cellar', wall='brick_cellar', mat=0),
    'B': dict(name='Boiler room', wall='pipes_cellar', mat=1),
    'L': dict(name='Laundry', wall='tile_kitchen', mat=2),
    'G': dict(name='Generator room', wall='pipes_cellar', mat=1),
    'M': dict(name='Cold room', wall='tile_bath', mat=2),
    'S': dict(name='The spring', wall='stone_well', mat=3),
    'E': dict(name='Lift lobby', wall='brick_cellar', mat=1),
}

P = Plan(14, 13)
P.room('W', 0, 0, 5, 4).room('A', 6, 0, 8, 1).room('B', 9, 0, 13, 3)
P.room('C', 6, 2, 8, 10)
P.room('L', 0, 5, 5, 8).room('G', 9, 4, 13, 8)
P.room('M', 0, 9, 5, 12).room('S', 9, 9, 13, 12)
P.room('E', 6, 11, 8, 12)
P.door(7, 2, 'N', 'a')                       # stair foot -> passage
P.door(6, 3, 'W')                            # wine cellar
P.door(9, 2, 'W', 'l')                       # boiler room (locked)
P.door(6, 6, 'W')                            # laundry
P.door(9, 6, 'W', 'D')                       # generator room
P.door(6, 10, 'W')                           # cold room
P.door(9, 10, 'W', 'n')                      # the spring
P.door(7, 11, 'N', 'a')                      # lift lobby
P.door(11, 4, 'N')                           # boiler room -> generator room
P.door(7, 0, 'N', 'x')                       # the stair back up
MAP = P.render()

EDGES = {
    (9, 2, 'W'): dict(lock=2, leaf='leaf_cellar', name='boiler'),
    (7, 0, 'N'): dict(sign="The cellar door slammed shut above me. It's bolted from the other side.", leaf='leaf_cellar'),
    (7, 13, 'N'): dict(tex_low='lift_gate', event='lift'),
}

DECOR = [
    (6, 4, 'W', 'sconce'), (8, 8, 'E', 'sconce'), (6, 1, 'W', 'sconce_off'),
    (0, 10, 'W', 'crucifix'), (11, 9, 'N', 'crucifix'),
]

PROPS = [
    # wine cellar
    on_n('wine_rack', 0.8, 0.0), on_n('wine_rack', 2.0, 0.0), on_n('wine_rack', 3.2, 0.0),
    on_w('wine_rack', 0.0, 2.6), on_w('wine_rack', 0.0, 3.8),
    at('barrel', 4.5, 0.6), at('barrel', 5.4, 0.55), at('barrel', 4.9, 1.3),
    at('table_kitchen', 2.8, 2.6, 'S'), at('crates', 4.6, 4.3),
    # boiler room
    at('boiler', 11.5, 1.3, 'S'), at('crates', 9.6, 0.6), at('crate', 13.4, 0.5), at('crates', 12.9, 3.2),
    on_e('shelves', 14.0, 2.4),
    # laundry
    on_n('sink', 1.2, 5.0), on_n('sink', 2.2, 5.0),
    at('table_kitchen', 2.5, 7.0, 'E'), at('bathtub', 4.6, 7.2, 'S'),
    on_w('wardrobe', 0.0, 7.2, inter=('locker',)),
    on_s('shelves_linen', 4.7, 9.0),
    # generator room
    at('generator', 11.4, 6.0, 'S', inter=('generator', 'generator'), front=0.45),
    on_e('fusebox', 14.0, 5.0, inter=('fusebox', 'fusebox'), front=0.25),
    at('crates', 9.6, 8.4), at('barrel', 13.4, 8.4),
    # cold room
    at('table_surgery', 2.0, 10.6, 'S'), at('table_surgery', 2.0, 12.0, 'S'),
    at('covered', 4.4, 10.3), on_e('wardrobe', 6.0, 12.3, inter=('locker',)),
    on_w('shelves', 0.0, 11.5),
    # the spring
    at('altar', 11.5, 12.4, 'N'),
    # lift lobby
    at('crate', 6.4, 12.5), at('chair', 8.5, 11.4, 160),
]

THINGS = [
    dict(x=7.0, y=1.6, type='note', param=3, event='scrawl'),    # gardener's scrawl
    dict(x=2.9, y=2.55, z=0.5, type='fuse', event='fuse_wine'),  # wine cellar table
    dict(x=13.4, y=1.6, type='fuse', event='fuse_boiler'),       # behind the boiler
    dict(x=2.0, y=12.0, z=0.55, type='fuse', event='cold_fuse'), # on a slab in the cold room
    dict(x=2.6, y=7.0, z=0.5, type='key', param=2),              # laundry table
    dict(x=10.0, y=5.6, type='note', param=4),                   # maintenance notice
    dict(x=4.2, y=5.6, type='note', param=5),                    # Thomas's notebook
    dict(x=11.5, y=12.2, z=0.62, type='note', param=6, event='mere'),   # Ashby's clinical notes, on the altar
    dict(x=11.0, y=12.3, z=0.62, type='candles'), dict(x=12.0, y=12.3, z=0.62, type='candles'),
    dict(x=0.6, y=0.9, type='battery'), dict(x=13.3, y=11.3, type='battery'), dict(x=7.6, y=9.5, type='battery'),
    dict(x=1.0, y=8.5, type='sheets'), dict(x=3.6, y=5.7, type='sheets'),
    dict(x=4.4, y=12.4, type='bodybag'), dict(x=3.8, y=9.5, type='bucket'),
]

LIGHTS = [
    (6.3, 4.5, 13, 3.0, 'flicker'), (8.7, 8.5, 13, 3.0),         # passage lamps
    (11.5, 2.2, 13, 3.0, 'candle'),                               # boiler firebox
    (11.0, 12.2, 14, 3.0, 'candle'), (12.0, 12.2, 12, 2.6, 'candle'),   # the spring's candles
    # mains lights: off until the generator runs
    (2.5, 2.0, 16, 3.6, 'buzz', 1), (2.5, 6.8, 16, 3.6, 'steady', 1), (2.5, 10.8, 16, 3.6, 'buzz', 1),
    (7.5, 6.5, 16, 3.6, 'steady', 1), (11.5, 6.5, 17, 3.8, 'buzz', 2), (7.5, 12.0, 16, 3.0, 'steady', 2),
]

TRIGGERS = [
    (6, 5, 8, 7, 'first_sight'),
    (0, 9, 5, 12, 'coldroom'),
    (9, 9, 13, 12, 'spring'),
    (0, 0, 5, 4, 'wine'),
    (0, 5, 5, 8, 'laundry'),
]
PATROL = [(7, 3), (7, 6), (7, 9), (3, 3), (2, 6), (2, 10), (11, 7), (12, 10), (7, 12), (11, 2)]
DOOR_NAMES = {}

EVENTS = {
    'start': [
        ('light', 1, 0), ('light', 2, 0),
        ('wait', 40),
        ('msg', "The music stopped the moment the door closed. Coal smoke, damp stone, and something sweeter.", 280),
        ('start', 'drips'),
        ('wait', 200),
        ('if_flag', 'l2_scrawl', 'done'),
        ('objective', "Find another way out of the cellars."),
        ('wait', 2400),
        ('if_flag', 'l2_scrawl', 'done'),
        ('objective', "Find a way out. Read the note by the stairs."),
        ('label', 'done'),
    ],
    'scrawl': [
        ('wait', 10),
        ('flag', 'l2_scrawl'),
        ('if_flag', 'l2_fuses', 'done'),
        ('objective', "Find 3 fuses: wine cellar, boiler room, cold room."),
        ('label', 'done'),
    ],
    'fuse_wine': [('flag', 'l2_fw'), ('start', 'fusecheck')],
    'fuse_boiler': [('flag', 'l2_fb'), ('start', 'fusecheck')],
    'fusecheck': [
        ('ifnot_flag', 'l2_fw', 'more'),
        ('ifnot_flag', 'l2_fb', 'more'),
        ('ifnot_flag', 'l2_fc', 'more'),
        ('flag', 'l2_fuses'),
        ('wait', 160),
        ('objective', "Fit the fuses in the generator room's panel."),
        ('end',),
        ('label', 'more'),
        ('if_flag', 'l2_scrawl', 'done'),
        ('wait', 160),
        ('objective', "Find more fuses. The generator will want three."),
        ('label', 'done'),
    ],
    'laundry': [
        ('wait', 30),
        ('msg', "Sheets hang on the drying lines. They're still wet, after all these months.", 230),
    ],
    'mere': [
        ('wait', 20),
        ('sound3d', 'whisper', 11, 10, 230),
        ('fear', 45),
        ('wait', 60),
        ('msg', "Behind me, out on the black water, something surfaced. When I turned there were only rings.", 270),
    ],
    'drips': [
        ('label', 'top'),
        ('wait', 220),
        ('jrand', 120, 'b'),
        ('sound3d', 'drip', 11, 11, 150),
        ('jmp', 'top'),
        ('label', 'b'),
        ('sound3d', 'drip', 2, 3, 140),
        ('wait', 180),
        ('jrand', 200, 'top'),
        ('sound3d', 'bang', 11, 1, 110),
        ('jmp', 'top'),
    ],
    'first_sight': [
        ('wait', 10),
        ('sound3d', 'distant_scream', 11, 11, 200),
        ('fear', 50),
        ('wait', 100),
        ('msg', "That came from the far end of the passage. She's down here with me.", 230),
        ('creature', 'mode', 1),
        ('creature', 'spawn', 11, 10),
    ],
    'wine': [
        ('wait', 40),
        ('sound3d', 'glass', 0, 3, 160),
        ('msg', "A bottle rolled off a rack somewhere in the dark.", 180),
    ],
    'coldroom': [
        ('wait', 30),
        ('msg', "A cold room. There are shapes under the sheets on the slabs.", 220),
    ],
    'cold_fuse': [
        ('flag', 'l2_fc'),
        ('start', 'fusecheck'),
        ('wait', 50),
        ('sound3d', 'whisper', 2, 10, 170),
        ('fear', 40),
        ('wait', 40),
        ('msg', "Under the other sheet, something let out a long, slow breath.", 220),
    ],
    'spring': [
        ('sound3d', 'drip', 11, 11, 200),
        ('wait', 40),
        ('msg', "The floor gives way to black water. A spring, under the house. It doesn't move at all.", 260),
    ],
    'fusebox': [
        ('if_flag', 'l2_power', 'running'),
        ('if_fuses_lt', 3, 'need'),
        ('msg', "All three fuses are fitted.", 160),
        ('end',),
        ('label', 'need'),
        ('placefuses',),
        ('if_fuses_lt', 1, 'empty'),
        ('sound', 'fuse', 200),
        ('if_fuses_lt', 3, 'partial'),
        ('msg', "The third fuse clicks home. Now the start lever on the generator.", 230),
        ('objective', "Pull the generator's start lever."),
        ('checkpoint',),
        ('end',),
        ('label', 'partial'),
        ('msg', "Fuse fitted. The panel has three slots.", 200),
        ('end',),
        ('label', 'empty'),
        ('msg', "A fuse panel with three empty slots. 30-amp cartridge fuses.", 220),
        ('if_flag', 'l2_scrawl', 'known'),
        ('objective', "Find three fuses for the generator."),
        ('label', 'known'),
        ('end',),
        ('label', 'running'),
        ('msg', "The generator is running.", 140),
    ],
    'generator': [
        ('if_flag', 'l2_power', 'running'),
        ('if_fuses_lt', 3, 'nofuse'),
        ('flag', 'l2_power'),
        ('sound', 'generator', 230),
        ('shake', 1, 120),
        ('wait', 110),
        ('light', 2, 255),
        ('wait', 30),
        ('light', 1, 255),
        ('sound', 'fuse', 160),
        ('msg', "The generator coughs and catches. Bulbs stutter on all over the cellars.", 260),
        ('creature', 'mode', 2),
        ('creature', 'hear', 11, 6),
        ('fear', 60),
        ('objective', "Get to the service lift. Hurry."),
        ('checkpoint',),
        ('end',),
        ('label', 'nofuse'),
        ('msg', "I pull the lever. Nothing. The fuse panel must be empty.", 220),
        ('end',),
        ('label', 'running'),
        ('msg', "The generator is roaring. She will have heard it.", 160),
    ],
    'lift': [
        ('if_flag', 'l2_liftready', 'go'),
        ('ifnot_flag', 'l2_power', 'nopower'),
        ('if_flag', 'l2_liftcalled', 'waiting'),
        ('flag', 'l2_liftcalled'),
        ('sound', 'chain', 220),
        ('msg', "I press the call button. Far above, machinery groans into motion.", 240),
        ('objective', "Wait for the lift. Stay alive."),
        ('wait', 420),
        ('sound3d', 'locker_close', 7, 12, 255),
        ('sound3d', 'chain', 7, 12, 220),
        ('flag', 'l2_liftready'),
        ('msg', "The lift has arrived.", 200),
        ('objective', "Get in the lift."),
        ('end',),
        ('label', 'waiting'),
        ('msg', "Come on. Come on...", 120),
        ('end',),
        ('label', 'nopower'),
        ('msg', "The service lift. The call button is dead: no power.", 220),
        ('objective', "Get the power back on."),
        ('end',),
        ('label', 'go'),
        ('freeze', 1),
        ('sound', 'locker_open', 220),
        ('wait', 40),
        ('endlevel', 2),
    ],
}
