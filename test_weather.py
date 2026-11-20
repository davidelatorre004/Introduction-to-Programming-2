"""Tests for weather.py and the storm in main.py: one storm that grows with the three puzzles.

conftest.py switches the storm off for the other tests; these turn it back on.
"""

import pygame
import pytest

import effects
import engine
import main
import sounds
import sprites
import story
import test_main as game
import weather

VIEW_SIZE = main.VIEW.size


@pytest.fixture(autouse=True)
def storm_on(monkeypatch):
    monkeypatch.setitem(effects.FX, "weather", True)


@pytest.fixture
def app():
    pygame.font.init()
    return main.new_app(main.load_fonts())


def at_level(level, seed=weather.SEED):
    """A weather already at this level."""
    storm = weather.new_weather(seed)
    weather.set_goal(storm, level)
    return storm


def run(storm, frames):
    """Move the weather on, frame by frame; returns [(frame, thunder)] for each thunder heard."""
    heard = []
    for frame in range(frames):
        thunder = weather.update(storm, VIEW_SIZE)
        if thunder is not None:
            heard.append((frame, thunder))
    return heard


def strikes(storm, frames):
    """The frames at which lightning struck, and the thunders heard, over `frames` frames."""
    struck = []
    heard = []
    for frame in range(frames):
        thunder = weather.update(storm, VIEW_SIZE)
        if storm["flash"] == 0:
            struck.append(frame)
        if thunder is not None:
            heard.append(frame)
    return struck, heard


def average(surface, area=None):
    return pygame.transform.average_color(surface, area or surface.get_rect())[:3]


# --- The level follows the progress -----------------------------------------------------------


def test_the_storm_waits_in_the_calm_until_the_first_puzzle_begins():
    assert weather.storm_level(0, 3, 0.0, started=False) == 0.0
    assert weather.storm_level(0, 3, 0.0, started=True) == weather.START


def test_each_puzzle_takes_the_storm_further_and_it_never_goes_back():
    levels = []
    for solved in range(3):
        for share in (0.0, 0.25, 0.5, 0.75, 1.0):
            levels.append(weather.storm_level(solved, 3, share, started=True))
    levels.append(weather.storm_level(3, 3, 0.0, started=True))
    assert levels == sorted(levels)
    assert levels[-1] == 1.0


def test_solving_a_puzzle_is_a_step_forward():
    for solved in range(2):
        before = weather.storm_level(solved, 3, 1.0, started=True)
        after = weather.storm_level(solved + 1, 3, 0.0, started=True)
        assert after - before == pytest.approx(weather.SOLVE_STEP)


def test_the_last_puzzle_starts_below_the_worst_and_reaches_it_just_before_its_end():
    start = weather.storm_level(2, 3, 0.0, started=True)
    assert start == pytest.approx(2 / 3) and start < 1.0
    assert weather.storm_level(2, 3, 0.5, started=True) < 1.0  # still growing during the last puzzle
    assert weather.storm_level(2, 3, 1.0, started=True) == 1.0  # only its last step left: the peak


def test_the_rain_and_the_thunder_start_with_the_second_puzzle():
    end_of_first = weather.storm_level(0, 3, 1.0, started=True)
    start_of_second = weather.storm_level(1, 3, 0.0, started=True)
    assert weather.rain_amount(end_of_first) == 0 and end_of_first < weather.THUNDER_FROM
    assert weather.rain_amount(start_of_second) > 0 and start_of_second >= weather.THUNDER_FROM
    assert weather.rain_amount(1.0) == 1.0


def test_the_first_goal_is_taken_at_once_then_the_level_moves_slowly_and_only_up():
    storm = weather.new_weather()
    weather.set_goal(storm, 0.5)
    assert storm["level"] == 0.5  # a saved game resumes in its own weather
    weather.set_goal(storm, 0.9)
    previous = storm["level"]
    for _ in range(30):
        weather.update(storm, VIEW_SIZE)
        assert 0 < storm["level"] - previous <= weather.LEVEL_SPEED + 1e-9
        previous = storm["level"]
    weather.set_goal(storm, 0.2)
    assert storm["goal"] == 0.9  # a puzzle that starts over does not calm the storm
    run(storm, round(0.5 / weather.LEVEL_SPEED))
    assert storm["level"] == 0.9


def test_a_reset_brings_back_the_calm_but_keeps_soft_lightning():
    storm = at_level(1.0)
    storm["soft"] = True
    run(storm, 50)
    weather.reset(storm)
    assert storm["level"] == 0 and storm["fresh"] and storm["drops"] == [] and storm["soft"]


# --- Lightning and thunder --------------------------------------------------------------------


def test_no_lightning_and_no_thunder_in_the_calm():
    storm = at_level(0.0)
    struck, heard = strikes(storm, 4000)
    assert struck == [] and heard == []


def test_far_lightning_flashes_silently_while_the_first_puzzle_is_played():
    storm = at_level(0.2)
    struck, heard = strikes(storm, 8000)
    assert len(struck) >= 2 and heard == []


def test_lightning_strikes_at_irregular_moments_more_often_as_the_storm_grows():
    few, _ = strikes(at_level(0.35), 6000)
    many, _ = strikes(at_level(1.0), 6000)
    assert len(many) > 2 * len(few) > 0
    gaps = [later - earlier for earlier, later in zip(many, many[1:])]
    assert len(set(gaps)) > len(gaps) // 2  # never like clockwork


def test_each_thunder_follows_its_flash_sooner_as_the_storm_comes_near():
    def delays(level):
        storm = at_level(level, seed=3)
        struck, heard = strikes(storm, 6000)
        pairs = []
        for frame in heard:
            pairs.append(frame - max(strike for strike in struck if strike <= frame))
        assert pairs and all(delay >= 3 for delay in pairs)  # the light first, then the sound
        return sum(pairs) / len(pairs)

    assert delays(1.0) < delays(0.4)


def test_the_thunder_is_near_and_loud_only_in_the_worst_of_the_storm():
    far = [thunder for _, thunder in run(at_level(0.4), 6000)]
    near = [thunder for _, thunder in run(at_level(1.0), 6000)]
    assert {thunder["name"] for thunder in far} == {"thunder_far"}
    assert "thunder_near" in {thunder["name"] for thunder in near}
    assert max(thunder["volume"] for thunder in near) > max(thunder["volume"] for thunder in far)
    for thunder in far + near:
        assert thunder["name"] in sounds.EFFECTS and 0 < thunder["volume"] <= 1


def test_a_flash_is_short_and_never_too_bright():
    storm = at_level(1.0)
    longest = 0
    lit = 0
    for _ in range(6000):
        weather.update(storm, VIEW_SIZE)
        strength = weather.flash_strength(storm)
        assert 0 <= strength <= 1
        lit = lit + 1 if strength > 0 else 0
        longest = max(longest, lit)
    assert 0 < longest <= 4  # a flicker lasts a few frames


def test_soft_lightning_is_paler_flickers_once_and_never_shakes():
    storm = at_level(1.0)
    storm["soft"] = True
    flickers = 0
    for _ in range(6000):
        before = weather.flash_strength(storm)
        weather.update(storm, VIEW_SIZE)
        now = weather.flash_strength(storm)
        assert now <= weather.SOFT_FLASH
        assert storm["shake"] == 0
        if now > 0 and before == 0:
            flickers += 1
        if storm["flash"] == weather.FLASH_LENGTH:
            assert flickers == 1  # one flicker for each strike
            flickers = 0


def test_the_strongest_thunder_shakes_the_ship_only_in_the_worst_of_the_storm():
    calm = at_level(0.5)
    for _ in range(6000):
        weather.update(calm, VIEW_SIZE)
        assert calm["shake"] == 0
    storm = at_level(1.0)
    shaken = False
    for frame in range(6000):
        weather.update(storm, VIEW_SIZE)
        offset = weather.shake(storm, frame, weather.SHAKE_POWER)
        assert abs(offset[0]) <= weather.SHAKE_POWER and abs(offset[1]) <= weather.SHAKE_POWER
        shaken = shaken or storm["shake"] > 0
    assert shaken


# --- Rain, wind and clouds --------------------------------------------------------------------


def test_the_rain_thickens_a_few_drops_at_a_time():
    storm = at_level(0.0)
    weather.set_goal(storm, 1.0)
    previous = 0
    for _ in range(round(1 / weather.LEVEL_SPEED) + 200):
        weather.update(storm, VIEW_SIZE)
        assert len(storm["drops"]) - previous <= weather.DROPS_PER_FRAME
        previous = len(storm["drops"])
    assert len(storm["drops"]) == weather.MAX_DROPS


def test_the_wind_slants_the_rain_more_as_it_blows_harder():
    def drift(level):
        storm = at_level(level)
        run(storm, 200)
        drop = storm["drops"][0]
        x = drop["x"]
        weather.update(storm, VIEW_SIZE)
        return drop["x"] - x

    assert drift(1.0) < drift(0.45) < 0  # the drops fall to the left, more so in the strong wind


def test_the_waves_of_the_sea_move_faster_in_the_storm():
    calm, storm = at_level(0.0), at_level(1.0)
    run(calm, 600)
    run(storm, 600)
    assert storm["waves"] > 1.5 * calm["waves"]


def test_the_clouds_gather_and_darken_as_the_storm_grows():
    def shadow(level):
        return average(weather.cloud_picture(level))

    calm, middle, worst = shadow(0.0), shadow(0.5), shadow(1.0)
    assert all(m < c for m, c in zip(middle, calm))
    assert all(w < m for w, m in zip(worst, middle))


def test_the_clouds_repeat_with_no_seam():
    width, height = weather.CLOUD_SIZE
    for x, y in ((0, 5), (13, 40), (50, 71)):
        assert weather.periodic_noise(x, y, 24, 1) == pytest.approx(weather.periodic_noise(x + width, y + height, 24, 1))


# --- Drawing ------------------------------------------------------------------------------------


def drawn(level, outdoor=True, exposure=1.0, frames=120):
    storm = at_level(level)
    run(storm, frames)
    storm["flash"] = -1  # no lightning in the picture: only the weather itself
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    screen.fill((200, 160, 120))
    weather.draw(screen, main.VIEW, storm, outdoor, exposure, (0, 0))
    return screen


def test_the_deck_darkens_as_the_storm_grows_but_stays_readable():
    calm, middle, worst = (average(drawn(level), main.VIEW) for level in (0.0, 0.5, 1.0))
    assert sum(worst) < sum(middle) < sum(calm)
    assert max(worst) > 100  # still well lit enough to see everything


def test_inside_the_ship_the_storm_is_milder_and_the_mine_feels_nothing():
    outside = average(drawn(1.0), main.VIEW)
    inside = average(drawn(1.0, outdoor=False, exposure=main.weather_exposure("hold")), main.VIEW)
    mine = drawn(1.0, outdoor=False, exposure=main.weather_exposure("mine"))
    assert sum(inside) > sum(outside)
    assert average(mine) == (200, 160, 120)


def test_the_storm_never_covers_the_bar_at_the_top():
    screen = drawn(1.0)
    for x in range(0, main.WIDTH, 7):
        for y in range(0, main.HUD_HEIGHT):
            assert tuple(screen.get_at((x, y)))[:3] == (200, 160, 120)


def test_a_flash_brightens_the_deck_more_than_the_rooms_inside():
    def flashed(outdoor, exposure):
        storm = at_level(1.0)
        storm["flash"] = 0
        storm["power"] = 1.0
        screen = pygame.Surface((main.WIDTH, main.HEIGHT))
        screen.fill((100, 100, 100))
        weather.draw(screen, main.VIEW, storm, outdoor, exposure, (0, 0))
        dark = pygame.Surface((main.WIDTH, main.HEIGHT))
        dark.fill((100, 100, 100))
        storm["flash"] = -1
        weather.draw(dark, main.VIEW, storm, outdoor, exposure, (0, 0))
        return sum(average(screen, main.VIEW)) - sum(average(dark, main.VIEW))

    assert flashed(True, 1.0) > flashed(False, main.WEATHER_INSIDE) > 0


def test_puddles_form_on_the_deck_only_in_the_heavy_rain():
    surface = pygame.Surface((64, 64))
    spots = [pygame.Rect(16, 16, 16, 16)]
    surface.fill((165, 115, 65))
    weather.draw_puddles(surface, spots, weather.PUDDLE_FROM - 0.01, 0)
    assert average(surface) == (165, 115, 65)
    weather.draw_puddles(surface, spots, 1.0, 0)
    assert tuple(surface.get_at(spots[0].center))[:3] == weather.PUDDLE_COLOR


# --- The storm in the game ----------------------------------------------------------------------


def target_after(actions):
    return main.storm_target(game.play(actions))


def test_the_storm_follows_the_three_puzzles_of_the_ship_from_the_calm_to_its_worst():
    recipe = story.POTION_PUZZLES["remedy"]["recipe"]
    pours = [game.act("use_item", "cauldron", tincture) for tincture in recipe]
    stages = [
        [],                                                      # the opening: the calm
        game.IN_THE_CABIN,                                       # the first puzzle begins
        game.IN_THE_CABIN + [game.act("activate", "generator_a")],
        game.CIRCUIT_COMPLETE,                                   # the first puzzle solved
        game.IN_THE_HOLD,
        game.IN_THE_HOLD + [game.act("step_on", tile) for tile in game.TILE_SEQUENCE[:5]],
        game.TILES_SOLVED,                                       # the second puzzle solved
        game.TINCTURES_FOUND,
        game.TINCTURES_FOUND + pours[:1],
        game.TINCTURES_FOUND + pours[:2],
        game.TINCTURES_FOUND + pours[:3],                        # only the last tincture is left
        game.TINCTURES_FOUND + pours,                            # the third puzzle solved
        game.KEY_FUSED,
    ]
    levels = [target_after(actions) for actions in stages]
    assert levels == sorted(levels)
    assert levels[0] == 0.0 and levels[1] == weather.START
    assert weather.rain_amount(levels[2]) == 0                      # the first puzzle: no rain yet
    assert levels[3] >= 1 / 3 and weather.rain_amount(levels[3]) > 0  # the second: the rain begins
    assert 2 / 3 <= levels[6] < levels[7] < levels[8] < levels[9] < 1.0  # the third: it keeps growing...
    assert levels[10] == 1.0                                        # ...to its worst just before the end
    assert levels[11] == levels[12] == 1.0                          # and it stays there


def test_a_puzzle_that_starts_over_does_not_calm_the_storm(app):
    game.playing(app, game.IN_THE_CABIN + [game.act("activate", "generator_a")])
    main.update(app, 0, 0)
    high = app["weather"]["level"]
    app["state"] = game.play(game.IN_THE_CABIN)  # the generators back as they were, as when walking in again
    for _ in range(30):
        main.update(app, 0, 0)
    assert app["weather"]["level"] == high


def test_solving_a_puzzle_moves_the_storm_on_smoothly(app):
    game.playing(app, game.IN_THE_CABIN)
    main.update(app, 0, 0)
    assert app["weather"]["level"] == weather.START
    app["state"] = game.play(game.CIRCUIT_COMPLETE)
    main.update(app, 0, 0)
    assert app["weather"]["level"] == pytest.approx(weather.START + weather.LEVEL_SPEED)  # no jump
    for _ in range(round(1 / weather.LEVEL_SPEED)):
        main.update(app, 0, 0)
    assert app["weather"]["level"] == pytest.approx(main.storm_target(app["state"]))


def test_a_new_game_starts_in_the_calm_and_a_resumed_one_in_its_own_storm(app):
    game.playing(app, game.TILES_SOLVED)
    main.update(app, 0, 0)
    assert app["weather"]["level"] == pytest.approx(main.storm_target(app["state"]))
    main.open_main_menu(app)
    main.update(app, 0, 0)
    assert app["weather"]["fresh"] and app["weather"]["level"] == 0
    game.start_new_game(app)
    main.update(app, 0, 0)
    assert app["weather"]["level"] == 0.0 and app["lightning_due"] is False  # the opening bolt has struck


def test_the_thunder_is_heard_outside_and_muffled_inside(app, monkeypatch):
    heard = []
    monkeypatch.setattr(sounds, "play", lambda name, volume=1.0, pan=0.0: heard.append((name, volume)))
    for room, expected in (("deck", {"thunder_far", "thunder_near"}), ("hold", {"thunder_inside"})):
        heard.clear()
        state = game.play(game.TINCTURES_FOUND)
        state["room"] = room
        game.playing(app, game.TINCTURES_FOUND)
        app["state"] = state
        main.place_at_entry(app)
        app["weather"] = at_level(1.0)
        for _ in range(3000):
            main.update(app, 0, 0)
        thunders = {name for name, _ in heard if name.startswith("thunder")}
        assert thunders and thunders <= expected


def test_no_storm_reaches_the_mine(app, monkeypatch):
    heard = []
    monkeypatch.setattr(sounds, "play", lambda name, volume=1.0, pan=0.0: heard.append(name))
    state = game.play(game.TINCTURES_FOUND)
    state["room"] = "mine"
    app["state"] = state
    main.set_scene(app, "play")
    main.place_at_entry(app)
    app["weather"] = at_level(1.0)
    for _ in range(3000):
        main.update(app, 0, 0)
    assert not [name for name in heard if name.startswith("thunder")]
    assert main.weather_sounds(app) == (None, None)
    assert main.thunder_shake("mine") == 0


def test_the_rain_and_the_wind_are_heard_louder_on_the_deck_than_inside(app):
    game.playing(app, game.TINCTURES_FOUND)
    app["weather"] = at_level(1.0)
    main.update(app, 0, 0)
    app["state"]["room"] = "deck"
    (rain, rain_volume), (wind, wind_volume) = main.weather_sounds(app)
    assert (rain, wind) == ("rain", "wind") and rain_volume > 0 and wind_volume > 0
    app["state"]["room"] = "infirmary"
    (rain_far, rain_far_volume), (wind_far, wind_far_volume) = main.weather_sounds(app)
    assert (rain_far, wind_far) == ("rain_far", "wind_far")
    assert rain_far_volume < rain_volume and wind_far_volume < wind_volume
    for name in ("rain", "rain_far", "wind", "wind_far"):
        assert name in sounds.LOOPS


def test_in_the_calm_there_is_no_rain_to_hear(app):
    game.playing(app, [])
    main.update(app, 0, 0)
    rain, wind = main.weather_sounds(app)
    assert rain is None and wind[0] == "wind" and wind[1] < 0.1  # a breath of wind


def test_the_ceiling_leaks_in_the_heavy_rain(app):
    game.playing(app, game.TINCTURES_FOUND)
    main.update(app, 0, 0)
    app["weather"] = at_level(0.0)
    calm_hold = main.drip_chance(app, "hold")
    assert calm_hold == 1 / main.DRIP_EVERY and main.drip_chance(app, "cabin") == 0
    app["weather"] = at_level(1.0)
    assert main.drip_chance(app, "hold") > calm_hold and main.drip_chance(app, "cabin") > 0
    assert main.drip_chance(app, "mine") == 1 / main.DRIP_EVERY  # deep in the rock, as always


def test_without_the_storm_everything_is_as_before(app, monkeypatch):
    monkeypatch.setitem(effects.FX, "weather", False)
    assert main.drip_chance(app, "hold") == 1 / main.DRIP_EVERY and main.drip_chance(app, "cabin") == 0
    assert main.lantern_wind(app, "deck_lantern") == 1.0
    app["frame"] = main.WAVE_FRAMES * 5
    assert main.wave_frame(app) == 5 % main.SEA_PICTURES


def test_the_lantern_on_the_deck_swings_more_in_the_wind(app):
    game.playing(app, [])
    app["weather"] = at_level(1.0)
    run(app["weather"], 10)
    assert main.lantern_wind(app, "deck_lantern") > 1.5
    assert main.lantern_wind(app, "cabin_lantern") == 1.0  # inside, it only swings with the ship


def test_the_puddles_lie_on_free_floor_of_the_deck():
    spots = main.puddle_spots("deck")
    assert spots
    taken = [main.thing_rect(name) for name, info in story.OBJECTS.items() if info["room"] == "deck"]
    taken += [main.thing_rect(name) for name, info in story.ITEMS.items() if info["room"] == "deck"]
    taken += [main.door_rect(door) for door in main.doors_in("deck")]
    floor = main.floor_rect("deck")
    for spot in spots:
        assert spot.collidelist(taken) == -1 and floor.contains(spot)


def test_every_room_can_be_drawn_in_every_weather(app):
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    game.playing(app, game.TINCTURES_FOUND)
    for level in (0.0, 0.5, 1.0):
        for room in story.ROOMS:
            state = game.play(game.TINCTURES_FOUND)
            state["room"] = room
            app["state"] = state
            main.place_at_entry(app)
            app["weather"] = at_level(level)
            run(app["weather"], 90)
            app["weather"]["flash"] = 0
            app["weather"]["power"] = 1.0
            main.draw_play_screen(app, screen)


def test_f10_turns_soft_lightning_on_and_off(app):
    assert main.SOFT_FLASHES_KEY == pygame.K_F10 and "F10" in story.MESSAGES["window_title"]
    main.toggle_soft_flashes(app)
    assert app["weather"]["soft"] and app["banner"] == story.MESSAGES["soft_flashes_on"]
    main.toggle_soft_flashes(app)
    assert not app["weather"]["soft"] and app["banner"] == story.MESSAGES["soft_flashes_off"]


def test_soft_lightning_also_softens_the_opening_bolt(app, monkeypatch):
    monkeypatch.setattr(main, "LIGHTNING_FRAMES", 60)

    def brightness(soft):
        app["weather"]["soft"] = soft
        app["lightning"] = main.LIGHTNING_FRAMES  # its first frame: the white flash
        screen = pygame.Surface((main.WIDTH, main.HEIGHT))
        screen.fill((0, 0, 0))
        main.draw_lightning(app, screen)
        return sum(average(screen, pygame.Rect(0, 0, 20, 20)))

    assert 0 < brightness(True) < brightness(False)


def test_the_ending_has_no_storm_sounds(app):
    game.playing(app, game.TO_THE_CRAB_ENDING)
    main.update(app, 0, 0)
    assert engine.is_over(app["state"])
    assert main.weather_sounds(app) == (None, None)


# --- The seagulls ---------------------------------------------------------------------------------


SKY = main.deck_sky()


def flights(storm, frames):
    """The flights that took off over `frames` frames: (frame, heading, how many, line) each."""
    taken = []
    for frame in range(frames):
        before = len(storm["gulls"])
        flight = storm["flight"]
        weather.update(storm, VIEW_SIZE, SKY)
        if storm["flight"] != flight:
            new = storm["gulls"][before:] if len(storm["gulls"]) > before else storm["gulls"][-1:]
            taken.append((frame, new[0]["heading"], len(new), new[0]["line"]))
    return taken


def test_seagulls_fly_over_the_deck_in_a_pattern_that_repeats():
    taken = flights(at_level(0.0), weather.GULL_FIRST + weather.GULL_EVERY * (2 * len(weather.GULL_FLIGHTS) - 1))
    frames = [frame for frame, _, _, _ in taken]
    assert frames[0] == weather.GULL_FIRST - 1
    assert all(later - earlier == weather.GULL_EVERY for earlier, later in zip(frames, frames[1:]))  # like clockwork
    pattern = [(heading, count) for _, heading, count, _ in taken]
    expected = [(heading, count) for _, heading, count in weather.GULL_FLIGHTS]
    assert pattern == expected * 2
    lines = [line for _, _, _, line in taken]
    assert lines[:len(expected)] == lines[len(expected):]  # the same lines every time
    assert flights(at_level(0.0, seed=99), 2000) == flights(at_level(0.0), 2000)  # whatever the luck


def test_a_flight_flies_in_a_v_behind_its_leader():
    storm = at_level(0.0)
    storm["next_flight"] = 1
    weather.update(storm, VIEW_SIZE, SKY)
    leader, *others = storm["gulls"]
    for other in others:
        assert (other["x"] - leader["x"]) * leader["heading"] < 0  # behind
        assert other["line"] != leader["line"]                      # above or below


def test_seagulls_cross_the_whole_deck_and_then_are_gone():
    storm = at_level(0.0)
    storm["next_flight"] = 1
    weather.update(storm, VIEW_SIZE, SKY)
    storm["next_flight"] = 10 ** 6  # no other flight
    leader = storm["gulls"][0]
    start = leader["x"]
    for _ in range(1000):
        weather.update(storm, VIEW_SIZE, SKY)
        for gull in storm["gulls"]:
            assert SKY.top - weather.GULL_SIZE <= gull["y"] <= SKY.bottom
    assert abs(leader["x"] - start) > SKY.width and storm["gulls"] == []  # all of the flight, across and away


def test_no_new_seagull_comes_once_it_rains_and_the_last_ones_fly_away():
    storm = at_level(weather.START)
    while not storm["gulls"]:
        weather.update(storm, VIEW_SIZE, SKY)
    weather.set_goal(storm, weather.storm_level(1, 3, 0.0, started=True))  # the first puzzle is solved
    while weather.rain_amount(storm["level"]) == 0:
        weather.update(storm, VIEW_SIZE, SKY)
    flying = list(storm["gulls"])
    for _ in range(2000):
        weather.update(storm, VIEW_SIZE, SKY)
        for gull in storm["gulls"]:
            assert gull in flying  # no new one
    assert storm["gulls"] == []  # the last ones are gone


def test_a_seagull_flaps_then_glides():
    pictures = [weather.gull_wings({"age": age}) for age in range(0, 120, weather.GULL_FLAP)]
    assert {0, 1, 2} <= set(pictures)
    glide = pictures[len(weather.GULL_WINGS):len(weather.GULL_WINGS) + weather.GULL_GLIDE]
    assert glide == [1] * weather.GULL_GLIDE


def test_the_seagull_pictures_fly_left_and_flip_to_fly_right():
    for wings in range(3):
        left = sprites.image("seagull_" + str(wings))
        right = sprites.image("seagull_" + str(wings), flip=True)
        assert left.get_size() == (weather.GULL_SIZE, weather.GULL_SIZE)
        beak = [x for x in range(16) for y in range(16) if tuple(left.get_at((x, y)))[:3] == sprites.PALETTE["o"]]
        assert beak and max(beak) < 8  # the head on the left
        assert tuple(right.get_at((15 - beak[0], 10)))[:3] == sprites.PALETTE["o"]


def gull_at(x, y):
    return {"x": x, "y": y, "line": y, "heading": -1, "age": 0}


def white_pixels(screen):
    return {(x, y) for x in range(main.WIDTH) for y in range(main.VIEW.top, main.HEIGHT)
            if tuple(screen.get_at((x, y)))[:3] == sprites.PALETTE["w"]}


def test_the_seagulls_are_drawn_on_the_deck_only():
    storm = at_level(0.0)
    storm["gulls"] = [gull_at(100, main.HUD_HEIGHT + 60)]
    outside = pygame.Surface((main.WIDTH, main.HEIGHT))
    outside.fill((40, 60, 120))
    weather.draw(outside, main.VIEW, storm, True, 1.0, (0, 0))
    inside = pygame.Surface((main.WIDTH, main.HEIGHT))
    inside.fill((40, 60, 120))
    weather.draw(inside, main.VIEW, storm, False, main.WEATHER_INSIDE, (0, 0))
    assert white_pixels(outside)  # a white seagull over the deck
    assert not white_pixels(inside)


def test_the_seagulls_stay_on_their_way_when_the_view_scrolls():
    storm = at_level(0.0)
    storm["gulls"] = [gull_at(100, main.HUD_HEIGHT + 60)]

    def seen(camera):
        screen = pygame.Surface((main.WIDTH, main.HEIGHT))
        screen.fill((40, 60, 120))
        weather.draw(screen, main.VIEW, storm, True, 1.0, camera)
        return white_pixels(screen)

    still = seen((0, 0))
    scrolled = seen((0, 40))  # the player has walked down the deck: the view is 40 pixels lower
    assert scrolled == {(x, y - 40) for x, y in still if y - 40 >= main.VIEW.top}  # 40 pixels higher on screen
    assert seen((0, 150)) == set()  # far enough down, they are out of the view


def test_in_the_game_the_seagulls_fly_over_the_deck_not_the_screen(app):
    game.playing(app, [])
    main.update(app, 0, 0)
    storm = app["weather"]
    storm["next_flight"] = 1
    main.update(app, 0, 0)
    assert storm["gulls"] and all(SKY.left - 3 * 16 <= gull["x"] <= SKY.right + 3 * 16 for gull in storm["gulls"])
    lines = [gull["line"] for gull in storm["gulls"]]
    game.p1(app)["pos"] = main.spawn_at_entry("deck")
    for _ in range(30):
        main.update(app, 0, 1)  # the player walks down: the gulls keep their lines in the room
    assert [gull["line"] for gull in storm["gulls"]] == lines
