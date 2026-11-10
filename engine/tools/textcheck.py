#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks every string of the game against the code that draws it, and exits 1
when one does not fit: textcheck.py

  messages and signs    hud_message: one line up to 224 px, else two halves
                        split at the space nearest the middle, each at most
                        236 px and 127 characters
  objectives            one HUD line of 232 px
  every string          ASCII with a glyph for each character

The rules mirror engine/src/hud.c and engine/src/gfx.c. A game adds the rules
of its own screens in tests/textrules.py: check(T), with this module as T."""
import importlib
import sys
import paths
import font
import story
from manifest import LEVELS

gt = font.glyph_table()
problems = []


def bad(where, what, s):
    problems.append(f"{where}: {what}: {s[:70]!r}{'...' if len(s) > 70 else ''}")


def glyphs(where, s):
    for c in s:
        if c in '\n\x01\x02\x03\x04':
            continue
        if ord(c) > 126 or c not in gt:
            bad(where, f"no glyph for {c!r}", s)
            return False
    return True


def width(s):
    w = sum((gt[c][0] if c in gt else 3) + 1 for c in s)
    return w - 1 if s else 0


def msg_lines(s):
    """hud_message's split (engine/src/hud.c)."""
    n = len(s)
    if width(s) <= 224 or n < 3:
        return [s]
    best = -1
    i = j = n // 2
    while i > 0 or j < n:
        if j < n and s[j] == ' ':
            best = j; break
        if i > 0 and s[i] == ' ':
            best = i; break
        i -= 1; j += 1
    if best < 0:
        return [s[:n // 2], s[n // 2:]]
    return [s[:best], s[best + 1:]]


def check_msg(where, s):
    if not glyphs(where, s):
        return
    for ln in msg_lines(s):
        if width(ln) > 236:
            bad(where, f"message line too wide ({width(ln)} px, 236 fit)", ln)
        if len(ln) > 127:
            bad(where, f"message line too long ({len(ln)} characters, 127 fit)", ln)


def check_line(where, s, px=236, chars=127):
    if not glyphs(where, s):
        return
    if width(s) > px:
        bad(where, f"too wide ({width(s)} px, {px} fit)", s)
    if len(s) > chars:
        bad(where, f"too long ({len(s)} characters, {chars} fit)", s)


def wrap(s, w):
    """gfx.c wrap_impl: the lines a text wraps into at width w."""
    lines, p = [], 0
    while p < len(s):
        lw, n, last_space, q = 0, 0, -1, p
        while q < len(s) and s[q] != '\n':
            cw = (gt[s[q]][0] if s[q] in gt else 3) + 1
            if lw + cw - 1 > w and n > 0:
                break
            if s[q] == ' ':
                last_space = n
            n += 1; lw += cw; q += 1
        if q < len(s) and s[q] != '\n' and last_space > 0:
            n = last_space
            q = p + last_space + 1
        elif q < len(s) and s[q] == '\n':
            q += 1
        lines.append(s[p:p + n])
        p = q
    return lines


def check_page(where, s, w, max_lines, max_chars=None):
    if not glyphs(where, s):
        return
    if max_chars and len(s) > max_chars:
        bad(where, f"too long ({len(s)} characters, {max_chars} fit)", s)
    lines = wrap(s, w)
    if len(lines) > max_lines:
        bad(where, f"{len(lines)} lines, {max_lines} fit", s)
    for ln in lines:
        if len(ln) > 63:
            bad(where, f"a wrapped line of {len(ln)} characters (63 fit)", ln)
        if width(ln) > w:
            bad(where, f"a word wider than the page ({width(ln)} px, {w} fit)", ln)


def main():
    """The checks every game shares: the text of level scripts and signs as
    the HUD draws it, and a glyph for every character of every string. Then
    the game's own rules, if it has any: tests/textrules.py, check(T) with T
    this module (check_msg, check_line, check_page, wrap, width, glyphs, bad)."""
    for ln in LEVELS:
        M = importlib.import_module(ln)
        for ev, acts in getattr(M, 'EVENTS', {}).items():
            for a in acts:
                if a[0] == 'msg':
                    check_msg(f"{ln} event {ev}", a[1])
                elif a[0] == 'objective':
                    check_line(f"{ln} event {ev} objective", a[1], 232)
        for k, op in getattr(M, 'EDGES', {}).items():
            if 'sign' in op:
                check_msg(f"{ln} sign {k}", op['sign'])
        for p in getattr(M, 'PROPS', []):
            if 'inter' in p and p['inter'][0] == 'sign':
                check_msg(f"{ln} sign on {p['model']}", p['inter'][1])
        for r, d in getattr(M, 'ROOMS', {}).items():
            glyphs(f"{ln} room {r}", d['name'])
    for nm, t in story.string_list():
        glyphs(nm, t)
    try:
        import textrules
    except ModuleNotFoundError as e:
        if e.name != 'textrules':
            raise
        textrules = None
    if textrules:
        textrules.check(sys.modules[__name__])
    for p in problems:
        print(p)
    print("text check:", "OK" if not problems else f"{len(problems)} problems")
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
