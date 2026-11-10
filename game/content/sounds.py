# SPDX-License-Identifier: MIT
"""Hollowmere sound effects, all synthesized. Each entry returns
(float array in [-1,1], loop_start or None)."""
import numpy as np
from synth import *

SOUNDS = {}


def snd(name, loop=False):
    def deco(fn):
        SOUNDS[name] = (fn, loop)
        return fn
    return deco


# ------------------------------------------------------------ footsteps
def _step(seed, heavy=0.0):
    r = rng_(seed)
    n = secs(0.16)
    click = hp(noise(n, r), 2500) * env_exp(n, 0.004) * 0.5
    body = lp(noise(n, r), 400 + 200 * r.random()) * env_exp(n, 0.025) * 1.4
    thump = sine(85 + 15 * r.random() - 30 * heavy, n) * env_exp(n, 0.035 + 0.03 * heavy) * (0.8 + heavy)
    scuff = bp(noise(n, r), 1500, 4000) * env_lin(n, [(0, 0), (0.04, 0), (0.06, 0.25), (0.12, 0)])
    x = click + body + thump + scuff * (1 - heavy)
    return normalize(fade_edges(x), 0.9)


for i in range(3):
    snd(f'step{i}')(lambda i=i: (_step(100 + i), None))


def _creature_step(seed, crack=False):
    r = rng_(seed)
    n = secs(0.55)
    slap = bp(noise(n, r), 700, 2200) * env_exp(n, 0.012)
    thump = (sine(55 * (1 + 0.4 * env_exp(n, 0.02)), n) * env_exp(n, 0.09)) * 1.6
    thump += lp(noise(n, r), 180) * env_exp(n, 0.06) * 2.0
    grain = (r.random(n) < 0.25).astype(float) * r.uniform(-1, 1, n)
    drag = bp(noise(n, r) * 0.6 + grain * 0.6, 220, 1100) * env_lin(n, [(0, 0), (0.08, 0), (0.18, 0.5), (0.42, 0.25), (0.55, 0)])
    # bare and sodden: a wet slap as the foot lands, water dripping off her
    squelch = bp(noise(n, r), 900, 3200) * env_lin(n, [(0, 0), (0.01, 1.0), (0.05, 0.35), (0.12, 0)])
    squelch *= 0.6 + 0.4 * np.sin(2 * np.pi * 70 * tt(n))
    drips = np.zeros(n)
    for k in range(3):
        t0 = 0.14 + 0.11 * k + 0.05 * r.random()
        m = secs(0.05)
        f0 = 1500 + 1400 * r.random()
        f = f0 * (1 + 0.6 * env_exp(m, 0.006))
        d = np.sin(2 * np.pi * np.cumsum(f) / (len(tt(m)) / 0.05)) * env_exp(m, 0.012)
        drips += at(d, t0, n) * (0.35 - 0.08 * k)
    x = slap * 0.9 + thump + drag * 0.8 + squelch * 0.7 + drips
    if crack:
        for k in range(4):
            t0 = 0.05 + 0.025 * k + 0.01 * r.random()
            c = hp(noise(secs(0.01), r), 1500) * env_exp(secs(0.01), 0.002)
            x += at(c, t0, n) * 0.7
    x = reverb(x, size=0.6, damp=2500, mix_=0.2, tail=0.25)
    return normalize(fade_edges(x), 0.95)


snd('cstep0')(lambda: (_creature_step(200), None))
snd('cstep1')(lambda: (_creature_step(201, crack=True), None))


@snd('cbreath', loop=True)
def cbreath():
    r = rng_(300)
    n = secs(3.2)
    t = tt(n)
    out = np.zeros(n)
    for start, dur, kind in ((0.15, 0.75, 'in'), (1.05, 1.15, 'out'), (2.45, 0.6, 'in2')):
        m = secs(dur)
        e = np.sin(np.pi * np.linspace(0, 1, m)) ** 1.5
        nz = noise(m, r)
        if kind.startswith('in'):
            f = np.linspace(500, 1100, m)
            b = reson_tv(nz, f, 3.0) * 0.8 + bp(nz, 1800, 3500) * 0.12
            seg = b * e * (0.55 if kind == 'in' else 0.4)
        else:
            f = np.linspace(700, 380, m)
            b = reson_tv(nz, f, 2.5)
            growl = (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 31 * tt(m) + r.random()))) * \
                    (1 + 0.3 * lp(r.normal(0, 1, m), 20))
            sub = sine(52 + 4 * np.sin(2 * np.pi * 0.7 * tt(m)), m) * 0.5
            seg = (b * growl + sub * 0.6) * e
        out += at(seg, start, n)
    out = reverb(out, size=0.7, damp=2200, mix_=0.25, tail=0.0)[:n]
    out = loopify(normalize(out, 0.9), 0.15)
    return out, 0


@snd('cscream')
def cscream():
    r = rng_(400)
    n = secs(2.2)
    t = tt(n)
    pitch = 380 + 160 * np.clip(t / 0.25, 0, 1) - 120 * np.clip((t - 0.9) / 1.0, 0, 1)
    vib = 1 + 0.025 * np.sin(2 * np.pi * 7.5 * t) + 0.01 * lp(r.normal(0, 1, n), 30)
    src = sum(saw(pitch * vib * d, n, harmonics=20) for d in (1.0, 1.013, 0.987, 1.5))
    src = src + noise(n, r) * 0.6
    voc = reson(src, 820, 4) * 1.2 + reson(src, 1250, 5) + reson(src, 2700, 6) * 0.7
    voc = distort(voc * 1.5, 2.5)
    hiss = bp(noise(n, r), 2500, 6000) * 0.4
    env = env_lin(n, [(0, 0), (0.04, 1), (0.9, 0.85), (1.5, 0.3), (2.2, 0)])
    growl = lp(saw(70 + 10 * np.sin(2 * np.pi * 3 * t), n, 10), 600) * 0.6
    x = (voc + hiss + growl) * env
    x = reverb(x, size=1.1, damp=3500, mix_=0.35, tail=1.0)
    return normalize(fade_edges(x), 0.95), None


@snd('jumpscare')
def jumpscare():
    r = rng_(500)
    n = secs(1.5)
    t = tt(n)
    idx = 9 * np.exp(-t / 0.5) + 2
    mod = np.sin(2 * np.pi * 1470 * t) * idx
    car = np.sin(2 * np.pi * 1060 * t + mod)
    car2 = np.sin(2 * np.pi * 1420 * t + mod * 0.7)
    scream = (car + car2 * 0.7 + noise(n, r) * 0.8)
    boom = sine(110 * np.exp(-t / 0.12) + 45, n) * env_exp(n, 0.18) * 1.2
    env = env_lin(n, [(0, 0), (0.01, 1), (0.7, 0.9), (1.5, 0)])
    x = distort((scream * env) * 1.5, 4) * 0.7 + boom
    x = crush(x, 6, 2)
    return normalize(fade_edges(x), 1.0), None


# --------------------------------------------------------------- doors
@snd('door_open')
def door_open():
    r = rng_(600)
    n = secs(1.3)
    t = tt(n)
    rate = 55 + 90 * np.sin(np.pi * np.clip(t / 1.0, 0, 1)) + 20 * lp(r.normal(0, 1, n), 8)
    ph = np.cumsum(rate / SR)
    imp = np.diff(np.floor(ph), prepend=0) * r.uniform(0.5, 1.0, n)
    creak = reson(imp, 620, 12) + reson(imp, 1340, 14) * 0.8 + reson(imp, 2380, 18) * 0.5
    creak *= env_lin(n, [(0, 0), (0.05, 1), (0.95, 0.8), (1.05, 0)])
    groan = lp(noise(n, r), 300) * 0.3 * env_lin(n, [(0, 0), (0.2, 1), (1.0, 0.5), (1.1, 0)])
    thud = (sine(70, secs(0.25)) * env_exp(secs(0.25), 0.05) + lp(noise(secs(0.25), r), 250) * env_exp(secs(0.25), 0.04)) * 0.7
    creak = creak / (np.abs(creak).max() + 1e-9)
    x = creak * 0.9 + groan * 0.6 + at(thud, 1.05, n) * 0.5
    x = reverb(x, 0.6, 3000, 0.2, 0.3)
    return normalize(fade_edges(x), 0.9), None


@snd('door_close')
def door_close():
    r = rng_(610)
    n = secs(0.7)
    thud = sine(65, n) * env_exp(n, 0.07) * 1.2 + lp(noise(n, r), 300) * env_exp(n, 0.05)
    latch = reson(hp(noise(n, r), 2000) * env_exp(n, 0.003), 3200, 8)
    x = thud + at(latch, 0.02, n) * 0.8
    x = reverb(x, 0.7, 2500, 0.25, 0.3)
    return normalize(fade_edges(x), 0.9), None


@snd('door_locked')
def door_locked():
    r = rng_(620)
    n = secs(0.55)
    x = np.zeros(n)
    for k, t0 in enumerate((0.0, 0.09, 0.17, 0.3)):
        m = secs(0.06)
        c = reson(noise(m, r) * env_exp(m, 0.004), 2900 + 400 * (k % 2), 15) + \
            reson(noise(m, r) * env_exp(m, 0.004), 4400, 20) * 0.5
        thunk = lp(noise(m, r), 500) * env_exp(m, 0.01)
        x += at(c + thunk * 0.6, t0, n)
    return normalize(fade_edges(reverb(x, 0.5, 3000, 0.15, 0.1)), 0.85), None


def _metal(seed, n, partials, decays, amp=1.0):
    r = rng_(seed)
    t = tt(n)
    out = np.zeros(n)
    for f, d in zip(partials, decays):
        out += np.sin(2 * np.pi * f * t + r.random() * 6) * np.exp(-t / d) * r.uniform(0.5, 1)
    return out * amp


@snd('locker_open')
def locker_open():
    r = rng_(630)
    n = secs(0.9)
    t = tt(n)
    squeal = sine(2100 - 500 * np.clip(t / 0.35, 0, 1), n) * env_lin(n, [(0, 0), (0.03, 0.5), (0.3, 0.4), (0.38, 0)])
    squeal *= 1 + 0.5 * np.sin(2 * np.pi * 23 * t)
    clank = _metal(631, n, [310, 742, 1190, 1820, 2760], [0.25, 0.18, 0.12, 0.08, 0.05])
    hit = lp(noise(n, r), 1200) * env_exp(n, 0.015)
    x = squeal * 0.5 + at(clank * env_exp(n, 0.3) + hit, 0.36, n) * 0.9
    return normalize(fade_edges(reverb(x, 0.5, 3500, 0.2, 0.3)), 0.9), None


@snd('locker_close')
def locker_close():
    r = rng_(640)
    n = secs(0.8)
    clank = _metal(641, n, [290, 690, 1230, 1950, 2900], [0.3, 0.2, 0.12, 0.07, 0.04])
    hit = lp(noise(n, r), 900) * env_exp(n, 0.02) * 1.5
    rattle = at(_metal(642, secs(0.3), [1500, 2300, 3100], [0.03, 0.02, 0.02]), 0.12, n) * 0.4
    x = clank * env_exp(n, 0.25) + hit + rattle
    return normalize(fade_edges(reverb(x, 0.5, 3500, 0.2, 0.3)), 0.95), None


# ----------------------------------------------------------- items / ui
@snd('pickup')
def pickup():
    r = rng_(700)
    n = secs(0.9)
    t = tt(n)
    f0 = 784.0
    bell = sum(a * np.sin(2 * np.pi * f0 * k * t) * np.exp(-t / d)
               for k, a, d in ((1, 1.0, 0.45), (2.76, 0.35, 0.18), (5.4, 0.15, 0.08), (2.0, 0.3, 0.3)))
    bell2 = at(sum(a * np.sin(2 * np.pi * f0 * 1.5 * k * t) * np.exp(-t / d)
                   for k, a, d in ((1, 0.8, 0.4), (2.76, 0.25, 0.15))), 0.09, n)
    rustle = bp(noise(n, r), 1500, 5000) * env_exp(n, 0.05) * 0.4
    x = (bell + bell2 * 0.8) * 0.6 + rustle
    return normalize(fade_edges(reverb(x, 0.8, 4000, 0.3, 0.4)), 0.75), None


@snd('paper')
def paper():
    r = rng_(710)
    n = secs(0.6)
    env = np.zeros(n)
    for _ in range(14):
        t0 = r.uniform(0, 0.45)
        env += at(env_exp(secs(0.05), r.uniform(0.005, 0.02)) * r.uniform(0.3, 1), t0, n)
    crinkle = hp(noise(n, r), 1800) * env
    body = bp(noise(n, r), 400, 1500) * lp(env, 30) * 0.5
    return normalize(fade_edges(crinkle + body), 0.8), None


@snd('click')
def click():
    r = rng_(720)
    n = secs(0.06)
    c = reson(noise(n, r) * env_exp(n, 0.002), 2600, 6) + at(reson(noise(n, r) * env_exp(n, 0.002), 1900, 6), 0.018, n) * 0.6
    return normalize(fade_edges(c), 0.7), None


@snd('heartbeat')
def heartbeat():
    n = secs(0.55)
    t = tt(n)
    lub = (np.sin(2 * np.pi * 52 * t) + 0.4 * np.sin(2 * np.pi * 104 * t)) * env_ad(n, 0.01, 0.06)
    dub = at((np.sin(2 * np.pi * 44 * t) + 0.3 * np.sin(2 * np.pi * 88 * t)) * env_ad(n, 0.012, 0.08), 0.19, n) * 0.8
    x = lp(lub + dub, 180, 4)
    r = rng_(725)
    knock = lp(noise(n, r), 320) * (env_ad(n, 0.004, 0.03) + at(env_ad(n, 0.004, 0.035), 0.19, n) * 0.8)
    x = normalize(x, 1.0) + normalize(knock, 0.45)
    return normalize(fade_edges(x), 0.95), None


@snd('ui_move')
def ui_move():
    n = secs(0.05)
    return normalize(sine(1300, n) * env_exp(n, 0.012), 0.5), None


@snd('ui_select')
def ui_select():
    n = secs(0.25)
    t = tt(n)
    x = sine(880, n) * env_exp(n, 0.06) + at(sine(1320, n) * env_exp(n, 0.08), 0.06, n)
    return normalize(reverb(x, 0.6, 4000, 0.25, 0.2), 0.55), None


@snd('ui_back')
def ui_back():
    n = secs(0.2)
    x = sine(990, n) * env_exp(n, 0.04) + at(sine(660, n) * env_exp(n, 0.06), 0.05, n)
    return normalize(x, 0.5), None


# ------------------------------------------------------------ ambience
@snd('amb_ward', loop=True)
def amb_ward():
    r = rng_(800)
    n = secs(9.0)
    t = tt(n)
    pn = pink(n, r)
    f = 420 + 220 * np.sin(2 * np.pi * t / 4.5) + 120 * np.sin(2 * np.pi * t / 1.7 + 1)
    wind = reson_tv(pn, f, 2.2) * (0.55 + 0.45 * np.sin(2 * np.pi * t / 3.0) ** 2)
    whistle = sine(f * 2.1, n) * 0.03 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 2.3))
    hum = (sine(49, n) * 0.25 + sine(98.5, n) * 0.12) * (0.8 + 0.2 * np.sin(2 * np.pi * t / 7))
    rum = lp(brown(n, r), 90) * 0.5
    x = wind * 1.0 + whistle + hum + rum
    return loopify(normalize(x, 0.9), 1.0), 0


@snd('amb_basement', loop=True)
def amb_basement():
    r = rng_(810)
    n = secs(9.0)
    t = tt(n)
    hum = sum(a * np.sin(2 * np.pi * f * t + p) for f, a, p in
              ((50, 0.5, 0), (100.3, 0.35, 1), (150, 0.2, 2), (200.6, 0.1, 3), (250, 0.06, 1)))
    hum *= 0.8 + 0.2 * np.sin(2 * np.pi * t / 2.9)
    rum = lp(brown(n, r), 120) * 0.8
    ring = reson(noise(n, r), 1730, 60) * 0.25 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 5.3))
    hiss = hp(pink(n, r), 3000) * 0.05
    x = hum * 0.7 + rum + ring + hiss
    # a couple of distant knocks in pipes
    for t0 in (2.2, 6.4):
        m = secs(0.4)
        k = _metal(811 + int(t0), m, [180, 410, 870], [0.2, 0.1, 0.06]) * env_exp(m, 0.08)
        x += at(k, t0, n) * 0.35
    return loopify(normalize(x, 0.9), 1.0), 0


@snd('amb_chapel', loop=True)
def amb_chapel():
    r = rng_(820)
    n = secs(10.0)
    t = tt(n)
    drone = sum(a * saw(f * (1 + 0.002 * np.sin(2 * np.pi * t / p)), n, 8) for f, a, p in
                ((55, 0.5, 5.1), (82.4, 0.3, 3.7), (110.3, 0.25, 6.3), (130.8, 0.12, 4.1)))
    drone = lp(drone, 500)
    choir_src = sum(saw(f * (1 + 0.004 * np.sin(2 * np.pi * t * 4.8 + i)), n, 14) for i, f in enumerate((220, 261.6, 329.6, 246.9)))
    vowel = reson(choir_src, 700, 5) + reson(choir_src, 1100, 6) * 0.6 + reson(choir_src, 2600, 8) * 0.25
    vowel *= 0.15 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 10.0 - 1.2) ** 2)
    water = bp(pink(n, r), 300, 1500) * (0.3 + 0.3 * np.sin(2 * np.pi * t / 1.9) ** 2) * 0.4
    x = drone + vowel + water
    x = reverb(x, 1.2, 2500, 0.3, 0.0)[:n]
    return loopify(normalize(x, 0.9), 1.0), 0


@snd('rain', loop=True)
def rain():
    r = rng_(830)
    n = secs(5.0)
    x = hp(pink(n, r), 900) * 0.6 + lp(noise(n, r), 2500) * 0.15
    drops = (r.random(n) < 0.004) * r.uniform(-1, 1, n)
    x += reson(drops, 2800, 4) * 0.6
    return loopify(normalize(x, 0.9), 0.6), 0


@snd('drip')
def drip():
    n = secs(0.5)
    t = tt(n)
    f = 1400 * np.exp(-t / 0.02) + 700
    x = sine(f, n) * env_ad(n, 0.001, 0.025)
    x += at(sine(1900, secs(0.05)) * env_exp(secs(0.05), 0.008), 0.06, n) * 0.4
    return normalize(fade_edges(reverb(x, 1.0, 3500, 0.45, 0.5)), 0.7), None


@snd('thunder')
def thunder():
    r = rng_(840)
    n = secs(4.0)
    crack = hp(noise(n, r), 800) * env_exp(n, 0.06) * 0.8
    rum = lp(brown(n, r), 160) * env_lin(n, [(0, 0), (0.1, 1), (0.6, 0.7), (1.2, 0.9), (2.5, 0.4), (4.0, 0)]) * 2.0
    x = crack + rum
    return normalize(fade_edges(reverb(x, 1.3, 1500, 0.3, 0.5)), 0.95), None


@snd('whisper')
def whisper():
    r = rng_(850)
    n = secs(2.4)
    t = tt(n)
    syl = np.zeros(n)
    tpos = 0.12
    while tpos < 1.9:
        dur = r.uniform(0.08, 0.26)
        m = secs(dur)
        syl += at(np.sin(np.pi * np.linspace(0, 1, m)) ** 0.8 * r.uniform(0.5, 1.0), tpos, n)
        tpos += dur + r.uniform(0.02, 0.14)
    syl = np.clip(syl, 0, 1)
    f1 = 500 + 900 * np.clip(lp(r.normal(0, 1, n), 6) * 4, -0.4, 0.4)
    f2 = 1500 + 2200 * np.clip(lp(r.normal(0, 1, n), 6) * 4, -0.35, 0.35)
    nz = noise(n, r)
    v = reson_tv(nz, f1, 6) + reson_tv(nz, f2, 8) * 0.7
    sib = hp(noise(n, r), 4000) * np.clip(lp(r.normal(0, 1, n), 3) * 6, 0, 1) * 0.35
    x = v * syl + sib * syl
    x = reverb(x, 1.0, 3000, 0.5, 0.8)
    return normalize(fade_edges(x), 0.8), None


@snd('musicbox')
def musicbox():
    n = secs(1.8)
    t = tt(n)
    f = 523.25
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.7)
         + 0.25 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / 0.25)
         + 0.12 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.05)
         + 0.08 * np.sin(2 * np.pi * f * 8.9 * t) * np.exp(-t / 0.02))
    x *= env_ad(n, 0.002, 10)
    return normalize(fade_edges(x, 0.001, 0.05), 0.9), None


@snd('piano')
def piano():
    """Dark felt piano note recorded at C5 (used for low stingers via pitch)."""
    r = rng_(860)
    n = secs(2.5)
    t = tt(n)
    f = 523.25
    x = np.zeros(n)
    for k, a in ((1, 1.0), (2, 0.5), (3, 0.25), (4, 0.15), (5, 0.08), (6, 0.04)):
        fk = f * k * (1 + 0.0004 * k * k)
        x += a * np.sin(2 * np.pi * fk * t) * np.exp(-t / (1.2 / k ** 0.7))
    x += lp(noise(n, r), 1500) * env_exp(n, 0.008) * 0.3
    x = lp(x, 2500)
    return normalize(fade_edges(reverb(x, 1.0, 2500, 0.25, 0.0)[:n], 0.001, 0.2), 0.9), None


@snd('stinger')
def stinger():
    """Low dissonant cluster + sub hit for scares."""
    r = rng_(870)
    n = secs(4.0)
    t = tt(n)
    x = np.zeros(n)
    for f in (65.4, 69.3, 92.5, 98.0):
        x += karplus(f, n, r, decay=0.9985, bright=0.6) * 0.6
    sub = sine(36 + 20 * np.exp(-t / 0.2), n) * env_exp(n, 0.9) * 1.2
    hit = lp(noise(n, r), 600) * env_exp(n, 0.05)
    x = distort(x + sub + hit, 1.8)
    x = reverb(x, 1.3, 1800, 0.35, 0.5)
    return normalize(fade_edges(x), 0.98), None


@snd('braam')
def braam():
    r = rng_(880)
    n = secs(3.0)
    t = tt(n)
    x = sum(saw(f * (1 + 0.003 * np.sin(2 * np.pi * 0.5 * t + i)), n, 30) for i, f in enumerate((41.2, 41.5, 61.7, 82.4)))
    x = lp(distort(x * 2, 3), 900)
    x *= env_lin(n, [(0, 0), (0.05, 1), (1.5, 0.7), (3.0, 0)])
    return normalize(fade_edges(reverb(x, 1.2, 1500, 0.3, 0.8)), 0.98), None


@snd('generator')
def generator():
    r = rng_(890)
    n = secs(3.5)
    t = tt(n)
    rpm = np.clip(t / 2.2, 0, 1) ** 0.6
    f = 8 + 42 * rpm
    chug = (0.5 + 0.5 * np.sign(np.sin(phase_of(f, n)))) * lp(noise(n, r), 400)
    whine = sine(f * 6, n) * 0.25 * rpm
    hum = (sine(50, n) + 0.5 * sine(100, n)) * np.clip((t - 1.8) / 1.0, 0, 1) * 0.6
    cough = at(lp(noise(secs(0.3), r), 300) * env_exp(secs(0.3), 0.05), 0.15, n) * 1.5
    x = chug * 0.9 + whine + hum + cough
    x *= env_lin(n, [(0, 0), (0.05, 1), (3.2, 1), (3.5, 0)])
    return normalize(fade_edges(reverb(x, 0.8, 2500, 0.2, 0.3)), 0.9), None


@snd('fuse')
def fuse():
    r = rng_(900)
    n = secs(0.9)
    t = tt(n)
    clunk = (lp(noise(n, r), 900) * env_exp(n, 0.02) + sine(140, n) * env_exp(n, 0.05)) * 1.2
    buzz = bp(square(120, n, 25), 200, 3000) * env_lin(n, [(0, 0), (0.1, 0), (0.12, 0.6), (0.7, 0.3), (0.9, 0)])
    crackle = hp((r.random(n) < 0.01) * r.uniform(-1, 1, n), 2000) * env_lin(n, [(0, 0), (0.1, 1), (0.5, 0.2), (0.9, 0)]) * 2
    return normalize(fade_edges(clunk + buzz + crackle), 0.9), None


@snd('static', loop=True)
def static():
    r = rng_(910)
    n = secs(1.5)
    x = bp(noise(n, r), 400, 3500) * (0.7 + 0.3 * lp(r.normal(0, 1, n), 10) * 4)
    x += (r.random(n) < 0.003) * r.uniform(-1, 1, n) * 3
    return loopify(normalize(x, 0.8), 0.2), 0


@snd('pbreath', loop=True)
def pbreath():
    r = rng_(920)
    n = secs(1.4)
    t = tt(n)
    e = np.clip(np.sin(2 * np.pi * t / 0.7), 0, 1) ** 1.2 + 0.6 * np.clip(-np.sin(2 * np.pi * t / 0.7), 0, 1) ** 1.5
    x = (bp(noise(n, r), 500, 1600) + bp(noise(n, r), 1800, 3000) * 0.3) * e
    return loopify(normalize(x, 0.8), 0.1), 0


@snd('stairs')
def stairs():
    n = secs(3.0)
    x = np.zeros(n)
    for k in range(7):
        x += at(_step(950 + k, heavy=0.3) * (1 - 0.08 * k), 0.15 + 0.33 * k, n)
    x = reverb(x, 1.1, 2500, 0.35, 0.0)[:n]
    return normalize(fade_edges(x), 0.85), None


@snd('bang')
def bang():
    r = rng_(960)
    n = secs(1.4)
    x = sine(55, n) * env_exp(n, 0.12) * 1.5 + lp(noise(n, r), 500) * env_exp(n, 0.06) * 1.2
    x += at(_metal(961, secs(0.6), [220, 530, 970], [0.15, 0.1, 0.06]) * 0.3, 0.0, n)
    return normalize(fade_edges(reverb(x, 1.2, 2000, 0.4, 0.8)), 0.98), None


@snd('glass')
def glass():
    r = rng_(970)
    n = secs(1.2)
    x = hp(noise(n, r), 3000) * env_exp(n, 0.04) * 0.8
    for k in range(30):
        t0 = r.uniform(0, 0.6) ** 1.5
        m = secs(0.15)
        f = r.uniform(2500, 7000)
        x += at(np.sin(2 * np.pi * f * tt(m)) * env_exp(m, r.uniform(0.01, 0.04)) * r.uniform(0.2, 0.6), t0, n)
    return normalize(fade_edges(reverb(x, 0.9, 5000, 0.3, 0.4)), 0.9), None


@snd('bell')
def bell():
    n = secs(6.0)
    t = tt(n)
    f = 220.0
    parts = ((0.5, 0.6, 4.0), (1.0, 1.0, 3.0), (1.19, 0.5, 2.0), (1.5, 0.4, 1.6), (2.0, 0.6, 1.3),
             (2.52, 0.3, 0.9), (3.0, 0.25, 0.7), (4.07, 0.15, 0.4))
    x = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t / d) for k, a, d in parts)
    x *= 1 + 0.05 * np.sin(2 * np.pi * 2.1 * t)
    x = reverb(x, 1.4, 3000, 0.3, 0.0)[:n]
    return normalize(fade_edges(x, 0.001, 0.5), 0.9), None


@snd('chain')
def chain():
    r = rng_(980)
    n = secs(0.9)
    x = np.zeros(n)
    for k in range(9):
        t0 = 0.05 * k + r.uniform(0, 0.03)
        m = secs(0.08)
        x += at(_metal(981 + k, m, [r.uniform(2000, 3500), r.uniform(4000, 6000)], [0.02, 0.01]), t0, n) * (1 - k / 10)
    return normalize(fade_edges(reverb(x, 0.6, 5000, 0.2, 0.2)), 0.8), None


@snd('slam')
def slam():
    r = rng_(990)
    n = secs(1.5)
    x = sine(60, n) * env_exp(n, 0.1) * 1.4 + lp(noise(n, r), 1200) * env_exp(n, 0.03) * 1.5
    x += reson(noise(n, r) * env_exp(n, 0.01), 180, 3) * 1.0
    return normalize(fade_edges(reverb(x, 1.1, 2500, 0.4, 0.8)), 1.0), None


@snd('wind_gust')
def wind_gust():
    r = rng_(995)
    n = secs(3.0)
    t = tt(n)
    f = 500 + 500 * np.sin(np.pi * t / 3.0)
    x = reson_tv(pink(n, r), f, 2.5) * np.sin(np.pi * t / 3.0) ** 2
    return normalize(fade_edges(x), 0.85), None


@snd('distant_scream')
def distant_scream():
    x, _ = cscream()
    x = lp(x, 1200)
    x = reverb(x, 1.4, 1200, 0.6, 1.0)
    return normalize(x, 0.8), None


@snd('lantern')
def lantern():
    """Creaking lantern handle swing + faint hiss (positional loop)."""
    r = rng_(997)
    n = secs(2.0)
    t = tt(n)
    hiss = bp(noise(n, r), 2000, 5000) * 0.02
    sw = np.zeros(n)
    for t0 in (0.2, 1.2):
        m = secs(0.35)
        tm = tt(m)
        rate = 90 + 40 * np.sin(np.pi * tm / 0.35)
        ph = np.cumsum(rate / SR)
        imp = np.diff(np.floor(ph), prepend=0)
        sw += at(reson(imp, 2400, 20) + reson(imp, 3600, 25) * 0.5, t0, n) * 0.8
    return loopify(normalize(hiss + sw, 0.8), 0.1), 0


@snd('creak')
def creak():
    """A floorboard settling somewhere in the house."""
    r = rng_(990)
    n = secs(0.9)
    t = tt(n)
    f = 140 + 60 * np.sin(2 * np.pi * 1.3 * t) + 25 * np.sin(2 * np.pi * 7.0 * t)
    ph = phase_of(f, n)
    x = np.sign(np.sin(ph)) * 0.25 + np.sin(ph * 2.01) * 0.2
    x = bp(x + noise(n, r) * 0.15, 300, 1800) * env_lin(n, [(0, 0), (0.08, 1), (0.5, 0.7), (0.9, 0)])
    x *= (0.6 + 0.4 * (np.sin(2 * np.pi * 23 * t) > 0))
    return normalize(fade_edges(reverb(x, 0.9, 2200, 0.35, 0.7)), 0.7), None


# ------------------------------------------------------------ lures
@snd('musicbox_phrase')
def musicbox_phrase():
    """The lullaby's first phrase on the music box, heard through a floor or a
    door: played from a place by the scripts so the player can follow it."""
    import music
    base, _ = musicbox()
    beat = 0.9
    notes = music.MELODY[:9]
    total = sum(d for _, d in notes) * beat + 2.0
    n = secs(total)
    out = np.zeros(n)
    t = 0.0
    src = np.arange(len(base))
    for m, d in notes:
        ratio = 2.0 ** ((m - 72) / 12.0)
        L = int(len(base) / ratio)
        note = np.interp(np.arange(L) * ratio, src, base)
        i0 = int(t * SR)
        k = min(L, n - i0)
        out[i0:i0 + k] += note[:k] * (0.85 + 0.15 * np.random.default_rng(int(t * 10)).random())
        t += d * beat
    out = lp(out, 2600)
    out = reverb(out, 1.2, 2200, 0.35, 0.0)[:n]
    return normalize(fade_edges(out, 0.002, 0.6), 0.85), None


@snd('phone_ring')
def phone_ring():
    """One ring of an old desk telephone: the clapper drumming between two
    bells for two seconds, then the bells dying away."""
    n = secs(2.7)
    x = np.zeros(n)
    rate = 19.0
    for k in range(int(2.0 * rate)):
        i0 = int(k / rate * SR)
        m = n - i0
        tt_ = np.arange(m) / SR
        f = 1170.0 if k % 2 == 0 else 1430.0
        tone = sum(a * np.sin(2 * np.pi * f * p * tt_ + p) * np.exp(-tt_ / d)
                   for p, a, d in ((1.0, 1.0, 0.30), (2.71, 0.35, 0.09), (5.2, 0.18, 0.03)))
        x[i0:] += tone * 0.45
        x[i0:i0 + 40] += np.random.default_rng(k).standard_normal(min(40, m)) * 0.25    # the clapper's tick
    x = hp(x, 300)
    x = reverb(x, 0.8, 4000, 0.22, 0.0)[:n]
    return normalize(fade_edges(x, 0.001, 0.3), 0.9), None


@snd('clock_strike')
def clock_strike():
    """A tall-case clock striking once: a deep rod gong, the hammer's knock."""
    n = secs(3.6)
    t = tt(n)
    f = 146.8
    parts = ((1.0, 1.0, 2.6), (2.0, 0.45, 1.6), (2.76, 0.5, 1.2), (3.01, 0.3, 1.0), (4.1, 0.25, 0.6),
             (5.43, 0.15, 0.35), (6.8, 0.08, 0.2))
    x = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t / d) for k, a, d in parts)
    x *= 1 + 0.06 * np.sin(2 * np.pi * 1.3 * t)
    x += lp(np.random.default_rng(77).standard_normal(n), 900) * np.exp(-t / 0.015) * 0.6
    x = reverb(x, 1.3, 2600, 0.3, 0.0)[:n]
    return normalize(fade_edges(x, 0.001, 0.4), 0.9), None
