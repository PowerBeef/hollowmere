#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Runs the game's regression tests: regress.py OUTDIR [name ...]

A test is a function test_<name>(t) in a file $GAME/tests/regress/test_*.py.
It gets a context t:
    t.out                    its own output folder
    t.run(lines, **kw)       harness.run in that folder (returns the Result)
    t.image(path)            a saved screenshot as a PIL image
    t.check(cond, message)   fail with a message
A test fails by an assertion, a failed harness expectation or a harness error.
Names given on the command line select tests (substring match).
Exits 1 when any test fails."""
import glob
import importlib.util
import os
import sys
import time
import traceback

import paths
import harness


class Ctx:
    def __init__(self, out):
        self.out = out
        self._n = 0
        os.makedirs(out, exist_ok=True)

    def run(self, lines, **kw):
        self._n += 1
        kw.setdefault('name', f"s{self._n}")
        lines = [l.replace('{out}', self.out) for l in lines]
        return harness.run(lines, self.out, **kw)

    def image(self, path):
        from PIL import Image
        return Image.open(path if os.path.isabs(path) else os.path.join(self.out, path)).convert('RGB')

    def check(self, cond, message):
        if not cond:
            raise AssertionError(message)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    want = sys.argv[2:]
    files = sorted(glob.glob(os.path.join(paths.TESTS, 'regress', 'test_*.py')))
    failed, ran = [], 0
    for f in files:
        spec = importlib.util.spec_from_file_location(os.path.basename(f)[:-3], f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name in [n for n in dir(mod) if n.startswith('test_')]:
            short = name[5:]
            if want and not any(w in short for w in want):
                continue
            ran += 1
            t0 = time.time()
            try:
                getattr(mod, name)(Ctx(os.path.join(out, short)))
                print(f"  pass  {short}  ({time.time() - t0:.1f} s)")
            except (AssertionError, harness.HarnessError) as e:
                failed.append(short)
                print(f"  FAIL  {short}: {e}")
            except Exception:
                failed.append(short)
                print(f"  FAIL  {short}: the test itself broke\n{traceback.format_exc()}")
            sys.stdout.flush()
    print(f"regress: {ran - len(failed)} of {ran} passed")
    if not ran:
        print("regress: no tests found", file=sys.stderr)
        return 1
    return 1 if failed else 0


if __name__ == '__main__':
    harness.main(main)
