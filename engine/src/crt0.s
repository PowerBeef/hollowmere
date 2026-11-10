@ SPDX-License-Identifier: MIT
@ Hollowmere startup code
    .section .crt0, "ax"
    .arm
    .global _start
_start:
    b       rom_start
    .fill   156, 1, 0               @ boot logo (inserted by fixheader.py)
    .fill   12, 1, 0                @ title
    .fill   4, 1, 0                 @ game code
    .fill   2, 1, 0                 @ maker
    .byte   0x96                    @ fixed
    .byte   0                       @ unit
    .byte   0                       @ device
    .fill   7, 1, 0
    .byte   0                       @ version
    .byte   0                       @ complement
    .hword  0
    @ save type id string so emulators/flashcarts detect battery SRAM
    .align 4
    .ascii  "SRAM_V113"
    .align 4

rom_start:
    @ IRQ mode stack
    mov     r0, #0x12
    msr     cpsr_c, r0
    ldr     sp, =0x03007FA0
    @ System mode stack: everything below the interrupt stack (the BIOS
    @ pushes 24 bytes there, isr_master 8 more before switching away)
    mov     r0, #0x1F
    msr     cpsr_c, r0
    ldr     sp, =0x03007F80

    @ copy .iwram (code + data) to IWRAM
    ldr     r0, =__iwram_lma
    ldr     r1, =__iwram_start
    ldr     r2, =__iwram_end
1:  cmp     r1, r2
    ldrlt   r3, [r0], #4
    strlt   r3, [r1], #4
    blt     1b

    @ clear .bss
    ldr     r1, =__bss_start
    ldr     r2, =__bss_end
    mov     r3, #0
2:  cmp     r1, r2
    strlt   r3, [r1], #4
    blt     2b

    @ copy .ewram
    ldr     r0, =__ewram_lma
    ldr     r1, =__ewram_start
    ldr     r2, =__ewram_end
3:  cmp     r1, r2
    ldrlt   r3, [r0], #4
    strlt   r3, [r1], #4
    blt     3b

    @ clear .sbss
    ldr     r1, =__sbss_start
    ldr     r2, =__sbss_end
    mov     r3, #0
4:  cmp     r1, r2
    strlt   r3, [r1], #4
    blt     4b

    @ paint the free fast RAM under the stack and the interrupt stack with
    @ a canary: engine/tools/stackcheck.py reads how deep either one went
    ldr     r1, =__bss_end
    mov     r2, sp
    ldr     r3, =0xA5A5A5A5
6:  cmp     r1, r2
    strlt   r3, [r1], #4
    blt     6b
    ldr     r1, =g_irqStack
    add     r2, r1, #1024
7:  cmp     r1, r2
    strlt   r3, [r1], #4
    blt     7b

    @ install interrupt handler
    ldr     r0, =isr_master
    ldr     r1, =0x03007FFC
    str     r0, [r1]

    ldr     r0, =main
    mov     lr, pc
    bx      r0
5:  b       5b
    .pool

@ ---------------------------------------------------------------------------
@ Master interrupt handler (ARM, IWRAM). Acknowledges, switches to system
@ mode so C handlers run on the large user stack, then dispatches.
@ ---------------------------------------------------------------------------
    .section .iwram, "ax", %progbits
    .arm
    .align 2
    .global isr_master
isr_master:
    mov     r3, #0x04000000
    add     r1, r3, #0x200
    ldr     r2, [r1]                    @ IE | IF<<16
    and     r0, r2, r2, lsr #16         @ pending & enabled
    strh    r0, [r1, #2]                @ ack IF
    ldrh    r2, [r3, #-8]               @ BIOS IntrWait flags (0x03FFFFF8)
    orr     r2, r2, r0
    strh    r2, [r3, #-8]
#ifdef DEV
    tst     r0, #0x10                   @ timer 1: the sampling profiler (pcprof.py)
    beq     1f
    ldr     r2, [sp, #20]               @ interrupted pc + 4 (saved by the BIOS)
    ldr     r1, =g_pcSamples
    ldr     r3, [r1]
    cmp     r3, #4096
    addlo   r12, r1, r3, lsl #2
    strlo   r2, [r12, #4]
    addlo   r3, r3, #1
    strlo   r3, [r1]
    bics    r0, r0, #0x10
    bxeq    lr                          @ nothing else pending
1:
#endif
    mrs     r2, spsr
    stmfd   sp!, {r2, lr}
    mrs     r3, cpsr
    bic     r3, r3, #0xDF
    orr     r3, r3, #0x9F               @ system mode, IRQ disabled
    msr     cpsr, r3

    mov     r2, sp                      @ the C handlers run on their own
    ldr     sp, =g_irqStack + 1024      @ stack (EWRAM): the main stack can
    stmfd   sp!, {r2, lr}               @ be at its deepest when they come
    ldr     r1, =irq_dispatch
    mov     lr, pc
    bx      r1
    ldmfd   sp!, {r2, lr}
    mov     sp, r2

    mrs     r3, cpsr
    bic     r3, r3, #0xDF
    orr     r3, r3, #0x92               @ back to IRQ mode
    msr     cpsr, r3
    ldmfd   sp!, {r2, lr}
    msr     spsr, r2
    bx      lr
    .pool
