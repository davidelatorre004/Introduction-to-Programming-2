"""Shared test setup: no test ever touches the real save file."""

import pytest

import save


@pytest.fixture(autouse=True)
def save_file(tmp_path, monkeypatch):
    """Point save.SAVE_PATH to a fresh temporary folder for every test, and return that file's path.

    The file does not exist until a test saves something.
    """
    path = tmp_path / "savegame.json"
    monkeypatch.setattr(save, "SAVE_PATH", str(path))
    return path
