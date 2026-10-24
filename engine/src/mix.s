@ Hollowmere mixer inner loop (ARM, IWRAM)
@ Packed stereo: each accumulator word holds L in the low half and R in the
@ high half; one MLA by (vl | vr << 16) mixes a sample into both channels.
@ The caller limits the summed volumes so neither half can overflow.
    .section .iwram, "ax", %progbits
    .arm
    .align 2

@ ---------------------------------------------------------------------------
@ u32 mix_packed(u32 *acc, const s8 *data, u32 pos, u32 inc, int m, u32 vp)
@   pos/inc 20.12; returns the new pos
@ ---------------------------------------------------------------------------
    .global mix_packed
    .type mix_packed, %function
mix_packed:
    stmfd   sp!, {r4-r11, lr}
    ldr     r4, [sp, #36]           @ m
    ldr     r5, [sp, #40]           @ vp
    subs    r4, r4, #4
    blt     2f
1:
    mov     r12, r2, lsr #12
    ldrsb   r6, [r1, r12]
    add     r2, r2, r3
    mov     r12, r2, lsr #12
    ldrsb   r7, [r1, r12]
    add     r2, r2, r3
    mov     r12, r2, lsr #12
    ldrsb   r8, [r1, r12]
    add     r2, r2, r3
    mov     r12, r2, lsr #12
    ldrsb   lr, [r1, r12]
    add     r2, r2, r3
    ldmia   r0, {r9, r10, r11, r12}
    mla     r9, r5, r6, r9
    mla     r10, r5, r7, r10
    mla     r11, r5, r8, r11
    mla     r12, r5, lr, r12
    stmia   r0!, {r9, r10, r11, r12}
    subs    r4, r4, #4
    bge     1b
2:
    adds    r4, r4, #4
    beq     3f
4:
    mov     r12, r2, lsr #12
    ldrsb   r6, [r1, r12]
    add     r2, r2, r3
    ldr     r9, [r0]
    mla     r9, r5, r6, r9
    str     r9, [r0], #4
    subs    r4, r4, #1
    bne     4b
3:
    mov     r0, r2
    ldmfd   sp!, {r4-r11, lr}
    bx      lr
