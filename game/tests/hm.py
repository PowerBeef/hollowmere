# SPDX-License-Identifier: MIT
"""Shared pieces of Hollowmere's test scripts: where things are in memory
(game/src/game.h keeps these offsets fixed with static asserts) and the
harness lines the tests keep repeating."""
import harness

# SaveState g_state
LEVEL, OBJECTIVE, KEYS, FUSES, PLACED, FLASH_ON, DEATHS = 4, 6, 12, 14, 15, 20, 22
# Creature g_cr
CR_STATE, CR_X, CR_Y = 0, 4, 8
CR_OFF, CR_SCRIPT, CR_PATROL, CR_INVESTIGATE, CR_CHASE, CR_SEARCH, CR_LEAVE, CR_KILL, CR_PRAY, CR_WAIT, CR_RETURN = range(11)
# g_gameSignal
GS_PLAY, GS_DEAD, GS_EXIT, GS_ENDING = 0, 1, 2, 3

boot, teleport, load_level, dismiss = harness.boot, harness.teleport, harness.load_level, harness.dismiss


def spawn(dist_tiles, state, settle=8):
    """Debug command 1: the Sister, dist_tiles in front of the player."""
    return [f"poke32 {{g_debugA}} {int(dist_tiles * 16)}", f"poke32 {{g_debugB}} {state}", "poke32 {g_debugCmd} 1", f"run {settle}"]


def start_event(ev, settle=8):
    """Debug command 6: start script event number ev of the level."""
    return [f"poke32 {{g_debugA}} {ev}", "poke32 {g_debugCmd} 6", f"run {settle}"]


def act(frames=40, key='A'):
    return [f"tap {key}", f"run {frames}"]


def state(tag):
    """Echo a label and print level, keys, fuses, fuses placed, signal."""
    return [f"echo {tag}", f"peek8 {{g_state+{LEVEL}}}", f"peek16 {{g_state+{KEYS}}}", f"peek8 {{g_state+{FUSES}}}",
            f"peek8 {{g_state+{PLACED}}}", "peek8 {g_gameSignal}"]
