# SPDX-License-Identifier: MIT
"""Regression tests: the mixer's voices."""
import struct
import subprocess

import paths
import harness
import hm

# Voice in engine/src/audio.h (48 bytes; a static assert there keeps the size)
VOICE = 48
V = dict(data=(0, 'I'), pos=(4, 'I'), inc=(8, 'I'), end=(12, 'I'), loopLen=(16, 'I'), volL=(20, 'h'), volR=(22, 'h'), id=(24, 'H'),
         active=(26, 'B'), prio=(27, 'B'), serial=(28, 'H'), is3d=(30, 'B'), fadeL=(40, 'h'), fadeR=(42, 'h'), fadeRate=(44, 'h'), music=(46, 'B'))
MIX_LEN = 224                       # samples mixed per frame


def table(rom, elf):
    """(number of voices, [(data address, samples, loops)] of every sound) from the ROM."""
    out = subprocess.check_output(['arm-none-eabi-nm', '-S', elf]).decode()
    sym = {p[3]: (int(p[0], 16), int(p[1], 16)) for p in (l.split() for l in out.splitlines()) if len(p) == 4}
    addr, size = sym['snd_defs']
    raw = open(rom, 'rb').read()[addr - 0x08000000:addr - 0x08000000 + size]
    sounds = [struct.unpack_from('<IIIB', raw, 16 * i) for i in range(size // 16)]
    return sym['g_voices'][1] // VOICE, [(d, n, loop) for d, n, _, loop in sounds]


def voice_pokes(i, **f):
    """Script lines that set up voice i (switched on last)."""
    f = dict(dict(pos=0, inc=4096, loopLen=0, id=0, prio=255, serial=7000 + i, is3d=0, fadeRate=0, music=0), **f)
    f['fadeL'], f['fadeR'] = f['volL'], f['volR']
    L = [f"poke8 {{g_voices+{i * VOICE + V['active'][0]}}} 0"]
    for k, val in f.items():
        off, fmt = V[k]
        L.append(f"poke{8 * struct.calcsize(fmt)} {{g_voices+{i * VOICE + off}}} {val & 0xFFFFFFFF}")
    return L + [f"poke8 {{g_voices+{i * VOICE + V['active'][0]}}} 1"]


def test_quiet_voice_under_the_limiter(t):
    """With enough loud voices the limiter scales a quiet one down to
    nothing. It still plays on and ends in its time, instead of standing
    still until the loud ones stop."""
    rom, elf = paths.ROM, paths.ELF
    import os
    if os.environ.get('ROM'):
        rom, elf = os.environ['ROM'], os.environ.get('ELF', os.environ['ROM'][:-4] + '.elf')
    nvoices, sounds = table(rom, elf)
    longest = max(sounds, key=lambda s: s[1])
    short = min((s for s in sounds if 1500 < s[1] < 5000 and not s[2]), key=lambda s: s[1])
    frames = short[1] // MIX_LEN + 4
    quiet = nvoices - 1
    L = hm.boot() + hm.dismiss() + ["run 300", "poke32 {g_dbgFreeze} 4000", "run 4"]
    for i in range(nvoices - 1):
        L += voice_pokes(i, data=longest[0], end=longest[1] << 12, loopLen=longest[1] << 12, volL=256, volR=256)
    L += voice_pokes(quiet, data=short[0], end=short[1] << 12, volL=2, volR=2)
    L += ["run 6", f"peek32 {{g_voices+{quiet * VOICE + V['pos'][0]}}}", f"run {frames}", f"peek8 {{g_voices+{quiet * VOICE + V['active'][0]}}}"]
    pos, active = t.run(L).values()
    t.check(pos >= 4 * MIX_LEN << 12, f"after 6 frames the quiet voice is at sample {pos >> 12}: it is not running")
    t.check(not active, f"the quiet voice ({short[1]} samples) is still on after {frames + 6} frames")


def test_voices_stay_sane_through_random_play(t):
    """A minute of random input in every chapter, the voice table read twice
    a second: every voice in use points into its sound, moves, and a sound
    that does not loop is gone when its length has played."""
    nvoices, sounds = table(paths.ROM, paths.ELF)
    L = hm.boot() + ["seed 11"]
    snaps = 0
    for level in range(4):
        L += (hm.load_level(level) if level else []) + ["run 200"]
        for k in range(120):
            L += ["monkey 30 0x3FF", f"dump {{g_voices}} {nvoices * VOICE} {{out}}/v{snaps:04d}.bin"]
            snaps += 1
    t.run(L, ok=(0,))
    seen = {}                       # (voice, serial) -> first snapshot it was seen in
    used = 0
    for n in range(snaps):
        raw = open(f"{t.out}/v{n:04d}.bin", 'rb').read()
        for i in range(nvoices):
            f = {k: struct.unpack_from('<' + fmt, raw, i * VOICE + off)[0] for k, (off, fmt) in V.items()}
            if not f['active']:
                continue
            used += 1
            where = f"snapshot {n}, voice {i} (sound {f['id']})"
            t.check(f['id'] < len(sounds) and f['data'] == sounds[f['id']][0], f"{where}: data pointer {f['data']:#x} is not its sound's")
            length = sounds[f['id']][1] << 12
            t.check(f['end'] == length and f['pos'] < length and f['inc'] > 0, f"{where}: position {f['pos']:#x} of {f['end']:#x}, step {f['inc']}")
            t.check(f['loopLen'] <= length, f"{where}: loops over {f['loopLen']:#x} of {length:#x}")
            t.check(0 <= f['volL'] <= 256 and 0 <= f['volR'] <= 256, f"{where}: volumes {f['volL']}, {f['volR']}")
            if not f['loopLen']:
                first = seen.setdefault((i, f['serial']), n)
                lasts = length / f['inc'] / MIX_LEN                    # frames
                t.check((n - first) * 30 <= lasts + 90, f"{where}: a {lasts:.0f}-frame sound still playing after {(n - first) * 30} frames")
    t.check(used > 300, f"only {used} voices seen in use")
