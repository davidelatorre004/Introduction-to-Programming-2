"""Tests for the 8-bit graphics (M6): the sprites, the pixel font and what moves on screen.

M6 changed how the game looks, not what it does: the tests in the other files
did not change. These check that every thing on screen has a picture, that the
font can write every text of the game, and that the animations behave.
"""

import pygame
import pytest

import engine
import main
import pixel_font
import sprites
import story


@pytest.fixture
def app():
    """The interface just after launching the game, already playing a new game."""
    app = main.new_app(main.load_fonts())
    main.handle_key(app, pygame.K_RETURN)  # "New game"
    main.handle_key(app, pygame.K_RETURN)  # "1 player"
    main.handle_key(app, pygame.K_RETURN)  # the first character
    while app["dialog"]:
        main.handle_key(app, pygame.K_e)
    return app


def p1(app):
    """The first (and for now only) player of the interface."""
    return app["players"][0]


def play(actions):
    state = engine.new_game()
    for verb, target, item in actions:
        state, outcome = engine.perform(state, {"verb": verb, "target": target, "item": item})
        assert outcome["ok"], outcome
    return state


TILES = ["tile_1", "tile_2", "tile_3", "tile_4", "tile_5", "tile_3", "tile_1", "tile_5", "tile_2", "tile_4", "tile_3"]
TO_THE_CRAB_DOOR = ([("pick_up", "wand", None), ("enter", "deck_to_cabin", None), ("activate", "generator_a", None),
                     ("activate", "generator_c", None), ("pick_up", "key", None), ("enter", "cabin_to_deck", None),
                     ("enter", "deck_to_hold", None)]
                    + [("step_on", tile, None) for tile in TILES]
                    + [("pick_up", "second_key", None), ("enter", "hold_to_infirmary", None),
                       ("pick_up", "green_tincture", None), ("enter", "infirmary_to_corridor", None),
                       ("pick_up", "blue_tincture", None), ("enter", "corridor_to_infirmary", None),
                       ("enter", "infirmary_to_hold", None), ("enter", "hold_to_deck", None),
                       ("enter", "deck_to_cabin", None), ("enter", "cabin_to_galley", None),
                       ("pick_up", "red_tincture", None), ("enter", "galley_to_cabin", None),
                       ("enter", "cabin_to_helm", None), ("pick_up", "gold_tincture", None),
                       ("enter", "helm_to_cabin", None), ("enter", "cabin_to_deck", None),
                       ("enter", "deck_to_hold", None), ("enter", "hold_to_infirmary", None)]
                    + [("use_item", "cauldron", tincture) for tincture in story.POTION_PUZZLES["remedy"]["recipe"]]
                    + [("pick_up", "potion", None), ("use_item", "doctor", "potion"), ("enter", "infirmary_to_hold", None),
                       ("enter", "hold_to_deck", None), ("enter", "deck_to_cabin", None), ("enter", "cabin_to_galley", None),
                       ("use_item", "anvil", "key"), ("enter", "galley_to_cabin", None), ("enter", "cabin_to_deck", None)])
CRAB_ENDING = TO_THE_CRAB_DOOR + [("use_item", "deck_to_crab", "fused_key"), ("enter", "deck_to_crab", None),
                                  ("use_item", "crab", "wand")]
ANGEL_ENDING = TO_THE_CRAB_DOOR + [("use_item", "deck_to_angel", "fused_key"), ("enter", "deck_to_angel", None),
                                   ("use_item", "angel", "wand")]


# --- Sprites -------------------------------------------------------------------------


def test_every_sprite_is_a_proper_picture():
    """Rows of the same length, letters from the palette, and the sizes the game expects."""
    for name, rows in sprites.SPRITES.items():
        assert len({len(row) for row in rows}) == 1, name
        for row in rows:
            for letter in row:
                assert letter == "." or letter in sprites.PALETTE, (name, letter)
        size = (len(rows[0]), len(rows))
        sharing = [thing for thing, info in story.OBJECTS.items() if info.get("picture") == name]
        if name.startswith("door_") or name == "ship":
            assert size == (2 * main.TILE, main.TILE), name
        elif name == "decor_crab_pedestal":  # the statue without its crab: drawn in its place
            assert size == main.thing_rect("deck_statue").size, name
        elif sharing:  # a shared picture is as big as every piece that uses it
            for thing in sharing:
                assert size == main.thing_rect(thing).size, (name, thing)
        elif name in story.OBJECTS:
            assert size == main.thing_rect(name).size, name  # the big characters fill all their tiles
        else:
            assert size == (main.TILE, main.TILE), name


def test_everything_on_screen_has_a_picture():
    """No rectangles left: rooms, items, puzzles, characters, doors and the player all have sprites."""
    for room in story.ROOMS:
        assert sprites.image("floor_" + room) is not None, room
        assert sprites.image("wall_" + room) is not None or sprites.image("wall_" + room + "_0") is not None, room
    for item in story.ITEMS:
        assert sprites.image(item) is not None, item
    statuses = {"puzzle": ["solved", "unsolved"], "character": ["present"], "switch": ["on", "off"],
                "altar": ["present"], "anvil": ["present"], "barrier": ["up"], "tile": ["lit", "dark", "error"], "decor": ["present"],
                "cauldron": ["present"], "portal": ["present"]}
    for thing, info in story.OBJECTS.items():
        for status in statuses[info["kind"]]:
            if info["kind"] == "barrier":
                assert sprites.image("barrier_0") is not None and sprites.image("barrier_1") is not None
            elif info["kind"] == "tile":
                assert sprites.image("tile_" + status) is not None, status  # main.py writes the number on it
            else:
                picture = main.thing_picture({"id": thing, "kind": info["kind"], "status": status})
                assert picture is not None, (thing, status)
    assert sprites.image("zone") is not None
    for status in ("open", "barred", "locked", "sealed"):
        assert sprites.image("door_" + status) is not None, status
    for direction in ("down", "up", "right"):
        for step in range(3):
            assert sprites.image(f"player_{direction}_{step}") is not None, (direction, step)
    assert sprites.image("ship") is not None


def test_door_pictures_turn_to_fit_their_wall():
    for door, info in story.DOORS.items():
        picture = sprites.image("door_locked", turns=main.DOOR_TURNS[info["side"]])
        assert picture.get_size() == main.door_rect(door).size, door


def test_a_missing_picture_gives_none():
    assert sprites.image("no_such_picture") is None


def test_flipped_pictures_are_mirrored_pixel_by_pixel():
    picture = sprites.image("player_right_1")
    mirrored = sprites.image("player_right_1", flip=True)
    width, height = picture.get_size()
    for x in range(width):
        for y in range(height):
            assert mirrored.get_at((x, y)) == picture.get_at((width - 1 - x, y)), (x, y)


def test_turned_pictures_are_rotated_pixel_by_pixel():
    """A quarter turn counterclockwise: the top row becomes the left column, read from the bottom up."""
    picture = sprites.image("door_locked")
    turned = sprites.image("door_locked", turns=1)
    width, height = picture.get_size()
    assert turned.get_size() == (height, width)
    for x in range(height):
        for y in range(width):
            assert turned.get_at((x, y)) == picture.get_at((width - 1 - y, x)), (x, y)


def test_a_thing_without_a_picture_is_drawn_as_a_rectangle(app, monkeypatch):
    """If a sprite is missing, the game still runs: the thing gets its colored rectangle."""
    without_crab = dict(sprites.SPRITES)
    del without_crab["crab"]
    monkeypatch.setattr(sprites, "SPRITES", without_crab)
    app["state"] = play(CRAB_ENDING[:-1])  # in the crab's room
    app["fade"] = 0  # fully lit
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    main.draw(app, screen)
    assert tuple(screen.get_at(main.thing_rect("crab").center))[:3] == main.THING_COLORS["crab"]


# --- The pixel font --------------------------------------------------------------------


def game_texts():
    """Every text the game can show, plus what main.py adds around them."""
    texts = list(story.MESSAGES.values()) + list(story.CLUES.values())
    for room in story.ROOMS.values():
        texts += [room["name"], room["description"]]
    for item in story.ITEMS.values():
        texts += [item["name"], item["description"], item["pickup_text"] or ""]
    for door in story.DOORS.values():
        texts += [door["locked_text"] or "", door["sealed_text"] or "", door["open_text"] or ""]
    for thing in story.OBJECTS.values():
        texts += [thing["name"], thing["look_text"], thing["done_text"] or "", thing.get("fuse_text", "")]
        for reaction in thing["reactions"].values():
            texts.append(reaction["text"])
    for ending in story.ENDINGS.values():
        texts += [ending["title"]] + ending["text"]
    texts.append("> < 0123456789")  # the marks around the chosen menu entry, the ending number
    return texts


def test_the_font_can_write_every_text_of_the_game():
    missing = set()
    for text in game_texts():
        for char in text:
            if char not in pixel_font.GLYPHS and char not in "{}":  # braces only mark where values go
                missing.add(char)
    assert missing == set()


def test_every_character_is_a_proper_picture():
    for char, rows in pixel_font.GLYPHS.items():
        assert len(rows) == pixel_font.HEIGHT, char
        assert len({len(row) for row in rows}) == 1, char
        for row in rows:
            assert set(row) <= {"#", "."}, char


@pytest.mark.parametrize("scale", [1, 2, 3])
def test_the_font_draws_exactly_what_it_measures(scale):
    font = pixel_font.PixelFont(scale)
    for text in ["Ponte", "È chiusa a chiave.", "«Il granchio non mente mai.»", "ij", "E: Raccogli"]:
        assert font.render(text, False, (255, 255, 255)).get_size() == font.size(text), text
    assert font.size("") == (0, pixel_font.HEIGHT * scale)
    assert font.get_linesize() == (pixel_font.HEIGHT + pixel_font.LINE_GAP) * scale
    assert font.size("ii")[0] == (1 + pixel_font.SPACING + 1) * scale


def test_an_unknown_character_is_drawn_as_a_box():
    font = pixel_font.PixelFont(1)
    assert font.size("€") == (len(pixel_font.MISSING[0]), pixel_font.HEIGHT)


# --- Animations ------------------------------------------------------------------------


def test_the_player_walks_in_two_steps_and_stands_still(app):
    main.update(app, 1, 0)
    assert p1(app)["moving"]
    steps = set()
    for _ in range(4 * main.WALK_STEP_FRAMES):
        main.update(app, 1, 0)
        steps.add(main.player_picture(app, p1(app)))
    assert steps == {sprites.image("player_right_1"), sprites.image("player_right_2")}
    main.update(app, 0, 0)
    assert not p1(app)["moving"]
    assert main.player_picture(app, p1(app)) is sprites.image("player_right_0")


def test_facing_left_mirrors_the_right_pictures(app):
    main.update(app, -1, 0)
    main.update(app, 0, 0)
    assert main.player_picture(app, p1(app)) is sprites.image("player_right_0", flip=True)


def test_a_room_comes_out_of_the_dark_after_a_door(app):
    for _ in range(main.FADE_FRAMES):
        main.update(app, 0, 0)
    assert app["fade"] == 0
    p1(app)["pos"] = main.spawn_in_front_of("deck_to_cabin")
    p1(app)["touching"] = None
    while app["state"]["room"] == "deck":
        main.update(app, 0, -1)
    assert app["fade"] == main.FADE_FRAMES
    for _ in range(main.FADE_FRAMES):
        main.update(app, 0, 0)
    assert app["fade"] == 0


@pytest.mark.parametrize("ending_path", [CRAB_ENDING, ANGEL_ENDING])
def test_the_endings_play_their_animation(app, ending_path):
    """Every frame of the first five seconds of each ending can be drawn, and the story on screen moves on.

    The pictures compared are two seconds apart, when the waves and the ship's
    swaying are back where they started: only the ending's own animation differs.
    """
    app["state"] = play(ending_path)
    main.set_scene(app, "ending")
    app["frame"] = 0
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    pictures = {}
    for frame in range(5 * main.FPS):
        main.draw(app, screen)
        if frame in (0, 2 * main.FPS):
            pictures[frame] = pygame.image.tobytes(screen, "RGB")
        main.update(app, 0, 0)
    assert pictures[0] != pictures[2 * main.FPS]


