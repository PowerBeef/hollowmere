#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run shots.py and print a compact profile table (cycles; 30 fps = 561k per frame)."""
import subprocess, sys
import paths
out = subprocess.run(['python3', paths.tool('shots.py')] + sys.argv[1:], capture_output=True, text=True).stdout
lines = [l for l in out.split('\n') if l.strip()]
rows, cur = [], None
for l in lines:
    if '= ' not in l:
        if cur: rows.append(cur)
        cur = [l.strip()]
    else:
        cur.append(int(l.split('= ')[1]))
if cur: rows.append(cur)
print(f"{'view':>9} {'occ':>6} {'world':>7} {'objs':>7} {'render':>7} {'props':>5} {'faces':>5} {'cull':>6} {'lod':>5} fps")
for r in rows:
    if len(r) < 8: continue
    name, occ, world, _, objs, frame = r[0], r[1], r[2], r[3], r[4], r[5]
    props, faces = r[7], r[8]
    fps = 30 if frame + 80000 < 561000 else 20
    cull, lod = r[12], r[-1]
    print(f"{name:>9} {occ:7d} {world:7d} {objs:7d} {frame:7d} {props:5d} {faces:5d} {cull:6d} {lod:5d} {fps}")
