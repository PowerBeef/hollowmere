// Battery-backed SRAM save
#include "game.h"
#include <string.h>

#define SRAM ((vu8 *)0x0E000000)
#define SAVE_OFS 32
Settings g_settings = { 1, 3, 0, 0 };

static void sram_write(int ofs, const void *src, int n) {
    const u8 *s = src;
    for (int i = 0; i < n; i++) SRAM[ofs + i] = s[i];
}
static void sram_read(int ofs, void *dst, int n) {
    u8 *d = dst;
    for (int i = 0; i < n; i++) d[i] = SRAM[ofs + i];
}

static u16 checksum(const SaveState *s) {
    const u8 *p = (const u8 *)s;
    u32 sum = 0x1234;
    for (unsigned i = 0; i < offsetof(SaveState, checksum); i++) sum = (sum * 31 + p[i]) & 0xFFFF;
    return sum;
}

int save_write(const SaveState *s) {
    SaveState tmp;
    memcpy(&tmp, s, sizeof tmp);
    tmp.magic = SAVE_MAGIC;
    tmp.checksum = checksum(&tmp);
    sram_write(SAVE_OFS, &tmp, sizeof tmp);
    return 1;
}

int save_read(SaveState *s) {
    SaveState tmp;
    sram_read(SAVE_OFS, &tmp, sizeof tmp);
    if (tmp.magic != SAVE_MAGIC || tmp.checksum != checksum(&tmp)) return 0;
    memcpy(s, &tmp, sizeof tmp);
    return 1;
}

int save_exists(void) { SaveState t; return save_read(&t); }

void save_erase(void) {
    u32 z = 0;
    sram_write(SAVE_OFS, &z, 4);
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
