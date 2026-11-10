#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""How deep the stacks go: stackcheck.py OUTDIR [--min BYTES]
The startup code paints the free fast RAM under the main stack and the
interrupt handlers' stack with 0xA5. This runs the test ROM through the
benchmark views (interrupts on) and a stretch of random input in every level
and menu, and the release ROM through boot and random input, then reads how
much paint is left. Exits 1 when either main stack has less than --min bytes
of headroom (default 256).

A function that reserves stack without writing to all of it is counted only
as deep as it wrote, so the true high-water mark can be a little deeper."""
import os
import sys
import paths
import harness
import bench
from views import VIEWS



def measure(tag, rom, elf, script, out):
    syms = harness.symbols(elf)
    be, irq = syms['__bss_end'], syms['g_irqStack']
    TOP = syms.get('__stack_top', 0x03007F80)        # (gba.ld)
    script = script + [f"dump {be:#x} {TOP - be} {out}/{tag}_stack.bin", f"dump {irq:#x} 1024 {out}/{tag}_irq.bin"]
    harness.run(script, out, tag, rom=rom, elf=elf)
    res = []
    for name in ('stack', 'irq'):
        b = open(f"{out}/{tag}_{name}.bin", 'rb').read()
        i = 0
        while i < len(b) and b[i] == 0xA5: i += 1
        res.append((len(b), len(b) - i, i))
    (size, deep, room), (isize, ideep, iroom) = res
    print(f"{tag:8s} main stack: {size} bytes, deepest use {deep}, headroom {room};  "
          f"interrupt stack: {isize} bytes, deepest use {ideep}, headroom {iroom}")
    return room, iroom


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    floor = int(sys.argv[sys.argv.index('--min') + 1]) if '--min' in sys.argv else 256
    os.makedirs(out, exist_ok=True)
    levels = sorted({v[0] for v in VIEWS})
    dev = [l.replace('{out}', out) for l in bench.script(VIEWS, noirq=0)] + ["poke32 {g_govOff} 0", "seed 7"]
    for lv in levels:
        dev += harness.load_level(lv) + ["monkey 900 0x3FF"]
    rel = harness.boot() + ["seed 7", "monkey 3600 0x3FF"]
    rooms = [measure('test', paths.ROM, paths.ELF, dev, out),
             measure('release', paths.RELEASE_ROM, paths.RELEASE_ELF, rel, out)]
    low = min(r for r, _ in rooms)
    if low < floor or min(i for _, i in rooms) < 128:
        print(f"stackcheck.py: headroom {low} is under {floor} bytes", file=sys.stderr)
        return 1


if __name__ == '__main__':
    harness.main(main)
