// SPDX-License-Identifier: MIT
// Level definition structures (generated data lives in gen/levels.c)
#ifndef LEVELDEF_H
#define LEVELDEF_H
#include "gba.h"

typedef struct {
    u8 x, y, axis, kind;
    u8 lock;         // key id required (0 = none)
    u8 flags;        // DOORF_*
    u8 hinge;        // DOORH_*
    u8 edgeType;     // edge type of the doorway
    u16 leafTex;     // prop texture of the leaf
    u8 pad[2];
} DoorDef;
#define DOORF_STARTOPEN 1
#define DOORF_SCRIPTED  2   // cannot be opened by the player (script only)
#define DOORF_NOMONSTER 4   // the creature cannot pass

typedef struct {
    const struct SpriteImg_ *img;
    const struct SpriteImg_ *glint;
    u16 worldW, worldH;    // 1/256 tile
    s16 zoff;
    u8  flags;             // TT_*
    u8  pad;
} ThingType;
#define TT_SOLID      1
#define TT_FULLBRIGHT 2
#define TT_ITEM       4

typedef struct {
    u16 x, y;        // 1/256 tile
    u8  type;        // THING_* (see assets.h)
    u8  param;       // e.g. note id, key id
    u8  flags;       // TDF_*
    u8  event;       // script event on pickup
    s16 z;           // height above the floor, 1/256 tile (on a table...)
    u16 pad;
} ThingDef;
#define TDF_HIDDEN 1

typedef struct {
    u16 x, y;        // 1/256 tile
    u8  intensity;   // 0..31
    u8  radius;      // tiles * 16
    u8  mode;        // LIGHT_* flicker mode
    u8  group;       // script control group
} LightDef;
enum { LIGHT_STEADY = 0, LIGHT_FLICKER, LIGHT_BUZZ, LIGHT_PULSE, LIGHT_CANDLE };

typedef struct {
    u16 x, y;        // 1/256 tile: where the interaction happens
    u8 type;         // INTER_*
    u8 param;
    s8 nx, ny;       // facing (x64): usable from this side only
    u8 strHi;        // signs: high byte of the string id
    u8 prop;         // prop index or 0xFF
    u16 hx, hy;      // lockers/wardrobes: where the player hides (1/256 tile)
    u8 hangle;       // and the direction they look (256 per turn)
    u8 pad;
} InterDef;

typedef struct {
    u16 x, y;        // 1/256 tile
    s16 z;           // height above the floor, 1/256 tile
    u8 model;
    u8 angle;        // 256 per turn; 0 = front faces south (+y)
    u8 flags;
    u8 tex;          // texture for the model's instance faces
    s8 light;
    u8 pad;
} PropDef;

typedef struct { u16 x0, y0, x1, y1; } CollBox;    // 1/256 tile, axis aligned

typedef struct {
    u8 x0, y0, x1, y1;   // inclusive cell rectangle
    u8 event;            // script event id
    u8 flags;            // TRIGF_*
    u8 needFlag;         // script flag + 1 that must be set (needNot: clear) for it to fire; 0 = always
    u8 needNot;
} TriggerDef;
#define TRIGF_ONCE 1

typedef struct {
    u8 x, y;
} PathNode;

// The map screen: the house's bounding box of cells, a room per cell and
// what to draw on every edge (low nibble: west edge, high: north edge).
typedef struct {
    u8 x0, y0, w, h;             // bounding box in level cells
    u8 numRooms, pad;
    const u8 *room;              // w*h: room index, 0xFF outside
    const u8 *edge;              // (w+1)*(h+1): MAPE_* west | north << 4
    const char *const *roomName;
    const u8 *roomFlags;         // MAPR_*
    const char *floorName;
} MapDef;
enum { MAPE_OPEN = 0, MAPE_WALL, MAPE_DOOR, MAPE_ARCH, MAPE_WINDOW, MAPE_EXIT, MAPE_SEALED };
#define MAPR_VOID 1              // an open drop (the stairwell): shown once a room beside it is seen

typedef struct {
    const char *name;
    const u8 *edges;             // 32*32 cells x [west, north] edge types
    const struct EdgeType_ *edgeTypes;
    const u8 *lightLZ;           // LZ77 static light grid (64x64, material in bits 5-6)
    const u8 *visLZ;             // LZ77 dynamic light patches
    const u8 *cells;             // 32*32: 1 inside the house, 2 blocked by furniture
    u16 flatTex[8];              // 4 materials x (floor, ceiling) texture ids
    const DoorDef *doors;     u8 numDoors;
    const PropDef *props;     u8 numProps;
    const CollBox *boxes;     u8 numBoxes;
    const u16 *cellBox;          // per cell: offset into boxList
    const u8 *boxList;           // box indices, 255-terminated per cell
    const ThingDef *things;   u8 numThings;
    const LightDef *lights;   u8 numLights;
    const InterDef *inters;   u8 numInters;
    const TriggerDef *trigs;  u8 numTrigs;
    const PathNode *patrol;   u8 numPatrol;
    const u8 *const *events;  u8 numEvents;
    const u16 *eventLen;         // bytes of each event's script
    u8  startEvent;
    u16 startX, startY, startAngle;   // 1/256 tile, angle 0..65535
    u8  levelId;
    u8  monsterMode;             // initial creature presence
    u16 ambience;                // sound id of the ambience loop
    u16 musicId;
    const MapDef *map;
    u8  resumeEvent;             // run after a checkpoint restore: restarts loops and lures (0 = none)
} LevelDef;

#endif
