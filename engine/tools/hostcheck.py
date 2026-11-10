#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compiles engine/tools/hostcheck.c with the build machine's C compiler and
runs it: checks of the engine's pure functions (sort keys, queues, fixed
point helpers) that need no emulator. hostcheck.py [OUTDIR]
Exits 1 when a check fails or the file does not compile."""
import os
import subprocess
import sys

import paths


def main():
    out = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(paths.OUT, 'hostcheck')
    os.makedirs(out, exist_ok=True)
    exe = os.path.join(out, 'hostcheck')
    src = os.path.join(paths.TOOLS, 'hostcheck.c')
    inc = [f"-I{os.path.join(paths.ROOT, 'engine', 'src')}", f"-I{os.path.join(paths.GAME, 'src')}", f"-I{paths.GEN}"]
    cc = os.environ.get('HOSTCC', 'gcc')
    r = subprocess.run([cc, '-O1', '-Wall', '-Wextra', '-Wno-unused-parameter', '-Wno-attributes', '-DHOSTCHECK'] + inc + ['-o', exe, src],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stderr.strip(), file=sys.stderr)
        print("hostcheck.py: hostcheck.c does not compile", file=sys.stderr)
        return 1
    r = subprocess.run([exe], capture_output=True, text=True)
    print(r.stdout.strip())
    return 1 if r.returncode else 0


if __name__ == '__main__':
    sys.exit(main())
