# SPDX-License-Identifier: MIT
"""Regression tests: work that used to arrive in one frame and cost it
several (measured in CPU cycles by the test ROM's own timers)."""
import hm

FRAME = 842688                      # three vblanks: the budget of a frame at 20 fps
WORK = ["peek32 {g_renderCount}", "peek32 {g_profUpdate}", "peek32 {g_profRaw}"]


def watch(frames):
    L = []
    for _ in range(frames):
        L += ["run 1"] + WORK
    return L


def frames_of(values):
    """{rendered frame: (cycles of its logic updates, cycles of its drawing)}"""
    return {values[i]: (values[i + 1], values[i + 2]) for i in range(0, len(values) - 2, 3)}


def test_flashlight_switch_fits_a_frame(t):
    """Switching the flashlight off and on rebuilt its light tables in the
    frame of the switch (1.2 million cycles: a frame and a half). The tables
    of each power step are kept now."""
    L = hm.boot() + hm.dismiss() + ["run 600", "echo off", "tap SELECT 3"] + watch(40)
    L += ["run 60", "echo on", "tap SELECT 3"] + watch(40)
    L += ["run 120", f"poke32 {{g_state+{hm.BATTERY}}} 50000", "echo low"] + watch(1200)
    parts = {k: frames_of(v) for k, v in t.run(L).sections()}
    for k in ('off', 'on'):
        worst = max(u + r for u, r in parts[k].values())
        t.check(worst <= FRAME, f"switching the flashlight {k}: a frame of {worst:,} cycles (the budget is {FRAME:,})")
    low = [u + r for u, r in parts['low'].values()]
    slow = sum(1 for w in low if w > 900000)
    t.check(slow <= len(low) // 40, f"with a flickering, nearly flat battery {slow} of {len(low)} frames cost over 900,000 cycles")


def test_long_subtitle_is_drawn_over_several_frames(t):
    """A long line of text was drawn inside one logic update (0.77 million
    cycles for the 97 characters of the vestry's sign)."""
    L = hm.boot() + hm.dismiss() + hm.load_level(3) + ["run 600", "echo quiet"] + watch(90) + ["echo before", "peek8 {g_quality}"]
    L += ["echo text"] + hm.start_event(hm.event_id(3, 'vestry'), settle=0) + watch(120) + ["echo after", "peek8 {g_quality}"]
    raw = dict(t.run(L).sections())
    parts = {k: frames_of(raw[k]) for k in ('quiet', 'text')}
    quiet = max(u for u, _ in parts['quiet'].values())
    text = max(u for u, _ in parts['text'].values())
    t.check(text < 150000, f"the updates of one frame cost {text:,} cycles while the sign's text came up ({quiet:,} with no text)")
    t.check(raw['after'][0] <= raw['before'][0], f"drawing the text cost the view detail: level {raw['before'][0]} before it, {raw['after'][0]} two seconds after")


def test_chase_updates_stay_small(t):
    """The Sister's path search ran whole when the player changed cell (up
    to 171,000 cycles in one update) and her lantern's light was rebuilt
    whole on every new tile. Both are spread over several updates now."""
    L = hm.boot() + hm.dismiss() + ["run 600"] + hm.teleport(1.5, 4.5, 0) + hm.spawn(9.0, hm.CR_CHASE)
    L += ["echo chase"]
    for x in (1.5, 2.5, 1.5, 2.5, 1.5, 2.5):                # the player changes cell: a new path each time
        L += hm.teleport(x, 4.5, 0, settle=0) + watch(24)
    L += ["peek8 {g_cr}"]
    r = t.run(L)
    v = dict(r.sections())['chase']
    state, fr = v[-1], frames_of(v[:-1])
    worst = max(u for u, _ in fr.values())
    t.check(state == hm.CR_CHASE, f"the Sister is no longer chasing (state {state}): the test measured nothing")
    t.check(worst < 100000, f"the updates of one frame cost {worst:,} cycles during a chase")
