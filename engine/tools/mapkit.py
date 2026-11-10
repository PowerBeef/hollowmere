# SPDX-License-Identifier: MIT
"""Helpers for writing Hollowmere floor plans in code instead of ASCII art.

    P = Plan(14, 11)
    P.room('H', 4, 5, 8, 10)          # inclusive cell rectangle
    P.door(6, 5, 'N', 'a')            # edge char on the north edge of cell (6, 5)
    MAP = P.render()

Walls appear automatically between cells of different rooms and around the
outside; doors, arches and windows are set on edges explicitly.
Prop helpers place wall furniture flush against a wall, facing into the room.
"""


class Plan:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.cell = [[' '] * w for _ in range(h)]
        self.edges = {}

    def room(self, ch, x0, y0, x1, y1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.cell[y][x] = ch
        return self

    def door(self, x, y, o, ch='d'):
        """o: 'N' (edge above cell x,y) or 'W' (edge left of it); also 'S', 'E'."""
        if o == 'S':
            x, y, o = x, y + 1, 'N'
        elif o == 'E':
            x, y, o = x + 1, y, 'W'
        self.edges[(x, y, o)] = ch
        return self

    def wall(self, x, y, o):
        return self.door(x, y, o, '|' if o in 'WE' else '-')

    def render(self):
        W, H = self.w, self.h
        rows = [[' '] * (2 * W + 1) for _ in range(2 * H + 1)]
        for y in range(H):
            for x in range(W):
                rows[2 * y + 1][2 * x + 1] = self.cell[y][x]

        def c(x, y):
            return self.cell[y][x] if 0 <= x < W and 0 <= y < H else ' '
        for y in range(H + 1):
            for x in range(W + 1):
                rows[2 * y][2 * x] = '+'
        for y in range(H):
            for x in range(W + 1):              # west edges
                a, b = c(x - 1, y), c(x, y)
                ch = self.edges.get((x, y, 'W'))
                if ch is None:
                    ch = '|' if a != b and (a != ' ' or b != ' ') else ' '
                rows[2 * y + 1][2 * x] = ch
        for y in range(H + 1):
            for x in range(W):                  # north edges
                a, b = c(x, y - 1), c(x, y)
                ch = self.edges.get((x, y, 'N'))
                if ch is None:
                    ch = '-' if a != b and (a != ' ' or b != ' ') else ' '
                rows[2 * y][2 * x + 1] = ch
        return '\n' + '\n'.join(''.join(r) for r in rows) + '\n'


# ------------------------------------------------------------- furniture
E = 0.03        # gap between a wall piece and the wall


def on_n(model, x, y0, **kw):
    """Back against the north wall at y=y0, facing south."""
    return dict(model=model, x=x, y=y0 + E, angle=0, **kw)


def on_s(model, x, y1, **kw):
    return dict(model=model, x=x, y=y1 - E, angle=128, **kw)


def on_w(model, x0, y, **kw):
    return dict(model=model, x=x0 + E, y=y, angle=192, **kw)


def on_e(model, x1, y, **kw):
    return dict(model=model, x=x1 - E, y=y, angle=64, **kw)


FACING = {'S': 0, 'W': 64, 'N': 128, 'E': 192}


def at(model, x, y, facing='S', **kw):
    """Free-standing piece centred at (x, y) with its front towards `facing`
    (or an angle 0..255)."""
    a = FACING[facing] if isinstance(facing, str) else facing
    return dict(model=model, x=x, y=y, angle=a, **kw)
