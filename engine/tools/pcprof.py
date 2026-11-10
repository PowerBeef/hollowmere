#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Sampling profiler: pcprof.py OUTDIR LEVEL X Y DEG [frames]
Teleports to the view, samples the CPU's program counter every 1024 cycles
for a few frames and prints where the time goes, by function."""
import subprocess, sys, os, struct, bisect
import paths

out = sys.argv[1]
lv, x, y, d = int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
frames = int(sys.argv[6]) if len(sys.argv) > 6 else 12
_q = [int(v) for v in os.environ.get("PCQ", "147456,120,256").split(",")]
HD, BAND, LOD = _q[:3]
SPLIT, WHALF = (_q[3], _q[4]) if len(_q) > 4 else (0, 0)
os.makedirs(out, exist_ok=True)
boot = open(paths.BOOT).read()
L = [boot, "poke32 {g_debugCmd} 5", "run 2"]
if lv:
    L += [f"poke32 {{g_debugA}} {lv}", "poke32 {g_debugCmd} 4", "run 420", "poke32 {g_debugCmd} 5", "run 2"]
L += [f"poke32 {{g_debugA}} {int(x*256)}", f"poke32 {{g_debugB}} {int(y*256)}",
      f"poke32 {{g_debugC}} {int(d/360*65536) & 65535}", "poke32 {g_debugCmd} 2",
      "poke32 {g_govOff} 1", "poke32 {g_profNoIrq} 0", "poke32 {g_lodScale} 256", f"poke32 {{g_floorSplit}} {SPLIT}", f"poke32 {{g_wallHalfLh}} {WHALF}",
      f"poke32 {{g_halfDist}} {HD}", f"poke32 {{g_fullC0}} {120-BAND}", f"poke32 {{g_fullC1}} {120+BAND}", f"poke32 {{g_lodScale}} {LOD}", "run 20",
      "poke32 {g_debugCmd} 8", f"run {frames}", "poke32 {g_debugCmd} 9", "run 1",
      f"dump {{g_pcSamples}} 16388 {out}/pc.bin", f"shot {out}/view.ppm"]
open(f"{out}/p.in", 'w').write('\n'.join(L) + '\n')
txt = subprocess.check_output(['python3', paths.tool('sym.py'), f"{out}/p.in"]).decode()
open(f"{out}/p.txt", 'w').write(txt)
subprocess.run([paths.HARNESS, paths.ROM, f"{out}/p.txt"], capture_output=True, text=True, timeout=600)
raw = open(f"{out}/pc.bin", 'rb').read()
n = struct.unpack('<I', raw[:4])[0]
pcs = [struct.unpack('<I', raw[4 + 4 * i:8 + 4 * i])[0] - 4 for i in range(min(n, 4096))]
syms = []
for line in subprocess.check_output(['arm-none-eabi-nm', '-n', paths.ELF]).decode().splitlines():
    p = line.split()
    if len(p) == 3 and p[1] in 'tTwW':
        syms.append((int(p[0], 16), p[2]))
syms.sort()
addrs = [a for a, _ in syms]
hist = {}
for pc in pcs:
    pc &= ~1
    i = bisect.bisect_right(addrs, pc) - 1
    name = syms[i][1] if i >= 0 else '?'
    hist[name] = hist.get(name, 0) + 1
tot = len(pcs)
print(f"{tot} samples ({tot * 1024} cycles over {frames} frames)")
for name, c in sorted(hist.items(), key=lambda t: -t[1])[:40]:
    print(f"{c * 100.0 / tot:6.1f}%  {c:5d}  {name}")

# hot spots inside chosen functions: pcprof.py ... frames FUNC[,FUNC]
if len(sys.argv) > 7:
    want = sys.argv[7].split(',')
    for fn in want:
        base = [a for a, nme in syms if nme == fn]
        if not base: continue
        b = base[0]
        offs = {}
        for pc in pcs:
            pc &= ~1
            i = bisect.bisect_right(addrs, pc) - 1
            if i >= 0 and syms[i][1] == fn:
                o = (pc - b) & ~15
                offs[o] = offs.get(o, 0) + 1
        print(f"--- {fn} @ {b:#x}")
        for o, c in sorted(offs.items()):
            print(f"  +{o:#06x}  {c}")
