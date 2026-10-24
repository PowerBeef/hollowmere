@ Hollowmere hand-written ARM inner loops (IWRAM)
@
@ The 3D view is a mode-4 page (240 x 160 bytes, 16-bit writes only). The
@ renderer works on column pairs: one halfword holds the pixels of columns
@ 2k (low byte) and 2k+1 (high byte) of a row. Floors and ceilings are
@ sampled once per 2x2 pixels; walls and props at full resolution, the two
@ columns of a pair drawn together with their own texture coordinates, and
@ rows that only one of them covers merged with the pixel already there.
    .section .iwram, "ax", %progbits
    .arm
    .align 2

@ debug pixel counters (make DEFS=-DPIXCNT): g_pixCnt at 0x02037000
.macro PCNT slot, reg
#ifdef PIXCNT
    stmfd   sp!, {r0-r2}
    mov     r2, \reg
    mov     r0, #0x02000000
    orr     r0, r0, #0x37000
    ldr     r1, [r0, #(\slot*4)]
    add     r1, r1, r2
    str     r1, [r0, #(\slot*4)]
    ldmfd   sp!, {r0-r2}
#endif
.endm
.macro PCNTI slot, imm
#ifdef PIXCNT
    stmfd   sp!, {r0-r2}
    mov     r2, #\imm
    mov     r0, #0x02000000
    orr     r0, r0, #0x37000
    ldr     r1, [r0, #(\slot*4)]
    add     r1, r1, r2
    str     r1, [r0, #(\slot*4)]
    ldmfd   sp!, {r0-r2}
#endif
.endm


    .equ LIGHTGRID, 0x02000000
    .equ ROW0, 10
    .equ ROW1, 138
    .equ HORIZON, 68
    .equ WT_CM0, 0
    .equ WT_CM1, 8192
    .equ WT_CM2, 10240
    .equ WT_CM3, 10752

@ ---------------------------------------------------------------------------
@ void flat_column(u16 *pf, u16 *pc, const u32 *tbl, const FlatCtx *ctx,
@                  s32 rdx, s32 rdy)
@   tbl: per row-pair words: d<<16 | lc<<8 | lf, terminated by a 0 word
@   ctx: { s32 px64, py64; const u16 *bank; const u8 *cmap; }
@        bank: 4 interleaved floor|ceil<<8 64x64 textures, 32KB aligned;
@        the light grid byte (at LIGHTGRID) selects one with bits 5-6
@ Writes floor rows downward from pf and ceiling rows upward from pc,
@ two rows per sample (half vertical resolution).
@ ---------------------------------------------------------------------------
    .global flat_column
    .type flat_column, %function
flat_column:
#ifdef PIXCNT
    stmfd   sp!, {r0, r1}
    mov     r0, #0x02000000
    orr     r0, r0, #0x37000
    str     r2, [r0, #60]
    ldmfd   sp!, {r0, r1}
#endif
    stmfd   sp!, {r4-r11, lr}
    ldr     r4, [sp, #36]           @ rdx
    ldr     r5, [sp, #40]           @ rdy
    mov     r12, r3
    mov     r3, r4                  @ r3 = rdx
    mov     r4, r5                  @ r4 = rdy
    ldmia   r12, {r5, r6, r7, r8}   @ px64, py64, bank, cmap
1:
    @ ---- pair A (samples the light grid for A and B)
    ldr     r9, [r2], #4            @ w = d<<16 | lc<<8 | lf
    movs    r11, r9, lsr #16        @ d
    beq     2f
    mla     r12, r11, r4, r6        @ fy (2^-22 tiles)
    mla     r11, r3, r11, r5        @ fx (Rd != Rm on ARMv4)
    and     r10, r12, #0x07E00000
    mov     r10, r10, lsr #15
    and     lr, r11, #0x07E00000
    orr     r10, r10, lr, lsr #21
    orr     r10, r10, #LIGHTGRID
    ldrb    r10, [r10]              @ g = light | material << 5
    and     lr, r10, #0x60
    bic     r7, r7, #0x6000
    orr     r7, r7, lr, lsl #8      @ material texture
    and     r10, r10, #31
    and     r12, r12, #0x003F0000
    mov     r12, r12, lsr #9
    and     r11, r11, #0x003F0000
    orr     r12, r12, r11, lsr #15
    ldrh    r12, [r7, r12]          @ floor | ceil<<8 texels
    and     r11, r9, #0xFF
    cmp     r11, r10
    movlt   r11, r10
    and     lr, r12, #0xFF
    add     lr, lr, r11, lsl #8
    ldrb    lr, [r8, lr]
    orr     lr, lr, lr, lsl #8
    strh    lr, [r0], #240
    strh    lr, [r0], #240
    and     r11, r9, #0xFF00
    cmp     r11, r10, lsl #8
    movlt   r11, r10, lsl #8
    add     r11, r11, r12, lsr #8
    ldrb    r11, [r8, r11]
    orr     r11, r11, r11, lsl #8
    strh    r11, [r1], #-240
    strh    r11, [r1], #-240
    @ ---- pair B (reuses g and the material)
    ldr     r9, [r2], #4
    movs    r11, r9, lsr #16
    beq     2f
    mla     r12, r11, r4, r6
    mla     r11, r3, r11, r5
    and     r12, r12, #0x003F0000
    mov     r12, r12, lsr #9
    and     r11, r11, #0x003F0000
    orr     r12, r12, r11, lsr #15
    ldrh    r12, [r7, r12]
    and     r11, r9, #0xFF
    cmp     r11, r10
    movlt   r11, r10
    and     lr, r12, #0xFF
    add     lr, lr, r11, lsl #8
    ldrb    lr, [r8, lr]
    orr     lr, lr, lr, lsl #8
    strh    lr, [r0], #240
    strh    lr, [r0], #240
    and     r11, r9, #0xFF00
    cmp     r11, r10, lsl #8
    movlt   r11, r10, lsl #8
    add     r11, r11, r12, lsr #8
    ldrb    r11, [r8, r11]
    orr     r11, r11, r11, lsl #8
    strh    r11, [r1], #-240
    strh    r11, [r1], #-240
    b       1b
2:
#ifdef PIXCNT
    mov     r4, #0x02000000
    orr     r4, r4, #0x37000
    ldr     r5, [r4, #60]
    sub     r5, r2, r5
    mov     r5, r5, lsr #2
    sub     r5, r5, #1
    mov     r5, r5, lsl #3
    ldr     r6, [r4, #24]
    add     r6, r6, r5
    str     r6, [r4, #24]
#endif
    ldmfd   sp!, {r4-r11, lr}
    bx      lr

@ ---------------------------------------------------------------------------
@ void flat_floor(u16 *pf, const u32 *tbl, const FlatCtx *ctx, s32 rdx, s32 rdy)
@   floor-only variant for the rows below the last ceiling pair
@ ---------------------------------------------------------------------------
    .global flat_floor
    .type flat_floor, %function
flat_floor:
#ifdef PIXCNT
    stmfd   sp!, {r0, r1}
    mov     r0, #0x02000000
    orr     r0, r0, #0x37000
    str     r1, [r0, #60]
    ldmfd   sp!, {r0, r1}
#endif
    stmfd   sp!, {r4-r11, lr}
    ldr     r4, [sp, #36]           @ rdy
    mov     r12, r2
    mov     r2, r1                  @ r2 = tbl
    ldmia   r12, {r5, r6, r7, r8}
3:
    ldr     r9, [r2], #4
    movs    r11, r9, lsr #16
    beq     4f
    mla     r12, r11, r4, r6
    mla     r11, r3, r11, r5
    and     r10, r12, #0x07E00000
    mov     r10, r10, lsr #15
    and     lr, r11, #0x07E00000
    orr     r10, r10, lr, lsr #21
    orr     r10, r10, #LIGHTGRID
    ldrb    r10, [r10]
    and     lr, r10, #0x60
    bic     r7, r7, #0x6000
    orr     r7, r7, lr, lsl #8
    and     r10, r10, #31
    and     r12, r12, #0x003F0000
    mov     r12, r12, lsr #9
    and     r11, r11, #0x003F0000
    orr     r12, r12, r11, lsr #15
    ldrh    r12, [r7, r12]
    and     r11, r9, #0xFF
    cmp     r11, r10
    movlt   r11, r10
    and     lr, r12, #0xFF
    add     lr, lr, r11, lsl #8
    ldrb    lr, [r8, lr]
    orr     lr, lr, lr, lsl #8
    strh    lr, [r0], #240
    strh    lr, [r0], #240
    b       3b
4:
#ifdef PIXCNT
    mov     r4, #0x02000000
    orr     r4, r4, #0x37000
    ldr     r5, [r4, #60]
    sub     r5, r2, r5
    mov     r5, r5, lsr #2
    sub     r5, r5, #1
    mov     r5, r5, lsl #2
    ldr     r6, [r4, #24]
    add     r6, r6, r5
    str     r6, [r4, #24]
#endif
    ldmfd   sp!, {r4-r11, lr}
    bx      lr

@ four-column versions (one sample per 4x2 pixels, for the far floor):
@ 32-bit stores, the destinations must be 4-byte aligned
    .global flat_column2
    .type flat_column2, %function
flat_column2:
#ifdef PIXCNT
    stmfd   sp!, {r0, r1}
    mov     r0, #0x02000000
    orr     r0, r0, #0x37000
    str     r2, [r0, #60]
    ldmfd   sp!, {r0, r1}
#endif
    stmfd   sp!, {r4-r11, lr}
    ldr     r4, [sp, #36]           @ rdx
    ldr     r5, [sp, #40]           @ rdy
    mov     r12, r3
    mov     r3, r4                  @ r3 = rdx
    mov     r4, r5                  @ r4 = rdy
    ldmia   r12, {r5, r6, r7, r8}   @ px64, py64, bank, cmap
1:
    @ ---- pair A (samples the light grid for A and B)
    ldr     r9, [r2], #4            @ w = d<<16 | lc<<8 | lf
    movs    r11, r9, lsr #16        @ d
    beq     2f
    mla     r12, r11, r4, r6        @ fy (2^-22 tiles)
    mla     r11, r3, r11, r5        @ fx (Rd != Rm on ARMv4)
    and     r10, r12, #0x07E00000
    mov     r10, r10, lsr #15
    and     lr, r11, #0x07E00000
    orr     r10, r10, lr, lsr #21
    orr     r10, r10, #LIGHTGRID
    ldrb    r10, [r10]              @ g = light | material << 5
    and     lr, r10, #0x60
    bic     r7, r7, #0x6000
    orr     r7, r7, lr, lsl #8      @ material texture
    and     r10, r10, #31
    and     r12, r12, #0x003F0000
    mov     r12, r12, lsr #9
    and     r11, r11, #0x003F0000
    orr     r12, r12, r11, lsr #15
    ldrh    r12, [r7, r12]          @ floor | ceil<<8 texels
    and     r11, r9, #0xFF
    cmp     r11, r10
    movlt   r11, r10
    and     lr, r12, #0xFF
    add     lr, lr, r11, lsl #8
    ldrb    lr, [r8, lr]
    orr     lr, lr, lr, lsl #8
    orr     lr, lr, lr, lsl #16
    str     lr, [r0], #240
    str     lr, [r0], #240
    and     r11, r9, #0xFF00
    cmp     r11, r10, lsl #8
    movlt   r11, r10, lsl #8
    add     r11, r11, r12, lsr #8
    ldrb    r11, [r8, r11]
    orr     r11, r11, r11, lsl #8
    orr     r11, r11, r11, lsl #16
    str     r11, [r1], #-240
    str     r11, [r1], #-240
    @ ---- pair B (reuses g and the material)
    ldr     r9, [r2], #4
    movs    r11, r9, lsr #16
    beq     2f
    mla     r12, r11, r4, r6
    mla     r11, r3, r11, r5
    and     r12, r12, #0x003F0000
    mov     r12, r12, lsr #9
    and     r11, r11, #0x003F0000
    orr     r12, r12, r11, lsr #15
    ldrh    r12, [r7, r12]
    and     r11, r9, #0xFF
    cmp     r11, r10
    movlt   r11, r10
    and     lr, r12, #0xFF
    add     lr, lr, r11, lsl #8
    ldrb    lr, [r8, lr]
    orr     lr, lr, lr, lsl #8
    orr     lr, lr, lr, lsl #16
    str     lr, [r0], #240
    str     lr, [r0], #240
    and     r11, r9, #0xFF00
    cmp     r11, r10, lsl #8
    movlt   r11, r10, lsl #8
    add     r11, r11, r12, lsr #8
    ldrb    r11, [r8, r11]
    orr     r11, r11, r11, lsl #8
    orr     r11, r11, r11, lsl #16
    str     r11, [r1], #-240
    str     r11, [r1], #-240
    b       1b
2:
#ifdef PIXCNT
    mov     r4, #0x02000000
    orr     r4, r4, #0x37000
    ldr     r5, [r4, #60]
    sub     r5, r2, r5
    mov     r5, r5, lsr #2
    sub     r5, r5, #1
    mov     r5, r5, lsl #4
    ldr     r6, [r4, #24]
    add     r6, r6, r5
    str     r6, [r4, #24]
#endif
    ldmfd   sp!, {r4-r11, lr}
    bx      lr

@ ---------------------------------------------------------------------------
@ void flat_floor2(u8 *pf, const u32 *tbl, const FlatCtx *ctx, s32 rdx, s32 rdy)
@   floor-only variant for the rows below the last ceiling pair
@ ---------------------------------------------------------------------------
    .global flat_floor2
    .type flat_floor2, %function
flat_floor2:
#ifdef PIXCNT
    stmfd   sp!, {r0, r1}
    mov     r0, #0x02000000
    orr     r0, r0, #0x37000
    str     r1, [r0, #60]
    ldmfd   sp!, {r0, r1}
#endif
    stmfd   sp!, {r4-r11, lr}
    ldr     r4, [sp, #36]           @ rdy
    mov     r12, r2
    mov     r2, r1                  @ r2 = tbl
    ldmia   r12, {r5, r6, r7, r8}
3:
    ldr     r9, [r2], #4
    movs    r11, r9, lsr #16
    beq     4f
    mla     r12, r11, r4, r6
    mla     r11, r3, r11, r5
    and     r10, r12, #0x07E00000
    mov     r10, r10, lsr #15
    and     lr, r11, #0x07E00000
    orr     r10, r10, lr, lsr #21
    orr     r10, r10, #LIGHTGRID
    ldrb    r10, [r10]
    and     lr, r10, #0x60
    bic     r7, r7, #0x6000
    orr     r7, r7, lr, lsl #8
    and     r10, r10, #31
    and     r12, r12, #0x003F0000
    mov     r12, r12, lsr #9
    and     r11, r11, #0x003F0000
    orr     r12, r12, r11, lsr #15
    ldrh    r12, [r7, r12]
    and     r11, r9, #0xFF
    cmp     r11, r10
    movlt   r11, r10
    and     lr, r12, #0xFF
    add     lr, lr, r11, lsl #8
    ldrb    lr, [r8, lr]
    orr     lr, lr, lr, lsl #8
    orr     lr, lr, lr, lsl #16
    str     lr, [r0], #240
    str     lr, [r0], #240
    b       3b
4:
#ifdef PIXCNT
    mov     r4, #0x02000000
    orr     r4, r4, #0x37000
    ldr     r5, [r4, #60]
    sub     r5, r2, r5
    mov     r5, r5, lsr #2
    sub     r5, r5, #1
    mov     r5, r5, lsl #3
    ldr     r6, [r4, #24]
    add     r6, r6, r5
    str     r6, [r4, #24]
#endif
    ldmfd   sp!, {r4-r11, lr}
    bx      lr

@ ---------------------------------------------------------------------------
@ void wall_column(u16 *p, const u8 *texcol, const u8 *cmap, u32 tp, u32 step, int n)
@   draws n pixels downward (stride 240 bytes)
@ ---------------------------------------------------------------------------
    .global wall_column
    .type wall_column, %function
wall_column:
    stmfd   sp!, {r4-r7, lr}
    ldr     r4, [sp, #20]           @ step
    ldr     r5, [sp, #24]           @ n
#ifdef PIXCNT
    mov     r6, r5, lsl #1
    PCNT    2, r6
#endif
    subs    r5, r5, #4
    blt     6f
5:
    ldrb    r6, [r1, r3, lsr #16]
    add     r3, r3, r4
    ldrb    r7, [r1, r3, lsr #16]
    add     r3, r3, r4
    ldrb    r6, [r2, r6]
    ldrb    r7, [r2, r7]
    orr     r6, r6, r6, lsl #8
    orr     r7, r7, r7, lsl #8
    strh    r6, [r0], #240
    strh    r7, [r0], #240
    ldrb    r6, [r1, r3, lsr #16]
    add     r3, r3, r4
    ldrb    r7, [r1, r3, lsr #16]
    add     r3, r3, r4
    ldrb    r6, [r2, r6]
    ldrb    r7, [r2, r7]
    orr     r6, r6, r6, lsl #8
    orr     r7, r7, r7, lsl #8
    strh    r6, [r0], #240
    strh    r7, [r0], #240
    subs    r5, r5, #4
    bge     5b
6:
    adds    r5, r5, #4
    beq     8f
7:
    ldrb    r6, [r1, r3, lsr #16]
    add     r3, r3, r4
    ldrb    r6, [r2, r6]
    orr     r6, r6, r6, lsl #8
    strh    r6, [r0], #240
    subs    r5, r5, #1
    bne     7b
8:
    ldmfd   sp!, {r4-r7, lr}
    bx      lr

@ ---------------------------------------------------------------------------
@ void wall_column2(u16 *p, const u8 *texcol, const u8 *cmap, u32 tp, u32 step, int n)
@   magnified walls (<= 0.67 texel per row): one sample per two rows
@   (step is per row; tp is sampled at the first row of each pair)
@ ---------------------------------------------------------------------------
    .global wall_column2
    .type wall_column2, %function
wall_column2:
    stmfd   sp!, {r4-r7, lr}
    ldr     r4, [sp, #20]           @ step
    ldr     r5, [sp, #24]           @ n
#ifdef PIXCNT
    mov     r6, r5, lsl #1
    PCNT    2, r6
#endif
    add     r3, r3, r4, lsr #1      @ sample between the two rows
    mov     r4, r4, lsl #1          @ per pair
    subs    r5, r5, #4
    blt     2f
1:  ldrb    r6, [r1, r3, lsr #16]
    add     r3, r3, r4
    ldrb    r7, [r1, r3, lsr #16]
    add     r3, r3, r4
    ldrb    r6, [r2, r6]
    ldrb    r7, [r2, r7]
    orr     r6, r6, r6, lsl #8
    orr     r7, r7, r7, lsl #8
    strh    r6, [r0], #240
    strh    r6, [r0], #240
    strh    r7, [r0], #240
    strh    r7, [r0], #240
    subs    r5, r5, #4
    bge     1b
2:  adds    r5, r5, #4
    beq     4f
3:  ldrb    r6, [r1, r3, lsr #16]
    add     r3, r3, r4
    ldrb    r6, [r2, r6]
    orr     r6, r6, r6, lsl #8
    strh    r6, [r0], #240
    subs    r5, r5, #1
    beq     4f
    strh    r6, [r0], #240
    subs    r5, r5, #1
    bne     3b
4:  ldmfd   sp!, {r4-r7, lr}
    bx      lr

@ ---------------------------------------------------------------------------
@ void col_pair(ColPair *s)   two columns of textured rows (stride 240)
@  0 p (pair address at row 0, even)
@  4 a0  8 b0  12 a1  16 b1   rows [a0, a1) of column A (low byte) and
@                             [b0, b1) of column B (high byte); empty if x0 >= x1
@ 20 texA 24 texB   texture columns
@ 28 cmA  32 cmB    colour maps
@ 36 tpA  40 tpB    16.16 texel position at row a0 / b0
@ 44 stA  48 stB    16.16 texels per row
@ (every A field is followed by its B field, 4 bytes on)
@ Rows covered by both columns are written as whole halfwords, rows covered
@ by one column keep the other byte. Fields 4..12 are used as scratch.
@ ---------------------------------------------------------------------------
.macro ROW_A                        @ column A only: keep B's pixel
    ldrb    r10, [r1, r5, lsr #16]
    add     r5, r5, r7
    ldrb    r10, [r3, r10]
    ldrb    r11, [r0, #1]
    orr     r10, r10, r11, lsl #8
    strh    r10, [r0], #240
.endm
.macro ROW_B                        @ column B only: keep A's pixel
    ldrb    r10, [r2, r6, lsr #16]
    add     r6, r6, r8
    ldrb    r10, [r4, r10]
    ldrb    r11, [r0]
    orr     r10, r11, r10, lsl #8
    strh    r10, [r0], #240
.endm
.macro ROW_AB
    ldrb    r10, [r1, r5, lsr #16]
    add     r5, r5, r7
    ldrb    r11, [r2, r6, lsr #16]
    add     r6, r6, r8
    ldrb    r10, [r3, r10]
    ldrb    r11, [r4, r11]
    orr     r10, r10, r11, lsl #8
    strh    r10, [r0], #240
.endm

    .global col_pair, col_pair_p
    .type col_pair, %function
col_pair_p:                         @ (profiling alias used by props)
col_pair:
    stmfd   sp!, {r4-r11, lr}
#ifdef PIXCNT
    ldr     r4, [r0, #4]
    ldr     r5, [r0, #12]
    subs    r5, r5, r4
    movlt   r5, #0
    ldr     r4, [r0, #8]
    ldr     r6, [r0, #16]
    subs    r6, r6, r4
    movlt   r6, #0
    add     r5, r5, r6
    PCNT    0, r5
#endif
    mov     r12, r0
    add     lr, r12, #20
    ldmia   lr, {r1-r8}             @ texA texB cmA cmB tpA tpB stA stB
    ldr     r9, [r12, #4]           @ a0
    ldr     r10, [r12, #12]         @ a1
    cmp     r9, r10
    bge     .Lcp_b_only
    ldr     r11, [r12, #8]          @ b0
    ldr     lr, [r12, #16]          @ b1
    cmp     r11, lr
    bge     .Lcp_a_only
    @ top = max(a0, b0); end = min(a1, b1)
    cmp     r9, r11
    movge   r0, r9
    movlt   r0, r11                 @ r0 = top
    sub     r10, r10, lr            @ dbot = a1 - b1 (> 0: A goes on below B)
    cmp     r10, #0
    addle   lr, lr, r10             @ lr = end
    sub     lr, lr, r0              @ common rows
    cmp     lr, #0
    ble     .Lcp_apart
    sub     r11, r11, r9            @ dtop = b0 - a0 (> 0: A starts above B)
    str     r11, [r12, #4]
    str     lr, [r12, #8]
    str     r10, [r12, #12]
    cmp     r11, #0
    subgt   r0, r0, r11
    addlt   r0, r0, r11             @ first row = min(a0, b0)
    rsb     r9, r0, r0, lsl #4
    ldr     r0, [r12]
    add     r0, r0, r9, lsl #4      @ p
    ldr     r9, [r12, #4]
    cmp     r9, #0
    bgt     10f
    blt     11f
    b       12f
10: bl      .Lcp_rows_a
    b       12f
11: rsb     r9, r9, #0
    bl      .Lcp_rows_b
12: ldr     r9, [r12, #8]
    ldr     r10, [r12, #56]         @ pmode
    cmp     r10, #0
    bne     15f
    bl      .Lcp_rows_ab
    b       16f
15: bl      .Lcp_rows_pr
16:
    ldr     r9, [r12, #12]
    cmp     r9, #0
    bgt     13f
    blt     14f
    b       .Lcp_end
13: bl      .Lcp_rows_a
    b       .Lcp_end
14: rsb     r9, r9, #0
    bl      .Lcp_rows_b
    b       .Lcp_end
.Lcp_apart:                         @ no common rows: one column, then the other
    ldr     r10, [r12, #12]
.Lcp_a_only:                        @ r9 = a0, r10 = a1 (non-empty)
    rsb     r11, r9, r9, lsl #4
    ldr     r0, [r12]
    add     r0, r0, r11, lsl #4
    sub     r9, r10, r9
    bl      .Lcp_rows_a
.Lcp_b_only:
    ldr     r9, [r12, #8]
    ldr     r10, [r12, #16]
    subs    r10, r10, r9
    ble     .Lcp_end
    rsb     r11, r9, r9, lsl #4
    ldr     r0, [r12]
    add     r0, r0, r11, lsl #4
    mov     r9, r10
    bl      .Lcp_rows_b
.Lcp_end:
    ldmfd   sp!, {r4-r11, lr}
    bx      lr

.Lcp_rows_a:                        @ r9 >= 1 rows
    ROW_A
    subs    r9, r9, #1
    bne     .Lcp_rows_a
    bx      lr
.Lcp_rows_b:
    ROW_B
    subs    r9, r9, #1
    bne     .Lcp_rows_b
    bx      lr
@ rows both columns cover, both texels from one 16-bit read of the pair
@ layout (ptex) at A's texture position; r10 = pmode
.macro PAIR1                        @ A low byte, B high byte
    mov     r11, r5, lsr #16
    add     r11, r2, r11, lsl #1
    ldrh    r11, [r11]
    add     r5, r5, r7
    and     r10, r11, #0xFF
    ldrb    r10, [r3, r10]
    ldrb    r11, [r4, r11, lsr #8]
    orr     r10, r10, r11, lsl #8
    strh    r10, [r0], #240
.endm
.macro PAIR2                        @ A high byte, B low byte
    mov     r11, r5, lsr #16
    add     r11, r2, r11, lsl #1
    ldrh    r11, [r11]
    add     r5, r5, r7
    and     r10, r11, #0xFF
    ldrb    r10, [r4, r10]
    ldrb    r11, [r3, r11, lsr #8]
    orr     r10, r11, r10, lsl #8
    strh    r10, [r0], #240
.endm
.Lcp_rows_pr:
#ifdef PIXCNT
    mov     r11, r9, lsl #1
    PCNT    8, r11
#endif
    mla     r6, r9, r8, r6          @ B's position after these rows
    cmp     r10, #3
    beq     30f
    ldr     r2, [r12, #52]          @ ptex (texB is reloaded after)
    cmp     r10, #1
    bne     20f
    tst     r9, #1
    beq     2f
    PAIR1
    subs    r9, r9, #1
    beq     29f
2:  PAIR1
    PAIR1
    subs    r9, r9, #2
    bne     2b
    b       29f
20: tst     r9, #1
    beq     3f
    PAIR2
    subs    r9, r9, #1
    beq     29f
3:  PAIR2
    PAIR2
    subs    r9, r9, #2
    bne     3b
29: ldr     r2, [r12, #24]
    bx      lr
    @ pmode 3: both columns show column A's texel (one sample per pixel pair,
    @ each column lit by its own colormap)
30: cmp     r3, r4
    bne     32f
31: ldrb    r10, [r1, r5, lsr #16]
    add     r5, r5, r7
    ldrb    r10, [r3, r10]
    orr     r10, r10, r10, lsl #8
    strh    r10, [r0], #240
    subs    r9, r9, #1
    bne     31b
    bx      lr
32: ldrb    r10, [r1, r5, lsr #16]
    add     r5, r5, r7
    ldrb    r11, [r4, r10]
    ldrb    r10, [r3, r10]
    orr     r10, r10, r11, lsl #8
    strh    r10, [r0], #240
    subs    r9, r9, #1
    bne     32b
    bx      lr

.Lcp_rows_ab:
    tst     r9, #1
    beq     2f
    ROW_AB
    subs    r9, r9, #1
    bxeq    lr
2:  ROW_AB
    ROW_AB
    subs    r9, r9, #2
    bne     2b
    bx      lr

@ ---------------------------------------------------------------------------
@ void wall_pair(u8 *fb, int col, const ColHit *ha, const ColHit *hb)
@   the walls of the column pair col, col + 1 (col even):
@   - texture level from the texel density down the wall and, for two
@     columns on the same plain wall, across it
@   - the same texel column with (nearly) the same rows and scale, or a far
@     wall / outside the full-resolution band: one sample per halfword
@   - otherwise col_pair, the rows both columns cover read with one 16-bit
@     access of the pair layout when their texel columns are neighbours
@   - the rows a big prop face in front will paint over are skipped
@ ColHit: 0 dist  4 lh  8 tcol  12 light (u8)  36 key  40 tex  44 f (u16)
@ ---------------------------------------------------------------------------
    .equ WP_FB, 60
    .equ WP_COL, 64
    .equ WP_TOPA, 68
    .equ WP_TOPB, 72
    .equ WP_STEPA, 76
    .equ WP_STEPB, 80
    .equ WP_TA, 84
    .equ WP_BA, 88
    .equ WP_TB, 92
    .equ WP_BB, 96
    .equ WP_M, 100
    .equ WP_Y0A, 104
    .equ WP_Y1A, 108
    .equ WP_Y0B, 112
    .equ WP_Y1B, 116
    .equ WP_TI, 120             @ rows hidden in both columns (one sample per halfword)
    .equ WP_BI, 124
    .equ WP_SIZE, 128

@ the span of one column: \h ColHit -> top, y0, y1, step (mip 0)
.macro WSPAN h, top, y0, y1, step, t0, t1
    ldr     \t0, [\h, #4]           @ lh
    mov     \top, \t0, lsr #1
    rsb     \top, \top, #HORIZON
    add     \y1, \top, \t0
    cmp     \top, #ROW0
    movlt   \y0, #ROW0
    movge   \y0, \top
    cmp     \y1, #ROW1
    movgt   \y1, #ROW1
    ldr     \t0, [\h]               @ dist
    ldr     \t1, =26214
    umull   \step, \t1, \t0, \t1    @ 0.4 * dist: 128 texels over lh rows
    mov     \step, \step, lsr #16
    orr     \step, \step, \t1, lsl #16
.endm

    .global wall_pair
    .type wall_pair, %function
wall_pair:
    stmfd   sp!, {r4-r11, lr}
    sub     sp, sp, #WP_SIZE
    str     r0, [sp, #WP_FB]
    str     r1, [sp, #WP_COL]
    mov     r10, r2
    mov     r11, r3
    WSPAN   r10, r4, r5, r6, r7, r0, r1
    str     r4, [sp, #WP_TOPA]
    str     r5, [sp, #WP_Y0A]
    str     r6, [sp, #WP_Y1A]
    str     r7, [sp, #WP_STEPA]
    WSPAN   r11, r4, r5, r6, r8, r0, r1
    str     r4, [sp, #WP_TOPB]
    str     r5, [sp, #WP_Y0B]
    str     r6, [sp, #WP_Y1B]
    str     r8, [sp, #WP_STEPB]
    @ rows big prop faces in front of each wall will cover
    ldr     r1, [sp, #WP_COL]
    ldr     r12, =g_covF
    ldr     r2, [r12, r1, lsl #2]
    ldr     r0, [r10]
    mov     r3, #ROW1
    mov     r4, #ROW1
    cmp     r2, r0
    bge     1f
    ldr     r12, =g_covT
    mov     r9, r1, lsl #1
    ldrsh   r3, [r12, r9]
    ldr     r12, =g_covB
    ldrsh   r4, [r12, r9]
1:  str     r3, [sp, #WP_TA]
    str     r4, [sp, #WP_BA]
    add     r1, r1, #1
    ldr     r12, =g_covF
    ldr     r2, [r12, r1, lsl #2]
    ldr     r0, [r11]
    mov     r3, #ROW1
    mov     r4, #ROW1
    cmp     r2, r0
    bge     2f
    ldr     r12, =g_covT
    mov     r9, r1, lsl #1
    ldrsh   r3, [r12, r9]
    ldr     r12, =g_covB
    ldrsh   r4, [r12, r9]
2:  str     r3, [sp, #WP_TB]
    str     r4, [sp, #WP_BB]
    ldr     r1, [sp, #WP_TA]        @ the rows hidden in both columns
    cmp     r3, r1
    movlt   r3, r1
    ldr     r1, [sp, #WP_BA]
    cmp     r4, r1
    movgt   r4, r1
    cmp     r3, r4
    movge   r3, #ROW1
    movge   r4, #ROW1
    str     r3, [sp, #WP_TI]
    str     r4, [sp, #WP_BI]
    @ texture level: r0 = density, r9 = both columns on the same plain wall
    cmp     r7, r8
    movge   r0, r7
    movlt   r0, r8
    mov     r9, #0
    ldr     r2, [r10, #36]
    cmp     r2, #0
    beq     3f
    ldr     r3, [r11, #36]
    cmp     r2, r3
    bne     3f
    mov     r9, #1
    ldrh    r2, [r10, #44]
    ldrh    r3, [r11, #44]
    subs    r2, r3, r2
    rsbmi   r2, r2, #0
    mov     r2, r2, lsl #6          @ 1024 per texel along the edge -> 16.16
    cmp     r2, r0
    movgt   r0, r2
3:  mov     r8, #0
    ldr     r1, =0x16A0A
    cmp     r0, r1
    blo     4f
    mov     r8, #1
    ldr     r1, =0x2D414
    cmp     r0, r1
    blo     4f
    mov     r8, #2
    ldr     r1, =0x5A828
    cmp     r0, r1
    movhs   r8, #3
4:  str     r8, [sp, #WP_M]
    @ texel columns at that level (r0 = A, r2 = B) and their pointers
    ldr     r0, [r10, #8]
    ldr     r1, [r10, #40]
    sub     r0, r0, r1
    mov     r0, r0, lsr #7
    mov     r0, r0, lsr r8
    ldr     r2, [r11, #8]
    ldr     r3, [r11, #40]
    sub     r2, r2, r3
    mov     r2, r2, lsr #7
    mov     r2, r2, lsr r8
    adr     r12, .Lwp_cm
    ldr     r12, [r12, r8, lsl #2]
    rsb     r4, r8, #7
    add     r5, r1, r12
    add     r5, r5, r0, lsl r4
    str     r5, [sp, #20]           @ cp.texA
    add     r6, r3, r12
    add     r6, r6, r2, lsl r4
    str     r6, [sp, #24]           @ cp.texB
    @ light
    ldr     r12, =g_colormap
    ldrb    r4, [r10, #12]
    add     r4, r12, r4, lsl #8
    str     r4, [sp, #28]           @ cp.cmA
    ldrb    r5, [r11, #12]
    add     r5, r12, r5, lsl #8
    str     r5, [sp, #32]           @ cp.cmB
    @ steps at that level
    ldr     r6, [sp, #WP_STEPA]
    mov     r6, r6, lsr r8
    str     r6, [sp, #44]           @ cp.stA
    ldr     r7, [sp, #WP_STEPB]
    mov     r7, r7, lsr r8
    str     r7, [sp, #48]           @ cp.stB
    mov     r1, #0
    str     r1, [sp, #56]           @ pmode 0
    @ far wall (short) or outside the full-resolution band: one sample per
    @ halfword (for two different walls only if their rows agree within one)
    ldr     r1, [r10, #4]
    ldr     r3, [r11, #4]
    ldr     r12, =g_wallHalfLh
    ldr     r12, [r12]
    cmp     r1, r12
    cmplt   r3, r12
    blt     .Lwp_low
    ldr     r12, =g_fullC0
    ldmia   r12, {r1, r3}
    ldr     r12, [sp, #WP_COL]
    add     r12, r12, #1
    cmp     r12, r1
    blt     .Lwp_low
    sub     r12, r12, #1
    cmp     r12, r3
    bge     .Lwp_low
    cmp     r9, #0
    beq     .Lwp_pair               @ two different walls
    @ the same texel column, light, rows (within one) and scale (half a texel)
    cmp     r0, r2
    bne     .Lwp_pairs
    cmp     r4, r5
    bne     .Lwp_pairs
    ldr     r1, [sp, #WP_STEPA]
    ldr     r3, [sp, #WP_STEPB]
    subs    r1, r1, r3
    rsbmi   r1, r1, #0
    cmp     r1, #468
    bge     .Lwp_pairs
    ldr     r1, [sp, #WP_Y0A]
    ldr     r3, [sp, #WP_Y0B]
    subs    r1, r1, r3
    rsbmi   r1, r1, #0
    cmp     r1, #1
    bgt     .Lwp_pairs
    ldr     r1, [sp, #WP_Y1A]
    ldr     r3, [sp, #WP_Y1B]
    subs    r1, r1, r3
    rsbmi   r1, r1, #0
    cmp     r1, #1
    bgt     .Lwp_pairs

.Lwp_low:
    cmp     r9, #0
    bne     .Lwp_dup
    ldr     r1, [sp, #WP_Y0A]       @ two walls: rows within one?
    ldr     r3, [sp, #WP_Y0B]
    subs    r1, r1, r3
    rsbmi   r1, r1, #0
    cmp     r1, #1
    bgt     .Lwp_pair
    ldr     r1, [sp, #WP_Y1A]
    ldr     r3, [sp, #WP_Y1B]
    subs    r1, r1, r3
    rsbmi   r1, r1, #0
    cmp     r1, #1
    bgt     .Lwp_pair
.Lwp_dup:
    @ wall_column(p, tex, cm, tp, step, n) with column A for both, above and
    @ below the rows hidden in both columns
    ldr     r5, [sp, #WP_Y0A]
    ldr     r6, [sp, #WP_Y1A]
    ldr     r1, [sp, #WP_TI]
    cmp     r6, r1
    movgt   r6, r1                  @ ca = min(y1, tI)
    subs    r9, r6, r5
    ble     5f
    mov     r0, r5
    bl      .Lwp_dupcall
5:  ldr     r5, [sp, #WP_Y0A]
    ldr     r6, [sp, #WP_Y1A]
    ldr     r1, [sp, #WP_BI]
    cmp     r1, #ROW1
    bge     .Lwp_end
    cmp     r5, r1
    movlt   r5, r1                  @ cb = max(y0, bA)
    subs    r9, r6, r5
    ble     .Lwp_end
    mov     r0, r5
    bl      .Lwp_dupcall
    b       .Lwp_end

@ r0 = first row, r9 = rows (> 0): one sample per halfword from column A
.Lwp_dupcall:
    str     lr, [sp, #-4]!
    ldr     r1, [sp, #4 + WP_TOPA]
    sub     r1, r0, r1
    ldr     r2, [sp, #4 + WP_STEPA]
    mul     r3, r1, r2
    ldr     r8, [sp, #4 + WP_M]
    mov     r3, r3, lsr r8          @ tp
    ldr     r12, [sp, #4 + WP_FB]
    ldr     r1, [sp, #4 + WP_COL]
    add     r12, r12, r1
    rsb     r0, r0, r0, lsl #4
    add     r0, r12, r0, lsl #4     @ p
    ldr     r1, [sp, #4 + 20]       @ texA
    ldr     r2, [sp, #4 + 28]       @ cmA
    ldr     r12, [sp, #4 + 44]      @ stA
    sub     sp, sp, #8
    str     r12, [sp]
    str     r9, [sp, #4]
    @ the lowest detail, or magnified near walls at level 0: one sample per
    @ two rows
    ldr     r12, =g_vhalf
    ldr     r12, [r12]
    cmp     r12, #0
    bne     5f
    cmp     r8, #0
    bne     6f
    ldr     r12, [r10, #4]
    cmp     r12, #256
    blt     6f
5:  bl      wall_column2
    b       7f
6:  bl      wall_column
7:  add     sp, sp, #8
    ldr     lr, [sp], #4
    bx      lr

.Lwp_pairs:
    @ the same plain wall: neighbouring texel columns (or one apart: B
    @ shows A's neighbour) come from one 16-bit read of the pair layout
    subs    r1, r2, r0              @ dt = txB - txA
    beq     .Lwp_pair
    cmp     r1, #2
    bgt     .Lwp_pair
    cmn     r1, #2
    blt     .Lwp_pair
    cmp     r1, #0
    movgt   r3, #1
    movgt   r1, r0                  @ starts at A (A low byte)
    movlt   r3, #2
    sublt   r1, r0, #1              @ ends at A (A high byte)
    str     r3, [sp, #56]           @ pmode
    ldr     r8, [sp, #WP_M]
    tst     r1, #1
    adreq   r12, .Lwp_p0
    adrne   r12, .Lwp_p1
    ldr     r12, [r12, r8, lsl #2]
    ldr     r2, [r10, #40]
    add     r12, r2, r12
    mov     r1, r1, lsr #1
    mov     r2, #256
    mov     r2, r2, lsr r8          @ bytes per pair column
    mla     r12, r1, r2, r12
    str     r12, [sp, #52]          @ cp.ptex

.Lwp_pair:
    ldr     r0, [sp, #WP_FB]
    ldr     r1, [sp, #WP_COL]
    add     r0, r0, r1
    str     r0, [sp]                @ cp.p
    ldr     r8, [sp, #WP_M]
    @ above the hidden rows (or all of it)
    ldr     r0, [sp, #WP_Y0A]
    ldr     r1, [sp, #WP_Y1A]
    ldr     r2, [sp, #WP_TA]
    cmp     r1, r2
    movgt   r1, r2
    ldr     r2, [sp, #WP_Y0B]
    ldr     r3, [sp, #WP_Y1B]
    ldr     r4, [sp, #WP_TB]
    cmp     r3, r4
    movgt   r3, r4
    bl      .Lwp_cp
    @ below them
    ldr     r4, [sp, #WP_BA]
    ldr     r5, [sp, #WP_BB]
    cmp     r4, #ROW1
    cmpge   r5, #ROW1
    bge     .Lwp_end
    ldr     r0, [sp, #WP_Y0A]
    cmp     r0, r4
    movlt   r0, r4
    ldr     r1, [sp, #WP_Y1A]
    cmp     r4, #ROW1
    movge   r1, #0
    ldr     r2, [sp, #WP_Y0B]
    cmp     r2, r5
    movlt   r2, r5
    ldr     r3, [sp, #WP_Y1B]
    cmp     r5, #ROW1
    movge   r3, #0
    bl      .Lwp_cp
.Lwp_end:
    add     sp, sp, #WP_SIZE
    ldmfd   sp!, {r4-r11, lr}
    bx      lr

@ col_pair for rows r0..r1 of A and r2..r3 of B (r8 = level)
.Lwp_cp:
    cmp     r0, r1
    cmpge   r2, r3
    bxge    lr                      @ both empty
    str     lr, [sp, #-4]!
    str     r0, [sp, #4 + 4]
    str     r2, [sp, #4 + 8]
    str     r1, [sp, #4 + 12]
    str     r3, [sp, #4 + 16]
    ldr     r4, [sp, #4 + WP_TOPA]
    sub     r4, r0, r4
    ldr     r5, [sp, #4 + WP_STEPA]
    mul     r4, r5, r4
    mov     r4, r4, lsr r8
    str     r4, [sp, #4 + 36]       @ tpA
    ldr     r4, [sp, #4 + WP_TOPB]
    sub     r4, r2, r4
    ldr     r5, [sp, #4 + WP_STEPB]
    mul     r4, r5, r4
    mov     r4, r4, lsr r8
    str     r4, [sp, #4 + 40]       @ tpB
    add     r0, sp, #4
    bl      col_pair
    ldr     r8, [sp, #4 + WP_M]
    ldr     lr, [sp], #4
    bx      lr

.Lwp_cm: .word WT_CM0, WT_CM1, WT_CM2, WT_CM3
.Lwp_p0: .word 10880, 27264, 31360, 32384
.Lwp_p1: .word 19072, 29312, 31872, 32512
    .pool

@ ---------------------------------------------------------------------------
@ void quad_span(QuadArgs *q)   four columns of one wall (4-byte aligned),
@   rows ra..rb-1: one 32-bit read of the quad layout gives the four texels
@   of a row (column 0 in the lowest byte, or the highest when flipped).
@   Rows Y0..Y1-1 belong to all four columns; the others only to the
@   columns whose own span y0..y1 covers them (the rest of the word kept).
@  0 p0 (row 0)  4 ra  8 rb  12 Y0  16 Y1  20 y0[4]  36 y1[4]
@ 52 qtex  56 tp (at row ra)  60 st  64 cm[4]  80 flip  84 hmax (texel rows - 1)
@ ---------------------------------------------------------------------------
.macro QLOAD                        @ r12 = the row's four texels; tp steps
    mov     r12, r3, lsr #16
    ldr     r12, [r1, r12, lsl #2]
    add     r3, r3, r4
.endm
.macro QLIT                         @ lr = the four lit pixels (r12 texels)
    and     lr, r12, #0xFF
    ldrb    lr, [r5, lr]
    and     r2, r12, #0xFF00
    ldrb    r2, [r6, r2, lsr #8]
    orr     lr, lr, r2, lsl #8
    and     r2, r12, #0xFF0000
    ldrb    r2, [r7, r2, lsr #16]
    orr     lr, lr, r2, lsl #16
    ldrb    r2, [r8, r12, lsr #24]
    orr     lr, lr, r2, lsl #24
.endm
.macro QLITF                        @ flipped: column 0 takes byte 3
    ldrb    lr, [r5, r12, lsr #24]
    and     r2, r12, #0xFF0000
    ldrb    r2, [r6, r2, lsr #16]
    orr     lr, lr, r2, lsl #8
    and     r2, r12, #0xFF00
    ldrb    r2, [r7, r2, lsr #8]
    orr     lr, lr, r2, lsl #16
    and     r2, r12, #0xFF
    ldrb    r2, [r8, r2]
    orr     lr, lr, r2, lsl #24
.endm
    .global quad_span
    .type quad_span, %function
quad_span:
    stmfd   sp!, {r4-r11, lr}
    mov     r10, r0
    ldr     r0, [r10]
    ldr     r11, [r10, #4]          @ row
    rsb     r2, r11, r11, lsl #4
    add     r0, r0, r2, lsl #4      @ p at row ra
    ldr     r1, [r10, #52]
    add     r2, r10, #56
    ldmia   r2, {r3, r4}            @ tp, st
    add     r2, r10, #64
    ldmia   r2, {r5-r8}             @ cm[4]
    @ rows above Y0 (some columns only)
1:  ldr     r9, [r10, #12]
    ldr     r2, [r10, #8]
    cmp     r9, r2
    movgt   r9, r2                  @ min(Y0, rb)
    cmp     r11, r9
    bge     2f
    bl      .Lq_masked
    add     r11, r11, #1
    b       1b
    @ rows all four columns cover
2:  ldr     r9, [r10, #16]
    ldr     r2, [r10, #8]
    cmp     r9, r2
    movgt   r9, r2                  @ min(Y1, rb)
    subs    r9, r9, r11
    ble     4f
#ifdef PIXCNT
    mov     r2, r9, lsl #2
    PCNT    9, r2
#endif
    add     r11, r11, r9
    ldr     r2, [r10, #80]
    cmp     r2, #0
    bne     6f
5:  QLOAD
    QLIT
    str     lr, [r0], #240
    subs    r9, r9, #1
    bne     5b
    b       4f
6:  QLOAD
    QLITF
    str     lr, [r0], #240
    subs    r9, r9, #1
    bne     6b
    @ rows below Y1
4:  ldr     r2, [r10, #8]
    cmp     r11, r2
    bge     9f
    bl      .Lq_masked
    add     r11, r11, #1
    b       4b
9:  ldmfd   sp!, {r4-r11, lr}
    bx      lr

@ row r11 for the columns whose span covers it (r9 free)
.Lq_masked:
    str     lr, [sp, #-4]!
    PCNTI   10, 1
    movs    r12, r3, asr #16        @ the texel row, clamped to the texture
    movmi   r12, #0
    ldr     r2, [r10, #84]
    cmp     r12, r2
    movgt   r12, r2
    ldr     r12, [r1, r12, lsl #2]
    add     r3, r3, r4
    ldr     r2, [r10, #80]
    cmp     r2, #0
    bne     1f
    QLIT
    b       2f
1:  QLITF
2:  mov     r9, #0                  @ mask of the columns with wall in this row
    ldr     r2, [r10, #20]
    cmp     r11, r2
    blt     3f
    ldr     r2, [r10, #36]
    cmp     r11, r2
    orrlt   r9, r9, #0xFF
3:  ldr     r2, [r10, #24]
    cmp     r11, r2
    blt     3f
    ldr     r2, [r10, #40]
    cmp     r11, r2
    orrlt   r9, r9, #0xFF00
3:  ldr     r2, [r10, #28]
    cmp     r11, r2
    blt     3f
    ldr     r2, [r10, #44]
    cmp     r11, r2
    orrlt   r9, r9, #0xFF0000
3:  ldr     r2, [r10, #32]
    cmp     r11, r2
    blt     3f
    ldr     r2, [r10, #48]
    cmp     r11, r2
    orrlt   r9, r9, #0xFF000000
3:  ldr     r2, [r0]
    bic     r2, r2, r9
    and     lr, lr, r9
    orr     r2, r2, lr
    str     r2, [r0], #240
    ldr     lr, [sp], #4
    bx      lr

@ ---------------------------------------------------------------------------
@ int wall_quad(u8 *fb, int col, const ColHit *h)   (see render.iwram.c)
@   the four columns col..col+3 (h[0..3]) of one plain wall at a level where
@   its texels are about one per column: drawn together by quad_span.
@   Returns 0 (nothing drawn) when they do not qualify.
@ ColHit: 0 dist  4 lh  8 tcol  12 light (u8)  36 key  40 tex  44 f (u16); 48 bytes
@ ---------------------------------------------------------------------------
    @ frame: QuadArgs at 0 (88 bytes), then
    .equ WQ_TOP1, 88
    .equ WQ_STEP1, 92
    .equ WQ_M, 96
    .equ WQ_OT, 100
    .equ WQ_OB, 104
    .equ WQ_MN, 108
    .equ WQ_MX, 112
    .equ WQ_SIZE, 116

    .global wall_quad
    .type wall_quad, %function
wall_quad:
    stmfd   sp!, {r4-r11, lr}
    sub     sp, sp, #WQ_SIZE
    mov     r10, r2                 @ h
    mov     r11, r1                 @ col
    add     r0, r0, r1
    str     r0, [sp]                @ q.p0 = fb + col
    @ one plain wall
    ldr     r4, [r10, #36]
    cmp     r4, #0
    beq     .Lwq_no
    ldr     r5, [r10, #48 + 36]
    cmp     r5, r4
    ldreq   r5, [r10, #96 + 36]
    cmpeq   r5, r4
    ldreq   r5, [r10, #144 + 36]
    cmpeq   r5, r4
    bne     .Lwq_no
    @ far walls, outside the full-resolution band: the pairs' half resolution
    ldr     r0, [r10, #4]
    ldr     r1, =g_wallHalfLh
    ldr     r1, [r1]
    cmp     r0, r1
    blt     .Lwq_no
    ldr     r1, =g_fullC0
    ldmia   r1, {r2, r3}
    cmp     r11, r2
    blt     .Lwq_no
    add     r0, r11, #3
    cmp     r0, r3
    bge     .Lwq_no
    @ rows big prop faces in front will paint over in all four columns
    @ (the rows only some of them hide are drawn anyway: harmless)
    ldr     r6, =g_covF
    ldr     r7, =g_covT
    ldr     r8, =g_covB
    mov     r9, #0                  @ k
    mov     r4, #0                  @ latest top
    mov     r5, #ROW1 + 1           @ earliest bottom
1:  add     r0, r11, r9
    ldr     r1, [r6, r0, lsl #2]    @ covF
    add     r2, r9, r9, lsl #1
    add     r2, r10, r2, lsl #4     @ &h[k]
    ldr     r2, [r2]                @ dist
    cmp     r1, r2
    bge     .Lwq_noocc              @ this column hides nothing
    mov     r0, r0, lsl #1
    ldrsh   r3, [r7, r0]
    ldrsh   r12, [r8, r0]
    cmp     r3, r4
    movgt   r4, r3
    cmp     r12, r5
    movlt   r5, r12
    add     r9, r9, #1
    cmp     r9, #4
    blt     1b
    cmp     r4, r5
    blt     2f
.Lwq_noocc:
    mov     r4, #ROW1
    mov     r5, #ROW1
2:  str     r4, [sp, #WQ_OT]
    str     r5, [sp, #WQ_OB]
    @ spans: y0[k], y1[k]; Y0 = max y0, Y1 = min y1, mn, mx; density down
    mov     r4, #ROW0               @ Y0
    mov     r5, #ROW1               @ Y1
    mov     r6, #ROW1               @ mn
    mov     r7, #ROW0               @ mx
    mov     r8, #0                  @ max step
    mov     r9, #0
3:  add     r0, r9, r9, lsl #1
    add     r0, r10, r0, lsl #4
    ldr     r1, [r0, #4]            @ lh
    mov     r2, r1, lsr #1
    rsb     r2, r2, #HORIZON        @ top
    add     r3, r2, r1              @ bottom
    cmp     r9, #1
    streq   r2, [sp, #WQ_TOP1]
    cmp     r2, #ROW0
    movlt   r2, #ROW0
    cmp     r3, #ROW1
    movgt   r3, #ROW1
    add     r12, sp, #20
    str     r2, [r12, r9, lsl #2]   @ y0[k]
    add     r12, sp, #36
    str     r3, [r12, r9, lsl #2]   @ y1[k]
    cmp     r2, r4
    movgt   r4, r2
    cmp     r3, r5
    movlt   r5, r3
    cmp     r2, r6
    movlt   r6, r2
    cmp     r3, r7
    movgt   r7, r3
    ldr     r1, [r0]                @ dist
    ldr     r12, =26214
    umull   r2, r3, r1, r12         @ step = 0.4 * dist
    mov     r2, r2, lsr #16
    orr     r2, r2, r3, lsl #16
    cmp     r9, #1
    streq   r2, [sp, #WQ_STEP1]
    cmp     r2, r8
    movgt   r8, r2
    add     r9, r9, #1
    cmp     r9, #4
    blt     3b
    cmp     r4, r5
    bge     .Lwq_no
    str     r4, [sp, #12]           @ q.Y0
    str     r5, [sp, #16]           @ q.Y1
    str     r6, [sp, #WQ_MN]
    str     r7, [sp, #WQ_MX]
    @ density across: f moves 1024 per texel of level 0, over three columns
    ldrh    r0, [r10, #44]
    ldrh    r1, [r10, #144 + 44]
    subs    r0, r1, r0
    rsbmi   r0, r0, #0
    mov     r1, #21
    mul     r9, r0, r1              @ r9 = across
    cmp     r9, r8
    movgt   r8, r9
    @ level
    mov     r3, #0
    ldr     r1, =0x16A0A
    cmp     r8, r1
    blo     4f
    mov     r3, #1
    ldr     r1, =0x2D414
    cmp     r8, r1
    blo     4f
    mov     r3, #2
    ldr     r1, =0x5A828
    cmp     r8, r1
    movhs   r3, #3
4:  cmp     r3, #0
    bne     5f
    ldr     r1, =0xB505             @ magnified at level 0: the pairs share samples
    cmp     r9, r1
    blo     .Lwq_no
5:  str     r3, [sp, #WQ_M]
    @ texel columns at that level; the four texels s .. s+3 around their mean
    mov     r4, #0                  @ sum
    mov     r9, #0
6:  add     r0, r9, r9, lsl #1
    add     r0, r10, r0, lsl #4
    ldr     r1, [r0, #8]            @ tcol
    ldr     r2, [r0, #40]           @ tex
    sub     r1, r1, r2
    mov     r1, r1, lsr #7
    mov     r1, r1, lsr r3
    add     r4, r4, r1
    cmp     r9, #0
    moveq   r5, r1
    cmp     r9, #1
    moveq   r6, r1
    cmp     r9, #2
    moveq   r7, r1
    cmp     r9, #3
    moveq   r8, r1
    add     r9, r9, #1
    cmp     r9, #4
    blt     6b
    sub     r4, r4, #4
    movs    r4, r4, asr #2          @ s
    movmi   r4, #0
    mov     r0, #64
    mov     r0, r0, lsr r3          @ W
    sub     r1, r0, #4
    cmp     r4, r1
    movgt   r4, r1
    @ every column within one texel of its own
    subs    r1, r5, r4
    rsbmi   r1, r1, #0
    cmp     r1, #1
    bgt     .Lwq_no
    add     r2, r4, #1
    subs    r1, r6, r2
    rsbmi   r1, r1, #0
    cmp     r1, #1
    bgt     .Lwq_no
    add     r2, r4, #2
    subs    r1, r7, r2
    rsbmi   r1, r1, #0
    cmp     r1, #1
    bgt     .Lwq_no
    add     r2, r4, #3
    subs    r1, r8, r2
    rsbmi   r1, r1, #0
    cmp     r1, #1
    bgt     .Lwq_no
    @ quad layout: tex + QBase[m] + (s & 3) * W * H + (s >> 2) * H * 4
    mov     r1, #128
    mov     r1, r1, lsr r3          @ H
    sub     r2, r1, #1
    str     r2, [sp, #84]           @ q.hmax
    mul     r2, r0, r1              @ W * H
    and     r5, r4, #3
    mul     r6, r5, r2
    mov     r5, r4, lsr #2
    mul     r7, r5, r1
    add     r6, r6, r7, lsl #2
    adr     r12, .Lwq_qbase
    ldr     r12, [r12, r3, lsl #2]
    add     r6, r6, r12
    ldr     r12, [r10, #40]         @ tex
    add     r6, r6, r12
    str     r6, [sp, #52]           @ q.qtex
    ldr     r0, [sp, #WQ_STEP1]
    mov     r0, r0, lsr r3
    str     r0, [sp, #60]           @ q.st
    @ colormaps
    ldr     r12, =g_colormap
    ldrb    r0, [r10, #12]
    add     r0, r12, r0, lsl #8
    str     r0, [sp, #64]
    ldrb    r0, [r10, #48 + 12]
    add     r0, r12, r0, lsl #8
    str     r0, [sp, #68]
    ldrb    r0, [r10, #96 + 12]
    add     r0, r12, r0, lsl #8
    str     r0, [sp, #72]
    ldrb    r0, [r10, #144 + 12]
    add     r0, r12, r0, lsl #8
    str     r0, [sp, #76]
    mov     r0, #0
    str     r0, [sp, #80]           @ q.flip
    @ above the rows hidden by props (or all), then below
    ldr     r4, [sp, #WQ_MN]        @ ra
    ldr     r5, [sp, #WQ_MX]
    ldr     r6, [sp, #WQ_OT]
    cmp     r6, r5
    movlt   r5, r6                  @ rb
    cmp     r4, r5
    bge     7f
    bl      .Lwq_span
7:  ldr     r6, [sp, #WQ_OB]
    cmp     r6, #ROW1
    bge     8f
    ldr     r4, [sp, #WQ_MN]
    cmp     r6, r4
    movgt   r4, r6
    ldr     r5, [sp, #WQ_MX]
    cmp     r4, r5
    bge     8f
    bl      .Lwq_span
8:  mov     r0, #1
    add     sp, sp, #WQ_SIZE
    ldmfd   sp!, {r4-r11, lr}
    bx      lr
.Lwq_no:
    mov     r0, #0
    add     sp, sp, #WQ_SIZE
    ldmfd   sp!, {r4-r11, lr}
    bx      lr

@ rows r4..r5-1: q.tp from column 1's mapping, then quad_span
.Lwq_span:
    str     lr, [sp, #-4]!
    str     r4, [sp, #4 + 4]        @ q.ra
    str     r5, [sp, #4 + 8]        @ q.rb
    ldr     r0, [sp, #4 + WQ_TOP1]
    sub     r0, r4, r0
    ldr     r1, [sp, #4 + WQ_STEP1]
    mul     r2, r0, r1
    ldr     r3, [sp, #4 + WQ_M]
    mov     r2, r2, asr r3
    str     r2, [sp, #4 + 56]       @ q.tp
    add     r0, sp, #4
    bl      quad_span
    ldr     lr, [sp], #4
    bx      lr

.Lwq_qbase: .word 32640, 65408, 73600, 75648
    .pool

@ ---------------------------------------------------------------------------
@ void col_pair_uv(ColPairUV *s)   two columns of a polygon (stride 240)
@  0 p   4 a0  8 b0  12 a1  16 b1   as col_pair
@ 20 tex (64x64, column-major: texel = tex[u * 64 + v])
@ 24 cmA 28 cmB      32 uvA 36 uvB (u 6.10 << 16 | v 6.10 at row a0 / b0)
@ 40 duvA 44 duvB    (per row, both halves wrap)
@ ---------------------------------------------------------------------------
.macro TEXUV out, uv, t
    mov     \out, \uv, lsr #26
    and     \t, \uv, #0xFC00
    orr     \out, \t, \out, lsl #16
    ldrb    \out, [r1, \out, lsr #10]
.endm
.macro UROW_A
    TEXUV   r9, r5, r10
    add     r5, r5, r7
    ldrb    r9, [r3, r9]
    ldrb    r10, [r0, #1]
    orr     r9, r9, r10, lsl #8
    strh    r9, [r0], #240
.endm
.macro UROW_B
    TEXUV   r9, r6, r10
    add     r6, r6, r8
    ldrb    r9, [r4, r9]
    ldrb    r10, [r0]
    orr     r9, r10, r9, lsl #8
    strh    r9, [r0], #240
.endm
.macro UROW_AB
    TEXUV   r9, r5, r10
    add     r5, r5, r7
    TEXUV   r10, r6, r2
    add     r6, r6, r8
    ldrb    r9, [r3, r9]
    ldrb    r10, [r4, r10]
    orr     r9, r9, r10, lsl #8
    strh    r9, [r0], #240
.endm

    .global col_pair_uv
    .type col_pair_uv, %function
col_pair_uv:
    stmfd   sp!, {r4-r11, lr}
#ifdef PIXCNT
    ldr     r4, [r0, #4]
    ldr     r5, [r0, #12]
    subs    r5, r5, r4
    movlt   r5, #0
    ldr     r4, [r0, #8]
    ldr     r6, [r0, #16]
    subs    r6, r6, r4
    movlt   r6, #0
    add     r5, r5, r6
    PCNT    1, r5
#endif
    mov     r12, r0
    ldr     r1, [r12, #20]          @ tex
    add     lr, r12, #24
    ldmia   lr, {r3-r8}             @ cmA cmB uvA uvB duvA duvB
    ldr     r9, [r12, #4]           @ a0
    ldr     r10, [r12, #12]         @ a1
    cmp     r9, r10
    bge     .Lcu_b_only
    ldr     r11, [r12, #8]          @ b0
    ldr     lr, [r12, #16]          @ b1
    cmp     r11, lr
    bge     .Lcu_a_only
    cmp     r9, r11
    movge   r0, r9
    movlt   r0, r11
    sub     r10, r10, lr
    cmp     r10, #0
    addle   lr, lr, r10
    sub     lr, lr, r0
    cmp     lr, #0
    ble     .Lcu_apart
    sub     r11, r11, r9
    str     r11, [r12, #4]
    str     lr, [r12, #8]
    str     r10, [r12, #12]
    cmp     r11, #0
    subgt   r0, r0, r11
    addlt   r0, r0, r11
    rsb     r9, r0, r0, lsl #4
    ldr     r0, [r12]
    add     r0, r0, r9, lsl #4
    ldr     r11, [r12, #4]
    cmp     r11, #0
    bgt     10f
    blt     11f
    b       12f
10: bl      .Lcu_rows_a
    b       12f
11: rsb     r11, r11, #0
    bl      .Lcu_rows_b
12: ldr     r11, [r12, #8]
    bl      .Lcu_rows_ab
    ldr     r11, [r12, #12]
    cmp     r11, #0
    bgt     13f
    blt     14f
    b       .Lcu_end
13: bl      .Lcu_rows_a
    b       .Lcu_end
14: rsb     r11, r11, #0
    bl      .Lcu_rows_b
    b       .Lcu_end
.Lcu_apart:
    ldr     r10, [r12, #12]
.Lcu_a_only:
    rsb     r11, r9, r9, lsl #4
    ldr     r0, [r12]
    add     r0, r0, r11, lsl #4
    sub     r11, r10, r9
    bl      .Lcu_rows_a
.Lcu_b_only:
    ldr     r9, [r12, #8]
    ldr     r10, [r12, #16]
    subs    r10, r10, r9
    ble     .Lcu_end
    rsb     r11, r9, r9, lsl #4
    ldr     r0, [r12]
    add     r0, r0, r11, lsl #4
    mov     r11, r10
    bl      .Lcu_rows_b
.Lcu_end:
    ldmfd   sp!, {r4-r11, lr}
    bx      lr

.Lcu_rows_a:                        @ r11 >= 1 rows
    UROW_A
    subs    r11, r11, #1
    bne     .Lcu_rows_a
    bx      lr
.Lcu_rows_b:
    UROW_B
    subs    r11, r11, #1
    bne     .Lcu_rows_b
    bx      lr
.Lcu_rows_ab:                       @ r2 is free here (scratch in UROW_AB)
    UROW_AB
    subs    r11, r11, #1
    bne     .Lcu_rows_ab
    bx      lr

@ ---------------------------------------------------------------------------
@ void col_uv2(u8 *p, int n, const u8 *tex, const u8 *cm, u32 uv, u32 duv)
@   one polygon sample per row for both columns of a pair (half resolution);
@   p = pair address at the first row (even)
@ ---------------------------------------------------------------------------
    .global col_uv2
    .type col_uv2, %function
col_uv2:
    PCNT    4, r1
    cmp     r1, #0
    bxle    lr
    stmfd   sp!, {r4-r8, lr}
    ldr     r4, [sp, #24]           @ uv
    ldr     r5, [sp, #28]           @ duv
    ldr     r6, =g_vhalf
    ldr     r6, [r6]
    cmp     r6, #0
    bne     5f
1:  mov     r6, r4, lsr #26
    and     r7, r4, #0xFC00
    orr     r6, r7, r6, lsl #16
    ldrb    r6, [r2, r6, lsr #10]
    add     r4, r4, r5
    ldrb    r6, [r3, r6]
    orr     r6, r6, r6, lsl #8
    strh    r6, [r0], #240
    subs    r1, r1, #1
    bne     1b
    ldmfd   sp!, {r4-r8, lr}
    bx      lr
5:  add     r5, r5, r5              @ the lowest detail: one sample per two rows
6:  mov     r6, r4, lsr #26
    and     r7, r4, #0xFC00
    orr     r6, r7, r6, lsl #16
    ldrb    r6, [r2, r6, lsr #10]
    add     r4, r4, r5
    ldrb    r6, [r3, r6]
    orr     r6, r6, r6, lsl #8
    strh    r6, [r0], #240
    subs    r1, r1, #1
    beq     7f
    strh    r6, [r0], #240
    subs    r1, r1, #1
    bne     6b
7:  ldmfd   sp!, {r4-r8, lr}
    bx      lr
    .pool

@ ---------------------------------------------------------------------------
@ void col_one(u8 *p, int n, const u8 *tex, const u8 *cm, u32 tp, u32 step)
@   one column (p = pixel address of the first row), merged into its pair
@ ---------------------------------------------------------------------------
    .global col_one
    .type col_one, %function
col_one:
    PCNT    3, r1
    cmp     r1, #0
    bxle    lr
    stmfd   sp!, {r4-r7, lr}
    ldr     r4, [sp, #20]           @ tp
    ldr     r5, [sp, #24]           @ step
    tst     r0, #1
    bne     3f
1:  ldrb    r6, [r2, r4, lsr #16]   @ even column: low byte
    add     r4, r4, r5
    ldrb    r6, [r3, r6]
    ldrb    r7, [r0, #1]
    orr     r6, r6, r7, lsl #8
    strh    r6, [r0], #240
    subs    r1, r1, #1
    bne     1b
    ldmfd   sp!, {r4-r7, lr}
    bx      lr
3:  sub     r0, r0, #1              @ odd column: high byte
4:  ldrb    r6, [r2, r4, lsr #16]
    add     r4, r4, r5
    ldrb    r6, [r3, r6]
    ldrb    r7, [r0]
    orr     r6, r7, r6, lsl #8
    strh    r6, [r0], #240
    subs    r1, r1, #1
    bne     4b
    ldmfd   sp!, {r4-r7, lr}
    bx      lr

@ ---------------------------------------------------------------------------
@ u32 dda_edge(DDAE *d)
@   d: { u32 sdx, sdy, ddx, ddy; const u8 *p; s32 stepXb, stepYb, ex, ey; }
@   p points at the current cell's edge bytes [west, north]. Steps cell to
@   cell until the crossed edge is not open; returns edge | side << 8.
@ ---------------------------------------------------------------------------
    .global dda_edge
    .type dda_edge, %function
dda_edge:
    stmfd   sp!, {r4-r11, lr}
    ldmia   r0, {r1-r9}
14:
    cmp     r1, r2
    addlo   r1, r1, r3
    addlo   r5, r5, r6
    ldrlob  r10, [r5, r8]
    movlo   r11, #0
    addhs   r2, r2, r4
    addhs   r5, r5, r7
    ldrhsb  r10, [r5, r9]
    movhs   r11, #1
    cmp     r10, #0
    beq     14b
    stmia   r0, {r1, r2}
    str     r5, [r0, #16]
    orr     r0, r10, r11, lsl #8
    ldmfd   sp!, {r4-r11, lr}
    bx      lr

@ ---------------------------------------------------------------------------
@ void light_patch(u8 *dst, const u8 *src, int w, int h, int lvl)
@   max-blends a w*h patch scaled by lvl/256 into the light bits (0-4) of
@   the 64-wide light grid, keeping the material bits
@ ---------------------------------------------------------------------------
    .global light_patch
    .type light_patch, %function
light_patch:
    stmfd   sp!, {r4-r9, lr}
    ldr     r4, [sp, #28]           @ lvl
15:
    mov     r5, r2
    mov     r6, r0
16:
    ldrb    r7, [r1], #1
    mul     r7, r4, r7
    ldrb    r8, [r6]
    mov     r7, r7, lsr #8
    and     r9, r8, #31
    cmp     r9, r7
    biclo   r8, r8, #31
    orrlo   r8, r8, r7
    strb    r8, [r6], #1
    subs    r5, r5, #1
    bne     16b
    add     r0, r0, #64
    subs    r3, r3, #1
    bne     15b
    ldmfd   sp!, {r4-r9, lr}
    bx      lr
