# SPDX-License-Identifier: MIT
"""Hollowmere: what the engine's toolchain builds for this game
(engine/tools/build_assets.py reads it; docs/MAKING_A_GAME.md describes every
entry). The cartridge title and game code are in game/game.mk."""

# Level modules in game/content/levels, in play order (the engine's level
# index 0, 1, 2...).
LEVELS = ['l1_ground', 'l2_cellar', 'l3_upper', 'l4_attic']

# Events every level has, in this order. The engine starts the first when a
# level begins; the game's code starts the second (the lantern's: taking it
# from the Sister in the chapel, player.c) by its number.
LEVEL_EVENTS = ('start', 'lantern')

# Tunes a script can start with ('music', name): the sequence in music.py,
# the sound it is played on, whether it loops.
MUSIC = [('lullaby', 'musicbox', True), ('fragment', 'musicbox', False), ('ending', 'piano', False)]

# The furniture models the engine hangs in doorways.
DOOR_MODELS = dict(single='leaf_single', half='leaf_half')

# The Night Sister's pre-rendered sprite sheets (game/assets, made by
# game/content/sister/make.py), and the frames that speak for all of them
# when the shared palette is chosen.
ENEMY_SHEETS = dict(file='sister.npz',
                    palette_frames=['walk_0_0', 'walk_2_2', 'walk_4_4', 'walk_6_6', 'chase_0_3', 'idle_1_0',
                                    'search_0_0', 'kneel_4_0', 'attack_0_7'])
