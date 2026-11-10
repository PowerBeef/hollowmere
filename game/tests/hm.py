# SPDX-License-Identifier: MIT
"""Shared pieces of Hollowmere's test scripts: where things are in memory
(game/src/game.h keeps these offsets fixed with static asserts) and the
harness lines the tests keep repeating."""
import importlib

import harness

# SaveState g_state
LEVEL, OBJECTIVE, KEYS, FUSES, PLACED, FLASH_ON, DEATHS = 4, 6, 12, 14, 15, 20, 22
TRIG_FIRED, FLAGS, LIGHT_LEVEL = 56, 144, 152
# Creature g_cr
CR_STATE, CR_X, CR_Y, CR_TIMER = 0, 4, 8, 34
# Player g_player
PL_HIDING, PL_FROZEN = 16, 37
# FxState g_fx
FX_SLITS = 22
# Settings g_settings
SET_CONTROLS = 2
# Thing g_things[112] (16 bytes each); script threads s_th[8] (12 bytes each)
THING_SIZE, THING_FLAGS, MAX_THINGS, THF_HIDDEN = 16, 10, 112, 2
TH_SIZE, TH_ACTIVE, TH_EVENT, MAX_THREADS = 12, 10, 11, 8
CR_OFF, CR_SCRIPT, CR_PATROL, CR_INVESTIGATE, CR_CHASE, CR_SEARCH, CR_LEAVE, CR_KILL, CR_PRAY, CR_WAIT, CR_RETURN = range(11)
# g_gameSignal
GS_PLAY, GS_DEAD, GS_EXIT, GS_ENDING = 0, 1, 2, 3

boot, teleport, load_level, dismiss = harness.boot, harness.teleport, harness.load_level, harness.dismiss
HUD_OFF = ["poke8 {s_visible} 0"]      # hud.c: no text, prompts or icons until the next level


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


def die(deaths=1):
    """The Sister catches the player; through the death screen and Continue,
    back in play at the last checkpoint with the count of deaths checked."""
    return spawn(1.0, CR_CHASE, settle=0) + ["run 30", "tap A"] * 13 + ["run 60"] + [
        "expect8 {g_gameSignal} == 0 back in play after dying",
        f"expect16 {{g_state+{DEATHS}}} == {deaths} deaths counted"]


def hide_things():
    """Every pickup and note of the level out of sight (until it is reloaded)."""
    return [f"poke8 {{g_things+{i * THING_SIZE + THING_FLAGS}}} {THF_HIDDEN}" for i in range(MAX_THINGS)]


def threads():
    """Peeks: active flag and event number of every script thread (16 values)."""
    return [l for i in range(MAX_THREADS) for l in (f"peek8 {{s_th+{i * TH_SIZE + TH_ACTIVE}}}", f"peek8 {{s_th+{i * TH_SIZE + TH_EVENT}}}")]


def _level(index):
    from manifest import LEVELS
    return importlib.import_module(LEVELS[index])


def event_id(level, name):
    """The number of a level's script event (build_assets.py numbers them:
    start, lantern, then the rest in the order they are written)."""
    order = ['start', 'lantern'] + [k for k in _level(level).EVENTS if k not in ('start', 'lantern')]
    return order.index(name) + 1


def trigger_index(level, event):
    return [t[4] for t in _level(level).TRIGGERS].index(event)


def rendering(frames=60):
    """Peeks around a wait: the 3D view is being drawn if the count moved."""
    return ["peek32 {g_renderCount}", f"run {frames}", "peek32 {g_renderCount}"]
