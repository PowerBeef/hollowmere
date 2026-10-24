// Hollowmere software mixer (ARM, IWRAM). Called from the VBlank IRQ.
#include "audio.h"

EWRAM_BSS Voice g_voices[NUM_VOICES];
u8 g_masterVol = 64;

static u32 s_acc[MIX_LEN];
extern s8 g_mixL[MIX_LEN * 2], g_mixR[MIX_LEN * 2];
extern u8 g_mixHalf;      // half to mix into
static u32 s_vp[NUM_VOICES];
extern u32 mix_packed(u32 *acc, const s8 *data, u32 pos, u32 inc, int m, u32 vp);

IWRAM_CODE void audio_mix(void) {
    u32 *acc = s_acc;
    for (int i = 0; i < MIX_LEN; i += 8) {
        acc[i] = 0; acc[i + 1] = 0; acc[i + 2] = 0; acc[i + 3] = 0;
        acc[i + 4] = 0; acc[i + 5] = 0; acc[i + 6] = 0; acc[i + 7] = 0;
    }
    // pass 1: volume ramps, inaudible voices, packed volumes and their sum
    s32 total = 0;
    for (int v = 0; v < NUM_VOICES; v++) {
        Voice *vo = &g_voices[v];
        s_vp[v] = 0;
        if (!vo->active) continue;
        if (vo->fadeRate) {
            vo->fadeL -= vo->fadeRate; vo->fadeR -= vo->fadeRate;
            if (vo->fadeL < 0) vo->fadeL = 0;
            if (vo->fadeR < 0) vo->fadeR = 0;
            if (!vo->fadeL && !vo->fadeR) { vo->active = 0; continue; }
        }
        s32 vl = vo->volL, vr = vo->volR;
        s32 tl = vo->fadeL, tr = vo->fadeR;
        // ramp halfway toward target per frame to avoid zipper noise
        vl += (tl - vl) >> 1; vr += (tr - vr) >> 1;
        if ((tl - vl) * (tl - vl) < 4) vl = tl;
        if ((tr - vr) * (tr - vr) < 4) vr = tr;
        vo->volL = vl; vo->volR = vr;
        // packed units are half volume (0..128)
        vl >>= 1; vr >>= 1;
        if (vl <= 0 && vr <= 0) {
            // inaudible: just advance
            u32 pos = vo->pos + vo->inc * MIX_LEN;
            if (pos >= vo->end) {
                if (!vo->loopLen) { vo->active = 0; continue; }
                while (pos >= vo->end) pos -= vo->loopLen;
            }
            vo->pos = pos;
            continue;
        }
        if (vl > 128) vl = 128;
        if (vr > 128) vr = 128;
        total += vl > vr ? vl : vr;
        s_vp[v] = (u32)vl | ((u32)vr << 16);
    }
    // limiter: keep sum(vol) * 128 below 32768 so the packed halves never wrap
    s32 lim = 256;
    if (total > lim) {
        s32 k = (lim << 8) / total;
        for (int v = 0; v < NUM_VOICES; v++) {
            u32 p = s_vp[v];
            if (!p) continue;
            u32 l = ((p & 0xFFFF) * k) >> 8, r = ((p >> 16) * k) >> 8;
            s_vp[v] = l | (r << 16);
        }
    }
    // pass 2: mix
    for (int v = 0; v < NUM_VOICES; v++) {
        u32 vp = s_vp[v];
        if (!vp) continue;
        Voice *vo = &g_voices[v];
        const s8 *data = vo->data;
        u32 pos = vo->pos, inc = vo->inc, end = vo->end;
        u32 *a = acc;
        int n = MIX_LEN;
        while (n > 0) {
            u32 left = end - pos;
            int m = (int)((left + inc - 1) / inc);
            if (m > n) m = n;
            n -= m;
            pos = mix_packed(a, data, pos, inc, m, vp);
            a += m;
            if (pos >= end) {
                if (vo->loopLen) { while (pos >= end) pos -= vo->loopLen; }
                else { vo->active = 0; break; }
            }
        }
        vo->pos = pos;
    }
    // output with clipping
    s8 *outL = g_mixL + g_mixHalf * MIX_LEN;
    s8 *outR = g_mixR + g_mixHalf * MIX_LEN;
    s32 mv = g_masterVol;
    // four samples per 32-bit store (EWRAM byte stores are slow)
    u32 *oL = (u32 *)outL, *oR = (u32 *)outR;
    for (int i = 0; i < MIX_LEN; i += 4) {
        u32 pl = 0, pr = 0;
        #pragma GCC unroll 4
        for (int k = 0; k < 4; k++) {
            u32 w = acc[i + k];
            s32 lo = (s16)(w & 0xFFFF);
            s32 hi = (s32)(w - (u32)lo) >> 16;
            s32 l = (lo * mv) >> 13;
            s32 r = (hi * mv) >> 13;
            if (l > 127) l = 127; else if (l < -128) l = -128;
            if (r > 127) r = 127; else if (r < -128) r = -128;
            pl |= (u32)(l & 0xFF) << (k * 8);
            pr |= (u32)(r & 0xFF) << (k * 8);
        }
        oL[i >> 2] = pl; oR[i >> 2] = pr;
    }
}
