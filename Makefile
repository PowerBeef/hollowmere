# SPDX-License-Identifier: MIT
# Hollowmere Engine: builds one game (GAME, default game/ = Hollowmere) into a ROM.
#
#   make assets     generate the game's data from its content (engine/tools/build_assets.py)
#   make            build the release ROM (hollowmere.gba)
#   make test-rom   build the test ROM: the same game with the debug commands
#                   and profiling counters the tools in engine/tools drive
#   make harness    build the headless mGBA test runner (needs libmgba)
#   make check      build everything and run the whole test suite
#   make clean      remove objects, ELFs and ROMs (generated data and the asset cache stay)
#
#   make GAME=examples/minimal ...     the same for another game
#   make DEFS=-DPIXCNT test-rom        extra compiler flags (objects rebuild when flags change)
#
# The engine runtime lives in engine/src, a game's own code in $(GAME)/src;
# both build into one ROM with the data generated from $(GAME)/content.

GAME ?= game
GAME := $(patsubst %/,%,$(GAME))
ifeq ($(wildcard $(GAME)/game.mk),)
$(error no game at '$(GAME)': it needs a game.mk (see docs/MAKING_A_GAME.md))
endif
include $(GAME)/game.mk          # TARGET, GAME_TITLE, GAME_CODE, MAKER_CODE

PREFIX  := arm-none-eabi-
CC      := $(PREFIX)gcc
OBJCOPY := $(PREFIX)objcopy

# Hollowmere keeps the historical locations (gen/, build/, hollowmere.gba);
# any other game builds under build/<its folder name>/
ifeq ($(GAME),game)
OUT := build
GEN := gen
ROM := $(TARGET).gba
else
OUT := build/$(notdir $(GAME))
GEN := $(OUT)/gen
ROM := $(OUT)/$(TARGET).gba
endif

# two variants of the same sources, each with its own objects
VARIANT ?= release
ifeq ($(VARIANT),dev)
VDEFS := -DDEV
OBJ   := $(OUT)/dev
IMAGE := $(OBJ)/$(TARGET)-dev.gba
else ifeq ($(VARIANT),release)
VDEFS :=
OBJ   := $(OUT)/release
IMAGE := $(ROM)
else
$(error VARIANT must be release or dev)
endif
ELF := $(OBJ)/$(basename $(notdir $(IMAGE))).elf

ESRC    := engine/src
GSRC    := $(GAME)/src
SRCDIRS := $(ESRC) $(GSRC)

ARCH    := -mcpu=arm7tdmi -mtune=arm7tdmi -mthumb-interwork
CBASE   := $(ARCH) -O2 -Wall -Wextra -Wno-unused-parameter -Wno-missing-field-initializers -ffreestanding -fno-strict-aliasing \
           -fomit-frame-pointer -ffunction-sections -fdata-sections -I$(ESRC) -I$(GSRC) -I$(GEN) $(VDEFS) $(DEFS)
CTHUMB  := $(CBASE) -mthumb
CARM    := $(CBASE) -marm -O3 -mlong-calls -fno-tree-loop-distribute-patterns
ASFLAGS := $(ARCH) $(VDEFS) $(DEFS) -x assembler-with-cpp -I.
LDFLAGS := $(ARCH) -mthumb -nostartfiles -T $(OBJ)/gba.ld -Wl,-Map,$(ELF:.elf=.map) \
           -Wl,--gc-sections -specs=nano.specs
DEPFLAGS = -MMD -MP -MF $(@:.o=.d)

# Sources by file name, sorted (the link order: Thumb C, generated C, ARM
# IWRAM C, then assembly), found in either tree through vpath
CSRC    := $(filter-out %.iwram.c,$(foreach d,$(SRCDIRS),$(wildcard $(d)/*.c)))
ISRC    := $(foreach d,$(SRCDIRS),$(wildcard $(d)/*.iwram.c))
SSRC    := $(foreach d,$(SRCDIRS),$(wildcard $(d)/*.s))
ALLSRC  := $(CSRC) $(ISRC) $(SSRC)
# a file in the game with the same name as an engine file would silently lose to it
DUPES   := $(strip $(foreach f,$(sort $(notdir $(ALLSRC))),$(if $(word 2,$(filter %/$(f),$(ALLSRC))),$(f))))
ifneq ($(DUPES),)
$(error the same file name in $(ESRC) and $(GSRC): $(DUPES))
endif
CNAMES  := $(sort $(notdir $(CSRC))) assets.c
INAMES  := $(sort $(notdir $(ISRC)))
SNAMES  := $(sort $(notdir $(SSRC))) data.s
OBJS    := $(patsubst %.c,$(OBJ)/%.o,$(CNAMES)) \
           $(patsubst %.iwram.c,$(OBJ)/%.iwram.o,$(INAMES)) \
           $(patsubst %.s,$(OBJ)/%.o,$(SNAMES))
GENFILES := $(GEN)/assets.h $(GEN)/assets.c $(GEN)/data.s

vpath %.c $(SRCDIRS) $(GEN)
vpath %.s $(SRCDIRS) $(GEN)

.DELETE_ON_ERROR:

all: $(IMAGE)

# the ROM is written under a temporary name and renamed once its header is in
$(IMAGE): $(ELF)
	$(OBJCOPY) -O binary $< $@.tmp
	python3 engine/tools/fixheader.py $@.tmp '$(GAME_TITLE)' '$(GAME_CODE)' '$(MAKER_CODE)'
	mv $@.tmp $@

$(ELF): $(OBJS) $(OBJ)/gba.ld
	$(CC) $(LDFLAGS) -o $@ $(OBJS) -lc -lgcc

# Objects depend on the flags they were built with: a different DEFS (or a
# changed Makefile) rebuilds them.
FLAGSIG := $(CC) $(CTHUMB) / $(CARM) / $(ASFLAGS) / $(LDFLAGS)
$(OBJ)/.flags: FORCE | $(OBJ)
	@echo '$(FLAGSIG)' | cmp -s - $@ || echo '$(FLAGSIG)' > $@
BUILDDEPS := $(OBJ)/.flags Makefile $(GAME)/game.mk

# the linker script takes its sizes from limits.h, through the preprocessor
$(OBJ)/gba.ld: $(ESRC)/gba.ld $(ESRC)/limits.h $(BUILDDEPS)
	$(CC) -E -P -x c -I$(ESRC) $< -o $@

# the hottest ARM code is built at -O2 (smaller, so more of it fits IWRAM)
$(OBJ)/objects.iwram.o $(OBJ)/render.iwram.o $(OBJ)/audio.iwram.o: $(OBJ)/%.iwram.o: %.iwram.c $(BUILDDEPS) | $(GENFILES)
	$(CC) $(CARM) -O2 $(DEPFLAGS) -c $< -o $@

$(OBJ)/%.iwram.o: %.iwram.c $(BUILDDEPS) | $(GENFILES)
	$(CC) $(CARM) $(DEPFLAGS) -c $< -o $@

# generated data: out-of-range values must not be truncated silently
$(OBJ)/assets.o: $(GEN)/assets.c $(BUILDDEPS)
	$(CC) $(CTHUMB) -Werror=overflow $(DEPFLAGS) -c $< -o $@

$(OBJ)/%.o: %.c $(BUILDDEPS) | $(GENFILES)
	$(CC) $(CTHUMB) $(DEPFLAGS) -c $< -o $@

$(OBJ)/%.o: %.s $(BUILDDEPS)
	$(CC) $(ASFLAGS) -c $< -o $@

$(OBJ)/data.o: $(GEN)/data.s $(wildcard $(GEN)/bin/*.bin)

-include $(OBJS:.o=.d)

$(OBJ):
	mkdir -p $@

# No generated data yet (a fresh clone): make it. After that it is only
# regenerated on request (make assets), since the asset build is slow.
$(GENFILES) &:
	GAME=$(GAME) python3 engine/tools/build_assets.py

assets:
	GAME=$(GAME) python3 engine/tools/build_assets.py

test-rom:
	$(MAKE) VARIANT=dev

harness: engine/harness/harness

engine/harness/harness: engine/harness/harness.c
	gcc -O2 -Wall -Wextra -o $@ $< -lmgba

check: all test-rom harness
	GAME=$(GAME) python3 engine/tools/check.py

clean:
	rm -rf $(OUT)/release $(OUT)/dev $(ROM)

FORCE:
.PHONY: all clean assets harness test-rom check FORCE
