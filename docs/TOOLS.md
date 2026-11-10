# Toolchain & testing

Everything in `engine/tools` is Python 3 and runs from any directory. The tools work on one game at a time: the folder in `$GAME` (default `game/`, Hollowmere), the same variable the Makefile takes. `engine/tools/paths.py` knows where that game's content, generated data, ROMs and ELFs are.

## Requirements

| What | For | Built and tested with |
|---|---|---|
| `arm-none-eabi-gcc` + newlib | the ROM | 13.2.1 |
| Python 3 with NumPy, Pillow and SciPy | the asset build | 3.13, NumPy 2.5.3, Pillow 12.3.0, SciPy 1.18.1 |
| `libmgba` (headers + library) | `make harness`, every test in the emulator | mGBA 0.10.2 |
| Numba | only to re-render the Night Sister (`game/content/sister/make.py`) | 0.68.0 |

On Ubuntu 24.04:

```sh
sudo apt install gcc-arm-none-eabi libnewlib-arm-none-eabi libmgba-dev
pip install -r requirements.txt           # NumPy, Pillow, SciPy at the pinned versions
pip install -r requirements-optional.txt  # Numba, only to regenerate game/assets/sister*.npz
```

**Reproducing the release.** With exactly these versions a clean build gives the release ROM byte for byte: its SHA-256 is in the README and in `game/release.sha256`. Other compiler or library versions build a ROM that plays the same but may differ in bytes (a texture or a sound rounded differently). The GitHub workflow (`.github/workflows/check.yml`) builds from a clean checkout twice and compares the two ROMs, compares a tagged release with the recorded hash, runs the checks below and builds and boots `examples/minimal`.

## Building

```sh
make assets      # engine/tools/build_assets.py: the game's content -> gen/ (cached in build/cache)
make             # the release ROM: hollowmere.gba
make test-rom    # build/dev/hollowmere-dev.gba: the same game with debug commands and profiling counters
make harness     # engine/harness/harness, the headless test runner
make check       # all three, then every check (engine/tools/check.py)
make clean       # objects, ELFs and ROMs (gen/ and the cache stay)

make GAME=examples/minimal assets all     # another game: build/minimal/minimal.gba
make DEFS=-DFACEPROF test-rom             # extra compiler flags; objects rebuild when flags change
```

The release ROM carries none of the test hooks. The tools drive the **test ROM**, which is the same sources compiled with `-DDEV`.

`build_assets.py` generates `gen/assets.h`, `gen/assets.c`, `gen/data.s` and the binary blobs in `gen/bin`. Its cache (`build/cache`) keys every piece on its inputs and on the source of the code that shapes it; the build's last line says how many pieces were built and reused. An entry is written whole and renamed, an unreadable one is rebuilt, and entries unused for 60 days are deleted. Because all textures share one palette, a change that moves the palette re-quantizes nearly everything.

The asset build refuses content the engine cannot handle (a 41st door, a 129th vertex, a wait too long for its field, text the font cannot show) with one line naming the level, event or model. The limits are in `engine/src/limits.h`.

## The test harness

`engine/harness/harness [--lenient] ROM [SCRIPT | -] [SAVEFILE]` runs a ROM in mGBA with no window and no sound device, driven by a script. The optional third argument is the cartridge's save file (read at start, written back at the end). Exit status: 0 the script ran and every expectation held; 1 an expectation failed; 2 a usage, script or file error; 3 the emulator reported errors (a bad memory access, a jump to nowhere), unless `--lenient`. `harness --version` prints the emulator's version.

```
hold UP|A            keys held from now on ("hold -" releases)
run 120              run frames
tap START [N]        hold for N frames (default 2), release, run 2 more
monkey N MASK        N frames of random input from the keys in MASK;  seed N
shot out.ppm         save the screen
snap                 remember the screen
cmp NAME FILE [MAX]  pixels of the 3D view that differ from the snap (prints "CMP NAME count x0 y0 x1 y1")
audio out.wav        record audio ("audio -" stops)
peek8 / peek16 / peek32 / peeks32 ADDR          print memory (peeks32: signed)
poke8 / poke16 / poke32 ADDR VALUE
fill ADDR LEN BYTE   dump ADDR LEN FILE
expect8 / expect16 / expect32 / expects32 ADDR OP VALUE [text]     OP: == != < <= > >=
echo TEXT            frame            regs
```

Scripts may use symbols: `{g_state+12}` is replaced with the address from the test ROM's ELF, by `engine/tools/harness.py` (which every tool uses: `harness.run(lines, outdir)`) or by `sym.py script.in > script.txt` for a script run by hand. `$ROM` and `$ELF` point the tools at another ROM, to compare two builds.

**Debug commands.** A game's test ROM can expose a few variables for the tools to drive. Hollowmere's (`game/src/game.c`, compiled only with `-DDEV`):

| | |
|---|---|
| `g_debugCmd` with `g_debugA..C` | 1 spawn the enemy A/16 tiles ahead in state B; 2 teleport to (A, B) in 1/256 tile, angle C; 3 give keys and fuses; 4 load level A; 5 dismiss the enemy; 6 start script event A; 8 / 9 start and stop the sampling profiler |
| `g_dbgFreeze` | stop the world, so that a frame is repeatable |
| `g_govOff`, `g_lodScale`, `g_floorSplit`... | hold the detail level and set its knobs (the engine's, in any test ROM) |

One command is taken per logic update: leave eight frames between two. `sweep.py`, `fps.py`, `bench.py` and the shot tools need commands 2 and 4 and `g_dbgFreeze`; a game without them (like `examples/minimal`) still gets every other check. `tests/boot.txt` is the harness input from power-on to standing in the first level.

## The checks

`python3 engine/tools/check.py [OUTDIR] [--quick] [--only step,step]` runs every check the repository has and exits 1 if any fails; steps a game has no files for are skipped by name.

| Step | Tool | What must hold |
|---|---|---|
| limits | `contentcheck.py` | the asset tools refuse 47 kinds of bad content, each in its own words, and accept 14 inputs at the limits (run with `python3 -O`, where a check written as `assert` would pass everything) |
| cache | `cachecheck.py` | a truncated cache entry is rebuilt, writes are whole, unused entries are pruned |
| audit | `audit.py [level ...]` | no furniture through walls or in doorways, no door swinging into furniture, no decoration hidden, no item floating or sunk |
| text | `textcheck.py` | every script message and sign fits the HUD as `hud.c` draws it; then the game's `tests/textrules.py` (Hollowmere: notes, intro pages, chapter cards, the map heading) |
| lz77 | `lz77.py` | the packer's output unpacks to its input |
| host | `hostcheck.py` | the engine's pure functions (sort keys, the path queue, fixed-point helpers), compiled for the build machine |
| selftest | `selftest.py OUT` | the harness itself fails when it should: exit 1, 2 and 3 on scripts and ROMs that are wrong on purpose |
| boot | `bootcheck.py OUT` | the release ROM boots, draws frames, survives a minute of random input with no emulator error and carries no test symbol |
| playthrough | `tests/playtest.py OUT [--deaths]` | Hollowmere from power-on to the ending, asserting level, keys and fuses at every stage of the critical path; `--deaths` dies once in every chapter |
| regress | `regress.py OUT [name ...]` | the game's `tests/regress/test_*.py`: one test per bug fixed (Hollowmere: 38) |
| sweep | `sweep.py OUT [--every N] [--level L]` | no pixel of the 3D view is left undrawn, from every place the player can stand: 20,368 views at three detail levels (`--quick`: every 12th) |
| fps | `fps.py OUT [--turn] [--min FPS]` | the game's benchmark views (`tests/views.py`) hold its `MIN_FPS` |
| stack | `stackcheck.py OUT [--min BYTES]` | at least 256 bytes of the main stack are never touched (a canary painted at boot) |
| saves | `tests/savecheck.py OUT` | Hollowmere boots a running game from 43 save files: blank, random, cut off mid-write, checksum-valid but out of range, and a real v1.0 save |

`sweep.py OUT --fps [--min FPS]` measures the frame rate at the same places instead (two seconds a view, governor on). It is not part of `check.py`: Hollowmere does not hold 20 fps everywhere (see [ENGINE.md](ENGINE.md#the-frame)).

All timings come from mGBA's model of the hardware. Nothing in this repository has been run on a console; `fps.py` prints the emulator it timed in.

## Other tools

| Tool | What it does |
|---|---|
| `levelc.py`, `scriptc.py`, `meshkit.py`, `mapkit.py`, `spritekit.py` | level, script and mesh compilers and their helpers |
| `limits.py` | the limits of `engine/src/limits.h` for the tools, and `check()`, the one way they refuse content |
| `palette.py`, `lighttables.py`, `font.py`, `noise.py`, `synth.py`, `lz77.py` | palette and colormaps, flashlight tables, the pixel font, procedural noise, sound synthesis, BIOS-compatible LZ77 |
| `fixheader.py ROM TITLE CODE MAKER` | writes the cartridge header (with the boot logo a console requires) |
| `bench.py OUT [--lod N] [--only a,b]` | cycles per render stage at the benchmark views, with a contact sheet |
| `pcprof.py OUT LEVEL X Y DEG` | a sampling profiler: where the frame's time goes, by function |
| `abshot.py ROM ELF OUT` | deterministic screenshots for A/B comparisons (`ABVIEWS="lv,name,x,y,deg;..."`) |
| `shot.py OUT LEVEL:X:Y:DEG[:name] ...`, `shots.py OUT name x y deg ...` | screenshots from chosen spots; with profile counters |
| `preview_map.py LEVEL OUT.png` | a top-down plan of a level |
| `preview_tex.py OUT.png`, `preview_snd.py OUT.png` | contact sheets of floor textures and of every sound's waveform |

`make test-rom DEFS=-DFACEPROF` adds per-face timing inside the prop drawer (`g_objT`, `g_objF`); it is off by default because the code takes fast RAM the stack would otherwise have.
