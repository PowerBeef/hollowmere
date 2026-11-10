// SPDX-License-Identifier: MIT
// Headless mGBA test harness for Hollowmere.
// Reads commands from a script file (or stdin):
//   hold KEYS          set held keys (e.g. "hold UP|A", "hold -" for none)
//   run N              run N frames
//   tap KEYS [N]       hold keys for N frames (default 2) then release, run 2 frames
//   shot FILE.ppm      save the current frame
//   audio FILE.wav     start recording audio to wav (stop with "audio -")
//   peek8/16/32 ADDR   print memory value
//   poke8/16/32 ADDR V write memory
//   save FILE          set save file path before ROM start ("savefile" must come first)
//   echo TEXT
#include <mgba/core/core.h>
#include <mgba/core/blip_buf.h>
#include <mgba/core/log.h>
#include <mgba-util/vfs.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

static struct mCore *core;
static color_t *vbuf;
static unsigned W, H;
static FILE *wav; static long wavSamples;
static uint32_t heldKeys;

static void quietLog(struct mLogger *l, int cat, enum mLogLevel lvl, const char *fmt, va_list a) {
    (void)l; (void)cat;
    if (lvl & (mLOG_FATAL)) { vfprintf(stderr, fmt, a); fputc('\n', stderr); }
}
static struct mLogger logger = { .log = quietLog };

static uint32_t parseKeys(const char *s) {
    uint32_t k = 0;
    if (!strcmp(s, "-")) return 0;
    char buf[256]; strncpy(buf, s, 255); buf[255] = 0;
    for (char *t = strtok(buf, "|+,"); t; t = strtok(NULL, "|+,")) {
        if (!strcmp(t, "A")) k |= 1; else if (!strcmp(t, "B")) k |= 2;
        else if (!strcmp(t, "SELECT")) k |= 4; else if (!strcmp(t, "START")) k |= 8;
        else if (!strcmp(t, "RIGHT")) k |= 16; else if (!strcmp(t, "LEFT")) k |= 32;
        else if (!strcmp(t, "UP")) k |= 64; else if (!strcmp(t, "DOWN")) k |= 128;
        else if (!strcmp(t, "R")) k |= 256; else if (!strcmp(t, "L")) k |= 512;
        else fprintf(stderr, "unknown key %s\n", t);
    }
    return k;
}

static void wavHeader(FILE *f, long n) {
    uint32_t rate = 32768, bytes = n * 4;
    fseek(f, 0, SEEK_SET);
    fwrite("RIFF", 1, 4, f); uint32_t v = 36 + bytes; fwrite(&v, 4, 1, f);
    fwrite("WAVEfmt ", 1, 8, f); v = 16; fwrite(&v, 4, 1, f);
    uint16_t s = 1; fwrite(&s, 2, 1, f); s = 2; fwrite(&s, 2, 1, f);
    fwrite(&rate, 4, 1, f); v = rate * 4; fwrite(&v, 4, 1, f);
    s = 4; fwrite(&s, 2, 1, f); s = 16; fwrite(&s, 2, 1, f);
    fwrite("data", 1, 4, f); fwrite(&bytes, 4, 1, f);
}

static void drainAudio(void) {
    blip_t *L = core->getAudioChannel(core, 0), *R = core->getAudioChannel(core, 1);
    short buf[2048];
    int avail;
    while ((avail = blip_samples_avail(L)) > 0) {
        if (avail > 1024) avail = 1024;
        blip_read_samples(L, buf, avail, 1);
        blip_read_samples(R, buf + 1, avail, 1);
        if (wav) { fwrite(buf, 4, avail, wav); wavSamples += avail; }
    }
}

static void runFrames(int n) {
    for (int i = 0; i < n; i++) {
        core->setKeys(core, heldKeys);
        core->runFrame(core);
        drainAudio();
    }
}

static void shot(const char *path) {
    FILE *f = fopen(path, "wb");
    if (!f) { perror(path); return; }
    fprintf(f, "P6\n%u %u\n255\n", W, H);
    for (unsigned i = 0; i < W * H; i++) {
        uint32_t c = vbuf[i];
        unsigned char rgb[3] = { c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF };
        fwrite(rgb, 1, 3, f);
    }
    fclose(f);
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: harness rom.gba [script] [savefile]\n"); return 1; }
    mLogSetDefaultLogger(&logger);
    core = mCoreFind(argv[1]);
    if (!core) { fprintf(stderr, "no core\n"); return 1; }
    core->init(core);
    mCoreInitConfig(core, NULL);
    core->desiredVideoDimensions(core, &W, &H);
    vbuf = calloc(W * H, sizeof(color_t));
    core->setVideoBuffer(core, vbuf, W);
    core->setAudioBufferSize(core, 2048);
    blip_set_rates(core->getAudioChannel(core, 0), core->frequency(core), 32768);
    blip_set_rates(core->getAudioChannel(core, 1), core->frequency(core), 32768);
    if (!mCoreLoadFile(core, argv[1])) { fprintf(stderr, "load failed\n"); return 1; }
    if (argc > 3) {
        struct VFile *vf = VFileOpen(argv[3], O_CREAT | O_RDWR);
        if (vf) core->loadSave(core, vf);
    }
    core->reset(core);

    FILE *in = stdin;
    if (argc > 2 && strcmp(argv[2], "-")) in = fopen(argv[2], "r");
    if (!in) { perror("script"); return 1; }
    char line[512];
    while (fgets(line, sizeof line, in)) {
        char cmd[64] = {0}, a1[256] = {0}, a2[256] = {0};
        int n = sscanf(line, "%63s %255s %255s", cmd, a1, a2);
        if (n <= 0 || cmd[0] == '#') continue;
        if (!strcmp(cmd, "hold")) heldKeys = parseKeys(a1);
        else if (!strcmp(cmd, "run")) runFrames(atoi(a1));
        else if (!strcmp(cmd, "tap")) {
            uint32_t old = heldKeys; heldKeys = parseKeys(a1);
            runFrames(n > 2 ? atoi(a2) : 2); heldKeys = old; runFrames(2);
        }
        else if (!strcmp(cmd, "shot")) shot(a1);
        else if (!strcmp(cmd, "audio")) {
            if (wav) { wavHeader(wav, wavSamples); fclose(wav); wav = NULL; }
            if (strcmp(a1, "-")) { wav = fopen(a1, "wb"); wavSamples = 0; wavHeader(wav, 0); }
        }
        else if (!strcmp(cmd, "peek8")) printf("%s = %u\n", a1, core->busRead8(core, strtoul(a1, 0, 0)));
        else if (!strcmp(cmd, "peek16")) printf("%s = %u\n", a1, core->busRead16(core, strtoul(a1, 0, 0)));
        else if (!strcmp(cmd, "peek32")) printf("%s = %u\n", a1, core->busRead32(core, strtoul(a1, 0, 0)));
        else if (!strcmp(cmd, "peeks32")) printf("%s = %d\n", a1, (int32_t)core->busRead32(core, strtoul(a1, 0, 0)));
        else if (!strcmp(cmd, "poke8")) core->busWrite8(core, strtoul(a1, 0, 0), strtoul(a2, 0, 0));
        else if (!strcmp(cmd, "poke16")) core->busWrite16(core, strtoul(a1, 0, 0), strtoul(a2, 0, 0));
        else if (!strcmp(cmd, "poke32")) core->busWrite32(core, strtoul(a1, 0, 0), strtoul(a2, 0, 0));
        else if (!strcmp(cmd, "echo")) printf("%s", line + 5);
        else if (!strcmp(cmd, "dump")) {        // dump ADDR LEN FILE
            char a3[256] = {0};
            sscanf(line, "%*s %*s %*s %255s", a3);
            FILE *f = fopen(a3, "wb");
            uint32_t ad = strtoul(a1, 0, 0), len = strtoul(a2, 0, 0);
            for (uint32_t i = 0; i < len; i++) fputc(core->busRead8(core, ad + i), f);
            fclose(f);
        }
        else if (!strcmp(cmd, "frame")) printf("frame %u\n", core->frameCounter(core));
        else fprintf(stderr, "unknown cmd %s\n", cmd);
        fflush(stdout);
    }
    if (wav) { wavHeader(wav, wavSamples); fclose(wav); }
    core->deinit(core);
    return 0;
}
