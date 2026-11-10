// SPDX-License-Identifier: MIT
// Hollowmere - minimal GBA hardware definitions
#ifndef GBA_H
#define GBA_H

#include <stdint.h>

typedef uint8_t  u8;  typedef int8_t  s8;
typedef uint16_t u16; typedef int16_t s16;
typedef uint32_t u32; typedef int32_t s32;
typedef uint64_t u64; typedef int64_t s64;
typedef volatile u8 vu8; typedef volatile u16 vu16; typedef volatile u32 vu32;
typedef volatile s16 vs16; typedef volatile s32 vs32;

#ifndef HOSTCHECK
#define IWRAM_CODE __attribute__((section(".iwram"), long_call, target("arm"), noinline))
// cold code in IWRAM as Thumb (half the size)
#define IWRAM_THUMB __attribute__((section(".iwram"), long_call, target("thumb"), noinline))
#else       // engine/tools/hostcheck.py compiles the headers' pure functions for the build machine
#define IWRAM_CODE
#define IWRAM_THUMB
#endif
#define IWRAM_DATA __attribute__((section(".data.iwram")))
#define EWRAM_DATA __attribute__((section(".ewram")))
#define EWRAM_BSS  __attribute__((section(".sbss")))
#define ALIGN4     __attribute__((aligned(4)))
#define INLINE     static inline __attribute__((always_inline))

#define MEM_IO      0x04000000
#define MEM_PAL     ((vu16*)0x05000000)
#define MEM_PAL_OBJ ((vu16*)0x05000200)
#define MEM_VRAM    ((vu16*)0x06000000)
#define MEM_OAM     ((vu16*)0x07000000)
#define MEM_SRAM    ((vu8*)0x0E000000)

#define REG_DISPCNT   (*(vu16*)0x04000000)
#define REG_DISPSTAT  (*(vu16*)0x04000004)
#define REG_VCOUNT    (*(vu16*)0x04000006)
#define REG_BG0CNT    (*(vu16*)0x04000008)
#define REG_BG1CNT    (*(vu16*)0x0400000A)
#define REG_BG2CNT    (*(vu16*)0x0400000C)
#define REG_BG3CNT    (*(vu16*)0x0400000E)
#define REG_BG0HOFS   (*(vu16*)0x04000010)
#define REG_BG0VOFS   (*(vu16*)0x04000012)
#define REG_BG1HOFS   (*(vu16*)0x04000014)
#define REG_BG1VOFS   (*(vu16*)0x04000016)
#define REG_BG2PA     (*(vs16*)0x04000020)
#define REG_BG2PB     (*(vs16*)0x04000022)
#define REG_BG2PC     (*(vs16*)0x04000024)
#define REG_BG2PD     (*(vs16*)0x04000026)
#define REG_BG2X      (*(vs32*)0x04000028)
#define REG_BG2Y      (*(vs32*)0x0400002C)
#define REG_BG3PA     (*(vs16*)0x04000030)
#define REG_BG3PB     (*(vs16*)0x04000032)
#define REG_BG3PC     (*(vs16*)0x04000034)
#define REG_BG3PD     (*(vs16*)0x04000036)
#define REG_BG3X      (*(vs32*)0x04000038)
#define REG_BG3Y      (*(vs32*)0x0400003C)
#define REG_WIN0H     (*(vu16*)0x04000040)
#define REG_WIN1H     (*(vu16*)0x04000042)
#define REG_WIN0V     (*(vu16*)0x04000044)
#define REG_WIN1V     (*(vu16*)0x04000046)
#define REG_WININ     (*(vu16*)0x04000048)
#define REG_WINOUT    (*(vu16*)0x0400004A)
#define REG_MOSAIC    (*(vu16*)0x0400004C)
#define REG_BLDCNT    (*(vu16*)0x04000050)
#define REG_BLDALPHA  (*(vu16*)0x04000052)
#define REG_BLDY      (*(vu16*)0x04000054)

#define REG_SOUND1CNT_L (*(vu16*)0x04000060)
#define REG_SOUND1CNT_H (*(vu16*)0x04000062)
#define REG_SOUND1CNT_X (*(vu16*)0x04000064)
#define REG_SOUNDCNT_L  (*(vu16*)0x04000080)
#define REG_SOUNDCNT_H  (*(vu16*)0x04000082)
#define REG_SOUNDCNT_X  (*(vu16*)0x04000084)
#define REG_SOUNDBIAS   (*(vu16*)0x04000088)
#define REG_FIFO_A      (*(vu32*)0x040000A0)
#define REG_FIFO_B      (*(vu32*)0x040000A4)

#define REG_DMA0SAD   (*(vu32*)0x040000B0)
#define REG_DMA0DAD   (*(vu32*)0x040000B4)
#define REG_DMA0CNT   (*(vu32*)0x040000B8)
#define REG_DMA1SAD   (*(vu32*)0x040000BC)
#define REG_DMA1DAD   (*(vu32*)0x040000C0)
#define REG_DMA1CNT   (*(vu32*)0x040000C4)
#define REG_DMA1CNT_H (*(vu16*)0x040000C6)
#define REG_DMA2SAD   (*(vu32*)0x040000C8)
#define REG_DMA2DAD   (*(vu32*)0x040000CC)
#define REG_DMA2CNT   (*(vu32*)0x040000D0)
#define REG_DMA2CNT_H (*(vu16*)0x040000D2)
#define REG_DMA3SAD   (*(vu32*)0x040000D4)
#define REG_DMA3DAD   (*(vu32*)0x040000D8)
#define REG_DMA3CNT   (*(vu32*)0x040000DC)

#define REG_TM0CNT_L  (*(vu16*)0x04000100)
#define REG_TM0CNT_H  (*(vu16*)0x04000102)
#define REG_TM1CNT_L  (*(vu16*)0x04000104)
#define REG_TM1CNT_H  (*(vu16*)0x04000106)
#define REG_TM2CNT_L  (*(vu16*)0x04000108)
#define REG_TM2CNT_H  (*(vu16*)0x0400010A)
#define REG_TM3CNT_L  (*(vu16*)0x0400010C)
#define REG_TM3CNT_H  (*(vu16*)0x0400010E)

#define REG_KEYINPUT  (*(vu16*)0x04000130)
#define REG_IE        (*(vu16*)0x04000200)
#define REG_IF        (*(vu16*)0x04000202)
#define REG_WAITCNT   (*(vu16*)0x04000204)
#define REG_IME       (*(vu16*)0x04000208)

// DISPCNT
#define DCNT_MODE0   0x0000
#define DCNT_MODE2   0x0002
#define DCNT_MODE4   0x0004
#define DCNT_PAGE    0x0010
#define DCNT_OAM_HBL 0x0020
#define DCNT_OBJ_1D  0x0040
#define DCNT_BLANK   0x0080
#define DCNT_BG0     0x0100
#define DCNT_BG1     0x0200
#define DCNT_BG2     0x0400
#define DCNT_BG3     0x0800
#define DCNT_OBJ     0x1000
#define DCNT_WIN0    0x2000
#define DCNT_WIN1    0x4000
#define DCNT_WINOBJ  0x8000

// DMA
#define DMA_DST_INC    (0<<21)
#define DMA_DST_DEC    (1<<21)
#define DMA_DST_FIXED  (2<<21)
#define DMA_DST_RELOAD (3<<21)
#define DMA_SRC_INC    (0<<23)
#define DMA_SRC_FIXED  (2<<23)
#define DMA_REPEAT     (1<<25)
#define DMA_16         0
#define DMA_32         (1<<26)
#define DMA_AT_NOW     (0<<28)
#define DMA_AT_VBLANK  (1<<28)
#define DMA_AT_HBLANK  (2<<28)
#define DMA_AT_FIFO    (3<<28)
#define DMA_IRQ        (1<<30)
#define DMA_ENABLE     (1u<<31)

// IRQ bits
#define IRQ_VBLANK 0x0001
#define IRQ_HBLANK 0x0002
#define IRQ_VCOUNT 0x0004
#define IRQ_TIMER0 0x0008
#define IRQ_TIMER1 0x0010
#define IRQ_TIMER2 0x0020
#define IRQ_TIMER3 0x0040

// Keys
#define KEY_A      0x0001
#define KEY_B      0x0002
#define KEY_SELECT 0x0004
#define KEY_START  0x0008
#define KEY_RIGHT  0x0010
#define KEY_LEFT   0x0020
#define KEY_UP     0x0040
#define KEY_DOWN   0x0080
#define KEY_R      0x0100
#define KEY_L      0x0200
#define KEY_MASK   0x03FF

#define RGB15(r,g,b) ((r)|((g)<<5)|((b)<<10))

#define SCREEN_W 240
#define SCREEN_H 160

// OAM attributes
typedef struct { u16 attr0, attr1, attr2; s16 fill; } ALIGN4 OBJ_ATTR;
#define OAM ((OBJ_ATTR*)0x07000000)
#define ATTR0_HIDE   0x0200
#define ATTR0_BLEND  0x0400
#define ATTR0_WINDOW 0x0800
#define ATTR0_8BPP   0x2000
#define ATTR0_SQUARE 0x0000
#define ATTR0_WIDE   0x4000
#define ATTR0_TALL   0x8000
#define ATTR1_SIZE_8  0x0000
#define ATTR1_SIZE_16 0x4000
#define ATTR1_SIZE_32 0x8000
#define ATTR1_SIZE_64 0xC000
#define ATTR2_PRIO(n) ((n)<<10)
#define ATTR2_PAL(n)  ((n)<<12)

// BIOS calls
INLINE void bios_halt(void) { __asm__ volatile("swi 0x02" ::: "r0","r1","r2","r3","memory"); }
INLINE void bios_vblank_wait(void) { __asm__ volatile("swi 0x05" ::: "r0","r1","r2","r3","memory"); }
INLINE void bios_lz77_wram(const void *src, void *dst) {
    register const void *r0 __asm__("r0") = src; register void *r1 __asm__("r1") = dst;
    __asm__ volatile("swi 0x11" : "+r"(r0), "+r"(r1) :: "r2","r3","memory");
}
INLINE void bios_lz77_vram(const void *src, void *dst) {
    register const void *r0 __asm__("r0") = src; register void *r1 __asm__("r1") = dst;
    __asm__ volatile("swi 0x12" : "+r"(r0), "+r"(r1) :: "r2","r3","memory");
}
// CpuFastSet: count in words (multiple of 8). mode bit 24 = fill
INLINE void bios_cpufastset(const void *src, void *dst, u32 mode) {
    register const void *r0 __asm__("r0") = src; register void *r1 __asm__("r1") = dst;
    register u32 r2 __asm__("r2") = mode;
    __asm__ volatile("swi 0x0C" : "+r"(r0), "+r"(r1), "+r"(r2) :: "r3","memory");
}
INLINE void bios_cpuset(const void *src, void *dst, u32 mode) {
    register const void *r0 __asm__("r0") = src; register void *r1 __asm__("r1") = dst;
    register u32 r2 __asm__("r2") = mode;
    __asm__ volatile("swi 0x0B" : "+r"(r0), "+r"(r1), "+r"(r2) :: "r3","memory");
}

INLINE void dma3_copy32(void *dst, const void *src, u32 words) {
    REG_DMA3CNT = 0;
    REG_DMA3SAD = (u32)src; REG_DMA3DAD = (u32)dst;
    REG_DMA3CNT = words | DMA_32 | DMA_ENABLE;
}
INLINE void dma3_fill32(void *dst, u32 val, u32 words) {
    static volatile u32 tmp; tmp = val;
    REG_DMA3CNT = 0;
    REG_DMA3SAD = (u32)&tmp; REG_DMA3DAD = (u32)dst;
    REG_DMA3CNT = words | DMA_32 | DMA_SRC_FIXED | DMA_ENABLE;
}

#endif
