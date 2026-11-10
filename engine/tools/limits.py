# SPDX-License-Identifier: MIT
"""The engine's limits on content, and how the tools refuse what exceeds them.

The numbers live in engine/src/limits.h (the C code, the linker script and
these tools all read that one file). Here they are attributes of this module:
limits.MAX_DOORS, limits.MAP_W...

check(ok, where, what) raises ContentError("where: what") when ok is false.
The asset build catches it and prints that one line; `where` names the level,
event or model so the author can find the thing. (Not `assert`: python3 -O
turns asserts off, and a build that skips its checks ships broken data.)"""
import os
import re

HEADER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'limits.h')


class ContentError(Exception):
    """Content the engine cannot handle; str() is one line for the author."""


def check(ok, where, what):
    if not ok:
        raise ContentError(f"{where}: {what}")


def in_range(v, lo, hi, where, what):
    """v must be an integer in lo..hi; returns it."""
    check(isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi, where, f"{what} is {v!r}: it must be a whole number from {lo} to {hi}")
    return v


def load(path=HEADER):
    d = {}
    for line in open(path):
        m = re.match(r'#define\s+(\w+)\s+(-?\d+)\b', line)
        if m:
            d[m.group(1)] = int(m.group(2))
    if not d:
        raise RuntimeError(f"no limits found in {path}")
    return d


ALL = load()
globals().update(ALL)
