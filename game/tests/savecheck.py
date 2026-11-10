#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Hostile saves: savecheck.py OUTDIR

Plays the test ROM to chapter III to get a real save file (both slots
written), then boots the release ROM on that file and on forty-odd variants of
it: blank and random cartridges, a slot cut off half-way through a write,
states whose checksum is right but whose contents are out of range, odd but
legal states, and a save written by version 1.0. Every one must end in a
running game, without an emulator error, in the chapter expected:
  III    the newest slot was loaded
  II     it was refused and the older slot loaded
  I      nothing was loadable: a new game
After each boot a minute of random input is played. Exits 1 on any failure."""
import os
import random
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'engine', 'tools'))
import paths  # noqa: E402
import harness  # noqa: E402
import hm  # noqa: E402

# engine/src/save.c and SaveState in game/src/game.h (static asserts there keep these right)
SAVE_OFS, SLOT_SIZE, SIZE, CHECKSUM = 32, 256, 220, 218
OFF = dict(magic=0, level=4, version=5, objective=6, creatureMode=7, notesFound=8, keys=12, fuses=14, battery=16, seq=21, deaths=22,
           thingTaken=28, trigFired=56, roomsSeen=60, doorState=64, propHidden=104, propSet=124, flags=144, lightLevel=152,
           ev=168, pc=176, px=208, py=212)


def checksum(b):
    s = 0x1234
    for v in b:
        s = (s * 31 + v) & 0xFFFF
    return s


def sealed(state):
    """The slot's bytes with the checksum put right."""
    b = bytearray(state[:SIZE])
    b[CHECKSUM:CHECKSUM + 2] = struct.pack('<H', checksum(b[:CHECKSUM]))
    return bytes(b)


def poke(state, field, fmt, value, index=0):
    b = bytearray(state)
    o = OFF[field] + index * struct.calcsize(fmt)
    b[o:o + struct.calcsize(fmt)] = struct.pack('<' + fmt, value)
    return sealed(b)


def fill(state, field, n, value=0xFF):
    b = bytearray(state)
    b[OFF[field]:OFF[field] + n] = bytes([value]) * n
    return sealed(b)


def bad_spots(level):
    """Two places nobody can stand: the middle of a cell of a room that is
    only a drop, and the middle of a piece of furniture."""
    import sweep
    L, void = sweep.parsed(level)
    vx, vy = next((x, y) for y in range(L.H) for x in range(L.W) if L.cell[y][x] in void)
    x0, y0, x1, y1 = max(L.boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
    return (vx + 0.5, vy + 0.5), ((x0 + x1) / 2, (y0 + y1) / 2)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    os.makedirs(out, exist_ok=True)
    base = os.path.join(out, 'base.sav')
    if os.path.exists(base):
        os.remove(base)
    # chapter I's entry goes to slot 0, II's to slot 1, III's to slot 0 again
    harness.run(hm.boot() + hm.dismiss() + hm.load_level(1) + hm.dismiss() + hm.load_level(2) + ["run 60"], out, 'make', save=base)
    sram = bytearray(open(base, 'rb').read())
    sram += bytes([0xFF]) * (0x8000 - len(sram))
    s0, s1 = SAVE_OFS, SAVE_OFS + SLOT_SIZE
    new, old = bytes(sram[s0:s0 + SIZE]), bytes(sram[s1:s1 + SIZE])
    if new[OFF['level']] != 2 or old[OFF['level']] != 1 or checksum(new[:CHECKSUM]) != struct.unpack_from('<H', new, CHECKSUM)[0]:
        print("savecheck.py: the save file made by the test ROM is not what this tool expects "
              f"(slot levels {new[OFF['level']]}, {old[OFF['level']]}): has SaveState changed?", file=sys.stderr)
        return 1

    def cart(a=None, b=None, settings=True):
        """A cartridge with these two slots (None: erased)."""
        c = bytearray([0xFF]) * 0x8000
        if settings:
            c[0:SAVE_OFS] = sram[0:SAVE_OFS]
        if a: c[s0:s0 + len(a)] = a
        if b: c[s1:s1 + len(b)] = b
        return bytes(c)

    rng = random.Random(1958)
    drop, table = bad_spots(2)
    cases = [   # name, cartridge, chapter expected (0-based level)
        ('as written', cart(new, old), 2),
        ('erased cartridge', bytes([0xFF]) * 0x8000, 0),
        ('zeroed cartridge', bytes(0x8000), 0),
        ('random cartridge', bytes(rng.randrange(256) for _ in range(0x8000)), 0),
        ('newest slot half written', cart(new[:110], old), 1),
        ('newest slot half written over an older state', cart(new[:110] + old[110:], old), 1),
        ('older slot half written', cart(new, old[:90]), 2),
        ('both slots half written', cart(new[:60], old[:200]), 0),
        ('one flipped bit', cart(bytes([new[0]]) + new[1:40] + bytes([new[40] ^ 4]) + new[41:], None), 0),
        ('only the older slot', cart(None, old), 1),
        ('sequence number wrapped', cart(poke(new, 'seq', 'B', 2), poke(old, 'seq', 'B', 254)), 2),
    ]
    refused = [
        ('level 4', poke(new, 'level', 'B', 4)), ('level 255', poke(new, 'level', 'B', 255)),
        ('objective 255', poke(new, 'objective', 'B', 255)), ('creature mode 3', poke(new, 'creatureMode', 'B', 3)),
        ('nine fuses', poke(new, 'fuses', 'B', 9)), ('battery overfull', poke(new, 'battery', 'I', 0xFFFFFFFF)),
        ('light level 200', poke(new, 'lightLevel', 'B', 200, 3)),
        ('script event 200', poke(new, 'ev', 'B', 200)), ('script position 60000', poke(poke(new, 'ev', 'B', 1), 'pc', 'H', 60000)),
        ('position off the map', poke(new, 'px', 'i', 40 << 16)), ('negative position', poke(new, 'py', 'i', -1)),
        ('position in the stairwell drop', poke(poke(new, 'px', 'i', int(drop[0] * 65536)), 'py', 'i', int(drop[1] * 65536))),
        ('position inside furniture', poke(poke(new, 'px', 'i', int(table[0] * 65536)), 'py', 'i', int(table[1] * 65536))),
        ('layout version 2', poke(new, 'version', 'B', 2)), ('layout version 0', poke(new, 'version', 'B', 0)),
        ('another magic', poke(new, 'magic', 'I', 0x484C5734)),
    ]
    cases += [(f"refused: {n}", cart(s, old), 1) for n, s in refused]
    cases += [(f"refused, nothing older: {n}", cart(s, None), 0) for n, s in refused[:3]]
    legal = [
        ('every key', poke(new, 'keys', 'H', 0xFFFF)), ('every thing taken', fill(new, 'thingTaken', 14)),
        ('every door state bit', fill(new, 'doorState', 40)), ('every prop hidden', fill(new, 'propHidden', 20)),
        ('every prop set', fill(new, 'propSet', 20)), ('every flag', fill(new, 'flags', 8)),
        ('every trigger fired', fill(new, 'trigFired', 4)), ('65535 deaths', poke(new, 'deaths', 'H', 0xFFFF)),
        ('every note', poke(new, 'notesFound', 'I', 0xFFFFFFFF)), ('empty battery', poke(new, 'battery', 'I', 0)),
        ('lights out', fill(new, 'lightLevel', 16, 0)),
    ]
    cases += [(f"odd but legal: {n}", cart(s, None), 2) for n, s in legal]
    # version 1.0: one slot at the same place, the same fields up to the script threads, then position and checksum
    v1 = bytearray(new[:OFF['ev']] + new[OFF['px']:OFF['px'] + 10] + b'\0\0')
    v1[0:4] = struct.pack('<I', 0x484C5732)
    v1[OFF['version']] = 0
    v1[-2:] = struct.pack('<H', checksum(v1[:-2]))
    cases += [('a version 1.0 save: its chapter from the start', cart(bytes(v1), None), 2),
              ('a version 1.0 save with a bad checksum', cart(bytes(v1[:-1]) + bytes([v1[-1] ^ 1]), None), 0)]

    failed = 0
    for i, (name, data, level) in enumerate(cases):
        sav = os.path.join(out, f"case{i:02d}.sav")
        open(sav, 'wb').write(data)
        L = harness.boot() + ["run 400", f"expect8 {{g_state+{hm.LEVEL}}} == {level} the chapter loaded",
                              "expect8 {g_gameSignal} == 0 in play"] + hm.rendering() + ["seed 5", "monkey 3600 0x3FF"]
        try:
            r = harness.run(L, out, f"case{i:02d}", rom=paths.RELEASE_ROM, save=sav)
            a, b = r.values()[-2:]
            ok = b > a
            why = "" if ok else "the game is not running"
        except harness.HarnessError as e:
            ok, why = False, str(e).split('\n')[1].strip() if '\n' in str(e) else str(e)
        failed += not ok
        print(f"  {'pass' if ok else 'FAIL'}  {name}" + (f": {why}" if why else ""))
    print(f"savecheck: {len(cases) - failed} of {len(cases)} saves handled")
    return 1 if failed else 0


if __name__ == '__main__':
    harness.main(main)
