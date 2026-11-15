"""Tests for the sound effects: square waves made in code, and a game that runs the same without audio."""

import pygame
import pytest

import sounds

PEAK = int(32767 * sounds.VOLUME)


def test_a_note_is_a_square_wave_of_the_right_length():
    """1000 Hz at 8000 samples per second: four samples up, four down, for as long as the note lasts."""
    data = sounds.samples([(1000, 0.01)], 8000)
    assert len(data) == 80
    assert list(data[:16]) == ([PEAK] * 4 + [-PEAK] * 4) * 2


def test_each_note_fades_out_at_its_very_end():
    data = sounds.samples([(1000, 0.01)], 8000)
    assert 0 < abs(data[-1]) < PEAK
    assert abs(data[-1]) < abs(data[-30])


def test_a_pause_is_silence():
    data = sounds.samples([(0, 0.01)], 8000)
    assert len(data) == 80
    assert set(data) == {0}


def test_every_channel_gets_the_same_sample():
    mono = sounds.samples([(1000, 0.01)], 8000)
    stereo = sounds.samples([(1000, 0.01)], 8000, channels=2)
    assert list(stereo[0::2]) == list(mono)
    assert list(stereo[1::2]) == list(mono)


def test_every_effect_is_short():
    for name, notes in sounds.EFFECTS.items():
        assert notes, name
        assert 0 < sum(length for _, length in notes) < 1, name


def test_without_audio_everything_is_silent(monkeypatch):
    """No mixer (no sound card): nothing is loaded, and playing anything does nothing and breaks nothing."""
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)
    sounds.load()
    assert sounds._loaded == {}
    for name in list(sounds.EFFECTS) + [None, "no_such_sound"]:
        sounds.play(name)


def test_with_audio_every_effect_is_made_for_the_mixer(monkeypatch):
    """With a mixer (here SDL's silent "dummy" one), each effect becomes a sound as long as its notes."""
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    pygame.mixer.init(frequency=22050, size=-16, channels=2)
    try:
        sounds.load()
        rate = pygame.mixer.get_init()[0]
        assert set(sounds._loaded) == set(sounds.EFFECTS)
        for name, notes in sounds.EFFECTS.items():
            expected = sum(int(rate * length) for _, length in notes) / rate
            assert sounds._loaded[name].get_length() == pytest.approx(expected, abs=0.002), name
        sounds.play("ding")
    finally:
        sounds._loaded.clear()
        pygame.mixer.quit()


def test_a_negative_frequency_is_noise_held_for_as_long_as_it_says():
    """-1000 at 8000 samples per second: a level every 8 samples, up or down with no pattern, the same every time."""
    data = sounds.samples([(-1000, 0.1)], 8000)
    assert len(data) == 800
    levels = [data[index] for index in range(0, 720, 8)]
    for index in range(0, 720, 8):
        assert set(data[index:index + 8]) == {data[index]}  # held between two steps
    assert set(levels) == {PEAK, -PEAK}  # as loud as a square wave, both ways
    runs = [len(run) for run in "".join("u" if level > 0 else "d" for level in levels).replace("ud", "u d").replace("du", "d u").split()]
    assert len(set(runs)) > 2  # runs of different lengths: not a regular wave
    assert list(data) == list(sounds.samples([(-1000, 0.1)], 8000))
    assert 0 < abs(data[-1]) < PEAK  # it fades out like a note


def test_low_noise_is_rougher_than_high_noise():
    low = sounds.samples([(-50, 0.2)], 8000)
    high = sounds.samples([(-4000, 0.2)], 8000)

    def changes(data):
        return sum(1 for index in range(1, len(data) - 100) if (data[index] > 0) != (data[index - 1] > 0))
    assert changes(low) < 12 < 200 < changes(high)


def test_the_register_of_the_noise_never_gets_stuck():
    register, seen = sounds.NOISE_SEED, set()
    for _ in range(2000):
        register = sounds.noise_bit(register)
        assert 0 < register < 2 ** 15
        seen.add(register)
    assert len(seen) == 2000  # no short loop


def test_the_statue_and_the_claw_have_their_sounds():
    for name, noisy in (("crumble", True), ("snap", True), ("shatter", True)):
        notes = sounds.EFFECTS[name]
        assert any(frequency < 0 for frequency, _ in notes) == noisy, name
    assert min(frequency for frequency, _ in sounds.EFFECTS["crumble"] if frequency > 0) < 60   # deep
    assert sum(length for _, length in sounds.EFFECTS["snap"]) < 0.15                            # dry
    assert max(-frequency for frequency, _ in sounds.EFFECTS["shatter"] if frequency < 0) > 8000  # sharp
