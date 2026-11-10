# SPDX-License-Identifier: MIT
"""Low-poly mesh construction for Hollowmere's 3D props.

Units are tiles (1 tile = 1.5 m; rooms are 2 tiles tall, the eye is at 1).
x, y lie on the floor plane (y points "south", like the map), z is up.
Faces carry a texture name, flags and per-vertex texel coordinates. Vertical
faces are emitted bottom-left, bottom-right, top-right, top-left as seen
from outside so the engine can texture them like little walls.
"""
import math

FF_VERT, FF_2SIDED, FF_THIN = 1, 2, 8
TEXELS = 64          # texels per tile for tiled materials


def shade_bits(s):
    return (s & 15) << 4


class Mesh:
    def __init__(self, name=''):
        self.name = name
        self.verts = []
        self.faces = []
        self.boxes = []          # collision footprints (x0, y0, x1, y1)
        self.solid = True        # blocks movement
        self.block_cells = None  # override for creature pathing

    # ---------------------------------------------------------------- basics
    def v(self, x, y, z):
        key = (round(x * 256), round(y * 256), round(z * 256))
        for i, w in enumerate(self.verts):
            if w == key:
                return i
        self.verts.append(key)
        return len(self.verts) - 1

    def face(self, pts, tex, uv, normal, vert=False, two_sided=False, shade=0, thin=False):
        if len(pts) > 4:
            # the rasterizer takes tris and quads: fan the polygon into quads
            k = 1
            while k < len(pts) - 1:
                sel = [0] + list(range(k, min(k + 3, len(pts))))
                self.face([pts[i] for i in sel], tex, [uv[i] for i in sel], normal, vert, two_sided, shade, thin)
                k += 2
            return
        idx = [self.v(*p) for p in pts]
        n = normal
        ln = math.sqrt(sum(c * c for c in n)) or 1.0
        n = tuple(int(round(c / ln * 64)) for c in n)
        flags = (FF_VERT if vert else 0) | (FF_2SIDED if two_sided else 0) | (FF_THIN if thin else 0) | shade_bits(shade)
        uv = [(max(0, min(255, int(round(u)))), max(0, min(255, int(round(w))))) for u, w in uv]
        self.faces.append(dict(v=idx, tex=tex, flags=flags, n=n, uv=uv))

    def wall(self, a, b, z0, z1, tex, normal, u0=0.0, u1=None, v_top=0.0, v_bot=None, shade=0, two_sided=False,
             thin=False):
        """Vertical quad from floor point a to b (left to right seen from outside).
        thin: a post or pole that must not vanish with distance (never
        dropped by the level of detail, and at least one column wide)."""
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if u1 is None:
            u1 = u0 + L * TEXELS
        if v_bot is None:
            v_bot = v_top + min(64.0, (z1 - z0) * TEXELS)
        self.face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], tex,
                  [(u0, v_bot), (u1, v_bot), (u1, v_top), (u0, v_top)],
                  (normal[0], normal[1], 0), vert=True, shade=shade, two_sided=two_sided, thin=thin)

    def vquad(self, a, b, za0, za1, zb0, zb1, tex, normal, u0=0.0, u1=64.0, v_top=0.0, v_bot=64.0,
              shade=0, two_sided=False):
        """Vertical quad from floor point a to b (left to right seen from
        outside) spanning za0..za1 at a and zb0..zb1 at b: sloped top and
        bottom edges (stair strings, handrails, spandrels). Still drawn as a
        wall-like face; the texture runs from the top edge to the bottom one."""
        self.face([(a[0], a[1], za0), (b[0], b[1], zb0), (b[0], b[1], zb1), (a[0], a[1], za1)], tex,
                  [(u0, v_bot), (u1, v_bot), (u1, v_top), (u0, v_top)],
                  (normal[0], normal[1], 0), vert=True, shade=shade, two_sided=two_sided)

    def flat(self, pts, z, tex, up=True, scale=TEXELS, shade=0, uv=None, two_sided=False):
        """Horizontal polygon at height z; pts in any convex order."""
        P = [(p[0], p[1], z) for p in pts]
        if uv is None:
            uv = [(p[0] * scale, p[1] * scale) for p in pts]
            mu, mv = min(u for u, _ in uv), min(w for _, w in uv)
            off_u, off_v = math.floor(mu / 64) * 64, math.floor(mv / 64) * 64
            uv = [(u - off_u, w - off_v) for u, w in uv]
        self.face(P, tex, uv, (0, 0, 1 if up else -1), shade=shade, two_sided=two_sided)

    # ---------------------------------------------------------------- solids
    def box(self, x0, y0, z0, x1, y1, z1, tex, top=None, bottom=None, front=None, back=None,
            sides=None, skip=(), shade_top=1, decal=(), collide=True, vfit=()):
        """Axis-aligned box. tex: default material. Faces: 's' (+y, the model's
        front), 'n' (-y, back), 'w' (-x), 'e' (+x), 't' top, 'b' bottom.
        decal: faces whose texture spans the whole face (u 0..64, v 0..64);
        vfit: faces whose texture spans the face's height (v 0..64) but
        repeats along it (u: 64 texels per tile)."""
        names = dict(s=front, n=back, w=sides, e=sides, t=top, b=bottom)   # model front faces +y
        def tx(f):
            return names.get(f) or tex
        h = z1 - z0
        def uvx(f, L):
            return (0.0, 64.0) if f in decal else (0.0, L * TEXELS)
        def vrange(f):
            return (0.0, 64.0) if f in decal or f in vfit else (0.0, min(64.0, h * TEXELS))
        if 'n' not in skip:   # facing -y: seen from the north, left is +x? (viewer faces +y: right = -x)
            u0, u1 = uvx('n', x1 - x0); vt, vb = vrange('n')
            self.wall((x1, y0), (x0, y0), z0, z1, tx('n'), (0, -1), u0, u1, vt, vb)
        if 's' not in skip:
            u0, u1 = uvx('s', x1 - x0); vt, vb = vrange('s')
            self.wall((x0, y1), (x1, y1), z0, z1, tx('s'), (0, 1), u0, u1, vt, vb)
        if 'w' not in skip:
            u0, u1 = uvx('w', y1 - y0); vt, vb = vrange('w')
            self.wall((x0, y0), (x0, y1), z0, z1, tx('w'), (-1, 0), u0, u1, vt, vb)
        if 'e' not in skip:
            u0, u1 = uvx('e', y1 - y0); vt, vb = vrange('e')
            self.wall((x1, y1), (x1, y0), z0, z1, tx('e'), (1, 0), u0, u1, vt, vb)
        rect = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        if 't' not in skip:
            if 't' in decal:
                self.flat(rect, z1, tx('t'), True, shade=shade_top,
                          uv=[(0, 0), (64, 0), (64, 64), (0, 64)])
            else:
                self.flat(rect, z1, tx('t'), True, shade=shade_top)
        if 'b' not in skip:
            self.flat(rect, z0, tx('b'), False, shade=-3)
        if collide and z0 < 0.9:
            self.boxes.append((x0, y0, x1, y1))

    def prism(self, cx, cy, r, z0, z1, n, tex, top=None, bottom=False, rot=0.0, collide=False, u_tiles=None):
        """Upright n-sided prism (legs, posts, columns, lamp shades...)."""
        pts = [(cx + r * math.cos(rot + 2 * math.pi * k / n), cy + r * math.sin(rot + 2 * math.pi * k / n))
               for k in range(n)]
        per = 2 * math.pi * r
        ut = (per * TEXELS) if u_tiles is None else u_tiles * 64
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            mx, my = (a[0] + b[0]) / 2 - cx, (a[1] + b[1]) / 2 - cy
            # seen from outside, going counter-clockwise in math terms is right-to-left
            self.wall(b, a, z0, z1, tex, (mx, my), u0=ut * k / n, u1=ut * (k + 1) / n,
                      v_top=0, v_bot=min(64.0, (z1 - z0) * TEXELS))
        if top:
            self.flat(pts, z1, top, True, shade=1)
        if bottom:
            self.flat(pts, z0, bottom if isinstance(bottom, str) else tex, False, shade=-3)
        if collide:
            self.boxes.append((cx - r, cy - r, cx + r, cy + r))

    def pole(self, cx, cy, d, z0, z1, tex, v_top=0.0, v_bot=64.0):
        """A slim upright pole as two crossed two-sided quads, the texture's
        full width across it (shade it as a cylinder). It keeps the same
        width from any side and stays drawn at any distance."""
        h = d / 2
        self.wall((cx - h, cy), (cx + h, cy), z0, z1, tex, (0, 1), 0, 64, v_top, v_bot, two_sided=True, thin=True)
        self.wall((cx, cy + h), (cx, cy - h), z0, z1, tex, (1, 0), 0, 64, v_top, v_bot, two_sided=True, thin=True)
        # once the pole is about a column wide the first quad, never less
        # than a column, is enough: the second one drops out
        self.faces[-1]['lod'] = min(4.0, d * 80)

    def frustum(self, cx, cy, r0, r1, z0, z1, n, tex, top=None, rot=0.0):
        """Tapered upright prism (lamp shades, vases, table pedestals). Not FF_VERT."""
        p0 = [(cx + r0 * math.cos(rot + 2 * math.pi * k / n), cy + r0 * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]
        p1 = [(cx + r1 * math.cos(rot + 2 * math.pi * k / n), cy + r1 * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]
        for k in range(n):
            a0, b0 = p0[k], p0[(k + 1) % n]
            a1, b1 = p1[k], p1[(k + 1) % n]
            mx, my = (a0[0] + b0[0]) / 2 - cx, (a0[1] + b0[1]) / 2 - cy
            nz = (r0 - r1) / max(0.01, (z1 - z0))
            self.face([(b0[0], b0[1], z0), (a0[0], a0[1], z0), (a1[0], a1[1], z1), (b1[0], b1[1], z1)], tex,
                      [(64 * k / n, 64), (64 * (k + 1) / n, 64), (64 * (k + 1) / n, 0), (64 * k / n, 0)],
                      (mx, my, nz * math.hypot(mx, my)))
        if top:
            self.flat(p1, z1, top, True, shade=1)

    def loft(self, rings, n, tex, ax=1.0, ay=1.0, rot=0.0):
        """A tapering sleeve through rings (cx, cy, r, z, v), bottom to top:
        each ring an ellipse of radii r*ax, r*ay; u wraps once round (side k
        spans u 64k/n..64(k+1)/n, its middle at angle rot + 2pi(k+.5)/n).
        Rings are scaled copies of each other, so every face is planar."""
        def pt(rg, k):
            a = rot + 2 * math.pi * k / n
            return (rg[0] + rg[2] * ax * math.cos(a), rg[1] + rg[2] * ay * math.sin(a), rg[3])
        for i in range(len(rings) - 1):
            lo, hi = rings[i], rings[i + 1]
            for k in range(n):
                a0, b0, a1, b1 = pt(lo, k), pt(lo, k + 1), pt(hi, k), pt(hi, k + 1)
                e1 = [a0[j] - b0[j] for j in range(3)]
                e2 = [b1[j] - b0[j] for j in range(3)]
                nrm = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
                mid = [(a0[0] + b0[0]) / 2 - lo[0], (a0[1] + b0[1]) / 2 - lo[1]]
                if nrm[0] * mid[0] + nrm[1] * mid[1] < 0:
                    nrm = [-c for c in nrm]
                self.face([b0, a0, a1, b1], tex,
                          [(64 * k / n, lo[4]), (64 * (k + 1) / n, lo[4]), (64 * (k + 1) / n, hi[4]), (64 * k / n, hi[4])],
                          tuple(nrm))

    def slope(self, quad, tex, normal, uv=None, shade=0, two_sided=False):
        """Arbitrary planar quad (chair backs, lids, roof slopes)."""
        if uv is None:
            uv = [(0, 64), (64, 64), (64, 0), (0, 0)]
        self.face(quad, tex, uv, normal, shade=shade, two_sided=two_sided)

    # ---------------------------------------------------------------- transforms
    def merge(self, other, dx=0.0, dy=0.0, dz=0.0, rot=0):
        """Add another mesh rotated by rot quarter turns and translated."""
        c, s = [(1, 0), (0, 1), (-1, 0), (0, -1)][rot % 4]
        def tp(x, y):
            return (x * c - y * s + dx, x * s + y * c + dy)
        for f in other.faces:
            pts = []
            for i in f['v']:
                x, y, z = (q / 256 for q in other.verts[i])
                X, Y = tp(x, y)
                pts.append((X, Y, z + dz))
            nx, ny, nz = f['n']
            N = (nx * c - ny * s, nx * s + ny * c, nz)
            idx = [self.v(*p) for p in pts]
            self.faces.append(dict(v=idx, tex=f['tex'], flags=f['flags'], n=N, uv=list(f['uv'])))
        for (x0, y0, x1, y1) in other.boxes:
            a, b = tp(x0, y0), tp(x1, y1)
            self.boxes.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])))
        return self

    def shift(self, dx, dy):
        """Move the geometry by (dx, dy) in 1/256 tile (whole units, so the
        vertices stay exact) relative to the model's origin."""
        self.verts = [(x + dx, y + dy, z) for (x, y, z) in self.verts]
        self.boxes = [(x0 + dx / 256, y0 + dy / 256, x1 + dx / 256, y1 + dy / 256) for (x0, y0, x1, y1) in self.boxes]
        return self

    def radius(self):
        return max(math.hypot(x, y) for x, y, z in self.verts) / 256 if self.verts else 0.1

    def zmax(self):
        return max(z for x, y, z in self.verts) / 256 if self.verts else 0

    def stats(self):
        return f"{self.name}: {len(self.verts)} verts, {len(self.faces)} faces"
