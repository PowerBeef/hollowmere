# SPDX-License-Identifier: MIT
"""Text the game's code shows by name: string_list() returns (NAME, text)
pairs, each of which becomes STR_NAME in the generated assets.h. (The text of
level scripts needs no entry here: the script compiler adds it.)"""


def string_list():
    return [('OPEN', 'Open'), ('CLOSE', 'Close'), ('LOCKED', 'It is locked.')]
