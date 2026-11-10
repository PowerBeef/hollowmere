// SPDX-License-Identifier: MIT
// Hollowmere engine shared declarations
#ifndef ENGINE_H
#define ENGINE_H
#include "gba.h"

#define VIEW_W   240          // columns (full horizontal resolution)
#define VIEW_CX  120          // screen centre column
// The 3D view is letterboxed: rows VIS0..VIS1-1 are shown, ROW0..ROW1-1 are
// rendered (a margin for head bob and shake). The eye line sits a little
// above the middle of the view, like looking slightly down.
#define ROW0      10
#define ROW1      138
#define VIS0      18          // (a top bar tall enough to hold the objective)
#define VIS1      134
#define HORIZON   68
#define VIEW_H    160
#define FOCAL     160         // px per tile at distance 1
#define COLK      160         // columns per tile at distance 1 (square pixels)
#define PLANE_Q14 12288       // camera plane half width 0.75 -> 74 deg FOV
#define WALL_H    2           // room height in tiles; the eye is at mid height
#define EYE_256   256         // eye height in 1/256 tile
#define NPAIR_C   29          // ceiling row pairs  (rows HORIZON-1 .. ROW0)
#define NPAIR_F   35          // floor row pairs    (rows HORIZON .. ROW1-1)
#define MAP_W    32
#define MAP_H    32
#define MAP_SHIFT 5
#define FIX      16
#define ONE      (1 << FIX)
#define NUM_LIGHT 32
#define NCONE    16
#define GRID_W   64            // light grid: 2 subcells per tile
#define MAX_DOORS 40
#define MAX_SPRITES 64
#define WTEX_H   128           // wall textures: 64 wide x 128 tall, column-major, in ROM

// Fixed EWRAM areas (kept out of the linker's way, see gba.ld):
// light grid at the start of EWRAM (bits 0-4 light, bits 5-6 floor material)
// and the floor/ceiling material bank (4 x 8KB, 32KB aligned) at the end.
#define LIGHTGRID_ADDR 0x02000000
#define FLATBANK_ADDR  0x02038000
#define g_lightgrid ((u8 *)LIGHTGRID_ADDR)
#define g_flatBank  ((u16 *)FLATBANK_ADDR)
#define LG_LIGHT  31
#define LG_MAT    0x60

// --------------------------------------------------------------- map
// Walls are thin: they lie on the edges between cells. Each cell stores the
// edge type of its west and north edges: g_edges[(y*32+x)*2 + {0:W, 1:N}].
// Edge type 0 is open; others index the level's EdgeType table.
enum { EK_WALL = 1, EK_DOOR, EK_ARCH };
typedef struct EdgeType_ {
    u16 tex[2];      // wall texture seen from the low side (west/north) / high side
    u16 alt[2];      // doors: closed-door surface per side
    u8  kind;        // EK_*
    u8  param;       // door index
    u8  panel;       // static frame width either side of the opening (1/64 tile)
    u8  lintel;      // opening height (1/32 tile); above it the wall continues
} EdgeType;

// ------------------------------------------------------------------ doors
// Doors sit in a wall edge. Closed, the edge shows a door-in-frame surface;
// opening, the opening becomes see-through (with the lintel above) and the
// leaf is drawn as a 3D slab swinging on its hinge into one of the rooms.
enum { DOOR_SINGLE = 0, DOOR_DOUBLE = 1 };
#define DOORH_SWINGHI 1            // swings into the cell on the high side
#define DOORH_HINGEHI 2            // single leaf hinged at the high end of the edge
typedef struct {
    u8  x, y;       // cell whose west (axis 0) or north (axis 1) edge holds the door
    u8  axis;       // 0: west edge (wall runs along Y); 1: north edge (wall runs along X)
    u8  kind;       // DOOR_SINGLE / DOOR_DOUBLE
    u16 open;       // 0 closed .. 0xFFFF fully open
    u16 leafTex;    // prop texture of the leaf faces
    u8  lock;       // 0 = unlocked, else required key id
    s8  moving;     // +1 opening, -1 closing
    u8  flags;
    u8  hinge;      // DOORH_*
    u8  edgeType;   // edge type index (frame textures, panel width, lintel)
    u8  pad;
    u16 holdTimer;
} Door;

// ---------------------------------------------------------------- camera
typedef struct {
    s32 x, y;           // 16.16 world position
    u16 angle;          // 0..65535
    s32 dirX, dirY;     // Q14
    s32 planeX, planeY; // Q14
    s32 bob;            // vertical bob in 1/256 px (applied by hardware scroll)
} Camera;

// --------------------------------------------------------------- sprites
// Sprite image: column-major "posts". Header then per-column offsets.
typedef struct SpriteImg_ {
    u8 w, h;            // texture size (w <= 64, h <= 128)
    u16 offs[];         // w offsets (bytes from start of struct) to column data
    // column data: [top u8][len u8][len pixels]... terminated by top=0xFF
} SpriteImg;

typedef struct {
    s32 x, y;           // 16.16
    const SpriteImg *img;
    u16 worldW;         // world width in 1/256 tile
    u16 worldH;         // world height in 1/256 tile
    s16 zoff;           // bottom height above floor in 1/256 tile
    u8  flags;          // SPR_*
    u8  lightBoost;
    s32 dist;           // filled by renderer
} RSprite;
#define SPR_FULLBRIGHT 1
#define SPR_HIDDEN     2
#define SPR_FLIPX      4
#define SPR_OWNLIGHT   8      // lightBoost is the light floor; the light grid is ignored

// ------------------------------------------------------------- globals
extern u8  g_edges[MAP_W * MAP_H * 2];
extern const EdgeType *g_edgeTypes;
extern const u8 *const walltex[];           // 64x128 column-major wall textures (ROM)
extern Door g_doors[MAX_DOORS];
extern int g_numDoors;
extern u8  g_colormap[8192];                // 32 light levels x 256 colours (VRAM, 3D view)
extern u8  g_colormapSrc[8192];             // its master copy (EWRAM)
typedef struct { s32 px64, py64; const u16 *tex; const u8 *cmap; } FlatCtx;
extern FlatCtx g_flatCtx;
extern u8  g_lightStatic[GRID_W * GRID_W];  // baked static light (+ material bits)
extern Camera g_cam;
extern RSprite g_sprites[MAX_SPRITES];
extern int g_numSprites;
extern s32 g_zbuf[VIEW_W];

// lighting control
extern u8  g_flashOn;          // flashlight on
extern s16 g_flashPower;       // 0..256 (battery / flicker scaled)
extern s16 g_ambientBoost;     // added to all light (lightning), 0..31
extern s16 g_minLight;         // night-vision floor

// renderer API (IWRAM)
IWRAM_CODE void render_view(u8 *fb);
void render_enter_3d(void);
void render_init(void);
void render_build_flash_tables(void);

// math
extern const s16 sin_lut[1024];
INLINE s32 lu_sin(u16 a) { return sin_lut[a >> 6]; }
INLINE s32 lu_cos(u16 a) { return sin_lut[((a >> 6) + 256) & 1023]; }
void camera_update(Camera *c);


#endif
