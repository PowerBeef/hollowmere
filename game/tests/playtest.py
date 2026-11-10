#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Plays Hollowmere's critical path from power-on to the ending with debug
teleports and A presses, checking progress at every stage (level, keys,
fuses), and takes screenshots along the way: playtest.py OUTDIR
Exits 1 when a stage is not reached."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'engine', 'tools'))
import paths  # noqa: E402
import harness  # noqa: E402
from hm import LEVEL, KEYS, FUSES, PLACED, act, state, teleport as tp, dismiss as quiet  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    L = []

    def shot(name):
        L.append(f"shot {out}/pt_{name}.ppm")

    def want(tag, level, keys=None, fuses=None, placed=None):
        L.extend(state(tag))
        L.append(f"expect8 {{g_state+{LEVEL}}} == {level} {tag}: level")
        if keys is not None: L.append(f"expect16 {{g_state+{KEYS}}} == {keys} {tag}: keys")
        if fuses is not None: L.append(f"expect8 {{g_state+{FUSES}}} == {fuses} {tag}: fuses carried")
        if placed is not None: L.append(f"expect8 {{g_state+{PLACED}}} == {placed} {tag}: fuses placed")

    L += harness.boot() + quiet()
    want('I start', 0, 0); shot('l1_start')
    # ---------------- Chapter I: the house
    L += tp(8.5, 0.7, 270) + act(60); shot('l1_cellar_locked')
    L += ["run 400"]; shot('l1_lure')                       # the library door creaks open
    L += tp(2.0, 2.45, 270) + act(40) + act(30, 'B')        # read the housekeeper's ledger
    L += ["run 400"]
    L += tp(4.9, 6.5, 180) + act(60); want('I key', 0, 0x2); shot('l1_key')   # the hall clock
    L += ["run 120"] + quiet()
    L += tp(8.5, 0.7, 270) + act(300) + quiet()
    # ---------------- Chapter II: the cellars
    L += ["run 240"] + quiet()
    want('II start', 1, 0, 0, 0); shot('l2_start')
    L += tp(2.9, 3.35, 270) + act(40)            # fuse on the wine-cellar table
    L += tp(3.35, 7.0, 180) + act(40)            # boiler key on the laundry table
    L += tp(8.45, 2.5, 0) + act(80)              # unlock the boiler room
    shot('l2_boiler_door')
    L += tp(13.4, 2.45, 270) + act(40)           # fuse behind the boiler
    L += tp(2.0, 11.35, 90) + act(40)            # fuse on the cold-room slab
    L += quiet(); want('II fuses', 1, 0x4, 3, 0)
    L += tp(13.0, 5.0, 0) + act(60)              # fuse panel
    want('II panel', 1, 0x4, 0, 3)
    L += tp(11.4, 7.1, 270) + act(200)           # start lever
    L += quiet(); want('II power', 1, 0x4, 0, 3); shot('l2_power')
    L += tp(7.5, 12.35, 90) + act(60)            # call the lift
    L += quiet() + ["run 480"] + quiet()
    L += act(400) + quiet()
    # ---------------- Chapter III: the wards
    L += ["run 240"] + quiet()
    want('III start', 2, 0); shot('l3_start')
    L += tp(2.25, 7.35, 90) + act(40)            # suite key on the nursery stool
    L += tp(10.5, 4.45, 90) + act(80)            # unlock the doctor's suite
    shot('l3_suite')
    L += tp(13.05, 5.9, 270) + act(60)           # attic key on the desk
    L += quiet(); want('III attic key', 2, 0x18)
    L += tp(0.6, 4.5, 180) + act(300) + quiet()
    # ---------------- Chapter IV: the chapel
    L += ["run 240"]
    want('IV start', 3, 0); shot('l4_start')
    L += act(10, 'SELECT')                       # light off
    L += tp(10.6, 2.25, 270) + ["run 20"]; shot('l4_behind')
    L += act(400)
    L += state('IV lantern') + ["expect8 {g_gameSignal} == 3 the ending was not reached"]
    shot('l4_end')

    r = harness.run(L, out, 'playtest', ok=(0, 1))
    for tag, v in r.sections():
        if len(v) >= 5:
            print(f"{tag:14s} level={v[0]} keys={v[1]:#x} fuses={v[2]} placed={v[3]} signal={v[4]}")
    for f in r.failures():
        print(f)
    return 1 if r.code else 0


if __name__ == '__main__':
    harness.main(main)
