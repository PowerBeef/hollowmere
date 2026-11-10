#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The whole test suite: check.py [OUTDIR] [--quick] [--only step,step]
Runs every check the repository has, one after another, and exits 1 if any
fails. `make check` builds both ROMs and the harness first and then runs this.
Output of each step goes to OUTDIR (default build/check)/<step>.log.

Steps that need no emulator: content (level audit, text, the LZ77 packer) and
host (the engine's pure functions, compiled for this machine).
Steps in the emulator: selftest (the tools themselves), boot (the release
ROM), playthrough, regress, sweep (undrawn pixels over the levels; --quick
samples every 12th view), fps, stack, saves."""
import os
import subprocess
import sys
import time
import paths


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = os.path.abspath(args[0]) if args else os.path.join(paths.ROOT, 'build', 'check')
    quick = '--quick' in sys.argv
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
    os.makedirs(out, exist_ok=True)
    T, G = paths.TOOLS, paths.TESTS
    py = sys.executable
    steps = [
        ('audit', [py, f"{T}/audit.py"]),
        ('text', [py, f"{T}/textcheck.py"]),
        ('lz77', [py, f"{T}/lz77.py"]),
        ('host', [py, f"{T}/hostcheck.py", f"{out}/host"]),
        ('selftest', [py, f"{T}/selftest.py", f"{out}/selftest"]),
        ('boot', [py, f"{T}/bootcheck.py", f"{out}/boot"]),
        ('playthrough', [py, f"{G}/playtest.py", f"{out}/playthrough"]),
        ('regress', [py, f"{T}/regress.py", f"{out}/regress"]),
        ('sweep', [py, f"{T}/sweep.py", f"{out}/sweep"] + (['--every', '12'] if quick else [])),
        ('fps', [py, f"{T}/fps.py", f"{out}/fps"]),
        ('stack', [py, f"{T}/stackcheck.py", f"{out}/stack"]),
        ('saves', [py, f"{G}/savecheck.py", f"{out}/saves"]),
    ]
    failed = []
    for name, cmd in steps:
        if only and name not in only:
            continue
        if not os.path.exists(cmd[1]):
            print(f"  skip  {name}: this game has no {os.path.relpath(cmd[1], paths.ROOT)}")
            continue
        t0 = time.time()
        log = os.path.join(out, name + '.log')
        with open(log, 'w') as f:
            code = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode
        tail = open(log).read().strip().split('\n')[-1][:100]
        print(f"  {'pass' if code == 0 else 'FAIL'}  {name:12s} {time.time() - t0:6.1f} s   {tail}")
        sys.stdout.flush()
        if code:
            failed.append(name)
    if failed:
        print(f"check: FAILED: {', '.join(failed)} (logs in {os.path.relpath(out)})")
        return 1
    print("check: all passed")
    return 0


if __name__ == '__main__':
    sys.exit(main())
