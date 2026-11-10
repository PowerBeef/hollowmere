# SPDX-License-Identifier: MIT
"""Regression tests: progress, checkpoints, scripts and signals."""
import hm
from hm import LEVEL, DEATHS, CR_STATE, CR_TIMER, CR_PRAY, CR_CHASE, OBJECTIVE, LIGHT_LEVEL, TRIG_FIRED, KEYS


def test_finale_after_death(t):
    """Chapter IV can be finished after dying in it: the checkpoint puts the
    Sister back at her prayers."""
    L = hm.boot() + hm.dismiss() + hm.load_level(3) + ["run 300"]
    L += [f"expect8 {{g_cr+{CR_STATE}}} == {CR_PRAY} she prays when the chapter starts"]
    L += hm.die() + ["run 120"]
    L += [f"expect8 {{g_state+{LEVEL}}} == 3 still in the attic",
          f"expect8 {{g_cr+{CR_STATE}}} == {CR_PRAY} she prays again after Continue"]
    L += hm.act(10, 'SELECT') + hm.teleport(10.6, 2.25, 270) + ["run 20"] + hm.act(400)
    L += ["expect8 {g_gameSignal} == 3 the ending is reached after a death"]
    t.run(L)


def test_start_on_the_exit_tick(t):
    """START pressed on the tick a level ends does not cancel the exit."""
    L = hm.boot() + hm.dismiss() + ["poke32 {g_debugA} 1", "poke32 {g_debugCmd} 4", "tap START 1", "run 500"]
    L += [f"expect8 {{g_state+{LEVEL}}} == 1 the next chapter loaded"] + hm.rendering()
    a, b = t.run(L).values()[-2:]
    t.check(b > a, "the game is not running after START on the exit tick")


def test_start_on_the_catch_tick(t):
    """START pressed around the tick the Sister catches the player never
    swallows the death (which left the game stuck in her grip)."""
    for off in range(5, 17):
        L = hm.boot() + hm.dismiss() + ["run 200"] + hm.spawn(1.0, CR_CHASE, settle=0)
        L += [f"run {off}", "tap START 1", "run 30", "tap A", "run 300"] + ["run 30", "tap A"] * 14 + ["run 60"]
        L += [f"expect16 {{g_state+{DEATHS}}} >= 1 START {off} frames after she appears: the death was lost",
              "expect8 {g_gameSignal} == 0 back in play"]
        t.run(L, name=f"off{off}")


def test_no_kill_during_the_ending(t):
    """Her prayer ending while the last cutscene holds the player still does
    not kill him."""
    L = hm.boot() + hm.dismiss() + hm.load_level(3) + ["run 300"]
    L += hm.act(10, 'SELECT') + hm.teleport(10.6, 2.25, 270) + ["run 20"]
    L += [f"poke16 {{g_cr+{CR_TIMER}}} 30", "tap A", "run 400"]
    L += ["expect8 {g_gameSignal} == 3 the ending is reached", f"expect16 {{g_state+{DEATHS}}} == 0 nobody died"]
    t.run(L)


def test_keys_pressed_during_a_chapter_card(t):
    """START pressed while the chapter card is up does not open the pause
    menu when play begins."""
    L = hm.boot() + hm.dismiss() + ["poke32 {g_debugA} 1", "poke32 {g_debugCmd} 4"]
    L += ["run 60", "tap START", "run 60", "tap START", "run 60", "tap START", "run 60", "tap START", "run 300"]
    L += [f"expect8 {{g_state+{LEVEL}}} == 1 the next chapter loaded"] + hm.rendering()
    a, b = t.run(L).values()[-2:]
    t.check(b > a, "the pause menu opened by itself after the chapter card")


def test_checkpoint_keeps_what_the_start_event_set(t):
    """After dying, the level is as its opening script left it: the cellar
    dark, the objective shown."""
    for level, lights in ((1, (1, 2)), (2, ())):
        L = hm.boot() + hm.dismiss() + hm.load_level(level) + ["run 400"] + hm.dismiss()
        L += [f"expect8 {{g_state+{LIGHT_LEVEL + g}}} == 0 light group {g} is off before" for g in lights]
        L += [f"expect8 {{g_state+{OBJECTIVE}}} != 0 an objective is set", f"peek8 {{g_state+{OBJECTIVE}}}"]
        L += hm.die() + hm.dismiss() + ["run 400"]
        L += [f"expect8 {{g_state+{LIGHT_LEVEL + g}}} == 0 light group {g} is off after dying" for g in lights]
        L += [f"peek8 {{g_state+{OBJECTIVE}}}"]
        before, after = t.run(L, name=f"level{level}").values()[-2:]
        t.check(before == after, f"level {level}: objective {before} before dying, {after} after")


def test_lift_called_before_the_checkpoint(t):
    """The lift called in the moment between the generator starting and its
    checkpoint still arrives after a death."""
    L = hm.boot() + hm.dismiss() + hm.load_level(1) + ["run 300"] + hm.dismiss()
    L += ["poke32 {g_debugCmd} 3", "run 8"]                                   # three fuses
    L += hm.teleport(13.0, 5.0, 0) + hm.act(60)                               # fit them
    L += hm.teleport(11.4, 7.1, 270) + ["tap A", "run 20"]                    # the start lever
    L += hm.teleport(7.5, 12.35, 90) + ["tap A", "run 300"]                   # the lift, before the checkpoint
    L += hm.dismiss() + hm.teleport(7.5, 9.0, 270) + hm.die() + hm.dismiss() + ["run 600"] + hm.dismiss()
    L += hm.teleport(7.5, 12.35, 90) + hm.act(400) + hm.dismiss() + ["run 240"]
    L += [f"expect8 {{g_state+{LEVEL}}} == 2 the lift came and took the player up"]
    t.run(L)


def test_trigger_waits_for_a_free_thread(t):
    """A room trigger entered while every script thread is busy fires when
    one is free, instead of being marked done and lost."""
    ev, trig = hm.event_id(1, 'drips'), hm.trigger_index(1, 'laundry')
    bit = f"{{g_state+{TRIG_FIRED + trig // 8}}}"
    L = hm.boot() + hm.dismiss() + hm.load_level(1) + ["run 300"] + hm.dismiss()
    for _ in range(hm.MAX_THREADS):
        L += hm.start_event(ev)
    L += hm.threads() + hm.teleport(2.5, 6.5, 0) + ["run 30", f"peek8 {bit}"]
    L += [f"poke8 {{s_th+{7 * hm.TH_SIZE + hm.TH_ACTIVE}}} 0", "run 30", f"peek8 {bit}"]
    v = t.run(L).values()
    active = v[0:16:2]
    t.check(all(active), f"the test did not fill the threads: {active}")
    t.check(not (v[16] >> (trig % 8)) & 1, "the trigger was marked fired with no thread to run it")
    t.check((v[17] >> (trig % 8)) & 1, "the trigger did not fire once a thread was free")


def test_one_thread_per_interaction(t):
    """A pressed twice on the hall clock starts its script once."""
    ev = hm.event_id(0, 'clock')
    L = hm.boot() + hm.dismiss()
    L += hm.teleport(8.5, 0.7, 270) + hm.act(60) + ["run 400"]                 # the cellar door: the library opens
    L += hm.teleport(2.0, 2.45, 270) + hm.act(40) + hm.act(30, 'B') + ["run 400"]   # the ledger
    L += hm.teleport(4.9, 6.5, 180) + ["tap A", "tap A", "run 4"] + hm.threads() + ["run 300"]
    L += [f"expect16 {{g_state+{KEYS}}} == 2 the cellar key"]
    v = t.run(L).values()
    n = sum(1 for a, e in zip(v[0:16:2], v[1:16:2]) if a and e == ev)
    t.check(n == 1, f"{n} threads run the clock's script")
