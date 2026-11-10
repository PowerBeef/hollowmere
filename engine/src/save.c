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
// When neither is, the game may recognise a save of an older version of
// itself in the same bytes (game_save_import).
#include "game_api.h"
#include <string.h>
#include <stddef.h>

#define SRAM ((vu8 *)0x0E000000)
#define SAVE_OFS  32
#define SLOT_SIZE 256
_Static_assert(sizeof(SaveState) <= SLOT_SIZE, "SaveState no longer fits a save slot");

static void sram_write(int ofs, const void *src, int n) {
    const u8 *s = src;
    for (int i = 0; i < n; i++) SRAM[ofs + i] = s[i];
}
static void sram_read(int ofs, void *dst, int n) {
    u8 *d = dst;
    for (int i = 0; i < n; i++) d[i] = SRAM[ofs + i];
}

u16 save_sum16(const void *data, unsigned n) {
    const u8 *p = data;
    u32 sum = 0x1234;
    for (unsigned i = 0; i < n; i++) sum = (sum * 31 + p[i]) & 0xFFFF;
    return sum;
}
static u16 checksum(const SaveState *s) { return save_sum16(s, offsetof(SaveState, checksum)); }

void save_raw_read(int ofs, void *dst, int n) { sram_read(SAVE_OFS + ofs, dst, n); }

EWRAM_BSS static SaveState s_slot, s_work;      // (a state is too big to have several on the stack)

static int slot_good(int slot, SaveState *s) {
    sram_read(SAVE_OFS + slot * SLOT_SIZE, s, sizeof *s);
    return s->magic == game_info.saveMagic && s->version == SAVE_VERSION && s->checksum == checksum(s) && game_state_valid(s);
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
    tmp->magic = game_info.saveMagic;
    tmp->version = SAVE_VERSION;
    tmp->seq = seq;
    tmp->checksum = checksum(tmp);
    sram_write(SAVE_OFS + (have == 0 ? 1 : 0) * SLOT_SIZE, tmp, sizeof *tmp);
    return 1;
}

int save_read(SaveState *s) {
    if (newest(s) >= 0) return SAVE_OK;
    if (game_save_import(s)) { s->magic = game_info.saveMagic; s->version = SAVE_VERSION; return SAVE_IMPORTED; }
    return SAVE_NONE;
}

int save_exists(void) { return save_read(&s_work) != SAVE_NONE; }

void save_erase(void) {
    u32 z = 0;
    sram_write(SAVE_OFS, &z, 4);
    sram_write(SAVE_OFS + SLOT_SIZE, &z, 4);
}

// The game's options: four bytes after its tag, at the start of the save area.
void save_settings_write(const u8 v[4]) {
    u8 b[8];
    memcpy(b, game_info.settingsTag, 4);
    memcpy(b + 4, v, 4);
    sram_write(0, b, 8);
}

int save_settings_read(u8 v[4]) {
    u8 b[8];
    sram_read(0, b, 8);
    if (memcmp(b, game_info.settingsTag, 4)) return 0;
    memcpy(v, b + 4, 4);
    return 1;
}
