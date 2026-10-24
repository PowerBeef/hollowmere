#!/usr/bin/env python3
"""Deterministic screenshots for A/B renderer comparisons:
abshot.py ROM ELF OUTDIR [--only a,b] [poke lines with @ for spaces...]
The game logic is frozen (g_dbgFreeze) after each level loads, so each view
is a pure function of the level's start state, the camera and the knobs."""
import subprocess, sys, os, re
import paths
src = open(os.path.join(os.path.dirname(__file__), 'bench.py')).read()
VIEWS = eval(src[src.index('VIEWS = ['):src.index(']\n', src.index('VIEWS = [')) + 1].split('=', 1)[1])
if os.environ.get('ABVIEWS'):      # "level,name,x,y,deg;..."
    VIEWS = [(int(a), b, float(c), float(d), float(e)) for a, b, c, d, e in
             (v.split(',') for v in os.environ['ABVIEWS'].split(';'))]
rom, elf, out = sys.argv[1], sys.argv[2], sys.argv[3]
a = sys.argv[4:]
only = None
if '--only' in a:
    i = a.index('--only'); only = a[i + 1].split(','); a = a[:i] + a[i + 2:]
extra = [e.replace('@', ' ') for e in a]
os.makedirs(out, exist_ok=True)
syms = {}
for line in subprocess.check_output(['arm-none-eabi-nm', elf]).decode().splitlines():
    p = line.split()
    if len(p) == 3: syms[p[2]] = int(p[0], 16)
def S(t):
    def rep(m):
        s = m.group(1); off = 0
        if '+' in s: s, o = s.split('+'); off = int(o, 0)
        return hex(syms[s] + off)
    return re.sub(r'\{([A-Za-z_0-9+x]+)\}', rep, t)
boot = open(paths.BOOT).read()
L = [boot, "poke32 {g_debugCmd} 5", "run 2"]
level = -1
for lv, n, x, y, d in VIEWS:
    if only and n not in only: continue
    if lv != level:
        L += ["poke32 {g_dbgFreeze} 0", f"poke32 {{g_debugA}} {lv}", "poke32 {g_debugCmd} 4", "run 420",
              "poke32 {g_debugCmd} 5", "run 2", "poke32 {g_dbgFreeze} 4000", "run 2"]
        level = lv
    L += [f"poke32 {{g_debugA}} {int(x*256)}", f"poke32 {{g_debugB}} {int(y*256)}",
          f"poke32 {{g_debugC}} {int(d/360*65536) & 65535}", "poke32 {g_debugCmd} 2",
          "poke32 {g_govOff} 1", "poke32 {g_profNoIrq} 0", "poke32 {g_lodScale} 256", "poke32 {g_floorSplit} 0",
          "poke32 {g_wallHalfLh} 0", "poke32 {g_halfDist} 147456", "poke32 {g_fullC0} 0", "poke32 {g_fullC1} 240", "poke32 {g_vhalf} 0"] + extra + \
         ["run 12", f"shot {out}/{n}.ppm"]
open(f"{out}/ab.txt", 'w').write(S('\n'.join(L) + '\n'))
subprocess.run([paths.HARNESS, rom, f"{out}/ab.txt"], capture_output=True, text=True, timeout=900)
