#!/usr/bin/env python3
"""Screenshots at chosen spots: shot.py OUTDIR LEVEL:X:Y:DEG[:name] ...  (full quality, 3x PNG)"""
import subprocess, sys, os
import paths
from PIL import Image
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
boot = open(paths.BOOT).read()
L = [boot, "poke32 {g_debugCmd} 5", "run 2"]
level = 0
names = []
for i, a in enumerate(sys.argv[2:]):
    p = a.split(':')
    lv, x, y, d = int(p[0]), float(p[1]), float(p[2]), float(p[3])
    n = p[4] if len(p) > 4 else f"s{i}"
    if lv != level:
        L += [f"poke32 {{g_debugA}} {lv}", "poke32 {g_debugCmd} 4", "run 420", "poke32 {g_debugCmd} 5", "run 2"]
        level = lv
    L += [f"poke32 {{g_debugA}} {int(x*256)}", f"poke32 {{g_debugB}} {int(y*256)}",
          f"poke32 {{g_debugC}} {int(d/360*65536) & 65535}", "poke32 {g_debugCmd} 2", "run 6", "poke32 {g_debugCmd} 5",
          "poke32 {g_govOff} 1", "poke32 {g_profNoIrq} 0", "poke32 {g_lodScale} 256", "poke32 {g_floorSplit} 0",
          "poke32 {g_wallHalfLh} 0", "poke32 {g_halfDist} 147456", "poke32 {g_fullC0} 0", "poke32 {g_fullC1} 240",
          "run 24", f"shot {out}/{n}.ppm"]
    names.append(n)
open(f"{out}/s.in", 'w').write('\n'.join(L) + '\n')
txt = subprocess.check_output(['python3', paths.tool('sym.py'), f"{out}/s.in"]).decode()
open(f"{out}/s.txt", 'w').write(txt)
subprocess.run([paths.HARNESS, paths.ROM, f"{out}/s.txt"], capture_output=True, text=True, timeout=600)
for n in names:
    im = Image.open(f"{out}/{n}.ppm")
    im.resize((720, 480), Image.NEAREST).save(f"{out}/{n}.png")
print(' '.join(f"{out}/{n}.png" for n in names))
