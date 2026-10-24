"""Render waveform + spectrogram contact sheet for all sounds (debug)."""
import sys
import paths
import numpy as np
from PIL import Image, ImageDraw
from scipy.signal import spectrogram
import sounds
import synth

names = sys.argv[2:] or list(sounds.SOUNDS)
W, H = 360, 150
cols = 3
rows = (len(names) + cols - 1) // cols
sheet = Image.new('RGB', (cols * (W + 8), rows * (H + 20)), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for i, nm in enumerate(names):
    fn, loop = sounds.SOUNDS[nm]
    x, ls = fn()
    q = synth.to_s8(x).astype(float) / 127
    ox, oy = (i % cols) * (W + 8), (i // cols) * (H + 20)
    d.text((ox + 2, oy + 2), f"{nm} {len(q)/synth.SR:.2f}s peak={np.abs(q).max():.2f} rms={np.sqrt((q**2).mean()):.2f}", fill=(255, 255, 0))
    # waveform envelope (top 50px)
    n = len(q)
    for px in range(W):
        seg = q[px * n // W:(px + 1) * n // W + 1]
        lo, hi = seg.min(), seg.max()
        d.line([(ox + px, oy + 40 - hi * 25), (ox + px, oy + 40 - lo * 25)], fill=(120, 200, 255))
    f, t, S = spectrogram(q, fs=synth.SR, nperseg=256, noverlap=192)
    S = 10 * np.log10(S + 1e-10)
    S = np.clip((S - S.max() + 70) / 70, 0, 1)
    img = Image.fromarray((S[::-1] * 255).astype(np.uint8)).resize((W, 95))
    sheet.paste(Image.merge('RGB', (img, img.point(lambda v: v * 0.6), img.point(lambda v: v * 0.2))), (ox, oy + 70))
sheet.save(sys.argv[1])
