"""Original note sequences for Hollowmere (music box lullaby etc.).
Times are in frames (60 Hz). Notes are MIDI numbers."""

BEAT = 50   # 72 bpm


def _place(seq, beat, vol, ev):
    t = 0
    for note, dur in seq:
        if note:
            ev.append((int(round(t)), note, vol))
        t += dur * beat
    return int(round(t))


# "Hollowmere Lullaby" - A minor waltz (3/4), 16 bars
MELODY = [
    (69, 1), (72, 1), (76, 1),
    (74, 2), (72, 1),
    (71, 1), (68, 1), (71, 1),
    (76, 3),
    (69, 1), (72, 1), (76, 1),
    (77, 2), (76, 1),
    (74, 1), (72, 1), (71, 1),
    (69, 3),
    (76, 1), (81, 1), (79, 1),
    (77, 2), (76, 1),
    (74, 1), (77, 1), (76, 1),
    (71, 2), (68, 1),
    (69, 1), (72, 1), (76, 1),
    (75, 2), (76, 1),
    (72, 1), (71, 1), (68, 1),
    (69, 3),
]
BASS = [(57, 3), (50, 3), (52, 3), (52, 3), (57, 3), (53, 3), (50, 2), (52, 1), (57, 3),
        (57, 3), (53, 3), (50, 3), (52, 3), (57, 3), (47, 3), (52, 3), (45, 3)]
# soft accompaniment on beats 2 and 3 of each bar
ACCOMP = [(64, 69), (65, 69), (64, 68), (64, 71), (64, 69), (65, 69), (65, 64), (64, 69),
          (64, 69), (65, 69), (65, 69), (64, 68), (64, 69), (63, 66), (64, 68), (64, 57)]


def lullaby(beat=BEAT):
    ev = []
    total = _place(MELODY, beat, 255, ev)
    _place(BASS, beat, 150, ev)
    for bar, (a, b) in enumerate(ACCOMP):
        ev.append((int(round((bar * 3 + 1) * beat)), a, 80))
        ev.append((int(round((bar * 3 + 2) * beat)), b, 80))
    ev.sort()
    return ev, total


def ending(beat=70):
    """Slower, sparser variant for the ending."""
    ev = []
    _place(MELODY[:18] + [(69, 6)], beat, 220, ev)
    _place([(45, 3), (50, 3), (52, 6), (45, 3), (41, 3), (50, 3), (52, 3), (45, 6)], beat, 130, ev)
    ev.sort()
    return ev, 30 * beat + 4 * beat


def fragment(beat=60):
    """First phrase only, heard faintly from a music box in the ward."""
    ev = []
    total = _place(MELODY[:9], beat, 255, ev)
    ev.sort()
    return ev, total + beat * 3


SEQUENCES = {
    'lullaby': lullaby,
    'ending': ending,
    'fragment': fragment,
}
