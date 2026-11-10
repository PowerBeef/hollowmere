// SPDX-License-Identifier: MIT
// The frame loop every game runs on: the vblank interrupt (sound, the page
// flip, the HUD's sprites, key presses), the frame's clock and the detail
// governor that keeps a frame within three vblanks (20 fps).
#include "game_api.h"
#include "render.h"
#include "world.h"
#include "assets.h"
#include "audio.h"
#include "gfx.h"
#include "fx.h"
#include "hud.h"
#include "dev.h"

volatile u32 g_vblanks;
volatile u8  g_flipReq;
volatile u8  g_dispPage, g_bgHide;
volatile u32 g_lastFlip;
volatile u8  g_minFrames = 3;          // vblanks a frame stays up at least: 3 = 20 fps
u8 g_quality;               // the detail level the governor chose (0 = full)
u32 g_profRaw;              // cycles the last render took
u32 g_renderCount, g_profUpdate;
#ifdef DEV
u32 g_profFrame, g_profIrq;
EWRAM_BSS u32 g_irqParts[5];
volatile u32 g_govOff;      // test harness: hold the detail level fixed
EWRAM_BSS u32 g_pcSamples[4097];   // the sampling profiler's buffer (crt0.s)
#endif

volatile u16 g_keyPressAcc;
static u16 s_keyPrevIrq;

// the detail governor's state (engine_frame)
static u8 s_q, s_hold, s_since = 255;
static u16 s_wait = 8, s_stale;
static u32 s_prevWork, s_tried, s_failed = 0xFFFFFFFF;       // the frame cost the last try up started from; the one that failed
static s32 s_failX, s_failY;                                 // ... and where the camera was
static u16 s_failA;

// ---------------------------------------------------------------- the clock
// Timers 2 and 3, cascaded: CPU cycles since engine_frame_start().
void engine_frame_start(void) {
    REG_TM2CNT_H = 0; REG_TM3CNT_H = 0;
    REG_TM2CNT_L = 0; REG_TM3CNT_L = 0;
    REG_TM3CNT_H = 0x84; REG_TM2CNT_H = 0x80;
}
// (the two halves are read one after the other: when the low one wraps in
// between, the high one read first is one short, 65,536 cycles in all)
static inline u32 prof_read(void) {
    u32 hi = REG_TM3CNT_L, lo = REG_TM2CNT_L, hi2 = REG_TM3CNT_L;
    if (hi2 != hi) lo = REG_TM2CNT_L;
    return (hi2 << 16) | lo;
}

// ------------------------------------------------------------- interrupts
EWRAM_BSS u32 g_irqStack[256] ALIGN4;      // the interrupt handlers' stack (crt0.s)
void irq_dispatch(u32 flags) {
    if (flags & IRQ_VBLANK) {
        DEV_ONLY(u32 ta = prof_read();)
        audio_vblank();
        g_vblanks++;
        u16 k = ~REG_KEYINPUT & KEY_MASK;
        g_keyPressAcc |= k & ~s_keyPrevIrq;
        s_keyPrevIrq = k;
        int flipped = 0;
        if (g_flipReq && g_vblanks - g_lastFlip >= g_minFrames) {
            g_dispPage ^= 1;
            g_bgHide = 0;
            g_flipReq = 0;
            g_lastFlip = g_vblanks;
            flipped = 1;
        }
        DEV_ONLY(u32 t1 = prof_read();)
        fx_vblank(flipped);
        DEV_ONLY(u32 t2 = prof_read();)
        hud_oam_commit();
        DEV_ONLY(u32 t3 = prof_read();)
        music_tick();
        DEV_ONLY(u32 t4 = prof_read();)
        audio_mix();
        DEV_ONLY(u32 tb = prof_read();
                 g_profIrq = (g_profIrq * 7 + (tb - ta)) >> 3;
                 g_irqParts[0] = t1 - ta; g_irqParts[1] = t2 - t1; g_irqParts[2] = t3 - t2; g_irqParts[3] = t4 - t3; g_irqParts[4] = tb - t4;)
    }
}

u16 engine_keys_pressed(void) {
    REG_IME = 0;
    u16 p = g_keyPressAcc;
    g_keyPressAcc = 0;
    REG_IME = 1;
    return p;
}

int engine_ticks(void) {
    static u32 last;
    u32 now = g_vblanks;
    int steps = now - last;
    last = now;
    return steps < 1 ? 1 : steps > 4 ? 4 : steps;
}

void engine_present(void) {
    g_flipReq = 1;
    while (g_flipReq) bios_halt();
}

// ----------------------------------------------------------------- frames
// a new scene (a level just loaded, a checkpoint restored): full detail
// until its frames prove too slow, which takes one frame per level
void engine_frame_reset(void) { s_q = 0; s_hold = 0; s_since = 255; s_wait = 8; s_prevWork = 0; s_failed = 0xFFFFFFFF; s_stale = 0; }

// Draws a frame and waits for it to be shown. The governor adds the time
// since the last engine_frame_start() (the game update that led to this
// frame) to the time of the render: every caller starts the clock before
// its update, or just before the call when it renders without one.
void engine_frame(void) {
    g_profUpdate = prof_read();
    engine_frame_start();
    game_render();
    g_renderCount++;
    g_profRaw = prof_read();
    DEV_ONLY(g_profFrame = (g_profFrame * 7 + g_profRaw) >> 3;)
    // detail governor for the 20 fps frame (3 vblanks = 842k cycles): when
    // a frame comes close to the deadline the far floor gets coarser, far
    // walls and far furniture drop to one sample per column pair and small
    // furniture faces are dropped sooner; near things keep full detail.
#ifdef DEV
    if (!g_govOff)
#endif
    {
        // levels, cheapest-looking first: the far floor coarser (split), far
        // furniture at one sample per column pair (hd, 1/4096 tile), far
        // walls at one sample per pair (whalf: walls shorter than this) and
        // everything at one sample per pair also one sample per two rows
        // (vh), small far faces dropped sooner (lod), then the sides of the
        // view outside a central band of full resolution
        static const struct { u8 band, split, vh, pad; u16 whalf, hd, lod; } q[] = {
            { 120,  0, 0, 0,   0, 0x2400, 256 },
            { 120, 20, 0, 0,   0, 0x2000, 256 },
            { 120, 26, 1, 0,  96, 0x1C00, 288 },
            { 120, 30, 1, 0, 128, 0x1800, 320 },
            { 120, 35, 1, 0, 192, 0x1400, 384 },
            {  90, 35, 1, 0, 256, 0x1000, 448 },
            {  60, 35, 1, 0, 320, 0x0C00, 512 },
            {   0, 35, 1, 0, 400, 0x0000, 768 },
        };
        // a frame has 842,688 cycles (3 vblanks); the work is measured from
        // the start of the game update to the end of the render, interrupts
        // included. Too slow: one level down at once. Comfortably fast for 8
        // frames: try one level up; if that level then proves too slow at
        // once, wait longer before the next try.
        // (Successive frames alternate in cost by 20-25k: going up is judged
        // on the mean of the last two, going down on each frame.)
        // (A frame whose update drew a line of text is no measure of the
        // scene: it counts as its predecessor did.)
        u32 work = g_profUpdate + g_profRaw;
        if (g_hudDrew) { g_hudDrew = 0; if (s_prevWork) work = s_prevWork; }
        u32 pair = (work + s_prevWork) >> 1;
        s_prevWork = work;
        if (s_since < 255) s_since++;
        if (work > 820000) {
            if (s_q < 7) {
                s_q++;
                if (s_since <= 2) {                 // the try failed
                    s_wait = s_wait < 240 ? s_wait * 2 : 240;
                    s_failed = s_tried;             // ... from frames this cheap, here: no use trying again as things are
                    s_failX = g_cam.x; s_failY = g_cam.y; s_failA = g_cam.angle;
                }
            }
            s_hold = 0;
        } else if (pair < 770000 && (pair < s_failed - (s_failed >> 5) || s_stale > 600 ||
                                     dist_approx(g_cam.x - s_failX, g_cam.y - s_failY) > 0x8000 ||
                                     (u16)(g_cam.angle - s_failA + 0x1000) > 0x2000)) {
            // (not while the view is the one in which the last try failed and
            // costs what it did: a try that fails is a frame dropped. Half a
            // tile or a sixteenth of a turn away, 3% cheaper, or half a minute
            // on, it is worth another.)
            if (++s_hold >= s_wait && s_q > 0) { s_q--; s_hold = 0; s_since = 0; s_tried = pair; s_stale = 0; }
        } else s_hold = 0;
        if (s_stale < 0xFFFF) s_stale++;
        if (s_since > 60 && s_wait > 8) { s_wait--; }
        extern u32 g_lodScale;
        extern s32 g_halfDist, g_floorSplit, g_wallHalfLh, g_fullC0, g_fullC1;
        extern u32 g_vhalf;
        g_vhalf = q[s_q].vh;
        g_floorSplit = q[s_q].split;
        g_wallHalfLh = q[s_q].whalf;
        g_halfDist = (s32)q[s_q].hd << 4;
        g_lodScale = q[s_q].lod;
        g_fullC0 = VIEW_W / 2 - q[s_q].band;
        g_fullC1 = VIEW_W / 2 + q[s_q].band;
        g_quality = s_q;
    }
    g_flipReq = 1;
    while (g_flipReq) bios_halt();
}

// --------------------------------------------------------------- start-up
void engine_init(void) {
    REG_WAITCNT = 0x4317;
    REG_DISPCNT = DCNT_MODE4 | DCNT_BG2 | DCNT_OBJ | DCNT_OBJ_1D;
    pal_bg_game();
    bios_lz77_wram(cmap_default, g_colormapSrc);
    render_init();
    fx_init();
    hud_init();
    audio_init();
    REG_DISPSTAT = 8;
    REG_IE = IRQ_VBLANK;
    REG_IME = 1;
}
