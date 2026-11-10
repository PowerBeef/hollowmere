/* SPDX-License-Identifier: MIT */
/* Hollowmere GBA linker script */
OUTPUT_FORMAT("elf32-littlearm")
OUTPUT_ARCH(arm)
ENTRY(_start)

MEMORY {
    rom   : ORIGIN = 0x08000000, LENGTH = 32M
    iwram : ORIGIN = 0x03000000, LENGTH = 32K - 0x400
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
g_flatTbl   = 0x06016400;   /* 16 x 30 x u32 */
g_flatTblF  = 0x06016B80;   /* 16 x 7 x u32 */
g_ol        = 0x06016D40;   /* polygon outline buffers, 2880 bytes */
g_covT      = 0x06017880;   /* occluder spans: s16 x 240 */
g_covB      = 0x06017A60;
g_covF      = 0x06017C40;   /* s32 x 240 -> 0x06018000 */

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

    .bss (NOLOAD) : {
        __bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        . = ALIGN(4);
        __bss_end = .;
    } > iwram

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
        . = ALIGN(4);
        __sbss_end = .;
    } > ewram

    __rom_end = __ewram_lma + SIZEOF(.ewram);

    /DISCARD/ : { *(.comment) *(.note*) *(.ARM.attributes) }
}
