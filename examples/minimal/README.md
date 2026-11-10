# The minimal example

The smallest game the Hollowmere Engine builds: a lit room, a closet behind a door, a key on the closet floor. It exists to show what a game owes the engine and nothing more.

```sh
make GAME=examples/minimal assets all        # -> build/minimal/minimal.gba
```

D-pad walks and turns, L and R step sideways, A opens and closes the door ahead. Walk into the key to take it.

| File | What it shows |
|---|---|
| `game.mk` | the ROM's name and cartridge header |
| `src/main.c` | all of a game's C code in 180 lines: the nine hooks of `engine/src/game_api.h`, loading a level, a player (movement with collision, a door, pickups, triggers) and the frame loop |
| `content/manifest.py` | the level list (the one required entry) |
| `content/levels/room.py` | a floor plan, a door, lights, a thing, a trigger and three event scripts |
| `content/textures.py`, `walltex.py`, `proptex.py` | one floor, one ceiling, one wall, a door leaf; `walltex.ensure()` composes the doorway's textures |
| `content/furniture.py` | the two door-leaf models every game needs |
| `content/props.py` | one sprite, drawn with NumPy |
| `content/sounds.py` | three synthesized sounds |
| `content/story.py` | three strings for the code |
| `tests/boot.txt` | harness input from power-on to the room |

It has no enemy, no menus, no saves, no music and no debug commands, so `GAME=examples/minimal python3 engine/tools/check.py` runs the checks that need none of those (it boots, survives a minute of random input, keeps its stack) and skips the rest by name. [docs/MAKING_A_GAME.md](../../docs/MAKING_A_GAME.md) describes every piece; Hollowmere in `game/` is the full-size example.
