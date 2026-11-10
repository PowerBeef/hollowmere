// SPDX-License-Identifier: MIT
// Battery-backed SRAM save.
//
// Layout: the settings (8 bytes at 0), then two slots of SLOT_SIZE bytes at
// SAVE_OFS, each a SaveState. A checkpoint is written to the slot that does
// not hold the newest good state, with the next sequence number, so a write
// cut short by the power switch leaves the one before it intact: the slot
// being written fails its checksum and the other is loaded.
//
// A slot is loaded only if its magic, layout version and checksum are right
// and the game finds every index and range in it valid (game_state_valid).
#include "game.h"
#include "assets.h"
#include <string.h>

#define SRAM ((vu8 *)0x0E000000)
#define SAVE_OFS  32
#define SLOT_SIZE 256
_Static_assert(sizeof(SaveState) <= SLOT_SIZE, "SaveState no longer fits a save slot");
Settings g_settings = { 1, 3, 0, 0 };

static void sram_write(int ofs, const void *src, int n) {
    const u8 *s = src;
    for (int i = 0; i < n; i++) SRAM[ofs + i] = s[i];
}
static void sram_read(int ofs, void *dst, int n) {
    u8 *d = dst;
    for (int i = 0; i < n; i++) d[i] = SRAM[ofs + i];
}

static u16 sum16(const u8 *p, unsigned n) {
    u32 sum = 0x1234;
    for (unsigned i = 0; i < n; i++) sum = (sum * 31 + p[i]) & 0xFFFF;
    return sum;
}
static u16 checksum(const SaveState *s) { return sum16((const u8 *)s, offsetof(SaveState, checksum)); }

EWRAM_BSS static SaveState s_slot, s_work;      // (a state is too big to have several on the stack)

static int slot_good(int slot, SaveState *s) {
    sram_read(SAVE_OFS + slot * SLOT_SIZE, s, sizeof *s);
    return s->magic == SAVE_MAGIC && s->version == SAVE_VERSION && s->checksum == checksum(s) && game_state_valid(s);
}

// the slot holding the newest good state into *out; -1 if neither is good
static int newest(SaveState *out) {
    int g0 = slot_good(0, out), g1 = slot_good(1, &s_slot);
    if (g1 && (!g0 || (s8)(s_slot.seq - out->seq) > 0)) { memcpy(out, &s_slot, sizeof *out); return 1; }
    return g0 ? 0 : -1;
}

int save_write(const SaveState *s) {
    SaveState *tmp = &s_work;
    int have = newest(tmp);
    u8 seq = have < 0 ? 0 : (u8)(tmp->seq + 1);
    memcpy(tmp, s, sizeof *tmp);
    tmp->magic = SAVE_MAGIC;
    tmp->version = SAVE_VERSION;
    tmp->seq = seq;
    tmp->checksum = checksum(tmp);
    sram_write(SAVE_OFS + (have == 0 ? 1 : 0) * SLOT_SIZE, tmp, sizeof *tmp);
    return 1;
}

// A save written by version 1.0: one slot at SAVE_OFS, the same fields
// without the script threads. Its checkpoint cannot be resumed (the level
// scripts it would need were not saved), but the chapter and what carries
// from chapter to chapter can: the player starts that chapter again.
#define OLD_MAGIC 0x484C5732u       // "HLW2"
#define OLD_HEAD  offsetof(SaveState, script)
#define OLD_SIZE  (OLD_HEAD + 12)   // + px, py, pangle, checksum
static int old_save(SaveState *s) {
    SaveState *o = &s_slot;         // (its fields up to the script threads are where they were)
    const u8 *raw = (const u8 *)o;
    sram_read(SAVE_OFS, o, OLD_SIZE);
    u16 sum = raw[OLD_SIZE - 2] | raw[OLD_SIZE - 1] << 8;
    if (o->magic != OLD_MAGIC || sum != sum16(raw, OLD_SIZE - 2) || o->level >= NUM_LEVELS) return 0;
    memset(s, 0, sizeof *s);
    s->magic = SAVE_MAGIC; s->version = SAVE_VERSION;
    s->level = o->level;
    s->notesFound = o->notesFound;
    s->battery = o->battery > 1000000 ? 1000000 : o->battery;
    s->flashOn = 1;
    s->deaths = o->deaths;
    s->playFrames = o->playFrames;
    return 1;
}

int save_read(SaveState *s) {
    if (newest(s) >= 0) return SAVE_OK;
    return old_save(s) ? SAVE_CHAPTER : SAVE_NONE;
}

int save_exists(void) { return save_read(&s_work) != SAVE_NONE; }

void save_erase(void) {
    u32 z = 0;
    sram_write(SAVE_OFS, &z, 4);
    sram_write(SAVE_OFS + SLOT_SIZE, &z, 4);
}

void settings_save(void) {
    u8 b[8] = { 'H', 'L', 'S', '1', g_settings.brightness, g_settings.volume, g_settings.controls, g_settings.seenIntro };
    sram_write(0, b, 8);
}

void settings_load(void) {
    u8 b[8];
    sram_read(0, b, 8);
    if (b[0] == 'H' && b[1] == 'L' && b[2] == 'S' && b[3] == '1') {
        g_settings.brightness = b[4] > 2 ? 1 : b[4];
        g_settings.volume = b[5] > 4 ? 3 : b[5];
        g_settings.controls = b[6] > 1 ? 0 : b[6];
        g_settings.seenIntro = b[7] & 1;
    }
}
