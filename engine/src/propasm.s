@ Hollowmere prop and sprite fills (ARM, IWRAM), full resolution mode 4.
    .data
    .align 2
    .global g_fullC0, g_fullC1, g_vhalf
g_fullC0:   .word 0         @ full-resolution band of columns [g_fullC0, g_fullC1)
g_fullC1:   .word 240
g_vhalf:    .word 0         @ the lowest detail: far things one sample per two rows too

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


    .equ ROW0, 10
    .equ ROW1, 138

@ out = 2^32 / in (both 16.16), in < 2^28; clobbers tmp and the flags
.macro RCP out, in, tmp, tab
    cmp     \in, #0x10000
    movlo   \tmp, \in, lsr #4
    ldrlo   \out, [\tab, \tmp, lsl #2]
    movlo   \out, \out, lsl #4
    blo     99f
    cmp     \in, #0x100000
    movlo   \tmp, \in, lsr #8
    ldrlo   \out, [\tab, \tmp, lsl #2]
    blo     99f
    cmp     \in, #0x1000000
    movlo   \tmp, \in, lsr #12
    movhs   \tmp, \in, lsr #16
    ldr     \out, [\tab, \tmp, lsl #2]
    movlo   \out, \out, lsr #4
    movhs   \out, \out, lsr #8
99:
.endm

@ texel of a 64x64 column-major texture at uv (u 6.10 << 16 | v 6.10)
.macro TEX out, uv, t, tex
    mov     \out, \uv, lsr #26
    and     \t, \uv, #0xFC00
    orr     \out, \t, \out, lsl #16
    ldrb    \out, [\tex, \out, lsr #10]
.endm

@ ---------------------------------------------------------------------------
@ void rspan_draw(RSpan *s)    rows of a polygon band between two straight edges
@  0 fb   4 r (first row, advanced)   8 r1 (last row)
@ 12 xA 16 uA 20 vA 24 wA   28 xB 32 uB 36 vB 40 wB   (16.16 at the row centre;
@      u,v are texels, or texels/z when persp)
@ 44 dxA dwA.. 60 dxB..   (per row)   76 tex   80 cmap   84 persp   88 half
@ Every column is a pixel: two per halfword, the odd ends merged. With
@ perspective u and v are exact at both ends of a row and linear between;
@ a long row whose depth changes along it (an upright or sloping face) is
@ exact every 16 columns.
@ ---------------------------------------------------------------------------
    .equ RS_UW, 0           @ u/z, v/z, 1/z at the next exact column
    .equ RS_VW, 4
    .equ RS_W, 8
    .equ RS_DUW, 12         @ their steps per column
    .equ RS_DVW, 16
    .equ RS_DW, 20
    .equ RS_U, 24           @ u, v there (16.16 texels)
    .equ RS_V, 28
    .equ RS_C, 32           @ that column
    .equ RS_CE, 36          @ the row's last column
    .equ RS_SIZE, 40
.macro MULS out, a, b, t           @ out = (a * b) >> 16 (signed); out, a, t distinct
    smull   \t, \out, \a, \b
    mov     \t, \t, lsr #16
    orr     \out, \t, \out, lsl #16
.endm
    .global rspan_draw
    .type rspan_draw, %function
rspan_draw:
    stmfd   sp!, {r4-r11, lr}
    sub     sp, sp, #RS_SIZE
.Lrs_row:
    ldr     r12, =rcp_tab
    ldr     r2, [r0, #12]
    ldr     r6, [r0, #28]
    cmp     r2, r6
    addle   r1, r0, #12
    addle   lr, r0, #28
    addgt   r1, r0, #28
    addgt   lr, r0, #12
    ldmia   r1, {r2-r5}             @ left edge  x u v w
    ldmia   lr, {r6-r9}             @ right edge x u v w
    ldr     r10, =0x7FFF
    add     r1, r2, r10
    mov     r1, r1, asr #16         @ cs
    sub     lr, r6, r10
    sub     lr, lr, #1
    mov     lr, lr, asr #16         @ ce
    cmp     r1, #0
    movlt   r1, #0
    cmp     lr, #239
    movgt   lr, #239
    subs    lr, lr, r1
    blt     .Lrs_next
    add     lr, lr, #1              @ n
    PCNT    5, lr
    ldr     r10, [r0, #84]
    cmp     r10, #0
    beq     3f
    cmp     lr, #16                 @ a long row whose depth changes: in parts
    ble     2f
    subs    r10, r5, r9
    rsbmi   r10, r10, #0
    cmp     r10, r5, lsr #4
    bgt     .Lrs_sub
2:  RCP     r10, r5, r11, r12       @ 1/w at the left end
    smull   r11, r5, r3, r10
    mov     r11, r11, lsr #16
    orr     r3, r11, r5, lsl #16
    smull   r11, r5, r4, r10
    mov     r11, r11, lsr #16
    orr     r4, r11, r5, lsl #16
    RCP     r10, r9, r11, r12       @ right end
    smull   r11, r9, r7, r10
    mov     r11, r11, lsr #16
    orr     r7, r11, r9, lsl #16
    smull   r11, r9, r8, r10
    mov     r11, r11, lsr #16
    orr     r8, r11, r9, lsl #16
3:  sub     r5, r6, r2              @ span width
    cmp     r5, #0x10000
    movlt   r5, #0x10000
    RCP     r9, r5, r10, r12
    sub     r7, r7, r3
    smull   r10, r11, r7, r9
    mov     r10, r10, lsr #16
    orr     r7, r10, r11, lsl #16   @ du
    sub     r8, r8, r4
    smull   r10, r11, r8, r9
    mov     r10, r10, lsr #16
    orr     r8, r10, r11, lsl #16   @ dv
    mov     r5, r1, lsl #16
    add     r5, r5, #0x8000
    sub     r5, r5, r2              @ offset to the first column centre
    smull   r10, r11, r5, r7
    mov     r10, r10, lsr #16
    orr     r10, r10, r11, lsl #16
    add     r3, r3, r10             @ u0
    smull   r10, r11, r5, r8
    mov     r10, r10, lsr #16
    orr     r10, r10, r11, lsl #16
    add     r4, r4, r10             @ v0
    mov     r3, r3, asr #6
    mov     r4, r4, lsl #10
    mov     r4, r4, lsr #16
    add     r3, r4, r3, lsl #16     @ uv (6.10 | 6.10)
    mov     r7, r7, asr #6
    mov     r8, r8, asr #6
    add     r7, r8, r7, lsl #16     @ duv
    ldr     r9, [r0, #4]
    ldr     r10, [r0]
    add     r10, r10, r1            @ fb + cs
    rsb     r9, r9, r9, lsl #4
    add     r10, r10, r9, lsl #4    @ + row * 240
    ldr     r1, [r0, #76]
    ldr     r2, [r0, #80]
    mov     r9, lr
    bl      .Lrs_px
.Lrs_next:                          @ step both edges to the next row
    add     r1, r0, #12
    ldmia   r1, {r2-r5}
    add     lr, r0, #44
    ldmia   lr, {r6-r9}
    add     r2, r2, r6
    add     r3, r3, r7
    add     r4, r4, r8
    add     r5, r5, r9
    stmia   r1, {r2-r5}
    add     r1, r0, #28
    ldmia   r1, {r2-r5}
    add     lr, r0, #60
    ldmia   lr, {r6-r9}
    add     r2, r2, r6
    add     r3, r3, r7
    add     r4, r4, r8
    add     r5, r5, r9
    stmia   r1, {r2-r5}
    ldr     r1, [r0, #4]
    ldr     r2, [r0, #8]
    add     r1, r1, #1
    str     r1, [r0, #4]
    cmp     r1, r2
    ble     .Lrs_row
    add     sp, sp, #RS_SIZE
    ldmfd   sp!, {r4-r11, lr}
    bx      lr

@ a long perspective row: u/z, v/z and 1/z step along it, u and v exact at
@ every 16th column and linear between
.Lrs_sub:                           @ r1 cs, lr n, r2..r5 left (x uw vw w), r6..r9 right
    add     r10, r1, lr
    sub     r10, r10, #1
    str     r10, [sp, #RS_CE]
    str     r1, [sp, #RS_C]
    sub     r10, r6, r2             @ width
    RCP     r11, r10, lr, r12       @ 1 / width
    sub     r7, r7, r3
    MULS    r6, r7, r11, lr         @ per column: u/z
    sub     r8, r8, r4
    MULS    r7, r8, r11, lr         @ v/z
    sub     r9, r9, r5
    MULS    r8, r9, r11, lr         @ 1/z
    add     r10, sp, #RS_DUW
    stmia   r10, {r6-r8}
    mov     r10, r1, lsl #16
    add     r10, r10, #0x8000
    sub     r10, r10, r2            @ offset of the first column centre
    MULS    r9, r10, r6, lr
    add     r3, r3, r9
    MULS    r9, r10, r7, lr
    add     r4, r4, r9
    MULS    r9, r10, r8, lr
    add     r5, r5, r9
    stmia   sp, {r3-r5}
    bl      .Lrs_exact
.Lrs_seg:
    ldr     r1, [sp, #RS_C]         @ this part's first column
    ldr     r2, [sp, #RS_CE]
    orr     r9, r1, #15             @ to the next multiple of 16, or the end
    cmp     r9, r2
    movgt   r9, r2
    sub     r9, r9, r1
    add     r9, r9, #1              @ r9 = its columns
    add     r2, r1, r9
    str     r2, [sp, #RS_C]
    ldr     r10, [sp, #RS_U]        @ u, v at its first column
    ldr     r11, [sp, #RS_V]
    ldmia   sp, {r3-r5}
    add     r6, sp, #RS_DUW
    ldmia   r6, {r6-r8}
    mla     r3, r6, r9, r3
    mla     r4, r7, r9, r4
    mla     r5, r8, r9, r5
    stmia   sp, {r3-r5}
    bl      .Lrs_exact              @ u, v at the next part's first column
    ldr     r7, [sp, #RS_U]
    ldr     r8, [sp, #RS_V]
    sub     r7, r7, r10
    sub     r8, r8, r11
    ldr     r6, =rcp_tab
    ldr     r6, [r6, r9, lsl #2]
    mov     r6, r6, lsr #8          @ 65536 / columns
    MULS    r3, r7, r6, r5          @ du
    MULS    r4, r8, r6, r5          @ dv
    mov     r3, r3, asr #6
    mov     r4, r4, asr #6
    add     r7, r4, r3, lsl #16     @ duv
    mov     r10, r10, asr #6
    mov     r11, r11, lsl #10
    mov     r11, r11, lsr #16
    add     r3, r11, r10, lsl #16   @ uv
    ldr     r10, [r0]
    ldr     r11, [r0, #4]
    rsb     r11, r11, r11, lsl #4
    add     r10, r10, r11, lsl #4
    add     r10, r10, r1            @ fb + row * 240 + first column
    ldr     r1, [r0, #76]
    ldr     r2, [r0, #80]
    bl      .Lrs_px
    ldr     r1, [sp, #RS_C]
    ldr     r2, [sp, #RS_CE]
    cmp     r1, r2
    ble     .Lrs_seg
    b       .Lrs_next

@ RS_U, RS_V = (u/z, v/z) / (1/z) at RS_UW..RS_W; clobbers r3-r6, r12
.Lrs_exact:
    ldmia   sp, {r3-r5}
    cmp     r5, #0x100
    movlt   r5, #0x100
    ldr     r12, =rcp_tab
    RCP     r6, r5, r5, r12
    MULS    r5, r3, r6, r12
    MULS    r3, r4, r6, r12
    str     r5, [sp, #RS_U]
    str     r3, [sp, #RS_V]
    bx      lr

@ r9 >= 1 pixels from r10 (uv r3 stepping by duv r7; tex r1, colour map r2;
@ half: one sample per pixel pair); r3-r6, r8-r10 clobbered
.Lrs_px:
    tst     r10, #1
    beq     4f
    TEX     r4, r3, r5, r1          @ odd first column: high byte
    add     r3, r3, r7
    ldrb    r4, [r2, r4]
    ldrb    r5, [r10, #-1]
    orr     r4, r5, r4, lsl #8
    strh    r4, [r10, #-1]
    add     r10, r10, #1
    subs    r9, r9, #1
    bxeq    lr
4:  ldr     r8, [r0, #88]           @ half: one sample per pixel pair
    cmp     r8, #0
    bne     40f
    subs    r9, r9, #2
    blt     6f
5:  TEX     r4, r3, r5, r1
    add     r3, r3, r7
    TEX     r6, r3, r5, r1
    add     r3, r3, r7
    ldrb    r4, [r2, r4]
    ldrb    r6, [r2, r6]
    orr     r4, r4, r6, lsl #8
    strh    r4, [r10], #2
    subs    r9, r9, #2
    bge     5b
    b       6f
40: add     r8, r7, r7
    subs    r9, r9, #2
    blt     6f
41: TEX     r4, r3, r5, r1
    add     r3, r3, r8
    ldrb    r4, [r2, r4]
    orr     r4, r4, r4, lsl #8
    strh    r4, [r10], #2
    subs    r9, r9, #2
    bge     41b
6:  adds    r9, r9, #2
    bxeq    lr
    TEX     r4, r3, r5, r1          @ last column even: low byte
    ldrb    r4, [r2, r4]
    ldrb    r5, [r10, #1]
    orr     r4, r4, r5, lsl #8
    strh    r4, [r10]
    bx      lr
    .pool

@ ---------------------------------------------------------------------------
@ void col_mask(u8 *p, int n, const u8 *pix, const u8 *cm, u32 tp, u32 step)
@   one sprite column (p = pixel address of the first row); texel 0 is
@   transparent, the other pixel of each pair is kept
@ ---------------------------------------------------------------------------
    .global col_mask
    .type col_mask, %function
col_mask:
    PCNT    7, r1
    cmp     r1, #0
    bxle    lr
    stmfd   sp!, {r4-r7, lr}
    ldr     r4, [sp, #20]           @ tp
    ldr     r5, [sp, #24]           @ step
    tst     r0, #1
    bne     3f
1:  ldrb    r6, [r2, r4, lsr #16]   @ even column: low byte
    add     r4, r4, r5
    cmp     r6, #0
    beq     2f
    ldrb    r6, [r3, r6]
    ldrb    r7, [r0, #1]
    orr     r6, r6, r7, lsl #8
    strh    r6, [r0]
2:  add     r0, r0, #240
    subs    r1, r1, #1
    bne     1b
    ldmfd   sp!, {r4-r7, lr}
    bx      lr
3:  sub     r0, r0, #1              @ odd column: high byte
4:  ldrb    r6, [r2, r4, lsr #16]
    add     r4, r4, r5
    cmp     r6, #0
    beq     5f
    ldrb    r6, [r3, r6]
    ldrb    r7, [r0]
    orr     r6, r7, r6, lsl #8
    strh    r6, [r0]
5:  add     r0, r0, #240
    subs    r1, r1, #1
    bne     4b
    ldmfd   sp!, {r4-r7, lr}
    bx      lr

@ ---------------------------------------------------------------------------
@ void col_mask2(u8 *p, int n, const u8 *pix, const u8 *cm, u32 tp, u32 step)
@   one sprite column drawn into both pixels of a pair (p even, far or
@   lowest detail); texel 0 is transparent
@ ---------------------------------------------------------------------------
    .global col_mask2
    .type col_mask2, %function
col_mask2:
    PCNT    7, r1
    cmp     r1, #0
    bxle    lr
    stmfd   sp!, {r4-r6, lr}
    ldr     r4, [sp, #16]           @ tp
    ldr     r5, [sp, #20]           @ step
1:  ldrb    r6, [r2, r4, lsr #16]
    add     r4, r4, r5
    cmp     r6, #0
    ldrneb  r6, [r3, r6]
    orrne   r6, r6, r6, lsl #8
    strneh  r6, [r0]
    add     r0, r0, #240
    subs    r1, r1, #1
    bne     1b
    ldmfd   sp!, {r4-r6, lr}
    bx      lr

@ ---------------------------------------------------------------------------
@ Wall-like prop faces (vertical quads), column by column.
@ VFace:
@  0 fb   4 c0   8 c1  (columns, inclusive)
@ 12 yt  16 yb  (16.16 rows + 0x7FFF, so >> 16 rounds)  20 w (1/z)  24 uw (u/z)
@      at the centre of column c0 & ~1 (vface_half: of that pair)
@ 28 dyt 32 dyb 36 dw 40 duw   (per column; vface_half: per pair)
@ 44 tex   (column-major texture at the chosen level)
@ 48 ptex  (the level's P0 pair layout; P1 follows at ptex + psz)
@ 52 vt    (texel row at the top edge, 16.16)
@ 56 kstep (texel rows per screen row = kstep * depth: the face is a parallelogram)
@ 60 mask  (texel columns - 1)   64 cshift (log2 texel rows)   68 psz
@ 72 flags (1: one light (cm0), 2: no lintel can hide it, 4: in front of every wall,
@          8: a trapezoid, step = vr / screen height)
@ 76 cm0   80 lt[16] (light per flashlight cone class)   96 vr (texel rows top to bottom)
@ ---------------------------------------------------------------------------
    .equ VF_C0, 4
    .equ VF_C1, 8
    .equ VF_TEX, 44
    .equ VF_PTEX, 48
    .equ VF_VT, 52
    .equ VF_KSTEP, 56
    .equ VF_MASK, 60
    .equ VF_CSHIFT, 64
    .equ VF_PSZ, 68
    .equ VF_FLAGS, 72
    .equ VF_CM0, 76
    .equ VF_LT, 80
    .equ VF_VR, 96

@ column r4 (interpolants r5 yt, r6 yb, r7 w, r8 uw; VFace r11) into side
@ r10 (0 = A, 4 = B) of the ColPair at sp; its texel column index goes to
@ [sp + 60 + r10]. Clobbers r0-r3, r9, r12.
.Lvc:
    add     r3, sp, r10
    ldr     r12, =rcp_tab
    RCP     r0, r7, r1, r12         @ r0 = depth
    ldr     r9, [r11, #VF_FLAGS]
    tst     r9, #4
    bne     1f
    ldr     r1, =g_zbuf
    ldr     r1, [r1, r4, lsl #2]
    cmp     r0, r1
    bge     8f                      @ behind the wall
1:  mov     r1, r5, asr #16         @ first row
    mov     r2, r6, asr #16         @ end row
    tst     r9, #2
    bne     2f
    ldr     r12, =g_clipDepth
    ldr     r12, [r12, r4, lsl #2]
    cmp     r0, r12
    ble     2f
    ldr     r12, =g_clipTop         @ behind an opening: not above its lintel
    add     r12, r12, r4, lsl #1
    ldrsh   r12, [r12]
    cmp     r1, r12
    movlt   r1, r12
2:  cmp     r1, #ROW0
    movlt   r1, #ROW0
    cmp     r2, #ROW1
    movgt   r2, #ROW1
    cmp     r1, r2
    bge     8f
    str     r1, [r3, #4]
    str     r2, [r3, #12]
    @ texel column: the high word of uw * depth is the integer u
    smull   r12, r2, r8, r0
    ldr     r12, [r11, #VF_MASK]
    and     r2, r2, r12
    str     r2, [r3, #60]
    ldr     r12, [r11, #VF_CSHIFT]
    ldr     r9, [r11, #VF_TEX]
    add     r2, r9, r2, lsl r12
    str     r2, [r3, #20]
    @ step = kstep * depth (a parallelogram), else vr / screen height
    ldr     r9, [r11, #VF_FLAGS]
    tst     r9, #8
    bne     4f
    ldr     r12, [r11, #VF_KSTEP]
    smull   r9, r2, r12, r0
    mov     r9, r9, lsr #16
    orr     r2, r9, r2, lsl #16
    b       5f
4:  sub     r9, r6, r5
    cmp     r9, #0x1000
    movlt   r9, #0x1000
    ldr     r12, =rcp_tab
    RCP     r2, r9, r0, r12
    ldr     r12, [r11, #VF_VR]
    smull   r9, r0, r12, r2
    mov     r9, r9, lsr #16
    orr     r2, r9, r0, lsl #16
5:  str     r2, [r3, #44]
    @ tp = vt + (row centre - top edge) * step
    rsb     r9, r5, r1, lsl #16
    add     r9, r9, #0x10000
    sub     r9, r9, #1
    smull   r12, r9, r2, r9
    mov     r12, r12, lsr #16
    orr     r12, r12, r9, lsl #16
    ldr     r9, [r11, #VF_VT]
    adds    r12, r12, r9
    movmi   r12, #0
    str     r12, [r3, #36]
    @ light
    ldr     r9, [r11, #VF_FLAGS]
    tst     r9, #1
    ldrne   r12, [r11, #VF_CM0]
    bne     3f
    ldr     r9, =g_coneOf
    ldrb    r9, [r9, r4]
    add     r9, r9, r11
    ldrb    r9, [r9, #VF_LT]
    ldr     r12, =g_colormap
    add     r12, r12, r9, lsl #8
3:  str     r12, [r3, #28]
    bx      lr
8:  mov     r9, #1                  @ nothing: an empty span
    str     r9, [r3, #4]
    mov     r9, #0
    str     r9, [r3, #12]
    bx      lr
    .pool

@ ---------------------------------------------------------------------------
@ void vface_pair(VFace *s)   every column, the two of a pair drawn together:
@   one texel column for both (magnified) -> one sample per halfword;
@   neighbouring texel columns -> one 16-bit read of the pair layout per row;
@   else each column with its own texel column (col_pair)
@ ---------------------------------------------------------------------------
    .global vface_pair
    .type vface_pair, %function
vface_pair:
    stmfd   sp!, {r4-r11, lr}
    sub     sp, sp, #68             @ ColPair (60) + texel column of A and B
    mov     r11, r0
    ldr     r4, [r11, #VF_C0]
    bic     r4, r4, #1              @ first (even) column
    add     r0, r11, #12
    ldmia   r0, {r5-r8}             @ yt yb w uw
1:  ldr     r0, [r11]
    add     r0, r0, r4
    str     r0, [sp]                @ cp.p
    mov     r0, #0
    str     r0, [sp, #56]           @ pmode 0
    @ side A (column r4) unless left of the face
    mov     r10, #0
    ldr     r0, [r11, #VF_C0]
    cmp     r4, r0
    blt     10f
    bl      .Lvc
    b       11f
10: mov     r9, #1
    str     r9, [sp, #4]
    mov     r9, #0
    str     r9, [sp, #12]
11: bl      .Lvstep
    add     r4, r4, #1
    @ side B (column r4 + 1) unless right of the face
    mov     r10, #4
    ldr     r0, [r11, #VF_C1]
    cmp     r4, r0
    bgt     12f
    bl      .Lvc
    b       13f
12: mov     r9, #1
    str     r9, [sp, #8]
    mov     r9, #0
    str     r9, [sp, #16]
13: bl      .Lvstep
    sub     r4, r4, #1
    @ which sides draw?
    ldr     r0, [sp, #4]
    ldr     r1, [sp, #12]
    cmp     r0, r1
    bge     4f                      @ A empty: col_pair (B alone, if any)
    ldr     r2, [sp, #8]
    ldr     r3, [sp, #16]
    cmp     r2, r3
    bge     2f                      @ B empty: A alone
    @ both. Outside the full-resolution band: one sample for both columns
    ldr     r12, =g_fullC0
    ldmia   r12, {r2, r3}
    add     r12, r4, #1
    cmp     r12, r2
    blt     5f
    cmp     r4, r3
    bge     5f
    ldr     r2, [sp, #60]           @ texel columns
    ldr     r3, [sp, #64]
    subs    r9, r3, r2
    bne     6f
    @ the same texel column: one sample per halfword if the light, the rows
    @ (within one) and the scale (within half a texel over the view) agree
    ldr     r2, [sp, #28]
    ldr     r3, [sp, #32]
    cmp     r2, r3
    bne     2f
    ldr     r2, [sp, #8]
    subs    r2, r2, r0
    rsbmi   r2, r2, #0
    cmp     r2, #1
    bgt     2f
    ldr     r2, [sp, #16]
    subs    r2, r2, r1
    rsbmi   r2, r2, #0
    cmp     r2, #1
    bgt     2f
    ldr     r2, [sp, #44]
    ldr     r3, [sp, #48]
    subs    r3, r3, r2
    rsbmi   r3, r3, #0
    cmp     r3, #468
    bge     2f
5:  @ wall_column(p + a0 * 240, tex, cm, tp, step, a1 - a0): A for both
    ldr     r2, [sp, #44]
    sub     r1, r1, r0
    ldr     r12, [sp]
    rsb     r0, r0, r0, lsl #4
    add     r0, r12, r0, lsl #4
    str     r1, [sp, #-4]!
    str     r2, [sp, #-4]!
    ldr     r1, [sp, #8 + 20]
    ldr     r2, [sp, #8 + 28]
    ldr     r3, [sp, #8 + 36]
    bl      wall_column
    add     sp, sp, #8
    b       3f
6:  @ neighbouring texel columns: the pair layouts give both texels at once
    cmp     r9, #1
    moveq   r12, #1
    ldreq   r2, [sp, #60]           @ pair starts at A's column, A low byte
    beq     7f
    cmn     r9, #1
    bne     2f
    mov     r12, #2
    ldr     r2, [sp, #64]           @ starts at B's column, A high byte
7:  str     r12, [sp, #56]
    ldr     r0, [r11, #VF_PTEX]
    tst     r2, #1
    ldrne   r1, [r11, #VF_PSZ]
    addne   r0, r0, r1              @ odd start: P1
    ldr     r1, [r11, #VF_CSHIFT]
    add     r1, r1, #1
    mov     r2, r2, lsr #1
    add     r0, r0, r2, lsl r1      @ + (start / 2) * 2 * rows
    str     r0, [sp, #52]
    b       2f
4:  ldr     r0, [sp, #8]
    ldr     r1, [sp, #16]
    cmp     r0, r1
    bge     3f                      @ neither
2:  mov     r0, sp
    bl      col_pair
3:  add     r4, r4, #2
    ldr     r0, [r11, #VF_C1]
    cmp     r4, r0
    ble     1b
    add     sp, sp, #68
    ldmfd   sp!, {r4-r11, lr}
    bx      lr

.Lvstep:                            @ interpolants to the next column (or pair)
    add     r0, r11, #28
    ldmia   r0, {r0-r3}
    add     r5, r5, r0
    add     r6, r6, r1
    add     r7, r7, r2
    add     r8, r8, r3
    bx      lr
    .pool

@ ---------------------------------------------------------------------------
@ void vface_half(VFace *s)   far faces: one texel per column pair. The
@   interpolants are at the centre of the first pair (c0 & ~1) and step per
@   pair; the texture column, scale and depth come from the pair's centre,
@   but each column keeps its own rows (the silhouette stays exact). Rows
@   both columns cover are written whole (one lookup for both when they share
@   a light), rows only one covers are merged with the pixel already there.
@ ---------------------------------------------------------------------------
    .equ VH_YA0, 0              @ rows [y0, y1) of columns A and B (y0 = 255: none)
    .equ VH_YA1, 4
    .equ VH_YB0, 8
    .equ VH_YB1, 12
    .equ VH_DYTC, 16            @ top and bottom edge steps per column
    .equ VH_DYBC, 20
    .equ VH_CMA, 24             @ colour maps of A and B
    .equ VH_CMB, 28
    .equ VH_RET, 32             @ the row loops' return address
    .equ VH_R4, 36
    .equ VH_SIZE, 40

    .global vface_half
    .type vface_half, %function
vface_half:
    stmfd   sp!, {r4-r11, lr}
    sub     sp, sp, #VH_SIZE
    mov     r11, r0
    ldr     r4, [r11, #VF_C0]
    bic     r4, r4, #1              @ r4 = the pair's even column
    add     r0, r11, #12
    ldmia   r0, {r5-r8}             @ yt yb w uw at the first pair's centre
    ldr     r0, [r11, #28]
    ldr     r1, [r11, #32]
    mov     r2, r0, asr #1
    mov     r3, r1, asr #1
    str     r2, [sp, #VH_DYTC]
    str     r3, [sp, #VH_DYBC]
    sub     r5, r5, r0, asr #2      @ r5, r6: column A's edges, half a
    sub     r6, r6, r1, asr #2      @ column before the centre
.Lvh_pair:
    ldr     r12, =rcp_tab
    RCP     r9, r7, r1, r12         @ r9 = the pair's depth
    mov     r0, r5, asr #16         @ rows: A r0..r1, B r2..r3
    mov     r1, r6, asr #16
    ldr     r12, [sp, #VH_DYTC]
    add     r2, r5, r12
    mov     r2, r2, asr #16
    ldr     r12, [sp, #VH_DYBC]
    add     r3, r6, r12
    mov     r3, r3, asr #16
    ldr     r12, [r11, #VF_C0]
    cmp     r4, r12
    movlt   r1, #0                  @ A left of the face
    ldr     r12, [r11, #VF_C1]
    cmp     r4, r12
    movge   r3, #0                  @ B right of it
    ldr     r10, [r11, #VF_FLAGS]
    tst     r10, #4
    bne     1f
    ldr     r12, =g_zbuf            @ behind the walls
    add     r12, r12, r4, lsl #2
    ldmia   r12, {r12, lr}
    cmp     r9, r12
    movge   r1, #0
    cmp     r9, lr
    movge   r3, #0
1:  tst     r10, #2
    bne     2f
    ldr     r12, =g_clipDepth       @ behind an opening: not above its lintel
    add     r12, r12, r4, lsl #2
    ldmia   r12, {r12, lr}
    cmp     r9, r12
    ble     3f
    ldr     r12, =g_clipTop
    add     r12, r12, r4, lsl #1
    ldrsh   r12, [r12]
    cmp     r0, r12
    movlt   r0, r12
3:  cmp     r9, lr
    ble     2f
    ldr     r12, =g_clipTop
    add     r12, r12, r4, lsl #1
    ldrsh   r12, [r12, #2]
    cmp     r2, r12
    movlt   r2, r12
2:  cmp     r0, #ROW0
    movlt   r0, #ROW0
    cmp     r2, #ROW0
    movlt   r2, #ROW0
    cmp     r1, #ROW1
    movgt   r1, #ROW1
    cmp     r3, #ROW1
    movgt   r3, #ROW1
    cmp     r0, r1
    movge   r0, #255                @ A: nothing
    cmp     r2, r3
    movge   r2, #255                @ B: nothing
    and     r12, r0, r2
    cmp     r12, #255
    beq     .Lvh_next
    stmia   sp, {r0-r3}
    @ the texel column at the pair's centre: the high word of uw * depth
    smull   r12, lr, r8, r9
    ldr     r12, [r11, #VF_MASK]
    and     lr, lr, r12
    ldr     r12, [r11, #VF_CSHIFT]
    ldr     r1, [r11, #VF_TEX]
    add     r1, r1, lr, lsl r12     @ r1 = the texel column (kept)
    @ texel rows per screen row: kstep * depth, or vr / height (trapezoid)
    tst     r10, #8
    bne     4f
    ldr     r12, [r11, #VF_KSTEP]
    smull   r0, lr, r12, r9
    mov     r0, r0, lsr #16
    orr     r9, r0, lr, lsl #16     @ r9 = step (kept)
    b       5f
4:  ldr     r12, [sp, #VH_DYBC]
    ldr     r0, [sp, #VH_DYTC]
    sub     r12, r12, r0
    sub     r0, r6, r5
    add     r0, r0, r12, asr #1     @ the height at the centre
    cmp     r0, #0x1000
    movlt   r0, #0x1000
    ldr     r12, =rcp_tab
    RCP     r2, r0, r3, r12
    ldr     r12, [r11, #VF_VR]
    smull   r0, lr, r12, r2
    mov     r0, r0, lsr #16
    orr     r9, r0, lr, lsl #16
5:  tst     r10, #1                 @ light
    ldrne   r2, [r11, #VF_CM0]
    movne   r3, r2
    bne     6f
    ldr     r12, =g_coneOf
    add     r12, r12, r4
    ldrb    r2, [r12]
    ldrb    r3, [r12, #1]
    add     r2, r2, r11
    ldrb    r2, [r2, #VF_LT]
    add     r3, r3, r11
    ldrb    r3, [r3, #VF_LT]
    ldr     r12, =g_colormap
    add     r2, r12, r2, lsl #8
    add     r3, r12, r3, lsl #8
6:  str     r2, [sp, #VH_CMA]
    str     r3, [sp, #VH_CMB]
    ldmia   sp, {r0, r2, r3, r10}   @ yA0 yA1 yB0 yB1
    cmp     r0, #255
    beq     .Lvh_bonly
    cmp     r3, #255
    beq     .Lvh_aonly
    cmp     r0, r3
    movge   r12, r0                 @ max(y0)
    movlt   r12, r3
    cmp     r2, r10
    movle   lr, r2                  @ min(y1)
    movgt   lr, r10
    cmp     r12, lr
    bge     .Lvh_apart
    @ from the higher top: that column alone, then both, then the column
    @ that goes on lower alone
    cmp     r0, r3
    movgt   r0, r3
    bl      .Lvh_at
    ldr     r2, [sp, #VH_YA0]
    ldr     r12, [sp, #VH_YB0]
    subs    r10, r12, r2
    bgt     10f
    rsbs    r10, r10, #0
    blgt    .Lvh_rb
    b       11f
10: bl      .Lvh_ra
11: ldmia   sp, {r2, r10, r12, lr}  @ yA0 yA1 yB0 yB1
    cmp     r2, r12
    movlt   r2, r12
    cmp     r10, lr
    movgt   r10, lr
    sub     r10, r10, r2
    bl      .Lvh_rab
    ldr     r2, [sp, #VH_YA1]
    ldr     r12, [sp, #VH_YB1]
    subs    r10, r2, r12
    bgt     12f
    rsbs    r10, r10, #0
    blgt    .Lvh_rb
    b       .Lvh_next
12: bl      .Lvh_ra
    b       .Lvh_next
.Lvh_aonly:                         @ r0 = yA0, r2 = yA1
    sub     r10, r2, r0
    bl      .Lvh_at
    bl      .Lvh_ra
    b       .Lvh_next
.Lvh_bonly:                         @ r3 = yB0, r10 = yB1
    sub     r10, r10, r3
    mov     r0, r3
    bl      .Lvh_at
    bl      .Lvh_rb
    b       .Lvh_next
.Lvh_apart:                         @ no rows in common: A, then B
    sub     r10, r2, r0
    bl      .Lvh_at
    bl      .Lvh_ra
    ldr     r0, [sp, #VH_YB0]
    ldr     r10, [sp, #VH_YB1]
    sub     r10, r10, r0
    bl      .Lvh_at
    bl      .Lvh_rb
.Lvh_next:
    add     r0, r11, #28            @ interpolants to the next pair
    ldmia   r0, {r0-r3}
    add     r5, r5, r0
    add     r6, r6, r1
    add     r7, r7, r2
    add     r8, r8, r3
    add     r4, r4, #2
    ldr     r0, [r11, #VF_C1]
    cmp     r4, r0
    ble     .Lvh_pair
    add     sp, sp, #VH_SIZE
    ldmfd   sp!, {r4-r11, lr}
    bx      lr

@ r0 = a row -> r0 = the pair's address in it, r3 = the texel position there
@ (from the pair centre's top edge); clobbers r2, r12
.Lvh_at:
    ldr     r12, [sp, #VH_DYTC]
    add     r12, r5, r12, asr #1    @ the pair's top edge (+ 0x7FFF)
    rsb     r12, r12, r0, lsl #16
    add     r12, r12, #0xFF00
    add     r12, r12, #0xFF         @ row centre - top edge
    smull   r2, r3, r12, r9
    mov     r2, r2, lsr #16
    orr     r3, r2, r3, lsl #16
    ldr     r2, [r11, #VF_VT]
    adds    r3, r3, r2
    movmi   r3, #0
    ldr     r2, [r11]
    add     r2, r2, r4
    rsb     r0, r0, r0, lsl #4
    add     r0, r2, r0, lsl #4      @ fb + column + row * 240
    bx      lr

@ r10 >= 1 rows from r0 (texel position r3, step r9, texel column r1):
@ column A alone (low byte, B's pixel kept), B alone, or both
.Lvh_ra:
    str     lr, [sp, #VH_RET]
#ifdef PIXCNT
    PCNT    12, r10
#endif
    ldr     r2, [sp, #VH_CMA]
1:  ldrb    r12, [r1, r3, lsr #16]
    add     r3, r3, r9
    ldrb    r12, [r2, r12]
    ldrb    lr, [r0, #1]
    orr     r12, r12, lr, lsl #8
    strh    r12, [r0], #240
    subs    r10, r10, #1
    bne     1b
    ldr     pc, [sp, #VH_RET]
.Lvh_rb:
    str     lr, [sp, #VH_RET]
#ifdef PIXCNT
    PCNT    12, r10
#endif
    ldr     r2, [sp, #VH_CMB]
1:  ldrb    r12, [r1, r3, lsr #16]
    add     r3, r3, r9
    ldrb    r12, [r2, r12]
    ldrb    lr, [r0]
    orr     r12, lr, r12, lsl #8
    strh    r12, [r0], #240
    subs    r10, r10, #1
    bne     1b
    ldr     pc, [sp, #VH_RET]
.Lvh_rab:
    str     lr, [sp, #VH_RET]
#ifdef PIXCNT
    mov     r2, r10, lsl #1
    PCNT    12, r2
#endif
    ldr     r2, [sp, #VH_CMA]
    ldr     lr, [sp, #VH_CMB]
    cmp     r2, lr
    bne     3f
    ldr     r12, =g_vhalf
    ldr     r12, [r12]
    cmp     r12, #0
    bne     20f
    tst     r10, #1                 @ one light: one lookup for both
    beq     2f
    ldrb    r12, [r1, r3, lsr #16]
    add     r3, r3, r9
    ldrb    r12, [r2, r12]
    orr     r12, r12, r12, lsl #8
    strh    r12, [r0], #240
    subs    r10, r10, #1
    beq     9f
2:  ldrb    r12, [r1, r3, lsr #16]
    add     r3, r3, r9
    ldrb    lr, [r1, r3, lsr #16]
    add     r3, r3, r9
    ldrb    r12, [r2, r12]
    ldrb    lr, [r2, lr]
    orr     r12, r12, r12, lsl #8
    orr     lr, lr, lr, lsl #8
    strh    r12, [r0], #240
    strh    lr, [r0], #240
    subs    r10, r10, #2
    bne     2b
9:  ldr     pc, [sp, #VH_RET]
20: add     lr, r9, r9              @ the lowest detail: one sample per two rows
21: ldrb    r12, [r1, r3, lsr #16]
    add     r3, r3, lr
    ldrb    r12, [r2, r12]
    orr     r12, r12, r12, lsl #8
    strh    r12, [r0], #240
    subs    r10, r10, #1
    subeq   r3, r3, r9              @ (an odd count: one row less)
    beq     9b
    strh    r12, [r0], #240
    subs    r10, r10, #1
    bne     21b
    ldr     pc, [sp, #VH_RET]
3:  str     r4, [sp, #VH_R4]        @ two lights (r4 borrowed)
4:  ldrb    r12, [r1, r3, lsr #16]
    add     r3, r3, r9
    ldrb    r4, [lr, r12]
    ldrb    r12, [r2, r12]
    orr     r12, r12, r4, lsl #8
    strh    r12, [r0], #240
    subs    r10, r10, #1
    bne     4b
    ldr     r4, [sp, #VH_R4]
    ldr     pc, [sp, #VH_RET]
    .pool

@ ---------------------------------------------------------------------------
@ void pspan_pair(PSpan *s)    convex polygon from the outline buffers
@  0 fb   4 c0   8 c1   12 fnear (nearest depth, 16.16)   16 tex (64x64)
@ 20 lt[16]: final light level per flashlight cone class
@ g_ol: { s16 yA[240], yB[240] (rows 12.4); u32 uvA[240], uvB[240] (u|v 9.7) }
@ ---------------------------------------------------------------------------
    .global pspan_pair
    .type pspan_pair, %function
pspan_pair:
    stmfd   sp!, {r4-r11, lr}
    sub     sp, sp, #48             @ ColPairUV
    mov     r11, r0
    ldr     r0, [r11, #16]
    str     r0, [sp, #20]           @ cp.tex
    ldr     r4, [r11, #4]
    bic     r4, r4, #1
1:  ldr     r0, [r11]
    add     r0, r0, r4
    str     r0, [sp]
    mov     r10, #0
    bl      .Lpcol
    add     r4, r4, #1
    mov     r10, #4
    bl      .Lpcol
    sub     r4, r4, #1
    ldr     r0, [sp, #4]
    ldr     r1, [sp, #12]
    cmp     r0, r1
    blt     2f
    ldr     r0, [sp, #8]
    ldr     r1, [sp, #16]
    cmp     r0, r1
    bge     3f
2:  @ both sides drawn and outside the full-resolution band: side A for both
    ldr     r0, [sp, #4]
    ldr     r1, [sp, #12]
    cmp     r0, r1
    bge     6f
    ldr     r2, [sp, #8]
    ldr     r3, [sp, #16]
    cmp     r2, r3
    bge     6f
    ldr     r12, =g_fullC0
    ldmia   r12, {r2, r3}
    add     r12, r4, #1
    cmp     r12, r2
    blt     7f
    cmp     r4, r3
    blt     6f
7:  @ col_uv2(p + a0 * 240, n, tex, cm, uv, duv)
    sub     r1, r1, r0
    ldr     r12, [sp]
    rsb     r0, r0, r0, lsl #4
    add     r0, r12, r0, lsl #4
    ldr     r2, [sp, #20]
    ldr     r3, [sp, #24]
    ldr     r12, [sp, #32]
    ldr     r9, [sp, #40]
    sub     sp, sp, #8
    str     r12, [sp]
    str     r9, [sp, #4]
    bl      col_uv2
    add     sp, sp, #8
    b       3f
6:  mov     r0, sp
    bl      col_pair_uv
3:  add     r4, r4, #2
    ldr     r0, [r11, #8]
    cmp     r4, r0
    ble     1b
    add     sp, sp, #48
    ldmfd   sp!, {r4-r11, lr}
    bx      lr

@ column r4 into side r10 of the ColPairUV at sp
.Lpcol:
    add     r3, sp, r10
    ldr     r0, [r11, #4]
    cmp     r4, r0
    blt     8f
    ldr     r0, [r11, #8]
    cmp     r4, r0
    bgt     8f
    ldr     r2, [r11, #12]          @ fnear
    ldr     r0, =g_zbuf
    ldr     r0, [r0, r4, lsl #2]
    cmp     r2, r0
    bge     8f
    ldr     r0, =g_ol
    add     r1, r0, r4, lsl #1
    ldrsh   r5, [r1]                @ yA
    add     r1, r1, #480
    ldrsh   r6, [r1]                @ yB
    add     r1, r0, r4, lsl #2
    ldr     r7, [r1, #960]          @ uvA
    ldr     r8, [r1, #1920]         @ uvB
    cmp     r5, r6
    movgt   r1, r5
    movgt   r5, r6
    movgt   r6, r1
    movgt   r1, r7
    movgt   r7, r8
    movgt   r8, r1
    add     r9, r5, #7
    mov     r9, r9, asr #4          @ y0
    add     r1, r6, #7
    mov     r1, r1, asr #4          @ y1
    ldr     r0, =g_clipDepth
    ldr     r0, [r0, r4, lsl #2]
    cmp     r2, r0
    movle   r0, #ROW0
    ldrgt   r0, =g_clipTop
    addgt   r0, r0, r4, lsl #1
    ldrgtsh r0, [r0]
    cmp     r9, r0
    movlt   r9, r0
    cmp     r1, #ROW1
    movgt   r1, #ROW1
    cmp     r9, r1
    bge     8f
    str     r9, [r3, #4]
    str     r1, [r3, #12]
    @ 1 / outline height (at least one row)
    ldr     r12, =rcp_tab
    sub     r0, r6, r5
    mov     r0, r0, lsl #12
    cmp     r0, #0x10000
    movlt   r0, #0x10000
    RCP     r6, r0, r1, r12         @ r6 = 1 / height
    @ du (6.10 per row)
    mov     r2, r7, lsr #16         @ uA (9.7)
    rsb     r0, r2, r8, lsr #16
    mov     r0, r0, lsl #16
    mov     r0, r0, asr #13
    smull   r1, r12, r0, r6
    mov     r1, r1, lsr #16
    orr     r1, r1, r12, lsl #16    @ du
    @ dv
    mov     r0, r7, lsl #16
    rsb     r12, r0, r8, lsl #16
    mov     r12, r12, asr #13
    smull   r0, r8, r12, r6
    mov     r0, r0, lsr #16
    orr     r0, r0, r8, lsl #16     @ dv
    @ offset of the first row centre below the outline
    mov     r6, r9, lsl #16
    add     r6, r6, #0x8000
    sub     r6, r6, r5, lsl #12
    smull   r8, r12, r6, r1
    mov     r8, r8, lsr #16
    orr     r8, r8, r12, lsl #16
    add     r8, r8, r2, lsl #3      @ u0
    smull   r2, r12, r6, r0
    mov     r2, r2, lsr #16
    orr     r2, r2, r12, lsl #16
    mov     r7, r7, lsl #16
    add     r2, r2, r7, lsr #13     @ v0
    mov     r2, r2, lsl #16
    mov     r2, r2, lsr #16
    add     r7, r2, r8, lsl #16     @ uv
    add     r8, r0, r1, lsl #16     @ duv
    str     r7, [r3, #32]
    str     r8, [r3, #40]
    @ light from the face's cone table
    ldr     r2, =g_coneOf
    ldrb    r2, [r2, r4]
    add     r2, r2, r11
    ldrb    r2, [r2, #20]
    ldr     r0, =g_colormap
    add     r0, r0, r2, lsl #8
    str     r0, [r3, #24]
    bx      lr
8:  mov     r9, #1
    str     r9, [r3, #4]
    mov     r9, #0
    str     r9, [r3, #12]
    bx      lr
    .pool

@ ---------------------------------------------------------------------------
@ void pspan_half(PSpan *s)   convex polygon, one sample per column pair
@   (the pair's first column inside the face decides it)
@ ---------------------------------------------------------------------------
    .global pspan_half
    .type pspan_half, %function
pspan_half:
    stmfd   sp!, {r4-r11, lr}
    sub     sp, sp, #48             @ ColPairUV (side A used)
    mov     r11, r0
    ldr     r0, [r11, #16]
    str     r0, [sp, #20]
    ldr     r4, [r11, #4]
    bic     r4, r4, #1
1:  ldr     r0, [r11, #4]
    cmp     r4, r0
    addlt   r4, r4, #1
    mov     r10, #0
    bl      .Lpcol
    ldr     r0, [sp, #4]
    ldr     r1, [sp, #12]
    subs    r9, r1, r0
    ble     3f
    ldr     r1, [r11]
    add     r1, r1, r4
    rsb     r2, r0, r0, lsl #4
    add     r10, r1, r2, lsl #4
    tst     r4, #1
    bne     2f
    ldr     r1, [r11, #8]
    add     r2, r4, #1
    cmp     r2, r1
    bgt     2f
    ldr     r1, [r11, #12]          @ fnear
    ldr     r3, =g_zbuf
    ldr     r3, [r3, r2, lsl #2]
    cmp     r1, r3
    bge     2f
    @ both: col_uv2(p, n, tex, cm, uv, duv)
    mov     r0, r10
    mov     r1, r9
    ldr     r2, [sp, #20]
    ldr     r3, [sp, #24]
    ldr     r12, [sp, #32]          @ uv
    ldr     r9, [sp, #40]           @ duv
    sub     sp, sp, #8
    str     r12, [sp]
    str     r9, [sp, #4]
    bl      col_uv2
    add     sp, sp, #8
    b       3f
2:  @ one column: col_pair_uv with side B empty (pair address in p)
    bic     r0, r4, #1
    ldr     r1, [r11]
    add     r1, r1, r0
    str     r1, [sp]
    tst     r4, #1
    beq     4f
    @ the odd column: move side A to side B
    ldr     r0, [sp, #4]
    str     r0, [sp, #8]
    ldr     r0, [sp, #12]
    str     r0, [sp, #16]
    ldr     r0, [sp, #24]
    str     r0, [sp, #28]
    ldr     r0, [sp, #32]
    str     r0, [sp, #36]
    ldr     r0, [sp, #40]
    str     r0, [sp, #44]
    mov     r0, #1
    str     r0, [sp, #4]
    mov     r0, #0
    str     r0, [sp, #12]
    b       5f
4:  mov     r0, #1
    str     r0, [sp, #8]
    mov     r0, #0
    str     r0, [sp, #16]
5:  mov     r0, sp
    bl      col_pair_uv
3:  bic     r4, r4, #1
    add     r4, r4, #2
    ldr     r0, [r11, #8]
    cmp     r4, r0
    ble     1b
    add     sp, sp, #48
    ldmfd   sp!, {r4-r11, lr}
    bx      lr
    .pool

@ ---------------------------------------------------------------------------
@ void chain_walk(ChainArgs *a)   one outline chain of a convex polygon into
@   the per-column edge buffers: ey[c] = row (12.4, clamped to +-32000),
@   euv[c] = u >> 9 << 16 | v >> 9 (u, v 16.16 texels)
@ ChainArgs: 0 p (PV: x y w u v, 20 bytes)  4 list (u8 vertex indices)
@   8 len  12 c0  16 c1  20 ey (column 0)  24 euv (column 0)
@   28 persp (u, v are u/z, v/z: exact every 8 columns, linear between)
@ ---------------------------------------------------------------------------
.macro MUL16 out, a, b, t          @ out = (a * b) >> 16 (signed); out, a, t distinct
    smull   \t, \out, \a, \b
    mov     \t, \t, lsr #16
    orr     \out, \t, \out, lsl #16
.endm
    .equ CW_P, 0
    .equ CW_LIST, 4
    .equ CW_LEN, 8
    .equ CW_C0, 12
    .equ CW_C1, 16
    .equ CW_EY, 20
    .equ CW_EUV, 24
    .equ CW_PERSP, 28
    @ frame
    .equ F_K, 0
    .equ F_S1, 4
    .equ F_TMP, 8
    .equ F_UZ, 12
    .equ F_DUZ, 16
    .equ F_VZ, 20
    .equ F_DVZ, 24
    .equ F_W, 28
    .equ F_DW, 32
    .equ F_UC, 36
    .equ F_VC, 40
    .equ F_Y, 44
    .equ F_DY, 48
    .equ F_EY, 52
    .equ F_EUV, 56
    .equ F_LEFT, 60
    .equ F_SIZE, 64

    .global chain_walk
    .type chain_walk, %function
chain_walk:
    stmfd   sp!, {r4-r11, lr}
    sub     sp, sp, #F_SIZE
    mov     r11, r0
    mov     r0, #0
    str     r0, [sp, #F_K]
.Lcw_edge:
    ldr     r0, [sp, #F_K]
    ldr     r1, [r11, #CW_LEN]
    sub     r1, r1, #1
    cmp     r0, r1
    bge     .Lcw_done
    add     r1, r0, #1
    str     r1, [sp, #F_K]
    ldr     r2, [r11, #CW_LIST]
    ldrb    r3, [r2, r0]
    ldrb    r4, [r2, r1]
    ldr     r2, [r11, #CW_P]
    add     r3, r3, r3, lsl #2
    add     r9, r2, r3, lsl #2      @ a
    add     r4, r4, r4, lsl #2
    add     r10, r2, r4, lsl #2     @ b
    @ columns s0..s1 of this edge
    ldr     r0, [r9]                @ a.x
    ldr     r1, [r10]               @ b.x
    ldr     r2, =0x7FFF
    add     r4, r0, r2
    mov     r4, r4, asr #16         @ s0
    sub     r5, r1, #0x8000
    mov     r5, r5, asr #16         @ s1
    ldr     r2, [r11, #CW_C0]
    cmp     r4, r2
    movlt   r4, r2
    ldr     r2, [r11, #CW_C1]
    cmp     r5, r2
    movgt   r5, r2
    cmp     r4, r5
    bgt     .Lcw_edge
    str     r5, [sp, #F_S1]
    @ 1 / dx
    sub     r2, r1, r0
    cmp     r2, #0x100
    movlt   r2, #0x100
    ldr     r12, =rcp_tab
    RCP     r8, r2, r3, r12         @ r8 = inv
    @ t = first column centre - a.x
    mov     r7, r4, lsl #16
    add     r7, r7, #0x8000
    sub     r7, r7, r0              @ r7 = t
    @ y, dy
    ldr     r0, [r9, #4]
    ldr     r1, [r10, #4]
    sub     r1, r1, r0
    MUL16   r6, r1, r8, r2          @ dy
    MUL16   r1, r7, r6, r2
    add     r5, r0, r1              @ y
    @ buffers at s0
    ldr     r0, [r11, #CW_EY]
    add     r0, r0, r4, lsl #1
    ldr     r1, [r11, #CW_EUV]
    add     r1, r1, r4, lsl #2
    ldr     r2, [sp, #F_S1]
    sub     r2, r2, r4
    add     r2, r2, #1              @ columns
    ldr     r3, [r11, #CW_PERSP]
    cmp     r3, #0
    bne     .Lcw_persp
    @ affine: u, v linear along the edge
    mov     r3, r5                  @ y
    mov     r4, r6                  @ dy
    ldr     r6, [r9, #12]           @ a.u
    ldr     r12, [r10, #12]
    sub     r12, r12, r6
    MUL16   lr, r12, r8, r5         @ du
    MUL16   r12, r7, lr, r5
    add     r6, r6, r12             @ u
    str     lr, [sp, #F_TMP]
    ldr     r12, [r9, #16]          @ a.v
    ldr     r5, [r10, #16]
    sub     r5, r5, r12
    MUL16   r9, r5, r8, lr          @ dv
    MUL16   r5, r7, r9, lr
    add     r8, r12, r5             @ v
    ldr     r7, [sp, #F_TMP]        @ du
    bl      .Lcw_run
    b       .Lcw_edge

    @ perspective: u/z, v/z and 1/z linear; exact u, v every 8 columns
.Lcw_persp:
    str     r0, [sp, #F_EY]
    str     r1, [sp, #F_EUV]
    str     r2, [sp, #F_LEFT]
    str     r5, [sp, #F_Y]
    str     r6, [sp, #F_DY]
    ldr     r0, [r9, #8]            @ 1/z
    ldr     r1, [r10, #8]
    sub     r1, r1, r0
    MUL16   r2, r1, r8, r3
    str     r2, [sp, #F_DW]
    MUL16   r1, r7, r2, r3
    add     r0, r0, r1
    str     r0, [sp, #F_W]
    ldr     r0, [r9, #12]           @ u/z
    ldr     r1, [r10, #12]
    sub     r1, r1, r0
    MUL16   r2, r1, r8, r3
    str     r2, [sp, #F_DUZ]
    MUL16   r1, r7, r2, r3
    add     r0, r0, r1
    str     r0, [sp, #F_UZ]
    ldr     r0, [r9, #16]           @ v/z
    ldr     r1, [r10, #16]
    sub     r1, r1, r0
    MUL16   r2, r1, r8, r3
    str     r2, [sp, #F_DVZ]
    MUL16   r1, r7, r2, r3
    add     r0, r0, r1
    str     r0, [sp, #F_VZ]
    bl      .Lcw_exact              @ u, v at the first column
    str     r0, [sp, #F_UC]
    str     r1, [sp, #F_VC]
1:  ldr     r4, [sp, #F_LEFT]       @ a run of m <= 8 columns
    cmp     r4, #8
    movgt   r4, #8
    ldr     r0, [sp, #F_UZ]
    ldr     r1, [sp, #F_DUZ]
    mla     r0, r1, r4, r0
    str     r0, [sp, #F_UZ]
    ldr     r0, [sp, #F_VZ]
    ldr     r1, [sp, #F_DVZ]
    mla     r0, r1, r4, r0
    str     r0, [sp, #F_VZ]
    ldr     r0, [sp, #F_W]
    ldr     r1, [sp, #F_DW]
    mla     r0, r1, r4, r0
    str     r0, [sp, #F_W]
    bl      .Lcw_exact              @ u, v m columns on
    ldr     r12, =rcp_tab
    ldr     r12, [r12, r4, lsl #2]
    mov     r12, r12, lsr #8        @ 65536 / m
    ldr     r6, [sp, #F_UC]
    ldr     r8, [sp, #F_VC]
    str     r0, [sp, #F_UC]
    str     r1, [sp, #F_VC]
    sub     r0, r0, r6
    MUL16   r7, r0, r12, r3         @ du
    sub     r1, r1, r8
    MUL16   r9, r1, r12, r3         @ dv
    ldr     r0, [sp, #F_EY]
    ldr     r1, [sp, #F_EUV]
    ldr     r3, [sp, #F_Y]
    mov     r2, r4
    ldr     r4, [sp, #F_DY]
    bl      .Lcw_run
    str     r0, [sp, #F_EY]
    str     r1, [sp, #F_EUV]
    str     r3, [sp, #F_Y]
    ldr     r0, [sp, #F_LEFT]
    subs    r0, r0, #8
    str     r0, [sp, #F_LEFT]
    bgt     1b
    b       .Lcw_edge

@ u/z, v/z, 1/z from the frame -> r0 u, r1 v (clobbers r2, r3, r12)
.Lcw_exact:
    ldr     r0, [sp, #F_W]
    cmp     r0, #0x100
    movlt   r0, #0x100
    ldr     r12, =rcp_tab
    RCP     r2, r0, r3, r12         @ z
    ldr     r12, [sp, #F_UZ]
    MUL16   r0, r12, r2, r3
    ldr     r12, [sp, #F_VZ]
    MUL16   r1, r12, r2, r3
    bx      lr

@ write r2 >= 1 columns: r0 ey, r1 euv, r3 y, r4 dy, r6 u, r7 du, r8 v, r9 dv
@ (advances r0, r1, r3, r6, r8; clobbers r2, r10, r12)
.Lcw_run:
    str     lr, [sp, #-4]!
    ldr     lr, =32000
1:  mov     r12, r3, asr #12
    cmp     r12, lr
    movgt   r12, lr
    cmn     r12, lr
    rsblt   r12, lr, #0
    strh    r12, [r0], #2
    mov     r10, r8, lsl #7
    mov     r10, r10, lsr #16
    mov     r12, r6, asr #9
    orr     r12, r10, r12, lsl #16
    str     r12, [r1], #4
    add     r3, r3, r4
    add     r6, r6, r7
    add     r8, r8, r9
    subs    r2, r2, #1
    bne     1b
    ldr     lr, [sp], #4
    bx      lr

.Lcw_done:
    add     sp, sp, #F_SIZE
    ldmfd   sp!, {r4-r11, lr}
    bx      lr
    .pool


