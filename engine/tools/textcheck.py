#!/usr/bin/env python3
"""Checks that every in-game message, sign and objective fits the HUD:
messages wrap to at most two lines of 236 px, objectives to one."""
import sys, os, importlib
import paths
import font, story
gt = font.glyph_table()


def width(s):
    w = sum((gt[c][0] if c in gt else 3) + 1 for c in s)
    return w - 1 if s else 0


def msg_lines(s):
    if width(s) <= 224:
        return [s]
    n = len(s)
    best = -1
    i = j = n // 2
    while i > 0 or j < n:
        if j < n and s[j] == ' ':
            best = j; break
        if i > 0 and s[i] == ' ':
            best = i; break
        i -= 1; j += 1
    if best < 0:
        best = n // 2
    return [s[:best], s[best + 1:]]


bad = 0
def check_msg(where, s):
    global bad
    for ln in msg_lines(s):
        if width(ln) > 236:
            print(f"TOO WIDE ({width(ln)} px) {where}: {ln!r}"); bad += 1


def check_obj(where, s):
    global bad
    if width(s) > 232:
        print(f"OBJECTIVE TOO WIDE ({width(s)} px) {where}: {s!r}"); bad += 1


from manifest import LEVELS
for ln in LEVELS:
    M = importlib.import_module(ln)
    for ev, acts in M.EVENTS.items():
        for a in acts:
            if a[0] == 'msg':
                check_msg(f"{ln}/{ev}", a[1])
            elif a[0] == 'objective':
                check_obj(f"{ln}/{ev}", a[1])
    for k, op in getattr(M, 'EDGES', {}).items():
        if 'sign' in op:
            check_msg(f"{ln} sign {k}", op['sign'])
    for p in M.PROPS:
        if 'inter' in p and p['inter'][0] == 'sign':
            check_msg(f"{ln} prop sign {p['model']}", p['inter'][1])
for i, t in enumerate(story.LOCK_HINTS):
    check_msg(f"lock hint {i}", t)
for nm, t in story.FIXED:
    if nm.startswith('M_'):
        check_msg(nm, t)
print("text check:", "OK" if not bad else f"{bad} problems")
