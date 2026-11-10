# SPDX-License-Identifier: MIT
"""Sounds: SOUNDS maps a name to (function, loops). The function returns
(samples in -1..1 at synth.SR hertz, the sample a loop restarts from or None)."""
import numpy as np
from synth import SR, secs

SOUNDS = {}


def tone(freq, length, decay):
    n = secs(length)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * t) * np.exp(-t / decay) * 0.8


SOUNDS['step'] = (lambda: (tone(90, 0.12, 0.03), None), False)
SOUNDS['door'] = (lambda: (tone(140, 0.30, 0.08) + tone(55, 0.30, 0.10), None), False)
SOUNDS['chime'] = (lambda: (tone(880, 0.6, 0.20) + 0.5 * tone(1320, 0.6, 0.15), None), False)
