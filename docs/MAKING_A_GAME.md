# Making a game with the Hollowmere Engine

A game is two things: its C code in `game/src` (rules, player, enemies, menus) and its content in `game/content`. The content is **code too**: levels, models, textures, sprites, sounds, music and text are all Python that the engine's toolchain turns into C data and binary blobs in `gen/`.

```sh
make assets   # run engine/tools/build_assets.py over game/content -> gen/
make          # compile engine/src + game/src + gen/ into the ROM
```

The asset build caches its expensive steps in `build/cache`, keyed on the source of the generators, so after the first run only what you changed is regenerated.

The examples below come from Hollowmere. Its content is all rights reserved, so write your own rather than copying it.

## The manifest

`game/content/manifest.py` lists the levels in play order. The cartridge title and four-letter game code are set at the top of the `Makefile` (`GAME_TITLE`, `GAME_CODE`).

## Levels

A level is a Python module in `game/content/levels`. A trimmed example:

```python
from mapkit import Plan, on_n, on_s, on_w, on_e, at

NAME = "The Chapel"
FLOOR = "ATTIC"                     # heading on the map screen
AMBIENCE = 'amb_chapel'             # looping sound
START = (0.9, 5.4, 'N')             # player start: x, y in tiles, facing

MATERIALS = [('floor_boards', 'ceil_beams'),      # floor/ceiling pairs, up to 4
             ('floor_carpet', 'ceil_beams')]

ROOMS = {
    'A': dict(name='Stairhead', wall='attic_boards', mat=0),
    'P': dict(name='Chapel', wall='chapel_wall', mat=1),
}

P = Plan(13, 9)                     # cells
P.room('A', 0, 4, 1, 8)             # inclusive cell rectangles
P.room('P', 9, 0, 12, 8)
P.door(9, 4, 'W', 'D')              # double door on the west edge of cell (9, 4)
P.door(12, 2, 'E', 'w')             # a window
MAP = P.render()
```

Walls appear automatically between cells of different rooms and around the outside. Edges take a character: `d` single door, `D` double door, `l` locked door, `a` arch, `n` narrow arch, `w` window, `x` a closed door used as an exit or sign, `' '` open.

**`EDGES`** sets options per edge, keyed by `(x, y, 'N' | 'W')`: `lock=` (key id), `name=` (for scripts), `swing=`, `leaf=` (door model), `flags=['startopen', 'scripted', 'nomonster']`, `exit=` (next level), `sign=` (text shown on A), `event=` (a script), `tex_low=` / `tex_high=` (a different texture on either side of a wall).

**`DECOR`** hangs flat decorations on walls: `(x, y, side, kind)` with kinds such as `portrait`, `mirror`, `sconce`, `crucifix`.

**`PROPS`** places 3D models. `at(model, x, y, facing)` stands one anywhere; `on_n` / `on_s` / `on_w` / `on_e` put it flush against that wall facing into the room. Options: `inter=('locker',)` (a hiding place), `inter=('event', 'name')`, `inter=('sign', "text")`, `z=` (height), `front=` (where the interaction is).

**`THINGS`** are sprites and items: `dict(x=, y=, z=, type='note' | 'key' | 'battery' | 'candles' | ..., param=, event=)`.

**`LIGHTS`**: `(x, y, intensity 0-31, radius in tiles, mode, group)`; modes are `steady`, `flicker`, `buzz`, `pulse` and `candle`, and scripts switch lights by group.

**`TRIGGERS`**: `(x0, y0, x1, y1, 'event')` fires an event when the player enters the cell rectangle; add `once` (default 1) and a condition `'flag'` or `'!flag'` as the sixth and seventh items.

**`PATROL`** lists cells the enemy walks between; `MONSTER_MODE` sets her behaviour on this level.

### Event scripts

`EVENTS` maps names to lists of operations, compiled to bytecode for the engine's VM (8 threads run at once):

```python
EVENTS = {
    'start': [
        ('wait', 40),
        ('msg', "The attic. Somewhere ahead, a woman's voice is counting.", 250),
        ('start', 'counting'),                    # run another event alongside
        ('objective', "Follow the counting voice."),
    ],
    'counting': [
        ('label', 'top'),
        ('if_flag', 'l4_nave', 'stop'),
        ('sound3d', 'whisper', 10, 1, 255),       # sound at cell (10, 1)
        ('wait', 330),
        ('jmp', 'top'),
        ('label', 'stop'),
    ],
    'nave': [
        ('flag', 'l4_nave'),
        ('objective', "Take her lantern. Quietly, and with no light."),
        ('checkpoint',),
    ],
}
```

The operations: `wait`, `sound`, `sound3d`, `msg`, `objective`, `door` (open, close, lock, unlock, slam), `light`, `creature` (spawn, despawn, goto, chase, pray, hear, face, mode), `shake`, `flash`, `flag`, `if_flag` / `ifnot_flag`, `if_key` / `ifnot_key`, `jrand`, `jmp`, `label`, `give`, `checkpoint`, `endlevel`, `fear`, `blackout`, `music`, `musicstop`, `ambience`, `stopsounds`, `thing`, `prop`, `inter`, `fade`, `teleport`, `freeze`, `lookat`, `note`, `chapter`, `hudoff`, `ending`, `start`. The `start` event runs when the level loads and `resume` after a checkpoint is restored.

## Models

`game/content/furniture.py` builds every 3D model with `engine/tools/meshkit.py`. Units are tiles (1.5 m): x and y on the floor (y points south, like the map), z up, the model's front faces +y.

```python
@model('nightstand')
def nightstand():
    m = Mesh('nightstand')
    m.box(-0.2, 0, 0, 0.2, 0.3, 0.42, 'wood_dark', front='drawer_front', skip='bn')
    m.boxes = [(-0.2, 0, 0.2, 0.3)]          # collision, model space
    return m
```

The building blocks: `box`, `wall` (a vertical quad, drawn on the fast path), `vquad` (a vertical quad with sloped top and bottom), `flat` (a horizontal polygon), `slope`, `prism`, `frustum`, `pole`, `loft` (rings into a smooth body), and `merge` to combine meshes. A model may name a simpler `far` model and the distance to switch to it. Keep within 128 vertices and 64 faces. Vertical faces with stacked vertices take the fast trapezoid path, so prefer them for anything wall-like.

## Textures, sprites, sounds, music, text

| File | Contents |
|---|---|
| `walltex.py` | wall textures, 64×128 (one tile wide, two tall), registered with `@tex('name')` |
| `textures.py` | floor and ceiling textures, 64×64 |
| `proptex.py` | model textures, 64×64 |
| `props.py` | item and decor sprites, drawn supersampled with `spritekit` |
| `sounds.py` | sound effects, synthesized with `synth`, registered with `@snd('name', loop=...)` |
| `music.py` | note sequences for the sequencer |
| `story.py` | every string in the game: notes, messages, menus, credits |
| `images.py` | full-screen pictures (title, ending) |
| `sister/` | the offline renderer for the enemy's frames (needs Numba) |

All colours are quantized to one shared 256-colour palette whose dark end is tuned for the colormap lighting, so texture generators work in floating-point RGB and the build handles the rest. Everything uses seeded noise, which keeps the build reproducible.

## Checking your work

```sh
python3 engine/tools/audit.py           # furniture through walls, blocked doorways, floating items...
python3 engine/tools/textcheck.py       # every string fits its box on screen
python3 engine/tools/preview_map.py l1_ground out.png      # top-down plan of a level
```

With the test harness built (`make harness`) you can script whole playthroughs, benchmark views and take screenshots from any camera; see [Toolchain & testing](TOOLS.md).
