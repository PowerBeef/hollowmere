# SPDX-License-Identifier: MIT
"""Where everything lives, for the engine's tools.

The engine's toolchain (this folder) builds and tests one game at a time: the
folder given by $GAME (default: game/, Hollowmere), the same variable the
Makefile takes. Importing this module also puts the toolchain, the game's
content modules and its levels on the import path, so a content module can
`from meshkit import Mesh` and a tool can `import furniture` without caring
where either lives.

  ROOT      the repository
  TOOLS     engine/tools (this folder)
  GAME      the game: game.mk, src/ (its C code), content/ (generators), assets/, tests/
  CONTENT   the game's content generators (models, textures, sounds, text...)
  LEVELS    the game's level scripts
  ASSETS    pre-baked assets that are slow to regenerate
  TESTS     the game's test scripts (boot.txt, playthrough, benchmark views)
  GEN       generated C, assembly and binary blobs (not under version control)
  OUT       the game's build folder; CACHE the asset cache (shared by all games)
  ROM, ELF  the test ROM (make test-rom) and its ELF: what the tools run,
            since it carries the debug commands they drive
  RELEASE_ROM, RELEASE_ELF   the release ROM (make)
  HARNESS   the headless mGBA test runner (make harness)
  BOOT      harness input that gets from power-on to the first level

$ROM and $ELF override the ROM and ELF the tools use.
"""
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(TOOLS))
GAME_NAME = os.environ.get('GAME', 'game').rstrip('/')
GAME = os.path.join(ROOT, GAME_NAME)
CONTENT = os.path.join(GAME, 'content')
LEVELS = os.path.join(CONTENT, 'levels')
ASSETS = os.path.join(GAME, 'assets')
TESTS = os.path.join(GAME, 'tests')


def game_mk():
    """The KEY := value settings of the game's game.mk."""
    d = {}
    path = os.path.join(GAME, 'game.mk')
    if not os.path.exists(path):
        sys.exit(f"no game at {GAME}: it needs a game.mk (see docs/MAKING_A_GAME.md)")
    for line in open(path):
        line = line.split('#', 1)[0]
        if ':=' in line:
            k, v = line.split(':=', 1)
            d[k.strip()] = v.strip()
    return d


TARGET = game_mk().get('TARGET', os.path.basename(GAME))
# (the same layout as the Makefile: Hollowmere keeps gen/ and build/)
if GAME_NAME == 'game':
    OUT = os.path.join(ROOT, 'build')
    GEN = os.path.join(ROOT, 'gen')
    RELEASE_ROM = os.path.join(ROOT, TARGET + '.gba')
else:
    OUT = os.path.join(ROOT, 'build', os.path.basename(GAME))
    GEN = os.path.join(OUT, 'gen')
    RELEASE_ROM = os.path.join(OUT, TARGET + '.gba')
BUILD = OUT
CACHE = os.path.join(ROOT, 'build', 'cache')
RELEASE_ELF = os.path.join(OUT, 'release', TARGET + '.elf')
ROM = os.environ.get('ROM', os.path.join(OUT, 'dev', TARGET + '-dev.gba'))
ELF = os.environ.get('ELF', os.path.join(OUT, 'dev', TARGET + '-dev.elf'))
HARNESS = os.path.join(ROOT, 'engine', 'harness', 'harness')
BOOT = os.path.join(TESTS, 'boot.txt')

for _p in (TESTS, LEVELS, CONTENT, TOOLS):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def tool(name):
    """Path of a script in engine/tools (to run it as a subprocess)."""
    return os.path.join(TOOLS, name)


def source(name):
    """Path of a toolchain or content module by file name (the asset build
    hashes their source text to know when to regenerate)."""
    for d in (TOOLS, CONTENT, LEVELS):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(name)
