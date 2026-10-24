<div align="center">

<img src="docs/media/title.png" width="720" alt="Hollowmere title screen">

# Hollowmere Engine

**A first-person 3D engine for the Game Boy Advance, and _Hollowmere_, the survival-horror game built on it.**

Full-resolution textured 3D at 20 fps on a 16.78 MHz ARM7, in C and hand-written ARM assembly.

[**Download the game (v1.0)**](https://github.com/PowerBeef/hollowmere/releases/latest) · [Engine architecture](docs/ENGINE.md) · [Making a game](docs/MAKING_A_GAME.md) · [Toolchain & testing](docs/TOOLS.md)

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

Grab `Hollowmere.gba` from the [latest release](https://github.com/PowerBeef/hollowmere/releases/latest) and run it in any accurate GBA emulator ([mGBA](https://mgba.io) recommended) or on hardware with a flash cartridge (it saves to SRAM). Best played in the dark, with headphones.

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

The Hollowmere Engine renders a first-person 3D world into the GBA's 240×160 8-bit bitmap mode, entirely in software, at a steady 20 frames per second. Everything that runs per pixel is ARM code in the 32 KB of fast internal RAM.

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
- Level event scripting: a bytecode VM with 8 concurrent threads (doors, lights, sounds, messages, the enemy, cutscenes), compiled from Python
- Grid world with collision, line of sight, doors and locks, triggers and pickups
- Auto-mapping map screen, sprite-based HUD, battery-backed saves
- A detail governor that watches each frame's cycle count and trades far detail for speed before a frame can be missed

**Tricks worth stealing**
- Renderer tables live in the parts of video memory the letterbox hides: the off-screen rows of both frame buffers hold the depth buffer, colormaps and projection scratch, read as fast as internal RAM
- The ROM is spent on speed: about 10 MB of the 14.8 MB cartridge is pre-arranged texture data
- A fixed 842,688-cycle budget per frame (3 vblanks), measured on every frame, interrupts included

**Content pipeline** — the whole game is generated from Python: floor plans written in code, low-poly models built from boxes, prisms and lofts, procedural textures, synthesized sounds and music, and level scripts compiled to bytecode. See [Making a game](docs/MAKING_A_GAME.md).

**Testing** — a headless [mGBA](https://mgba.io)-based harness scripts input, reads and writes memory by symbol and takes screenshots, so the repository can play the whole game through, benchmark frame rates, check stack depth and audit level layouts automatically. See [Toolchain & testing](docs/TOOLS.md).

---

## Repository layout

```
engine/
  src/        the runtime: renderer, 3D objects, lighting, audio, effects, world, scripting VM, HUD, map
  tools/      the toolchain: asset compiler, level/mesh/script compilers, test and benchmark tools
  harness/    headless mGBA test runner
game/
  src/        Hollowmere's own code: main loop, game rules, the player, the Night Sister, menus
  content/    the game's content as code: levels, models, textures, sprites, sounds, music, story
  assets/     pre-rendered frames of the Night Sister (slow to regenerate)
  tests/      harness boot script
docs/         architecture, content and tooling guides
```

## Building

You need an ARM GCC toolchain and Python 3 with NumPy and Pillow:

```sh
sudo apt install gcc-arm-none-eabi libnewlib-arm-none-eabi python3-numpy python3-pil   # Debian/Ubuntu
make assets   # generate gen/ from game/content (about two minutes the first time, cached after)
make          # build hollowmere.gba
```

The build is reproducible: with the toolchain versions listed in [docs/TOOLS.md](docs/TOOLS.md), a clean build of v1.0 produces a ROM with SHA-256
`459e4a058b534e8acd0252b1244248d144a7f1387a6969471903caf80bdc98ae`.

Optional: `make harness` (needs `libmgba-dev`) for the test tools; SciPy for sound previews; Numba to re-render the Night Sister (`python3 game/content/sister/make.py`). Details in [docs/TOOLS.md](docs/TOOLS.md).

## License

- **The engine** — everything outside `game/` (`engine/`, the `Makefile`, the documentation text) — is released under the [MIT License](LICENSE). Use it for your own GBA games.
- **The game** — `game/` (Hollowmere's code, levels, story, models, textures, sounds, music, characters) and the screenshots in `docs/media/` — is **all rights reserved**; see [game/LICENSE](game/LICENSE). You may build and play it from this repository, but not redistribute it or reuse its content.

## Credits

Hollowmere and the Hollowmere Engine were directed by [PowerBeef](https://github.com/PowerBeef) and designed, programmed and generated by Claude (Anthropic). The test harness uses [mGBA](https://mgba.io) by endrift and contributors.
