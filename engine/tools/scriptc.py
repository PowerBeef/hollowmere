# SPDX-License-Identifier: MIT
"""Compiler for Hollowmere level event scripts -> bytecode (see engine/src/script.c).

Every value is checked against what its byte (or two) and the engine can
hold; a mistake is a limits.ContentError naming the level and the event."""
import limits
from limits import ContentError, check, in_range

OPS = ['end', 'wait', 'sound', 'sound3d', 'msg', 'objective', 'door', 'light', 'creature', 'shake',
       'flash', 'flag', 'ifnot_flag', 'if_flag', 'jmp', 'give', 'checkpoint', 'endlevel', 'fear',
       'blackout', 'music', 'musicstop', 'ambience', 'thing', 'ending', 'ifnot_key', 'fade',
       'teleport', 'if_fuses_lt', 'prop', 'freeze', 'lookat', 'note', 'start', 'placefuses',
       'stopsounds', 'jrand', 'hudoff', 'if_key']        # (the same list, in the same order, as the enum in engine/src/script.c)
OPC = {n: i for i, n in enumerate(OPS)}

CREATURE_OPS = {'despawn': 0, 'spawn': 1, 'script': 2, 'goto': 3, 'mode': 4, 'chase': 5, 'pray': 6,
                'hear': 7, 'face': 8}
DOOR_OPS = {'close': 0, 'open': 1, 'lock': 2, 'unlock': 3, 'slam': 4}
GIVE_KINDS = {'key': 0, 'fuse': 1, 'battery': 2, 'takekey': 3}
DIRS = {'E': 0, 'S': 1, 'W': 2, 'N': 3}


class StringTable:
    def __init__(self):
        self.items = []
        self.index = {}
        self.names = {}

    def add(self, text, name=None):
        if name is None and text in self.index:
            return self.index[text]
        i = len(self.items)
        self.items.append(text)
        if name is None:
            self.index.setdefault(text, i)
        else:
            self.names[name] = i
        return i


class Ctx:
    def __init__(self, strings, sounds, flags, events, doors, things, level_name):
        self.strings, self.sounds, self.flags = strings, sounds, flags
        self.events, self.doors, self.things = events, doors, things
        self.level = level_name

        self.where = level_name
        self.music = {}         # tune name -> number (the game's manifest)

    def snd(self, n):
        check(n in self.sounds, self.where, f"there is no sound {n!r}")
        return in_range(self.sounds[n], 0, 255, self.where, f"the number of sound {n!r} (a script can only play the first 256)")

    def flag(self, n):
        if n not in self.flags:
            # (the last flag is the game code's own: FLAG_GAME in game.h)
            check(len(self.flags) < limits.NUM_SCRIPT_FLAGS, self.where,
                  f"the flag {n!r} would be number {len(self.flags) + 1}: the scripts of all levels share {limits.NUM_SCRIPT_FLAGS}")
            self.flags[n] = len(self.flags)
        return self.flags[n]

    def door(self, n):
        check(n in self.doors, self.where, f"there is no door named {n!r}")
        return self.doors[n]

    def thing(self, n):
        check(n in self.things, self.where, f"there is no thing named {n!r}")
        return self.things[n]

    def prop(self, n):
        props = getattr(self, 'props', {})
        check(n in props, self.where, f"there is no prop named {n!r}")
        return props[n]

    def ev(self, n):
        check(n in self.events, self.where, f"there is no event {n!r}")
        return self.events[n]

    def s(self, text):
        return self.strings.add(text)


def u16(v):
    return [v & 255, (v >> 8) & 255]


def event_table(ev_src, first, where):
    """(the events of a level in id order, {name: id}): the ones named in
    `first` lead (the engine knows them by number), ids start at 1."""
    order = list(first) + [k for k in ev_src if k not in first]
    check(len(order) <= limits.MAX_EVENTS, where, f"{len(order)} events: the most is {limits.MAX_EVENTS}")
    return order, {nm: i + 1 for i, nm in enumerate(order)}


def compile_event(actions, ctx, name='?'):
    """The bytecode of one event (a list of action tuples)."""
    where = ctx.where = f"{ctx.level}, event '{name}'"
    code = []
    labels = {}
    fixups = []      # (pos, label)

    def jump(label):
        fixups.append((len(code), label))
        code.extend([0, 0])

    for a in actions:
        check(isinstance(a, (tuple, list)) and a and isinstance(a[0], str), where, f"{a!r} is not an action: an action is a tuple like ('wait', 30)")
        try:
            _compile_action(a, ctx, code, labels, jump, where)
        except (IndexError, KeyError, TypeError, AttributeError) as e:
            raise ContentError(f"{where}: the action {a!r} has a missing or mistaken argument ({type(e).__name__}: {e})") from None
    code.append(OPC['end'])
    for pos, lab in fixups:
        check(lab in labels, where, f"a jump to the label {lab!r}, which the event does not have")
        code[pos:pos + 2] = u16(labels[lab])
    for i, b in enumerate(code):
        check(isinstance(b, int) and 0 <= b <= 255, where, f"byte {i} of the compiled event is {b!r} (a value in one of its actions is out of range)")
    check(len(code) <= limits.MAX_EVENT_BYTES, where, f"the event compiles to {len(code)} bytes: the most is {limits.MAX_EVENT_BYTES}")
    return bytes(code)


def _compile_action(a, ctx, code, labels, jump, where):
    def byte(v, what, hi=255):
        return in_range(v, 0, hi, where, f"{what} in {a!r}")

    def word(v, what, hi=65535):
        return u16(in_range(v, 0, hi, where, f"{what} in {a!r}"))

    def cell(v, what):
        return byte(v, what, limits.MAP_W - 1)

    if True:
        op = a[0]
        args = a[1:]
        if op == 'label':
            check(args[0] not in labels, where, f"the label {args[0]!r} is there twice")
            labels[args[0]] = len(code)
            return
        check(op in OPC, where, f"there is no action {op!r} (in {a!r})")
        code.append(OPC[op])
        if op == 'wait':
            code += word(args[0], 'the frames to wait', limits.MAX_WAIT)
        elif op == 'sound':
            code += [ctx.snd(args[0]), byte(args[1] if len(args) > 1 else 200, 'the volume'), in_range(args[2] if len(args) > 2 else 0, -128, 127, where, f'the pitch shift (semitones) in {a!r}') & 255]
        elif op == 'sound3d':
            code += [ctx.snd(args[0]), cell(args[1], 'x'), cell(args[2], 'y'), byte(args[3] if len(args) > 3 else 220, 'the volume')]
        elif op == 'msg':
            code += word(ctx.s(args[0]), 'the string') + word(args[1] if len(args) > 1 else 200, 'the frames it stays')
        elif op == 'objective':
            sid = ctx.s(args[0])
            check(sid <= limits.MAX_OBJECTIVE_STRING, where, f"the objective {args[0]!r} is string number {sid}: objectives must be among the first "
                                                             f"{limits.MAX_OBJECTIVE_STRING + 1} strings (the save keeps the number in a byte)")
            code += u16(sid)
        elif op == 'door':
            check(args[1] in DOOR_OPS, where, f"a door cannot be told to {args[1]!r} (known: {', '.join(DOOR_OPS)})")
            code += [ctx.door(args[0]), DOOR_OPS[args[1]]]
        elif op == 'light':
            code += [byte(args[0], 'the light group', limits.MAX_LIGHT_GROUPS - 1), min(255, in_range(args[1], 0, 256, where, f'the level in {a!r}'))]
        elif op == 'creature':
            check(args[0] in CREATURE_OPS, where, f"the creature cannot be told to {args[0]!r} (known: {', '.join(CREATURE_OPS)})")
            c = CREATURE_OPS[args[0]]
            code += [c, byte(args[1] if len(args) > 1 else 0, 'the first value'), byte(args[2] if len(args) > 2 else 0, 'the second value')]
        elif op == 'shake':
            code += [byte(args[0], 'the strength'), byte(args[1], 'the frames')]
        elif op == 'flash':
            code += [byte(args[0], 'the frames')]
        elif op == 'flag':
            code += [ctx.flag(args[0]), byte(args[1] if len(args) > 1 else 1, 'the value', 1)]
        elif op in ('ifnot_flag', 'if_flag'):
            code += [ctx.flag(args[0])]
            jump(args[1])
        elif op == 'jmp':
            jump(args[0])
        elif op == 'give':
            check(args[0] in GIVE_KINDS, where, f"there is nothing called {args[0]!r} to give (known: {', '.join(GIVE_KINDS)})")
            n = args[1] if len(args) > 1 else 1
            code += [GIVE_KINDS[args[0]], byte(n, 'the key', limits.MAX_KEYS - 1) if args[0] in ('key', 'takekey') else byte(n, 'the amount')]
        elif op == 'endlevel':
            code += [byte(args[0], 'the next level', limits.MAX_LEVELS)]
        elif op == 'fear':
            code += [byte(args[0], 'the fear')]
        elif op == 'blackout':
            code += word(args[0], 'the frames')
        elif op == 'music':
            check(args[0] in ctx.music, where, f"there is no music {args[0]!r} (the manifest's MUSIC has: {', '.join(ctx.music) or 'none'})")
            code += [ctx.music[args[0]], byte(args[1] if len(args) > 1 else 200, 'the volume')]
        elif op == 'ambience':
            code += [ctx.snd(args[0]) if args[0] else 0, byte(args[1] if len(args) > 1 else 110, 'the volume')]
        elif op == 'thing':
            code += [ctx.thing(args[0]), 1 if args[1] else 0]
        elif op in ('ifnot_key', 'if_key'):
            code += [byte(args[0], 'the key', limits.MAX_KEYS - 1)]
            jump(args[1])
        elif op == 'fade':
            code += [byte(args[0], 'the level', 16), byte(args[1], 'the speed')]
        elif op == 'teleport':
            check(not isinstance(args[2], str) or args[2] in DIRS, where, f"{args[2]!r} is not a direction (E, S, W, N) in {a!r}")
            code += [cell(args[0], 'x'), cell(args[1], 'y'), DIRS[args[2]] if isinstance(args[2], str) else byte(args[2], 'the direction', 3)]
        elif op == 'if_fuses_lt':
            code += [byte(args[0], 'the number of fuses')]
            jump(args[1])
        elif op == 'prop':
            code += [ctx.prop(args[0]), 1 if args[1] else 0]
        elif op == 'freeze':
            code += [1 if args[0] else 0]
        elif op == 'lookat':
            code += [cell(args[0], 'x'), cell(args[1], 'y')] if args[0] is not None else [255, 255]
        elif op == 'note':
            code += [byte(args[0], 'the note', limits.MAX_NOTES - 1)]
        elif op == 'start':
            code += [ctx.ev(args[0])]
        elif op == 'jrand':
            code += [byte(args[0], 'the chance (out of 256)')]
            jump(args[1])
        elif op == 'hudoff':
            code += [1 if args[0] else 0]
        elif op in ('end', 'checkpoint', 'musicstop', 'ending', 'placefuses', 'stopsounds'):
            pass
        else:
            check(False, where, f"the compiler has no case for {op!r}")
