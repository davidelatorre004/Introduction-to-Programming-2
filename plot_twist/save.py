"""Saving and loading Plot Twist: one small JSON file next to the game.

This module only writes and reads. It does not know the rules: whatever comes
back from the file goes through engine.restore_state() before it is played.
"""

import json
import os

# Change this number when the shape of the save file changes: files written
# with another number are then ignored instead of being misread.
VERSION = 1

# Where the game is saved when no other path is given. The tests point it to
# a temporary folder (see conftest.py), so they never touch the real save.
SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "savegame.json")


def save_game(state, path=None):
    """Write the game to the save file, replacing the previous save.

    The game goes into a temporary file first, which then takes the place of
    the old one in a single step: if writing breaks halfway, the previous save
    is still there, intact. Errors while writing are not hidden: they are raised.
    """
    # None means SAVE_PATH as it is now. A default of path=SAVE_PATH would be
    # fixed once, when this file is loaded, and the tests could not move it.
    if path is None:
        path = SAVE_PATH
    temporary = str(path) + ".tmp"
    with open(temporary, "w", encoding="utf-8") as file:
        json.dump({"version": VERSION, "state": state}, file, indent=2)
    os.replace(temporary, path)


def load_game(path=None):
    """Return the game stored in the save file, or None if there is no usable save.

    A missing file, a broken one and one written with another VERSION all give
    None: the menu then simply does not offer to resume.
    """
    if path is None:
        path = SAVE_PATH
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError):
        # OSError: no file, or it cannot be read. ValueError: it is not valid JSON text.
        return None
    if not isinstance(data, dict) or data.get("version") != VERSION or "state" not in data:
        return None
    return data["state"]
