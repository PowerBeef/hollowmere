#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks every string of the game against the code that draws it, and exits 1
when one does not fit: textcheck.py

  messages, signs, lock hints   hud_message: one line up to 224 px, else two
                                halves split at the space nearest the middle,
                                each at most 236 px and 127 characters
  objectives, prompts           one HUD line of 236 px (objectives: 232)
  intro and ending pages        ui_text_screen: 599 characters, 13 lines of 200 px
  notes                         title 188 px; body in pages of 10 lines of 184 px, 9 pages
  credits, death lines,         centred lines of 236 px, 63 characters
  chapter cards, room names
  key names                     inside "Took the <key>." (46) and "Unlocked: <key>." (54)
  every string                  ASCII with a glyph for each character

The rules mirror engine/src/hud.c, engine/src/gfx.c and the game's ui.c."""
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
    fixed = dict(story.FIXED)
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
            # the map's heading: floor name on the left, room name on the right
            fl = getattr(M, 'FLOOR', getattr(M, 'NAME', ''))
            if glyphs(f"{ln} room {r}", d['name'] + fl) and width(fl) + width(d['name']) > 212:
                bad(f"{ln} room {r}", "floor and room name collide in the map heading", d['name'])
    for i, t in enumerate(story.LOCK_HINTS):
        check_msg(f"lock hint {i}", t)
    for nm, t in story.FIXED:
        if nm.startswith('M_'):
            check_msg(nm, t)
        elif nm.startswith('P_'):
            check_line(nm, t)
        elif nm in ('ENDING_TRUE', 'CREDITS'):
            pass                                    # pages of their own, below
        elif nm == 'CTRL_TIP':
            for ln_ in t.split('\n'):
                check_line(nm, ln_, 236, 63)
        else:
            check_line(nm, t, 236, 63)
    for i, t in enumerate(story.INTRO):
        check_page(f"intro page {i}", t, 200, 13, 599)
    for i, t in enumerate(list(story.ENDING) + [story.ENDING_TRUE]):
        check_page(f"ending page {i}", t, 200, 13, 599)
    for i, (title, body) in enumerate(zip(story.NOTE_TITLES, story.NOTES)):
        check_line(f"note {i} title", title, 188, 63)
        if glyphs(f"note {i}", body):
            lines = wrap(body, 184)
            if len(lines) > 90:
                bad(f"note {i}", f"{len(lines)} lines: more than 9 pages of 10", body)
            for ln_ in lines:
                if len(ln_) > 63 or width(ln_) > 184:
                    bad(f"note {i}", "a line that does not fit its page", ln_)
    for i, ln_ in enumerate(story.CREDITS.split('\n')):
        check_line(f"credits line {i}", ln_, 236, 63)
    for i, t in enumerate(story.DEATHS):
        check_line(f"death line {i}", t, 236, 63)
    for i, (t, n) in enumerate(zip(story.CHAPTERS, story.CHNUMS)):
        check_line(f"chapter {i} title", t, 236, 63)
        check_line(f"chapter {i} number", n, 118, 16)            # drawn at twice the size
    for i, k in enumerate(story.KEYS):
        if not k:
            continue
        glyphs(f"key {i}", k)
        took, unl = fixed.get('M_TOOK', ''), fixed.get('M_UNLOCKED', '')
        if len(took) > 40 or len(took) + len(k) + 1 > 46:
            bad(f"key {i}", "pickup message longer than its 48-byte buffer", took + k)
        if len(unl) > 40 or len(unl) + len(k) + 1 > 54:
            bad(f"key {i}", "unlock message longer than its 56-byte buffer", unl + k)
        check_msg(f"key {i} pickup", took + k + '.')
        check_msg(f"key {i} unlock", unl + k + '.')
    for p in problems:
        print(p)
    print("text check:", "OK" if not problems else f"{len(problems)} problems")
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
