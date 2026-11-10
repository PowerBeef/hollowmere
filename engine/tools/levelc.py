# SPDX-License-Identifier: MIT
"""Level compiler for Hollowmere's thin-wall maps.

A level module draws its floor plan as ASCII on a (2W+1) x (2H+1) grid:
even rows/columns are edges and corners, odd row/odd column positions are
cells. A cell holds a room letter (or ' ' for outside). Edge characters:

    '-' '|'   wall               ' '  open (or a wall if one side is outside)
    'd'       single door        'D'  double door
    'a'       wide archway       'n'  narrow archway with side panels
    'w'       window             'x'  closed door that is used as an exit/sign
    'l'       a door that must have lock= in EDGES (it is otherwise a 'd':
              the letter marks it on the plan, the option locks it)

ROOMS maps letters to dict(wall=texture, mat=floor material index, name=...).
EDGES gives per-edge options keyed by (x, y, 'N'|'W'): lock, swing, event,
sign, tex, flags... PROPS places 3D furniture, THINGS sprites and items.
"""
import math
import numpy as np

import limits
from limits import check, in_range

MAP_W, MAP_H = limits.MAP_W, limits.MAP_H
GRID = 64

DIRS = {'E': 0, 'S': 16384, 'W': 32768, 'N': 49152}
FACE_ANG = {'S': 0, 'W': 64, 'N': 128, 'E': 192}     # prop facing -> u8 angle (model front is +y)
INTER_TYPES = {'locker': 1, 'fusebox': 2, 'generator': 3, 'exit': 4, 'event': 5, 'sign': 6}
LIGHT_MODES = {'steady': 0, 'flicker': 1, 'buzz': 2, 'pulse': 3, 'candle': 4}
DOOR_FLAGS = {'startopen': 1, 'scripted': 2, 'nomonster': 4}
EK_WALL, EK_DOOR, EK_ARCH = 1, 2, 3

# door/arch geometry, shared with the engine's frame textures
DOOR_GEOM = {
    'single': dict(panel=13, lintel=45),     # 38/64 = 0.59 tile wide, 1.4 tiles tall
    'double': dict(panel=4, lintel=48),      # 0.875 wide, 1.5 tall
    'arch':   dict(panel=2, lintel=52),      # 0.94 wide, 1.62 tall
    'narrow': dict(panel=14, lintel=48),
}
LEAF_STYLE = {'leaf_panel': 'wood', 'leaf_wood': 'wood', 'leaf_metal': 'metal', 'leaf_ward': 'wood',
              'leaf_cellar': 'wood', 'leaf_double': 'wood'}


class Level:
    pass


def parse(mod, ids, models=None):
    tex_ids, flat_ids, ptex_ids = ids['wall'], ids['flat'], ids['ptex']
    model_ids, thing_types = ids['model'], ids['thing']
    L = Level()
    L.name = mod.NAME
    L.mod = mod
    rows = mod.MAP.strip('\n').split('\n')
    width = max(len(r) for r in rows)
    rows = [r.ljust(width) for r in rows]
    H = (len(rows) - 1) // 2
    W = (width - 1) // 2
    name = mod.NAME
    check(len(rows) >= 3 and width >= 3 and len(rows) % 2 == 1 and width % 2 == 1, name,
          f"the MAP is {width} characters by {len(rows)} rows: it must be 2W+1 by 2H+1 (edges on even rows and columns, cells on odd ones)")
    check(W <= MAP_W - 1 and H <= MAP_H - 1, name, f"the map is {W} by {H} cells: the most is {MAP_W - 1} by {MAP_H - 1}")
    L.W, L.H = W, H
    rooms = mod.ROOMS
    mats = mod.MATERIALS
    check(1 <= len(mats) <= limits.MAX_MATERIALS, name, f"MATERIALS has {len(mats)} entries: it needs 1 to {limits.MAX_MATERIALS} (floor, ceiling) pairs")
    for ch, r in rooms.items():
        check('wall' in r and 'name' in r, name, f"room '{ch}' needs wall= and name=")
        in_range(r.get('mat', 0), 0, len(mats) - 1, name, f"mat= of room '{ch}'")
    cell = [[' '] * MAP_W for _ in range(MAP_H)]
    for y in range(H):
        for x in range(W):
            ch = rows[2 * y + 1][2 * x + 1]
            if ch != ' ':
                check(ch in rooms, name, f"cell {x},{y} is room '{ch}', which ROOMS does not have")
            cell[y][x] = ch
    L.cell = cell

    def inside(x, y):
        return 0 <= x < MAP_W and 0 <= y < MAP_H and cell[y][x] != ' '

    def edge_char(x, y, o):
        if o == 'N':
            r, c = 2 * y, 2 * x + 1
        else:
            r, c = 2 * y + 1, 2 * x
        if 0 <= r < len(rows) and 0 <= c < width:
            return rows[r][c]
        return ' '

    def room_wall(ch):
        return rooms[ch]['wall'] if ch != ' ' else None

    # ---- edges
    opts = {k: dict(v) for k, v in getattr(mod, 'EDGES', {}).items()}
    # DECOR: (x, y, side, kind) puts a picture/mirror/sconce on that wall of cell (x, y)
    for (dx_, dy_, side, kind) in getattr(mod, 'DECOR', []):
        key, which = {'N': ((dx_, dy_, 'N'), 'deco_high'), 'S': ((dx_, dy_ + 1, 'N'), 'deco_low'),
                      'W': ((dx_, dy_, 'W'), 'deco_high'), 'E': ((dx_ + 1, dy_, 'W'), 'deco_low')}[side]
        opts.setdefault(key, {})[which] = kind
    L.tex_names = []
    L.edge_types = [None]          # index 0 = open
    et_index = {}
    edges = np.zeros((MAP_H, MAP_W, 2), np.uint8)    # [y][x][0: west, 1: north]
    L.doors = []
    L.inters = []
    L.edge_info = {}                # (x, y, o) -> kind for collision/LOS

    def tex(name):
        tex_ids[name]          # registers generated textures in the pre-pass
        return name

    def etype(t):
        key = tuple(t)
        if key not in et_index:
            et_index[key] = len(L.edge_types)
            L.edge_types.append(t)
        return et_index[key]

    def sides(x, y, o):
        """(low cell, high cell) of an edge: west/east or north/south."""
        if o == 'W':
            return (x - 1, y), (x, y)
        return (x, y - 1), (x, y)

    for y in range(MAP_H):
        for x in range(MAP_W):
            for oi, o in enumerate('WN'):
                (lx, ly), (hx, hy) = sides(x, y, o)
                lin, hin = inside(lx, ly), inside(hx, hy)
                if not lin and not hin:
                    continue
                ch = edge_char(x, y, o)
                op = opts.get((x, y, o), {})
                lw = room_wall(cell[ly][lx]) if lin else None
                hw = room_wall(cell[hy][hx]) if hin else None
                lw = op.get('tex_low', lw or hw)
                hw = op.get('tex_high', hw or lw)
                if ch == 'x':
                    continue                   # closed exit doors: second pass
                if ch == ' ' and lin and hin and not op:
                    continue
                if ch == ' ' and not (lin and hin):
                    ch = '|' if o == 'W' else '-'
                if ch == ' ' and (lin and hin) and set(op) <= {'deco_low', 'deco_high'}:
                    check(False, name, f"DECOR on the open edge {x},{y},{o}: there is no wall to hang it on")
                if ch in '-|+':
                    tl, th_ = op.get('tex_low', lw), op.get('tex_high', hw)
                    if op.get('deco_low') and lin:
                        tl = f"deco:{tl}:{op['deco_low']}"
                    if op.get('deco_high') and hin:
                        th_ = f"deco:{th_}:{op['deco_high']}"
                    t = (tex(tl), tex(th_), 0, 0, EK_WALL, 0, 0, 0)
                    # walls can carry an interaction too (lift call button, a sign...)
                    for kind_ in ('exit', 'sign', 'event'):
                        if kind_ in op:
                            hi_side = op.get('side', 'high' if hin else 'low') == 'high'
                            normal = {'W': (1, 0) if hi_side else (-1, 0), 'N': (0, 1) if hi_side else (0, -1)}[o]
                            px_ = x + (0.0 if o == 'W' else 0.5) + normal[0] * 0.05
                            py_ = y + (0.5 if o == 'W' else 0.0) + normal[1] * 0.05
                            L.inters.append(dict(x=px_, y=py_, type=kind_, ref=('event' if kind_ != 'sign' else 'sign', op[kind_]),
                                                 normal=normal))
                    edges[y, x, oi] = etype(t)
                    L.edge_info[(x, y, o)] = 'wall'
                elif ch == 'w':
                    a = tex('window:' + lw) if lin else tex(lw)
                    b = tex('window:' + hw) if hin else tex(hw)
                    edges[y, x, oi] = etype((a, b, 0, 0, EK_WALL, 0, 0, 0))
                    L.edge_info[(x, y, o)] = 'wall'
                elif ch in 'aAn':
                    check(lin and hin, name, f"the archway at {x},{y},{o} leads outside the map: an arch needs a room on both sides")
                    kind = 'arch' if ch in 'aA' else 'narrow'
                    g = DOOR_GEOM[kind]
                    a = tex(f'archf:{lw}:{g["panel"]}:{g["lintel"]}')
                    b = tex(f'archf:{hw}:{g["panel"]}:{g["lintel"]}')
                    edges[y, x, oi] = etype((a, b, 0, 0, EK_ARCH, 0, g['panel'], g['lintel']))
                    L.edge_info[(x, y, o)] = ('arch', g['panel'])
                elif ch in 'dDl':
                    check(lin and hin, name, f"the door at {x},{y},{o} leads outside the map: a door needs a room on both sides "
                                             f"(draw a way out as 'x' with exit=)")
                    in_range(op.get('lock', 0), 0, limits.MAX_KEYS - 1, name, f"lock= of the door at {x},{y},{o}")
                    check(ch != 'l' or op.get('lock'), name, f"the door at {x},{y},{o} is drawn 'l' (locked) but EDGES gives it no lock=: "
                                                              f"the letter alone locks nothing")
                    for f_ in op.get('flags', []):
                        check(f_ in DOOR_FLAGS, name, f"the door at {x},{y},{o} has the unknown flag {f_!r} (known: {', '.join(DOOR_FLAGS)})")
                    double = ch == 'D'
                    g = DOOR_GEOM['double' if double else 'single']
                    leaf = op.get('leaf', 'leaf_double' if double else 'leaf_panel')
                    style = LEAF_STYLE.get(leaf, 'wood')
                    # swing into the smaller of the two rooms unless told otherwise
                    swing = op.get('swing')
                    di = len(L.doors)
                    L.doors.append(dict(x=x, y=y, axis=0 if o == 'W' else 1, double=double, leaf=leaf,
                                        lock=op.get('lock', 0), flags=sum(DOOR_FLAGS[f] for f in op.get('flags', [])),
                                        swing=swing, hinge=op.get('hinge'), panel=g['panel'], lintel=g['lintel'],
                                        lw=lw, hw=hw, style=style, name=op.get('name')))
                    L.edge_info[(x, y, o)] = ('door', di)
                    edges[y, x, oi] = 255             # placeholder: separates regions
                else:
                    check(False, name, f"unknown edge character {ch!r} at {x},{y},{o}")
    # exits/signs drawn as closed doors in walls: 'x'
    for y in range(MAP_H):
        for x in range(MAP_W):
            for oi, o in enumerate('WN'):
                if edge_char(x, y, o) != 'x':
                    continue
                (lx, ly), (hx, hy) = sides(x, y, o)
                lin, hin = inside(lx, ly), inside(hx, hy)
                op = opts.get((x, y, o), {})
                lw = room_wall(cell[ly][lx]) if lin else None
                hw = room_wall(cell[hy][hx]) if hin else None
                lw, hw = lw or hw, hw or lw
                leaf = op.get('leaf', 'leaf_panel')
                a = tex(f'dclosed:{lw}:{leaf}:L')
                b = tex(f'dclosed:{hw}:{leaf}:R')
                edges[y, x, oi] = etype((a, b, 0, 0, EK_WALL, 0, 0, 0))
                L.edge_info[(x, y, o)] = 'wall'
                # interactable on the room side
                room_side = (lx, ly) if lin else (hx, hy)
                normal = {'W': (-1, 0) if lin else (1, 0), 'N': (0, -1) if lin else (0, 1)}[o]
                px = x + (0.0 if o == 'W' else 0.5)
                py = y + (0.5 if o == 'W' else 0.0)
                px += normal[0] * 0.05; py += normal[1] * 0.05
                if 'exit' in op:
                    L.inters.append(dict(x=px, y=py, type='exit', ref=('event', op['exit']), normal=normal))
                elif 'sign' in op:
                    L.inters.append(dict(x=px, y=py, type='sign', ref=('sign', op['sign']), normal=normal))
                elif 'event' in op:
                    L.inters.append(dict(x=px, y=py, type='event', ref=('event', op['event']), normal=normal))

    # ---- regions (for door swing defaults)
    region = -np.ones((MAP_H, MAP_W), int)
    sizes = []
    def open_between(ax, ay, bx, by):
        if bx == ax + 1: e = edges[ay, bx, 0]
        elif bx == ax - 1: e = edges[ay, ax, 0]
        elif by == ay + 1: e = edges[by, ax, 1]
        else: e = edges[ay, ax, 1]
        return e == 0
    for y in range(MAP_H):
        for x in range(MAP_W):
            if not inside(x, y) or region[y, x] >= 0:
                continue
            rid = len(sizes); stack = [(x, y)]; region[y, x] = rid; n = 0
            while stack:
                cx, cy = stack.pop(); n += 1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if inside(nx, ny) and region[ny, nx] < 0 and open_between(cx, cy, nx, ny):
                        region[ny, nx] = rid; stack.append((nx, ny))
            sizes.append(n)
    L.region = region

    # ---- doors: hinge/swing, frame and closed-door textures
    for i, d in enumerate(L.doors):
        x, y = d['x'], d['y']
        o = 'W' if d['axis'] == 0 else 'N'
        (lx, ly), (hx, hy) = sides(x, y, o)
        sl = sizes[region[ly, lx]] if inside(lx, ly) else 0
        sh = sizes[region[hy, hx]] if inside(hx, hy) else 0
        swing = d['swing']
        if swing is None:
            swing_hi = sh <= sl            # into the smaller room
        else:
            swing_hi = swing in ('E', 'S')
        hinge_hi = 0 if d['hinge'] in (None, 'L') else 1
        d['hingebits'] = (1 if swing_hi else 0) | (hinge_hi << 1)
        g = DOOR_GEOM['double' if d['double'] else 'single']
        a = tex(f"dframe:{d['lw']}:{d['style']}:{g['panel']}:{g['lintel']}")
        b = tex(f"dframe:{d['hw']}:{d['style']}:{g['panel']}:{g['lintel']}")
        # the closed leaf drawn into the wall: which side of the texture is the hinge?
        def variant(side):
            if d['double']:
                return 'D'
            mirrored = (d['axis'] == 0 and side == 1) or (d['axis'] == 1 and side == 0)
            return 'L' if (hinge_hi == 1) == mirrored else 'R'
        ca = tex(f"dclosed:{d['lw']}:{d['leaf']}:{variant(0)}")
        cb = tex(f"dclosed:{d['hw']}:{d['leaf']}:{variant(1)}")
        et = etype((a, b, ca, cb, EK_DOOR, i, g['panel'], g['lintel']))
        if d['axis'] == 0:
            edges[y, x, 0] = et
        else:
            edges[y, x, 1] = et
        d['edgetype'] = et
        ptex_ids[d['leaf']]
    check(len(L.doors) <= limits.MAX_DOORS, name, f"{len(L.doors)} doors: the most is {limits.MAX_DOORS}")
    check(len(L.edge_types) - 1 <= limits.MAX_EDGE_TYPES, name,
          f"{len(L.edge_types) - 1} different kinds of edge (texture pairs, doors, arches): the most is {limits.MAX_EDGE_TYPES}")
    L.edges = edges
    free_standing_walls(L, name)

    # ---- floors: material per cell
    L.materials = mats
    for f, c in mats:
        flat_ids[f]; flat_ids[c]
    L.cellmat = np.zeros((MAP_H, MAP_W), np.uint8)
    for y in range(MAP_H):
        for x in range(MAP_W):
            if inside(x, y):
                L.cellmat[y, x] = rooms[cell[y][x]].get('mat', 0)

    # ---- props
    L.props = []
    for p in getattr(mod, 'PROPS', []):
        p = dict(p)
        at = f"the prop {p.get('model')!r} at ({p.get('x')}, {p.get('y')})"
        check(p.get('model') in model_ids, name, f"{at}: there is no such model")
        check(isinstance(p.get('x'), (int, float)) and isinstance(p.get('y'), (int, float)) and 0 <= p['x'] < MAP_W and 0 <= p['y'] < MAP_H,
              name, f"{at} is off the map")
        in_range(int(p.get('z', 0)), -32768, 32767, name, f"z= of {at} (1/256 tile)")
        in_range(p.get('light', 0), -128, 127, name, f"light= of {at}")
        in_range(p.get('flags', 0), 0, 255, name, f"flags= of {at}")
        L.props.append(p)
    check(len(L.props) <= limits.MAX_PROPS, name, f"{len(L.props)} props: the most is {limits.MAX_PROPS}")
    L.boxes = []
    for pi, p in enumerate(L.props):
        mdl = models[p['model']] if models else None
        if mdl is None or not mdl.solid:
            continue
        ang = p.get('angle', 0) * 2 * math.pi / 256
        c, s = math.cos(ang), math.sin(ang)
        for (x0, y0, x1, y1) in mdl.boxes:
            pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            wpts = [(p['x'] + px * c - py * s, p['y'] + px * s + py * c) for px, py in pts]
            bx0 = min(q[0] for q in wpts); bx1 = max(q[0] for q in wpts)
            by0 = min(q[1] for q in wpts); by1 = max(q[1] for q in wpts)
            L.boxes.append((bx0, by0, bx1, by1))
    # creature pathing: cells mostly covered by furniture are blocked
    L.blocked = np.zeros((MAP_H, MAP_W), bool)
    for (x0, y0, x1, y1) in L.boxes:
        for y in range(int(y0), int(math.ceil(y1))):
            for x in range(int(x0), int(math.ceil(x1))):
                if not (0 <= x < MAP_W and 0 <= y < MAP_H):
                    continue
                ox = min(x1, x + 1) - max(x0, x); oy = min(y1, y + 1) - max(y0, y)
                if ox > 0.35 and oy > 0.35 and x0 < x + 0.5 < x1 and y0 < y + 0.5 < y1:
                    L.blocked[y, x] = True
                elif ox * oy > 0.45:
                    L.blocked[y, x] = True

    # ---- prop interactables (wardrobes to hide in, machines...)
    for p in L.props:
        if 'inter' not in p:
            continue
        kind, ref = p['inter'][0], (p['inter'][1] if len(p['inter']) > 1 else None)
        ang = p.get('angle', 0) * 2 * math.pi / 256
        fx, fy = -math.sin(ang), math.cos(ang)        # model front (+y) in world
        depth = p.get('front', 0.3)
        L.inters.append(dict(x=p['x'] + fx * depth, y=p['y'] + fy * depth, type=kind,
                             ref=(('event', ref) if kind in ('event', 'fusebox', 'generator') and ref
                                  else ('sign', ref) if kind == 'sign' else None),
                             normal=(fx, fy) if depth >= 0 else (-fx, -fy), prop=L.props.index(p),
                             hide=(p['x'] + fx * 0.05, p['y'] + fy * 0.05, p.get('angle', 0))))

    # ---- things
    L.things = []
    for t in getattr(mod, 'THINGS', []):
        L.things.append(dict(t))
    L.thing_names = {}
    for i, t in enumerate(L.things):
        at = f"the thing {t.get('type')!r} at ({t.get('x')}, {t.get('y')})"
        check(t.get('type') in thing_types, name, f"{at}: there is no such kind of thing")
        check(isinstance(t.get('x'), (int, float)) and isinstance(t.get('y'), (int, float)) and inside(int(t['x']), int(t['y'])),
              name, f"{at} is outside the rooms")
        in_range(t.get('param', 0), 0, 255, name, f"param= of {at}")
        in_range(int(t.get('z', 0) * 256), -32768, 32767, name, f"z= of {at}, in 1/256 tile,")
        check('name' not in t or t['name'] not in L.thing_names, name, f"two things are named {t.get('name')!r}")
        if 'name' in t:
            L.thing_names[t['name']] = i
    check(len(L.things) <= limits.MAX_THINGS, name, f"{len(L.things)} things: the most is {limits.MAX_THINGS}")
    L.door_names = {d['name']: i for i, d in enumerate(L.doors) if d.get('name')}
    L.prop_names = {p['name']: i for i, p in enumerate(L.props) if p.get('name')}
    for nm, (x, y, o) in getattr(mod, 'DOOR_NAMES', {}).items():
        idx = [i for i, d in enumerate(L.doors) if d['x'] == x and d['y'] == y and d['axis'] == (0 if o == 'W' else 1)]
        check(idx, name, f"DOOR_NAMES calls {x},{y},{o} {nm!r}, but there is no door on that edge")
        L.door_names[nm] = idx[0]
    sx, sy, sd = mod.START
    L.start = (sx, sy)
    L.start_angle = DIRS[sd] if isinstance(sd, str) else sd
    check(inside(int(sx), int(sy)), name, f"START ({sx}, {sy}) is outside the rooms")
    L.lights = []
    for lt in getattr(mod, 'LIGHTS', []):
        x, y, inten, radius = lt[:4]
        mode = lt[4] if len(lt) > 4 else 'steady'
        at = f"the light at ({x}, {y})"
        check(not isinstance(mode, str) or mode in LIGHT_MODES, name, f"{at} has the unknown mode {mode!r} (known: {', '.join(LIGHT_MODES)})")
        mode = LIGHT_MODES[mode] if isinstance(mode, str) else mode
        group = lt[5] if len(lt) > 5 else 0
        check(0 <= x < MAP_W and 0 <= y < MAP_H, name, f"{at} is off the map")
        in_range(inten, 0, limits.MAX_LIGHT_LEVEL, name, f"the brightness of {at}")
        check(0 < radius * 16 <= 255, name, f"the radius of {at} is {radius}: it must be over 0 and under 16 tiles")
        in_range(mode, 0, len(LIGHT_MODES) - 1, name, f"the mode of {at}")
        in_range(group, 0, limits.MAX_LIGHT_GROUPS - 1, name, f"the group of {at}")
        L.lights.append((x, y, inten, radius, mode, group))
    L.triggers = [tuple(t) for t in getattr(mod, 'TRIGGERS', [])]
    check(len(L.triggers) <= limits.MAX_TRIGGERS, name, f"{len(L.triggers)} triggers: the most is {limits.MAX_TRIGGERS}")
    for t in L.triggers:
        check(5 <= len(t) <= 7, name, f"the trigger {t!r} must be (x0, y0, x1, y1, event[, once[, flag]])")
        for v, hi, what in zip(t[:4], (MAP_W - 1, MAP_H - 1, MAP_W - 1, MAP_H - 1), ('x0', 'y0', 'x1', 'y1')):
            in_range(v, 0, hi, name, f"{what} of the trigger for {t[4]!r} (cells)")
        check(t[0] <= t[2] and t[1] <= t[3], name, f"the trigger for {t[4]!r} has its corners the wrong way round: {t[:4]}")
        if len(t) > 5:
            in_range(int(t[5]), 0, 1, name, f"once of the trigger for {t[4]!r}")
    L.patrol = []
    for (x, y) in getattr(mod, 'PATROL', []):
        check(isinstance(x, int) and isinstance(y, int) and inside(x, y), name, f"the patrol node ({x}, {y}) is not a cell inside the rooms")
        if L.blocked[y, x]:
            # nudge it to the nearest free cell of the same room
            best = None
            for yy in range(max(0, y - 2), min(MAP_H, y + 3)):
                for xx in range(max(0, x - 2), min(MAP_W, x + 3)):
                    if inside(xx, yy) and not L.blocked[yy, xx] and cell[yy][xx] == cell[y][x]:
                        d = abs(xx - x) + abs(yy - y)
                        if best is None or d < best[0]:
                            best = (d, xx, yy)
            check(best, name, f"the patrol node ({x}, {y}) is under furniture, and so is every cell near it")
            x, y = best[1], best[2]
        L.patrol.append((x, y))
    check(len(L.patrol) <= limits.MAX_PATROL, name, f"{len(L.patrol)} patrol nodes: the most is {limits.MAX_PATROL}")
    check(len(L.inters) <= limits.MAX_INTERS, name, f"{len(L.inters)} things to use (exits, signs, wardrobes, machines): the most is {limits.MAX_INTERS}")
    L.inside = np.array([[inside(x, y) for x in range(MAP_W)] for y in range(MAP_H)])
    L.ambient = getattr(mod, 'AMBIENT_LIGHT', 0)

    # ---- what the map screen draws on each edge
    L.map_kind = {}
    for y in range(H + 1):
        for x in range(W + 1):
            for o in 'WN':
                (lx, ly), (hx, hy) = sides(x, y, o)
                if not inside(lx, ly) and not inside(hx, hy):
                    continue
                ch = edge_char(x, y, o)
                op = opts.get((x, y, o), {})
                info = L.edge_info.get((x, y, o))
                leads = 'exit' in op or 'event' in op
                if ch == 'x':
                    k = 'exit' if leads else 'sealed'
                elif isinstance(info, tuple):
                    k = info[0]                         # 'door' or 'arch'
                elif ch == 'w':
                    k = 'window'
                elif info == 'wall':
                    k = 'exit' if leads else 'wall'
                else:
                    k = 'open'
                L.map_kind[(x, y, o)] = k
    return L


def free_standing_walls(L, name):
    """A straight run of wall that touches nothing at either end is refused:
    seen end on it is thinner than the renderer's four-column ray spacing,
    and the rays either side of it, hitting the same wall behind, would have
    the columns between them filled in from that wall."""
    solid = {k for k, v in L.edge_info.items() if v == 'wall' or isinstance(v, tuple)}

    def at_corner(cx, cy):
        return [e for e in ((cx, cy, 'N'), (cx - 1, cy, 'N'), (cx, cy, 'W'), (cx, cy - 1, 'W')) if e in solid]

    for (x, y, o) in sorted(solid):
        step = (1, 0) if o == 'N' else (0, 1)
        if len(at_corner(x, y)) != 1:
            continue                    # (runs are examined from their low end)
        cx, cy, n = x, y, 0
        while (cx, cy, o) in solid:
            cx, cy, n = cx + step[0], cy + step[1], n + 1
            here = at_corner(cx, cy)
            if len(here) == 1:
                check(False, name, f"the wall (or doorway) from corner {x},{y} to corner {cx},{cy} stands free at both ends: the renderer can lose a wall "
                                   f"that thin when it is seen end on. Join one end to another wall, or use a piece of furniture")
            if len(here) != 2 or (cx, cy, o) not in here:
                break


# ------------------------------------------------------------------ lighting
def make_blockers(L, doors_closed=True):
    """Blocking edges for light: walls, closed doors (arches let light through)."""
    bv = np.zeros((MAP_H, MAP_W + 1), bool)   # west edge of (x, y)
    bh = np.zeros((MAP_H + 1, MAP_W), bool)   # north edge of (x, y)
    for (x, y, o), info in L.edge_info.items():
        block = info == 'wall' or (isinstance(info, tuple) and info[0] == 'door' and doors_closed
                                   and not (L.doors[info[1]]['flags'] & 1))
        if not block:
            continue
        if o == 'W':
            bv[y, x] = True
        else:
            bh[y, x] = True
    return bv, bh


def los(bv, bh, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    mx, my = int(math.floor(x0)), int(math.floor(y0))
    ex, ey = int(math.floor(x1)), int(math.floor(y1))
    stepx = 1 if dx > 0 else -1
    stepy = 1 if dy > 0 else -1
    tdx = abs(1 / dx) if dx else 1e30
    tdy = abs(1 / dy) if dy else 1e30
    tx = ((mx + 1 - x0) if dx > 0 else (x0 - mx)) * tdx
    ty = ((my + 1 - y0) if dy > 0 else (y0 - my)) * tdy
    for _ in range(200):
        if (mx, my) == (ex, ey):
            return True
        if tx < ty:
            bx = mx + 1 if stepx > 0 else mx
            if bv[my, bx]:
                return False
            tx += tdx; mx += stepx
        else:
            by = my + 1 if stepy > 0 else my
            if bh[by, mx]:
                return False
            ty += tdy; my += stepy
        if not (0 <= mx < MAP_W and 0 <= my < MAP_H):
            return False
    return False


def light_contrib(L, bv, bh, lx, ly, inten, radius):
    g = np.zeros((GRID, GRID))
    r = radius
    gx0 = max(0, int((lx - r) * 2)); gx1 = min(GRID, int((lx + r) * 2) + 1)
    gy0 = max(0, int((ly - r) * 2)); gy1 = min(GRID, int((ly + r) * 2) + 1)
    for gy in range(gy0, gy1):
        for gx in range(gx0, gx1):
            cx, cy = (gx + 0.5) / 2, (gy + 0.5) / 2
            if not L.inside[int(cy), int(cx)]:
                continue
            d = math.hypot(cx - lx, cy - ly)
            if d >= r:
                continue
            vis = 0
            for ox, oy in ((0, 0), (0.16, 0.11), (-0.11, -0.16)):
                if los(bv, bh, lx + ox * 0.4, ly + oy * 0.4, cx + ox, cy + oy):
                    vis += 1
            if not vis:
                continue
            t = d / r
            f = (1 - t * t) ** 2
            g[gy, gx] = inten * f * vis / 3
    return g


def bake(L):
    bv, bh = make_blockers(L)
    static = np.zeros((GRID, GRID))
    patches = []
    for (x, y, inten, radius, mode, group) in L.lights:
        c = light_contrib(L, bv, bh, x, y, inten, radius)
        if mode == 0 and group == 0:
            static += c
        else:
            ys, xs = np.nonzero(c > 0.25)
            if len(xs) == 0:
                xs = np.array([int(x * 2)]); ys = np.array([int(y * 2)])
            x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
            patch = np.clip(np.round(c[y0:y1, x0:x1]), 0, 31).astype(np.uint8)
            patches.append(dict(x0=x0, y0=y0, w=x1 - x0, h=y1 - y0, data=patch))
    static += L.ambient
    # soften within each cell's open space (no bleeding through walls)
    s = static.copy()
    blur = s.copy()
    for gy in range(1, GRID - 1):
        for gx in range(1, GRID - 1):
            cx, cy = gx // 2, gy // 2
            if not L.inside[cy, cx]:
                continue
            acc, n = s[gy, gx] * 2, 2
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nx, ny = gx + dx, gy + dy
                if (nx // 2, ny // 2) == (cx, cy) or L.inside[ny // 2, nx // 2]:
                    if (nx // 2, ny // 2) != (cx, cy):
                        # crossing a cell edge: only when no wall between
                        if not los(bv, bh, (gx + 0.5) / 2, (gy + 0.5) / 2, (nx + 0.5) / 2, (ny + 0.5) / 2):
                            continue
                    acc += s[ny, nx]; n += 1
            blur[gy, gx] = acc / n
    light = np.clip(np.round(blur), 0, 31).astype(np.uint8)
    # floor material in bits 5-6
    for gy in range(GRID):
        for gx in range(GRID):
            light[gy, gx] |= (int(L.cellmat[gy // 2, gx // 2]) & 3) << 5
    return light, patches
