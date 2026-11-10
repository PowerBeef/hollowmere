# SPDX-License-Identifier: MIT
# The example game: what the engine's Makefile needs to know about it.
#   make GAME=examples/minimal assets all
TARGET     := minimal
# cartridge header: title (up to 12 ASCII characters), four-letter game code,
# two-character maker code (00: homebrew)
GAME_TITLE := MINIMAL
GAME_CODE  := MINE
MAKER_CODE := 00
