# Changelog

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
