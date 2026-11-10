# Hollowmere

The flagship game of the Hollowmere Engine: a first-person survival-horror game set in a lakeside sanatorium in 1958. See the [main README](../README.md) to play or build it.

| Folder | What is in it |
|---|---|
| `game.mk` | the ROM's name and its cartridge header |
| `src/` | the game's own C code: `main.c` (state machine, play loop), `game.c` (the engine's hooks, level state, checkpoints, fear), `player.c` (movement, flashlight, stamina, interaction, hiding), `creature.c` (the Night Sister: perception, flow-field pathfinding, behaviour), `map.c` (the map screen), `ui.c` (title, menus, notes, journal, options, death and ending) |
| `content/` | everything the asset build turns into data: `manifest.py` (levels, tunes, the door models, the Sister's sheets), `levels/` (the four chapters, their floor plans and event scripts), `furniture.py` (3D models), `walltex.py` / `textures.py` / `proptex.py` (textures), `props.py` (sprites), `sounds.py` and `music.py`, `story.py` (all text), `images.py` (title and ending pictures), `sister/` (the offline renderer for the Night Sister) |
| `assets/` | the Night Sister's pre-rendered frames (`sister.npz`, `sister_jumpscare.npz`), regenerated with `python3 game/content/sister/make.py` (needs Numba, takes a while), and the title's font |
| `tests/` | `boot.txt` (harness input from power-on to the first level), `playtest.py` (the whole game, start to ending), `regress/` (a test per bug fixed), `savecheck.py` (hostile save files), `textrules.py` (what fits Hollowmere's own screens), `views.py` (benchmark views), `hm.py` (where things are in memory, for the tests) |

Saves written by version 1.0 are recognised: the game continues at the start of the chapter the save had reached, with the notes found so far.

Hollowmere's code and content are released under the [MIT License](../LICENSE), like the engine around it.
