#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Frame rate with the detail governor on: fps.py OUTDIR [--turn] [--only a,b]
For each benchmark view: settle, then count rendered frames over 180 vblanks.
--turn holds LEFT while measuring (the view sweeps around the room)."""
import subprocess, sys, os
import paths
sys.path.insert(0, os.path.dirname(__file__))
src = open(os.path.join(os.path.dirname(__file__), 'bench.py')).read()
VIEWS = eval(src[src.index('VIEWS = ['):src.index(']\n', src.index('VIEWS = [')) + 1].split('=', 1)[1])

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
turn = '--turn' in sys.argv
only = None
if '--only' in sys.argv:
    only = sys.argv[sys.argv.index('--only') + 1].split(',')
views = [v for v in VIEWS if not only or v[1] in only]
boot = open(paths.BOOT).read()
L = [boot, "poke32 {g_debugCmd} 5", "run 2"]
level = 0
for lv, n, x, y, d in views:
    if lv != level:
        L += [f"poke32 {{g_debugA}} {lv}", "poke32 {g_debugCmd} 4", "run 420", "poke32 {g_debugCmd} 5", "run 2"]
        level = lv
    L += [f"poke32 {{g_debugA}} {int(x*256)}", f"poke32 {{g_debugB}} {int(y*256)}",
          f"poke32 {{g_debugC}} {int(d/360*65536) & 65535}", "poke32 {g_debugCmd} 2", "poke32 {g_govOff} 0", "run 6", "poke32 {g_debugCmd} 5",
          "run 120", "poke32 {g_debugCmd} 5", f"echo {n}", "peek32 {g_renderCount}", "peek32 {g_vblanks}"]
    if turn: L.append("hold LEFT")
    L += ["run 180", "hold -", "peek32 {g_renderCount}", "peek32 {g_vblanks}", "peek8 {g_quality}",
          "peek32 {g_profUpdate}", "peek32 {g_profRaw}", "peek32 {g_profStage}", "peek32 {g_profStage+4}", "peek32 {g_profStage+8}", "peek32 {g_profStage+12}", f"shot {out}/{n}.ppm"]
open(f"{out}/f.in", 'w').write('\n'.join(L) + '\n')
txt = subprocess.check_output(['python3', paths.tool('sym.py'), f"{out}/f.in"]).decode()
open(f"{out}/f.txt", 'w').write(txt)
res = subprocess.run([paths.HARNESS, paths.ROM, f"{out}/f.txt"], capture_output=True, text=True, timeout=900)
rows, cur = [], None
for l in res.stdout.split('\n'):
    l = l.strip()
    if not l: continue
    if '= ' not in l:
        if cur: rows.append(cur)
        cur = [l]
    else:
        cur.append(int(l.split('= ')[1]))
if cur: rows.append(cur)
tot = 0
for r in rows:
    if len(r) < 6: continue
    n, r0, v0, r1, v1, q = r[:6]
    fps = (r1 - r0) * 60.0 / max(1, v1 - v0)
    tot += fps
    ex = r[6:12] if len(r) >= 12 else []
    print(f"{n:>10} {fps:5.1f} fps  quality level {q}  update {ex[0] if ex else 0:7d} raw {ex[1] if ex else 0:7d}  3d {sum(ex[2:6]) if ex else 0:7d}")
k = len([r for r in rows if len(r) >= 6])
if k: print(f"{'mean':>10} {tot / k:5.1f} fps")
