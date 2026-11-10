// SPDX-License-Identifier: MIT
// Hollowmere audio API, DMA plumbing, positional audio and note sequencer
#include "audio.h"
#include "assets.h"
#include "engine.h"

EWRAM_BSS s8 g_mixL[MIX_LEN * 2] ALIGN4;
EWRAM_BSS s8 g_mixR[MIX_LEN * 2] ALIGN4;
u8 g_mixHalf;
static u8 s_playHalf;
static u16 s_serial = 1;
s16 g_listenerMuffle = 256;
u8 g_musicVol = 200;

void audio_init(void) {
    for (int i = 0; i < NUM_VOICES; i++) g_voices[i].active = 0;
    for (int i = 0; i < MIX_LEN * 2; i++) { g_mixL[i] = 0; g_mixR[i] = 0; }
    REG_SOUNDCNT_X = 0x80;
    REG_SOUNDCNT_L = 0;
    // DSA: 100%, left only, timer0 ; DSB: 100%, right only, timer0 ; reset FIFOs
    REG_SOUNDCNT_H = 0x0004 | 0x0008 | 0x0200 | 0x1000 | 0x0800 | 0x8000;
    REG_SOUNDBIAS = 0x200;
    REG_TM0CNT_H = 0;
    REG_TM0CNT_L = 65536 - 1254;
    REG_DMA1CNT = 0; REG_DMA2CNT = 0;
    REG_DMA1SAD = (u32)g_mixL; REG_DMA1DAD = (u32)&REG_FIFO_A;
    REG_DMA2SAD = (u32)g_mixR; REG_DMA2DAD = (u32)&REG_FIFO_B;
    REG_DMA1CNT = DMA_DST_FIXED | DMA_REPEAT | DMA_32 | DMA_AT_FIFO | DMA_ENABLE;
    REG_DMA2CNT = DMA_DST_FIXED | DMA_REPEAT | DMA_32 | DMA_AT_FIFO | DMA_ENABLE;
    REG_TM0CNT_H = 0x80;
    s_playHalf = 0;
    g_mixHalf = 1;
}

void audio_vblank(void) {
    if (s_playHalf == 1) {
        // restart DMA at the beginning of the buffers
        REG_DMA1CNT_H = 0; REG_DMA2CNT_H = 0;
        REG_DMA1SAD = (u32)g_mixL; REG_DMA2SAD = (u32)g_mixR;
        REG_DMA1CNT_H = (DMA_DST_FIXED | DMA_REPEAT | DMA_32 | DMA_AT_FIFO | DMA_ENABLE) >> 16;
        REG_DMA2CNT_H = (DMA_DST_FIXED | DMA_REPEAT | DMA_32 | DMA_AT_FIFO | DMA_ENABLE) >> 16;
        s_playHalf = 0;
        g_mixHalf = 1;
    } else {
        s_playHalf = 1;
        g_mixHalf = 0;
    }
}

// The mixer and the sequencer run in the VBlank interrupt and use the voice
// table too: everything that claims or sets up a voice from the main program
// does it with interrupts off, and puts the interrupt flag back as it was.
static inline u16 irq_off(void) { u16 ime = REG_IME; REG_IME = 0; return ime; }

static int alloc_voice(u8 prio) {
    int best = -1, bestPrio = 256;
    for (int i = 0; i < NUM_VOICES; i++) {
        if (!g_voices[i].active) return i;
        if (g_voices[i].prio < bestPrio) { bestPrio = g_voices[i].prio; best = i; }
    }
    if (bestPrio <= prio) return best;
    return -1;
}

// (interrupts are off: the caller finishes the voice and turns them back on)
static int start_voice(u16 id, u16 pitch, u8 prio) {
    if (id >= NUM_SND) return -1;
    const SoundDef *sd = &snd_defs[id];
    int v = alloc_voice(prio);
    if (v < 0) return -1;
    Voice *vo = &g_voices[v];
    vo->active = 0;
    vo->data = sd->data;
    vo->pos = 0;
    vo->inc = pitch ? pitch : 4096;
    vo->end = sd->len << 12;
    vo->loopLen = sd->loop ? (sd->len - sd->loopStart) << 12 : 0;
    vo->id = id;
    vo->prio = prio;
    vo->serial = s_serial++;
    vo->is3d = 0;
    vo->fadeRate = 0;
    vo->music = 0;
    return v;
}

static int handle_of(int v) { return v | (g_voices[v].serial << 8); }
static Voice *voice_of(int h) {
    if (h < 0) return 0;
    Voice *vo = &g_voices[h & 0xFF];
    if (!vo->active || vo->serial != (u16)(h >> 8)) return 0;
    return vo;
}

static void pan_vol(Voice *vo, int vol, int pan) {
    // vol 0..255, pan -128..127
    int l = vol, r = vol;
    if (pan > 0) l = vol * (256 - pan * 3 / 2) >> 8;
    if (pan < 0) r = vol * (256 + pan * 3 / 2) >> 8;
    if (l < 0) l = 0;
    if (r < 0) r = 0;
    vo->fadeL = l; vo->fadeR = r;
}

int snd_play(u16 id, u8 vol, s8 pan, u16 pitch, u8 prio) {
    u16 ime = irq_off();
    int v = start_voice(id, pitch, prio);
    if (v < 0) { REG_IME = ime; return -1; }
    Voice *vo = &g_voices[v];
    pan_vol(vo, vol, pan);
    vo->volL = vo->fadeL; vo->volR = vo->fadeR;
    vo->active = 1;
    int h = handle_of(v);
    REG_IME = ime;
    return h;
}

static s32 s_lx, s_ly; static u16 s_la;

static void update3d(Voice *vo) {
    s32 dx = (vo->x - s_lx) >> 8, dy = (vo->y - s_ly) >> 8;   // 1/256 tiles
    s32 adx = dx < 0 ? -dx : dx, ady = dy < 0 ? -dy : dy;
    s32 dist = adx > ady ? adx + (ady >> 1) - (ady >> 3) : ady + (adx >> 1) - (adx >> 3);   // ~euclid
    // falloff: full within 1 tile, inverse-ish beyond, silent at 16 tiles
    s32 att;
    if (dist <= 256) att = 256;
    else if (dist >= 20 * 256) att = 0;
    else {
        att = 65536 / (256 + (((dist - 256) * 90) >> 8));
        if (dist > 16 * 256) att = att * (20 * 256 - dist) / (4 * 256);
    }
    if (att < 0) att = 0;
    if (att > 256) att = 256;
    s32 vol = (vo->baseVol * att) >> 8;
    vol = (vol * g_listenerMuffle) >> 8;
    // pan: lateral component relative to facing
    s32 c = lu_cos(s_la), s = lu_sin(s_la);
    s32 lat = (dy * c - dx * s) >> 14;     // + right
    s32 fwd = (dx * c + dy * s) >> 14;
    s32 pan = dist > 16 ? (lat * 127) / (dist + 1) : 0;
    if (fwd < 0) vol = vol * 200 >> 8;     // slightly quieter behind
    pan_vol(vo, vol, pan);
}

int snd_play3d(u16 id, s32 x, s32 y, u8 vol, u16 pitch, u8 prio) {
    u16 ime = irq_off();
    int v = start_voice(id, pitch, prio);
    if (v < 0) { REG_IME = ime; return -1; }
    Voice *vo = &g_voices[v];
    vo->is3d = 1; vo->baseVol = vol; vo->x = x; vo->y = y;
    update3d(vo);
    vo->volL = vo->fadeL; vo->volR = vo->fadeR;
    vo->active = 1;
    int h = handle_of(v);
    REG_IME = ime;
    return h;
}

void snd_update_3d(s32 lx, s32 ly, u16 angle) {
    s_lx = lx; s_ly = ly; s_la = angle;
    for (int i = 0; i < NUM_VOICES; i++) {
        Voice *vo = &g_voices[i];
        if (vo->active && vo->is3d && !vo->fadeRate) update3d(vo);
    }
}

void snd_stop(int h) { Voice *vo = voice_of(h); if (vo) vo->active = 0; }
void snd_fade(int h, int rate) { Voice *vo = voice_of(h); if (vo) { vo->fadeRate = rate; } }
int  snd_active(int h) { return voice_of(h) != 0; }
void snd_set_vol(int h, u8 vol, s8 pan) { Voice *vo = voice_of(h); if (vo) { if (vo->is3d) vo->baseVol = vol; else pan_vol(vo, vol, pan); } }
void snd_set_pos(int h, s32 x, s32 y) { Voice *vo = voice_of(h); if (vo) { vo->x = x; vo->y = y; } }
void snd_stop_all(void) { for (int i = 0; i < NUM_VOICES; i++) g_voices[i].active = 0; }

// -------------------------------------------------------------- sequencer
static const NoteEv *s_seq;
static int s_seqLen, s_seqIdx;
static u16 s_seqT, s_seqLoop, s_seqInst;
static u8 s_seqVol;

static const u16 s_semi[12] = { 4096, 4340, 4598, 4871, 5161, 5468, 5793, 6137, 6502, 6889, 7298, 7732 };

u16 note_pitch(int note) {
    // instrument samples are recorded at note 72 (C5)
    int d = note - 72;
    int oct = 0;
    while (d < 0) { d += 12; oct--; }
    while (d >= 12) { d -= 12; oct++; }
    u32 p = s_semi[d];
    if (oct > 0) p <<= oct; else if (oct < 0) p >>= -oct;
    return p > 65535 ? 65535 : p;
}

void music_play(const NoteEv *seq, int count, u16 instrument, u16 loopFrames, u8 vol) {
    u16 ime = irq_off();        // (music_tick must not see half of the new tune)
    s_seq = seq; s_seqLen = count; s_seqIdx = 0; s_seqT = 0;
    s_seqLoop = loopFrames; s_seqInst = instrument; s_seqVol = vol;
    REG_IME = ime;
}

void music_stop(void) { s_seq = 0; }

#define MUSIC_POLY 3
void music_tick(void) {
    if (!s_seq) return;
    while (s_seqIdx < s_seqLen && s_seq[s_seqIdx].time <= s_seqT) {
        const NoteEv *e = &s_seq[s_seqIdx++];
        int vol = (e->vol * s_seqVol * g_musicVol) >> 16;
        s8 pan = (s8)(((e->note * 37) & 63) - 32);
        // cap polyphony: the oldest ringing note is faded out quickly
        {
            int cnt = 0, oldest = -1, oldAge = -1;
            for (int i = 0; i < NUM_VOICES; i++) {
                Voice *q = &g_voices[i];
                if (!q->active || !q->music || q->fadeRate) continue;
                cnt++;
                int age = (u16)(s_serial - q->serial);
                if (age > oldAge) { oldAge = age; oldest = i; }
            }
            if (cnt >= MUSIC_POLY && oldest >= 0) g_voices[oldest].fadeRate = 10;
        }
        // play without re-enabling IME (we are inside the IRQ)
        int v = alloc_voice(40);
        if (v < 0) continue;
        const SoundDef *sd = &snd_defs[s_seqInst];
        Voice *vo = &g_voices[v];
        vo->data = sd->data; vo->pos = 0; vo->inc = note_pitch(e->note);
        vo->end = sd->len << 12; vo->loopLen = 0; vo->id = s_seqInst;
        vo->prio = 40; vo->serial = s_serial++; vo->is3d = 0; vo->fadeRate = 0; vo->music = 1;
        pan_vol(vo, vol, pan);
        vo->volL = vo->fadeL; vo->volR = vo->fadeR;
        vo->active = 1;
    }
    s_seqT++;
    if (s_seqIdx >= s_seqLen) {
        if (s_seqLoop) { if (s_seqT >= s_seqLoop) { s_seqT = 0; s_seqIdx = 0; } }
        else s_seq = 0;
    }
}
