"""Tests for the sounds: the voices of an 8-bit sound chip made in code, their envelopes, sweeps and
filters, the effects and the loops, and a game that runs the same without audio."""

import math

import pygame
import pytest

import sounds

RATE = 8000


def plain(wave, freq, length=0.1, **more):
    """A voice at full volume all along: no attack, no release, so its samples are just the wave."""
    return sounds.layer(wave, freq, length, attack=0.0, release=0.0, **more)


def crossings(data):
    """How many times the sound goes from below zero to above it."""
    return sum(1 for index in range(1, len(data)) if data[index - 1] < 0 <= data[index])


def brightness(data):
    """How much the sound jumps from one sample to the next, on average: high for a hiss, low for a rumble."""
    return sum(abs(data[index] - data[index - 1]) for index in range(1, len(data))) / max(len(data) - 1, 1)


def loudness(data):
    return math.sqrt(sum(value * value for value in data) / max(len(data), 1))


# --- The voices of the chip ------------------------------------------------------------------


@pytest.mark.parametrize("wave, duty", [("pulse12", 0.125), ("pulse25", 0.25), ("square", 0.5)])
def test_a_pulse_is_up_for_its_duty_of_each_period(wave, duty):
    data = sounds.voice_samples(plain(wave, 500), RATE)
    assert len(data) == 800
    assert set(data) == {1.0, -1.0}
    assert sum(1 for value in data if value > 0) / len(data) == pytest.approx(duty, abs=0.01)
    assert crossings(data) == pytest.approx(50, abs=1)  # 500 Hz for a tenth of a second


def test_the_triangle_has_sixteen_levels_and_is_symmetric():
    data = sounds.voice_samples(plain("triangle", 125, 0.096), RATE)  # twelve whole periods
    levels = sorted(set(data))
    assert len(levels) == 16 and levels[0] == -1.0 and levels[-1] == 1.0
    assert sum(data) == pytest.approx(0, abs=1)  # as much down as up
    assert sounds.TRIANGLE == list(range(15, -1, -1)) + list(range(16))  # it falls, then rises again


def test_the_register_of_the_noise_never_gets_stuck():
    register, seen = sounds.NOISE_SEED, set()
    for _ in range(2000):
        register = sounds.noise_bit(register)
        assert 0 < register < 2 ** 15
        seen.add(register)
    assert len(seen) == 2000  # no short loop


def test_the_short_noise_loops_quickly_and_rings_like_metal():
    register, seen = sounds.NOISE_SEED, []
    for _ in range(400):
        register = sounds.noise_bit(register, short=True)
        seen.append(register)
    assert len(set(seen)) < 100  # a loop of 93 steps or less: a pitch, not a hiss
    noise = sounds.voice_samples(plain("noise", 4000, 0.2), RATE)
    metal = sounds.voice_samples(plain("metal", 4000, 0.2), RATE)
    assert set(noise) == set(metal) == {1.0, -1.0}
    assert noise != metal


def test_noise_is_held_between_two_steps_and_lower_is_rougher():
    data = sounds.voice_samples(plain("noise", 1000), RATE)
    for start in range(7, 720, 8):
        assert len(set(data[start:start + 8])) == 1  # a new level 1000 times a second: every 8 samples
    low = sounds.voice_samples(plain("noise", 50, 0.2), RATE)
    high = sounds.voice_samples(plain("noise", 4000, 0.2), RATE)
    assert crossings(low) < 12 < 100 < crossings(high)
    assert data == sounds.voice_samples(plain("noise", 1000), RATE)  # the same noise every time


# --- Envelopes, sweeps, filters ----------------------------------------------------------------


def test_the_envelope_rises_falls_holds_and_dies_in_sixteen_steps():
    voice = sounds.layer("square", 100, 0.5, attack=0.1, decay=0.1, sustain=0.5, release=0.2)
    levels = [sounds.envelope(voice, step / 100) for step in range(80)]
    assert levels[0] == 0.0 and levels[10] == 1.0          # attack
    assert levels[20] == 0.5 and levels[45] == 0.5         # decay, then sustain
    assert 0 < levels[60] < 0.5 and levels[71] == 0.0      # release, to silence
    assert all(level * sounds.STEPS == int(level * sounds.STEPS) for level in levels)  # 16 steps
    assert levels[:11] == sorted(levels[:11]) and levels[50:] == sorted(levels[50:], reverse=True)


def test_a_struck_voice_dies_away_by_itself():
    voice = sounds.hit("square", 440, 0.2)
    assert sounds.envelope(voice, 0.002) == 1.0
    assert sounds.envelope(voice, 0.1) == pytest.approx(0.5, abs=1 / 16)
    assert sounds.envelope(voice, 0.199) == pytest.approx(1 / 16)  # its last step...
    assert sounds.envelope(voice, 0.2 + voice["release"]) == 0.0  # ...then silence


def test_the_pitch_glides_to_its_target_by_equal_steps():
    voice = plain("square", 200, 1.0, to=800)
    assert sounds.pitch(voice, 0) == pytest.approx(200)
    assert sounds.pitch(voice, 0.5) == pytest.approx(400)  # half the way: an octave of the two
    assert sounds.pitch(voice, 1.0) == pytest.approx(800)
    data = sounds.voice_samples(voice, RATE)
    assert crossings(data[:2000]) < crossings(data[-2000:])  # it rises
    quick = plain("square", 200, 1.0, to=800, sweep=0.1)
    assert sounds.pitch(quick, 0.5) == pytest.approx(800)  # there in a tenth of a second, then it stays


def test_vibrato_wavers_and_tremolo_beats():
    voice = plain("square", 400, 1.0, vibrato=(5, 1.0))
    pitches = [sounds.pitch(voice, step / 100) for step in range(100)]
    assert max(pitches) == pytest.approx(400 * 2 ** (1 / 12), rel=0.01)
    assert min(pitches) == pytest.approx(400 * 2 ** (-1 / 12), rel=0.01)
    beating = sounds.voice_samples(plain("square", 400, 1.0, tremolo=(4, 0.8)), RATE)
    parts = [loudness(beating[start:start + 400]) for start in range(0, 8000, 400)]
    assert max(parts) > 3 * min(parts)


def test_a_lowpass_muffles_and_a_highpass_thins():
    raw = sounds.voice_samples(plain("noise", 8000), RATE)
    muffled = sounds.voice_samples(plain("noise", 8000, lowpass=300), RATE)
    thin = sounds.voice_samples(plain("square", 50, highpass=2000), RATE)
    assert brightness(muffled) < brightness(raw) / 4
    assert loudness(thin) < 0.5 * loudness(sounds.voice_samples(plain("square", 50), RATE))
    opening = sounds.voice_samples(plain("noise", 8000, 1.0, lowpass=200, lowpass_to=3000), RATE)
    assert brightness(opening[:1000]) < brightness(opening[-1000:])  # the filter opens: a whoosh


def test_voices_are_mixed_at_their_start():
    effect = [sounds.hit("square", 500, 0.05), sounds.hit("square", 500, 0.05, start=0.2)]
    data = sounds.render(effect, RATE)
    assert len(data) == int(sounds.effect_length(effect) * RATE)
    assert loudness(data[1000:1500]) == 0  # the pause between them
    assert loudness(data[1600:1800]) > 0


def test_loud_mixes_bend_instead_of_cracking():
    data = sounds.pcm([0.0, 0.5, 4.0, -4.0, 40.0], channels=2, repeat=2)
    assert len(data) == 5 * 4 and data[0] == 0
    assert list(data[4:8]) == [data[4]] * 4  # held, and the same on both sides
    assert 0 < data[4] < data[8] < data[16] <= 32767 and data[12] == -data[8]


# --- The effects ----------------------------------------------------------------------------


def test_every_effect_is_short_and_heard():
    for name, voices in sounds.EFFECTS.items():
        assert voices, name
        assert 0 < sounds.effect_length(voices) < 1.5, name
        assert loudness(sounds.render(voices, RATE)) > 0.05, name


def test_the_effects_all_sound_different():
    rendered = {name: sounds.render(voices, RATE) for name, voices in sounds.EFFECTS.items()}
    pictures = {(len(data), round(loudness(data), 3), round(brightness(data), 3)) for data in rendered.values()}
    assert len(pictures) == len(rendered)


def test_a_puddle_splashes_where_wood_knocks():
    wood = sounds.render(sounds.EFFECTS["step_wood"], RATE)
    puddle = sounds.render(sounds.EFFECTS["step_puddle"], RATE)
    assert len(puddle) > 2 * len(wood)  # a splash lasts
    assert any(voice["lowpass_to"] for voice in sounds.EFFECTS["step_puddle"])  # the water closes over the foot
    floors = {name for name in sounds.EFFECTS if name.startswith("step_")}
    assert floors == {"step_wood", "step_stone", "step_tiles", "step_earth", "step_puddle"}
    stone = sounds.render(sounds.EFFECTS["step_stone"], RATE)
    earth = sounds.render(sounds.EFFECTS["step_earth"], RATE)
    assert brightness(stone) > brightness(earth)  # stone clicks, earth thuds


def test_a_locked_door_thuds_and_rattles():
    voices = sounds.EFFECTS["locked"]
    assert any(voice["wave"] == "triangle" and voice["to"] < voice["freq"] for voice in voices)  # the thud
    rattles = [voice for voice in voices if voice["wave"] == "metal"]
    assert len(rattles) >= 3 and len({voice["start"] for voice in rattles}) == len(rattles)


def test_the_claws_click_and_through_a_wall_they_are_muffled():
    near = sounds.render(sounds.EFFECTS["claw_click"], RATE)
    far = sounds.render(sounds.EFFECTS["claw_click_far"], RATE)
    assert sounds.effect_length(sounds.EFFECTS["claw_click"]) < 0.1
    assert brightness(far) < brightness(near) / 2
    assert all(voice["lowpass"] for voice in sounds.EFFECTS["claw_click_far"])


def test_the_dash_is_a_rush_of_air_that_opens():
    voices = sounds.EFFECTS["dash"]
    air = next(voice for voice in voices if voice["wave"] == "noise")
    assert air["lowpass_to"] > air["lowpass"] and air["attack"] > 0.01
    assert any(voice["to"] and voice["to"] > voice["freq"] for voice in voices)  # and a rising pitch


def test_the_statue_rumbles_and_the_glass_tinkles():
    crumble = sounds.render(sounds.EFFECTS["crumble"], RATE)
    shatter = sounds.render(sounds.EFFECTS["shatter"], RATE)
    assert len(crumble) > len(shatter) and brightness(shatter) > brightness(crumble)
    assert min(voice["to"] or voice["freq"] for voice in sounds.EFFECTS["crumble"] if voice["wave"] == "triangle") < 50
    tinkles = [voice for voice in sounds.EFFECTS["shatter"] if voice["wave"] == "pulse12"]
    assert len(tinkles) >= 8 and min(voice["freq"] for voice in tinkles) > 2000
    pebbles = [voice for voice in sounds.EFFECTS["crumble"] if voice["highpass"]]
    assert len({voice["start"] for voice in pebbles}) >= 6  # bouncing at different moments
    assert sounds.EFFECTS["crumble"] == sounds.EFFECTS["crumble"]  # and always the same ones


# --- The loops -----------------------------------------------------------------------------


@pytest.mark.parametrize("name", list(sounds.LOOPS))
def test_a_loop_fades_into_its_own_start(name):
    length, voices = sounds.LOOPS[name]
    data = sounds.loop_samples(length, voices, RATE)
    assert len(data) == int(length * RATE)
    assert abs(data[-1] - data[0]) < 0.25  # no click at the seam
    assert loudness(data) > 0.02
    assert 0.9 < length <= 4.0


def test_the_sea_swells_and_inside_the_ship_it_is_muffled():
    length, voices = sounds.LOOPS["sea"]
    sea = sounds.loop_samples(length, voices, RATE)
    parts = [loudness(sea[start:start + 1600]) for start in range(0, len(sea) - 1600, 1600)]
    assert max(parts) > 1.5 * min(parts)  # waves
    far = sounds.loop_samples(*sounds.LOOPS["sea_far"][:1], sounds.LOOPS["sea_far"][1], RATE)
    assert brightness(far) < brightness(sea)


# --- Playing: left and right, loops that fade, no audio ---------------------------------------


def test_left_and_right_keep_the_same_loudness():
    assert sounds.sides(1.0, 0.0) == (pytest.approx(1.0), pytest.approx(1.0))
    assert sounds.sides(1.0, -1.0) == (pytest.approx(1.0), pytest.approx(0.0, abs=1e-9))
    assert sounds.sides(0.5, 1.0) == (pytest.approx(0.0, abs=1e-9), pytest.approx(0.5))
    left, right = sounds.sides(1.0, 0.5)
    assert left < right and left ** 2 + right ** 2 >= 1.0
    assert sounds.sides(3.0, 9.0) == sounds.sides(1.0, 1.0)  # out of range: kept in it


def test_without_audio_everything_is_silent(monkeypatch):
    """No mixer (no sound card): nothing is loaded, and playing anything does nothing and breaks nothing."""
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)
    sounds.load()
    assert sounds._loaded == {}
    for name in list(sounds.EFFECTS) + [None, "no_such_sound"]:
        sounds.play(name, 0.5, -0.3)
    sounds.loop("bed", "sea", 0.5)
    sounds.update_loops()
    assert sounds.loop_volume("bed", "sea") > 0  # the fades are kept all the same: the game does not care
    sounds._loops.clear()


def test_a_new_loop_fades_in_as_the_old_one_fades_out(monkeypatch):
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)
    sounds.load()
    sounds.loop("bed", "sea", 0.6)
    for _ in range(sounds.LOOP_FADE_FRAMES):
        sounds.update_loops()
    assert sounds.loop_volume("bed", "sea") == pytest.approx(0.6)
    sounds.loop("bed", "drips", 0.5)  # a new room
    for _ in range(sounds.LOOP_FADE_FRAMES // 2):
        sounds.update_loops()
    assert 0 < sounds.loop_volume("bed", "sea") < 0.6 and 0 < sounds.loop_volume("bed", "drips") < 0.5  # both, crossing
    for _ in range(sounds.LOOP_FADE_FRAMES):
        sounds.update_loops()
    assert sounds.loop_volume("bed", "sea") == 0 and [sound["name"] for sound in sounds._loops["bed"]] == ["drips"]
    sounds.loop("bed", None)
    for _ in range(sounds.LOOP_FADE_FRAMES):
        sounds.update_loops()
    assert sounds._loops["bed"] == []
    sounds._loops.clear()


def test_with_audio_every_sound_is_made_and_loops_have_channels_of_their_own(monkeypatch):
    """With a mixer (here SDL's silent "dummy" one), each effect and loop becomes a sound of its length."""
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    pygame.mixer.init(frequency=22050, size=-16, channels=2)
    try:
        sounds.load()
        assert set(sounds._loaded) == set(sounds.EFFECTS) | set(sounds.LOOPS)
        for name, voices in sounds.EFFECTS.items():
            assert sounds._loaded[name].get_length() == pytest.approx(sounds.effect_length(voices), abs=0.003), name
        for name, (length, _) in sounds.LOOPS.items():
            assert sounds._loaded[name].get_length() == pytest.approx(length, abs=0.003), name
        assert len(sounds._free) == sounds.LOOP_CHANNELS
        sounds.play("ding", 0.5, 0.7)
        sounds.loop("bed", "sea", 0.5, -0.4)
        assert len(sounds._free) == sounds.LOOP_CHANNELS - 1
        channel = sounds._loops["bed"][0]["channel"]
        assert channel.get_busy() and sounds.loop_volume("bed", "sea") == 0.0  # it starts silent and fades in
        for _ in range(sounds.LOOP_FADE_FRAMES):
            sounds.update_loops()
        assert sounds.loop_volume("bed", "sea") == pytest.approx(0.5)
        sounds.loop("bed", None)
        for _ in range(sounds.LOOP_FADE_FRAMES):
            sounds.update_loops()
        assert not channel.get_busy() and len(sounds._free) == sounds.LOOP_CHANNELS  # stopped, and given back
    finally:
        sounds._loaded.clear()
        sounds._loops.clear()
        sounds._free.clear()
        pygame.mixer.quit()
