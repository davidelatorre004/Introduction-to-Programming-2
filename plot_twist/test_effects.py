"""Tests for the visual effects (effects.py, and how main.py starts them).

The effects never change the game: these tests check that they start when they
should, end when they should, and that their tools (particles, glows, dissolves,
ripples) do what they promise. conftest.py keeps the save file in a temporary folder.
"""

import pygame
import pytest

import effects
import engine
import main
import sprites
import story
import test_main as game


@pytest.fixture
def app():
    pygame.font.init()
    app = main.new_app(main.load_fonts())
    main.set_scene(app, "play")
    return app


p1 = game.p1


def playing(app, actions, position=None):
    app["state"] = game.play(actions)
    app["dialog"] = []
    app["fade"] = 0
    p1(app)["pos"] = position or main.spawn_at_entry(app["state"]["room"])
    main.update(app, 0, 0)  # the effects settle into the room
    return app


def run(app, frames):
    for _ in range(frames):
        main.update(app, 0, 0)
        app["dialog"] = []


def act(app, verb, target, item=None):
    main.do_action(app, {"verb": verb, "target": target, "item": item})
    app["dialog"] = []


# --- The tools ------------------------------------------------------------------------


def test_particles_move_and_die():
    fx = effects.new_fx()
    effects.spawn(fx, 10, 10, 5, effects.SPARK, speed=1, life=10)
    assert len(fx["particles"]) == 5
    start = [(p["x"], p["y"]) for p in fx["particles"]]
    effects.update(fx)
    assert [(p["x"], p["y"]) for p in fx["particles"]] != start
    for _ in range(10):
        effects.update(fx)
    assert fx["particles"] == []


def test_particles_never_pile_up():
    fx = effects.new_fx()
    effects.spawn(fx, 0, 0, effects.MAX_PARTICLES + 50, effects.SPARK)
    assert len(fx["particles"]) == effects.MAX_PARTICLES


def test_the_effects_look_the_same_every_time():
    first, second = effects.new_fx(), effects.new_fx()
    for fx in (first, second):
        effects.spawn(fx, 5, 5, 20, effects.SPARK, speed=2)
    assert first["particles"] == second["particles"]


def test_a_dissolve_hides_more_and_more_pixels():
    picture = pygame.Surface((16, 16), pygame.SRCALPHA)
    picture.fill((200, 100, 50, 255))

    def solid(surface):
        return sum(1 for x in range(16) for y in range(16) if surface.get_at((x, y))[3] > 0)
    assert solid(effects.dissolved(picture, 0)) == 256
    assert solid(effects.dissolved(picture, 1)) == 0
    half = solid(effects.dissolved(picture, 0.5))
    assert 80 < half < 176
    assert solid(effects.dissolved(picture, 0.5, appearing=True)) == 256 - half  # building up is the reverse
    assert solid(effects.dissolved(picture, 0.25)) > half > solid(effects.dissolved(picture, 0.75))


def test_a_glow_adds_light_and_a_dimmed_one_adds_none():
    surface = pygame.Surface((40, 40))
    surface.fill((10, 10, 10))
    effects.glow(surface, (20, 20), 8, (100, 50, 0), 0)
    assert tuple(surface.get_at((20, 20)))[:3] == (10, 10, 10)
    effects.glow(surface, (20, 20), 8, (100, 50, 0), 1)
    middle, edge, outside = (tuple(surface.get_at(p))[:3] for p in ((20, 20), (26, 20), (35, 20)))
    assert middle[0] > edge[0] > 10 and outside == (10, 10, 10)


def test_a_ripple_keeps_the_edges_of_its_area_still():
    surface = pygame.Surface((40, 40))
    for x in range(40):
        surface.fill((x * 6, 0, 0), (x, 0, 1, 40))
    before = pygame.image.tobytes(surface, "RGB")
    area = pygame.Rect(5, 5, 30, 30)
    changed = False
    for frame in range(0, 80, 7):
        copy = surface.copy()
        effects.ripple(copy, area, frame)
        for x in range(40):
            assert copy.get_at((x, area.top)) == surface.get_at((x, area.top))
            assert copy.get_at((x, area.bottom - 1)) == surface.get_at((x, area.bottom - 1))
        changed = changed or pygame.image.tobytes(copy, "RGB") != before
    assert changed


# --- What starts the effects ---------------------------------------------------------------


def test_a_barrier_dissolves_instead_of_vanishing(app):
    playing(app, game.IN_THE_CABIN + [game.act("activate", "generator_a")], main.tile_rect(14, 4).topleft)
    act(app, "activate", "generator_c")  # the circuit is complete
    assert "barrier" not in [thing["id"] for thing in engine.things_here(app["state"])]  # gone for the rules
    fading = app["fx"]["fading"]
    assert len(fading) == 1 and fading[0]["rect"] == main.thing_rect("barrier")
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    run(app, effects.BARRIER_FADE_FRAMES // 2)
    main.draw(app, screen)  # half dissolved: it can be drawn
    assert app["fx"]["fading"]
    run(app, effects.BARRIER_FADE_FRAMES)
    assert app["fx"]["fading"] == []


def test_leaving_the_room_forgets_its_effects(app):
    playing(app, game.IN_THE_CABIN + [game.act("activate", "generator_a")], main.tile_rect(14, 4).topleft)
    act(app, "activate", "generator_c")
    app["state"] = game.play(game.FIRST_HALF)
    main.update(app, 0, 0)
    assert app["fx"]["fading"] == [] and app["fx"]["room"] == "deck"


def test_the_generator_left_off_trembles_when_the_others_are_on(app):
    state = game.play(game.IN_THE_CABIN)
    for letter in "abcdefgh":
        state["flags"]["generator_" + letter] = letter != "c"
    assert main._almost_complete(state, "generator_c")
    assert not main._almost_complete(state, "generator_d")  # it is on
    assert not main._almost_complete(game.play(game.IN_THE_CABIN), "generator_a")  # half of them are off


def test_generators_that_are_on_throw_sparks(app):
    playing(app, game.IN_THE_CABIN + [game.act("activate", "generator_a")])
    run(app, 200)
    assert app["fx"]["particles"]


def test_the_liquid_follows_the_recipe(app):
    playing(app, game.TINCTURES_FOUND, main.tile_rect(9, 8).topleft)
    colors = [main.cauldron_color(app["state"])]
    for tincture in story.POTION_PUZZLES["remedy"]["recipe"]:
        act(app, "use_item", "cauldron", tincture)
        colors.append(main.cauldron_color(app["state"]))
        assert app["fx"]["particles"], tincture  # bubbles
    assert colors == [effects.LIQUID[0], effects.LIQUID[1], effects.LIQUID[2], effects.LIQUID[3], effects.LIQUID["ready"]]


def test_a_portal_warps_instead_of_fading(app):
    state = engine.new_game()
    state["room"] = "corridor_end"
    app["state"] = state
    main.go_through_portal(app, "corridor_portal")
    assert app["fx"]["warp"] == effects.WARP_FRAMES and app["fade"] == 0
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    main.draw(app, screen)
    run(app, effects.WARP_FRAMES)
    assert app["fx"]["warp"] == 0


def test_a_lit_tile_sends_a_wave_and_a_mistake_red_sparks(app):
    playing(app, game.IN_THE_HOLD)
    main.floor_action(app, {"verb": "step_on", "target": "tile_1"})
    assert app["fx"]["waves"] and app["fx"]["waves"][0]["center"] == main.thing_rect("tile_1").center
    main.floor_action(app, {"verb": "step_on", "target": "tile_4"})
    assert [p["color"] for p in app["fx"]["particles"] if p["color"] in effects.RED]
    run(app, effects.TILE_WAVE_FRAMES)
    assert app["fx"]["waves"] == []


def test_the_halves_weld_with_sparks_and_a_flash(app):
    before_anvil = game.DOCTOR_AT_PEACE + [game.act("enter", "infirmary_to_hold"), game.act("enter", "hold_to_deck"),
                                           game.act("enter", "deck_to_cabin"), game.act("enter", "cabin_to_east_room")]
    playing(app, before_anvil, main.tile_rect(7, 7).topleft)
    act(app, "use_item", "anvil", "key")
    assert app["fx"]["fuse"] is not None
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    for _ in range(effects.FUSE_FRAMES):
        main.draw(app, screen)
        main.update(app, 0, 0)
        if app["fx"]["fuse"] is not None and app["fx"]["fuse"]["age"] == main.FUSE_MEET + 1:
            assert app["fx"]["flash"] > 0 and len(app["fx"]["particles"]) >= effects.FUSE_SPARKS // 2
    assert app["fx"]["fuse"] is None


def test_picking_up_the_wand_sends_a_spark_up_the_arm(app):
    playing(app, [], main.tile_rect(8, 6).topleft)
    act(app, "pick_up", "wand")
    assert app["fx"]["wand_rise"] is not None
    run(app, 5)
    assert app["fx"]["particles"]
    run(app, effects.WAND_RISE_FRAMES)
    assert app["fx"]["wand_rise"] is None


def test_dust_floats_only_indoors_and_always_the_same(app):
    playing(app, [])
    assert app["fx"]["dust"] == []  # the deck is outdoors
    playing(app, game.IN_THE_HOLD)
    assert app["fx"]["dust"]
    floor = main.floor_rect("hold")
    first, second = effects.new_fx(), effects.new_fx()
    effects.reset_room(first, "hold", floor, True)
    effects.reset_room(second, "hold", floor, True)
    assert first["dust"] == second["dust"]  # walking back in finds the same dust
    for speck in first["dust"]:
        assert floor.collidepoint(speck["x"], speck["y"])


def test_the_map_shows_the_anvil_once_the_doctor_is_at_peace_and_its_room_is_known(app):
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    # To the empty room east of the cabin, and back into the cabin (so the player's dot is not on it).
    there_and_back = [game.act("enter", door) for door in ("infirmary_to_hold", "hold_to_deck", "deck_to_cabin",
                                                           "cabin_to_east_room", "east_room_to_cabin")]

    def anvil_drawn(actions):
        playing(app, actions)
        main.draw_hud(app, screen)
        area = main.map_area("east_room")
        return tuple(screen.get_at(area.center))[:3] == main.COLORS["black"]
    assert not anvil_drawn(game.TINCTURES_FOUND + there_and_back)  # the room is known, the doctor not at peace yet
    assert not anvil_drawn(game.DOCTOR_AT_PEACE)                   # at peace, but the room not seen yet
    assert anvil_drawn(game.DOCTOR_AT_PEACE + there_and_back)


def test_every_effect_can_be_switched_off(app, monkeypatch):
    for name in effects.FX:
        monkeypatch.setitem(effects.FX, name, False)
    playing(app, game.IN_THE_CABIN + [game.act("activate", "generator_a")], main.tile_rect(14, 4).topleft)
    act(app, "activate", "generator_c")
    assert app["fx"]["fading"] == []  # the barrier simply vanishes, as before
    playing(app, game.IN_THE_HOLD)
    assert app["fx"]["dust"] == []
    state = engine.new_game()
    state["room"] = "corridor_end"
    app["state"] = state
    main.go_through_portal(app, "corridor_portal")
    assert app["fx"]["warp"] == 0 and app["fade"] == main.FADE_FRAMES  # the dark fade of before
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    for room in story.ROOMS:
        playing(app, [])
        app["state"]["room"] = room
        main.draw(app, screen)


def test_every_room_can_be_drawn_with_every_effect_running(app):
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    for room in story.ROOMS:
        state = engine.new_game()
        state["room"] = room
        app["state"] = state
        p1(app)["pos"] = main.spawn_at_entry(room)
        for _ in range(3):
            main.update(app, 0, 0)
            main.draw(app, screen)
    assert sprites.image("portal") is not None


# --- Shaking, and a screen that breaks into pieces ----------------------------------------


def test_a_shake_pushes_the_picture_around_and_dies_down():
    total, power = 40, 4
    first = [effects.shake_offset(frame, total - frame, total, power) for frame in range(10)]
    last = [effects.shake_offset(frame, total - frame, total, power) for frame in range(30, 40)]
    assert len(set(first)) > 5  # a different push in almost every frame
    assert any(dx != 0 for dx, dy in first) and any(dy != 0 for dx, dy in first)  # both ways
    assert any(dx < 0 for dx, dy in first + last) and any(dx > 0 for dx, dy in first + last)
    for frame in range(total):
        dx, dy = effects.shake_offset(frame, total - frame, total, power)
        reach = power * (total - frame) / total
        assert abs(dx) <= reach + 0.5 and abs(dy) <= reach + 0.5, frame  # never further than it should
    assert max(abs(dx) + abs(dy) for dx, dy in first) > max(abs(dx) + abs(dy) for dx, dy in last)
    assert effects.shake_offset(7, 0, total, power) == (0, 0) and effects.shake_offset(7, -3, total, power) == (0, 0)
    assert effects.shake_offset(12, 30, total, power) == effects.shake_offset(12, 30, total, power)  # no surprises


SCREEN = (256, 224)
HIT = (128, 112)


def test_the_web_of_cracks_covers_the_whole_screen_with_pieces_around_the_hit():
    pieces = effects.crack_web(SCREEN, HIT, seed=11)
    assert pieces == effects.crack_web(SCREEN, HIT, seed=11) and pieces != effects.crack_web(SCREEN, HIT, seed=12)
    assert len(pieces) >= 20 and all(len(piece) >= 3 for piece in pieces)
    for piece in pieces:
        for x, y in piece:
            assert 0 <= x <= SCREEN[0] and 0 <= y <= SCREEN[1]
    assert sum(1 for piece in pieces if HIT in piece) >= 8  # a fan of pieces meets where the claw hit
    for corner in ((0, 0), (SCREEN[0], 0), (0, SCREEN[1]), SCREEN):
        assert any(corner in piece for piece in pieces), corner
    covered = pygame.Surface(SCREEN)
    for piece in pieces:
        pygame.draw.polygon(covered, (255, 255, 255), piece)
    assert all(covered.get_at((x, y))[0] == 255 for x in range(SCREEN[0]) for y in range(SCREEN[1]))  # no hole


def test_the_web_works_for_a_hit_anywhere():
    for hit in ((40, 30), (200, 200), (128, 20)):
        covered = pygame.Surface(SCREEN)
        for piece in effects.crack_web(SCREEN, hit, seed=3):
            pygame.draw.polygon(covered, (255, 255, 255), piece)
        assert all(covered.get_at((x, y))[0] == 255 for x in range(0, SCREEN[0], 3) for y in range(0, SCREEN[1], 3))


def painted():
    """A picture with a different colour in every corner, to tell where a piece comes from."""
    picture = pygame.Surface(SCREEN)
    for x in range(SCREEN[0]):
        for y in range(0, SCREEN[1], 1):
            picture.set_at((x, y), (x, y, 90))
    return picture


def test_the_shards_are_cut_from_the_picture_and_put_together_they_are_the_picture():
    picture = painted()
    pieces = effects.crack_web(SCREEN, HIT, seed=11)
    shards = effects.cut_shards(picture, pieces, HIT, seed=11)
    assert len(shards) == len(pieces)
    again = pygame.Surface(SCREEN)
    again.fill((255, 0, 255))
    effects.draw_shards(again, shards, age=0)  # nothing has moved yet
    same = edges = 0
    for x in range(0, SCREEN[0], 2):
        for y in range(0, SCREEN[1], 2):
            color = tuple(again.get_at((x, y)))[:3]
            assert color != (255, 0, 255), (x, y)  # every pixel belongs to a shard
            same += color == (x, y, 90)
            edges += color == effects.SHARD_EDGE
    assert same > 0.85 * (SCREEN[0] // 2) * (SCREEN[1] // 2)  # the picture, but for the light on the edges
    assert edges > 100


def test_the_shards_fall_away_from_the_hit_turning_until_nothing_is_left():
    shards = effects.cut_shards(painted(), effects.crack_web(SCREEN, HIT, seed=11), HIT, seed=11)
    assert min(shard["delay"] for shard in shards) < max(shard["delay"] for shard in shards)  # the near ones first
    for shard in shards:
        start, turned = effects.shard_position(shard, shard["delay"])
        assert start == shard["rect"].center and turned == 0.0
        early, _ = effects.shard_position(shard, shard["delay"] + 5)
        late, angle = effects.shard_position(shard, shard["delay"] + 60)
        assert late[1] > early[1] and late[1] > SCREEN[1]  # down, and off the screen in a second
        away = shard["rect"].centerx - HIT[0]
        if abs(away) > 20:
            assert (early[0] - start[0]) * away > 0  # pushed away from the hit, sideways too
        assert angle == shard["spin"] * 60
    assert len({round(shard["spin"], 3) for shard in shards}) > len(shards) // 2  # each turns its own way
    screen = pygame.Surface(SCREEN)
    black = []
    for age in (0, 15, 30, 45, 70):
        screen.fill((0, 0, 0))
        effects.draw_shards(screen, shards, age)
        black.append(sum(1 for x in range(0, SCREEN[0], 4) for y in range(0, SCREEN[1], 4)
                         if tuple(screen.get_at((x, y)))[:3] == (0, 0, 0)))
    assert black == sorted(black) and black[0] == 0  # more and more of the black behind shows
    assert black[-1] == (SCREEN[0] // 4) * (SCREEN[1] // 4)  # in the end, all of it


def test_the_cracks_run_outwards_from_the_hit():
    pieces = effects.crack_web(SCREEN, HIT, seed=11)

    def cracked(reach):
        screen = pygame.Surface(SCREEN)
        screen.fill((90, 90, 90))
        effects.draw_cracks(screen, pieces, HIT, reach)
        return [(x, y) for x in range(SCREEN[0]) for y in range(SCREEN[1]) if tuple(screen.get_at((x, y)))[:3] != (90, 90, 90)]
    assert cracked(0) == [] or len(cracked(0)) < 12
    near, all_of_it = cracked(40), cracked(400)
    assert 0 < len(near) < len(all_of_it)
    assert all(abs(x - HIT[0]) <= 42 and abs(y - HIT[1]) <= 42 for x, y in near)  # not further than they have got
    assert any(x < 4 for x, y in all_of_it) and any(y > SCREEN[1] - 4 for x, y in all_of_it)  # to the edges


def test_the_two_new_effects_have_their_switches():
    assert effects.FX["crumble"] is True and effects.FX["shatter"] is True
