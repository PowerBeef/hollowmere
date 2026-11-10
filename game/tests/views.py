# SPDX-License-Identifier: MIT
"""Hollowmere's benchmark views: (level, name, x, y, degrees). bench.py,
fps.py, stackcheck.py and abshot.py measure and photograph the game from
these spots."""
VIEWS = [
    (0, 'hall', 6.30, 10.20, 285), (0, 'stairs', 5.6, 8.9, 10), (0, 'drawing', 3.60, 5.30, 140),
    (0, 'dining', 9.40, 9.60, 320), (0, 'library', 3.60, 3.60, 225), (0, 'kitchen', 7.6, 3.4, 300),
    (0, 'corridor', 0.5, 4.5, 0),
    (1, 'passage', 7.5, 2.6, 90), (1, 'generator', 9.5, 8.6, 320),
    (2, 'ward', 4.5, 3.6, 270), (2, 'nursery', 3.6, 5.4, 135), (2, 'study', 12.6, 8.6, 290),
    (3, 'chapel', 10.9, 7.6, 270), (3, 'boxroom', 4.3, 1.2, 190),
]
# fps.py fails below this at any of them
MIN_FPS = 19.0
