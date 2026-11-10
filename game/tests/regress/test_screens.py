# SPDX-License-Identifier: MIT
"""Regression tests: menus, transitions, controls and the HUD."""
import hm
from hm import PL_HIDING, FX_SLITS, SET_CONTROLS, CR_STATE, CR_WAIT, CR_INVESTIGATE, CR_CHASE

WARDROBE = (7.2, 7.8, 0)        # in front of the cupboard under the stairs (chapter I)


def black_rows(im, rows):
    """Pixels that are not black in the given rows."""
    w = im.size[0]
    px = im.tobytes()
    return sum(1 for y in rows for x in range(w) if px[(y * w + x) * 3:(y * w + x) * 3 + 3] != b'\0\0\0')


def test_hiding_does_not_leak_into_menus(t):
    """Hiding in a cupboard, then pausing and quitting to the title: the
    slats and the muffled sound stay behind."""
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + hm.teleport(*WARDROBE) + hm.act(60)
    L += [f"expect8 {{g_player+{PL_HIDING}}} == 1 hidden", f"expect8 {{g_fx+{FX_SLITS}}} != 0 the slats are up",
          "expect16 {g_listenerMuffle} < 256 sound is muffled"]
    L += ["tap START", "run 60", f"expect8 {{g_fx+{FX_SLITS}}} == 0 no slats over the pause menu", "shot {out}/pause.ppm"]
    L += ["tap DOWN", "run 10"] * 4 + ["tap A", "run 200", f"expect8 {{g_fx+{FX_SLITS}}} == 0 no slats over the title", "shot {out}/title.ppm"]
    L += ["tap A", "run 150"] + ["tap A", "run 40"] * 12 + ["run 300"]
    L += [f"expect8 {{g_player+{PL_HIDING}}} == 0 not hidden in the new game", f"expect8 {{g_fx+{FX_SLITS}}} == 0 no slats in the new game",
          "expect16 {g_listenerMuffle} == 256 sound is not muffled in the new game"] + hm.rendering()
    a, b = t.run(L).values()[-2:]
    t.check(b > a, "the new game is not running")


def test_no_garbage_rows_leaving_the_pause_menu(t):
    """Back from the pause menu, the rows around the 3D view stay black from
    the first frame (they hold the renderer's tables)."""
    L = hm.boot() + hm.dismiss() + ["run 900"] + hm.dismiss() + ["tap START", "run 60", "tap A 1"]
    for i in range(24):
        L += ["run 1", f"shot {{out}}/f{i:02d}.ppm"]
    L += ["run 60", "shot {out}/steady.ppm"]
    t.run(L)
    steady = t.image('steady.ppm')
    rows = list(range(0, 10)) + list(range(138, 160))
    base = black_rows(steady, rows)
    for i in range(24):
        n = black_rows(t.image(f"f{i:02d}.ppm"), rows)
        t.check(n <= base, f"frame {i} after Resume: {n} lit pixels outside the view (steady: {base})")


def test_map_opens_with_a_fade(t):
    """Opening the map fades the view out and the map in: no frame of the 3D
    view in the map's colours."""
    L = hm.boot() + hm.dismiss() + ["run 900"] + hm.dismiss() + ["shot {out}/view.ppm", "hold SELECT"]
    for i in range(70):
        L += ["run 1", f"shot {{out}}/m{i:02d}.ppm"]
    L += ["hold -", "run 30", "shot {out}/map.ppm"]
    t.run(L)

    def lum(im):
        return sum(im.convert('L').tobytes())
    seq = [lum(t.image(f"m{i:02d}.ppm")) for i in range(70)]
    low = min(range(70), key=lambda i: seq[i])
    t.check(seq[low] < seq[0] // 20, "the view never fades out before the map")
    for i in range(1, low + 1):
        t.check(seq[i] <= seq[i - 1] * 1.02 + 2000, f"frame {i}: brighter than the one before while fading out ({seq[i - 1]} -> {seq[i]})")
    full = next(i for i in range(low, 70) if seq[i] >= 0.9 * max(seq[low:]))      # (the map's own marker blinks after that)
    for i in range(low + 1, full + 1):
        t.check(seq[i] >= seq[i - 1] * 0.98 - 2000, f"frame {i}: darker than the one before while the map fades in ({seq[i - 1]} -> {seq[i]})")


def test_long_message_shows_both_lines(t):
    """The longest line of the game (the vestry's) is shown whole, on two lines."""
    ev = hm.event_id(3, 'vestry')
    L = hm.boot() + hm.dismiss() + hm.load_level(3) + ["run 600"] + hm.start_event(ev) + ["run 90", "shot {out}/vestry.ppm"]
    t.run(L)
    im = t.image('vestry.ppm')
    first, second = black_rows(im, range(138, 148)), black_rows(im, range(149, 159))
    t.check(first > 150 and second > 150, f"text pixels: {first} on the first line, {second} on the second")


def test_b_in_a_cupboard_with_alternative_controls(t):
    """With the alternative controls B is the flashlight: it does not step
    out of a hiding place."""
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.dismiss() + [f"poke8 {{g_settings+{SET_CONTROLS}}} 1"]
    L += hm.teleport(*WARDROBE) + hm.act(60) + [f"expect8 {{g_player+{PL_HIDING}}} == 1 hidden"]
    L += hm.act(30, 'B') + [f"expect8 {{g_player+{PL_HIDING}}} == 1 still hidden after B"]
    L += hm.act(60) + [f"expect8 {{g_player+{PL_HIDING}}} == 0 out again with A"]
    t.run(L)


def test_running_is_heard(t):
    """Running past a wall she stands behind brings the Sister; walking the
    same way does not."""
    for how, keys, want in (('walk', 'UP', (CR_WAIT,)), ('run', 'UP|B', (CR_INVESTIGATE, CR_CHASE))):
        L = hm.boot() + hm.dismiss() + hm.load_level(1) + ["run 300"] + hm.dismiss() + ["run 600"] + hm.dismiss()
        # in the passage beside the boiler room; she waits two tiles away, behind its wall
        L += hm.teleport(8.5, 3.5, 0) + hm.spawn(2.0, CR_WAIT) + hm.teleport(8.5, 3.5, 90, settle=2)
        L += [f"hold {keys}", "run 25", "hold -", f"peek8 {{g_cr+{CR_STATE}}}"]
        got = t.run(L, name=how).values()[-1]
        t.check(got in want, f"{how}: the Sister's state is {got}, expected {' or '.join(map(str, want))}")


def test_no_rain_over_the_options(t):
    """The title screen's rain (sprites 0..39) is put away while the options
    box is up."""
    L = ["run 100", "tap A", "run 140"] + [f"peek16 {0x07000000 + 8 * i:#x}" for i in range(40)]
    L += ["tap DOWN", "run 10", "tap A", "run 60", "shot {out}/options.ppm"] + [f"peek16 {0x07000000 + 8 * i:#x}" for i in range(40)]
    v = t.run(L).values()
    shown = [sum(1 for a in part if a & 0x300 != 0x200) for part in (v[:40], v[40:80])]
    t.check(shown[0] > 0, "the test found no rain on the title screen")
    t.check(shown[1] == 0, f"{shown[1]} rain drops are drawn over the options")


def test_jumpscare_has_no_miscoloured_frame(t):
    """Being caught: the 3D view, a white flash, then her face. No frame of
    the view in the face's palette."""
    L = hm.boot() + hm.dismiss() + ["run 300"] + hm.spawn(1.0, hm.CR_CHASE, settle=0) + ["run 100"]
    for i in range(90):
        L += ["run 1", f"shot {{out}}/j{i:02d}.ppm"]
    t.run(L)
    frames = [t.image(f"j{i:02d}.ppm") for i in range(90)]
    lum = [sum(f.convert('L').tobytes()) // (240 * 160) for f in frames]
    k = next((i for i, v in enumerate(lum) if v >= 150), None)
    t.check(k is not None and k >= 20, f"no jumpscare found in the frames taken (first bright frame: {k})")
    usual = set()
    for f in frames[max(0, k - 45):k - 6]:
        usual |= {c for _, c in f.getcolors(70000)}
    for i in range(k - 5, k):
        cols = frames[i].getcolors(70000)
        if len(cols) == 1:
            continue                                    # the flash
        known = sum(n for n, c in cols if c in usual)
        t.check(known >= 240 * 160 * 0.85, f"frame {i - k} before her face: only {known * 100 // 38400}% of it in the view's own colours")


def test_shake_and_roll_stay_inside_the_view(t):
    """A strong shake, the walking bob and the roll of the death scene never
    bring the rows beyond the 3D view (the renderer's tables) on screen."""
    ROW0, ROW1, VIS0, VIS1 = 10, 138, 18, 134               # engine.h
    probe = ["peek8 {s_fx3d}", "peek8 {s_fx3d+1}"] + [f"peeks32 {{s_refY+{4 * n}}}" for n in (0, 1)] + \
            [f"peek16 {{s_m+{8 * n + 2 * k}}}" for n in (0, 1) for k in (2, 3)]
    L = hm.boot() + hm.dismiss() + ["run 300", "poke32 {g_shakeAmt} 5", "poke32 {g_shakeT} 100000", "hold UP"]
    for _ in range(60):
        L += ["run 1"] + probe
    L += ["hold -"] + hm.spawn(1.0, hm.CR_CHASE, settle=0)
    for _ in range(120):
        L += ["run 1"] + probe
    v = t.run(L).values()
    seen3d = 0
    for i in range(0, len(v), 8):
        d3, ref, m = v[i:i + 2], v[i + 2:i + 4], v[i + 4:i + 8]
        for n in (0, 1):
            if not d3[n]:
                continue
            seen3d += 1
            pc, pd = ((x ^ 0x8000) - 0x8000 for x in m[2 * n:2 * n + 2])
            rows = [(ref[n] + pc * sx + pd * sy) >> 8 for sx in (0, 239) for sy in (VIS0, VIS1 - 1)]
            t.check(ROW0 <= min(rows) and max(rows) < ROW1, f"frame {i // 8}: the screen shows view rows {min(rows)}..{max(rows)} (drawn: {ROW0}..{ROW1 - 1})")
    t.check(seen3d > 200, "the test did not see the 3D view")


def test_detail_level_after_a_fade(t):
    """The fade into a level, the fade back from the map and a visit to the
    pause menu leave the detail governor where the scene's own cost puts it,
    not at the bottom (it used to count the wait for the screen as work)."""
    def watch(frames, step=10):
        L = []
        for _ in range(frames // step):
            L += [f"run {step}", "peek8 {g_quality}"]
        return L
    L = hm.boot()                                          # ends on the fade into chapter I
    L += watch(120) + ["run 600", "echo steady", "peek8 {g_quality}"]
    L += ["hold SELECT", "run 50", "hold -", "run 30", "tap B", "run 60", "echo map"] + watch(60)
    L += ["tap START", "run 60", "tap A", "run 20", "echo pause"] + watch(60)
    r = t.run(L)
    parts = dict(r.sections())
    start = r.values()[:12]
    steady = parts['steady'][0]
    t.check(max(start[6:]) <= steady + 1, f"detail level over the first two seconds: {start}; the scene settles at {steady}")
    t.check(max(parts['map']) <= steady + 1, f"detail level after closing the map: {parts['map']}; the scene settles at {steady}")
    t.check(max(parts['pause']) <= steady + 1, f"detail level after the pause menu: {parts['pause']}; the scene settles at {steady}")
