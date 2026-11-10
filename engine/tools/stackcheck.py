#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Stack high-water mark during gameplay rendering: stackcheck.py OUTDIR
Runs the benchmark views (interrupts on) after clearing the free IWRAM
between the end of .bss and the live stack, then reports the deepest use."""
import subprocess, sys, os
import paths
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
subprocess.run(['python3', paths.tool('bench.py'), out], capture_output=True)
syms = {}
for line in subprocess.check_output(['arm-none-eabi-nm', paths.ELF]).decode().splitlines():
    p = line.split()
    if len(p) == 3: syms[p[2]] = int(p[0], 16)
be = syms['__bss_end']
lines = open(f"{out}/b.txt").read().split('\n')
noirq = "poke32 %#x 1" % syms['g_profNoIrq']
lines = [l.replace(noirq, "poke32 %#x 0" % syms['g_profNoIrq']) for l in lines]
idx = [i for i, l in enumerate(lines) if l.startswith('echo ')][0]
clear = ["poke32 %#x 0" % a for a in range(be, 0x03007C00, 4)]
lines = lines[:idx + 1] + clear + lines[idx + 1:]
lines.append("dump %#x %d %s/stack.bin" % (be, 0x03007F80 - be, out))
open(f"{out}/stk.txt", 'w').write('\n'.join(lines) + '\n')
subprocess.run([paths.HARNESS, paths.ROM, f"{out}/stk.txt"], capture_output=True, timeout=900)
b = open(f"{out}/stack.bin", 'rb').read()
i = 0
while i < len(b) and b[i] == 0: i += 1
print(f"stack: {len(b)} bytes free below 0x03007F80, deepest use {len(b) - i}, headroom {i}")
