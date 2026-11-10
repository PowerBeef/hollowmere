// SPDX-License-Identifier: MIT
// Hollowmere game state and module interfaces
#ifndef GAME_H
#define GAME_H
#include "gba.h"
#include "engine.h"
#include "leveldef.h"

#define MAX_THINGS 112
#define NUM_FLAGS  64

// The script threads a checkpoint remembers: which event each is running,
// how far in, and how long it still waits.
#define MAX_THREADS 8
typedef struct { u8 ev[MAX_THREADS]; u16 pc[MAX_THREADS]; s16 wait[MAX_THREADS]; } ScriptSave;

// ---------------------------------------------------------------- save
typedef struct {
    u32 magic;
    u8  level;
    u8  version;
    u8  objective;
    u8  creatureMode;
    u32 notesFound;      // bitmask of collected notes
    u16 keys;            // bitmask of keys held
    u8  fuses, fusesPlaced;
    u32 battery;         // 0..1000000
    u8  flashOn, pad0;
    u16 deaths;
    u32 playFrames;
    u8  thingTaken[MAX_THINGS / 8];
    u8  thingShown[MAX_THINGS / 8];
    u8  trigFired[4];
    u8  roomsSeen[4];           // map: rooms of this floor visited (bit per room)
    u8  doorState[MAX_DOORS];   // DS_*
    u8  propHidden[20];         // script-toggled furniture
    u8  propSet[20];
    u8  flags[NUM_FLAGS / 8];
    u8  lightLevel[16];         // per light group brightness /16
    ScriptSave script;          // the level scripts in flight (engine/src/script.c)
    s32 px, py;
    u16 pangle;
    u16 checksum;
} SaveState;
#define DS_OPEN     1
#define DS_UNLOCKED 2
#define DS_LOCKED   4    // locked by script

#define SAVE_MAGIC 0x484C5732u   // "HLW2"

extern SaveState g_state;
extern SaveState g_checkpoint;
extern u8 g_hasCheckpoint;

// --------------------------------------------------------------- things
typedef struct {
    s32 x, y;
    u8  type, param, flags, event;
    s16 z;
} Thing;
#define THF_TAKEN  1
#define THF_HIDDEN 2

extern Thing g_things[MAX_THINGS];
extern int g_numThings;

// interactables
enum { INTER_NONE = 0, INTER_LOCKER, INTER_FUSEBOX, INTER_GENERATOR, INTER_EXIT, INTER_EVENT, INTER_SIGN, INTER_CREATURE };

// --------------------------------------------------------------- player
typedef struct {
    s32 x, y;
    u16 angle;
    s16 turnVel;
    s16 stamina;
    u8  running, exhausted;
    u8  hiding;
    u8  hideIdx;
    u16 hideBaseAngle;
    s32 outX, outY;
    u16 outAngle;
    u32 stride;        // distance accumulator for steps
    u8  stepIdx;
    u8  frozen;        // controls disabled (cutscene / death)
    s16 bob;
    u32 bobPhase;
    s32 speed;         // current speed, for bob
    int breathHandle;
    s16 flickerT;
    u8  seenBy;        // creature currently sees player
} Player;
extern Player g_player;

// target under the crosshair
enum { TGT_NONE = 0, TGT_THING, TGT_DOOR, TGT_INTER, TGT_CREATURE };
typedef struct { u8 kind; u8 idx; } Target;
extern Target g_target;

// ------------------------------------------------------------- creature
enum { CR_OFF = 0, CR_SCRIPT, CR_PATROL, CR_INVESTIGATE, CR_CHASE, CR_SEARCH, CR_LEAVE, CR_KILL, CR_PRAY, CR_WAIT, CR_RETURN };
typedef struct {
    u8  state;
    u8  mode;          // level presence mode: 0 scripted only, 1 roaming, 2 aggressive
    s32 x, y;
    u16 angle;
    s32 goalX, goalY;  // movement goal (16.16)
    s32 speed;
    u32 anim;
    u8  frame;
    u8  moving;
    s16 timer;
    s16 lostTimer;
    s32 lastX, lastY;
    s16 alert;
    u8  knowsHiding;
    u8  hasLOS;
    s32 dist;          // distance to player 16.16
    int breath, lantern;
    u32 strideAcc;
    s16 doorWait;
    u8  pathCell;      // target cell of current flow field
    s16 pathAge;
    s16 cooldown;      // frames until respawn (when OFF in roaming mode)
    u8  screamed;
    u8  prayTurn;
    s16 lookTimer;
    u16 lookAngle;
    s16 scriptIdx;
    s32 prayX, prayY;
    u16 prayAngle;
} Creature;
extern Creature g_cr;
extern s16 g_fear;          // 0..256

// --------------------------------------------------------------- script
int  script_start(int event);        // 0: no free thread (or no such event)
int  script_running(int event);
void script_update(void);
void script_reset(void);
void script_save(ScriptSave *out);
void script_load(const ScriptSave *in);
int  script_flag(int f);
void script_set_flag(int f, int v);

// --------------------------------------------------------------- game
enum { GS_PLAY = 0, GS_DEAD, GS_EXIT, GS_ENDING, GS_PAUSE = 100, GS_MAP = 101 };
extern u8 g_gameSignal;      // set by systems to request a state change
extern u8 g_nextLevel;
extern u32 g_frame;

void game_new(void);
void game_load_level(int level, int fromCheckpoint);
void game_update(void);      // one logic step (1/60 s)
void game_render(void);
void game_checkpoint(void);
void game_restore_checkpoint(void);
void game_set_objective(int str);
void game_message(int str, int frames);
const char *game_str(int id);
void game_build_sprites(void);
void game_noise(s32 x, s32 y, s32 radius);
void game_event(int ev);          // start a script event; waits for a free thread if need be

// player
void player_init(s32 x, s32 y, u16 angle);
void player_update(u16 keys, u16 pressed);
void player_hide_exit(void);
void player_apply_flashlight(void);

// creature
void creature_init(int mode);
void creature_spawn(s32 x, s32 y, int state);
void creature_despawn(void);
void creature_update(void);
void creature_hear(s32 x, s32 y, s32 radius);
void creature_goto(s32 x, s32 y);
int  creature_sprite(RSprite *s);
void creature_light(void);

// things
void things_load(const LevelDef *L);
int  thing_take(int idx);

// save
int  save_write(const SaveState *s);
int  save_read(SaveState *s);
int  save_exists(void);
void save_erase(void);

// settings stored alongside the save
typedef struct { u8 brightness, volume, controls, seenIntro; } Settings;
extern Settings g_settings;
void settings_save(void);
void settings_load(void);

// misc helpers
s32 isqrt32(u32 v);
s32 dist_approx(s32 dx, s32 dy);
u16 angle_to(s32 dx, s32 dy);

#endif
