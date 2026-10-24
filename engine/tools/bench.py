#!/usr/bin/env python3
"""Fixed-view benchmark across all floors: bench.py OUTDIR [--lod N] [--only name,name]
Prints per view the render stage costs (cycles) and writes OUTDIR/bench.png.
20 fps = 3 vblanks = 842k cycles per frame (minus interrupts and game updates)."""
import subprocess, sys, os
import paths
from PIL import Image, ImageDraw

RUNF = int(os.environ.get("RUNF", "30"))
VIEWS = [
    # level, name, x, y, deg
    (0, 'hall', 6.30, 10.20, 285), (0, 'stairs', 5.6, 8.9, 10), (0, 'drawing', 3.60, 5.30, 140),
    (0, 'dining', 9.40, 9.60, 320), (0, 'library', 3.60, 3.60, 225), (0, 'kitchen', 7.6, 3.4, 300),
    (0, 'corridor', 0.5, 4.5, 0),
    (1, 'passage', 7.5, 2.6, 90), (1, 'generator', 9.5, 8.6, 320),
    (2, 'ward', 4.5, 3.6, 270), (2, 'nursery', 3.6, 5.4, 135), (2, 'study', 12.6, 8.6, 290),
    (3, 'chapel', 10.9, 7.6, 270), (3, 'boxroom', 4.3, 1.2, 190),
]


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    lod = 256
    only = None
    knobs = ["poke32 {g_profNoIrq} 1", "poke32 {g_floorSplit} 0", "poke32 {g_wallHalfLh} 0", f"poke32 {{g_halfDist}} {0x24000}",
             "poke32 {g_fullC0} 0", "poke32 {g_fullC1} 240", "poke32 {g_vhalf} 0"]
    a = sys.argv[2:]
    while a:
        if a[0] == '--lod': lod = int(a[1]); a = a[2:]
        elif a[0] == '--only': only = a[1].split(','); a = a[2:]
        elif a[0] == '--split': knobs.append(f"poke32 {{g_floorSplit}} {int(a[1])}"); a = a[2:]
        elif a[0] == '--whalf': knobs.append(f"poke32 {{g_wallHalfLh}} {int(a[1])}"); a = a[2:]
        elif a[0] == '--hd': knobs.append(f"poke32 {{g_halfDist}} {int(float(a[1]) * 65536)}"); a = a[2:]
        elif a[0] == '--band': knobs += [f"poke32 {{g_fullC0}} {120 - int(a[1])}", f"poke32 {{g_fullC1}} {120 + int(a[1])}"]; a = a[2:]
        elif a[0] == '--vhalf': knobs.append(f"poke32 {{g_vhalf}} {int(a[1])}"); a = a[2:]
        else: a = a[1:]
    views = [v for v in VIEWS if not only or v[1] in only]
    boot = open(paths.BOOT).read()
    L = [boot, "poke32 {g_debugCmd} 5", "run 2"]
    level = 0
    for lv, n, x, y, d in views:
        if lv != level:
            L += [f"poke32 {{g_debugA}} {lv}", "poke32 {g_debugCmd} 4", "run 420", "poke32 {g_debugCmd} 5", "run 2"]
            level = lv
        L += [f"poke32 {{g_debugA}} {int(x*256)}", f"poke32 {{g_debugB}} {int(y*256)}",
              f"poke32 {{g_debugC}} {int(d/360*65536) & 65535}", "poke32 {g_debugCmd} 2",
              "poke32 {g_govOff} 1", f"poke32 {{g_lodScale}} {lod}"] + knobs + [f"run {RUNF}",
              f"shot {out}/{n}.ppm", f"echo {n}",
              "peek32 {g_profStage}", "peek32 {g_profStage+4}", "peek32 {g_profStage+8}", "peek32 {g_profStage+12}", "peek32 {g_profRaw}",
              "peek32 {g_profUpdate}", "peek32 {g_profIrq}",
              "peek32 {g_objPub+4}", "peek32 {g_objPub+8}", "peek32 {g_objPub+12}", "peek32 {g_lodScale}"]
    open(f"{out}/b.in", 'w').write('\n'.join(L) + '\n')
    txt = subprocess.check_output(['python3', paths.tool('sym.py'), f"{out}/b.in"]).decode()
    open(f"{out}/b.txt", 'w').write(txt)
    res = subprocess.run([paths.HARNESS, paths.ROM, f"{out}/b.txt"], capture_output=True, text=True, timeout=600)
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
    print(f"{'view':>10} {'cast':>6} {'fl+wl':>6} {'occ':>6} {'objs':>6} {'3d':>7} {'render':>7} {'update':>6} {'irq':>5} {'props':>5} {'faces':>5} {'cols':>5} {'lod':>4}")
    tot = [0] * 6
    k = 0
    for r in rows:
        if len(r) < 12: continue
        n, cast, flo, wal, objs, rend, upd, irq, props, faces, cols, lodv = r[:12]
        v3 = cast + flo + wal + objs
        for i, v in enumerate((cast, flo, wal, objs, v3, rend)): tot[i] += v
        k += 1
        print(f"{n:>10} {cast:6d} {flo:6d} {wal:6d} {objs:6d} {v3:7d} {rend:7d} {upd:6d} {irq:5d} {props:5d} {faces:5d} {cols:5d} {lodv:4d}")
    k = max(1, k)
    print(f"{'mean':>10} " + ' '.join(f"{t // k:6d}" for t in tot[:4]) + f" {tot[4] // k:7d} {tot[5] // k:7d}")
    if res.returncode:
        print(res.stderr[-2000:])
    ims = []
    for lv, n, *_ in views:
        p = f"{out}/{n}.ppm"
        if os.path.exists(p):
            ims.append((n, Image.open(p).resize((480, 320), Image.NEAREST)))
    if ims:
        cols = 2
        rws = (len(ims) + 1) // 2
        sheet = Image.new('RGB', (480 * cols, 330 * rws), (40, 40, 40))
        for i, (n, im) in enumerate(ims):
            sheet.paste(im, ((i % cols) * 480, (i // cols) * 330))
            ImageDraw.Draw(sheet).text(((i % cols) * 480 + 4, (i // cols) * 330 + 2), n, fill=(255, 255, 0))
        sheet.save(f"{out}/bench.png")


main()
