# Toolchain & testing

Everything in `engine/tools` is Python 3 and runs from any directory; `engine/tools/paths.py` knows where the repository, the game (`$GAME`, default `game/`), the ROM and the ELF are.

## Requirements

| What | For | Tested with |
|---|---|---|
| `arm-none-eabi-gcc` + newlib | the ROM | 13.2.1 |
| Python 3, NumPy, Pillow | the asset build | 3.13, NumPy 2.5.3, Pillow 12.3.0 |
| `libmgba` (headers + library) | `make harness`, every test tool | mGBA 0.10.2 |
| SciPy | `preview_snd.py` | 1.18.1 |
| Numba | re-rendering the Night Sister (`game/content/sister/make.py`) | 0.68.0 |

On Debian or Ubuntu:

```sh
sudo apt install gcc-arm-none-eabi libnewlib-arm-none-eabi libmgba-dev python3-numpy python3-pil python3-scipy
pip install numba          # only to regenerate game/assets/sister*.npz
```

With the versions above, a clean build reproduces the release ROM bit for bit (SHA-256 in the README). Other compiler or NumPy versions build a ROM that plays the same but may differ in bytes.

## Building

```sh
make assets    # engine/tools/build_assets.py: game/content -> gen/ (cached in build/cache)
make           # hollowmere.gba
make harness   # engine/harness/harness, the headless test runner
make clean     # objects, ELF and ROM (gen/ and the cache stay)
```

`build_assets.py` generates `gen/assets.h`, `gen/assets.c`, `gen/data.s` and the binary blobs in `gen/bin`. It hashes the source of each generator, so it only redoes what changed. Delete `build/cache` to force a full rebuild.

## The test harness

`engine/harness/harness ROM SCRIPT` runs the ROM in mGBA with no window and no sound device, driven by a script:

```
hold UP|A          hold keys ("hold -" releases)
run 120            run frames
tap START [N]      press for N frames, then release
shot out.ppm       save the screen
audio out.wav      record audio ("audio -" stops)
peek32 0x03001234  print memory     (also peek8, peek16)
poke32 0x03001234 5                 (also poke8, poke16)
echo text
```

Scripts may use symbols: `python3 engine/tools/sym.py script.in > script.txt` replaces `{g_player}` or `{g_state+12}` with addresses from the ELF. The game exposes a few hooks for tests: `g_debugCmd` with `g_debugA..C` (teleport, spawn or dismiss the enemy, load a level, give items), `g_dbgFreeze` (stop the world so a frame is repeatable) and `g_govOff` (hold the detail level). `game/tests/boot.txt` gets from power-on through the title and intro to the first level.

## Tools

| Tool | What it does |
|---|---|
| `build_assets.py` | the asset compiler (see above) |
| `levelc.py`, `scriptc.py`, `meshkit.py`, `mapkit.py`, `spritekit.py` | level, script and mesh compilers and their helpers |
| `palette.py`, `lighttables.py`, `font.py`, `noise.py`, `synth.py`, `lz77.py` | palette and colormaps, flashlight tables, the pixel font, procedural noise, sound synthesis, BIOS-compatible LZ77 |
| `fixheader.py ROM TITLE CODE MAKER` | writes a valid cartridge header |
| `playtest.py OUT` | plays the whole game through its critical path and prints progress per chapter |
| `fps.py OUT [--turn] [--only a,b]` | frame rate at the benchmark views with the governor on (`--turn` sweeps the view) |
| `bench.py OUT [--lod N] [--only a,b]` | cycles per render stage at fixed views, with a contact sheet |
| `stackcheck.py OUT` | the stack's high-water mark during rendering |
| `pcprof.py OUT LEVEL X Y DEG` | a sampling profiler: where the frame's time goes, by function |
| `abshot.py ROM ELF OUT` | deterministic screenshots for A/B comparisons (`ABVIEWS="lv,name,x,y,deg;..."`) |
| `shot.py OUT LEVEL:X:Y:DEG[:name] ...` | screenshots from chosen spots |
| `shots.py OUT name x y deg ...`, `prof.py` | screenshots with profile counters |
| `audit.py [level ...]` | level layout audit: furniture through walls or doorways, doors swinging into furniture, decorations hidden behind furniture, items floating or sunk |
| `textcheck.py` | every string fits on screen |
| `preview_map.py LEVEL OUT.png` | a top-down plan of a level |
| `preview_tex.py OUT.png`, `preview_snd.py OUT.png` | contact sheets of floor textures and of every sound's waveform |

A typical check after a change:

```sh
make assets && make && python3 engine/tools/audit.py && python3 engine/tools/textcheck.py \
  && python3 engine/tools/playtest.py /tmp/pt && python3 engine/tools/fps.py /tmp/fps
```
