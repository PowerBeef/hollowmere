#!/usr/bin/env python3
"""Expand {symbol} / {symbol+off} in a harness script using the ELF symbol table."""
import re, subprocess, sys, os
import paths
syms = {}
for line in subprocess.check_output(['arm-none-eabi-nm', paths.ELF]).decode().splitlines():
    p = line.split()
    if len(p) == 3:
        syms[p[2]] = int(p[0], 16)
def rep(m):
    s = m.group(1)
    off = 0
    if '+' in s:
        s, o = s.split('+'); off = int(o, 0)
    return hex(syms[s] + off)
for line in open(sys.argv[1]):
    sys.stdout.write(re.sub(r'\{([A-Za-z_0-9+x]+)\}', rep, line))
