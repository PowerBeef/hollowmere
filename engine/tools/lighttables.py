# SPDX-License-Identifier: MIT
"""Flashlight beam and night-vision base tables (consumed by the engine)."""
import numpy as np

FOCAL = 160          # physical px per tile (rows)
VIEW_W = 240
PLANE = 0.75
NCONE = 16
NPAIR_F = 35         # floor row pairs below the eye line
NPAIR_C = 29         # ceiling row pairs above it
EYE = 1.0            # eye height (tiles); rooms are 2 tiles tall


def camx(col):
    return 2 * (col + 0.5) / VIEW_W - 1


def cone_of(col):
    return min(NCONE - 1, int(abs(camx(col)) * NCONE))


def cone(theta_deg):
    # bright core, soft edge
    inner, outer = 6.0, 34.0
    if theta_deg <= inner:
        return 1.0
    t = min(1.0, (theta_deg - inner) / (outer - inner))
    s = t * t * (3 - 2 * t)
    return 1.0 - 0.82 * s


def falloff(d):
    return np.exp(-max(0.0, d - 1.3) * 0.24)


def spill(d):
    return 0.28 * np.exp(-d * 0.40)


def to_level(i):
    # perceptual mapping of intensity to 0..255 (engine scales to 0..31)
    return int(round(255 * min(1.0, max(0.0, i)) ** 0.95))


def build():
    beamW = np.zeros((NCONE, 256), np.uint8)
    beamF = np.zeros((NCONE, NPAIR_F), np.uint8)
    beamC = np.zeros((NCONE, NPAIR_F), np.uint8)
    nvW = np.zeros(256, np.uint8)
    nvF = np.zeros(NPAIR_F, np.uint8)
    for c in range(NCONE):
        th_h = np.degrees(np.arctan((c + 0.5) / NCONE * PLANE))
        for di in range(256):
            d = (di + 0.5) / 16.0
            beamW[c, di] = to_level(falloff(d) * cone(th_h) + spill(d))
        for j in range(NPAIR_F):
            k = 2 * j + 1
            d = EYE * FOCAL / k
            th_v = np.degrees(np.arctan(k / FOCAL))
            aim = 2.5   # beam aimed at the middle of the (pitched) view
            tf = np.hypot(th_h, th_v - aim)
            tc = np.hypot(th_h, th_v + aim)
            # floor seen at grazing angle receives a little less light
            graze = 0.75 + 0.25 * min(1.0, k / 40.0)
            beamF[c, j] = to_level((falloff(d) * cone(tf) + spill(d)) * graze)
            beamC[c, j] = to_level((falloff(d) * cone(tc) * 0.6 + spill(d)) * graze * 0.8)
    for di in range(256):
        d = (di + 0.5) / 16.0
        nvW[di] = int(round(5.2 * np.exp(-d * 0.5)))
    for j in range(NPAIR_F):
        d = EYE * FOCAL / (2 * j + 1)
        nvF[j] = int(round(4.6 * np.exp(-d * 0.5)))
    return beamW, beamF, beamC, nvW, nvF
