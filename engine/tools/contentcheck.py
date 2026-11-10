#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Proves that the asset tools refuse content the engine cannot handle:
contentcheck.py [-v]

Takes a small level, script and model that the tools accept, breaks each in
one way at a time (a door too many, a wait too long, a wall standing free...)
and expects a limits.ContentError whose one line names the thing. Exits 1 when
a broken input is accepted, or refused with anything but that. No emulator and
no game content is involved; check.py runs it with python3 -O, where a
validation written as `assert` would silently pass everything."""
import sys
import types

import numpy as np

import paths            # noqa: F401  (the tools' import path)
import limits
import levelc
import scriptc
import build_assets
from limits import ContentError


class Any(dict):
    """An id table that knows every name (the textures and models of a real game are not this test's business)."""

    def __missing__(self, k):
        return 1

    def __contains__(self, k):
        return True


def plan(w, h, vertical=' ', inner_row=None):
    """The MAP text of a w by h block of room 'a': `vertical` on the edges
    between cells of a row, inner_row(y) -> the characters of horizontal edge
    row y (1..h-1) or None for open."""
    rows = []
    for y in range(h + 1):
        if y == 0 or y == h or inner_row is None:
            edge = '-' if y in (0, h) else ' '
            rows.append('+' + '+'.join(edge * 1 for _ in range(w)) + '+')
        else:
            rows.append('+' + '+'.join(inner_row(y)[x] for x in range(w)) + '+')
        if y < h:
            rows.append('|' + vertical.join('a' * 1 for _ in range(w)) + '|')
    return '\n'.join(rows)


def level(**over):
    """A level module the compiler accepts, with attributes replaced."""
    m = types.ModuleType('testlevel')
    m.NAME = 'testlevel'
    m.MAP = plan(4, 3)
    m.ROOMS = {'a': dict(wall='plaster', mat=0, name='Room')}
    m.MATERIALS = [('floor', 'ceiling')]
    m.START = (0.5, 0.5, 'E')
    m.EDGES = {}
    m.PROPS = []
    m.THINGS = [dict(type='key', x=1.5, y=1.5, param=1, name='key')]
    m.LIGHTS = [(1.5, 1.5, 12, 3.0, 'flicker', 1)]
    m.TRIGGERS = [(0, 0, 1, 1, 'start')]
    m.PATROL = [(1, 1), (2, 2)]
    m.EVENTS = {'start': [('wait', 30)]}
    for k, v in over.items():
        setattr(m, k, v)
    return m


def parse(**over):
    return levelc.parse(level(**over), dict(wall=Any(), flat=Any(), ptex=Any(), model=Any(), thing=Any()), None)


def script(actions, flags=None):
    ctx = scriptc.Ctx(scriptc.StringTable(), {'click': 0}, {} if flags is None else flags, {'start': 1}, {'front': 0}, {'key': 0}, 'testlevel')
    ctx.props = {'shelf': 0}
    ctx.music = {'tune': 0}
    return scriptc.compile_event(actions, ctx, 'start')


class Mesh:
    def __init__(self, verts, faces):
        self.verts, self.faces = verts, faces


def quad(i0=0, size=64):
    return dict(v=[i0, i0 + 1, i0 + 2, i0 + 3], uv=[(0, 0), (size % 256, 0), (size % 256, 64), (0, 64)], tex=0, n=(0, -64, 0), flags=1)


def model(nverts=4, nfaces=1, length=64, rows=64):
    verts = [(0, 0, 0), (length, 0, 0), (length, 0, 64), (0, 0, 64)] + [(i, 1, 0) for i in range(nverts - 4)]
    faces = [quad() for _ in range(nfaces)]
    faces[0]['uv'] = [(0, 0), (64, 0), (64, rows), (0, rows)]
    build_assets.check_model('testmodel', Mesh(verts, faces), {}, {})


def tex(h, w):
    return np.zeros((h, w, 3))


def textures(flat=(64, 64), wall=(128, 64), prop=(64, 64)):
    build_assets.check_textures({'w': tex(*wall)}, {'f': tex(*flat)}, {'p': tex(*prop)})


def doors_map(n_cols):
    """Two rows of n_cols cells with a door on every edge between neighbours of a row."""
    return plan(n_cols, 2, vertical='d')


def stub_row(y):
    return ' - '        # one wall edge in the middle of the room, touching nothing


def joined_row(y):
    return '-  '        # the same edge, joined to the outer wall


# (what is broken, a function that must raise ContentError, words its message must contain)
CASES = [
    ("41 doors", lambda: parse(MAP=doors_map(22)), "42 doors: the most is 40"),
    ("a wait of 32,768 frames", lambda: script([('wait', 32768)]), "from 0 to 32767"),
    ("a model of 129 vertices", lambda: model(nverts=129), "129 vertices: the most is 128"),
    ("a model of 65 faces", lambda: model(nfaces=65), "65 faces: the most is 64"),
    ("113 things", lambda: parse(THINGS=[dict(type='key', x=1.5, y=1.5)] * 113), "113 things: the most is 112"),
    ("161 props", lambda: parse(PROPS=[dict(model='chair', x=1.5, y=1.5)] * 161), "161 props: the most is 160"),
    ("a door on an outside edge", lambda: parse(MAP=plan(4, 3).replace('|a', 'da', 1)), "leads outside the map"),
    ("an arch on an outside edge", lambda: parse(MAP=plan(4, 3).replace('+-+', '+a+', 1)), "leads outside the map"),
    ("a trigger at x 300", lambda: parse(TRIGGERS=[(0, 0, 300, 1, 'start')]), "x1 of the trigger"),
    ("a trigger at x -1", lambda: parse(TRIGGERS=[(-1, 0, 1, 1, 'start')]), "x0 of the trigger"),
    ("33 triggers", lambda: parse(TRIGGERS=[(0, 0, 1, 1, 'start')] * 33), "33 triggers: the most is 32"),
    ("light group 16", lambda: parse(LIGHTS=[(1.5, 1.5, 12, 3.0, 'steady', 16)]), "the group of the light"),
    ("a light 20 tiles wide", lambda: parse(LIGHTS=[(1.5, 1.5, 12, 20.0)]), "under 16 tiles"),
    ("a light of brightness 40", lambda: parse(LIGHTS=[(1.5, 1.5, 40, 3.0)]), "the brightness of the light"),
    ("a script setting light group 16", lambda: script([('light', 16, 255)]), "the light group"),
    ("a door drawn locked with no lock=", lambda: parse(MAP=doors_map(2).replace('d', 'l')), "gives it no lock="),
    ("a door locked with key 16", lambda: parse(MAP=doors_map(2), EDGES={(1, 0, 'W'): dict(lock=16)}), "lock= of the door"),
    ("a script giving key 16", lambda: script([('give', 'key', 16)]), "the key in"),
    ("a script testing key 16", lambda: script([('label', 'a'), ('if_key', 16, 'a')]), "the key in"),
    ("256 events", lambda: scriptc.event_table({f"e{i}": [] for i in range(256)}, ('start',), 'testlevel'), "257 events: the most is 255"),
    ("the 64th script flag", lambda: script([('flag', f"f{i}") for i in range(64)]), "the scripts of all levels share 63"),
    ("a face 2.5 tiles long", lambda: model(length=640), "2.50 tiles long: the most is 2.4"),
    ("an upright face two textures tall", lambda: model(rows=128), "cannot repeat its texture downwards"),
    ("a wall standing free", lambda: parse(MAP=plan(3, 3, inner_row=stub_row)), "stands free at both ends"),
    ("a floor texture of 32 by 32", lambda: textures(flat=(32, 32)), "must be 64 wide and 64 tall"),
    ("a wall texture of 64 by 64", lambda: textures(wall=(64, 64)), "must be 64 wide and 128 tall"),
    ("no MATERIALS", lambda: parse(MATERIALS=[]), "MATERIALS has 0 entries"),
    ("five MATERIALS", lambda: parse(MATERIALS=[('f', 'c')] * 5), "MATERIALS has 5 entries"),
    ("a room using material 3 of 1", lambda: parse(ROOMS={'a': dict(wall='plaster', mat=3, name='Room')}), "mat= of room 'a'"),
    ("text with an accent", lambda: build_assets.check_text(["The café is closed."]), "no glyph for 'é'"),
    ("an unknown room letter", lambda: parse(MAP=plan(4, 3).replace('a', 'z', 1)), "which ROOMS does not have"),
    ("a map of 32 cells across", lambda: parse(MAP=plan(32, 2)), "32 by 2 cells: the most is 31 by 31"),
    ("the start outside the rooms", lambda: parse(START=(9.5, 9.5, 'E')), "START (9.5, 9.5) is outside"),
    ("a thing outside the rooms", lambda: parse(THINGS=[dict(type='key', x=9.5, y=1.5)]), "is outside the rooms"),
    ("a thing with param 300", lambda: parse(THINGS=[dict(type='key', x=1.5, y=1.5, param=300)]), "param= of the thing"),
    ("a prop off the map", lambda: parse(PROPS=[dict(model='chair', x=40.0, y=1.5)]), "is off the map"),
    ("a patrol node outside", lambda: parse(PATROL=[(9, 9)]), "patrol node (9, 9)"),
    ("an unknown action", lambda: script([('explode', 3)]), "there is no action 'explode'"),
    ("an action with an argument missing", lambda: script([('sound3d', 'click', 3)]), "missing or mistaken argument"),
    ("a jump to no label", lambda: script([('jmp', 'nowhere')]), "the label 'nowhere'"),
    ("an unknown sound", lambda: script([('sound', 'boom')]), "there is no sound 'boom'"),
    ("an unknown tune", lambda: script([('music', 'waltz')]), "there is no music 'waltz'"),
    ("an action the engine no longer has", lambda: script([('chapter', 'One')]), "there is no action 'chapter'"),
    ("an unknown door", lambda: script([('door', 'back', 'open')]), "there is no door named 'back'"),
    ("a teleport to cell 40", lambda: script([('teleport', 40, 1, 'E')]), "x in"),
    ("a volume of 300", lambda: script([('sound', 'click', 300)]), "the volume in"),
    ("a note numbered 32", lambda: script([('note', 32)]), "the note in"),
]

# inputs just inside the limits, which must be accepted
ACCEPTED = [
    ("the plain level", lambda: parse()),
    ("40 doors", lambda: parse(MAP=doors_map(21), PATROL=[])),
    ("a door drawn locked, with lock=", lambda: parse(MAP=doors_map(2).replace('d', 'l'), EDGES={(1, 0, 'W'): dict(lock=2), (1, 1, 'W'): dict(lock=3)}, PATROL=[])),
    ("a wait of 32,767 frames", lambda: script([('wait', 32767)])),
    ("a model of 128 vertices and 64 faces", lambda: model(nverts=128, nfaces=64)),
    ("a face 2.4 tiles long", lambda: model(length=614)),
    ("112 things", lambda: parse(THINGS=[dict(type='key', x=1.5, y=1.5)] * 112)),
    ("160 props", lambda: parse(PROPS=[dict(model='chair', x=1.5, y=1.5)] * 160)),
    ("a wall joined at one end", lambda: parse(MAP=plan(3, 3, inner_row=joined_row))),
    ("63 script flags", lambda: script([('flag', f"f{i}") for i in range(63)])),
    ("255 events", lambda: scriptc.event_table({f"e{i}": [] for i in range(254)}, ('start',), 'testlevel')),
    ("textures of the right sizes", lambda: textures()),
    ("ASCII text with a line break", lambda: build_assets.check_text(["Plain text.\nSecond line."])),
    ("every action with plain arguments", lambda: script([
        ('label', 'top'), ('sound', 'click', 200, -20), ('sound3d', 'click', 3, 2), ('msg', 'Hello.', 120), ('objective', 'Leave.'),
        ('door', 'front', 'open'), ('light', 1, 256), ('creature', 'spawn', 3, 2), ('shake', 3, 20), ('flash', 4), ('flag', 'seen'),
        ('if_flag', 'seen', 'top'), ('give', 'key', 15), ('give', 'battery', 30), ('fear', 40), ('blackout', 600), ('thing', 'key', False),
        ('ifnot_key', 15, 'top'), ('fade', 16, 3), ('teleport', 3, 2, 'N'), ('if_fuses_lt', 3, 'top'), ('prop', 'shelf', True),
        ('freeze', True), ('lookat', 3, 2), ('lookat', None), ('note', 31), ('start', 'start'), ('jrand', 128, 'top'), ('hudoff', False),
        ('music', 'tune', 180), ('musicstop',), ('ambience', 'click', 100), ('stopsounds',), ('placefuses',),
        ('checkpoint',), ('endlevel', 1), ('ending',), ('jmp', 'top')])),
]


def main():
    verbose = '-v' in sys.argv
    failed = 0
    for what, fn in ACCEPTED:
        try:
            fn()
            if verbose:
                print(f"  ok    accepted: {what}")
        except ContentError as e:
            failed += 1
            print(f"  FAIL  {what} is within the limits but was refused: {e}")
    for what, fn, words in CASES:
        try:
            fn()
        except ContentError as e:
            line = str(e)
            if words not in line or '\n' in line or 'testlevel' not in line and 'testmodel' not in line and 'text' not in line:
                failed += 1
                print(f"  FAIL  {what}: refused, but not in the words expected ({words!r}): {line}")
            elif verbose:
                print(f"  ok    {what}: {line}")
            continue
        except Exception as e:                      # a crash is not a refusal the author can read
            failed += 1
            print(f"  FAIL  {what}: {type(e).__name__}: {e} (instead of a one-line ContentError)")
            continue
        failed += 1
        print(f"  FAIL  {what}: accepted")
    n = len(CASES) + len(ACCEPTED)
    if failed:
        print(f"content check: {failed} of {n} cases FAILED")
        return 1
    print(f"content check: OK ({len(CASES)} kinds of bad content refused, {len(ACCEPTED)} at the limits accepted"
          f"{'' if __debug__ else ', with assertions off'})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
