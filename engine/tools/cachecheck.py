#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests the asset cache of build_assets.py: cachecheck.py
An entry cut short by a killed build is rebuilt instead of breaking every
later build; a write is whole or absent; entries nobody uses are pruned and
used ones kept. Works in a temporary folder; exits 1 on a failure."""
import os
import sys
import tempfile
import time

import paths            # noqa: F401
import build_assets as B


def main():
    bad = []

    def expect(ok, what):
        if not ok:
            bad.append(what)

    with tempfile.TemporaryDirectory() as d:
        B.CACHE = d
        calls = []

        def make():
            calls.append(1)
            return {'value': list(range(1000))}
        v = B.cached(('k', 1), make)
        expect(len(calls) == 1 and B.cached(('k', 1), make) == v and len(calls) == 1, "a stored entry is reused")
        expect(B.cached(('k', 2), make) == v and len(calls) == 2, "another key is built")
        files = sorted(f for f in os.listdir(d) if f.endswith('.pkl'))
        expect(len(files) == 2 and not [f for f in os.listdir(d) if f.endswith('.tmp')], "two entries and no temporary file left")
        # a build killed while writing used to leave half an entry: every later build then died reading it
        p = os.path.join(d, files[0])
        whole = open(p, 'rb').read()
        open(p, 'wb').write(whole[:len(whole) // 2])
        n = len(calls)
        stderr, sys.stderr = sys.stderr, open(os.devnull, 'w')
        try:
            r1, r2 = B.cached(('k', 1), make), B.cached(('k', 2), make)
        except Exception as e:
            r1 = r2 = None
            bad.append(f"a truncated entry breaks the build: {type(e).__name__}: {e}")
        finally:
            sys.stderr = stderr
        expect(r1 == v and r2 == v and len(calls) == n + 1, "a truncated entry is rebuilt, once")
        expect(open(p, 'rb').read() == whole, "... and stored whole again")
        # pruning by last use
        old = time.time() - (B.CACHE_DAYS + 1) * 86400
        os.utime(os.path.join(d, files[0]), (old, old))
        os.utime(os.path.join(d, files[1]), (old, old))
        open(os.path.join(d, 'x.pkl.123.tmp'), 'wb').close()
        os.utime(os.path.join(d, 'x.pkl.123.tmp'), (old, old))
        B.cached(('k', 1), make)                 # used again: stays
        gone = B.prune_cache()
        left = sorted(f for f in os.listdir(d))
        expect(gone == 2 and len(left) == 1 and left[0].endswith('.pkl'), f"pruning deletes the unused entry and the stale temporary file ({gone} deleted, left: {left})")
    for b in bad:
        print(f"  FAIL  {b}")
    print("cache check: " + (f"{len(bad)} FAILED" if bad else "OK"))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
