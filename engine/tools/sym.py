#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Expand {symbol} / {symbol+offset} in a harness script with addresses from
the test ROM's ELF: sym.py script.in > script.txt"""
import sys
import paths  # noqa: F401
import harness


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.stdout.write(harness.expand(open(sys.argv[1]).read()))


if __name__ == '__main__':
    harness.main(main)
