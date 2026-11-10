# SPDX-License-Identifier: MIT
"""Hollowmere: what the engine's toolchain builds for this game.

LEVELS are level modules in game/content/levels, in play order (the
engine's level index 0, 1, 2...). The cartridge title and game code are set
in the Makefile (GAME_TITLE, GAME_CODE)."""

LEVELS = ['l1_ground', 'l2_cellar', 'l3_upper', 'l4_attic']
