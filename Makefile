# Hollowmere Engine + Hollowmere (the flagship game)
#
#   make assets     generate gen/ from the game's content (engine/tools/build_assets.py)
#   make            build hollowmere.gba
#   make harness    build the headless mGBA test runner (needs libmgba)
#   make clean      remove build/ and the ROM (gen/ and the asset cache stay)
#
# The engine runtime lives in engine/src, the game's own code in game/src;
# both build into one ROM with the assets generated in gen/.

PREFIX  := arm-none-eabi-
CC      := $(PREFIX)gcc
AS      := $(PREFIX)gcc
OBJCOPY := $(PREFIX)objcopy

BUILD   := build
ESRC    := engine/src
GSRC    := game/src
GEN     := gen
SRCDIRS := $(ESRC) $(GSRC)
HEADERS := $(wildcard $(ESRC)/*.h) $(wildcard $(GSRC)/*.h) $(wildcard $(GEN)/*.h)

ARCH    := -mcpu=arm7tdmi -mtune=arm7tdmi -mthumb-interwork
CBASE   := $(ARCH) -O2 -Wall -Wextra -Wno-unused-parameter -Wno-missing-field-initializers -ffreestanding -fno-strict-aliasing \
           -fomit-frame-pointer -ffunction-sections -fdata-sections -I$(ESRC) -I$(GSRC) -I$(GEN) $(DEFS)
CTHUMB  := $(CBASE) -mthumb
CARM    := $(CBASE) -marm -O3 -mlong-calls -fno-tree-loop-distribute-patterns
LDFLAGS := $(ARCH) -mthumb -nostartfiles -T $(ESRC)/gba.ld -Wl,-Map,$(BUILD)/hollowmere.map \
           -Wl,--gc-sections -specs=nano.specs

# Sources by file name, sorted (the link order: Thumb C, generated C, ARM
# IWRAM C, then assembly), found in either tree through vpath
CNAMES  := $(sort $(notdir $(filter-out %.iwram.c,$(foreach d,$(SRCDIRS),$(wildcard $(d)/*.c))))) \
           $(notdir $(wildcard $(GEN)/*.c))
INAMES  := $(sort $(notdir $(foreach d,$(SRCDIRS),$(wildcard $(d)/*.iwram.c))))
SNAMES  := $(sort $(notdir $(foreach d,$(SRCDIRS),$(wildcard $(d)/*.s)))) $(notdir $(wildcard $(GEN)/*.s))
OBJS    := $(patsubst %.c,$(BUILD)/%.o,$(CNAMES)) \
           $(patsubst %.iwram.c,$(BUILD)/%.iwram.o,$(INAMES)) \
           $(patsubst %.s,$(BUILD)/%.o,$(SNAMES))

vpath %.c $(SRCDIRS) $(GEN)
vpath %.s $(SRCDIRS) $(GEN)

TARGET     := hollowmere
GAME_TITLE := HOLLOWMERE
GAME_CODE  := HLWE

all: $(TARGET).gba

$(TARGET).gba: $(BUILD)/$(TARGET).elf
	$(OBJCOPY) -O binary $< $@
	python3 engine/tools/fixheader.py $@ $(GAME_TITLE) $(GAME_CODE) 01

$(BUILD)/$(TARGET).elf: $(OBJS) $(ESRC)/gba.ld
	$(CC) $(LDFLAGS) -o $@ $(OBJS) -lc -lgcc

# the hottest ARM code is built at -O2 (smaller, so more of it fits IWRAM)
$(BUILD)/objects.iwram.o: objects.iwram.c $(HEADERS) | $(BUILD)
	$(CC) $(CARM) -O2 -c $< -o $@

$(BUILD)/render.iwram.o: render.iwram.c $(HEADERS) | $(BUILD)
	$(CC) $(CARM) -O2 -c $< -o $@

$(BUILD)/audio.iwram.o: audio.iwram.c $(HEADERS) | $(BUILD)
	$(CC) $(CARM) -O2 -c $< -o $@

$(BUILD)/%.iwram.o: %.iwram.c $(HEADERS) | $(BUILD)
	$(CC) $(CARM) -c $< -o $@

$(BUILD)/%.o: %.c $(HEADERS) | $(BUILD)
	$(CC) $(CTHUMB) -c $< -o $@

$(BUILD)/%.o: %.s | $(BUILD)
	$(AS) $(ARCH) $(DEFS) -x assembler-with-cpp -I. -c $< -o $@

$(BUILD)/data.o: $(wildcard $(GEN)/bin/*.bin)

$(BUILD):
	mkdir -p $@

harness: engine/harness/harness

engine/harness/harness: engine/harness/harness.c
	gcc -O2 -o $@ $< -lmgba

assets:
	python3 engine/tools/build_assets.py

clean:
	rm -rf $(BUILD)/*.o $(BUILD)/$(TARGET).elf $(BUILD)/$(TARGET).map $(TARGET).gba

.PHONY: all clean assets harness
