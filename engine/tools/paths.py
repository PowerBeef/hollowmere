"""Where everything lives, for the engine's tools.

The engine's toolchain (this folder) builds and tests one game at a time; the
game is the folder given by $GAME (default: game/, Hollowmere). Importing this
module also puts the toolchain, the game's content modules and its levels on
the import path, so a content module can `from meshkit import Mesh` and a
tool can `import furniture` without caring where either lives.

  ROOT     the repository
  TOOLS    engine/tools (this folder)
  GAME     the game: src/ (its C code), content/ (generators), assets/, tests/
  CONTENT  the game's content generators (models, textures, sounds, text...)
  LEVELS   the game's level scripts
  ASSETS   pre-baked assets that are slow to regenerate (the Sister's frames)
  GEN      generated C, assembly and binary blobs (not under version control)
  BUILD    object files, the ELF and the asset cache (not under version control)
  ROM      the built cartridge image
  ELF      the linked ELF (symbols for the test harness)
  HARNESS  the headless mGBA test runner (make harness)
  BOOT     harness input that gets from power-on to the first level
"""
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(TOOLS))
GAME = os.path.join(ROOT, os.environ.get('GAME', 'game'))
CONTENT = os.path.join(GAME, 'content')
LEVELS = os.path.join(CONTENT, 'levels')
ASSETS = os.path.join(GAME, 'assets')
GEN = os.path.join(ROOT, 'gen')
BUILD = os.path.join(ROOT, 'build')
ROM = os.environ.get('ROM', os.path.join(ROOT, 'hollowmere.gba'))
ELF = os.environ.get('ELF', os.path.join(BUILD, 'hollowmere.elf'))
HARNESS = os.path.join(ROOT, 'engine', 'harness', 'harness')
BOOT = os.path.join(GAME, 'tests', 'boot.txt')

for _p in (LEVELS, CONTENT, TOOLS):
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
