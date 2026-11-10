#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks that the test tools can fail: selftest.py OUTDIR
Feeds the harness scripts and ROMs that are wrong on purpose and checks its
exit status each time: 1 for a failed expectation, 2 for a script or file
error, 3 for a ROM that crashes. Exits 1 if the harness lets any through."""
import os
import subprocess
import sys
import paths
import harness


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    os.makedirs(out, exist_ok=True)
    rom = paths.ROM
    if not os.path.exists(rom):
        raise harness.HarnessError(f"no ROM at {rom}: make test-rom")
    # a ROM whose first instruction jumps into nowhere
    crashed = os.path.join(out, 'crashed.gba')
    b = bytearray(open(rom, 'rb').read())
    entry = (((int.from_bytes(b[0:4], 'little') & 0xFFFFFF) << 2) + 8)
    b[entry:entry + 4] = (0xE3A0F40E).to_bytes(4, 'little')         # mov pc, #0x0E000000
    open(crashed, 'wb').write(b)
    cases = [
        # name, rom, script, expected exit
        ('fine', rom, "run 30\nexpect32 0x03000000 >= 0\n", 0),
        ('failed expectation', rom, "run 30\nexpect8 0x03000000 > 255 never true\n", 1),
        ('unknown command', rom, "run 10\nfrobnicate 3\n", 2),
        ('unknown key', rom, "hold UPP\n", 2),
        ('unresolved symbol', rom, "poke32 {g_debugCmd} 5\n", 2),
        ('bad number', rom, "run abc\n", 2),
        ('bad output path', rom, f"run 2\nshot {out}/no/such/dir/x.ppm\n", 2),
        ('bad dump path', rom, f"dump 0x03000000 16 {out}/no/such/dir/x.bin\n", 2),
        ('missing ROM', os.path.join(out, 'missing.gba'), "run 10\n", 2),
        ('crashed ROM', crashed, "run 600\n", 3),
    ]
    bad = 0
    for name, r, script, want in cases:
        path = os.path.join(out, name.replace(' ', '_') + '.txt')
        open(path, 'w').write(script)
        try:
            p = subprocess.run([paths.HARNESS, r, path], capture_output=True, text=True, timeout=120)
            got = p.returncode
        except subprocess.TimeoutExpired:
            got = 'timeout'
        ok = got == want
        bad += not ok
        print(f"  {'pass' if ok else 'FAIL'}  {name}: exit {got}" + ('' if ok else f", expected {want}"))
    # the Python layer turns each of those into an error too
    for name, fn in (('helper: failed expectation', lambda: harness.run(["expect8 0x03000000 > 255"], out, 'h1')),
                     ('helper: unknown symbol', lambda: harness.run(["peek8 {no_such_symbol}"], out, 'h2')),
                     ('helper: missing ROM', lambda: harness.run(["run 1"], out, 'h3', rom=os.path.join(out, 'missing.gba'), elf=paths.ELF))):
        try:
            fn()
            ok = False
        except harness.HarnessError:
            ok = True
        bad += not ok
        print(f"  {'pass' if ok else 'FAIL'}  {name}")
    print(f"selftest: {'OK' if not bad else '%d problems' % bad}")
    return 1 if bad else 0


if __name__ == '__main__':
    harness.main(main)
