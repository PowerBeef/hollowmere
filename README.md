<div align="center">

<img src="docs/media/title.png" width="720" alt="Hollowmere title screen">

# Hollowmere Engine

**A first-person 3D engine for the Game Boy Advance, and _Hollowmere_, the survival-horror game built on it.**

Full-resolution textured 3D at 20 fps on a 16.78 MHz ARM7, in C and hand-written ARM assembly.

[**Download the game**](https://github.com/PowerBeef/hollowmere/releases/latest) · [Engine architecture](docs/ENGINE.md) · [Making a game](docs/MAKING_A_GAME.md) · [Toolchain & testing](docs/TOOLS.md)

<img src="docs/media/walk.gif" width="720" alt="Walking through the hall of Hollowmere">

</div>

---

## Hollowmere, the flagship game

*Autumn, 1958.* Your brother Thomas was sent to Hollowmere, a private sanatorium on an island in a cold, black lake, for "the water cure". His letters grew shorter, then stopped. One night you row across the lake alone. The house is dark — all but one window, high up under the roof.

Explore the manor floor by floor, piece together what happened from the notes left behind, and keep your light low: **the Night Sister** is drawn to light and noise. Hide in wardrobes, hold still in the dark, and never let her count you.

- Four chapters: the house, the cellars, the wards upstairs and the attic chapel
- An enemy with sight, hearing and memory who patrols, investigates, searches and hunts, finding her way through the house (and its doors) by flow-field pathfinding
- Flashlight with a battery to manage, running that she can hear, hiding places
- Resident Evil-style map screen, journal of collected notes, checkpoints saved to the cartridge
- Every texture, model, sprite, sound and note of music generated procedurally from code

<table>
<tr>
<td><img src="docs/media/sister.png" alt="The Night Sister in the gallery"></td>
<td><img src="docs/media/hall.png" alt="The hall and its staircase"></td>
</tr>
<tr>
<td><img src="docs/media/dining.png" alt="The dining room"></td>
<td><img src="docs/media/library.png" alt="The library"></td>
</tr>
<tr>
<td><img src="docs/media/larder.png" alt="The larder"></td>
<td><img src="docs/media/chapel.png" alt="The attic chapel"></td>
</tr>
<tr>
<td><img src="docs/media/drawing.png" alt="The drawing room"></td>
<td><img src="docs/media/generator.png" alt="The generator room in the cellars"></td>
</tr>
<tr>
<td><img src="docs/media/map.png" alt="The map screen"></td>
<td><img src="docs/media/note.png" alt="Reading a note"></td>
</tr>
</table>

### Play it

Download the zip from the [latest release](https://github.com/PowerBeef/hollowmere/releases/latest) and run the `Hollowmere.gba` inside it in any accurate GBA emulator ([mGBA](https://mgba.io) recommended) or on hardware with a flash cartridge (it saves to SRAM). Best played in the dark, with headphones.

| Button | Action |
|---|---|
| D-pad | Walk / turn |
| L / R | Step sideways |
| A | Open, take, read, hide |
| B (hold) | Run — she hears it |
| SELECT | Flashlight on / off (hold: map) |
| START | Pause, map, journal, options |

An alternative layout (B for the light, R to run, SELECT for the map) is in the options.

---

## The engine

The Hollowmere Engine renders a first-person 3D world into the GBA's 240×160 8-bit bitmap mode, entirely in software, at 20 frames per second in all but its heaviest views. Everything that runs per pixel is ARM code in the 32 KB of fast internal RAM.

**World rendering**
- Thin-wall raycaster: walls sit on the edges of a grid, so rooms share walls the way real buildings do, with doorways, arches, windows and lintels you can see through
- Full horizontal resolution (240 columns), with columns drawn in pairs by hand-written assembly fillers
- Two-tile-tall rooms, textured floors and ceilings with per-room materials, four mip levels per texture
- Wall textures stored in seven layouts (column order, pairs, four quad alignments) so one memory read fetches two or four texels

**Real 3D objects**
- Furniture, door leaves and props are textured polygon meshes, not sprites: projected with reciprocal tables (no divisions), back-face culled, depth-sorted and clipped against the walls and lintels
- Three fill paths: wall-like faces as perspective-correct trapezoids, general convex polygons through per-column edge buffers, and wide faces as exact rows
- Per-face level of detail and far-model swaps, plus an occluder pre-pass so walls hidden behind large furniture are never drawn
- Doors are physical leaves that swing open on their hinges

**Light and atmosphere**
- 32-level colormap lighting with a flashlight cone, a per-cell light grid and scripted dynamic lights (flickering bulbs, candles, a pulsing night-light)
- Hardware effects driven every frame: affine head-bob, shake, roll and zoom; HDMA wave distortion; window-based vignettes and cinema bars; fades and blending
- Billboard sprites for characters and items, the main character pre-rendered from a 3D rig at 8 viewing angles with 4 sizes each

**Systems**
- Stereo software mixer on both Direct Sound channels at 13 kHz with an ARM inner loop, positional 3D sound and a note sequencer
- Level event scripting: a bytecode VM with 8 concurrent threads (doors, lights, sounds, messages, the enemy, cutscenes), compiled from Python; a checkpoint keeps the scripts in flight
- Grid world with collision, line of sight, doors and locks, triggers and pickups
- Sprite-based HUD, map data for an auto-mapping map screen, battery-backed saves in two alternating slots that survive a power cut mid-write
- A detail governor that watches each frame's cycle count and trades far detail for speed before a frame can be missed
- One small interface between engine and game ([`game_api.h`](engine/src/game_api.h)): nine hooks, and a 180-line [example game](examples/minimal) that implements them

**Tricks worth stealing**
- Renderer tables live in the parts of video memory the letterbox hides: the off-screen rows of both frame buffers hold the depth buffer, colormaps and projection scratch, read as fast as internal RAM
- The ROM is spent on speed: about 10 MB of the 14.8 MB cartridge is pre-arranged texture data
- A fixed 842,688-cycle budget per frame (3 vblanks), measured on every frame, interrupts included

**Content pipeline** — the whole game is generated from Python: floor plans written in code, low-poly models built from boxes, prisms and lofts, procedural textures, synthesized sounds and music, and level scripts compiled to bytecode. See [Making a game](docs/MAKING_A_GAME.md).

**Testing** — a headless [mGBA](https://mgba.io)-based harness scripts input, reads and writes memory by symbol, takes screenshots and fails on any bad memory access. On it, `make check` plays the whole game through, runs a regression test for every bug fixed, looks for undrawn pixels from every place the player can stand, boots the game from hostile save files, measures frame rates and stack depth, and proves that the asset tools refuse content the engine cannot handle. See [Toolchain & testing](docs/TOOLS.md).

**Limits, stated** — the engine's limits live in one file that the C code, the tools and the linker script all read, and the frame rate is measured, not promised: most views hold 20 fps, the heaviest fall to 15 (see [the frame](docs/ENGINE.md#the-frame)). All timing is from the mGBA emulator; nothing here has been run on a console.

---

## Repository layout

```
engine/
  src/        the runtime: renderer, 3D objects, lighting, audio, effects, world, scripting VM, HUD, saves,
              the frame loop; game_api.h is its whole interface to a game, limits.h its limits
  tools/      the toolchain: asset compiler, level/mesh/script compilers, checks, benchmarks
  harness/    headless mGBA test runner
game/         Hollowmere
  src/        its code: play loop, game rules, the player, the Night Sister, the map screen, menus
  content/    its content as code: levels, models, textures, sprites, sounds, music, story
  assets/     pre-rendered frames of the Night Sister (slow to regenerate), the title font
  tests/      the playthrough, regression tests, hostile saves, benchmark views
examples/
  minimal/    the smallest game the engine builds: one C file, a room, a door, a key
docs/         architecture, content and tooling guides
```

## Building

You need an ARM GCC toolchain and Python 3 with NumPy, Pillow and SciPy:

```sh
sudo apt install gcc-arm-none-eabi libnewlib-arm-none-eabi     # Debian/Ubuntu
pip install -r requirements.txt
make assets   # generate gen/ from game/content (about two minutes the first time, cached after)
make          # build hollowmere.gba
```

The build is reproducible: with the versions pinned in `requirements.txt` and listed in [docs/TOOLS.md](docs/TOOLS.md), a clean build of v1.1 produces a ROM with SHA-256
`792b0c6cab5545d648aa85ae23b0cacc8f746e633c19ac1f64942c47e005bcde`.

To run the tests as well, install `libmgba-dev` and run `make check` (ten minutes with `python3 engine/tools/check.py --quick` after `make test-rom harness`; an hour in full). To build the example game: `make GAME=examples/minimal assets all`. Re-rendering the Night Sister (`python3 game/content/sister/make.py`) needs Numba (`requirements-optional.txt`). Details in [docs/TOOLS.md](docs/TOOLS.md).

## License

Everything in this repository is released under the [MIT License](LICENSE): the engine, the toolchain, the documentation, and the game itself — Hollowmere's code, levels, story, models, textures, sounds, music and characters, and the screenshots in `docs/media/`. Use the engine for your own GBA games, and take whatever is useful from the game.

The title screen is set in TeX Gyre Bonum, which ships in `game/assets/fonts` under the GUST Font License.

## Credits

Hollowmere and the Hollowmere Engine were directed by [PowerBeef](https://github.com/PowerBeef) and designed, programmed and generated by Claude (Anthropic). The test harness uses [mGBA](https://mgba.io) by endrift and contributors.
