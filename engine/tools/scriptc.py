# SPDX-License-Identifier: MIT
"""Compiler for Hollowmere level event scripts -> bytecode (see engine/src/script.c)."""

OPS = ['end', 'wait', 'sound', 'sound3d', 'msg', 'objective', 'door', 'light', 'creature', 'shake',
       'flash', 'flag', 'ifnot_flag', 'if_flag', 'jmp', 'give', 'checkpoint', 'endlevel', 'fear',
       'blackout', 'music', 'musicstop', 'ambience', 'thing', 'ending', 'inter', 'ifnot_key', 'fade',
       'teleport', 'if_fuses_lt', 'prop', 'freeze', 'lookat', 'note', 'start', 'placefuses',
       'stopsounds', 'jrand', 'chapter', 'hudoff', 'if_key']
OPC = {n: i for i, n in enumerate(OPS)}

CREATURE_OPS = {'despawn': 0, 'spawn': 1, 'script': 2, 'goto': 3, 'mode': 4, 'chase': 5, 'pray': 6,
                'hear': 7, 'face': 8}
DOOR_OPS = {'close': 0, 'open': 1, 'lock': 2, 'unlock': 3, 'slam': 4}
GIVE_KINDS = {'key': 0, 'fuse': 1, 'battery': 2, 'takekey': 3}
MUSIC = {'lullaby': 0, 'fragment': 1, 'ending': 2}
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

    def snd(self, n):
        if n not in self.sounds:
            raise KeyError(f"{self.level}: unknown sound {n}")
        return self.sounds[n]

    def flag(self, n):
        if n not in self.flags:
            if len(self.flags) >= 64:
                raise ValueError("too many flags")
            self.flags[n] = len(self.flags)
        return self.flags[n]

    def door(self, n):
        if n not in self.doors:
            raise KeyError(f"{self.level}: unknown door {n}")
        return self.doors[n]

    def thing(self, n):
        if n not in self.things:
            raise KeyError(f"{self.level}: unknown thing {n}")
        return self.things[n]

    def prop(self, n):
        props = getattr(self, 'props', {})
        if n not in props:
            raise KeyError(f"{self.level}: unknown prop {n}")
        return props[n]

    def ev(self, n):
        if n not in self.events:
            raise KeyError(f"{self.level}: unknown event {n}")
        return self.events[n]

    def s(self, text):
        return self.strings.add(text)


def u16(v):
    return [v & 255, (v >> 8) & 255]


def compile_event(actions, ctx):
    code = []
    labels = {}
    fixups = []      # (pos, label)

    def jump(label):
        fixups.append((len(code), label))
        code.extend([0, 0])

    for a in actions:
        op = a[0]
        args = a[1:]
        if op == 'label':
            labels[args[0]] = len(code)
            continue
        if op not in OPC:
            raise KeyError(f"{ctx.level}: unknown op {op}")
        code.append(OPC[op])
        if op == 'wait':
            code += u16(int(args[0]))
        elif op == 'sound':
            code += [ctx.snd(args[0]), args[1] if len(args) > 1 else 200, (args[2] if len(args) > 2 else 0) & 255]
        elif op == 'sound3d':
            code += [ctx.snd(args[0]), args[1], args[2], args[3] if len(args) > 3 else 220]
        elif op == 'msg':
            code += u16(ctx.s(args[0])) + u16(args[1] if len(args) > 1 else 200)
        elif op == 'objective':
            sid = ctx.s(args[0])
            assert sid < 256, f"{ctx.level}: objective string id {sid} does not fit the save's u8"
            code += u16(sid)
        elif op == 'door':
            code += [ctx.door(args[0]), DOOR_OPS[args[1]]]
        elif op == 'light':
            code += [args[0], min(255, args[1])]
        elif op == 'creature':
            c = CREATURE_OPS[args[0]]
            code += [c, args[1] if len(args) > 1 else 0, args[2] if len(args) > 2 else 0]
        elif op == 'shake':
            code += [args[0], args[1]]
        elif op == 'flash':
            code += [args[0]]
        elif op == 'flag':
            code += [ctx.flag(args[0]), args[1] if len(args) > 1 else 1]
        elif op in ('ifnot_flag', 'if_flag'):
            code += [ctx.flag(args[0])]
            jump(args[1])
        elif op == 'jmp':
            jump(args[0])
        elif op == 'give':
            code += [GIVE_KINDS[args[0]], args[1] if len(args) > 1 else 1]
        elif op == 'endlevel':
            code += [args[0]]
        elif op == 'fear':
            code += [args[0]]
        elif op == 'blackout':
            code += u16(args[0])
        elif op == 'music':
            code += [MUSIC[args[0]], args[1] if len(args) > 1 else 200]
        elif op == 'ambience':
            code += [ctx.snd(args[0]) if args[0] else 0, args[1] if len(args) > 1 else 110]
        elif op == 'thing':
            code += [ctx.thing(args[0]), 1 if args[1] else 0]
        elif op == 'inter':
            code += [args[0], args[1]]
        elif op in ('ifnot_key', 'if_key'):
            code += [args[0]]
            jump(args[1])
        elif op == 'fade':
            code += [args[0], args[1]]
        elif op == 'teleport':
            code += [args[0], args[1], DIRS[args[2]] if isinstance(args[2], str) else args[2]]
        elif op == 'if_fuses_lt':
            code += [args[0]]
            jump(args[1])
        elif op == 'prop':
            code += [ctx.prop(args[0]), 1 if args[1] else 0]
        elif op == 'freeze':
            code += [1 if args[0] else 0]
        elif op == 'lookat':
            code += [args[0], args[1]] if args[0] is not None else [255, 255]
        elif op == 'note':
            code += [args[0]]
        elif op == 'start':
            code += [ctx.ev(args[0])]
        elif op == 'jrand':
            code += [args[0]]
            jump(args[1])
        elif op == 'chapter':
            code += u16(ctx.s(args[0]))
        elif op == 'hudoff':
            code += [1 if args[0] else 0]
        elif op in ('end', 'checkpoint', 'musicstop', 'ending', 'placefuses', 'stopsounds'):
            pass
        else:
            raise KeyError(op)
    code.append(OPC['end'])
    for pos, lab in fixups:
        if lab not in labels:
            raise KeyError(f"{ctx.level}: unknown label {lab}")
        code[pos:pos + 2] = u16(labels[lab])
    return bytes(code)
