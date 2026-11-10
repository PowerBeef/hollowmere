# SPDX-License-Identifier: MIT
"""Run the headless test harness from Python.

    import harness
    r = harness.run(["run 100", "peek32 {g_vblanks}", "expect8 {g_quality} <= 7"], out)
    r.values()      # the numbers printed by the peeks, in order

Scripts may name symbols as {symbol} or {symbol+offset}; they are looked up in
the ELF of the ROM being run. run() writes the script, the harness's output
and its error stream into the output folder (never into memory: a crashed ROM
can log a great deal) and raises HarnessError when the harness reports a
failure, unless the caller says which exit codes it accepts.

Exit codes of the harness: 0 fine, 1 an expectation failed, 2 a usage or
script error, 3 the emulator reported errors (the ROM crashed).
"""
import os
import re
import subprocess
import sys

import paths


class HarnessError(Exception):
    pass


_syms = {}


def emulator():
    """The emulator the harness is built on, e.g. 'mGBA 0.10.2' (every timing the tools report is its model of the hardware)."""
    try:
        return subprocess.check_output([paths.HARNESS, '--version'], stderr=subprocess.DEVNULL).decode().strip() or 'mGBA'
    except (OSError, subprocess.CalledProcessError):
        return 'mGBA'


def symbols(elf=None):
    elf = elf or paths.ELF
    if elf not in _syms:
        if not os.path.exists(elf):
            raise HarnessError(f"no ELF at {os.path.relpath(elf)}: build it first (make test-rom)")
        d = {}
        for line in subprocess.check_output(['arm-none-eabi-nm', elf]).decode().splitlines():
            p = line.split()
            if len(p) == 3:
                d[p[2]] = int(p[0], 16)
        _syms[elf] = d
    return _syms[elf]


def expand(text, elf=None):
    """Replace {symbol} and {symbol+offset} with addresses."""
    syms = symbols(elf)

    def rep(m):
        name, off = m.group(1), m.group(2)
        if name not in syms:
            raise HarnessError(f"unknown symbol {name}: not in {os.path.relpath(elf or paths.ELF)} "
                               f"(the debug hooks are only in the test ROM)")
        return hex(syms[name] + (int(off, 0) if off else 0))
    return re.sub(r'\{([A-Za-z_][A-Za-z_0-9]*)(?:\+(0x[0-9a-fA-F]+|[0-9]+))?\}', rep, text)


class Result:
    def __init__(self, text, code, folder, name):
        self.text, self.code, self.folder, self.name = text, code, folder, name
        self.lines = text.split('\n')

    def values(self):
        """The numbers printed by peeks, in order."""
        return [int(l.split('= ')[1]) for l in self.lines if re.match(r'^\S+ = -?\d+$', l)]

    def sections(self):
        """[(label, [values])]: the peeks that follow each echoed line."""
        out, cur = [], None
        for l in self.lines:
            l = l.strip()
            if not l or l.startswith(('EMULOG', 'CMP ', 'EXPECT', 'regs ', 'frame ', 'harness:')):
                continue
            if re.match(r'^\S+ = -?\d+$', l):
                if cur is not None:
                    cur[1].append(int(l.split('= ')[1]))
            else:
                cur = (l, [])
                out.append(cur)
        return out

    def cmps(self):
        """{name: (count, x0, y0, x1, y1)} from cmp commands."""
        d = {}
        for l in self.lines:
            if l.startswith('CMP '):
                p = l.split()
                d[p[1]] = tuple(int(v) for v in p[2:7])
        return d

    def failures(self):
        return [l for l in self.lines if l.startswith('EXPECT FAILED')]

    def emu_errors(self):
        for l in self.lines:
            m = re.match(r'EMULOG errors=(\d+)', l)
            if m:
                return int(m.group(1))
        return 0


def run(script, out, name='run', rom=None, elf=None, save=None, timeout=900, lenient=False, ok=(0,)):
    """Run a script (a string or a list of lines) and return its Result."""
    rom = rom or paths.ROM
    if not elf:
        elf = paths.ELF if rom == paths.ROM else paths.RELEASE_ELF if rom == paths.RELEASE_ROM else rom[:-4] + '.elf'
    if not os.path.exists(paths.HARNESS):
        raise HarnessError("the harness is not built: make harness")
    if not os.path.exists(rom):
        raise HarnessError(f"no ROM at {os.path.relpath(rom)}: build it first (make test-rom)")
    os.makedirs(out, exist_ok=True)
    text = script if isinstance(script, str) else '\n'.join(script) + '\n'
    base = os.path.join(out, name)
    open(base + '.txt', 'w').write(expand(text, elf))
    cmd = [paths.HARNESS] + (['--lenient'] if lenient else []) + [rom, base + '.txt'] + ([save] if save else [])
    with open(base + '.out', 'w') as fo, open(base + '.err', 'w') as fe:
        try:
            p = subprocess.run(cmd, stdout=fo, stderr=fe, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise HarnessError(f"{name}: no end after {timeout} s (the ROM hung?); see {base}.out")
    r = Result(open(base + '.out').read(), p.returncode, out, name)
    if p.returncode not in ok:
        why = {1: "an expectation failed", 2: "script or usage error", 3: "the emulator reported errors (a crash?)"}
        detail = r.failures() + [l for l in r.lines if l.startswith(('EMULOG error', 'harness:'))][:6]
        err = open(base + '.err').read().strip().split('\n')[-3:]
        raise HarnessError(f"{name}: {why.get(p.returncode, 'exit %d' % p.returncode)}\n  " +
                           '\n  '.join(x for x in detail + err if x) + f"\n  (script and output: {base}.txt, .out)")
    return r


def main(fn):
    """Run a tool's main function; a harness failure ends it with a message and exit 1."""
    try:
        code = fn()
    except HarnessError as e:
        print(f"{os.path.basename(sys.argv[0])}: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(code or 0)


# ------------------------------------------------------------ script pieces
def boot():
    """From power-on to the first level (the game's tests/boot.txt)."""
    return open(paths.BOOT).read().splitlines()


def teleport(x, y, deg, settle=8):
    """Debug command 2: stand at (x, y) tiles facing deg. One debug command is
    taken per logic update and updates come in batches with each rendered
    frame, so the script waits `settle` frames before the next command."""
    return [f"poke32 {{g_debugA}} {int(x * 256)}", f"poke32 {{g_debugB}} {int(y * 256)}",
            f"poke32 {{g_debugC}} {int(deg / 360 * 65536) & 65535}", "poke32 {g_debugCmd} 2", f"run {settle}"]


def load_level(level, frames=420):
    return [f"poke32 {{g_debugA}} {level}", "poke32 {g_debugCmd} 4", f"run {frames}"]


def dismiss(settle=8):
    """Debug command 5: send the enemy away and keep it away."""
    return ["poke32 {g_debugCmd} 5", f"run {settle}"]


FULL_DETAIL = ["poke32 {g_govOff} 1", "poke32 {g_lodScale} 256", "poke32 {g_floorSplit} 0", "poke32 {g_wallHalfLh} 0",
               "poke32 {g_halfDist} 147456", "poke32 {g_fullC0} 0", "poke32 {g_fullC1} 240", "poke32 {g_vhalf} 0"]
