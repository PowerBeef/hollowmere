# SPDX-License-Identifier: MIT
"""Regression tests: lights, the Sister's path finding, doors."""
import hm
from hm import CR_WAIT

GRID = 64 * 64          # the light grid: 64 x 64 half-tile cells, light in the low five bits
LIGHT_GRID = 0x02000000  # g_lightgrid (engine.h: the start of EWRAM)


def test_lantern_leaves_no_light_behind(t):
    """The light of the Sister's lantern goes with her: where she has walked,
    and after she is gone, the light grid shows only what the lamps give."""
    def dump(tag):
        return [f"dump {LIGHT_GRID:#x} {GRID} {{out}}/{tag}.bin"]

    def grid(tag):
        return [b & 31 for b in open(f"{t.out}/{tag}.bin", 'rb').read()]
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + [f"poke8 {{g_player+{hm.PL_FROZEN}}} 1"]     # (held still: she takes no notice)
    for k in range(10):
        L += ["run 7"] + dump(f"lamps{k}")                   # the lamps alone, flickering
    L += hm.spawn(3.0, hm.CR_PATROL, settle=0)
    for k in range(4):
        L += ["run 180", f"expect8 {{g_cr}} == {hm.CR_PATROL} she is on her rounds"] + dump(f"walk{k}") + ["peeks32 {g_cr+4}", "peeks32 {g_cr+8}"]
    L += hm.dismiss() + ["run 30"] + dump('gone')
    v = t.run(L).values()
    most = [max(c) for c in zip(*(grid(f"lamps{k}") for k in range(10)))]
    moved = set()
    for k in range(4):
        x, y = v[2 * k] >> 15, v[2 * k + 1] >> 15            # where she is, in light cells; the lantern reaches seven
        moved.add((x, y))
        lit = grid(f"walk{k}")
        trail = [i for i in range(GRID) if lit[i] > most[i] and max(abs((i & 63) - x), abs((i >> 6) - y)) > 7]
        t.check(not trail, f"after {3 * (k + 1)} s: {len(trail)} cells out of the lantern's reach are lit by it: a trail")
    t.check(len(moved) >= 3, "she did not walk")
    left = [i for i, (a, b) in enumerate(zip(grid('gone'), most)) if a > b]
    t.check(not left, f"{len(left)} cells are still lit after she is gone")


def test_lamps_flicker_at_the_same_rate_at_15_fps(t):
    """The dining-room candles flicker ten times a second at 20 frames a
    second and at 15."""
    cell = (15 << 6) | 23                                    # the light cell at the candles (11.5, 7.5)
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + hm.teleport(11.5, 9.3, 90)      # facing the wall: a quick frame
    for vblanks in (3, 4):                                    # per frame: 20 and 15 frames a second
        L += [f"poke8 {{g_minFrames}} {vblanks}", "run 120", "peek32 {g_renderCount}"]
        for _ in range(600):
            L += ["run 1", f"peek8 {LIGHT_GRID + cell:#x}"]
        L += ["peek32 {g_renderCount}"]
    v = t.run(L).values()
    rate = []
    for k in range(2):
        part = v[k * 602:(k + 1) * 602]
        frames, levels = part[-1] - part[0], [x & 31 for x in part[1:-1]]
        changes = sum(1 for a, b in zip(levels, levels[1:]) if a != b)
        rate.append((frames / 10, changes / 10))
    (fps20, f20), (fps15, f15) = rate
    t.check(19 <= fps20 <= 20.5 and 14 <= fps15 <= 15.5, f"frame rates {fps20} and {fps15}: the test did not set them")
    t.check(f20 >= 5 and f15 >= 5, f"the candles change {f20} and {f15} times a second: no flicker to compare")
    t.check(abs(f20 - f15) <= 0.2 * max(f20, f15), f"the candles change {f20} times a second at 20 fps and {f15} at 15 fps")


def test_door_locked_after_she_chose_her_way(t):
    """Chasing the player into the drawing room, the Sister heads for its
    corridor door. Locked before she gets there, the door stays shut and she
    comes round through the hall instead of giving up."""
    CORRIDOR_DOOR, HALL_DOOR, DS_LOCKED = 5, 8, 4          # doors (2,5,N) and (4,7,W) of chapter I

    def door(i):
        return f"{{g_doors+{16 * i + 4}}}"
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss()
    L += [f"expect8 {{g_doors+{16 * CORRIDOR_DOOR}}} == 2 door {CORRIDOR_DOOR} is the drawing room's", f"expect8 {{g_doors+{16 * HALL_DOOR + 1}}} == 7 door {HALL_DOOR} is the hall's"]
    L += hm.teleport(12.5, 4.5, 180) + hm.spawn(6.0, hm.CR_CHASE, settle=2)        # she stands in the corridor at (6.5, 4.5)
    L += hm.teleport(1.5, 5.5, 90, settle=10)                                      # the player: in the drawing room, by that door
    L += [f"poke8 {{g_state+{64 + CORRIDOR_DOOR}}} {DS_LOCKED}", "run 600"]
    L += [f"peek16 {door(CORRIDOR_DOOR)}", f"peek16 {door(HALL_DOOR)}", "peeks32 {g_cr+4}", "peeks32 {g_cr+8}", f"peek16 {{g_state+{hm.DEATHS}}}"]
    shut, hall, x, y, deaths = t.run(L).values()
    t.check(shut == 0, "she opened the locked door")
    t.check(hall > 0 and (deaths or (x < 4 << 16 and y >= 5 << 16)),
            f"she did not come round through the hall (hall door {hall}, she is at {x / 65536:.1f}, {y / 65536:.1f}, deaths {deaths})")
