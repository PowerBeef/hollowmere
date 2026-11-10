# SPDX-License-Identifier: MIT
"""Decor and item sprites for Hollowmere."""
import numpy as np
from spritekit import Canvas, preview

METAL = np.array([0.55, 0.56, 0.55])
RUST = np.array([0.40, 0.22, 0.12])
SHEET = np.array([0.72, 0.70, 0.64])
WOOD = np.array([0.36, 0.23, 0.13])
BRASS = np.array([0.72, 0.58, 0.28])
PAPER = np.array([0.82, 0.78, 0.64])
GLINT = np.array([1.0, 1.0, 1.0])

PROPS = {}


def prop(name, w, h, world_w, world_h, zoff=0.0, solid=False, fullbright=False, glint=False):
    def deco(fn):
        PROPS[name] = dict(fn=fn, w=w, h=h, ww=world_w, wh=world_h, zoff=zoff, solid=solid,
                           fullbright=fullbright, glint=glint)
        return fn
    return deco


def tube(c, p0, p1, wdt, col, light=1.15, dark=0.6):
    m = c.mask_line([p0, p1], wdt)
    vertical = abs(p1[0] - p0[0]) < abs(p1[1] - p0[1])
    if vertical:
        cx = (p0[0] + p1[0]) / 2
        sh = c.grad_x(cx - wdt / 2, cx + wdt / 2, light, dark)
    else:
        cy = (p0[1] + p1[1]) / 2
        sh = c.grad_y(cy - wdt / 2, cy + wdt / 2, light, dark)
    c.paint(m, col, sh)


def rusty(c, m, amount=0.5):
    r = (c.tex(8, 3, 0, 1) > 0.58) * m
    c.paint(r, RUST, c.tex(16, 2, 0.7, 1.1), alpha=amount)


# ------------------------------------------------------------------ decor
@prop('bed', 64, 40, 0.92, 0.57, solid=True)
def bed(seed=1):
    c = Canvas(64, 40, seed)
    for x in (3, 60):
        tube(c, (x, 6), (x, 39), 2.2, METAL)
    tube(c, (3, 8), (60, 8), 1.6, METAL * 0.9)
    tube(c, (3, 14), (60, 14), 1.4, METAL * 0.8)
    for x in range(8, 58, 6):
        tube(c, (x, 8), (x, 14), 1.0, METAL * 0.85)
    tube(c, (3, 30), (60, 30), 1.8, METAL * 0.7)
    for x in (8, 56):
        c.paint(c.mask_ellipse(x, 38, 2, 2), np.array([0.1, 0.1, 0.1]))
    mat = c.mask_poly([(4, 18), (59, 18), (60, 29), (3, 29)])
    c.paint(mat, np.array([0.55, 0.52, 0.45]), c.grad_y(18, 29, 1.1, 0.65) * c.tex(6, 3, 0.85, 1.1))
    sheet = c.mask_poly([(10, 15), (52, 14), (58, 19), (56, 27), (40, 33), (20, 32), (6, 26), (5, 19)])
    c.paint(sheet, SHEET, c.grad_y(14, 33, 1.15, 0.55) * c.tex(10, 3, 0.85, 1.1))
    # human-shaped lump under the sheet
    lump = c.mask_ellipse(30, 16, 14, 4) + c.mask_ellipse(48, 16, 4, 3.5)
    c.paint(np.clip(lump, 0, 1), SHEET * 1.05, c.grad_y(11, 20, 1.2, 0.8))
    st = (c.tex(5, 3, 0, 1) > 0.66) * np.clip(sheet + lump, 0, 1)
    c.paint(st, np.array([0.45, 0.14, 0.08]), alpha=0.7)
    pil = c.mask_ellipse(52, 18, 6, 3)
    c.paint(pil, SHEET * 1.1, c.grad_y(15, 21, 1.1, 0.7))
    rusty(c, c.a, 0.25)
    return c.result()


@prop('bed_empty', 64, 40, 0.92, 0.57, solid=True)
def bed_empty(seed=2):
    c = Canvas(64, 40, seed)
    for x in (3, 60):
        tube(c, (x, 6), (x, 39), 2.2, METAL)
    tube(c, (3, 8), (60, 8), 1.6, METAL * 0.9)
    for x in range(8, 58, 6):
        tube(c, (x, 8), (x, 14), 1.0, METAL * 0.85)
    tube(c, (3, 14), (60, 14), 1.4, METAL * 0.8)
    tube(c, (3, 30), (60, 30), 1.8, METAL * 0.7)
    for x in (8, 56):
        c.paint(c.mask_ellipse(x, 38, 2, 2), np.array([0.1, 0.1, 0.1]))
    mat = c.mask_poly([(4, 21), (59, 20), (60, 29), (3, 29)])
    c.paint(mat, np.array([0.50, 0.46, 0.38]), c.grad_y(20, 29, 1.1, 0.6) * c.tex(6, 3, 0.8, 1.1))
    st = (c.tex(4, 3, 0, 1) > 0.6) * mat
    c.paint(st, np.array([0.30, 0.20, 0.10]), alpha=0.8)
    # leather restraint straps
    for x in (18, 40):
        c.paint(c.mask_poly([(x, 19), (x + 3, 19), (x + 4, 33), (x + 1, 33)]), np.array([0.25, 0.15, 0.08]))
        c.paint(c.mask_ellipse(x + 2.5, 26, 1.2, 1.2), BRASS)
    rusty(c, c.a, 0.3)
    return c.result()


@prop('wheelchair', 40, 44, 0.44, 0.48, solid=True)
def wheelchair(seed=3):
    c = Canvas(40, 44, seed)
    big = c.mask_ellipse(16, 30, 13, 13) - c.mask_ellipse(16, 30, 11.6, 11.6)
    c.paint(np.clip(big, 0, 1), np.array([0.12, 0.12, 0.12]))
    for a in np.linspace(0, np.pi, 6, endpoint=False):
        dx, dy = np.cos(a) * 11.5, np.sin(a) * 11.5
        c.paint(c.mask_line([(16 - dx, 30 - dy), (16 + dx, 30 + dy)], 0.5), METAL * 0.9)
    c.paint(c.mask_ellipse(16, 30, 2, 2), METAL)
    c.paint(c.mask_ellipse(34, 40, 3.5, 3.5), np.array([0.1, 0.1, 0.1]))
    tube(c, (6, 4), (8, 30), 1.6, METAL)          # backrest post / handle
    tube(c, (4, 4), (8, 4), 1.6, np.array([0.15, 0.15, 0.15]))
    seat = c.mask_poly([(8, 22), (30, 22), (31, 26), (8, 26)])
    c.paint(seat, np.array([0.30, 0.18, 0.10]), c.tex(8, 2, 0.8, 1.1))
    back = c.mask_poly([(7, 6), (10, 6), (11, 23), (8, 23)])
    c.paint(back, np.array([0.28, 0.17, 0.09]))
    tube(c, (30, 24), (34, 38), 1.4, METAL)
    tube(c, (10, 16), (28, 16), 1.4, METAL * 0.9)    # armrest
    tube(c, (28, 16), (29, 23), 1.2, METAL * 0.9)
    tube(c, (30, 36), (37, 36), 1.6, METAL * 0.8)    # footrest
    rusty(c, c.a, 0.35)
    return c.result()


@prop('ivstand', 22, 72, 0.2, 0.68)
def ivstand(seed=4):
    c = Canvas(22, 72, seed)
    tube(c, (11, 6), (11, 66), 1.5, METAL)
    for dx in (-8, -3, 3, 8):
        tube(c, (11, 66), (11 + dx, 70), 1.3, METAL * 0.8)
        c.paint(c.mask_ellipse(11 + dx, 70.5, 1.3, 1.3), np.array([0.1, 0.1, 0.1]))
    tube(c, (5, 6), (17, 6), 1.2, METAL)
    bag = c.mask_poly([(12, 8), (18, 8), (19, 20), (15, 23), (11, 20)])
    c.paint(bag, np.array([0.60, 0.62, 0.55]), c.grad_x(11, 19, 1.2, 0.7), alpha=0.85)
    fluid = bag * c.grad_y(13, 14, 0, 1)
    c.paint(fluid, np.array([0.45, 0.12, 0.08]), alpha=0.85)
    c.paint(c.mask_line([(15, 23), (14, 34), (8, 44), (7, 56)], 0.6), np.array([0.55, 0.55, 0.5]))
    return c.result()


@prop('gurney', 64, 36, 0.95, 0.53, solid=True)
def gurney(seed=5):
    c = Canvas(64, 36, seed)
    tube(c, (4, 18), (60, 18), 2.0, METAL)
    for x in (8, 56):
        tube(c, (x, 18), (x, 33), 1.6, METAL * 0.85)
        c.paint(c.mask_ellipse(x, 34, 1.8, 1.8), np.array([0.1, 0.1, 0.1]))
    tube(c, (8, 28), (56, 28), 1.2, METAL * 0.7)
    body = c.mask_poly([(5, 17), (6, 12), (14, 9), (22, 10), (30, 8), (44, 9), (52, 11), (58, 8), (61, 11), (60, 17)])
    head = c.mask_ellipse(56, 9, 4.5, 4)
    feet = c.mask_ellipse(8, 11, 3, 3.5)
    sheet = np.clip(body + head + feet, 0, 1)
    c.paint(sheet, SHEET, c.grad_y(5, 18, 1.2, 0.6) * c.tex(8, 3, 0.85, 1.1))
    st = (c.tex(5, 3, 0, 1) > 0.6) * sheet
    c.paint(st, np.array([0.42, 0.10, 0.06]), alpha=0.75)
    # hanging arm
    c.paint(c.mask_tapered([(38, 15), (39, 22), (39.5, 28)], [2.2, 1.6, 1.4]), np.array([0.55, 0.55, 0.47]))
    c.paint(c.mask_line([(39.5, 28), (39, 31)], 0.7), np.array([0.5, 0.5, 0.42]))
    tag = c.mask_poly([(6, 12), (9, 12), (9, 16), (6, 16)])
    c.paint(tag, PAPER)
    return c.result()


@prop('chair', 30, 42, 0.3, 0.42, solid=True)
def chair(seed=6):
    c = Canvas(30, 42, seed)
    grain = c.tex(3, 3, 0.75, 1.15, aspect=0.2)
    for x0 in (5, 22):
        c.paint(c.mask_poly([(x0, 2), (x0 + 3, 2), (x0 + 3, 41), (x0, 41)]), WOOD, grain * c.grad_x(x0, x0 + 3, 1.2, 0.7))
    for y in (6, 11, 16):
        c.paint(c.mask_poly([(6, y), (24, y), (24, y + 2.5), (6, y + 2.5)]), WOOD * 0.9, grain)
    seat = c.mask_poly([(3, 23), (27, 23), (28, 27), (2, 27)])
    c.paint(seat, WOOD * 1.1, c.grad_y(23, 27, 1.2, 0.7) * grain)
    for x0 in (4, 24):
        c.paint(c.mask_poly([(x0, 27), (x0 + 2.5, 27), (x0 + 2.5, 41), (x0, 41)]), WOOD * 0.8, grain)
    return c.result()


@prop('cabinet', 40, 60, 0.45, 0.66, solid=True)
def cabinet(seed=7):
    c = Canvas(40, 60, seed)
    body = c.mask_poly([(2, 2), (38, 2), (38, 58), (2, 58)])
    c.paint(body, np.array([0.55, 0.57, 0.53]), c.grad_x(2, 38, 1.1, 0.75) * c.tex(6, 3, 0.85, 1.1))
    glass = c.mask_poly([(5, 5), (35, 5), (35, 30), (5, 30)])
    c.paint(glass, np.array([0.08, 0.09, 0.09]))
    for y in (13, 22):
        tube(c, (5, y), (35, y), 1.0, METAL * 0.7)
    for i, x in enumerate((8, 12, 17, 23, 28, 31)):
        y = 12 if i % 2 else 21
        bot = c.mask_poly([(x, y - 5), (x + 3, y - 5), (x + 3, y), (x, y)])
        col = [np.array([0.35, 0.22, 0.10]), np.array([0.25, 0.35, 0.30]), np.array([0.55, 0.55, 0.50])][i % 3]
        c.paint(bot, col, c.grad_x(x, x + 3, 1.3, 0.6))
    c.paint(c.mask_line([(20, 5), (20, 30)], 0.8), np.array([0.4, 0.42, 0.4]))
    for y in (34, 46):
        dr = c.mask_poly([(5, y), (35, y), (35, y + 10), (5, y + 10)])
        c.paint(dr, np.array([0.50, 0.52, 0.48]), c.grad_y(y, y + 10, 1.1, 0.8))
        c.paint(c.mask_ellipse(20, y + 5, 2.5, 1), METAL * 1.2)
    rusty(c, body, 0.45)
    # crack in the glass
    c.paint(c.mask_line([(10, 6), (14, 14), (12, 22), (17, 29)], 0.5), np.array([0.6, 0.62, 0.62]))
    return c.result()


@prop('doll', 22, 30, 0.17, 0.24)
def doll(seed=8):
    c = Canvas(22, 30, seed)
    dress = c.mask_poly([(6, 13), (16, 13), (20, 26), (2, 26)])
    c.paint(dress, np.array([0.55, 0.40, 0.42]), c.tex(6, 3, 0.75, 1.1) * c.grad_x(2, 20, 1.1, 0.7))
    for x0 in (6, 13):
        c.paint(c.mask_tapered([(x0 + 1, 24), (x0 - 1, 28)], [2.4, 2.0]), np.array([0.82, 0.78, 0.72]))
    for side in (-1, 1):
        c.paint(c.mask_tapered([(11 + side * 5, 14), (11 + side * 8, 21)], [2.2, 1.8]), np.array([0.82, 0.78, 0.72]))
    head = c.mask_ellipse(11, 8, 6, 6.5)
    c.paint(head, np.array([0.88, 0.84, 0.78]), c.radial(10, 6, 7, 1.1, 0.7))
    hair = c.mask_ellipse(11, 4, 6.5, 3.5) * (1 - c.mask_ellipse(11, 8, 5, 5))
    c.paint(np.clip(hair + c.mask_poly([(4.5, 4), (7, 4), (6, 14), (4, 13)]) + c.mask_poly([(15, 4), (17.5, 4), (18, 13), (16, 14)]), 0, 1),
            np.array([0.20, 0.12, 0.06]))
    for ex in (8.5, 13.5):
        c.paint(c.mask_ellipse(ex, 8, 1.4, 1.6), np.array([0.05, 0.05, 0.08]))
    c.paint(c.mask_ellipse(11, 12, 1.0, 0.6), np.array([0.45, 0.10, 0.10]))
    # crack across the face
    c.paint(c.mask_line([(7, 3), (10, 7), (9, 10), (12, 13)], 0.5), np.array([0.25, 0.2, 0.18]))
    return c.result()


@prop('candles', 26, 22, 0.2, 0.17)
def candles(seed=9):
    c = Canvas(26, 22, seed)
    for x, h in ((5, 9), (10, 14), 15 and (15, 7), (20, 11)):
        y0 = 21 - h
        c.paint(c.mask_poly([(x - 1.6, y0), (x + 1.6, y0), (x + 1.6, 21), (x - 1.6, 21)]), np.array([0.85, 0.82, 0.70]),
                c.grad_x(x - 1.6, x + 1.6, 1.1, 0.7))
        c.paint(c.mask_ellipse(x + 0.6, y0 + 2, 0.7, 1.6), np.array([0.85, 0.82, 0.70]))   # drip
        c.paint(c.mask_ellipse(x, y0 - 2.4, 1.0, 2.0), np.array([1.0, 0.85, 0.45]), emissive=True)
        c.paint(c.mask_ellipse(x, y0 - 2.0, 0.5, 1.0), np.array([1.0, 0.97, 0.80]), emissive=True)
    c.paint(c.mask_poly([(1, 20), (25, 20), (25, 22), (1, 22)]), np.array([0.6, 0.55, 0.45]))
    return c.result(edge_dark=0.15)


@prop('lamp_hanging', 24, 40, 0.24, 0.4, zoff=0.6)
def lamp_hanging(seed=10):
    c = Canvas(24, 40, seed)
    c.paint(c.mask_line([(12, 0), (12, 26)], 0.8), np.array([0.15, 0.15, 0.15]))
    shade = c.mask_poly([(6, 26), (18, 26), (23, 34), (1, 34)])
    c.paint(shade, np.array([0.30, 0.36, 0.30]), c.grad_x(1, 23, 1.2, 0.6))
    c.paint(c.mask_ellipse(12, 35, 3.5, 2.5), np.array([1.0, 0.95, 0.75]), emissive=True)
    return c.result()


@prop('lamp_hanging_off', 24, 40, 0.24, 0.4, zoff=0.6)
def lamp_hanging_off(seed=11):
    c = Canvas(24, 40, seed)
    c.paint(c.mask_line([(12, 0), (12, 26)], 0.8), np.array([0.15, 0.15, 0.15]))
    shade = c.mask_poly([(6, 26), (18, 26), (23, 34), (1, 34)])
    c.paint(shade, np.array([0.30, 0.36, 0.30]), c.grad_x(1, 23, 1.2, 0.6))
    c.paint(c.mask_ellipse(12, 35, 3.5, 2.5), np.array([0.45, 0.43, 0.38]))
    return c.result()


@prop('crates', 48, 40, 0.55, 0.46, solid=True)
def crates(seed=12):
    c = Canvas(48, 40, seed)
    grain = c.tex(3, 3, 0.75, 1.15, aspect=0.3)
    for (x0, y0, x1, y1) in ((2, 16, 26, 40), (24, 20, 46, 40), (10, 2, 32, 18)):
        m = c.mask_poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        c.paint(m, np.array([0.45, 0.33, 0.20]), grain * c.grad_x(x0, x1, 1.15, 0.75))
        for y in np.linspace(y0, y1, 4)[1:-1]:
            c.darken(c.mask_line([(x0, y), (x1, y)], 0.6), 0.45)
        c.darken(c.mask_line([(x0, y0), (x1, y1)], 1.2), 0.25)
        c.darken(c.mask_line([(x0, y0 + 0.3), (x1, y0 + 0.3)], 0.6), -0.3)
    return c.result()


@prop('jars', 48, 64, 0.55, 0.74, solid=True)
def jars(seed=13):
    c = Canvas(48, 64, seed)
    frame = np.clip(sum(c.mask_line([(x, 2), (x, 63)], 2) for x in (3, 45)), 0, 1)
    c.paint(frame, np.array([0.30, 0.20, 0.12]))
    rng = np.random.default_rng(seed)
    for y in (20, 40, 61):
        c.paint(c.mask_poly([(2, y), (46, y), (46, y + 2.5), (2, y + 2.5)]), np.array([0.34, 0.22, 0.13]))
        x = 6
        while x < 40:
            w = rng.uniform(6, 10); h = rng.uniform(10, 16)
            jar = c.mask_poly([(x, y - h), (x + w, y - h), (x + w, y), (x, y)])
            fl = np.array([0.45, 0.48, 0.30]) * rng.uniform(0.7, 1.1)
            c.paint(jar, fl, c.grad_x(x, x + w, 1.3, 0.6), alpha=0.9)
            # specimen silhouette
            c.paint(c.mask_ellipse(x + w / 2, y - h / 2, w / 3.5, h / 3.5), np.array([0.30, 0.25, 0.20]), alpha=0.8)
            c.paint(c.mask_poly([(x - 0.5, y - h - 2), (x + w + 0.5, y - h - 2), (x + w + 0.5, y - h), (x - 0.5, y - h)]), METAL * 0.6)
            c.lighten(c.mask_line([(x + 1.2, y - h + 1), (x + 1.2, y - 2)], 0.6), np.array([0.9, 0.95, 0.85]), 0.5)
            x += w + 2
    return c.result()


@prop('bathtub', 64, 30, 0.9, 0.42, solid=True)
def bathtub(seed=14):
    c = Canvas(64, 30, seed)
    tub = c.mask_poly([(2, 6), (62, 6), (60, 24), (4, 24)])
    c.paint(tub, np.array([0.75, 0.74, 0.68]), c.grad_y(6, 24, 1.15, 0.6) * c.tex(8, 3, 0.85, 1.1))
    c.paint(c.mask_ellipse(32, 7, 29, 2.2), np.array([0.25, 0.30, 0.22]))   # murky water
    for x in (8, 56):
        c.paint(c.mask_poly([(x - 3, 24), (x + 3, 24), (x + 2, 29), (x - 2, 29)]), BRASS * 0.7)
    st = drip = c.mask_line([(20, 6), (21, 14), (20, 20)], 1.3) + c.mask_line([(41, 6), (41, 11)], 1.0)
    c.paint(np.clip(st, 0, 1), np.array([0.35, 0.25, 0.15]), alpha=0.7)
    rusty(c, tub, 0.3)
    return c.result()


@prop('optable', 64, 40, 0.9, 0.57, solid=True)
def optable(seed=15):
    c = Canvas(64, 40, seed)
    tube(c, (32, 20), (32, 37), 4, METAL * 0.8)
    c.paint(c.mask_poly([(20, 36), (44, 36), (46, 40), (18, 40)]), METAL * 0.6)
    top = c.mask_poly([(3, 14), (61, 14), (61, 20), (3, 20)])
    c.paint(top, np.array([0.45, 0.47, 0.45]), c.grad_y(14, 20, 1.2, 0.6))
    pad = c.mask_poly([(5, 11), (59, 11), (59, 14), (5, 14)])
    c.paint(pad, np.array([0.20, 0.22, 0.20]))
    st = (c.tex(4, 3, 0, 1) > 0.55) * (pad + top)
    c.paint(np.clip(st, 0, 1), np.array([0.35, 0.06, 0.04]), alpha=0.8)
    for x in (8, 56):
        c.paint(c.mask_poly([(x - 1, 9), (x + 3, 9), (x + 3, 12), (x - 1, 12)]), np.array([0.25, 0.15, 0.08]))
    return c.result()


@prop('bear', 22, 24, 0.17, 0.19)
def bear(seed=16):
    c = Canvas(22, 24, seed)
    fur = np.array([0.45, 0.32, 0.20])
    sh = c.tex(10, 3, 0.7, 1.15)
    c.paint(c.mask_ellipse(11, 16, 7, 7), fur, sh)
    for x in (5, 17):
        c.paint(c.mask_ellipse(x, 21, 3, 2.5), fur * 0.9, sh)
        c.paint(c.mask_ellipse(x, 13, 2.5, 3), fur * 0.9, sh)
    c.paint(c.mask_ellipse(11, 7, 5.5, 5), fur, sh)
    for x in (6.5, 15.5):
        c.paint(c.mask_ellipse(x, 3, 2, 2), fur * 0.8)
    c.paint(c.mask_ellipse(11, 9, 2.2, 1.6), np.array([0.65, 0.52, 0.38]))
    c.paint(c.mask_ellipse(9, 6.5, 0.8, 0.8), np.array([0.05, 0.05, 0.05]))
    # one eye missing: stuffing
    c.paint(c.mask_ellipse(13.2, 6.5, 1.0, 0.9), np.array([0.85, 0.82, 0.75]))
    c.paint(c.mask_line([(11, 13), (12, 20)], 0.6), np.array([0.85, 0.82, 0.75]))   # torn seam
    return c.result()


@prop('pew', 64, 34, 0.95, 0.5, solid=True)
def pew(seed=17):
    c = Canvas(64, 34, seed)
    grain = c.tex(3, 4, 0.7, 1.15, aspect=0.15)
    back = c.mask_poly([(2, 2), (62, 2), (62, 16), (2, 16)])
    c.paint(back, WOOD * 0.9, grain * c.grad_y(2, 16, 1.2, 0.7))
    c.darken(c.mask_line([(2, 3), (62, 3)], 1.0), -0.25)
    seat = c.mask_poly([(2, 18), (62, 18), (62, 22), (2, 22)])
    c.paint(seat, WOOD, grain * c.grad_y(18, 22, 1.3, 0.7))
    for x in (3, 32, 59):
        c.paint(c.mask_poly([(x, 2), (x + 3, 2), (x + 3, 34), (x, 34)]), WOOD * 0.75, grain)
    c.paint(c.mask_ellipse(4.5, 2, 2.5, 2.5), WOOD * 0.8)
    c.paint(c.mask_ellipse(60.5, 2, 2.5, 2.5), WOOD * 0.8)
    return c.result()


@prop('statue', 30, 72, 0.32, 0.78, solid=True)
def statue(seed=18):
    c = Canvas(30, 72, seed)
    stone = np.array([0.55, 0.54, 0.50])
    sh = c.tex(8, 4, 0.75, 1.15)
    c.paint(c.mask_poly([(5, 60), (25, 60), (27, 72), (3, 72)]), stone * 0.8, sh)
    robe = c.mask_poly([(10, 18), (20, 18), (24, 60), (6, 60)])
    c.paint(robe, stone, sh * c.grad_x(6, 24, 1.15, 0.65))
    c.paint(c.mask_poly([(9, 12), (21, 12), (23, 28), (7, 28)]), stone * 0.95, sh)   # veil
    c.paint(c.mask_ellipse(15, 12, 4.2, 5), stone * 1.05, sh)
    # hands pressed together
    c.paint(c.mask_ellipse(15, 33, 2.2, 3.5), stone * 1.1, sh)
    # face worn away, dark tear streaks
    for x in (13.5, 16.5):
        c.paint(c.mask_line([(x, 12), (x + 0.2, 22), (x - 0.3, 30)], 0.7), np.array([0.25, 0.08, 0.06]), alpha=0.8)
    moss = (c.tex(5, 3, 0, 1) > 0.62) * c.a
    c.paint(moss, np.array([0.28, 0.35, 0.20]), alpha=0.7)
    return c.result()


@prop('boat', 64, 30, 1.2, 0.56, solid=True)
def boat(seed=19):
    c = Canvas(64, 30, seed)
    hull = c.mask_poly([(1, 12), (63, 10), (58, 26), (8, 27)])
    c.paint(hull, np.array([0.30, 0.25, 0.20]), c.grad_y(10, 27, 1.2, 0.5) * c.tex(3, 3, 0.75, 1.15, aspect=0.2))
    c.paint(c.mask_line([(1, 12), (63, 10)], 1.5), np.array([0.45, 0.38, 0.28]))
    c.paint(c.mask_line([(20, 11), (40, 2)], 1.2), WOOD)      # oar
    c.paint(c.mask_poly([(38, 1), (44, 0), (45, 4), (39, 5)]), WOOD)
    return c.result()


@prop('bodybag', 64, 18, 0.9, 0.25, solid=False)
def bodybag(seed=20):
    c = Canvas(64, 18, seed)
    bag = c.mask_poly([(3, 16), (5, 9), (14, 7), (26, 9), (40, 7), (54, 9), (61, 12), (61, 17), (3, 17)])
    c.paint(bag, np.array([0.18, 0.20, 0.17]), c.grad_y(7, 17, 1.4, 0.7) * c.tex(8, 3, 0.8, 1.15))
    c.paint(c.mask_line([(6, 11), (58, 10)], 0.6), METAL * 0.6)
    return c.result()


@prop('rockinghorse', 40, 36, 0.42, 0.38, solid=True)
def rockinghorse(seed=21):
    c = Canvas(40, 36, seed)
    paint_ = np.array([0.80, 0.78, 0.70])
    rock = c.mask_ellipse(20, 40, 19, 8) - c.mask_ellipse(20, 41, 17, 7)
    c.paint(np.clip(rock, 0, 1) * (c.yy > 30), WOOD * 0.8)
    for x in (9, 31):
        c.paint(c.mask_tapered([(x, 20), (x + (2 if x < 20 else -2), 32)], [2.2, 1.8]), paint_ * 0.8)
    body = c.mask_ellipse(20, 18, 12, 5.5)
    c.paint(body, paint_, c.grad_y(12, 24, 1.15, 0.7))
    neck = c.mask_tapered([(28, 16), (32, 8), (33, 5)], [5, 4, 3.5])
    c.paint(neck, paint_, c.grad_x(28, 36, 1.1, 0.7))
    c.paint(c.mask_ellipse(35, 6, 4, 2.6), paint_)
    c.paint(c.mask_ellipse(35.5, 5.2, 0.8, 0.8), np.array([0.05, 0.05, 0.05]))
    mane = c.mask_tapered([(30, 3), (27, 8), (26, 14)], [2, 2, 1.5])
    c.paint(mane, np.array([0.25, 0.12, 0.08]))
    c.paint(c.mask_tapered([(8, 15), (4, 20), (3, 25)], [2, 1.6, 1]), np.array([0.25, 0.12, 0.08]))
    for _ in range(6):
        x, y = c.rng.uniform(10, 30), c.rng.uniform(14, 22)
        c.paint(c.mask_ellipse(x, y, 1.0, 0.7), np.array([0.30, 0.18, 0.12]))
    c.paint(c.mask_poly([(14, 13), (22, 13), (21, 16), (15, 16)]), np.array([0.45, 0.10, 0.08]))
    return c.result()


@prop('desk', 56, 34, 0.75, 0.46, solid=True)
def desk(seed=22):
    c = Canvas(56, 34, seed)
    grain = c.tex(3, 3, 0.75, 1.15, aspect=0.2)
    top = c.mask_poly([(1, 8), (55, 8), (55, 12), (1, 12)])
    c.paint(top, WOOD * 1.15, grain * c.grad_y(8, 12, 1.3, 0.8))
    for x0 in (3, 38):
        ped = c.mask_poly([(x0, 12), (x0 + 15, 12), (x0 + 15, 34), (x0, 34)])
        c.paint(ped, WOOD * 0.85, grain * c.grad_x(x0, x0 + 15, 1.15, 0.75))
        for y in (15, 22, 28):
            c.darken(c.mask_line([(x0 + 1, y), (x0 + 14, y)], 0.6), 0.5)
            c.paint(c.mask_ellipse(x0 + 7.5, y + 3, 1.4, 0.8), BRASS)
    # papers, lamp, telephone
    c.paint(c.mask_poly([(10, 6), (22, 5), (23, 8), (11, 8)]), PAPER)
    c.paint(c.mask_line([(44, 8), (45, 0)], 0.8), BRASS * 0.8)
    c.paint(c.mask_poly([(40, 0), (50, 0), (48, 3), (42, 3)]), np.array([0.15, 0.30, 0.18]))
    c.paint(c.mask_ellipse(30, 6.5, 4, 1.8), np.array([0.08, 0.08, 0.08]))
    return c.result()


@prop('cot', 48, 30, 0.6, 0.38, solid=True)
def cot(seed=23):
    c = Canvas(48, 30, seed)
    WH = np.array([0.82, 0.80, 0.74])
    for x in (2, 45):
        tube(c, (x, 4), (x, 29), 1.6, WH)
    tube(c, (2, 5), (45, 5), 1.3, WH * 0.95)
    tube(c, (2, 20), (45, 20), 1.3, WH * 0.9)
    for x in range(6, 44, 3):
        tube(c, (x, 5), (x, 20), 0.8, WH * 0.85)
    blanket = c.mask_poly([(4, 14), (43, 13), (44, 19), (3, 19)])
    c.paint(blanket, np.array([0.55, 0.62, 0.70]), c.grad_y(13, 19, 1.2, 0.7) * c.tex(8, 2, 0.85, 1.1))
    rusty(c, c.a, 0.25)
    return c.result()


@prop('surglamp', 40, 30, 0.5, 0.36, zoff=0.62, fullbright=False)
def surglamp(seed=24):
    c = Canvas(40, 30, seed)
    c.paint(c.mask_line([(20, 0), (20, 10)], 1.2), METAL * 0.6)
    dome = c.mask_ellipse(20, 18, 18, 9) * (c.yy < 19)
    c.paint(dome, METAL * 0.9, c.grad_y(9, 19, 1.3, 0.6))
    for x in (10, 20, 30):
        c.paint(c.mask_ellipse(x, 19, 4, 2.2), np.array([1.0, 0.97, 0.85]), emissive=True)
    return c.result(edge_dark=0.15)


@prop('cart', 40, 40, 0.45, 0.45, solid=True)
def cart(seed=25):
    c = Canvas(40, 40, seed)
    basket = c.mask_poly([(3, 8), (37, 8), (34, 32), (6, 32)])
    c.paint(basket, np.array([0.50, 0.44, 0.34]), c.tex(20, 2, 0.7, 1.1) * c.grad_x(3, 37, 1.1, 0.7))
    for x in range(6, 36, 4):
        c.darken(c.mask_line([(x, 9), (x - 1, 31)], 0.5), 0.35)
    linen = c.mask_poly([(4, 8), (10, 2), (20, 5), (30, 1), (36, 8)])
    c.paint(linen, SHEET, c.grad_y(1, 9, 1.2, 0.8))
    c.paint((c.tex(5, 3, 0, 1) > 0.65) * linen, np.array([0.45, 0.12, 0.08]), alpha=0.8)
    for x in (8, 32):
        c.paint(c.mask_ellipse(x, 36, 3, 3), np.array([0.08, 0.08, 0.08]))
    return c.result()


@prop('sheets', 44, 72, 0.6, 0.98, solid=False)
def sheets(seed=26):
    c = Canvas(44, 72, seed)
    c.paint(c.mask_line([(0, 2), (44, 2)], 0.8), np.array([0.3, 0.3, 0.28]))
    pts = [(2, 2)]
    for k in range(9):
        pts.append((2 + k * 5, 64 + c.rng.uniform(-4, 6)))
    pts.append((42, 2))
    sheet = c.mask_poly(pts)
    folds = 0.8 + 0.2 * np.sin(c.xx * 0.9 + np.sin(c.yy * 0.1) * 2)
    c.paint(sheet, SHEET, folds * c.grad_y(2, 70, 1.1, 0.75) * c.tex(10, 2, 0.9, 1.05))
    st = (c.tex(4, 3, 0, 1) > 0.66) * sheet * (c.yy > 30)
    c.paint(st, np.array([0.40, 0.25, 0.15]), alpha=0.6)
    # a silhouette pressing through the cloth...
    c.darken(c.mask_ellipse(22, 22, 5, 6) * sheet, 0.25)
    c.darken(c.mask_poly([(14, 28), (30, 28), (32, 56), (12, 56)]) * sheet, 0.15)
    return c.result()


@prop('candelabra', 22, 72, 0.22, 0.72, solid=True)
def candelabra(seed=27):
    c = Canvas(22, 72, seed)
    IRON = np.array([0.20, 0.18, 0.15])
    tube(c, (11, 18), (11, 68), 1.6, IRON)
    c.paint(c.mask_poly([(5, 68), (17, 68), (19, 72), (3, 72)]), IRON)
    c.paint(c.mask_line([(3, 18), (6, 22), (11, 23), (16, 22), (19, 18)], 1.2), IRON)
    for x in (3, 11, 19):
        top = 10 if x == 11 else 12
        c.paint(c.mask_poly([(x - 1.3, top), (x + 1.3, top), (x + 1.3, 19), (x - 1.3, 19)]), np.array([0.85, 0.82, 0.70]))
        c.paint(c.mask_ellipse(x, top - 2.4, 1.0, 2.0), np.array([1.0, 0.85, 0.45]), emissive=True)
        c.paint(c.mask_ellipse(x, top - 2.0, 0.5, 1.0), np.array([1.0, 0.97, 0.80]), emissive=True)
    return c.result(edge_dark=0.15)


@prop('coffin', 64, 26, 0.95, 0.38, solid=True)
def coffin(seed=28):
    c = Canvas(64, 26, seed)
    lid = c.mask_poly([(2, 8), (20, 4), (62, 6), (62, 14), (20, 15), (2, 13)])
    body = c.mask_poly([(2, 13), (20, 15), (62, 14), (61, 26), (3, 26)])
    grain = c.tex(3, 3, 0.7, 1.15, aspect=0.2)
    c.paint(body, WOOD * 0.7, grain * c.grad_y(13, 26, 1.1, 0.6))
    c.paint(lid, WOOD * 0.9, grain * c.grad_y(4, 15, 1.3, 0.7))
    c.paint(c.mask_line([(30, 6), (30, 13)], 1.0), BRASS * 0.8)
    c.paint(c.mask_line([(26, 9), (34, 9)], 1.0), BRASS * 0.8)
    # lid slightly open: dark slit and fingers
    c.paint(c.mask_line([(40, 14), (61, 13.5)], 1.2), np.array([0.02, 0.02, 0.02]))
    for x in (46, 49, 52):
        c.paint(c.mask_line([(x, 13.5), (x + 0.5, 16)], 0.9), np.array([0.62, 0.60, 0.52]))
    return c.result()


@prop('bucket', 18, 18, 0.15, 0.15)
def bucket(seed=29):
    c = Canvas(18, 18, seed)
    b = c.mask_poly([(2, 4), (16, 4), (14, 17), (4, 17)])
    c.paint(b, METAL * 0.75, c.grad_x(2, 16, 1.3, 0.6))
    c.paint(c.mask_ellipse(9, 4, 7, 1.6), np.array([0.25, 0.10, 0.06]))
    c.paint(c.mask_line([(2, 4), (9, -1), (16, 4)], 0.6), METAL)
    rusty(c, b, 0.5)
    return c.result()


# ------------------------------------------------------------------ items
@prop('battery', 16, 26, 0.12, 0.19, glint=True)
def battery(seed=30):
    c = Canvas(16, 26, seed)
    body = c.mask_poly([(3, 5), (13, 5), (13, 25), (3, 25)])
    c.paint(body, np.array([0.12, 0.22, 0.45]), c.grad_x(3, 13, 1.4, 0.55))
    label = c.mask_poly([(3, 10), (13, 10), (13, 19), (3, 19)])
    c.paint(label, np.array([0.85, 0.65, 0.15]), c.grad_x(3, 13, 1.3, 0.55))
    c.paint(c.mask_poly([(3, 13), (13, 13), (13, 15), (3, 15)]), np.array([0.65, 0.15, 0.10]), c.grad_x(3, 13, 1.3, 0.6))
    c.paint(c.mask_ellipse(8, 5, 5, 1.6), METAL * 1.2)
    c.paint(c.mask_poly([(6.5, 1.5), (9.5, 1.5), (9.5, 4.5), (6.5, 4.5)]), METAL * 1.3)
    return c.result(edge_dark=0.2)


@prop('fuse', 30, 14, 0.24, 0.11, glint=True)
def fuse(seed=31):
    c = Canvas(30, 14, seed)
    body = c.mask_poly([(6, 3), (24, 3), (24, 12), (6, 12)])
    c.paint(body, np.array([0.40, 0.22, 0.12]), c.grad_y(3, 12, 1.4, 0.55))
    c.paint(c.mask_poly([(10, 5.5), (20, 5.5), (20, 9.5), (10, 9.5)]), PAPER * 0.9, c.grad_y(5, 10, 1.2, 0.8))
    for x0 in (1, 23):
        cap = c.mask_poly([(x0, 2), (x0 + 6, 2), (x0 + 6, 13), (x0, 13)])
        c.paint(cap, BRASS, c.grad_y(2, 13, 1.5, 0.5))
        c.darken(c.mask_line([(x0 + 3, 2), (x0 + 3, 13)], 0.5), 0.3)
    return c.result(edge_dark=0.2)


@prop('key', 26, 16, 0.2, 0.12, glint=True)
def key(seed=32):
    c = Canvas(26, 16, seed)
    bow = c.mask_ellipse(6, 8, 4.5, 4.5) - c.mask_ellipse(6, 8, 2.2, 2.2)
    c.paint(np.clip(bow, 0, 1), BRASS, c.grad_y(3, 13, 1.4, 0.6))
    c.paint(c.mask_poly([(10, 7), (22, 7), (22, 9.5), (10, 9.5)]), BRASS, c.grad_y(7, 10, 1.4, 0.6))
    for x in (16, 19.5):
        c.paint(c.mask_poly([(x, 9.5), (x + 2, 9.5), (x + 2, 13), (x, 13)]), BRASS * 0.9)
    tag = c.mask_poly([(14, 1), (24, 0.5), (25, 5), (15, 5.5)])
    c.paint(tag, PAPER, c.grad_y(0, 6, 1.1, 0.8))
    c.paint(c.mask_line([(10, 6), (14, 3)], 0.5), np.array([0.6, 0.55, 0.45]))
    return c.result(edge_dark=0.2)


@prop('note', 22, 16, 0.18, 0.13, glint=True)
def note(seed=33):
    c = Canvas(22, 16, seed)
    pg = c.mask_poly([(2, 4), (18, 1), (20, 13), (4, 15)])
    c.paint(pg, PAPER, c.grad_x(2, 20, 1.15, 0.8) * c.tex(6, 2, 0.9, 1.05))
    for k in range(4):
        y = 5 + k * 2.4
        c.paint(c.mask_line([(5, y + 0.5), (16, y - 1.5)], 0.45), np.array([0.25, 0.22, 0.30]))
    c.paint(c.mask_poly([(14, 11), (20, 13), (18, 14.5)]), PAPER * 0.7)   # curled corner
    return c.result(edge_dark=0.2)


@prop('tape', 22, 16, 0.18, 0.13, glint=True)
def tape(seed=34):
    """Wax phonograph cylinder in a case (Thomas's recordings)."""
    c = Canvas(22, 16, seed)
    case = c.mask_poly([(3, 2), (19, 2), (19, 15), (3, 15)])
    c.paint(case, np.array([0.30, 0.16, 0.10]), c.grad_x(3, 19, 1.3, 0.6))
    c.paint(c.mask_poly([(6, 5), (16, 5), (16, 12), (6, 12)]), np.array([0.55, 0.45, 0.25]), c.grad_x(6, 16, 1.4, 0.6))
    return c.result(edge_dark=0.2)


def add_glint(res, x, y):
    rgb, mask, em = res
    rgb = rgb.copy(); mask = mask.copy(); em = em.copy()
    h, w = mask.shape
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        xx, yy = x + dx, y + dy
        if 0 <= xx < w and 0 <= yy < h:
            rgb[yy, xx] = GLINT if (dx, dy) == (0, 0) else np.array([1.0, 0.95, 0.75])
            mask[yy, xx] = True
            em[yy, xx] = True
    return rgb, mask, em


if __name__ == '__main__':
    import sys
    frames = [PROPS[k]['fn']() for k in PROPS]
    preview(frames, sys.argv[1], scale=3)


@prop('telephone', 28, 22, 0.2, 0.16)
def telephone(seed=35):
    """A black Bakelite desk telephone: the handset on its cradle, the dial."""
    c = Canvas(28, 22, seed)
    BAK = np.array([0.07, 0.065, 0.06])
    body = c.mask_poly([(4, 10), (24, 10), (27, 21), (1, 21)])
    c.paint(body, BAK, c.grad_y(10, 21, 1.6, 0.7))
    # cradle prongs and the handset lying across them
    for x in (8, 20):
        c.paint(c.mask_poly([(x - 1.5, 6), (x + 1.5, 6), (x + 1, 11), (x - 1, 11)]), BAK * 1.4)
    hs = c.mask_tapered([(2, 5), (8, 3.5), (20, 3.5), (26, 5)], [4.5, 2.6, 2.6, 4.5])
    c.paint(hs, BAK * 1.2, c.grad_y(1, 8, 2.6, 0.6))
    # the dial: a pale ring with finger holes, a brass centre
    c.paint(c.mask_ellipse(14, 16, 5.5, 3.6), np.array([0.62, 0.60, 0.54]), c.grad_y(12, 20, 1.2, 0.8))
    for k in range(8):
        a = np.pi * (0.15 + 1.55 * k / 7)
        c.paint(c.mask_ellipse(14 + 4.1 * np.cos(a), 16 - 2.6 * np.sin(a), 0.9, 0.7), BAK * 1.5)
    c.paint(c.mask_ellipse(14, 16, 1.6, 1.1), BRASS)
    # the cord trailing off the back
    c.paint(c.mask_line([(25, 14), (27, 18), (26, 21)], 0.8), BAK * 1.2)
    return c.result(edge_dark=0.25)
