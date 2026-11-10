# Making a game with the Hollowmere Engine

A game is a folder with three things in it:

```
mygame/
  game.mk       its name on the cartridge
  src/          its C code: rules, a player, menus. It includes engine/src/game_api.h and nothing else of the engine is off limits
  content/      its levels, models, textures, sprites, sounds and text, as Python the toolchain turns into data
  tests/        boot.txt and whatever tests it has (optional beyond boot.txt)
```

and it is built by the engine's Makefile:

```sh
make GAME=mygame assets     # engine/tools/build_assets.py over mygame/content -> build/mygame/gen/
make GAME=mygame            # engine/src + mygame/src + the generated data -> build/mygame/<TARGET>.gba
make GAME=mygame test-rom   # the same game with the engine's profiling counters, for the test tools
```

`GAME` defaults to `game/`, which is Hollowmere. **Start from `examples/minimal`**: a complete game in one C file and nine short content modules (a room, a closet behind a door, a key). Everything below is what it and Hollowmere are made of. Both are MIT-licensed like the engine: copy freely.

## The C side: `game_api.h`

The engine includes no header of a game. A game includes `engine/src/game_api.h`, which holds

- the **state of a playthrough**, `SaveState g_state`: level, objective, keys, fuses, battery, flags, light groups, door and prop states, the script threads. The script operations work on it; a game that has no use for a field leaves it 0;
- the **frame loop**: `engine_init()`, then per frame `engine_frame_start()`, one `update` per `engine_ticks()` (1/60 s logic steps), `engine_frame()`;
- **scripts** (`script_start`, `script_update`...) and the **battery save** (`save_write`, `save_read`);
- the **hooks** a game must define. The whole list:

| Hook | What the engine wants |
|---|---|
| `const GameInfo game_info` | four characters that mark this game's saves, four for its settings block |
| `void game_render(void)` | draw one frame: set `g_cam`, fill `g_sprites`, call `render_view()` (see the example) |
| `const char *game_str(int id)` | a string of the generated table |
| `void game_message(int str, int frames)` | a script's `('msg', ...)` |
| `void game_set_objective(int str)` | a script's `('objective', ...)` |
| `void game_checkpoint(void)` | a script's `('checkpoint',)` |
| `int game_state_valid(const SaveState *)` | is a state read from the cartridge usable (every index in range)? |
| `int game_save_import(SaveState *)` | is there a save of an older version to carry over? (usually `return 0`) |
| `void game_script(int what, int a, int b, int c)` | script operations whose meaning is the game's: the enemy, ending a level, the ending, fear, teleporting and freezing the player |

`main()` is the game's too. The smallest one:

```c
int main(void) {
    engine_init();
    load_level(0);              // world_load_level(), fill g_things, script_start(L->startEvent)
    for (;;) {
        engine_frame_start();
        for (int n = engine_ticks(); n > 0; n--) update();      // input, world_move(), script_update(), hud_update()...
        engine_frame();         // game_render(), the detail governor, wait for the frame to be shown
    }
}
```

What the engine offers beyond that (collision with `world_move`, line of sight, doors, sound, the HUD, the 2D canvas for menus) is toured in [ENGINE.md](ENGINE.md).

## `game.mk`

```make
TARGET     := mygame        # the ROM's file name
GAME_TITLE := MYGAME        # cartridge header: up to 12 ASCII characters
GAME_CODE  := MYGE          # four letters
MAKER_CODE := 00            # two characters; 00 is homebrew
```

## The content contract

`build_assets.py` imports these modules from `content/` (and level modules from `content/levels/`). The first column is the whole contract: what each must export.

| Module | Must export | Notes |
|---|---|---|
| `manifest.py` | `LEVELS`: level module names in play order | optional entries below |
| `textures.py` | `TEXTURES`: name → function returning a 64×64×3 RGB array (0..1) | floors and ceilings |
| `walltex.py` | `TEXTURES`: name → function returning a 128×64×3 array; `ensure(name)` | `ensure` adds the composites the level compiler names: `dframe:wall:style:panel:lintel` (an open doorway's surround), `dclosed:wall:leaf:L\|R\|D` (the door shut), `archf:wall:panel:lintel`, `window:wall`, `deco:wall:kind` |
| `proptex.py` | `TEXTURES`: name → 64×64×3 | textures of 3D models and door leaves |
| `furniture.py` | `MODELS`: name → function returning a `meshkit.Mesh`; `build_all()` | must include the two door-leaf models |
| `props.py` | `PROPS`: name → `dict(fn, w, h, ww, wh, zoff, solid, fullbright, glint)` | the sprites of `THINGS`; `add_glint()` if any has `glint` |
| `sounds.py` | `SOUNDS`: name → `(function, loops)`; the function returns `(samples in -1..1, loop start or None)` | at least one |
| `story.py` | `string_list()`: `(NAME, text)` pairs, each becoming `STR_NAME` | optional `COUNTS`, `BASES` dicts of extra `#define`s; `late_strings()`: more pairs, numbered after the levels' own strings (text added in a later version: a save holds its objective as a string's number) |
| `music.py` | `SEQUENCES`: name → function returning `(notes, frames)` | optional |
| `images.py` | `IMAGES`, `render()` | optional: full-screen pictures with their own palettes |

Optional manifest entries:

| Entry | Default | Meaning |
|---|---|---|
| `LEVEL_EVENTS` | `('start',)` | events every level has, in this order (ids 1, 2...). The engine's `LevelDef.startEvent` is the first; the game's code can start the others by number |
| `MUSIC` | `[]` | tunes a script can start: `(name in music.SEQUENCES, instrument sound, loops)` |
| `DOOR_MODELS` | `dict(single='leaf_single', half='leaf_half')` | the models hung in single doors and in each half of double doors |
| `ENEMY_SHEETS` | `None` | `dict(file=, palette_frames=[...])`: pre-rendered sprite sheets in `assets/`, emitted as `creature_frames[4][CR_NFRAMES]` |

All colours are quantized to one shared 256-colour palette whose dark end is tuned for the colormap lighting, so generators work in floating-point RGB and the build handles the rest. Use seeded random numbers: the build is then reproducible.

The asset build caches its expensive steps in `build/cache`. A piece is rebuilt when its inputs or the source of the code that shapes it change; the last line of the build says how many pieces were built and reused. Because the palette is shared, changing a colour that moves the palette re-quantizes nearly everything (the first build's two minutes again). Entries unused for 60 days are deleted.

## Levels

A level is a module in `content/levels`. A trimmed example from Hollowmere:

```python
from mapkit import Plan, on_n, on_s, on_w, on_e, at

NAME = "The Chapel"
FLOOR = "ATTIC"                     # heading on the map screen
AMBIENCE = 'amb_chapel'             # looping sound
START = (0.9, 5.4, 'N')             # player start: x, y in tiles, facing

MATERIALS = [('floor_boards', 'ceil_beams'),      # (floor, ceiling) pairs, 1 to 4
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

Walls appear between cells of different rooms and around the outside. An edge takes a character:

| | |
|---|---|
| `d`, `D` | single door, double door |
| `l` | a single door that must have `lock=` in `EDGES`. The letter marks it on the plan; the option is what locks it |
| `a`, `n` | arch, narrow arch |
| `w` | window |
| `x` | a closed door that is really a wall: a way out or a sign (`exit=`, `sign=`, `event=`) |
| `' '` | open |

A door or arch needs a room on both sides. A wall that touches nothing at either end is refused (seen end on, the renderer can lose it): join one end to another wall.

**`EDGES`** sets options per edge, keyed by `(x, y, 'N' | 'W')`:

| Option | |
|---|---|
| `lock=` | key id 1..15 the door needs |
| `name=` | the door's name in scripts |
| `leaf=` | the **prop texture** of the door's leaf (default `leaf_panel`, `leaf_double` for double doors) |
| `swing=`, `hinge=` | `'N'`/`'S'`/`'E'`/`'W'` the room it opens into (default: the smaller one); hinge `'L'` or `'R'` |
| `flags=` | `'startopen'`, `'scripted'` (only a script opens it), `'nomonster'` |
| `exit=`, `event=` | the **name of an event** to start when the player uses it (an exit's event usually ends with `('endlevel', n)`) |
| `sign=` | text shown when the player examines it |
| `tex_low=`, `tex_high=` | a different wall texture on the west/north or east/south side |

**`DECOR`** hangs flat decorations on walls, painted into the wall texture: `(x, y, side, kind)`; the kinds are whatever the game's `walltex.ensure` knows for `deco:`.

**`PROPS`** places 3D models. `at(model, x, y, facing)` stands one anywhere; `on_n` / `on_s` / `on_w` / `on_e` put it flush against that wall facing into the room. Options: `name=` (for scripts), `z=`, `tex=` (the model's instance texture), `light=`, `inter=('locker',)` (a hiding place), `inter=('event', 'name')`, `inter=('sign', "text")`, `inter=('hearth', n)` (a fixture that carries a number for the game's code: Hollowmere's hearths, with their light group), `front=` (how far in front the interaction is).

**`THINGS`** are sprites and items: `dict(type=, x=, y=, z=, param=, event=, name=, hidden=)`. `type` is a name of `props.PROPS`; `event` starts when the game says the thing was taken.

**`LIGHTS`**: `(x, y, brightness 0..31, radius under 16 tiles[, mode[, group 0..15]])`. Modes: `steady`, `flicker`, `buzz`, `pulse`, `candle`, `fire`. Steady lights of group 0 are baked; the others (at most 20 a level) flicker or can be switched by scripts through their group. `AMBIENT_LIGHT` adds a floor under everything.

**`TRIGGERS`**: `(x0, y0, x1, y1, 'event'[, once[, 'flag' or '!flag']])`. The event starts when the player **walks into** the cell rectangle; with `once=0` it starts again on every entry (not on every tick spent inside).

**`PATROL`** lists cells an enemy walks between and `MONSTER_MODE` is a number handed to the game: both are there for the game's code to use.

### Event scripts

`EVENTS` maps names to lists of operations, compiled to bytecode for the engine's VM:

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
}
```

**Eight events run at once.** `script_start()` returns 0 when all eight threads are busy; a game that must not lose an event (an item's, a note's) queues it and tries again, as Hollowmere's `game_event()` does.

Every operation:

| Operation | |
|---|---|
| `('wait', frames)` | up to 32,767 (nine minutes) |
| `('sound', name[, volume[, semitones]])` | volume 0..255 (200) |
| `('sound3d', name, x, y[, volume])` | at a cell |
| `('ambience', name or None[, volume])`, `('stopsounds',)` | the looping background sound |
| `('music', name[, volume])`, `('musicstop',)` | a tune of the manifest's `MUSIC` |
| `('msg', text[, frames])`, `('objective', text)` | subtitle; the objective line |
| `('hudoff', on)` | hide the HUD |
| `('door', name, 'open' \| 'close' \| 'lock' \| 'unlock' \| 'slam')` | |
| `('light', group, level 0..256)` | |
| `('thing', name, show)`, `('prop', name, show)` | show or hide |
| `('flag', name[, 0 or 1])` | 63 flags, shared by all levels and kept in the save |
| `('if_flag', name, label)`, `('ifnot_flag', name, label)` | |
| `('if_key', id, label)`, `('ifnot_key', id, label)`, `('if_fuses_lt', n, label)` | |
| `('jmp', label)`, `('jrand', chance of 256, label)`, `('label', name)` | |
| `('start', event)`, `('end',)` | |
| `('give', 'key' \| 'takekey', id)`, `('give', 'fuse' \| 'battery', amount)`, `('placefuses',)` | |
| `('note', id)` | asks the game to show note `id` |
| `('shake', amount, frames)`, `('flash', frames)`, `('blackout', frames)`, `('fade', level 0..16, speed)`, `('lookat', x, y)` / `('lookat', None)` | set variables the game acts on (`g_shakeAmt`, `g_flashT`...) |
| `('checkpoint',)` | calls `game_checkpoint()` |
| `('creature', op[, a[, b]])`, `('endlevel', next)`, `('ending',)`, `('fear', amount)`, `('teleport', x, y, dir)`, `('freeze', on)` | passed to `game_script()`: their meaning is the game's. In Hollowmere the creature ops are `spawn`, `script`, `pray` (x, y), `goto` (x, y), `hear` (x, y), `chase`, `despawn`, `mode` (n), `face` (angle 0..255) |

A level's first `LEVEL_EVENTS` event (`start`) runs when the level loads. An event named `resume`, if there is one, is `LevelDef.resumeEvent`: Hollowmere starts it after restoring a checkpoint, to put back what a checkpoint does not hold (the enemy, music).

## Models

`furniture.py` builds every 3D model with `engine/tools/meshkit.py`. Units are tiles (1.5 m): x and y on the floor (y points south, like the map), z up, the model's front faces +y.

```python
@model('nightstand')
def nightstand():
    m = Mesh('nightstand')
    m.box(-0.2, 0, 0, 0.2, 0.3, 0.42, 'wood_dark', front='drawer_front', skip='bn')
    m.boxes = [(-0.2, 0, 0.2, 0.3)]          # collision, model space
    return m
```

The building blocks: `box`, `wall` (a vertical quad, drawn on the fast path), `vquad` (a vertical quad with sloped top and bottom), `flat` (a horizontal polygon), `slope`, `prism`, `frustum`, `pole`, `loft` (rings into a smooth body), and `merge` to combine meshes. A model may name a simpler `far` model and the distance to switch to it. Vertical faces with stacked vertices take the fast trapezoid path, so prefer them for anything wall-like; such a face cannot repeat its texture downwards (keep its texture rows within 0..64).

## Limits

The asset build checks all of these and stops with one line naming the level, event or model. The numbers live in one file, `engine/src/limits.h`, which the C code, the tools and the linker script all read.

| | Limit |
|---|---|
| map | 31 × 31 cells |
| doors / props / things per level | 40 / 160 / 112 |
| triggers / rooms / dynamic lights per level | 32 / 32 / 20 |
| edge types (texture pairs, doors, arches) per level | 255 |
| furniture collision boxes per level | 254 |
| events per level / threads at once | 255 / 8 |
| `wait` | 32,767 frames |
| script flags / keys / notes / light groups | 63 / 15 (ids 1..15) / 32 / 16 |
| model | 128 vertices, 64 faces, no face edge over 2.4 tiles |
| textures | walls 64×128, floors, ceilings and models 64×64 |
| text | ASCII with a glyph in the font (`engine/tools/font.py`) |

Two limits are on what is drawn at once, which the build cannot know: 11 open door leaves and 62 things. Past them the rest is not drawn; the build prints a note for a level that has more in total.

## Checking your work

```sh
python3 engine/tools/audit.py           # furniture through walls, blocked doorways, floating items...
python3 engine/tools/textcheck.py       # every script message fits the HUD; plus the game's own tests/textrules.py
python3 engine/tools/preview_map.py l1_ground out.png      # top-down plan of a level
GAME=mygame python3 engine/tools/check.py                  # everything, skipping what the game has no tests for
```

With the test harness built (`make harness`) you can script whole playthroughs, benchmark views and take screenshots from any camera; see [Toolchain & testing](TOOLS.md).
