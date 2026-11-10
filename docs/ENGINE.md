# Hollowmere Engine — architecture

This is a tour of the runtime in `engine/src`, the parts that make a first-person 3D world run on a Game Boy Advance: a 16.78 MHz ARM7TDMI with 32 KB of fast internal RAM (IWRAM), 256 KB of slower external RAM (EWRAM), 96 KB of video RAM and no 3D hardware at all.

## The frame

The game logic runs at a fixed 60 Hz and the 3D view renders at 20 fps:

```
VBlank IRQ (60 Hz)        mix audio, page flip (when a frame is ready and 3 vblanks have passed),
                          display effects, sprite attributes, key edge capture
main loop (the game's)    engine_frame_start()
                          the game's update, once per elapsed vblank (at most 4 per frame)
                          engine_frame(): game_render() into the back page, the detail governor,
                          then wait for the flip
```

The interrupt handler, the frame's clock and the governor are the engine's (`runtime.c`); the loop itself and what an update does are the game's (see [The game interface](#the-game-interface)).

A frame has a budget of **842,688 cycles** (3 vblanks). `engine_frame()` measures every frame with two cascaded timers, from `engine_frame_start()` to the end of the render, interrupts included, and the **detail governor** steps through eight detail levels: first the far floor gets coarser, then far furniture and far walls drop to one sample per column pair, small far faces drop out sooner, and finally the sides of the view outside a central band go to half resolution. It falls one level the moment a frame comes close to the deadline and climbs back after a run of comfortable frames, waiting longer each time a climb fails, and not at all while the camera stands where the last climb failed. A frame whose update drew a line of HUD text is not counted; a new scene (`engine_frame_reset()`) starts from full detail. Near things always keep full detail.

Work that would cost a frame several is spread out: the flashlight's light tables are kept per power step and only copied when the light is switched, a line of HUD text is drawn one line per logic tick, and games are expected to do the same with their own heavy steps (Hollowmere builds its enemy's path field 32 cells a tick, `engine/src/flow.h`).

Not every view holds 20 fps. Over the 3,396 places and headings the frame-rate sweep samples in Hollowmere (`sweep.py --fps --every 6`), 62 are below 19.5 fps and 17 of those stay at 15 fps at the lowest detail level: close views of the hall staircase and of the chapel's pews, where the furniture covers the screen several times over. Three quarters of the views run at full detail. And every figure in this repository was timed in the mGBA emulator: **nothing has been run on a console**, which may read video memory more slowly than mGBA models it.

## Display

The view uses **mode 4**: 240×160, 8 bits per pixel with a 256-colour palette, two pages flipped in VBlank. The 3D view occupies rows 10–137 of each page; window registers draw cinema bars over the margins (head bob and shake move the image inside them), and the rows the bars hide are reused as fast memory (below).

`fx.c` / `fxprep.c` drive the hardware effects every frame from one description (`g_fx`): BG2's affine matrix for head bob, shake, roll and zoom; an HDMA table for wave distortion; window 0 as an elliptical vignette or the slats of a wardrobe door when hiding; window 1 for the cinema bars; brightness fades to black or white; mosaic.

## The world renderer (`render.iwram.c`, `rasm.s`)

The world is a 32×32 grid of cells, and **walls live on cell edges** (each cell has a west and a north edge). A wall can be solid, a window, an arch or a doorway with a lintel, so rooms share thin walls the way real buildings do and you can see from one room into the next. Rooms are two tiles tall (a tile is 1.5 m) and the eye is at one tile.

A frame:

1. **Occluder pre-pass** — big opaque furniture faces mark the rows they will cover in each column, so the walls behind them are not drawn at all.
2. **Cast 240 rays**, one per column, stepping edge to edge. Each ray records the first solid wall plus every see-through edge on the way (doorway lintels, arch tops), and the per-column depth buffer, lintel clip rows and per-8-column min/max depths that the object renderer uses for occlusion.
3. **Floors and ceilings** in row pairs, per-room materials, the far floor optionally at quarter resolution.
4. **Walls and lintels**: perspective-correct vertical texture runs, two columns at a time. Wall textures (64×128 with 32×64, 16×32 and 8×16 mips) are stored in seven layouts in ROM — column order, column pairs at both alignments, and column quads at all four alignments — so the hand-written fillers fetch two or four texels in one read.
5. **Objects** far to near (next section).

Lighting is done by **colormaps**: 32 light levels × 256 colours, applied per texel. The light at a point comes from a 64×64 light grid (static light baked by the level compiler, plus dynamic lights that flicker, buzz, pulse or burn like candles and can be switched in groups by scripts) and from the **flashlight**, whose beam is precomputed per screen column "cone" and per distance.

## 3D objects (`objects.c`, `objects.iwram.c`, `propasm.s`)

Furniture, door leaves and props are **textured polygon meshes** (up to 128 vertices and 64 faces each) built offline by `engine/tools/meshkit.py`. Per prop:

- cull by distance, frustum and the walls' depth buffer;
- transform only the vertices that front-facing faces use, projecting with a reciprocal table (no divisions);
- back-face cull against precomputed planes, drop faces too small to see at this distance (per-face LOD), and swap in a simpler far model where one exists;
- sort the faces far to near and fill them. A face marked always-drawn (lod 255: posts, rails) is never dropped.

A model over 128 vertices or 64 faces would draw nothing, so the asset build refuses it. Edge slopes are computed with a 2^44 reciprocal (`edge_rcp`) so that an edge clipped at the near plane lands within one row; the camera's angle and each column's ray share one 4,096-step table, which keeps prop edges within a quarter column of the walls they stand against.

Three fill paths share the wall fillers' column-pair machinery:

| Face | How it is drawn |
|---|---|
| wall-like (two vertical edges: box sides, legs, panels) | a trapezoid with depth, 1/z and u/z stepped across columns, each column a perspective-correct texture run — exactly like a wall |
| any other convex polygon | upper and lower outlines walked into per-column edge buffers, then each column interpolated; perspective-correct edges when the depth range is large |
| wide faces clear of the walls | rows, with exact u,v along each row |

Every column is tested against the wall depth and the lintel clip rows, so furniture disappears correctly behind door frames and through arches. Faces that span a wall in depth (a staircase seen end-on) are culled column by column.

**Sprites** (items, decor and an enemy) are depth-sorted together with the props; one that stands on a prop (a note on a table) is drawn after it. The Sister is pre-rendered offline from a 3D rig: 8 viewing angles, walk and chase cycles of 8 phases, idle, search, kneel and attack frames, each at four sizes so her texels stay about one per pixel.

## Memory

| Where | What |
|---|---|
| IWRAM (32 KB) | every per-pixel routine (ARM code), the mixer, their variables, the stack. Only the `.bss` of `*.iwram.c` files is placed here; everything else's variables go to EWRAM. The linker script asserts that 1,280 bytes are left for the stack (deepest use measured: about 1,000) |
| VRAM, hidden rows | the depth buffer, colormaps, lintel clips, per-column tables, projected vertices — the bars hide rows of both pages, so the renderer keeps its tables there and reads them as fast as IWRAM (see `gba.ld`) |
| EWRAM (256 KB) | level state, props, sprites, light grids, script threads, the 2D canvas |
| ROM | textures in their seven layouts, models, sprites, sounds, levels, text |

The ROM is spent on speed: about 10 MB of the 14.8 MB cartridge is pre-arranged wall texture data.

The renderer's tables in video memory are placed by hand in `gba.ld`. The script is run through the C preprocessor with `limits.h`, and asserts that each table still fits when a limit (vertices per model, voices, view width) is raised.

## Audio (`audio.c`, `audio.iwram.c`, `mix.s`)

A software mixer on both Direct Sound channels (left and right) at 13,379 Hz, mixing one 224-sample buffer per VBlank with an ARM inner loop in IWRAM. Voices carry volume, pan, pitch and priority; **positional sounds** take a world position and are panned and attenuated from the listener every frame (full volume within a tile, silent beyond 20). A small **note sequencer** plays the music-box and piano pieces. A voice the limiter has scaled to silence still plays on and ends in its time. All samples are 8-bit signed PCM generated by the game's `content/sounds.py` with `engine/tools/synth.py`.

## World and scripting (`world.c`, `script.c`)

`world.c` loads a level (generated by `engine/tools/levelc.py`): edges and edge types, doors (single, double, locked, scripted; their leaves swing as real 3D props), collision boxes, items, interactions (signs, lockers, events), lights and triggers. It provides movement with wall and furniture collision, line of sight and the dynamic light grid.

Levels are driven by **event scripts**: a bytecode VM with 8 concurrent threads. Events are started by the game: from triggers (walking into a cell rectangle, optionally gated by a flag), item pickups, interactions, or by other scripts. Operations cover waiting, sounds (positional or not), subtitles and objectives, doors, lights, flags and branches, giving items, checkpoints, music and ambience, showing items and props, and a handful the engine passes to the game (`game_script()`): the enemy, ending the level, fear, teleporting and freezing the player. Scripts are written as Python lists in each level file and compiled by `engine/tools/scriptc.py`; [Making a game](MAKING_A_GAME.md) lists every operation. A checkpoint keeps the threads in flight (`script_save` / `script_load`), so a restored game goes on from the step each event had reached.

## Interface

- **HUD** (`hud.c`): objective, subtitles and prompts rendered into 4bpp sprite tiles with an outline, so text costs nothing on the 3D view; a battery gauge.
- **2D canvas** (`gfx.c`): text with a proportional pixel font, paper and frames for notes and menus, LZ77 full-screen images.
- **Map data**: each level carries its rooms, edge kinds and names (`MapDef`), for a game to draw a map screen from. Hollowmere's is `game/src/map.c`.
- **Saves** (`save.c`): battery-backed SRAM. Eight bytes of settings under the game's tag, then two slots of 256 bytes, each a whole `SaveState` with the game's magic, the layout version, a sequence number and a checksum. A checkpoint is written to the slot that does not hold the newest good state, so a write cut short by the power switch leaves the one before it intact. A slot is loaded only if its magic, version and checksum are right **and** the game finds every index and range in it usable (`game_state_valid`); a game can also carry over a save of an older version of itself (`game_save_import`).

## The game interface

The engine includes no header of a game: `engine/src/game_api.h` is the whole agreement, and the Makefile compiles the engine's files without the game's folder on the include path. It declares

- the state of a playthrough (`SaveState g_state`, `Thing g_things[]`) that scripts, doors and the save work on;
- what the engine offers beyond drawing and sound: the frame loop (`engine_init`, `engine_frame_start`, `engine_ticks`, `engine_frame`), scripts, the battery save;
- nine hooks a game defines: its identity (`game_info`), `game_render`, its strings and messages, its checkpoint, the validity of a save, and `game_script` for the script operations whose meaning is the game's.

`examples/minimal/src/main.c` implements all of it in 180 lines. Hollowmere's side is `game/src`: `main.c` (the state machine and play loop), `game.c` (the hooks, level state, checkpoints, fear), `player.c` (movement, flashlight, stamina, interaction, hiding), `creature.c` (the Night Sister's perception, flow-field pathfinding and behaviour), `map.c` (the map screen) and `ui.c` (title, menus, notes, journal, options, death and ending screens). See [Making a game](MAKING_A_GAME.md).

## Limits

`engine/src/limits.h` is the one table of the engine's limits: cells, doors, props, things, events, threads, flags, model sizes, texture sizes. The C code includes it, the asset tools read it and refuse content over a limit by name (`engine/tools/limits.py`; `contentcheck.py` proves each refusal), the generated data repeats the counts as static asserts, and the linker script takes its table sizes from it.
