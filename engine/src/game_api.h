// SPDX-License-Identifier: MIT
// What the engine and a game agree on. The engine includes no header of a
// game; a game includes this one. It has three parts:
//
//   1. the state of a playthrough, which the engine's scripts and save code
//      work on and a game extends with its own modules;
//   2. what the engine offers a game beyond drawing and sound: the frame
//      loop, the script threads, the battery save;
//   3. the hooks: functions and one constant every game defines, which the
//      engine calls. examples/minimal implements all of them in one file.
#ifndef GAME_API_H
#define GAME_API_H
#include "engine.h"
#include "leveldef.h"

// ================================================================ 1. state
// The script threads a checkpoint remembers: which event each is running,
// how far in, and how long it still waits.
typedef struct { u8 ev[MAX_THREADS]; u16 pc[MAX_THREADS]; s16 wait[MAX_THREADS]; } ScriptSave;

// Everything a checkpoint keeps. The script operations (engine/tools/
// scriptc.py) work on these fields: keys, fuses, battery, flags, light
// groups, doors, props, things. A game that has no use for one leaves it 0.
typedef struct {
    u32 magic;           // game_info.saveMagic
    u8  level;
    u8  version;         // SAVE_VERSION
    u8  objective;       // string id of the current objective (0: none)
    u8  creatureMode;    // the game's: how present its enemy is on this level
    u32 notesFound;      // bitmask of collected notes
    u16 keys;            // bitmask of keys held
    u8  fuses, fusesPlaced;
    u32 battery;         // 0..1000000
    u8  flashOn;
    u8  seq;             // which of the two save slots is the newer (save.c)
    u16 deaths;
    u32 playFrames;
    u8  thingTaken[MAX_THINGS / 8];
    u8  thingShown[MAX_THINGS / 8];
    u8  trigFired[MAX_TRIGGERS / 8];
    u8  roomsSeen[MAX_ROOMS / 8];    // map: rooms of this floor visited (bit per room)
    u8  doorState[MAX_DOORS];        // DS_*
    u8  propHidden[MAX_PROPS / 8];   // script-toggled furniture
    u8  propSet[MAX_PROPS / 8];
    u8  flags[NUM_FLAGS / 8];
    u8  lightLevel[MAX_LIGHT_GROUPS];   // per light group brightness /16
    ScriptSave script;          // the level scripts in flight (script.c)
    s32 px, py;
    u16 pangle;
    u16 checksum;
} SaveState;
#define DS_OPEN     1
#define DS_UNLOCKED 2
#define DS_LOCKED   4    // locked by script
#define SAVE_VERSION 3   // of this layout; a save of any other is not loaded
_Static_assert(MAX_KEYS == 16 && MAX_NOTES == 32 && MAX_ROOMS == 32 && MAX_TRIGGERS == 32 && MAX_THINGS % 8 == 0 && MAX_PROPS % 8 == 0 &&
               NUM_FLAGS % 8 == 0 && NUM_SCRIPT_FLAGS == NUM_FLAGS - 1,
               "limits.h against the save state: keys and notes are bit masks in a u16 and a u32, rooms and triggers in 32 bits");
#define FLAG_GAME (NUM_FLAGS - 1)      // the one flag the scripts cannot name (the compiler hands out 0..NUM_SCRIPT_FLAGS-1)

extern SaveState g_state;       // the playthrough in progress (script.c)

// The things of the level: items to take and decor sprites (world.c). The
// game fills them when it loads a level and draws them as it likes.
typedef struct {
    s32 x, y;
    u8  type, param, flags, event;
    s16 z;
} Thing;
#define THF_TAKEN  1
#define THF_HIDDEN 2
extern Thing g_things[MAX_THINGS];
extern int g_numThings;

// =========================================================== 2. the engine
// ---- the frame loop (runtime.c)
// engine_init() sets up video, the renderer's tables, sound and interrupts.
// Then, for every frame: engine_frame_start(), the game's logic updates
// (engine_ticks() says how many 1/60 s steps are due), engine_frame().
void engine_init(void);
void engine_frame_start(void);  // starts the frame's clock: before the updates that lead to the frame
int  engine_ticks(void);        // logic steps due since the last call, 1 to 4
void engine_frame(void);        // game_render(), the detail governor, then waits until the frame is on screen
void engine_frame_reset(void);  // a new scene (level loaded, checkpoint restored): detail starts from full again
void engine_present(void);      // shows a frame the game rendered itself, and waits for it
u16  engine_keys_pressed(void); // keys that went down since the last call (caught in the vblank interrupt)
extern u8 g_quality;            // the detail level the governor chose (0 = full, 7 = least)

// ---- level scripts (script.c)
int  script_start(int event);        // 0: no free thread (or no such event)
int  script_running(int event);
void script_update(void);            // once per logic step
void script_reset(void);
void script_save(ScriptSave *out);
void script_load(const ScriptSave *in);
int  script_flag(int f);
void script_set_flag(int f, int v);
// set by scripts, for the game to act on and count down (script_reset clears them)
extern int g_shakeAmt, g_shakeT;         // ('shake', amount, frames)
extern int g_flashT;                     // ('flash', frames): lightning
extern int g_blackoutT;                  // ('blackout', frames): lights and flashlight out
extern int g_fadeTarget, g_fadeSpeed, g_fadeAcc;   // ('fade', level 0..16, frames per step)
extern int g_lookX, g_lookY;             // ('lookat', x, y): a cell to turn the view to, or -1
extern int g_ambience;                   // the ambience loop's sound handle, or -1
extern int g_noteRequest;                // ('note', id): show this note, or -1

// ---- battery save (save.c): a settings block and two alternating slots
int  save_write(const SaveState *s);
int  save_read(SaveState *s);        // SAVE_NONE, SAVE_OK, or SAVE_IMPORTED: game_save_import() filled it from an older format
int  save_exists(void);
void save_erase(void);
enum { SAVE_NONE = 0, SAVE_OK, SAVE_IMPORTED };
void save_settings_write(const u8 b[4]);     // four bytes of options, kept under game_info.settingsTag
int  save_settings_read(u8 b[4]);            // 0: none stored
void save_raw_read(int ofs, void *dst, int n);       // bytes of the save area, for game_save_import()
u16  save_sum16(const void *p, unsigned n);          // the slots' checksum

// ---- helpers
s32 isqrt32(u32 v);
s32 dist_approx(s32 dx, s32 dy);
u16 angle_to(s32 dx, s32 dy);

// =========================================================== 3. the hooks
// Every game defines these.
typedef struct {
    u32  saveMagic;         // four characters that tell this game's saves from another's
    char settingsTag[4];    // ... and its settings block
} GameInfo;
extern const GameInfo game_info;

void game_render(void);                      // draw one frame of the 3D view into the back buffer (engine_frame calls it)
const char *game_str(int id);                // a string of the generated table (assets.h: STR_*)
void game_message(int str, int frames);      // ('msg', text, frames): a subtitle
void game_set_objective(int str);            // ('objective', text)
void game_checkpoint(void);                  // ('checkpoint',): keep the state (and save it, if the game saves)
int  game_state_valid(const SaveState *s);   // a state read from the cartridge: is every index and range in it usable?
int  game_save_import(SaveState *out);       // no slot is good: is there a save of an older version to carry over? 0: no
// Script operations whose meaning is the game's. `what` is one of GSC_*.
enum {
    GSC_ENEMY,          // ('creature', op, a, b): a = the operation (scriptc.CREATURE_OPS), b, c = its two values
    GSC_ENDLEVEL,       // ('endlevel', next): a = the level to go to
    GSC_ENDING,         // ('ending',)
    GSC_FEAR,           // ('fear', amount)
    GSC_TELEPORT,       // ('teleport', x, y, dir): cell a, b; c = 0 east, 1 south, 2 west, 3 north
    GSC_FREEZE,         // ('freeze', on): the player's controls off or on
};
void game_script(int what, int a, int b, int c);

#endif
