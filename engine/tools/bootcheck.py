#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Boots the release ROM (no debug hooks) through the game's tests/boot.txt
and a minute of random input: bootcheck.py OUTDIR
Fails if the emulator reports an error, if no 3D frame is rendered, or if the
ROM still contains the test build's symbols."""
import os
import sys
import paths
import harness


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    syms = harness.symbols(paths.RELEASE_ELF)
    leaked = [s for s in ('g_debugCmd', 'g_dbgFreeze', 'g_pcSamples', 'g_profStage', 'g_objPub') if s in syms]
    if leaked:
        print(f"bootcheck.py: the release ROM has test-build symbols: {', '.join(leaked)}", file=sys.stderr)
        return 1
    L = harness.boot() + ["expect32 {g_renderCount} > 0 no 3D frame after boot", "peek32 {g_renderCount}",
                          "seed 3", "monkey 3600 0x3FF", "peek32 {g_renderCount}", "peek32 {g_vblanks}",
                          f"shot {out}/after.ppm"]
    r = harness.run(L, out, 'boot', rom=paths.RELEASE_ROM, elf=paths.RELEASE_ELF)
    v = r.values()
    print(f"release ROM: {v[0]} frames after boot, {v[1]} after a minute of random input, no emulator errors")


if __name__ == '__main__':
    harness.main(main)
