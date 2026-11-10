// SPDX-License-Identifier: MIT
// The engine's limits, in one place. Three readers:
//   the C code (engine.h includes this file);
//   the asset tools (engine/tools/limits.py reads the #define lines below and
//     refuses content that goes over, naming the level and the limit);
//   the linker script (gba.ld is run through the preprocessor with this file
//     and asserts that its hand-placed tables still fit).
// One "#define NAME value" per line, plain integers only: the tools parse them.
#ifndef LIMITS_H
#define LIMITS_H

// ---- a level
#define MAP_W 32                  // the cell grid; a level's plan is at most MAP_W-1 by MAP_H-1 cells
#define MAP_H 32
#define MAX_EDGE_TYPES 255        // distinct wall/door/arch looks in one level (a u8 per edge, 0 = open)
#define MAX_DOORS 40
#define MAX_PROPS 160
#define MAX_BOXES 254             // collision boxes of the furniture (a u8 list, 255 ends it)
#define MAX_THINGS 112
#define MAX_INTERS 255
#define MAX_TRIGGERS 32
#define MAX_ROOMS 32
#define MAX_PATROL 255
#define MAX_DLIGHTS 20            // lights that flicker or belong to a script's group
#define MAX_LIGHT_BYTES 8192      // their baked patches, together
#define MAX_LIGHT_LEVEL 31
#define MAX_LIGHT_GROUPS 16
#define MAX_MATERIALS 4           // floor and ceiling texture pairs
#define MAX_LEVELS 255

// ---- scripts
#define MAX_EVENTS 255            // per level (a u8, 0 = none)
#define MAX_EVENT_BYTES 65535     // one event's bytecode
#define MAX_THREADS 8             // events running at once
#define MAX_WAIT 32767            // frames one ('wait', N) can hold
#define NUM_FLAGS 64
#define NUM_SCRIPT_FLAGS 63       // the scripts' own; the last one is the game code's
#define MAX_KEYS 16
#define MAX_NOTES 32
#define MAX_OBJECTIVE_STRING 255  // an objective's string id is saved in a byte
#define MAX_STRINGS 65535

// ---- models and textures
#define MAX_MODEL_VERTS 128
#define MAX_MODEL_FACES 64
#define MAX_FACE_LEN 614          // a face's longest edge, 1/256 tile (2.4 tiles)
#define MAX_MODEL_COORD 32767     // a vertex coordinate, 1/256 tile
#define MAX_MODELS 255
#define MAX_PROP_TEXTURES 255
#define WALL_TEX_W 64
#define WALL_TEX_H 128
#define FLAT_TEX_SIZE 64          // floor and ceiling textures are square
#define PROP_TEX_SIZE 64

// ---- drawn at once (what is over is not drawn, in the level's own order: the
// asset build prints a note for a level that could get there)
#define MAX_DYNPROPS 12           // door leaves standing open or moving, less one
#define MAX_SPRITES 64            // things and the enemy, less two

// ---- sizes the linker script's table layout depends on (gba.ld)
#define VIEW_W 240                // columns of the 3D view
#define NUM_LIGHT 32              // light levels of the colour map
#define MAX_VOICES 10             // the mixer's

#endif
