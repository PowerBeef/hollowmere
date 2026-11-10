#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Walks the critical path of the whole game with debug teleports and A presses,
taking screenshots and printing progress (level, keys, fuses, signal).
usage: playtest.py OUTDIR"""
import subprocess
import paths
import sys
import os

SP = os.path.abspath(sys.argv[1])
os.makedirs(SP, exist_ok=True)
lines = []


def cmd(s):
    lines.append(s)


def tp(x, y, deg):
    cmd(f"poke32 {{g_debugA}} {int(x * 256)}")
    cmd(f"poke32 {{g_debugB}} {int(y * 256)}")
    cmd(f"poke32 {{g_debugC}} {int(deg / 360 * 65536) & 65535}")
    cmd("poke32 {g_debugCmd} 2")
    cmd("run 8")


def quiet():
    cmd("poke32 {g_debugCmd} 5")
    cmd("run 2")


def act(frames=40, key='A'):
    cmd(f"tap {key}")
    cmd(f"run {frames}")


def state(tag):
    cmd(f"echo == {tag}")
    cmd("peek8 {g_state+4}")        # level
    cmd("peek16 {g_state+12}")      # keys
    cmd("peek8 {g_state+14}")       # fuses
    cmd("peek8 {g_state+15}")       # fusesPlaced
    cmd("peek8 {g_gameSignal}")


def shot(name):
    cmd(f"shot {SP}/pt_{name}.ppm")


boot = open(paths.BOOT).read().splitlines()
lines += boot
quiet()
state('L1 start')
shot('l1_start')
# ---------------- Chapter I: the house
tp(8.5, 0.7, 270); act(60); shot('l1_cellar_locked')
cmd("run 400"); shot('l1_lure')                 # the library door creaks open
tp(2.0, 2.45, 270); act(40); act(30, 'B')       # read the housekeeper's ledger
cmd("run 400")
tp(4.9, 6.5, 180); act(60); state('L1 key'); shot('l1_key')   # open the hall clock
cmd("run 120"); quiet()
tp(8.5, 0.7, 270); act(300); state('L1 exit')
quiet()
# ---------------- Chapter II: the cellars
cmd("run 240"); quiet()
state('L2 start'); shot('l2_start')
tp(2.9, 3.35, 270); act(40)            # fuse on the wine-cellar table
tp(3.35, 7.0, 180); act(40)            # boiler key on the laundry table
tp(8.45, 2.5, 0); act(80)              # unlock the boiler room
shot('l2_boiler_door')
tp(13.4, 2.45, 270); act(40)           # fuse behind the boiler
tp(2.0, 11.35, 90); act(40)            # fuse on the cold-room slab
quiet(); state('L2 fuses')
tp(13.0, 5.0, 0); act(60)              # fuse panel
state('L2 panel')
tp(11.4, 7.1, 270); act(200)           # start lever
quiet(); state('L2 power'); shot('l2_power')
tp(7.5, 12.35, 90); act(60)            # call the lift
quiet(); cmd("run 480"); quiet()
act(400); state('L2 exit')
quiet()
# ---------------- Chapter III: the wards
cmd("run 240"); quiet()
state('L3 start'); shot('l3_start')
tp(2.25, 7.35, 90); act(40)            # suite key on the nursery stool
tp(10.5, 4.45, 90); act(80)            # unlock the doctor's suite
shot('l3_suite')
tp(13.05, 5.9, 270); act(60)           # attic key on the desk
quiet(); state('L3 attic key')
tp(0.6, 4.5, 180); act(300); state('L3 exit')
quiet()
# ---------------- Chapter IV: the chapel
cmd("run 240")
state('L4 start'); shot('l4_start')
act(10, 'SELECT')                      # light off
tp(10.6, 2.25, 270); cmd("run 20"); shot('l4_behind')
act(400); state('L4 lantern')
shot('l4_end')

open(os.path.join(SP, 'pt.in'), 'w').write('\n'.join(lines) + '\n')
txt = subprocess.check_output(['python3', paths.tool('sym.py'), os.path.join(SP, 'pt.in')]).decode()
open(os.path.join(SP, 'pt.txt'), 'w').write(txt)
res = subprocess.run([paths.HARNESS, paths.ROM, os.path.join(SP, 'pt.txt')],
                     capture_output=True, text=True, timeout=900)
out = res.stdout.split('\n')
tag = None
vals = []
for l in out:
    if l.startswith('== '):
        if tag:
            print(f"{tag:14s} level={vals[0]} keys={vals[1]:#x} fuses={vals[2]} placed={vals[3]} signal={vals[4]}")
        tag, vals = l[3:], []
    elif '= ' in l:
        vals.append(int(l.split('= ')[1]))
if tag and len(vals) >= 5:
    print(f"{tag:14s} level={vals[0]} keys={vals[1]:#x} fuses={vals[2]} placed={vals[3]} signal={vals[4]}")
print(res.stderr[-1500:])
