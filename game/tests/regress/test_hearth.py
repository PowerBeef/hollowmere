# SPDX-License-Identifier: MIT
"""Regression tests: the hearths. Fires the player lights with matches and
puts out, and the Night Sister comes to and kneels to until they are cold."""
import os
import re

import paths
import hm

GRID = 0x02000000           # g_lightgrid: 64 x 64 half-tile cells, light in the low five bits
GROUPS = dict(drawing=12, dining=13, study=14)       # the ground floor's hearths (game/content/levels/l1_ground.py)


def ids():
    text = open(os.path.join(paths.GEN, 'assets.h')).read()
    return {m.group(1): int(m.group(2)) for m in re.finditer(r'#define (PT_FIRE_\w+|CRF_\w+|CR_NFRAMES) (\d+)', text)}


def state(group):
    return f"peek8 {{g_state+{hm.LIGHT_LEVEL + group}}}"


def hearths():
    """Peeks: prop, group, glow of each of the four entries of g_hearths."""
    L = []
    for i in range(4):
        b = i * hm.HEARTH_SIZE
        L += [f"peek8 {{g_hearths+{b + hm.H_PROP}}}", f"peek8 {{g_hearths+{b + hm.H_GROUP}}}", f"peek16 {{g_hearths+{b + hm.H_GLOW}}}"]
    return L


def test_a_fire_is_lit_with_matches_and_put_out(t):
    """A hearth is laid and cold until the player lights it; that takes the
    matches from the kitchen stove. Lit, its fireplace shows flames and its
    light fills the room; put out by the player, it is laid again."""
    P = ids()
    cell = GRID + 15 * 64 + 3                   # the light cell a tile and a half into the room from the drawing-room hearth
    look = [state(GROUPS['drawing']), f"peek8 {cell:#x}"] + hearths()
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss()
    L += hm.teleport(0.95, 7.5, 180, settle=30) + ["tap A", "run 60", "echo nomatch"] + look
    L += hm.teleport(9.95, 1.0, 270, settle=30) + ["tap A", "run 30", "echo took", f"peek16 {{g_state+{hm.KEYS}}}"]
    L += hm.teleport(0.95, 7.5, 180, settle=30) + ["tap A", "run 90", "echo lit"] + look
    for k in range(12):
        L += ["run 5", f"echo tex{k}", "peek32 {g_numHearths}"]         # (the pictures of the fire: read below, once the prop is known)
    L += ["tap A", "run 150", "echo out"] + look + ["tap A", "run 90", "echo again"] + look
    r = t.run(L)
    S = dict(r.sections())

    def one(v):
        st, light = v[0], v[1] & 31
        hs = [v[2 + 3 * i:5 + 3 * i] for i in range(4)]
        prop, _, glow = next(h for h in hs if h[1] == GROUPS['drawing'])
        return st, light, prop, glow
    st0, dark, prop, glow0 = one(S['nomatch'])
    t.check(st0 == hm.HS_LAID and glow0 == 0, f"with no matches the hearth is in state {st0}, glowing {glow0} (expected laid, 0)")
    t.check(S['took'][0] >> hm.KEY_MATCHES & 1, "the matches on the stove were not taken")
    st1, lit, _, glow1 = one(S['lit'])
    t.check(st1 == hm.HS_BURNING and glow1 == 256, f"lit, the hearth is in state {st1}, glowing {glow1} (expected burning, 256)")
    t.check(lit >= dark + 10, f"the room is no brighter for its fire: light {dark} before, {lit} with it")
    st2, after, _, glow2 = one(S['out'])
    t.check(st2 == hm.HS_LAID and glow2 == 0, f"put out, the hearth is in state {st2}, glowing {glow2} (expected laid again, 0)")
    t.check(after <= dark + 1, f"the fire is out and the room is still lit by it: light {after} (it was {dark})")
    t.check(one(S['again'])[0] == hm.HS_BURNING, "a fire the player put out cannot be lit again")
    # its pictures: flames while it burns, more than one of them
    tex = f"peek8 {{g_props+{prop * hm.PROP_SIZE + hm.PROP_TEX}}}"
    L2 = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + [f"poke16 {{g_state+{hm.KEYS}}} {1 << hm.KEY_MATCHES}"]
    L2 += hm.teleport(0.95, 7.5, 180, settle=30) + ["echo cold", tex, "tap A", "run 90", "echo flames"]
    for k in range(20):
        L2 += ["run 5", tex]
    S2 = dict(t.run(L2).sections())
    flames = {P['PT_FIRE_A'], P['PT_FIRE_B'], P['PT_FIRE_C']}
    t.check(S2['cold'] == [P['PT_FIRE_COLD']], f"cold, the fireplace shows texture {S2['cold']} (expected the laid logs, {P['PT_FIRE_COLD']})")
    t.check(set(S2['flames']) <= flames and len(set(S2['flames'])) >= 2, f"burning, the fireplace shows textures {sorted(set(S2['flames']))} (expected two or three of {sorted(flames)})")


def test_she_kneels_to_a_fire_until_it_is_cold(t):
    """A fire brings the Night Sister when she is away, and she goes to it:
    she kneels (the pictures of rising from prayer, backwards), the fire dies
    under her, she gets up and searches the room. What she has put out cannot
    be lit again."""
    P = ids()
    g = 12                                      # the west ward's hearth (game/content/levels/l3_upper.py)
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.load_level(2) + ["tap SELECT 3", "run 10"]      # (in the linen room, in the dark)
    L += [f"poke8 {{g_state+{hm.LIGHT_LEVEL + g}}} {hm.HS_BURNING}", "echo watch"]
    for _ in range(300):
        L += ["run 6", "peek8 {g_cr}", f"peek16 {{g_cr+{hm.CR_TENDT}}}", "peek16 {g_crFrame}", state(g)]
    L += hm.dismiss() + [f"poke16 {{g_state+{hm.KEYS}}} {1 << hm.KEY_MATCHES}"] + hm.teleport(5.05, 2.7, 0, settle=30) + ["tap A", "run 60", "echo relight", state(g)]
    S = dict(t.run(L).sections())
    v = S['watch']
    rows = [v[i:i + 4] for i in range(0, len(v), 4)]
    states = [r[0] for r in rows]
    first = next((i for i, s in enumerate(states) if s != hm.CR_OFF), None)
    t.check(first is not None and first <= 80, "eight seconds after the fire was lit she has not come")
    t.check(hm.CR_TEND in states, f"she never went to the fire (her states: {sorted(set(states))})")
    kneel = [r for r in rows if r[0] == hm.CR_TEND and r[1] > 0]
    t.check(len(kneel) > 20, "she went to the fire and did not kneel to it")
    kinds = []
    for _, tt, f, _ in kneel:
        k = 'rise' if P['CRF_RISE'] <= f < P['CRF_DOOR'] else 'kneel' if P['CRF_KNEEL'] <= f < P['CRF_RISE'] else '?'
        if not kinds or kinds[-1] != k:
            kinds.append(k)
    t.check(kinds == ['rise', 'kneel', 'rise'], f"at the fire she is drawn {kinds} (expected down, kneeling, up)")
    down = [(f - P['CRF_RISE']) % 6 for _, tt, f, _ in kneel if tt < 36]
    t.check(down == sorted(down, reverse=True) and down[0] > down[-1], f"going down on her knees plays the pictures {down}")
    last = max(i for i, s in enumerate(states) if s == hm.CR_TEND)
    t.check(rows[last][3] == hm.HS_DEAD, f"she got up from a fire in state {rows[last][3]} (expected dead)")
    t.check(last + 1 < len(states) and states[last + 1] == hm.CR_SEARCH, f"after the fire she is in state {states[last + 1] if last + 1 < len(states) else None} (expected searching)")
    t.check(S['relight'] == [hm.HS_DEAD], f"a fire she put out was lit again (state {S['relight']})")


def test_she_does_not_start_her_rounds_shut_in(t):
    """One of the upper floor's patrol nodes is in the doctor's suite, locked
    until the player finds its key. Coming back on her rounds there, she
    could not leave: no sound and no fire brought her out. She starts only
    where the rest of her rounds can be reached."""
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.load_level(2) + hm.teleport(4.35, 1.65, 32, settle=30) + ["tap SELECT 3", "run 10", "echo spawns"]
    again = [f"poke16 {{g_cr+{hm.CR_COOLDOWN}}} 1", "run 12"]      # (a node too near or in sight is refused: she tries another two seconds later)
    for k in range(14):
        L += [f"run {7 + k}"] + again * 4 + ["peek8 {g_cr}", "peeks32 {g_cr+4}", "peeks32 {g_cr+8}"] + hm.dismiss()
    v = dict(t.run(L).sections())['spawns']
    came = [(v[i + 1] >> 16, v[i + 2] >> 16) for i in range(0, len(v), 3) if v[i] != hm.CR_OFF]
    t.check(len(came) >= 6, f"she came back only {len(came)} times of 14: the test measured little")
    inside = [c for c in came if c[0] >= 9 and c[1] >= 5]
    t.check(not inside, f"she started her rounds in the locked suite {len(inside)} times of {len(came)}, at {sorted(set(inside))}")
