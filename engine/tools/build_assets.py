#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Hollowmere asset build: generates gen/*.c, gen/*.h, gen/*.s and gen/bin/."""
import os
import sys
import hashlib
import pickle
import importlib
import math
import numpy as np

import paths                    # (also puts the game's content and levels on the path)
ROOT = paths.ROOT
GEN = paths.GEN
BIN = os.path.join(GEN, 'bin')
CACHE = os.path.join(paths.BUILD, 'cache')

import lz77
import palette as P
import textures
import walltex
import proptex
import furniture
import lighttables
import levelc

os.makedirs(BIN, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)


def cached(key_obj, fn):
    key = hashlib.sha1(pickle.dumps(key_obj)).hexdigest()
    path = os.path.join(CACHE, key + '.pkl')
    if os.path.exists(path):
        return pickle.load(open(path, 'rb'))
    v = fn()
    pickle.dump(v, open(path, 'wb'))
    return v


SISTER_NPZ = os.path.join(paths.ASSETS, 'sister.npz')
SISTER_PALETTE_FRAMES = ['walk_0_0', 'walk_2_2', 'walk_4_4', 'walk_6_6', 'chase_0_3', 'idle_1_0',
                         'search_0_0', 'kneel_4_0', 'attack_0_2']


def sister_mips(rgb8, a8, e8, w):
    """One rendered frame (uint8, padded) -> [(rgb, mask, em)] at full,
    half, quarter and eighth size; coverage averaged before thresholding."""
    rgb = rgb8[:, :w].astype(float) / 255
    a = a8[:, :w].astype(float) / 255
    e = e8[:, :w].astype(float) / 255
    out = []
    for lv in range(4):
        if lv:
            h2, w2 = a.shape[0] // 2, a.shape[1] // 2
            pa = (rgb * a[..., None])[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2, 3).sum((1, 3))
            a_ = a[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2)
            rgb = pa / np.maximum(a_.sum((1, 3)), 1e-9)[..., None]
            a = a_.mean((1, 3))
            e = e[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2).mean((1, 3))
        mask = a > 0.5
        out.append((np.clip(rgb, 0, 1), mask, (e > 0.45) & mask))
    return out


def load_sister():
    z = np.load(SISTER_NPZ)
    key = hashlib.sha1(open(SISTER_NPZ, 'rb').read()).hexdigest()
    def build():
        d = {}
        for i, nm in enumerate(z['names']):
            d[str(nm)] = sister_mips(z['rgb'][i], z['alpha'][i], z['em'][i], int(z['widths'][i]))
        return d
    return cached(('sister', key), build)


def cname(s):
    return ''.join(c if c.isalnum() else '_' for c in s)


class Out:
    def __init__(self):
        self.h = []      # header lines
        self.c = []      # C source lines
        self.s = []      # assembly incbin lines

    def blob(self, name, data, align=4):
        """Binary blob in ROM via incbin."""
        path = os.path.join(BIN, name + '.bin')
        old = open(path, 'rb').read() if os.path.exists(path) else None
        if old != bytes(data):
            open(path, 'wb').write(bytes(data))
        self.s.append(f"    .section .rodata.{name}, \"a\"\n    .align {align}\n    .global {name}\n"
                      f"{name}:\n    .incbin \"gen/bin/{name}.bin\"\n")
        self.h.append(f"extern const u8 {name}[];   // {len(data)} bytes")

    def carray(self, ctype, name, values, per_line=16):
        vals = [str(int(v)) for v in values]
        lines = [', '.join(vals[i:i + per_line]) for i in range(0, len(vals), per_line)]
        self.c.append(f"const {ctype} {name}[{len(vals)}] = {{\n  " + ',\n  '.join(lines) + "\n};\n")
        self.h.append(f"extern const {ctype} {name}[{len(vals)}];")


def write_if_changed(path, text):
    if os.path.exists(path) and open(path).read() == text:
        return
    open(path, 'w').write(text)


from manifest import LEVELS     # the game's levels, in play order


def main():
    out = Out()
    out.h.append('#include "gba.h"\n#include "leveldef.h"\n#include "engine.h"\n#include "objects.h"\n')

    # ------------------------------------------------------------ tables
    sinv = [int(round(np.sin(2 * np.pi * i / 1024) * 16384)) for i in range(1024)]
    out.carray('s16', 'sin_lut', sinv)
    sin4096 = [int(round(np.sin(2 * np.pi * i / 4096) * 16384)) for i in range(4096)]
    out.carray('s16', 'sin4096', sin4096)
    sec = []
    for i in range(4096):
        c = abs(np.cos(2 * np.pi * i / 4096))
        v = 0x7FFFFFF if c < 1e-6 else min(0x7FFFFFF, int(round(65536 / c)))
        sec.append(v)
    out.carray('u32', 'sec4096', sec)
    PLANE = lighttables.PLANE
    ra, rf = [], []
    for col in range(lighttables.VIEW_W):
        cx = ((2 * col + 1) * 16384 // lighttables.VIEW_W - 16384) / 16384.0
        a_ = np.arctan(cx * PLANE)
        ra.append(int(round(a_ / (2 * np.pi) * 65536)) & 0xFFFF)
        rf.append(int(round(np.cos(a_) * 16384)))
    out.carray('u16', 'ray_angle', ra)
    out.carray('s16', 'ray_fishcos', rf)
    LH = 2 * lighttables.FOCAL           # wall height 2 tiles
    lhn = [4000] + [min(4000, int(round(LH * 1024 / i))) for i in range(1, 8192)]
    lhf = [4000] + [min(4000, int(round(LH * 128 / i))) for i in range(1, 8192)]
    out.carray('u16', 'lh_near', lhn)
    out.carray('u16', 'lh_far', lhf)
    out.carray('u32', 'rcp_tab', [1 << 24] + [min(0xFFFFFFFF, (1 << 24) // i) for i in range(1, 4096)])
    bw, bf, bc, nvw, nvf = lighttables.build()
    out.carray('u8', 'beam_wall', bw.flatten())
    out.carray('u8', 'beam_floor', bf.flatten())
    out.carray('u8', 'beam_ceil', bc.flatten())
    out.carray('u8', 'nv_wall', nvw)
    out.carray('u8', 'nv_floor', nvf)

    # ---------------------------------------------------------- textures
    # pre-pass over the levels: which generated wall textures (frames,
    # windows, closed doors) and which flats/prop textures/models they use
    models = furniture.build_all()

    class _Collect(dict):
        def __init__(self, ensure=None, known=None):
            super().__init__()
            self.ensure, self.known = ensure, known

        def __missing__(self, k):
            if self.ensure:
                self.ensure(k)
            if self.known is not None and k not in self.known:
                raise KeyError(k)
            self[k] = len(self)
            return self[k]

    class _AnyThing(dict):
        def __contains__(self, k):
            return True

        def __missing__(self, k):
            return 1
    used_flats = set()
    for ln in LEVELS:
        ids = dict(wall=_Collect(walltex.ensure), flat=_Collect(None, textures.TEXTURES),
                   ptex=_Collect(None, proptex.TEXTURES), model={k: 0 for k in models}, thing=_AnyThing())
        levelc.parse(importlib.import_module(ln), ids, models)
        used_flats |= set(ids['flat'])
    wall_names = list(walltex.TEXTURES)
    flat_names = sorted(used_flats)
    ptex_names = list(proptex.TEXTURES)
    src_w = [open(paths.source(f)).read() for f in ('walltex.py', 'noise.py', 'proptex.py', 'textures.py')]
    wall_imgs = cached(('wtex', wall_names, src_w), lambda: {n: walltex.TEXTURES[n]() for n in wall_names})
    flat_imgs = cached(('ftex', flat_names, src_w), lambda: {n: textures.TEXTURES[n]() for n in flat_names})
    ptex_imgs = cached(('ptex', ptex_names, src_w), lambda: {n: proptex.TEXTURES[n]() for n in ptex_names})
    import props
    spr_src = [open(paths.source(f)).read() for f in ('props.py', 'spritekit.py', 'noise.py')]
    sister = load_sister()

    def build_sprites():
        d = {}
        for k, pd in props.PROPS.items():
            d[k] = pd['fn']()
            if pd['glint']:
                h, w = d[k][1].shape
                ys, xs = np.nonzero(d[k][1])
                i = int(np.argmin(ys * 100 + np.abs(xs - w * 0.6)))
                d[k + '_g'] = props.add_glint(d[k], int(xs[i]) + 1, int(ys[i]) + 1)
        return d
    sprites = cached(('spr', spr_src), build_sprites)
    sprite_imgs = [rgb[mask & ~em].reshape(-1, 1, 3) for (rgb, mask, em) in sprites.values()]
    # the Night Sister: a handful of her frames speak for all of them in the
    # palette (about as many pixels as the old hand-drawn creature had)
    for nm in SISTER_PALETTE_FRAMES:
        rgb, mask, em = sister[nm][0]
        sprite_imgs.append(rgb[mask & ~em].reshape(-1, 1, 3))

    emissive = [(1.0, 0.85, 0.45), (1.0, 0.65, 0.25), (0.95, 0.45, 0.15), (1.0, 0.95, 0.75),
                (0.85, 0.15, 0.10), (0.55, 0.85, 1.0), (0.35, 1.0, 0.45), (1.0, 1.0, 1.0)]
    ui = [(1, 1, 1), (0.75, 0.75, 0.72), (0.45, 0.45, 0.43), (0.15, 0.15, 0.15),
          (0.85, 0.12, 0.10), (0.93, 0.88, 0.74), (0.55, 0.47, 0.35), (0.08, 0.06, 0.05)]
    # the palette sees each wall texture's top half only (composites repeat it)
    base_walls = [n for n in wall_names if ':' not in n]
    imgs = [wall_imgs[n] for n in base_walls] + [flat_imgs[n] for n in flat_names] + \
           [ptex_imgs[n] for n in ptex_names] + sprite_imgs
    pal = cached(('pal', [hashlib.sha1(i.tobytes()).hexdigest() for i in imgs], emissive, ui,
                  open(paths.source('palette.py')).read()),
                 lambda: P.build_palette(imgs, emissive, ui))
    out.carray('u16', 'pal_game', P.to_bgr555(pal))
    cm = cached(('cm', pal.tobytes(), open(paths.source('palette.py')).read()),
                lambda: P.build_colormap(pal))
    out.blob('cmap_default', lz77.compress(cm.tobytes()))

    def quant(img):
        return cached(('q', img.tobytes(), pal.tobytes()), lambda: P.quantize(img, pal))

    # wall textures: 64x128 and three mip levels (32x64, 16x32, 8x16, box
    # filtered), each column-major, followed by the same levels as column
    # pairs: P0 holds columns (2k, 2k+1) and P1 columns (2k+1, 2k+2) side by
    # side in each halfword, row after row, so that one 16-bit read gives the
    # texels of two neighbouring screen columns (see col_pair)
    wall_ids = {}
    out.h.append('\n// wall textures')

    def wall_blob(img):
        mips = [img]
        for _ in range(3):
            a = mips[-1]
            mips.append(0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]))
        qs = [quant(np.ascontiguousarray(m)) for m in mips]
        parts = [q.T.copy().tobytes() for q in qs]
        for q in qs:
            h, w = q.shape
            p0 = np.stack([q[:, 0::2], q[:, 1::2]], axis=2)                 # (h, w/2, 2)
            nxt = np.roll(q, -1, axis=1)
            p1 = np.stack([q[:, 1::2], nxt[:, 1::2]], axis=2)
            parts.append(np.transpose(p0, (1, 0, 2)).copy().tobytes())      # pair column, row, (lo, hi)
            parts.append(np.transpose(p1, (1, 0, 2)).copy().tobytes())
        # then each level as column quads in four alignments: Qa holds texel
        # columns 4g+a .. 4g+a+3 (wrapping) of each row in one 32-bit word
        for q in qs:
            h, w = q.shape
            for a in range(4):
                r = np.roll(q, -a, axis=1).reshape(h, w // 4, 4)            # (row, group, 4)
                parts.append(np.transpose(r, (1, 0, 2)).copy().tobytes())  # group, row, 4
        b = b''.join(parts)
        assert len(b) == 76160
        return b
    for i, n in enumerate(wall_names):
        wall_ids[n] = i
        out.blob(f"wt_{cname(n)}", wall_blob(wall_imgs[n]))
    out.c.append("const u8 *const walltex[] = {\n  " + ',\n  '.join(f"wt_{cname(n)}" for n in wall_names) + "\n};\n")
    out.h.append(f"#define NUM_WALLTEX {len(wall_names)}")
    for n in base_walls:
        out.h.append(f"#define WT_{cname(n).upper()} {wall_ids[n]}")
    # floor/ceiling textures: 64x64 row-major, LZ77 (unpacked into the material bank)
    flat_ids = {}
    for i, n in enumerate(flat_names):
        flat_ids[n] = i
        out.blob(f"tex_{cname(n)}", lz77.compress(quant(flat_imgs[n]).tobytes()))
    out.c.append("const u8 *const tex_lz[] = {\n  " + ',\n  '.join(f"tex_{cname(n)}" for n in flat_names) + "\n};\n")
    out.h.append("extern const u8 *const tex_lz[];")
    # prop textures: 64x64 column-major, uncompressed
    ptex_ids = {}
    out.h.append('\n// prop textures')
    def prop_blob(img):
        # 64x64 and mips 32, 16, 8 (column-major), then each level as column
        # pairs like the walls' (P0: 2k|2k+1, P1: 2k+1|2k+2)
        mips = [img]
        for _ in range(3):
            a = mips[-1]
            mips.append(0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]))
        qs = [quant(np.ascontiguousarray(m)) for m in mips]
        parts = [q.T.copy().tobytes() for q in qs]
        for q in qs:
            p0 = np.stack([q[:, 0::2], q[:, 1::2]], axis=2)
            nxt = np.roll(q, -1, axis=1)
            p1 = np.stack([q[:, 1::2], nxt[:, 1::2]], axis=2)
            parts.append(np.transpose(p0, (1, 0, 2)).copy().tobytes())
            parts.append(np.transpose(p1, (1, 0, 2)).copy().tobytes())
        b = b''.join(parts)
        assert len(b) == 16320
        return b
    for i, n in enumerate(ptex_names):
        ptex_ids[n] = i
        out.blob(f"pt_{cname(n)}", prop_blob(ptex_imgs[n]))
        out.h.append(f"#define PT_{cname(n).upper()} {i}")
    out.c.append("const u8 *const proptex[] = {\n  " + ',\n  '.join(f"pt_{cname(n)}" for n in ptex_names) + "\n};\n")

    # ------------------------------------------------------------ models
    out.h.append('\n// models')
    model_ids = {}
    mdl_lines = []
    for i, (n, m) in enumerate(models.items()):
        model_ids[n] = i
        out.h.append(f"#define MDL_{cname(n).upper()} {i}")
        if not m.verts:
            m.verts = [(0, 0, 0)]       # (a marker with nothing to draw)
        vs = ','.join(f"{{{x},{y},{z}}}" for (x, y, z) in m.verts)
        fs = []
        m.solid_faces = getattr(m, 'occlude', True)
        def is_occ(f):
            # big opaque wall-like faces (sloped top or bottom edges too):
            # the walls behind them are not drawn where they will paint over
            if not (f['flags'] & 1) or not m.solid_faces or len(f['v']) != 4 or f['flags'] & 2:
                return False
            FP = [m.verts[i] for i in f['v']]
            wdt = math.hypot(FP[1][0] - FP[0][0], FP[1][1] - FP[0][1]) / 256
            h0, h1 = (FP[3][2] - FP[0][2]) / 256, (FP[2][2] - FP[1][2]) / 256
            return wdt >= 0.4 and max(h0, h1) >= 0.5 and min(h0, h1) >= 0.1 and \
                FP[0][:2] == FP[3][:2] and FP[1][:2] == FP[2][:2]
        m.faces.sort(key=lambda f: 0 if is_occ(f) else 1)
        nocc = sum(1 for f in m.faces if is_occ(f))
        # a slab's rim stays drawn as long as its top does: otherwise a thin
        # top (a mantel shelf, a table top) floats over its body far away,
        # its edge faces dropped and the top still there
        def lod_of(f):
            FP = [m.verts[i] for i in f['v']]
            nx, ny, nz = f['n']
            exts = sorted(max(q[i] for q in FP) - min(q[i] for q in FP) for i in range(3))
            if nz == 0:
                run = max(math.hypot(FP[a_][0] - FP[b_][0], FP[a_][1] - FP[b_][1]) for a_ in range(len(FP)) for b_ in range(len(FP)))
                narrow = min(run, max(q[2] for q in FP) - min(q[2] for q in FP)) / 256
            else:
                edges = [math.dist(FP[i_], FP[(i_ + 1) % len(FP)]) for i_ in range(len(FP))]
                narrow = min(exts[1], min(edges)) / 256
            return min(255, int(narrow * 80 * 8)) if narrow < 0.4 else 255
        top_edge_lod = {}
        for f in m.faces:
            if f['n'][2] > 0 and 'lod' not in f:
                FP = [tuple(m.verts[i]) for i in f['v']]
                for i_ in range(len(FP)):
                    e = frozenset((FP[i_], FP[(i_ + 1) % len(FP)]))
                    top_edge_lod[e] = max(top_edge_lod.get(e, 0), lod_of(f))
        for f in m.faces:
            v = list(f['v']) + [255] * (4 - len(f['v']))
            t = f['tex'] if isinstance(f['tex'], int) else ptex_ids[f['tex']]
            uv = [c for pair in f['uv'] for c in pair] + [0] * (8 - 2 * len(f['uv']))
            FP = [m.verts[i] for i in f['v']]
            flags = f['flags']
            if flags & 1:
                # the fast path needs a wall-like quad: v0/v3 and v1/v2 stacked, u constant up each side
                ok = (len(FP) == 4 and FP[0][:2] == FP[3][:2] and FP[1][:2] == FP[2][:2] and FP[0][:2] != FP[1][:2]
                      and f['uv'][0][0] == f['uv'][3][0] and f['uv'][1][0] == f['uv'][2][0]
                      and f['uv'][0][1] == f['uv'][1][1] and f['uv'][2][1] == f['uv'][3][1]
                      and FP[3][2] > FP[0][2] and FP[2][2] > FP[1][2])
                if not ok:
                    flags &= ~1
            nx, ny, nz = f['n']
            if flags & 1 and is_occ(f):
                flags |= 4          # FF_OCC: big opaque face, hides the wall behind it
            d = nx * FP[0][0] + ny * FP[0][1] + nz * FP[0][2]
            cx = sum(q[0] for q in FP) / len(FP) + nx / 64 * 16
            cy = sum(q[1] for q in FP) / len(FP) + ny / 64 * 16
            # level of detail: drop a face once its narrower side would be under
            # about one column on screen (80 columns per tile at distance 1)
            exts = sorted(max(q[i] for q in FP) - min(q[i] for q in FP) for i in range(3))
            if nz == 0:      # vertical: horizontal run and height
                run = max(math.hypot(FP[a_][0] - FP[b_][0], FP[a_][1] - FP[b_][1]) for a_ in range(len(FP)) for b_ in range(len(FP)))
                narrow = min(run, exts[2] if exts[2] != max(exts[0], exts[1]) else run) / 256
                narrow = min(run, max(q[2] for q in FP) - min(q[2] for q in FP)) / 256
            else:
                # the face's narrower dimension: its shortest edge (a long
                # thin strip, like a handrail's top, is as narrow as its ends)
                edges = [math.dist(FP[i_], FP[(i_ + 1) % len(FP)]) for i_ in range(len(FP))]
                narrow = min(exts[1], min(edges)) / 256
            lod = min(255, int(narrow * 80 * 8)) if narrow < 0.4 else 255
            if nz == 0 and len(FP) == 4:
                e = frozenset((tuple(FP[2]), tuple(FP[3])))       # its top edge
                lod = max(lod, top_edge_lod.get(e, 0))
            if flags & 8:
                lod = 255           # FF_THIN: posts and poles never drop out
            if 'lod' in f:
                lod = min(255, int(f['lod'] * 8))   # an explicit distance (tiles)
            fs.append("{{%s},%d,%d,{%d,%d,%d},%d,{%s},%d,%d,%d}" % (','.join(map(str, v)), t, flags,
                      nx, ny, nz, lod, ','.join(map(str, uv)), d, int(round(cx)), int(round(cy))))
        out.c.append(f"static const MVert mdl_{cname(n)}_v[] = {{{vs}}};")
        out.c.append(f"static const MFace mdl_{cname(n)}_f[] = {{{','.join(fs) if fs else '{{0}}'}}};")
        rad = int(math.ceil(m.radius() * 256)) + 8
        mflags = 1 if getattr(m, 'half', False) else 0
        far = getattr(m, 'far', None)
        far_i = (list(models.keys()).index(far) + 1) if far else 0
        far_d = min(255, int(round(getattr(m, 'far_dist', 0) * 8)))
        xs = [v[0] for v in m.verts]; ys = [v[1] for v in m.verts]
        ccx, ccy = (min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2
        mdl_lines.append(f"{{mdl_{cname(n)}_v, mdl_{cname(n)}_f, {len(m.verts)}, {len(m.faces)}, {rad}, {int(m.zmax() * 256)}, {nocc}, {mflags}, {far_i}, {far_d}, {ccx}, {ccy}}}")
    out.c.append("const Model models[] = {\n  " + ',\n  '.join(mdl_lines) + "\n};\n")
    out.h.append(f"#define NUM_MODELS {len(models)}")

    # ---------------------------------------------------------- sprites
    def encode_sprite(rgb, mask, em):
        idx = P.quantize(rgb, pal, mask=mask, emissive=em)
        h, w = mask.shape
        cols = []
        for x in range(w):
            col = bytearray()
            y = 0
            while y < h:
                if mask[y, x]:
                    y0 = y
                    while y < h and mask[y, x] and y - y0 < 250:
                        y += 1
                    col += bytes([y0, y - y0]) + bytes(idx[y0:y, x].tolist())
                else:
                    y += 1
            col.append(0xFF)
            cols.append(col)
        hdr = 2 + 2 * w
        offs = []
        body = bytearray()
        for col in cols:
            offs.append(hdr + len(body))
            body += col
        b = bytearray([w, h])
        for o in offs:
            b += o.to_bytes(2, 'little')
        b += body
        while len(b) % 4:
            b.append(0)
        return bytes(b)

    out.h.append('\n// sprites')
    spr_names = list(sprites)
    for nm in spr_names:
        enc = cached(('enc', sprites[nm][0].tobytes(), sprites[nm][1].tobytes(), sprites[nm][2].tobytes(), pal.tobytes()),
                     lambda: encode_sprite(*sprites[nm]))
        out.blob(f"spr_{cname(nm)}", enc)
    # thing types: index 0 = none, then props in order
    thing_names = list(props.PROPS)
    tt_lines = ['{0}']
    out.h.append('#define THING_NONE 0')
    for i, nm in enumerate(thing_names):
        pd = props.PROPS[nm]
        flags = (1 if pd['solid'] else 0) | (2 if pd['fullbright'] else 0) | (4 if pd['glint'] else 0)
        g = f"(const SpriteImg*)spr_{cname(nm)}_g" if pd['glint'] else "0"
        k = 0.75     # the sprites were drawn for the old, larger tile
        tt_lines.append(f"{{(const SpriteImg*)spr_{cname(nm)}, {g}, {int(pd['ww']*256*k)}, {int(pd['wh']*256*k)}, {int(pd['zoff']*256*k)}, {flags}, 0}}")
        out.h.append(f"#define THING_{cname(nm).upper()} {i + 1}")
    out.h.append(f"#define NUM_THING_TYPES {len(thing_names) + 1}")
    out.h.append("extern const ThingType thing_types[NUM_THING_TYPES];")
    out.c.append("const ThingType thing_types[NUM_THING_TYPES] = {\n  " + ',\n  '.join(tt_lines) + "\n};\n")
    # the Night Sister: every frame at four sizes (full, 1/2, 1/4, 1/8)
    out.h.append('\n// the Night Sister (game/content/sister): frames x view-angle, each at 4 sizes')
    cr_names = list(sister)
    for nm in cr_names:
        for lv, img in enumerate(sister[nm]):
            enc = cached(('enc', img[0].tobytes(), img[1].tobytes(), img[2].tobytes(), pal.tobytes()),
                         lambda: encode_sprite(*img))
            out.blob(f"spr_cr_{nm}_{lv}", enc)
    rows = []
    for lv in range(4):
        rows.append('{' + ','.join(f"(const SpriteImg*)spr_cr_{nm}_{lv}" for nm in cr_names) + '}')
    out.h.append(f"#define CR_NFRAMES {len(cr_names)}")
    out.c.append("const SpriteImg *const creature_frames[4][CR_NFRAMES] = {\n  " + ',\n  '.join(rows) + "\n};\n")
    out.h.append("extern const SpriteImg *const creature_frames[4][CR_NFRAMES];")
    first = {}
    for i, nm in enumerate(cr_names):
        first.setdefault(nm.split('_')[0], i)
    for kind, i in first.items():
        out.h.append(f"#define CRF_{kind.upper()} {i}")

    # -------------------------------------------------------------- font
    import font
    gt = font.glyph_table()
    widths = [0] * 128
    rows = [0] * (128 * font.HEIGHT)
    for ch, (w, bits) in gt.items():
        o = ord(ch)
        widths[o] = w
        for r, b in enumerate(bits):
            rows[o * font.HEIGHT + r] = b
    for o in range(128):
        if widths[o] == 0 and chr(o) not in gt:
            widths[o] = 3     # unknown glyph: blank
    out.carray('u8', 'font_width', widths)
    out.carray('u8', 'font_rows', rows)
    out.h.append(f"#define FONT_H {font.HEIGHT}")

    # ------------------------------------------------------------ sounds
    import sounds
    import music
    import synth
    src_hash = [open(paths.source(f)).read() for f in ('sounds.py', 'synth.py')]
    snd_names = list(sounds.SOUNDS)
    out.h.append('\n// sounds')
    defs = []
    for i, nm in enumerate(snd_names):
        fn, loop = sounds.SOUNDS[nm]
        data, loop_start = cached(('snd', nm, src_hash), lambda: fn())
        pcm = synth.to_s8(data)
        b = bytearray(pcm.tobytes())
        while len(b) % 4:
            b.append(0)
        out.blob(f"snd_{cname(nm)}", b)
        out.h.append(f"#define SND_{cname(nm).upper()} {i}")
        defs.append(f"{{(const s8*)snd_{cname(nm)}, {len(pcm)}, {loop_start or 0}, {1 if loop else 0}, {{0,0,0}}}}")
    out.h.append(f"#define NUM_SND {len(snd_names)}")
    out.h.append('#include "audio.h"\nextern const SoundDef snd_defs[NUM_SND];')
    out.c.append('#include "audio.h"\nconst SoundDef snd_defs[NUM_SND] = {\n  ' + ',\n  '.join(defs) + '\n};\n')
    for nm, fn in music.SEQUENCES.items():
        ev, total = fn()
        out.c.append(f"const NoteEv mus_{nm}[] = {{" + ','.join(f"{{{t},{n},{v}}}" for t, n, v in ev) + "};\n")
        out.h.append(f"extern const NoteEv mus_{nm}[];\n#define MUS_{nm.upper()}_LEN {len(ev)}\n#define MUS_{nm.upper()}_FRAMES {total}")

    # ---------------------------------------------------------- levels
    def cstr(t):
        return '"' + t.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\x01', '\\001').replace('\x02', '\\002').replace('\x03', '\\003').replace('\x04', '\\004') + '"'
    import story
    import scriptc
    thing_types = {'none': 0}
    for i, nm in enumerate(thing_names):
        thing_types[nm] = i + 1
    strings = scriptc.StringTable()
    for nm, txt in story.string_list():
        strings.add(txt, nm)
    sound_ids = {nm: i for i, nm in enumerate(snd_names)}
    flags = {}
    level_names = LEVELS
    lv_c = []
    INTER = levelc.INTER_TYPES
    for li, ln in enumerate(level_names):
        mod = importlib.import_module(ln)
        ids = dict(wall=wall_ids, flat=flat_ids, ptex=ptex_ids, model=model_ids, thing=thing_types)
        L = levelc.parse(mod, ids, models)
        src_l = open(paths.source('levelc.py')).read()
        static, patches = cached(('bake2', L.edges.tobytes(), L.cellmat.tobytes(), L.inside.tobytes(), L.lights,
                                  [(d['x'], d['y'], d['axis'], d['flags']) for d in L.doors], L.ambient, src_l),
                                 lambda: levelc.bake(L))
        pre = f"lv_{cname(ln)}"
        out.blob(pre + '_light', lz77.compress(static.tobytes()))
        vis = bytearray()
        for pt in patches:
            vis += bytes([pt['x0'], pt['y0'], pt['w'], pt['h']]) + pt['data'].tobytes()
        if not vis:
            vis = bytes(4)
        assert len(vis) <= 8192, f"{ln}: light patches {len(vis)} bytes (max 8192)"
        assert len(patches) <= 20, f"{ln}: {len(patches)} dynamic lights (max 20)"
        out.blob(pre + '_vis', lz77.compress(bytes(vis)))
        # ---- events
        ev_src = dict(getattr(mod, 'EVENTS', {}))
        order = ['start', 'lantern'] + [k for k in ev_src if k not in ('start', 'lantern')]
        ev_ids = {nm: i + 1 for i, nm in enumerate(order)}
        ctx = scriptc.Ctx(strings, sound_ids, flags, ev_ids, L.door_names, L.thing_names, L.name)
        ctx.props = L.prop_names
        ev_ptrs = ['0']
        for nm in order:
            code = scriptc.compile_event(ev_src.get(nm, []), ctx)
            lv_c.append(f"static const u8 {pre}_ev_{nm}[] = {{" + ','.join(str(b) for b in code) + "};")
            ev_ptrs.append(f"{pre}_ev_{nm}")
        lv_c.append(f"static const u8 *const {pre}_events[] = {{" + ','.join(ev_ptrs) + "};")

        def arr(ctype, nm, items):
            items = list(items) + ['{0}']
            lv_c.append(f"static const {ctype} {pre}_{nm}[] = {{" + ','.join(items) + "};")
        # ---- map
        lv_c.append(f"static const u8 {pre}_edges[2048] = {{" + ','.join(str(v) for v in L.edges.flatten()) + "};")
        ets = []
        for t in L.edge_types[1:]:
            ta, tb, ca, cb, kind, param, panel, lintel = t
            ets.append(f"{{{{{wall_ids[ta]},{wall_ids[tb]}}},{{{wall_ids[ca] if ca else 0},{wall_ids[cb] if cb else 0}}},"
                       f"{kind},{param},{panel},{lintel}}}")
        lv_c.append(f"static const EdgeType {pre}_etypes[] = {{{{{{0,0}},{{0,0}},0,0,0,0}},{','.join(ets)}}};")
        cf = np.zeros((32, 32), np.uint8)
        cf[L.inside] |= 1
        cf[L.blocked] |= 2
        lv_c.append(f"static const u8 {pre}_cells[1024] = {{" + ','.join(str(v) for v in cf.flatten()) + "};")
        mats = []
        for f, c in L.materials:
            mats += [flat_ids[f], flat_ids[c]]
        while len(mats) < 8:
            mats += mats[:2]
        # ---- doors
        arr('DoorDef', 'doors', (f"{{{d['x']},{d['y']},{d['axis']},{1 if d['double'] else 0},{d['lock']},{d['flags']},"
                                 f"{d['hingebits']},{d['edgetype']},{ptex_ids[d['leaf']]},{{0,0}}}}" for d in L.doors))
        # ---- props
        pr = []
        for p_ in L.props:
            pr.append(f"{{{int(round(p_['x'] * 256))},{int(round(p_['y'] * 256))},{int(p_.get('z', 0))},"
                      f"{model_ids[p_['model']]},{int(p_.get('angle', 0)) & 255},{p_.get('flags', 0)},"
                      f"{ptex_ids[p_['tex']] if 'tex' in p_ else 0},{p_.get('light', 0)},0}}")
        arr('PropDef', 'props', pr)
        # ---- collision boxes and the per-cell index
        bx = [f"{{{int(x0 * 256)},{int(y0 * 256)},{int(math.ceil(x1 * 256))},{int(math.ceil(y1 * 256))}}}"
              for (x0, y0, x1, y1) in L.boxes]
        assert len(L.boxes) < 255, f"{ln}: too many collision boxes"
        arr('CollBox', 'boxes', bx)
        cell_list = []
        offs = []
        for cy in range(32):
            for cx in range(32):
                offs.append(len(cell_list))
                for k, (x0, y0, x1, y1) in enumerate(L.boxes):
                    if x0 < cx + 1.25 and x1 > cx - 0.25 and y0 < cy + 1.25 and y1 > cy - 0.25:
                        cell_list.append(k)
                cell_list.append(255)
        lv_c.append(f"static const u16 {pre}_cellbox[1024] = {{" + ','.join(map(str, offs)) + "};")
        lv_c.append(f"static const u8 {pre}_boxlist[] = {{" + ','.join(map(str, cell_list)) + "};")
        # ---- things
        th = []
        for t in L.things:
            ev = ev_ids[t['event']] if t.get('event') else 0
            fl = 1 if t.get('hidden') else 0
            th.append(f"{{{int(t['x']*256)},{int(t['y']*256)},{thing_types[t['type']]},{t.get('param', 0)},{fl},{ev},{int(t.get('z', 0)*256)},0}}")
        arr('ThingDef', 'things', th)
        lights_c = []
        for (x, y, inten, radius, mode, group) in L.lights:
            if mode == 0 and group == 0:
                continue
            lights_c.append(f"{{{int(x*256)},{int(y*256)},{inten},{int(radius*16)},{mode},{group}}}")
        assert len(lights_c) == len(patches)
        arr('LightDef', 'lights', lights_c)
        inters = []
        for it in L.inters:
            ref = it['ref']
            if ref is None:
                param = 0
            elif ref[0] == 'sign':
                param = strings.add(ref[1])
            else:
                param = ev_ids[ref[1]]
            hx, hy, ha = it.get('hide', (it['x'], it['y'], 0))
            nx, ny = it['normal']
            ln_ = math.hypot(nx, ny) or 1
            inters.append(f"{{{int(it['x'] * 256)},{int(it['y'] * 256)},{INTER[it['type']]},{param & 255},"
                          f"{int(round(nx / ln_ * 64))},{int(round(ny / ln_ * 64))},{param >> 8},"
                          f"{it.get('prop', 255)},{int(hx * 256)},{int(hy * 256)},{int(ha) & 255},0}}")
        arr('InterDef', 'inters', inters)
        trig = []
        for t in L.triggers:
            x0, y0, x1, y1, evn = t[:5]
            once = t[5] if len(t) > 5 else 1
            cond = t[6] if len(t) > 6 else None          # 'flag' (must be set) or '!flag' (must be clear)
            nf, nn = 0, 0
            if cond:
                nn = 1 if cond.startswith('!') else 0
                nf = ctx.flag(cond.lstrip('!')) + 1
            trig.append(f"{{{x0},{y0},{x1},{y1},{ev_ids[evn]},{once},{nf},{nn}}}")
        arr('TriggerDef', 'trigs', trig)
        arr('PathNode', 'patrol', (f"{{{x},{y}}}" for (x, y) in L.patrol))
        amb = sound_ids[mod.AMBIENCE] if getattr(mod, 'AMBIENCE', None) else 0
        # ---- the map screen: rooms over the house's bounding box, edge kinds, names
        assert len(L.triggers) <= 32, f"{ln}: more than 32 triggers"
        cells = [(x, y) for y in range(L.H) for x in range(L.W) if L.cell[y][x] != ' ']
        mx0, my0 = min(x for x, y in cells), min(y for x, y in cells)
        mx1, my1 = max(x for x, y in cells) + 1, max(y for x, y in cells) + 1
        mw, mh = mx1 - mx0, my1 - my0
        room_ix = {}
        for y in range(my0, my1):
            for x in range(mx0, mx1):
                ch = L.cell[y][x]
                if ch != ' ' and ch not in room_ix:
                    room_ix[ch] = len(room_ix)
        assert len(room_ix) <= 32, f"{ln}: more than 32 rooms"
        mroom = [room_ix[L.cell[y][x]] if L.cell[y][x] != ' ' else 255 for y in range(my0, my1) for x in range(mx0, mx1)]
        MK = dict(open=0, wall=1, door=2, arch=3, window=4, exit=5, sealed=6)
        medge = []
        for y in range(my0, my1 + 1):
            for x in range(mx0, mx1 + 1):
                w_ = MK[L.map_kind.get((x, y, 'W'), 'open')]
                n_ = MK[L.map_kind.get((x, y, 'N'), 'open')]
                medge.append(w_ | (n_ << 4))
        rooms_by_ix = sorted(room_ix, key=room_ix.get)
        lv_c.append(f"static const u8 {pre}_mroom[] = {{" + ','.join(map(str, mroom)) + "};")
        lv_c.append(f"static const u8 {pre}_medge[] = {{" + ','.join(map(str, medge)) + "};")
        lv_c.append(f"static const char *const {pre}_mname[] = {{" +
                    ','.join(cstr(mod.ROOMS[c]['name']) for c in rooms_by_ix) + "};")
        lv_c.append(f"static const u8 {pre}_mflag[] = {{" +
                    ','.join('1' if mod.ROOMS[c].get('map') == 'void' else '0' for c in rooms_by_ix) + "};")
        lv_c.append(f"static const MapDef {pre}_map = {{{mx0},{my0},{mw},{mh},{len(room_ix)},0,{pre}_mroom,{pre}_medge,"
                    f"{pre}_mname,{pre}_mflag,{cstr(getattr(mod, 'FLOOR', L.name))}}};")
        lv_c.append(f"""const LevelDef level_{cname(ln)} = {{
  "{L.name}", {pre}_edges, {pre}_etypes, {pre}_light, {pre}_vis, {pre}_cells, {{{','.join(map(str, mats))}}},
  {pre}_doors, {len(L.doors)}, {pre}_props, {len(L.props)}, {pre}_boxes, {len(L.boxes)}, {pre}_cellbox, {pre}_boxlist,
  {pre}_things, {len(L.things)}, {pre}_lights, {len(lights_c)},
  {pre}_inters, {len(L.inters)}, {pre}_trigs, {len(L.triggers)}, {pre}_patrol, {len(L.patrol)},
  {pre}_events, {len(ev_ptrs)}, 1,
  {int(L.start[0]*256)}, {int(L.start[1]*256)}, {L.start_angle}, {li}, {getattr(mod, 'MONSTER_MODE', 0)}, {amb}, 0,
  &{pre}_map, {ev_ids.get('resume', 0)}
}};""")
        out.h.append(f"extern const LevelDef level_{cname(ln)};")
        print(f"  {ln}: {L.W}x{L.H} cells, {len(L.edge_types) - 1} edge types, {len(L.doors)} doors, "
              f"{len(L.props)} props, {len(L.boxes)} boxes, {len(patches)} dyn lights")
    lv_c.append("const LevelDef *const level_table[] = {" + ','.join(f"&level_{cname(n)}" for n in level_names) + "};")
    out.h.append(f"#define NUM_LEVELS {len(level_names)}\nextern const LevelDef *const level_table[];")

    # ----------------------------------------------------------- strings
    def cstr(t):
        return '"' + t.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\x01', '\\001').replace('\x02', '\\002').replace('\x03', '\\003').replace('\x04', '\\004') + '"'
    lv_c.append("const char *const str_table[] = {\n  " + ',\n  '.join(cstr(t) for t in strings.items) + "\n};")
    out.h.append(f"#define NUM_STRINGS {len(strings.items)}\nextern const char *const str_table[];")
    for nm, i in strings.names.items():
        out.h.append(f"#define STR_{nm} {i}")
    for k, v in story.COUNTS.items():
        out.h.append(f"#define {k} {v}")
    for k, v in story.BASES.items():
        out.h.append(f"#define {k} STR_{v}")

    # ------------------------------------------------------------ images
    import images
    img_src = [open(paths.source(f)).read() for f in ('images.py', 'noise.py', 'palette.py')]
    # the jumpscare is a render of the Night Sister: rebuild when it changes
    img_src.append(hashlib.sha1(open(os.path.join(paths.ASSETS, 'sister_jumpscare.npz'), 'rb').read()).hexdigest())
    for nm, fn in images.IMAGES.items():
        idx, ipal = cached(('img', nm, img_src, pal.tobytes()), lambda: images.render(fn, pal))
        out.blob(f"img_{nm}", lz77.compress(idx.tobytes()))
        out.carray('u16', f"pal_{nm}", P.to_bgr555(ipal))

    # ------------------------------------------------------------- write
    write_if_changed(os.path.join(GEN, 'assets.h'),
                     "// generated by engine/tools/build_assets.py\n#ifndef ASSETS_H\n#define ASSETS_H\n" +
                     '\n'.join(out.h) + "\n#endif\n")
    write_if_changed(os.path.join(GEN, 'assets.c'),
                     '// generated\n#include "assets.h"\n\n' + '\n'.join(out.c) + '\n' + '\n'.join(lv_c) + '\n')
    write_if_changed(os.path.join(GEN, 'data.s'), '@ generated\n' + '\n'.join(out.s))
    # preview of palette
    print(f"textures: {len(wall_names)} wall, {len(flat_names)} flat, {len(ptex_names)} prop; "
          f"{len(models)} models; levels: {len(level_names)}")


if __name__ == '__main__':
    main()
