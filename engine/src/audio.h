// SPDX-License-Identifier: MIT
// Hollowmere audio: 8-voice stereo software mixer on Direct Sound A (L) / B (R)
#ifndef AUDIO_H
#define AUDIO_H
#include "gba.h"

#define MIX_LEN    224          // samples per frame at 13379 Hz
#define NUM_VOICES 10

typedef struct {
    const s8 *data;
    u32 len;        // samples
    u32 loopStart;  // samples
    u8  loop;       // 1 = looped
    u8  pad[3];
} SoundDef;

typedef struct {
    const s8 *data;
    u32 pos;        // 20.12
    u32 inc;        // 20.12
    u32 end;        // 20.12
    u32 loopLen;    // 20.12 (0 = one-shot)
    s16 volL, volR; // 0..256
    u16 id;         // sound id
    u8  active;
    u8  prio;
    u16 serial;     // handle check
    // positional
    u8  is3d;
    u8  baseVol;    // 0..255
    s32 x, y;       // 16.16 world position
    s16 fadeL, fadeR; // target volumes for smoothing
    s16 fadeRate;   // 0 = none; else per-frame volume decrement (fade out)
} Voice;

extern Voice g_voices[NUM_VOICES];
extern u8 g_masterVol;      // 0..64 global master (fades)
extern s16 g_listenerMuffle; // 0..256 reduce 3D volume (hiding)

void audio_init(void);
void audio_vblank(void);            // call first thing in VBlank IRQ
IWRAM_CODE void audio_mix(void);    // call in VBlank IRQ after audio_vblank

// returns handle (voice | serial<<8) or -1
int  snd_play(u16 id, u8 vol, s8 pan, u16 pitch, u8 prio);
int  snd_play3d(u16 id, s32 x, s32 y, u8 vol, u16 pitch, u8 prio);
void snd_stop(int handle);
void snd_fade(int handle, int rate);
void snd_set_vol(int handle, u8 vol, s8 pan);
void snd_set_pos(int handle, s32 x, s32 y);
int  snd_active(int handle);
void snd_stop_all(void);
void snd_update_3d(s32 lx, s32 ly, u16 angle);   // once per game frame

// music sequencer
typedef struct { u16 time; u8 note; u8 vol; } NoteEv;   // time in frames, note semitone (60 = middle C)
void music_play(const NoteEv *seq, int count, u16 instrument, u16 loopFrames, u8 vol);
void music_stop(void);
void music_tick(void);              // 60 Hz from IRQ
extern u8 g_musicVol;
u16 note_pitch(int note);

#endif
