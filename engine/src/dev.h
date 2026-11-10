// SPDX-License-Identifier: MIT
// Test-build hooks. The test ROM (make test-rom) is compiled with -DDEV and
// carries the debug commands, the profiling counters and the sampling
// profiler the tools in engine/tools drive; the release ROM has none of them.
#ifndef DEV_H
#define DEV_H
#include "gba.h"

#ifdef DEV
#define DEV_ONLY(...) __VA_ARGS__
// cycles since the frame's timers were started (timers 2+3 cascaded, see main.c)
#define PROF_T() (((u32)REG_TM3CNT_L << 16) | REG_TM2CNT_L)
#else
#define DEV_ONLY(...)
#endif

#endif
