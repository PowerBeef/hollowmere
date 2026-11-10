# SPDX-License-Identifier: MIT
"""Hollowmere's own text rules, run by engine/tools/textcheck.py after the
ones every game shares. They mirror the game's screens (game/src/ui.c,
game/src/map.c, player.c):

  lock hints, M_* strings       subtitles (hud_message)
  prompts (P_*)                 one HUD line of 236 px
  intro and ending pages        ui_text_screen: 599 characters, 13 lines of 200 px
  notes                         title 188 px; body in pages of 10 lines of 184 px, 9 pages
  credits, death lines,         centred lines of 236 px, 63 characters
  chapter cards
  the map's heading             floor name and room name side by side in 212 px
  key names                     inside "Took the <key>." (46) and "Unlocked: <key>." (54)"""
import importlib

import story
from manifest import LEVELS


def check(T):
    fixed = dict(story.FIXED)
    for ln in LEVELS:
        M = importlib.import_module(ln)
        fl = getattr(M, 'FLOOR', getattr(M, 'NAME', ''))
        for r, d in getattr(M, 'ROOMS', {}).items():
            # the map's heading: floor name on the left, room name on the right
            if T.glyphs(f"{ln} room {r}", d['name'] + fl) and T.width(fl) + T.width(d['name']) > 212:
                T.bad(f"{ln} room {r}", "floor and room name collide in the map heading", d['name'])
    for i, t in enumerate(story.LOCK_HINTS):
        T.check_msg(f"lock hint {i}", t)
    for nm, t in story.FIXED:
        if nm.startswith('M_'):
            T.check_msg(nm, t)
        elif nm.startswith('P_'):
            T.check_line(nm, t)
        elif nm in ('ENDING_TRUE', 'CREDITS'):
            pass                                    # pages of their own, below
        elif nm == 'CTRL_TIP':
            for ln_ in t.split('\n'):
                T.check_line(nm, ln_, 236, 63)
        else:
            T.check_line(nm, t, 236, 63)
    for i, t in enumerate(story.INTRO):
        T.check_page(f"intro page {i}", t, 200, 13, 599)
    for i, t in enumerate(list(story.ENDING) + [story.ENDING_TRUE]):
        T.check_page(f"ending page {i}", t, 200, 13, 599)
    for i, (title, body) in enumerate(zip(story.NOTE_TITLES, story.NOTES)):
        T.check_line(f"note {i} title", title, 188, 63)
        if T.glyphs(f"note {i}", body):
            lines = T.wrap(body, 184)
            if len(lines) > 90:
                T.bad(f"note {i}", f"{len(lines)} lines: more than 9 pages of 10", body)
            for ln_ in lines:
                if len(ln_) > 63 or T.width(ln_) > 184:
                    T.bad(f"note {i}", "a line that does not fit its page", ln_)
    for i, ln_ in enumerate(story.CREDITS.split('\n')):
        T.check_line(f"credits line {i}", ln_, 236, 63)
    for i, t in enumerate(story.DEATHS):
        T.check_line(f"death line {i}", t, 236, 63)
    for i, (t, n) in enumerate(zip(story.CHAPTERS, story.CHNUMS)):
        T.check_line(f"chapter {i} title", t, 236, 63)
        T.check_line(f"chapter {i} number", n, 118, 16)            # drawn at twice the size
    for i, k in enumerate(story.KEYS):
        if not k:
            continue
        T.glyphs(f"key {i}", k)
        took, unl = fixed.get('M_TOOK', ''), fixed.get('M_UNLOCKED', '')
        if len(took) > 40 or len(took) + len(k) + 1 > 46:
            T.bad(f"key {i}", "pickup message longer than its 48-byte buffer", took + k)
        if len(unl) > 40 or len(unl) + len(k) + 1 > 54:
            T.bad(f"key {i}", "unlock message longer than its 56-byte buffer", unl + k)
        T.check_msg(f"key {i} pickup", took + k + '.')
        T.check_msg(f"key {i} unlock", unl + k + '.')
