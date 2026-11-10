// SPDX-License-Identifier: MIT
// Headless mGBA test harness.
//
//   harness [--lenient] rom.gba [script | -] [savefile]
//
// Runs the ROM with no window and no sound device, driven by a script (a
// file, or stdin). Exit status: 0 the script ran and every expectation
// held; 1 an expectation failed; 2 a usage, script or file error; 3 the
// emulator reported errors (a bad memory access, a jump to nowhere: the ROM
// crashed or read wild pointers). --lenient reports those without failing.
//
// Script commands (numbers in any C base; a line starting with # is a comment):
//   hold KEYS              keys held from now on ("hold UP|A", "hold -" for none)
//   run N                  run N frames
//   tap KEYS [N]           hold KEYS for N frames (default 2), release, run 2 more
//   monkey N MASK          N frames of random input from the keys in MASK
//   seed N                 seed for monkey
//   shot FILE.ppm          save the screen
//   snap                   remember the screen
//   cmp NAME FILE [MAX]    pixels of rows 18..133 that differ from the snap:
//                          prints "CMP NAME count x0 y0 x1 y1", saves the
//                          screen to FILE when any do; more than MAX fails
//   audio FILE.wav         record audio ("audio -" stops)
//   peek8/peek16/peek32/peeks32 ADDR        print memory (peeks32: signed)
//   poke8/poke16/poke32 ADDR VALUE          write memory
//   fill ADDR LEN BYTE     fill memory (32-bit writes)
//   dump ADDR LEN FILE     save memory to a file
//   expect8/expect16/expect32/expects32 ADDR OP VALUE [text]
//                          OP is == != < <= > >=; a false one is reported
//                          and the run exits 1 at the end
//   echo TEXT              print TEXT
//   frame                  print the frame counter
//   regs                   print pc, sp, lr and cpsr
#include <mgba/core/core.h>
#include <mgba/core/blip_buf.h>
#include <mgba/core/log.h>
#include <mgba/internal/gba/gba.h>
#include <mgba/internal/arm/arm.h>
#include <mgba-util/vfs.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <ctype.h>

static struct mCore *core;
static color_t *vbuf, *snapbuf;
static unsigned W, H;
static FILE *wav; static long wavSamples;
static uint32_t heldKeys;
static int lineNo;
static int failedExpect;
static uint32_t rngState = 1;

// ---------------------------------------------------------------- errors
// Emulator complaints, de-duplicated by message and code address.
#define MAXMSG 256
#define FLOOD  64          // this many distinct errors, or 5000 in all: the ROM has crashed
#define FLOOD_ALL 5000
static struct { char msg[160]; unsigned count, pc, lr, frame; int level; } msgs[MAXMSG];
static int nmsg, nerr, nerrAll, fatal;
#define ERR_LEVELS (mLOG_FATAL | mLOG_ERROR | mLOG_GAME_ERROR)

static void logger_fn(struct mLogger *l, int cat, enum mLogLevel lvl, const char *fmt, va_list a) {
    (void)l;
    if (!(lvl & (ERR_LEVELS | mLOG_WARN | mLOG_STUB))) return;
    char m[160];
    int n = snprintf(m, sizeof m, "[%s] ", mLogCategoryName(cat));
    vsnprintf(m + n, sizeof m - n, fmt, a);
    unsigned pc = 0, lr = 0;
    if (core && core->board) {
        struct GBA *g = core->board;
        if (g->cpu) { pc = g->cpu->gprs[15]; lr = g->cpu->gprs[14]; }
    }
    if (lvl & mLOG_FATAL) fatal = 1;
    if (lvl & ERR_LEVELS) nerrAll++;
    for (int i = 0; i < nmsg; i++)
        if (msgs[i].pc == pc && !strcmp(msgs[i].msg, m)) { msgs[i].count++; return; }
    if (lvl & ERR_LEVELS) nerr++;
    if (nmsg < MAXMSG) {
        strcpy(msgs[nmsg].msg, m);
        msgs[nmsg].count = 1; msgs[nmsg].pc = pc; msgs[nmsg].lr = lr; msgs[nmsg].level = lvl;
        msgs[nmsg].frame = core ? core->frameCounter(core) : 0;
        nmsg++;
    }
}
static struct mLogger logger = { .log = logger_fn };

static void report_log(void) {
    int shown = 0;
    for (int i = 0; i < nmsg && shown < 24; i++, shown++)
        printf("EMULOG %s x%u pc=%08x lr=%08x frame=%u %s\n", (msgs[i].level & ERR_LEVELS) ? "error" : "note",
               msgs[i].count, msgs[i].pc, msgs[i].lr, msgs[i].frame, msgs[i].msg);
    printf("EMULOG errors=%d notes=%d\n", nerr, nmsg - nerr);
}

static void die(const char *fmt, ...) {
    va_list a;
    va_start(a, fmt);
    fprintf(stderr, "harness: ");
    if (lineNo) fprintf(stderr, "line %d: ", lineNo);
    vfprintf(stderr, fmt, a);
    fputc('\n', stderr);
    va_end(a);
    exit(2);
}

// ---------------------------------------------------------------- parsing
static uint32_t num(const char *s, const char *what) {
    if (!*s) die("missing %s", what);
    char *end;
    unsigned long v = strtoul(s, &end, 0);
    if (*end) die("bad %s '%s' (an unresolved {symbol}? run the script through sym.py)", what, s);
    return (uint32_t)v;
}
static int32_t snum(const char *s, const char *what) {
    if (!*s) die("missing %s", what);
    char *end;
    long v = strtol(s, &end, 0);
    if (*end) die("bad %s '%s'", what, s);
    return (int32_t)v;
}

static uint32_t parse_keys(const char *s) {
    static const char *names[10] = { "A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L" };
    if (!*s) die("missing keys");
    if (!strcmp(s, "-")) return 0;
    uint32_t k = 0;
    char buf[256];
    strncpy(buf, s, 255); buf[255] = 0;
    for (char *t = strtok(buf, "|+,"); t; t = strtok(NULL, "|+,")) {
        int i;
        for (i = 0; i < 10; i++) if (!strcmp(t, names[i])) { k |= 1u << i; break; }
        if (i == 10) die("unknown key '%s'", t);
    }
    return k;
}

static FILE *open_out(const char *path) {
    if (!*path) die("missing file name");
    FILE *f = fopen(path, "wb");
    if (!f) die("cannot write %s", path);
    return f;
}

// ---------------------------------------------------------------- running
static void wav_header(FILE *f, long n) {
    uint32_t rate = 32768, bytes = n * 4;
    fseek(f, 0, SEEK_SET);
    fwrite("RIFF", 1, 4, f); uint32_t v = 36 + bytes; fwrite(&v, 4, 1, f);
    fwrite("WAVEfmt ", 1, 8, f); v = 16; fwrite(&v, 4, 1, f);
    uint16_t s = 1; fwrite(&s, 2, 1, f); s = 2; fwrite(&s, 2, 1, f);
    fwrite(&rate, 4, 1, f); v = rate * 4; fwrite(&v, 4, 1, f);
    s = 4; fwrite(&s, 2, 1, f); s = 16; fwrite(&s, 2, 1, f);
    fwrite("data", 1, 4, f); fwrite(&bytes, 4, 1, f);
}

static void drain_audio(void) {
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

static int lenient;
static void finish(void);
static void run_frames(int n) {
    for (int i = 0; i < n; i++) {
        core->setKeys(core, heldKeys);
        core->runFrame(core);
        drain_audio();
        if (fatal || nerr >= FLOOD || nerrAll >= FLOOD_ALL) {
            printf("harness: the ROM crashed (line %d, frame %u)\n", lineNo, core->frameCounter(core));
            finish();
        }
    }
}

static void shot(const char *path) {
    FILE *f = open_out(path);
    fprintf(f, "P6\n%u %u\n255\n", W, H);
    for (unsigned i = 0; i < W * H; i++) {
        uint32_t c = vbuf[i];
        unsigned char rgb[3] = { c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF };
        fwrite(rgb, 1, 3, f);
    }
    fclose(f);
}

static uint32_t rnd(void) { rngState ^= rngState << 13; rngState ^= rngState >> 17; rngState ^= rngState << 5; return rngState; }

static uint32_t mem(int bits, uint32_t ad) {
    return bits == 8 ? core->busRead8(core, ad) : bits == 16 ? core->busRead16(core, ad) : core->busRead32(core, ad);
}

static void expect(int bits, int sgn, const char *a1, const char *op, const char *a3, const char *text) {
    uint32_t ad = num(a1, "address");
    int64_t have = sgn ? (int64_t)(int32_t)mem(bits, ad) : (int64_t)mem(bits, ad);
    int64_t want = sgn ? (int64_t)snum(a3, "value") : (int64_t)num(a3, "value");
    int ok;
    if (!strcmp(op, "==")) ok = have == want;
    else if (!strcmp(op, "!=")) ok = have != want;
    else if (!strcmp(op, "<")) ok = have < want;
    else if (!strcmp(op, "<=")) ok = have <= want;
    else if (!strcmp(op, ">")) ok = have > want;
    else if (!strcmp(op, ">=")) ok = have >= want;
    else { die("unknown comparison '%s'", op); return; }
    if (!ok) {
        failedExpect++;
        printf("EXPECT FAILED line %d: [%s] is %lld, expected %s %lld%s%s\n", lineNo, a1, (long long)have, op,
               (long long)want, *text ? ": " : "", text);
    }
}

static void finish(void) {
    if (wav) { wav_header(wav, wavSamples); fclose(wav); wav = NULL; }
    report_log();
    fflush(stdout);
    int status = (fatal || (nerr && !lenient)) ? 3 : failedExpect ? 1 : 0;
    core->deinit(core);
    exit(status);
}

int main(int argc, char **argv) {
    int ai = 1;
    while (ai < argc && argv[ai][0] == '-' && argv[ai][1] == '-') {
        if (!strcmp(argv[ai], "--lenient")) lenient = 1;
        else { fprintf(stderr, "harness: unknown option %s\n", argv[ai]); return 2; }
        ai++;
    }
    if (argc - ai < 1) { fprintf(stderr, "usage: harness [--lenient] rom.gba [script | -] [savefile]\n"); return 2; }
    const char *rom = argv[ai], *script = argc - ai > 1 ? argv[ai + 1] : "-", *save = argc - ai > 2 ? argv[ai + 2] : NULL;
    { FILE *t = fopen(rom, "rb"); if (!t) { fprintf(stderr, "harness: cannot read ROM %s\n", rom); return 2; } fclose(t); }
    mLogSetDefaultLogger(&logger);
    core = mCoreFind(rom);
    if (!core) { fprintf(stderr, "harness: %s is not a ROM mGBA knows\n", rom); return 2; }
    core->init(core);
    mCoreInitConfig(core, NULL);
    core->desiredVideoDimensions(core, &W, &H);
    vbuf = calloc(W * H, sizeof(color_t));
    snapbuf = calloc(W * H, sizeof(color_t));
    core->setVideoBuffer(core, vbuf, W);
    core->setAudioBufferSize(core, 2048);
    blip_set_rates(core->getAudioChannel(core, 0), core->frequency(core), 32768);
    blip_set_rates(core->getAudioChannel(core, 1), core->frequency(core), 32768);
    if (!mCoreLoadFile(core, rom)) { fprintf(stderr, "harness: cannot load %s\n", rom); return 2; }
    if (save) {
        struct VFile *vf = VFileOpen(save, O_CREAT | O_RDWR);
        if (!vf) { fprintf(stderr, "harness: cannot open save file %s\n", save); return 2; }
        core->loadSave(core, vf);
    }
    core->reset(core);

    FILE *in = stdin;
    if (strcmp(script, "-")) in = fopen(script, "r");
    if (!in) { fprintf(stderr, "harness: cannot read script %s\n", script); return 2; }
    char line[1024];
    while (fgets(line, sizeof line, in)) {
        lineNo++;
        char cmd[64] = {0}, a1[256] = {0}, a2[256] = {0}, a3[256] = {0};
        int used = 0;
        int n = sscanf(line, "%63s %255s %255s %255s%n", cmd, a1, a2, a3, &used);
        if (n <= 0 || cmd[0] == '#') continue;
        const char *rest = n >= 4 ? line + used : "";
        while (*rest == ' ') rest++;
        char text[256];
        strncpy(text, rest, 255); text[255] = 0;
        text[strcspn(text, "\r\n")] = 0;
        if (!strcmp(cmd, "hold")) heldKeys = parse_keys(a1);
        else if (!strcmp(cmd, "run")) run_frames((int)num(a1, "frame count"));
        else if (!strcmp(cmd, "tap")) {
            uint32_t old = heldKeys;
            heldKeys = parse_keys(a1);
            run_frames(n > 2 ? (int)num(a2, "frame count") : 2);
            heldKeys = old;
            run_frames(2);
        }
        else if (!strcmp(cmd, "seed")) rngState = num(a1, "seed") | 1;
        else if (!strcmp(cmd, "monkey")) {
            // random held keys, changed every 4..60 frames, a quarter of them down, biased to walking
            int left = (int)num(a1, "frame count");
            uint32_t mask = num(a2, "key mask");
            while (left > 0) {
                uint32_t k = rnd() & rnd() & mask;
                if ((rnd() & 3) == 0) k |= 64 & mask;
                int d = 4 + rnd() % 57;
                if (d > left) d = left;
                heldKeys = k; run_frames(d); left -= d;
            }
            heldKeys = 0;
        }
        else if (!strcmp(cmd, "shot")) shot(a1);
        else if (!strcmp(cmd, "snap")) memcpy(snapbuf, vbuf, W * H * sizeof(color_t));
        else if (!strcmp(cmd, "cmp")) {
            unsigned cnt = 0, x0 = W, y0 = H, x1 = 0, y1 = 0;
            for (unsigned y = 18; y < 134; y++)
                for (unsigned x = 0; x < W; x++)
                    if ((vbuf[y * W + x] & 0xFFFFFF) != (snapbuf[y * W + x] & 0xFFFFFF)) {
                        cnt++;
                        if (x < x0) x0 = x;
                        if (x > x1) x1 = x;
                        if (y < y0) y0 = y;
                        if (y > y1) y1 = y;
                    }
            if (!*a1) die("cmp needs a name");
            printf("CMP %s %u %u %u %u %u\n", a1, cnt, cnt ? x0 : 0, cnt ? y0 : 0, x1, y1);
            if (cnt && *a2 && strcmp(a2, "-")) shot(a2);
            if (n > 3 && cnt > num(a3, "maximum")) {
                failedExpect++;
                printf("EXPECT FAILED line %d: %s: %u pixels differ, at most %s allowed\n", lineNo, a1, cnt, a3);
            }
        }
        else if (!strcmp(cmd, "audio")) {
            if (wav) { wav_header(wav, wavSamples); fclose(wav); wav = NULL; }
            if (strcmp(a1, "-")) { wav = open_out(a1); wavSamples = 0; wav_header(wav, 0); }
        }
        else if (!strcmp(cmd, "peek8")) printf("%s = %u\n", a1, mem(8, num(a1, "address")));
        else if (!strcmp(cmd, "peek16")) printf("%s = %u\n", a1, mem(16, num(a1, "address")));
        else if (!strcmp(cmd, "peek32")) printf("%s = %u\n", a1, mem(32, num(a1, "address")));
        else if (!strcmp(cmd, "peeks32")) printf("%s = %d\n", a1, (int32_t)mem(32, num(a1, "address")));
        else if (!strcmp(cmd, "poke8")) core->busWrite8(core, num(a1, "address"), num(a2, "value"));
        else if (!strcmp(cmd, "poke16")) core->busWrite16(core, num(a1, "address"), num(a2, "value"));
        else if (!strcmp(cmd, "poke32")) core->busWrite32(core, num(a1, "address"), num(a2, "value"));
        else if (!strcmp(cmd, "expect8")) expect(8, 0, a1, a2, a3, text);
        else if (!strcmp(cmd, "expect16")) expect(16, 0, a1, a2, a3, text);
        else if (!strcmp(cmd, "expect32")) expect(32, 0, a1, a2, a3, text);
        else if (!strcmp(cmd, "expects32")) expect(32, 1, a1, a2, a3, text);
        else if (!strcmp(cmd, "echo")) { const char *t = line + 4; if (*t == ' ') t++; fputs(t, stdout); if (!strchr(t, '\n')) fputc('\n', stdout); }
        else if (!strcmp(cmd, "fill")) {
            uint32_t ad = num(a1, "address"), len = num(a2, "length"), b = num(a3, "byte") & 255;
            for (uint32_t i = 0; i < len; i += 4) core->busWrite32(core, ad + i, b * 0x01010101u);
        }
        else if (!strcmp(cmd, "dump")) {
            uint32_t ad = num(a1, "address"), len = num(a2, "length");
            FILE *f = open_out(a3);
            for (uint32_t i = 0; i < len; i++) fputc(core->busRead8(core, ad + i), f);
            fclose(f);
        }
        else if (!strcmp(cmd, "frame")) printf("frame %u\n", core->frameCounter(core));
        else if (!strcmp(cmd, "regs")) {
            struct GBA *g = core->board;
            printf("regs pc=%08x sp=%08x lr=%08x cpsr=%08x\n", g->cpu->gprs[15], g->cpu->gprs[13], g->cpu->gprs[14], g->cpu->cpsr.packed);
        }
        else die("unknown command '%s'", cmd);
        fflush(stdout);
    }
    finish();
    return 0;
}
