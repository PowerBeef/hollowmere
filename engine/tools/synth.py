# SPDX-License-Identifier: MIT
"""Small synthesis toolkit for Hollowmere's procedurally generated audio."""
import numpy as np
from scipy.signal import butter, lfilter, sosfilt

SR = 16777216 / 1254.0  # 13379 Hz (GBA timer-driven mixing rate, 224 samples a frame)


def secs(s):
    return int(round(s * SR))


def tt(n):
    return np.arange(n) / SR


def rng_(seed):
    return np.random.default_rng(seed)


def noise(n, rng):
    return rng.uniform(-1, 1, n)


def pink(n, rng):
    w = rng.normal(0, 1, n)
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    x = lfilter(b, a, w)
    return x / (np.abs(x).max() + 1e-9)


def brown(n, rng):
    x = np.cumsum(rng.normal(0, 1, n))
    x = x - lfilter([1], [1, -0.995], x) * 0.005   # leak
    x = hp(x, 15)
    return x / (np.abs(x).max() + 1e-9)


def _sos(kind, f, order=2):
    nyq = SR / 2
    if isinstance(f, (tuple, list)):
        wn = [min(0.99, max(1e-4, v / nyq)) for v in f]
    else:
        wn = min(0.99, max(1e-4, f / nyq))
    return butter(order, wn, kind, output='sos')


def lp(x, f, order=2):
    return sosfilt(_sos('low', f, order), x)


def hp(x, f, order=2):
    return sosfilt(_sos('high', f, order), x)


def bp(x, lo, hi, order=2):
    return sosfilt(_sos('band', (lo, hi), order), x)


def reson(x, f, q):
    """RBJ constant-peak bandpass (static)."""
    w0 = 2 * np.pi * f / SR
    alpha = np.sin(w0) / (2 * q)
    b = [alpha, 0, -alpha]
    a = [1 + alpha, -2 * np.cos(w0), 1 - alpha]
    return lfilter(np.array(b) / a[0], np.array(a) / a[0], x)


def reson_tv(x, f, q, block=64):
    """Time-varying resonant bandpass; f is an array (per sample)."""
    y = np.zeros_like(x)
    z1 = z2 = 0.0
    x1 = x2 = 0.0
    y1 = y2 = 0.0
    for s in range(0, len(x), block):
        fc = float(np.mean(f[s:s + block]))
        w0 = 2 * np.pi * max(20.0, min(fc, SR * 0.45)) / SR
        alpha = np.sin(w0) / (2 * q)
        a0 = 1 + alpha
        b0, b2 = alpha / a0, -alpha / a0
        a1, a2 = -2 * np.cos(w0) / a0, (1 - alpha) / a0
        seg = x[s:s + block]
        out = np.empty_like(seg)
        for i, xi in enumerate(seg):
            yi = b0 * xi + b2 * x2 - a1 * y1 - a2 * y2
            x2, x1 = x1, xi
            y2, y1 = y1, yi
            out[i] = yi
        y[s:s + block] = out
    return y


def phase_of(freq, n):
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    return 2 * np.pi * np.cumsum(f) / SR


def sine(freq, n, ph=0.0):
    return np.sin(phase_of(freq, n) + ph)


def saw(freq, n, harmonics=None):
    """Band-limited saw by additive synthesis (freq may vary slowly)."""
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    ph = phase_of(f, n)
    fmax = f.max()
    H = harmonics or max(1, int((SR * 0.45) / max(fmax, 1)))
    out = np.zeros(n)
    for k in range(1, H + 1):
        out += np.sin(k * ph) / k
    return out * 0.6


def square(freq, n, H=None):
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    ph = phase_of(f, n)
    Hm = H or max(1, int((SR * 0.45) / max(f.max(), 1)))
    out = np.zeros(n)
    for k in range(1, Hm + 1, 2):
        out += np.sin(k * ph) / k
    return out * 0.8


def env_exp(n, tau, delay=0):
    e = np.exp(-tt(n) / tau)
    if delay:
        d = secs(delay)
        e = np.concatenate([np.zeros(d), e[:n - d]])
    return e


def env_ad(n, a, d, curve=1.0):
    t = tt(n)
    e = np.where(t < a, (t / max(a, 1e-6)), np.exp(-(t - a) / max(d, 1e-6)))
    return e ** curve


def env_lin(n, points):
    """points: list of (time_s, value)."""
    t = tt(n)
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    return np.interp(t, xs, ys)


def pad(x, n):
    if len(x) >= n:
        return x[:n]
    return np.concatenate([x, np.zeros(n - len(x))])


def mix(n, *parts):
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p[:n]
    return out


def at(x, t0, n):
    """Place x at time t0 in an n-sample buffer."""
    out = np.zeros(n)
    s = secs(t0)
    m = min(len(x), n - s)
    if m > 0:
        out[s:s + m] = x[:m]
    return out


def karplus(freq, n, rng, decay=0.996, bright=0.5):
    N = max(2, int(round(SR / freq)))
    buf = rng.uniform(-1, 1, N)
    buf = lp(buf, SR * 0.25 * bright + 200)
    out = np.zeros(n)
    idx = 0
    prev = 0.0
    for i in range(n):
        v = buf[idx]
        out[i] = v
        nv = decay * 0.5 * (v + prev)
        prev = v
        buf[idx] = nv
        idx = (idx + 1) % N
    return out


def comb(x, delay_s, g):
    D = max(1, secs(delay_s))
    a = np.zeros(D + 1); a[0] = 1; a[D] = -g
    return lfilter([1], a, x)


def allpass(x, delay_s, g):
    D = max(1, secs(delay_s))
    b = np.zeros(D + 1); b[0] = -g; b[D] = 1
    a = np.zeros(D + 1); a[0] = 1; a[D] = -g
    return lfilter(b, a, x)


def reverb(x, size=1.0, damp=3000, mix_=0.35, tail=1.5):
    n = len(x) + secs(tail)
    xin = pad(x, n)
    combs = [0.0297, 0.0371, 0.0411, 0.0437]
    g = min(0.92, 0.70 + 0.18 * size)
    wet = np.zeros(n)
    for c in combs:
        wet += comb(xin, c * size, g)
    wet = lp(wet, damp)
    wet = allpass(wet, 0.005, 0.7)
    wet = allpass(wet, 0.0017, 0.7)
    wet = wet / (np.abs(wet).max() + 1e-9) * (np.abs(x).max() + 1e-9)
    return xin * (1 - mix_) + wet * mix_


def distort(x, drive=3.0):
    return np.tanh(x * drive) / np.tanh(drive)


def crush(x, bits=5, hold=2):
    q = 2 ** (bits - 1)
    y = np.round(x * q) / q
    if hold > 1:
        y = np.repeat(y[::hold], hold)[:len(x)]
    return y


def normalize(x, peak=0.9):
    m = np.abs(x).max()
    return x if m < 1e-9 else x * (peak / m)


def fade_edges(x, fin=0.002, fout=0.01):
    n = len(x)
    a, b = secs(fin), secs(fout)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def loopify(x, xfade_s=0.5):
    """Make a seamless loop by crossfading the tail into the head."""
    c = secs(xfade_s)
    head, body, tail = x[:c], x[c:-c] if c else x, x[-c:]
    w = np.linspace(0, 1, c)
    blended = tail * (1 - w) + head * w
    return np.concatenate([body, blended])


def to_s8(x):
    return np.clip(np.round(x * 127), -128, 127).astype(np.int8)
