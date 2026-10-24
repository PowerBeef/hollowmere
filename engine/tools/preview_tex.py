"""Render a contact sheet of all textures (debug)."""
import sys
import paths
import numpy as np
from PIL import Image
import textures

names = list(textures.TEXTURES)
cols = 6
rows = (len(names) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 136, rows * 136), (40, 40, 40))
for i, n in enumerate(names):
    a = textures.TEXTURES[n]()
    assert a.shape == (64, 64, 3), (n, a.shape)
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype('uint8')).resize((128, 128), Image.NEAREST)
    sheet.paste(im, ((i % cols) * 136 + 4, (i // cols) * 136 + 4))
sheet.save(sys.argv[1])
print(names)
