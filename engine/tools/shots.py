#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Take screenshots from a list of camera poses: shots.py OUTDIR name x y deg [name x y deg ...]
Writes OUTDIR/sheet.png (contact sheet, 2x) and prints profiling counters."""
import subprocess, sys, os
import paths
from PIL import Image, ImageDraw
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
args = sys.argv[2:]
poses = [(args[i], float(args[i+1]), float(args[i+2]), float(args[i+3])) for i in range(0, len(args), 4)]
boot = open(paths.BOOT).read()
L = [boot, "poke32 {g_debugCmd} 5", "run 2"]
for n, x, y, d in poses:
    L += [f"poke32 {{g_debugA}} {int(x*256)}", f"poke32 {{g_debugB}} {int(y*256)}",
          f"poke32 {{g_debugC}} {int(d/360*65536) & 65535}", "poke32 {g_debugCmd} 2", "run 40",
          f"shot {out}/{n}.ppm", f"echo {n}", "peek32 {g_profStage}", "peek32 {g_profStage+4}", "peek32 {g_profStage+8}", "peek32 {g_profStage+12}", "peek32 {g_profRaw}"] + [f"peek32 {{g_objPub+{4*k}}}" for k in range(20)] + ["peek32 {g_lodScale}"]
open(f"{out}/s.in", 'w').write('\n'.join(L) + '\n')
txt = subprocess.check_output(['python3', paths.tool('sym.py'), f"{out}/s.in"]).decode()
open(f"{out}/s.txt", 'w').write(txt)
res = subprocess.run([paths.HARNESS, paths.ROM, f"{out}/s.txt"], capture_output=True, text=True, timeout=300)
print(res.stdout, res.stderr[-2000:])
ims = [Image.open(f"{out}/{n}.ppm").resize((480, 320), Image.NEAREST) for n, *_ in poses]
cols = 2 if len(ims) > 1 else 1
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (480 * cols, 330 * rows), (40, 40, 40))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * 480, (i // cols) * 330))
    ImageDraw.Draw(sheet).text(((i % cols) * 480 + 4, (i // cols) * 330 + 2), poses[i][0], fill=(255, 255, 0))
sheet.save(f"{out}/sheet.png")
