/* SPDX-License-Identifier: MIT */
/* Hollowmere GBA linker script. The Makefile runs it through the C
   preprocessor first, for the constants of limits.h. */
#include "limits.h"
OUTPUT_FORMAT("elf32-littlearm")
OUTPUT_ARCH(arm)
ENTRY(_start)

/* Fast RAM, from the bottom: IWRAM code and data, the renderer's and the
   mixer's variables, then the main stack growing down from __stack_top (the
   BIOS and the interrupt entry own the 128 bytes above it, see crt0.s).
   STACK_MIN is the deepest the stack has been measured (1,020 bytes in the
   test ROM, engine/tools/stackcheck.py) and 256 bytes over: code or data
   that would leave it less fails the link here, instead of the stack running
   into the renderer's tables at run time. */
__stack_top = 0x03007F80;
STACK_MIN   = 1280;

MEMORY {
    rom   : ORIGIN = 0x08000000, LENGTH = 32M
    iwram : ORIGIN = 0x03000000, LENGTH = 0x7F80 - 1280
    /* 0x02000000-0x02000FFF: light grid; 0x02038000-0x0203FFFF: floor material bank */
    ewram : ORIGIN = 0x02001000, LENGTH = 0x37000
}

/* Renderer tables kept in otherwise unused VRAM (16/32-bit writes only,
   reads as fast as IWRAM). The 3D view only draws rows 10..137 of a page and
   the cinema bars hide the rest, so rows 138..159 of page 0, the gap after
   it and rows 0..9 of page 1 form one free block (0x060081B0-0x0600A960);
   rows 138..159 of page 1 and the gap after it another (0x060121B0-
   0x06014000). Menu screens overwrite them: render_enter_3d() restores the
   colour map, everything else there is rebuilt every frame. The OBJ tiles
   past the HUD's (tile 800+) are never touched by menus. */
g_colormap  = 0x06008200;   /* 32 light levels x 256 colours -> 0x0600A200 */
g_vf        = 0x06012200;   /* prop vertices in camera space, 3 x 128 x s32 */
g_vr        = 0x06012400;
g_vz        = 0x06012600;
g_sx        = 0x06012800;   /* their projections */
g_sy        = 0x06012A00;
g_sw        = 0x06012C00;
g_vmark     = 0x06012E00;   /* u16 x 128: vertex used by this prop */
g_clipTop   = 0x06012F00;   /* s16 x 240: row below the nearest lintel */
g_clipDepth = 0x06013100;   /* s32 x 240: nearest lintel depth -> 0x060134C0 */
g_zmax8     = 0x06013500;   /* s32 x 30 per block of 8 columns: farthest wall */
g_zmin8     = 0x06013580;   /* nearest wall */
g_cdmin8    = 0x06013600;   /* nearest lintel clip depth -> 0x06013678 */
g_camX      = 0x06013680;   /* s16 x 240: camera-plane coordinate per column */
g_coneOf    = 0x06013860;   /* u8 x 240: flashlight cone class per column */
g_rowDist2  = 0x06013950;   /* u16 x 35: floor row pair distance -> 0x06013996 */
g_zbuf      = 0x060139A0;   /* s32 x 240: each column's wall distance -> 0x06013D60 */
g_polyPV    = 0x06013D60;   /* 8 x 20: a polygon's projected vertices -> 0x06013E00 */
g_rspan     = 0x06013E00;   /* 92: row rasterizer state -> 0x06013E5C */
g_faceKey   = 0x06013E60;   /* s16 x 64: a prop's face sort keys -> 0x06013EE0 */
g_voiceVol  = 0x06013EE0;   /* u32 x 16: the mixer's packed volumes per voice -> 0x06013F20 */
g_flatTbl   = 0x06016400;   /* 16 x 30 x u32 */
g_flatTblF  = 0x06016B80;   /* 16 x 7 x u32 */
g_ol        = 0x06016D40;   /* polygon outline buffers, 2880 bytes */
g_covT      = 0x06017880;   /* occluder spans: s16 x 240 */
g_covB      = 0x06017A60;
g_covF      = 0x06017C40;   /* s32 x 240 -> 0x06018000 */

/* The tables above are placed by hand for these sizes. A limit raised in
   limits.h without moving them fails here. */
ASSERT(g_colormap + NUM_LIGHT * 256 <= 0x0600A960, "gba.ld: g_colormap (NUM_LIGHT) runs out of its free block")
ASSERT(g_vf + 4 * MAX_MODEL_VERTS <= g_vr && g_vr + 4 * MAX_MODEL_VERTS <= g_vz && g_vz + 4 * MAX_MODEL_VERTS <= g_sx &&
       g_sx + 4 * MAX_MODEL_VERTS <= g_sy && g_sy + 4 * MAX_MODEL_VERTS <= g_sw && g_sw + 4 * MAX_MODEL_VERTS <= g_vmark &&
       g_vmark + 2 * MAX_MODEL_VERTS <= g_clipTop, "gba.ld: the vertex tables are placed for fewer vertices than MAX_MODEL_VERTS")
ASSERT(g_clipTop + 2 * VIEW_W <= g_clipDepth && g_clipDepth + 4 * VIEW_W <= g_zmax8 && g_zmax8 + 4 * (VIEW_W / 8) <= g_zmin8 &&
       g_zmin8 + 4 * (VIEW_W / 8) <= g_cdmin8 && g_cdmin8 + 4 * (VIEW_W / 8) <= g_camX && g_camX + 2 * VIEW_W <= g_coneOf &&
       g_coneOf + VIEW_W <= g_rowDist2 && g_zbuf + 4 * VIEW_W <= g_polyPV, "gba.ld: the per-column tables are placed for fewer columns than VIEW_W")
ASSERT(g_faceKey + 2 * MAX_MODEL_FACES <= g_voiceVol, "gba.ld: g_faceKey is placed for fewer faces than MAX_MODEL_FACES")
ASSERT(g_voiceVol + 4 * MAX_VOICES <= 0x06014000, "gba.ld: g_voiceVol (MAX_VOICES) runs into the OBJ tiles")
ASSERT(g_covT + 2 * VIEW_W <= g_covB && g_covB + 2 * VIEW_W <= g_covF && g_covF + 4 * VIEW_W <= 0x06018000,
       "gba.ld: the occluder tables are placed for fewer columns than VIEW_W")

SECTIONS
{
    .text : {
        KEEP(*(.crt0))
        EXCLUDE_FILE(*iwram.o) *(.text .text.*)
        *(.romcode .romcode.*)
        *(.gnu.linkonce.t.*)
        . = ALIGN(4);
    } > rom

    .rodata : {
        EXCLUDE_FILE(*iwram.o) *(.rodata .rodata.*)
        *(.gnu.linkonce.r.*)
        . = ALIGN(4);
    } > rom

    .ARM.exidx : { *(.ARM.exidx*) } > rom

    __iwram_lma = ALIGN(4);
    .iwram : AT(__iwram_lma) {
        __iwram_start = .;
        *(.iwram .iwram.*)
        *iwram.o(.text .text.* .rodata .rodata.*)
        *(.data .data.*)
        . = ALIGN(4);
        __iwram_end = .;
    } > iwram

    /* Fast RAM is for code, the renderer's and mixer's own variables and the
       stack: only the .bss of the *.iwram.c files stays here. Everything
       else (the game's and the Thumb code's variables) goes to EWRAM below;
       that code runs from ROM and does not notice. */
    .bss (NOLOAD) : {
        __bss_start = .;
        *iwram.o(.bss .bss.*)
        *iwram.o(COMMON)
        . = ALIGN(4);
        __bss_end = .;
    } > iwram
    ASSERT(__bss_end + STACK_MIN <= __stack_top, "fast RAM is full: under STACK_MIN bytes are left for the stack (move code or data out of the *.iwram.c files)")

    __ewram_lma = __iwram_lma + SIZEOF(.iwram);
    .ewram : AT(__ewram_lma) {
        __ewram_start = .;
        *(.ewram .ewram.*)
        . = ALIGN(4);
        __ewram_end = .;
    } > ewram

    .sbss (NOLOAD) : {
        __sbss_start = .;
        *(.sbss .sbss.*)
        *(.bss .bss.*)
        *(COMMON)
        . = ALIGN(4);
        __sbss_end = .;
    } > ewram

    __rom_end = __ewram_lma + SIZEOF(.ewram);

    /DISCARD/ : { *(.comment) *(.note*) *(.ARM.attributes) }
}
