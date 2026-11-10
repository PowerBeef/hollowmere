# SPDX-License-Identifier: MIT
"""Regression tests: the Night Sister's animations. Each reads the frame of
her sprite sheets the game drew (g_crFrame) while she is put through a state,
and checks that the pictures of that state play, in order."""
import os
import re

import paths
import hm

TIMER, GOAL_X, GOAL_Y = 34, 16, 20          # Creature: timer (s16), goalX, goalY


def sheets():
    """{'IDLE': first frame, ...} and the number of frames, from the generated assets.h."""
    text = open(os.path.join(paths.GEN, 'assets.h')).read()
    first = {m.group(1): int(m.group(2)) for m in re.finditer(r'#define CRF_(\w+) (\d+)', text)}
    return first, int(re.search(r'#define CR_NFRAMES (\d+)', text).group(1))


def watch(frames, step=2):
    L = []
    for _ in range(frames // step):
        L += [f"run {step}", "peek16 {g_crFrame}"]
    return L


def phases(values, first, count, per_view):
    """The phases (0..per_view-1) of the frames in values that belong to the block starting at `first`."""
    return [(v - first) % per_view for v in values if first <= v < first + count]


def changes(seq):
    """seq without immediate repeats."""
    return [v for i, v in enumerate(seq) if i == 0 or v != seq[i - 1]]


def test_she_breathes_and_looks_about(t):
    """Standing on her rounds she used to be one still picture, and another
    while searching. Standing now plays a six-picture breath, searching an
    eight-picture turn of the head and lantern."""
    F, _ = sheets()
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + [f"poke8 {{g_player+{hm.PL_FROZEN}}} 1"]      # (held still, the player is no business of hers)
    L += hm.teleport(12.5, 4.5, 180) + hm.spawn(4.0, hm.CR_PATROL) + [f"poke16 {{g_cr+{TIMER}}} 900", "echo idle"] + watch(200)
    L += [f"poke8 {{g_cr+{hm.CR_STATE}}} {hm.CR_INVESTIGATE}", f"poke16 {{g_cr+{TIMER}}} 900", "run 4", "echo search"] + watch(320)
    parts = dict(t.run(L).sections())
    idle = phases(parts['idle'], F['IDLE'], 48, 6)
    search = phases(parts['search'], F['SEARCH'], 64, 8)
    t.check(len(idle) == len(parts['idle']), f"standing on her rounds she is drawn from frames {sorted(set(parts['idle']))}, not all idle ones")
    t.check(len(set(idle)) == 6, f"her breath plays phases {sorted(set(idle))} of 6")
    t.check(len(search) == len(parts['search']), f"searching she is drawn from frames {sorted(set(parts['search']))}, not all search ones")
    t.check(len(set(search)) == 8, f"her look around plays phases {sorted(set(search))} of 8")


def test_she_rises_from_prayer_and_kneels_again(t):
    """At prayer she rocks; when she stirs she gets up through six pictures
    (she used to pop to her feet), stands, and kneels again through the same
    six backwards."""
    F, _ = sheets()
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss()
    L += hm.teleport(12.5, 4.5, 180) + hm.spawn(4.0, hm.CR_PRAY) + hm.teleport(1.5, 1.5, 0)      # the player well out of her sight
    L += ["echo kneel"] + watch(240) + [f"poke16 {{g_cr+{TIMER}}} 2", "echo stir"] + watch(260, step=1) + ["peek8 {g_cr}"]
    parts = dict(t.run(L).sections())
    kneel = phases(parts['kneel'], F['KNEEL'], 32, 4)
    t.check(len(kneel) == len(parts['kneel']) and len(set(kneel)) == 4, f"kneeling she plays phases {sorted(set(kneel))} of 4 (frames {sorted(set(parts['kneel']))})")
    stir, state = parts['stir'][:-1], parts['stir'][-1]
    t.check(state == hm.CR_PRAY, f"she left her prayer (state {state}): the test measured nothing")
    kinds = changes(['kneel' if F['KNEEL'] <= v < F['RISE'] else 'rise' if F['RISE'] <= v < F['DOOR'] else 'stand' if F['IDLE'] <= v < F['SEARCH'] else '?'
                     for v in stir])
    t.check(kinds[-4:] == ['rise', 'stand', 'rise', 'kneel'] and kinds[:-4] in ([], ['kneel']), f"stirring, she goes through {kinds}")
    rise = changes(phases(stir, F['RISE'], 48, 6))
    t.check(rise == [0, 1, 2, 3, 4, 5, 5, 4, 3, 2, 1, 0] or rise == [0, 1, 2, 3, 4, 5, 4, 3, 2, 1, 0],
            f"getting up and down again plays the pictures {rise}")


def test_she_pushes_the_door_she_opens(t):
    """Opening a door she used to stand in front of it as if idle while it
    swung. Her free hand now goes out to it: four pictures, in order."""
    F, _ = sheets()
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss()
    L += hm.teleport(12.5, 4.5, 180) + hm.spawn(6.0, hm.CR_CHASE)           # she stands in the corridor at (6.5, 4.5)
    L += hm.teleport(1.5, 5.5, 90, settle=10) + ["echo chase"] + watch(400, step=1)       # the player in the drawing room, behind its closed door
    v = dict(t.run(L).sections())['chase']
    door = changes(phases(v, F['DOOR'], 32, 4))
    t.check(door[:4] == [0, 1, 2, 3], f"at the door she plays the pictures {door} (expected 0, 1, 2, 3)")


def test_the_lunge_has_eight_pictures(t):
    """The lunge that ends a chase was three pictures over a second and a half; it is eight."""
    F, n = sheets()
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + hm.spawn(1.0, hm.CR_CHASE, settle=0) + ["echo lunge"] + watch(140, step=1)
    v = dict(t.run(L).sections())['lunge']
    lunge = changes([x - F['ATTACK'] for x in v if F['ATTACK'] <= x < n])
    t.check(lunge == list(range(8)), f"the lunge plays the pictures {lunge}")
