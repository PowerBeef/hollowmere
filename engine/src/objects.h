// SPDX-License-Identifier: MIT
// 3D props (furniture, door leaves) and their data formats
#ifndef OBJECTS_H
#define OBJECTS_H
#include "engine.h"

// ---------------------------------------------------------------- models
// Model space: x, y on the floor plane, z up, units of 1/256 tile.
typedef struct { s16 x, y, z; } MVert;

// A face is a convex quad (v[3] != 0xFF) or triangle. Vertical faces with
// horizontal top and bottom edges (box sides) take a faster path: their
// v coordinates run from the top edge to the bottom edge.
typedef struct {
    u8 v[4];
    u8 tex;          // prop texture; FACE_TEXINST = the instance's own texture
    u8 flags;        // FF_*
    s8 n[3];         // outward normal (model space), length ~64
    u8 lod;          // drawn up to this distance (1/8 tile); 255 = always
    u8 uv[8];        // u,v per vertex in texels (0..255, textures repeat every 64)
    s32 d;           // plane: n . p = d for points p on the face
    s16 cx, cy;      // where the face samples the light grid (model space)
} MFace;
#define FACE_TEXINST 255
#define FF_VERT   1
#define FF_2SIDED 2
#define FF_OCC    4      // big opaque wall-like face (listed first; Model.nocc of them)
#define FF_THIN   8      // post or pole: never dropped, at least one column wide
#define FF_SHADE(f) ((s8)((f) & 0xF0) >> 4)   // signed light offset, bits 4-7

typedef struct {
    const MVert *v;
    const MFace *f;
    u8  nv, nf;
    u16 radius;      // xy bounding radius from the origin, 1/256 tile
    s16 zmax;        // top, 1/256 tile
    u8  nocc;        // faces 0..nocc-1 are occluders (FF_OCC)
    u8  mflags;      // MF_*
    u8  far;         // 1 + the model drawn instead beyond farDist (0: none)
    u8  farDist;     // 1/8 tile, from the model's centre (scaled with the detail level)
    s16 cx, cy;      // the model's centre (1/256 tile)
} Model;
#define MF_HALF 1        // always one sample per column pair (big, soft-textured: rugs)
extern const Model models[];
extern const u8 *const proptex[];      // 64x64 column-major textures (ROM)

// --------------------------------------------------------------- instances
typedef struct {
    s32 x, y;        // 16.16 world position of the model origin
    s16 z;           // base height above the floor, 1/256 tile
    u16 angle;       // 0..65535
    u8  model;
    u8  flags;       // PIF_*
    u8  tex;         // texture for FACE_TEXINST faces
    s8  light;       // light bonus
} PropInst;
#define PIF_HIDDEN 1
#define MAX_PROPS  160
#define MAX_DYNPROPS 12

extern PropInst g_props[MAX_PROPS];
extern int g_numProps;
extern PropInst g_dynProps[MAX_DYNPROPS];   // rebuilt every frame (door leaves)
extern int g_numDynProps;
IWRAM_CODE void draw_prop(u8 *fb, const PropInst *pi, s32 f0, s32 r0);

#endif
