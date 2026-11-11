# Changelog

## v1.3.1

One fix to v1.3.

- **Fixed: a pale line along the top of some walls.** Where a room with a dark ceiling meets one with a pale ceiling (the hall and the corridor behind its far wall, most of all), a line of the next room's ceiling showed above the wall between them, up to three rows thick, at some distances and not at others; a line of the next room's floor showed along the wall's foot the same way. Floors and ceilings are drawn in pairs of rows, each pair sampled at its middle, and the one row left showing where a wall's edge fell inside a pair could be sampled just beyond the wall. Each pair is now sampled at its near edge, which no wall that leaves part of it showing stands in front of. In 600 views of the drawing room with its doors shut, 54,174 pixels came from beyond the walls in v1.3 and 326 do now (a few at wall corners, 16 in the worst view). It costs no frame time: the change is in a table.
- In every version since v1.0. Saves are untouched.

## v1.3

Fire. The fireplaces were painted embers with a faint flicker; they are hearths now, and the first new thing to do in the house since v1.0.

- **Hearths are laid and cold until you light them.** With the box of matches from the kitchen stove (upstairs, the one on the Night Sister's dresser), A at a hearth lights it: flames in the firebox, a warm light that fills the room, the crackle of the logs. A again rakes it out; it can be lit again.
- **She cannot leave a fire burning.** Once she walks a floor, a fire brings her within seconds if she is away, and wherever she is on her rounds she goes to it, sets her lantern down, kneels until it is cold, gets up and searches the room. What she has put out is ash: it will not light again. The housekeeper's ledger says as much, in one new line.
- **So a fire is a tool, and a risk.** It lights a room without the flashlight, and she sees you sooner in its light. It draws her to one end of the house while you cross the other, and it calls her when she was not there at all.
- Six hearths: the drawing room, the dining room and the study downstairs; upstairs, new ones in the two wards (back to back on one chimney) and in the doctor's bedroom. Upstairs the dress form in the east ward and the doctor's armchair moved a little to make room. No wall or door changed.
- **Fixed: she could come back on her rounds shut in the doctor's suite.** One of the upper floor's patrol nodes is behind its locked door; starting there (two or three returns of fourteen with the player in the west ward) she walked up and down inside until the player unlocked it. She now starts only where the rest of her rounds can be reached.

- **Fixed: switching the flashlight could still cost a frame.** In the heaviest view (the hall from the front door) the switch sometimes fell together with the lamps' flicker step: 858,000 cycles against the 842,688 a frame has. The flicker now waits two frames around a switch; the worst measured is under 800,000.

Saves from v1.2 load as they were, with every hearth cold: new text, things and furniture are numbered after the old.

### Known limits

- Frame rate, measured again on all four floors: of 3,381 places and headings, 70 fall below 19.5 fps (v1.1: 62 of 3,396) and 18 of them stay at 15 fps (17). Three quarters of all views run at full detail, as before.
- A fireplace seen from close up is costly to draw. The views of the three new hearths upstairs run at a lower detail level than the bare walls they replaced: 78% of that floor's views are at full detail, where 86% were. The one new view at 15 fps is a corner of the west ward, standing against the wardrobe.
- Still measured in the mGBA emulator only.

### For people building on the engine

- A light mode `fire`: slow swells with a gutter now and then, beside `candle`'s shimmer.
- A fixture kind that carries a number (`inter=('hearth', group)`), and `late_strings()` in a game's `story.py`: text added in a later version, numbered after everything else so that older saves' string numbers keep their meaning.
- The fireplace shows how a game animates a prop: its front face takes the instance's texture, and the game sets that every few ticks (`game/src/hearth.c`).
- A light that is out (level 0) costs nothing in the flicker step; it used to have its rectangle of the light grid put back ten times a second.
- Two tests no longer depend on the moment they run at: the flashlight test tries four timings (and fails on v1.2), and the lantern-trail test looks at the lamps sixty times, not ten, before it calls a flicker a trail.

## v1.2

The Night Sister moves. She had walk and run cycles and four still poses; the stills are now animations: 360 pre-rendered frames where there were 155.

- **She breathes.** Standing on her rounds she was one frozen picture; she now plays a six-picture loop, her shoulders and lantern rising and settling.
- **She looks for you.** Searching a room she turns her shoulders, head and lantern from side to side over eight pictures instead of holding one pose.
- **She prays, and gets up.** Kneeling in the chapel she rocks slowly. When she stirs she takes up her lantern and rises through six pictures, then kneels again through the same six; she used to snap between kneeling and standing.
- **She opens doors by hand.** Her free hand goes out to a door as it swings, four pictures in step with the door, where she used to stand and wait in front of it.
- **The lunge that ends a chase has eight pictures** over its second and a half, not three.

For people building on the engine: re-rendering part of her sheet (`make.py --only door`) no longer unpacks the whole sheet once per frame, which had come to need more memory than most machines have.

Nothing else changes: her behaviour, the levels and the saves are those of v1.1.1. The ROM grows from 14.8 to 17.2 MB of the cartridge's 32.

## v1.1.1

- The portraits on the walls no longer have a black blob over the bottom of their frames: the sitter's dark coat was painted past the edge of the canvas (it was so in v1.0 too).
- The ending credits name the game's director, PowerBeef.

Because all textures share one palette, the portrait's change moved a few palette entries, so the ROM differs from v1.1 in more bytes than these two changes suggest. Saves are compatible.

## v1.1

The remediation of an audit of v1.0: 59 findings, from a chapter that could not be finished after a death to a test suite that could not fail. Saves from v1.0 still work (the game continues at the start of the chapter the save had reached).

### For players

- **Chapter IV can be finished after dying in it.** A death used to lose the level's opening script, and with it the Night Sister at prayer. Every chapter's opening now survives a death, and a checkpoint keeps the scripts that were running when it was taken.
- Pressing START in the frame of a death or of a level exit no longer swallows it (the player was left frozen at the cellar door).
- **Running makes noise.** The controls screen always said she hears it; now she does, five tiles away (three through walls).
- Furniture no longer vanishes from some angles (the stove, a fireplace, the hall staircase), notes and batteries lying on tables can be seen from every side, and no view leaves pixels of the previous frame on screen: 20,368 views checked, none with an undrawn pixel (v1.0: 583).
- Objects seen through two doorways are no longer cut off by the farther lintel; a third doorway in a row keeps its lintel.
- Edges of furniture close to the camera no longer wobble by several pixels, and furniture stays put against the wall behind it when the view turns.
- The wardrobe's slats and its muffled sound no longer follow you into the pause menu, the title or a new game; the HUD is back after the ending; resuming from pause, opening the map and the death scene no longer flash wrong rows or colours.
- The long sign in the vestry is shown whole. Subtitles of any length fit their two lines.
- With the alternative controls, B in a wardrobe only works the light.
- Taking the lantern can no longer get you killed in the moment of winning.
- Buttons pressed during a chapter card or the death scene no longer act once the game is back.
- The Night Sister's lantern no longer leaves a trail of light, lights flicker at the same rate whatever the frame rate, and she does not walk through a door a script has just locked.
- **Saves cannot be lost or abused.** Two alternating slots: a power cut during a save leaves the previous one intact. A save file with a valid checksum and nonsense inside (level 200) used to hang the game; every field is now checked.
- Smoother: switching the flashlight, a line of text appearing and the Sister re-planning her path each used to cost a frame or more, and after every fade the view ran at its lowest detail for some seconds.

### For people building on the engine

- **The engine stands apart from the game.** `engine/src/game_api.h` is the whole interface (nine hooks); `examples/minimal` is a complete second game in one 180-line C file; `make GAME=<folder>` builds any game.
- **One table of limits** (`engine/src/limits.h`), read by the C code, the tools and the linker script. The asset tools refuse content over a limit with one line naming the level, event or model; `contentcheck.py` proves 47 refusals.
- The linker script asserts its hand-placed tables against the limits and keeps 1,280 bytes of fast RAM for the stack; only the hot code's variables live in fast RAM.
- **Tests that can fail.** The harness has expectations and exits non-zero on a crashed ROM; `make check` runs a playthrough with assertions, 38 regression tests, the hole sweep, 43 hostile saves, stack and frame-rate checks, and the tools' own self-tests. The release ROM carries no debug hook.
- The asset cache cannot serve stale output (three cases fixed), survives a truncated entry and prunes itself. Requirements are pinned; a GitHub workflow builds twice and compares the ROMs.
- A clean clone builds from the README: SciPy is listed as required and the title font ships in the repository.
- The script operations `inter` and `chapter`, which did nothing, are gone. `l` on a floor plan must come with `lock=`.
- Documentation matches the code: `exit=` and `leaf=`, triggers, the harness's commands, every script operation, the save format, and what is not known.

### Known limits

- Not every view holds 20 fps. Of 3,396 places and headings sampled with the detail governor on, 62 fall below 19.5 fps (v1.0: 189) and 17 of them stay at 15 fps at the lowest detail level (v1.0: 9): close views of the hall staircase and of the chapel's pews, where furniture covers the screen several times over. v1.1 draws furniture there that v1.0 dropped by mistake and places its edges exactly, which costs those views a few percent more than they had.
- All timing is from the mGBA emulator (0.10.2). Nothing has been run on a console, which may read video memory more slowly.
- One finding of the audit could not be reproduced on v1.0 (the Sister opening a door locked after she had planned her path: v1.0 already re-checked the door). The re-check is now explicit and has a test.

### Licence

The game joins the engine under the MIT licence: the whole repository has one licence.
