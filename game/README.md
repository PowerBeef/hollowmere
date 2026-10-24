# Hollowmere

The flagship game of the Hollowmere Engine: a first-person survival-horror game set in a lakeside sanatorium in 1958. See the [main README](../README.md) to play or build it.

| Folder | What is in it |
|---|---|
| `src/` | the game's own C code: `main.c` (state machine, play loop, frame governor), `game.c` (level state, checkpoints, fear), `player.c` (movement, flashlight, stamina, interaction, hiding), `creature.c` (the Night Sister: perception, flow-field pathfinding, behaviour), `ui.c` (title, menus, notes, journal, options, death and ending) |
| `content/` | everything the asset build turns into data: `levels/` (the four chapters, their floor plans and event scripts), `furniture.py` (3D models), `walltex.py` / `textures.py` / `proptex.py` (textures), `props.py` (sprites), `sounds.py` and `music.py`, `story.py` (all text), `images.py` (title and ending pictures), `sister/` (the offline renderer for the Night Sister), `manifest.py` (the level list) |
| `assets/` | the Night Sister's pre-rendered frames (`sister.npz`, `sister_jumpscare.npz`), regenerated with `python3 game/content/sister/make.py` (needs Numba, takes a while) |
| `tests/` | `boot.txt`, the harness input from power-on to the first level |

Hollowmere's code and content are **all rights reserved**; see [LICENSE](LICENSE). The engine around it is MIT-licensed.
