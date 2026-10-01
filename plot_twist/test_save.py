"""Tests for save.py: writing the save file and reading it back.

conftest.py points save.SAVE_PATH to a fresh temporary folder for every test,
so these tests never touch the real save file.
"""

import json
import os

import pytest

import engine
import save


def mid_game():
    """A game in progress: the wand picked up, now in the cabin."""
    state, _ = engine.pick_up(engine.new_game(), "wand")
    state, _ = engine.enter(state, "deck_to_cabin")
    return state


def test_a_saved_game_loads_back_identical():
    save.save_game(mid_game())
    assert save.load_game() == mid_game()


def test_saving_without_a_path_uses_save_path(save_file):
    """SAVE_PATH is read at every save, not fixed when save.py is loaded: that is what lets the tests move it."""
    save.save_game(mid_game())
    assert save_file.exists()


def test_the_file_holds_a_version_and_the_state_only(save_file):
    """The four keys of the state and nothing else: the position on screen is not saved."""
    save.save_game(mid_game())
    data = json.loads(save_file.read_text(encoding="utf-8"))
    assert data == {"version": save.VERSION, "state": mid_game()}
    assert set(data["state"]) == engine.STATE_KEYS


def test_a_new_save_replaces_the_old_one():
    save.save_game(engine.new_game())
    save.save_game(mid_game())
    assert save.load_game() == mid_game()


def test_saving_leaves_no_temporary_file(save_file):
    save.save_game(mid_game())
    assert os.listdir(save_file.parent) == [save_file.name]


def test_a_save_that_breaks_halfway_keeps_the_previous_one(save_file):
    """The new save goes to a temporary file first: if writing breaks, the old file is untouched."""
    save.save_game(mid_game())
    before = save_file.read_bytes()
    broken = mid_game()
    broken["ending"] = {"not", "json"}  # a set cannot be written as JSON: writing fails halfway
    with pytest.raises(TypeError):
        save.save_game(broken)
    assert save_file.read_bytes() == before
    assert save.load_game() == mid_game()


def test_no_file_means_nothing_to_load():
    assert save.load_game() is None


GOOD_FILE = json.dumps({"version": save.VERSION, "state": engine.new_game()}).encode()


@pytest.mark.parametrize("content", [
    pytest.param(b"", id="empty file"),
    pytest.param(b"{ not json", id="broken JSON"),
    pytest.param(GOOD_FILE[:30], id="cut halfway"),
    pytest.param(b"\xff\xfe\x00\x01", id="not text"),
    pytest.param(b"[]", id="not an object"),
    pytest.param(json.dumps({"state": engine.new_game()}).encode(), id="no version"),
    pytest.param(json.dumps({"version": save.VERSION + 1, "state": engine.new_game()}).encode(), id="another version"),
    pytest.param(json.dumps({"version": save.VERSION}).encode(), id="no state"),
])
def test_unusable_files_load_as_nothing(save_file, content):
    save_file.write_bytes(content)
    assert save.load_game() is None


def test_a_folder_instead_of_a_file_loads_as_nothing(save_file):
    save_file.mkdir()
    assert save.load_game() is None


def test_another_path_can_be_given(tmp_path):
    other = tmp_path / "other.json"
    save.save_game(mid_game(), other)
    assert save.load_game(other) == mid_game()
    assert save.load_game() is None
