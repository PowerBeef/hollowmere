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

// Time and count per face inside the prop drawer (g_objT, g_objF): only with
// make test-rom DEFS=-DFACEPROF, because the code is fast RAM the stack
// would otherwise have (engine/tools/stackcheck.py).
#if defined(DEV) && (defined(FACEPROF) || defined(FACELOG))
#define FACEPROF_ONLY(...) __VA_ARGS__
#else
#define FACEPROF_ONLY(...)
#endif

#endif
