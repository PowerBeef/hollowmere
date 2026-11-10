#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Frame rate with the detail governor on: fps.py OUTDIR [--turn] [--only a,b] [--min FPS]
For each of the game's benchmark views (tests/views.py): settle, then count
the frames rendered over 180 vblanks (59.73 a second). --turn holds LEFT while
measuring, so the view sweeps round the room. Exits 1 when a view is below
--min (default: the game's MIN_FPS). Measured in mGBA, which may be faster
than a console at reading video memory."""
import os
import sys
import paths
import harness
import views as V

VBLANK_HZ = 16777216 / 280896


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    a = sys.argv[2:]
    turn, only, floor = False, None, getattr(V, 'MIN_FPS', 0)
    while a:
        if a[0] == '--turn': turn = True; a = a[1:]
        elif a[0] == '--only': only = a[1].split(','); a = a[2:]
        elif a[0] == '--min': floor = float(a[1]); a = a[2:]
        else: sys.exit(f"fps.py: unknown option {a[0]}\n{__doc__}")
    views = [v for v in V.VIEWS if not only or v[1] in only]
    if not views:
        sys.exit("fps.py: no such view")
    L = harness.boot() + harness.dismiss()
    level = 0
    for lv, n, x, y, d in views:
        if lv != level:
            L += harness.load_level(lv) + harness.dismiss()
            level = lv
        L += harness.teleport(x, y, d) + ["poke32 {g_govOff} 0"] + harness.dismiss() + ["run 120"] + harness.dismiss(0)
        L += [f"echo {n}", "peek32 {g_renderCount}", "peek32 {g_vblanks}"]
        if turn: L.append("hold LEFT")
        L += ["run 180", "hold -", "peek32 {g_renderCount}", "peek32 {g_vblanks}", "peek8 {g_quality}",
              "peek32 {g_profUpdate}", "peek32 {g_profRaw}", f"shot {out}/{n}.ppm"]
    r = harness.run(L, out, 'fps')
    rows = [(n, v) for n, v in r.sections() if len(v) >= 7]
    if len(rows) != len(views):
        print(f"fps.py: {len(views) - len(rows)} views gave no numbers", file=sys.stderr)
        return 1
    tot, slow = 0, []
    for n, (r0, v0, r1, v1, q, upd, raw) in rows:
        fps = (r1 - r0) * VBLANK_HZ / max(1, v1 - v0)
        tot += fps
        if fps < floor: slow.append(n)
        print(f"{n:>10} {fps:5.1f} fps  detail level {q}  update {upd:7d}  render {raw:7d}{'   BELOW %.1f' % floor if fps < floor else ''}")
    print(f"(timed in {harness.emulator()}: an emulator's model of the hardware. Nothing here has been run on a console, which may "
          f"read video memory more slowly.)")
    print(f"{'mean':>10} {tot / len(rows):5.1f} fps")
    if slow:
        print(f"fps.py: below {floor} fps at: {', '.join(slow)}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    harness.main(main)
