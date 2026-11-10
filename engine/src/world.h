// SPDX-License-Identifier: MIT
#ifndef WORLD_H
#define WORLD_H
#include "engine.h"
#include "leveldef.h"

typedef struct {
    const LightDef *def;
    const u8 *patch;
    u8 x0, y0, w, h;
    s16 level;      // script brightness 0..256
    u8 on;
    u8 flick;
} DynLight;

extern DynLight g_dlights[MAX_DLIGHTS];
extern int g_numDLights;
extern u8 g_lightsDirty;          // set when a light group changes level
extern const LevelDef *g_level;
extern const u8 *g_cellFlags;      // per cell: 1 inside, 2 blocked by furniture
#define CELLF_INSIDE  1
#define CELLF_BLOCKED 2

void world_load_level(const LevelDef *L);
void world_update_lights(int frame);            // frame: the logic tick (60 a second)
void world_light_guest(int x0, int y0, int w, int h);  // light cells lit by someone else: restored at the next refresh
void world_update_doors(void);
void world_door_props(void);
u8   world_edge(int x, int y, int north);          // west (0) / north (1) edge of a cell
u8   world_edge_dir(int x, int y, int dir);        // edge crossed leaving (x,y): 0 N, 1 E, 2 S, 3 W
int  world_edge_pass(u8 et);
Door *world_door_on(u8 et);
int  world_inside(int x, int y);
int  world_point_blocked(s32 x, s32 y);
void world_move(s32 *px, s32 *py, s32 dx, s32 dy, s32 r);
int  world_los(s32 x0, s32 y0, s32 x1, s32 y1);
u32  rng_next(void);
void rng_seed(u32 v);

#endif
