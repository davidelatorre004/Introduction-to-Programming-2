"""Tests for main.py: the room layout, walking through doors, the menus and saving, without a window.

They drive the interface the way the main loop does: handle_key() for a key
press, update() once per frame with the direction held. conftest.py keeps the
save file in a temporary folder.
"""

import collections
import socket
import time

import pygame
import pytest

import claw
import effects
import engine
import main
import net
import save
import sounds
import sprites
import story

OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}



def p1(app):
    """The first (and for now only) player of the interface."""
    return app["players"][0]


def act(verb, target, item=None):
    return {"verb": verb, "target": target, "item": item}


# The crab's path, from a new game to its ending, in stages.
IN_THE_CABIN = [act("pick_up", "wand"), act("enter", "deck_to_cabin")]  # with the wand, the barrier up
CIRCUIT_COMPLETE = IN_THE_CABIN + [act("activate", "generator_a"), act("activate", "generator_c")]
FIRST_HALF = CIRCUIT_COMPLETE + [act("pick_up", "key"), act("enter", "cabin_to_deck")]  # back on the deck
IN_THE_HOLD = FIRST_HALF + [act("enter", "deck_to_hold")]
TILE_SEQUENCE = ["tile_1", "tile_2", "tile_3", "tile_4", "tile_5", "tile_3", "tile_1", "tile_5", "tile_2", "tile_4", "tile_3"]
TILES_SOLVED = IN_THE_HOLD + [act("step_on", tile) for tile in TILE_SEQUENCE]
BOTH_HALVES = TILES_SOLVED + [act("pick_up", "second_key")]  # in the hold, not fused yet
# The tinctures: the green one in the infirmary, then the three it scatters, and back in the infirmary.
TINCTURES_FOUND = BOTH_HALVES + [
    act("enter", "hold_to_infirmary"), act("pick_up", "green_tincture"),
    act("enter", "infirmary_to_corridor"), act("pick_up", "blue_tincture"), act("enter", "corridor_to_infirmary"),
    act("enter", "infirmary_to_hold"), act("enter", "hold_to_deck"), act("enter", "deck_to_cabin"),
    act("enter", "cabin_to_galley"), act("pick_up", "red_tincture"), act("enter", "galley_to_cabin"),
    act("enter", "cabin_to_helm"), act("pick_up", "gold_tincture"), act("enter", "helm_to_cabin"),
    act("enter", "cabin_to_deck"), act("enter", "deck_to_hold"), act("enter", "hold_to_infirmary")]
DOCTOR_AT_PEACE = (TINCTURES_FOUND
                   + [act("use_item", "cauldron", tincture) for tincture in story.POTION_PUZZLES["remedy"]["recipe"]]
                   + [act("pick_up", "potion"), act("use_item", "doctor", "potion")])  # in the infirmary
KEY_FUSED = DOCTOR_AT_PEACE + [act("enter", "infirmary_to_hold"), act("enter", "hold_to_deck"),
                               act("enter", "deck_to_cabin"), act("enter", "cabin_to_east_room"),
                               act("use_item", "anvil", "second_key"),
                               act("enter", "east_room_to_cabin"), act("enter", "cabin_to_deck")]  # back on the deck
CRAB_DOOR_OPEN = KEY_FUSED + [act("use_item", "deck_to_crab", "fused_key")]
TO_THE_CRAB_ENDING = CRAB_DOOR_OPEN + [act("enter", "deck_to_crab"), act("use_item", "crab", "wand")]
TO_THE_ANGEL_ENDING = KEY_FUSED + [act("use_item", "deck_to_angel", "fused_key"), act("enter", "deck_to_angel"),
                                     act("use_item", "angel", "wand")]


@pytest.fixture
def app():
    """The interface just after launching the game: on the main menu."""
    pygame.font.init()
    return main.new_app(main.load_fonts())


def relaunch():
    """Close the game and launch it again: only the save file is left."""
    return main.new_app(main.load_fonts())


def press(app, *keys):
    for key in keys:
        main.handle_key(app, key)


def read_all(app):
    """Close every page of the text box, like the player pressing E. Fails instead of looping forever."""
    for _ in range(50):
        if not app["dialog"]:
            return
        main.handle_key(app, pygame.K_e)
    assert not app["dialog"], "E does not close the text box"


def dialog_text(app):
    """Everything waiting in the text box, as one string."""
    lines = []
    for page in app["dialog"]:
        lines.extend(page)
    return " ".join(lines)


def start_new_game(app):
    """Choose "New game" on a menu without saves, then "1 player", keep the first character, and read the opening scene."""
    press(app, pygame.K_RETURN, pygame.K_RETURN, pygame.K_RETURN)
    read_all(app)


def stand_next_to(app, thing):
    """Put the player within reach of a thing: on it if it is an item on the floor, else just below it,
    or just above it if there is no room below (the anvil stands against the bottom wall)."""
    rect = main.thing_rect(thing)
    body = pygame.Rect(0, 0, main.PLAYER_SIZE, main.PLAYER_SIZE)
    if thing in story.ITEMS and not main.on_an_altar(app["state"], thing):
        body.center = rect.center
    else:
        body.midtop = (rect.centerx, rect.bottom + 2)
        if body.collidelist(main.solid_rects(app["state"])) != -1:
            body.midbottom = (rect.centerx, rect.top - 2)
    p1(app)["pos"] = (body.x, body.y)
    p1(app)["touching"] = None


def walk_until(app, arrived, direction, limit=300):
    """Hold the direction that direction(x, y) gives, frame by frame, until arrived(x, y) is true.

    (x, y) is the middle of the player's body. Fails instead of walking forever.
    """
    for _ in range(limit):
        x, y = main.player_rect(p1(app)["pos"]).center
        if arrived(x, y):
            return
        main.update(app, *direction(x, y))
    raise AssertionError(f"the player never arrived; now at {p1(app)['pos']}")


def walk_onto(app, tile):
    """Walk onto a numbered tile the way a player does, with the arrow keys only.

    First up or down into the lane of the zone just above the row of tiles, then
    along it, then down onto the tile: the movement triggers fire as in the game.
    """
    target = main.thing_rect(tile)
    lane = target.top - main.TILE // 2
    walk_until(app, lambda x, y: abs(y - lane) <= 1, lambda x, y: (0, 1 if lane > y else -1))
    walk_until(app, lambda x, y: abs(x - target.centerx) <= 1, lambda x, y: (1 if target.centerx > x else -1, 0))
    walk_until(app, lambda x, y: target.collidepoint(x, y), lambda x, y: (0, 1))


def choose_in_menu(app, verb, item=None):
    """In the menu opened by E, go down to the action with this verb and item, and choose it."""
    for index, action in enumerate(app["actions"]):
        if action["verb"] == verb and action["item"] == item:
            press(app, *([pygame.K_DOWN] * index), pygame.K_RETURN)
            return
    raise AssertionError(f"no {verb} {item} among {app['actions']}")


def walk_into(app, door, frames=30):
    """Put the player just in front of a door of the current room and walk into it."""
    p1(app)["pos"] = main.spawn_in_front_of(door)
    p1(app)["touching"] = None
    room = app["state"]["room"]
    dx, dy = main.TOWARD[story.DOORS[door]["side"]]
    for _ in range(frames):
        main.update(app, dx, dy)
        if app["state"]["room"] != room or app["dialog"]:
            return


def in_room(room):
    """A new game, moved to a room (to look at rooms the player cannot reach yet)."""
    state = engine.new_game()
    state["room"] = room
    return state


def play(actions):
    """Play a list of actions on a new game with the engine alone."""
    state = engine.new_game()
    for action in actions:
        state, outcome = engine.perform(state, action)
        assert outcome["ok"], (action, outcome)
    return state


def playing(app, actions):
    """Put the interface in the middle of a game: the actions played, the player at the entry of the room."""
    app["state"] = play(actions)
    main.set_scene(app, "play")
    main.place_at_entry(app)
    app["dialog"] = []


# --- The layout in story.py -------------------------------------------------------


def on_the_floor(tile, room):
    col, row = tile
    columns, rows = main.room_size(room)
    return 1 <= col <= columns - 2 and 1 <= row <= rows - 2


def test_layout_everything_stands_on_the_floor():
    for room_id, room in story.ROOMS.items():
        assert on_the_floor(room["entry"], room_id), room_id
    for thing_id, info in list(story.ITEMS.items()) + list(story.OBJECTS.items()):
        if info["room"] is None:
            continue  # made at the anvil: it never lies anywhere
        assert on_the_floor(info["pos"], info["room"]), thing_id
        width, height = info.get("size", (1, 1))
        last_tile = (info["pos"][0] + width - 1, info["pos"][1] + height - 1)
        assert on_the_floor(last_tile, info["room"]), thing_id


def test_layout_nothing_shares_a_tile():
    """Each thing has its own tiles, all of them for the big ones, except an item lying on an altar or the anvil.

    The barriers are left out: they wrap around what they guard.
    """
    for room in story.ROOMS:
        areas = [main.tile_rect(*story.ROOMS[room]["entry"])]
        for thing, info in story.OBJECTS.items():
            if info["room"] == room and info["kind"] != "barrier":
                areas.append(main.thing_rect(thing))
        for item, info in story.ITEMS.items():
            if info["room"] == room and not main.on_an_altar(in_room(room), item):
                areas.append(main.thing_rect(item))
        for index, area in enumerate(areas):
            assert area.collidelist(areas[index + 1:]) == -1, (room, area)


@pytest.mark.parametrize("room, item", [("cabin", "key"), ("hold", "second_key")])
def test_layout_the_barrier_keeps_the_key_out_of_reach(room, item):
    """While the barrier stands, there is no spot in the room from where E could reach the half of the key."""
    state = in_room(room)
    solids = main.solid_rects(state)
    guarded = main.reach_rect(item)
    columns, rows = main.room_size(room)
    for x in range(main.TILE, (columns - 1) * main.TILE, 2):
        for y in range(main.HUD_HEIGHT + main.TILE, main.HUD_HEIGHT + (rows - 1) * main.TILE, 2):
            body = main.player_rect((x, y))
            if body.collidelist(solids) == -1:
                assert not body.inflate(2 * main.REACH, 2 * main.REACH).colliderect(guarded), (x, y)


def puzzle_tiles(puzzle):
    return sorted({tile for phase in story.FLOOR_PUZZLES[puzzle]["phases"] for tile in phase["steps"]})


def test_layout_each_zone_holds_its_tiles_and_nothing_else():
    """A zone lies on the floor, around every tile of its puzzle, and nothing else stands in it."""
    floor = main.tile_rect(1, 1, main.COLUMNS - 2, main.ROWS - 2)
    for puzzle_id, puzzle in story.FLOOR_PUZZLES.items():
        zone = main.zone_rect(puzzle_id)
        assert floor.contains(zone), puzzle_id
        tiles = puzzle_tiles(puzzle_id)
        for tile in tiles:
            assert zone.contains(main.thing_rect(tile)), tile
        for thing_id, info in list(story.ITEMS.items()) + list(story.OBJECTS.items()):
            if info["room"] == puzzle["room"] and thing_id not in tiles:
                assert not zone.colliderect(main.thing_rect(thing_id)), thing_id


def test_layout_any_tile_leads_to_any_other_without_crossing_a_third():
    """The lanes of the zone let the player skip tiles, as the sequences need: 5 then 3, or 1 then 5.

    The middle of the player's body moves in small steps from the middle of one tile
    to the middle of another, never over a third tile and never out of the zone.
    """
    for puzzle_id, puzzle in story.FLOOR_PUZZLES.items():
        solids = main.solid_rects(in_room(puzzle["room"]))
        zone = main.zone_rect(puzzle_id)
        tiles = puzzle_tiles(puzzle_id)
        for start in tiles:
            for goal in tiles:
                if start == goal:
                    continue
                others = [main.thing_rect(tile) for tile in tiles if tile not in (start, goal)]

                def allowed(point):
                    body = pygame.Rect(0, 0, main.PLAYER_SIZE, main.PLAYER_SIZE)
                    body.center = point
                    return (zone.collidepoint(point) and body.collidelist(solids) == -1
                            and not any(rect.collidepoint(point) for rect in others))

                end = main.thing_rect(goal).center
                seen = {main.thing_rect(start).center}
                frontier = list(seen)
                while frontier and end not in seen:
                    further = []
                    for x, y in frontier:
                        for dx, dy in ((4, 0), (-4, 0), (0, 4), (0, -4)):
                            point = (x + dx, y + dy)
                            if point not in seen and allowed(point):
                                seen.add(point)
                                further.append(point)
                    frontier = further
                assert end in seen, (start, goal)


def test_layout_doors_on_the_same_wall_keep_apart():
    """A wall can have more than one door ("at"), but their openings and the floor in front never overlap."""
    for room in story.ROOMS:
        doors = main.doors_in(room)
        for index, door in enumerate(doors):
            for other in doors[index + 1:]:
                assert not approach(door).inflate(2, 2).colliderect(approach(other)), (room, door, other)


def test_layout_the_way_back_is_on_the_opposite_wall():
    for door_id, door in story.DOORS.items():
        back = main.return_door(door["to"], door["room"])
        assert back is not None, door_id
        assert story.DOORS[back]["side"] == OPPOSITE[door["side"]], door_id


def approach(door):
    """The strip of floor, two tiles deep, in front of a door: where the player arrives and walks in."""
    opening = main.door_rect(door)
    depth = 2 * main.TILE
    side = story.DOORS[door]["side"]
    if side == "N":
        return pygame.Rect(opening.left, opening.bottom, opening.width, depth)
    if side == "S":
        return pygame.Rect(opening.left, opening.top - depth, opening.width, depth)
    if side == "W":
        return pygame.Rect(opening.right, opening.top, depth, opening.height)
    return pygame.Rect(opening.left - depth, opening.top, depth, opening.height)


def test_layout_nothing_stands_in_front_of_a_door():
    for door_id, door in story.DOORS.items():
        for thing_id, info in list(story.ITEMS.items()) + list(story.OBJECTS.items()):
            if info["room"] == door["room"]:
                assert not approach(door_id).colliderect(main.thing_rect(thing_id)), (door_id, thing_id)


def test_layout_every_door_and_thing_can_be_reached():
    """From the entry of each room the player can walk to every door and get within reach of every thing.

    A search over the floor in small steps, like the player's own: what new decor
    adds must never wall off a door or a puzzle. What a barrier guards is left out.
    """
    for room in story.ROOMS:
        state = in_room(room)
        solids = main.solid_rects(state)
        barriers = [main.thing_rect(thing) for thing, info in story.OBJECTS.items()
                    if info["room"] == room and info["kind"] == "barrier"]
        inside = main.tile_rect(0, 0, *main.room_size(room))  # open doors lead out: stop at the room's edge
        start = main.spawn_at_entry(room)
        seen = {start}
        frontier = [start]
        while frontier:
            further = []
            for x, y in frontier:
                for dx, dy in ((4, 0), (-4, 0), (0, 4), (0, -4)):
                    point = (x + dx, y + dy)
                    body = main.player_rect(point)
                    if point not in seen and inside.contains(body) and body.collidelist(solids) == -1:
                        seen.add(point)
                        further.append(point)
            frontier = further
        bodies = [main.player_rect(point) for point in seen]
        for door in main.doors_in(room):
            assert any(body.colliderect(approach(door)) for body in bodies), (room, door)
        for thing, info in list(story.OBJECTS.items()) + list(story.ITEMS.items()):
            if info["room"] != room or info.get("kind") == "barrier":
                continue
            rect = main.thing_rect(thing)
            if any(barrier.contains(rect) for barrier in barriers):
                continue  # behind a barrier until a puzzle is solved
            assert any(body.inflate(2 * main.REACH, 2 * main.REACH).colliderect(rect) for body in bodies), (room, thing)


def test_flat_decor_can_be_walked_over_and_solid_decor_cannot():
    for thing, info in story.OBJECTS.items():
        if info["kind"] != "decor":
            continue
        solids = main.solid_rects(in_room(info["room"]))
        blocked = main.thing_rect(thing).collidelist(solids) != -1
        assert blocked == info["solid"], thing


# --- Room geometry ------------------------------------------------------------------


def test_doors_are_in_the_middle_of_their_wall_unless_told_otherwise():
    for door_id, door in story.DOORS.items():
        rect = main.door_rect(door_id)
        columns, rows = main.room_size(door["room"])
        if "at" in door:
            along = rect.left if door["side"] in ("N", "S") else rect.top - main.HUD_HEIGHT
            assert along == door["at"] * main.TILE, door_id
        elif door["side"] in ("N", "S"):
            assert rect.centerx == columns * main.TILE // 2, door_id
        else:
            assert rect.centery == main.HUD_HEIGHT + rows * main.TILE // 2, door_id


def test_walls_close_the_room_except_at_the_doors():
    """Every tile of the border is wall or door, and no wall covers a door."""
    for room in story.ROOMS:
        walls = main.wall_rects(room)
        openings = [main.door_rect(door) for door in main.doors_in(room)]
        for opening in openings:
            assert opening.collidelist(walls) == -1, room
        columns, rows = main.room_size(room)
        for col in range(columns):
            for row in range(rows):
                if col in (0, columns - 1) or row in (0, rows - 1):
                    center = main.tile_rect(col, row).center
                    assert pygame.Rect(center, (1, 1)).collidelist(walls + openings) != -1, (room, col, row)


def test_players_appear_on_free_floor():
    """At the entry of a room and in front of each door, the player touches nothing."""
    for room in story.ROOMS:
        solids = main.solid_rects(in_room(room))
        spawns = [main.spawn_at_entry(room)]
        for door in main.doors_in(room):
            spawns.append(main.spawn_in_front_of(door))
        for spawn in spawns:
            assert main.player_rect(spawn).collidelist(solids) == -1, room
            assert main.door_touched(room, spawn, 0, 0) is None, room
            assert main.zones_around(in_room(room), spawn) == set(), room  # arriving is not walking on tiles


def test_player_never_walks_through_walls_or_closed_doors(app):
    """Walking in every direction for five seconds: the player never overlaps anything solid."""
    start_new_game(app)
    room_area = main.tile_rect(0, 0, *main.room_size("deck"))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            app["state"] = engine.new_game()
            p1(app)["pos"] = main.spawn_at_entry("deck")
            p1(app)["touching"] = None
            for _ in range(300):
                main.update(app, dx, dy)
                read_all(app)
                rect = main.player_rect(p1(app)["pos"])
                assert rect.collidelist(main.solid_rects(app["state"])) == -1
                assert room_area.contains(rect)


# --- Doors ------------------------------------------------------------------------


def test_walking_between_deck_cabin_and_hold(app):
    """The player goes around the deck, the cabin and the hold; every move is saved."""
    start_new_game(app)
    trips = [("deck_to_cabin", "cabin"), ("cabin_to_deck", "deck")]
    for _ in range(2):
        for door, room in trips:
            came_from = app["state"]["room"]
            walk_into(app, door)
            assert app["state"]["room"] == room
            assert p1(app)["pos"] == main.spawn_in_front_of(main.return_door(room, came_from))
            assert app["banner"] == story.ROOMS[room]["name"]
            assert engine.restore_state(save.load_game()) == app["state"]
        playing(app, FIRST_HALF)  # the second time round, with the first half of the key: the hold opens
        trips = [("deck_to_hold", "hold"), ("hold_to_deck", "deck")]


def test_the_barred_hold_explains_itself_until_the_first_half(app):
    """R1 on screen: the gate of the hold says what bars it; nothing is saved; with the first half it opens."""
    start_new_game(app)
    saved = save.load_game()
    walk_into(app, "deck_to_hold")
    assert app["state"]["room"] == "deck"
    assert dialog_text(app) == story.DOORS["deck_to_hold"]["barred_text"]
    assert save.load_game() == saved
    playing(app, FIRST_HALF)
    walk_into(app, "deck_to_hold")
    assert app["state"]["room"] == "hold"


def test_locked_door_explains_and_keeps_the_player_on_the_deck(app):
    """A1 on screen: the crab's door says it is locked; the player stays on the deck and nothing is saved."""
    start_new_game(app)
    saved = save.load_game()
    walk_into(app, "deck_to_crab")
    assert app["state"]["room"] == "deck"
    assert dialog_text(app) == story.DOORS["deck_to_crab"]["locked_text"]
    assert save.load_game() == saved


def test_walking_along_a_wall_past_a_door_does_not_go_through(app):
    """Only walking into a door counts: sliding along the wall in front of it does not."""
    start_new_game(app)
    p1(app)["pos"] = (main.tile_rect(1, 1).x, main.tile_rect(1, 1).y)  # top-left corner, against the top wall
    for _ in range(150):
        main.update(app, 1, 0)  # walk right, past the cabin door
    assert app["state"]["room"] == "deck"
    assert main.player_rect(p1(app)["pos"]).left > main.door_rect("deck_to_cabin").right


def test_a_locked_door_speaks_once_per_push(app):
    start_new_game(app)
    walk_into(app, "deck_to_crab")
    read_all(app)
    for _ in range(30):
        main.update(app, 1, 0)  # still pushing: no new message
    assert app["dialog"] == []
    main.update(app, 0, 0)  # let go...
    main.update(app, 1, 0)  # ...and push again
    assert app["dialog"] != []


def test_player_cannot_move_while_reading(app):
    press(app, pygame.K_RETURN, pygame.K_RETURN, pygame.K_RETURN)  # the opening scene is on screen
    before = p1(app)["pos"]
    for _ in range(30):
        main.update(app, 1, 0)
    assert p1(app)["pos"] == before
    read_all(app)
    for _ in range(30):
        main.update(app, 1, 0)
    assert p1(app)["pos"] != before


# --- Menus and saving (PT01, PT05, A6) -------------------------------------------------


def test_menu_offers_resume_only_when_a_game_is_saved(app):
    assert main.menu_entries(app) == ["new_game", "join_game", "quit"]
    start_new_game(app)
    assert main.menu_entries(relaunch()) == ["new_game", "resume", "join_game", "quit"]


def test_new_game_shows_the_opening_scene_and_saves_at_once(app):
    press(app, pygame.K_RETURN)
    assert app["scene"] == "mode"  # first the choice of the mode
    press(app, pygame.K_RETURN)  # "1 player"
    assert app["scene"] == "character"  # then of the character
    press(app, pygame.K_RETURN)
    assert app["scene"] == "play"
    assert dialog_text(app) == story.MESSAGES["intro"]
    assert p1(app)["pos"] == main.spawn_at_entry(story.START_ROOM)
    assert engine.restore_state(save.load_game()) == engine.new_game()


def test_resume_starts_at_the_entry_of_the_saved_room(app):
    """Close the game in the cabin and launch it again: "Riprendi" goes back to the cabin's entry."""
    start_new_game(app)
    walk_into(app, "deck_to_cabin")
    for _ in range(40):
        main.update(app, 1, -1)  # away from the door, which is in the bottom wall
    again = relaunch()
    press(again, pygame.K_DOWN, pygame.K_RETURN)  # "Riprendi"
    assert again["scene"] == "play"
    assert again["state"]["room"] == "cabin"
    assert p1(again)["pos"] == main.spawn_at_entry("cabin")


def test_new_game_over_a_save_asks_first(app):
    """A6 on screen: "No" keeps the save as it is; "Sì" replaces it with a new game."""
    start_new_game(app)
    walk_into(app, "deck_to_cabin")
    again = relaunch()
    saved = save.load_game()
    press(again, pygame.K_RETURN)  # "New game"
    assert again["scene"] == "confirm"
    assert main.menu_entries(again)[again["menu_index"]] == "no"  # the safe answer is highlighted
    press(again, pygame.K_RETURN)  # "No"
    assert again["scene"] == "menu"
    assert save.load_game() == saved
    press(again, pygame.K_RETURN, pygame.K_UP, pygame.K_RETURN, pygame.K_RETURN)  # "New game", "Yes", "1 player"
    assert again["scene"] == "character"
    assert save.load_game() == saved  # nothing replaced until the character is chosen
    press(again, pygame.K_RETURN)
    assert again["scene"] == "play"
    assert engine.restore_state(save.load_game()) == engine.new_game()


def test_pause_menu(app):
    start_new_game(app)
    press(app, pygame.K_ESCAPE)
    assert app["scene"] == "pause"
    press(app, pygame.K_ESCAPE)
    assert app["scene"] == "play"
    press(app, pygame.K_ESCAPE, pygame.K_DOWN, pygame.K_RETURN)  # "Ricomincia" asks first
    assert app["scene"] == "confirm"
    press(app, pygame.K_ESCAPE)  # Esc means no
    assert app["scene"] == "pause"
    press(app, pygame.K_DOWN, pygame.K_DOWN, pygame.K_RETURN)  # "Menu principale"
    assert app["scene"] == "menu"
    assert "resume" in main.menu_entries(app)


def test_finished_game_resumes_on_its_ending(app):
    """PT05: the outcome can be reviewed after relaunching; starting over still asks first."""
    save.save_game(play(TO_THE_CRAB_ENDING))
    again = relaunch()
    press(again, pygame.K_DOWN, pygame.K_RETURN)  # "Riprendi"
    assert again["scene"] == "ending"
    press(again, pygame.K_RETURN)  # "New game"
    assert again["scene"] == "confirm"


def test_a_failed_save_is_reported_not_fatal(app, monkeypatch):
    def full_disk(state, path=None):
        raise OSError("No space left on device")
    monkeypatch.setattr(save, "save_game", full_disk)
    press(app, pygame.K_RETURN, pygame.K_RETURN, pygame.K_RETURN)
    assert app["scene"] == "play"
    assert story.MESSAGES["save_failed"] in dialog_text(app)


# --- Acting with E, the inventory and the endings (M4) -----------------------------------


def test_prompt_says_what_e_does_here():
    """PT02: the bar at the top shows the action E would do, or the name of the thing if there are several."""
    def hint(action):
        return story.MESSAGES["prompt"].format(action=action)

    state = engine.new_game()
    assert main.prompt(state, main.spawn_at_entry("deck")) == ""  # nothing near: no hint, E does nothing
    wand = main.thing_rect("wand")
    on_the_wand = (wand.centerx - main.PLAYER_SIZE // 2, wand.centery - main.PLAYER_SIZE // 2)
    pick_up_label = story.MESSAGES["label_pick_up"].format(item=story.ITEMS["wand"]["name"])
    assert main.prompt(state, on_the_wand) == hint(pick_up_label)
    with_wand_in_cabin = play(IN_THE_CABIN)
    generator = main.thing_rect("generator_a")
    below_generator = (generator.centerx - main.PLAYER_SIZE // 2, generator.bottom + 2)
    activate_label = story.MESSAGES["label_activate"].format(name=story.OBJECTS["generator_a"]["name"])
    assert main.prompt(with_wand_in_cabin, below_generator) == hint(activate_label)
    barrier = main.thing_rect("barrier")
    below_barrier = (barrier.centerx - main.PLAYER_SIZE // 2, barrier.bottom + 2)
    assert main.prompt(with_wand_in_cabin, below_barrier) == hint(story.OBJECTS["barrier"]["name"])


def test_the_nearest_thing_is_the_one_e_acts_on(app):
    """In the corner between generator C and the barrier both are in reach: E picks the closer generator.

    On the very same tile, the key lying on the altar comes before the altar itself.
    """
    state = play(IN_THE_CABIN)  # with the wand, the barrier still up
    generator, barrier = main.thing_rect("generator_c"), main.thing_rect("barrier")
    body = pygame.Rect(0, 0, main.PLAYER_SIZE, main.PLAYER_SIZE)
    body.bottomright = (generator.left - 2, generator.top - 2)
    reach = body.inflate(2 * main.REACH, 2 * main.REACH)
    assert reach.colliderect(generator) and reach.colliderect(barrier)
    assert main.nearest_target(state, body.topleft) == "generator_c"
    solved = play(CIRCUIT_COMPLETE)  # the key free on the altar
    app["state"] = solved
    stand_next_to(app, "key")
    assert main.nearest_target(solved, p1(app)["pos"]) == "key"


def test_e_with_nothing_near_does_nothing(app):
    """Far from everything, E does nothing at all: no text box, nothing saved, the player keeps walking."""
    start_new_game(app)
    saved = save.load_game()
    press(app, pygame.K_e)
    assert app["scene"] == "play" and app["dialog"] == []
    assert save.load_game() == saved


def test_e_ignores_furniture_and_reaches_what_matters_behind_it(app):
    """Next to a barrel, E does nothing: no barrel ever comes before something that matters. A note is still read."""
    start_new_game(app)
    stand_next_to(app, "deck_barrel_1")
    assert main.nearest_target(app["state"], p1(app)["pos"]) is None
    press(app, pygame.K_e)
    assert app["dialog"] == []
    app["state"]["room"] = "infirmary"
    stand_next_to(app, "infirmary_notes")
    assert main.nearest_target(app["state"], p1(app)["pos"]) == "infirmary_notes"  # a note is still read
    press(app, pygame.K_e)
    assert dialog_text(app) == story.OBJECTS["infirmary_notes"]["look_text"]


def test_e_picks_up_an_item_at_once_and_saves(app):
    start_new_game(app)
    stand_next_to(app, "wand")
    press(app, pygame.K_e)
    assert app["scene"] == "play"
    assert dialog_text(app) == story.ITEMS["wand"]["pickup_text"]
    assert engine.restore_state(save.load_game())["inventory"] == ["wand"]
    read_all(app)
    assert [thing["id"] for thing in engine.things_here(app["state"])].count("wand") == 0


def test_e_menu_offers_every_action_and_esc_closes_it(app):
    start_new_game(app)
    stand_next_to(app, "wand")
    press(app, pygame.K_e)
    read_all(app)
    walk_into(app, "deck_to_cabin")
    stand_next_to(app, "barrier")
    press(app, pygame.K_e)
    assert app["scene"] == "actions"
    use_wand = story.MESSAGES["label_use"].format(item=story.ITEMS["wand"]["name"])
    assert main.menu_labels(app) == [story.MESSAGES["label_examine"], use_wand]
    press(app, pygame.K_ESCAPE)
    assert app["scene"] == "play"
    assert app["dialog"] == []


def test_a_choice_that_cannot_be_undone_asks_first(app):
    """Giving the wand asks for confirmation; "No" changes nothing, not even the save."""
    app["state"] = play(CRAB_DOOR_OPEN + [act("enter", "deck_to_crab")])
    main.set_scene(app, "play")
    save.save_game(app["state"])
    saved = save.load_game()
    stand_next_to(app, "crab")
    press(app, pygame.K_e)
    choose_in_menu(app, "use_item", "wand")
    assert app["scene"] == "confirm"
    assert main.menu_entries(app)[app["menu_index"]] == "no"
    press(app, pygame.K_RETURN)  # "No"
    assert app["scene"] == "play"
    assert not engine.is_over(app["state"])
    assert save.load_game() == saved


def test_the_fused_key_opens_both_doors_on_screen(app):
    """No confirmation and no sealing: the fused key opens the crab's door, then the angel's, and both lead in."""
    app["state"] = play(KEY_FUSED)
    main.set_scene(app, "play")
    for door, room in (("deck_to_crab", "crab_room"), ("deck_to_angel", "angel_room")):
        p1(app)["pos"] = main.spawn_in_front_of(door)
        press(app, pygame.K_e)
        choose_in_menu(app, "use_item", "fused_key")
        assert app["scene"] == "play"  # no question: nothing is lost
        assert dialog_text(app) == story.DOORS[door]["open_text"]
        read_all(app)
        walk_into(app, door)
        assert app["state"]["room"] == room
        walk_into(app, main.return_door(room, "deck"))
    assert engine.has_item(app["state"], "fused_key")


def test_a_half_on_the_door_says_to_fuse_it(app):
    """PT04 on screen: the halves, even both, do not open the door, and the text says where to fuse them."""
    playing(app, BOTH_HALVES + [act("enter", "hold_to_deck")])
    p1(app)["pos"] = main.spawn_in_front_of("deck_to_crab")
    press(app, pygame.K_e)
    choose_in_menu(app, "use_item", "second_key")
    assert dialog_text(app) == story.MESSAGES["not_fused"]
    assert engine.door_status(app["state"], "deck_to_crab") == "locked"


def test_inventory_shows_items_and_clues(app):
    """PT03: I opens the inventory with the items and their descriptions, and the clues found."""
    start_new_game(app)
    press(app, pygame.K_i)
    assert app["scene"] == "inventory"
    assert main.inventory_lines(app["state"]) == [("text", story.MESSAGES["inventory_empty"])]
    press(app, pygame.K_i)
    assert app["scene"] == "play"
    found_clue = play(IN_THE_HOLD + [act("use_item", "hold_puzzle", "wand")])
    assert main.inventory_lines(found_clue) == [
        ("name", story.ITEMS["wand"]["name"]),
        ("text", story.ITEMS["wand"]["description"]),
        ("name", story.ITEMS["key"]["name"]),
        ("text", story.ITEMS["key"]["description"]),
        ("heading", story.MESSAGES["clues"]),
        ("text", story.CLUES["crab_truthful"]),
    ]


@pytest.mark.parametrize("door, character, ending", [
    ("deck_to_crab", "crab", "saved"),
    ("deck_to_angel", "angel", "explosion"),
])
def test_a_whole_game_on_screen(app, door, character, ending):
    """A5 on screen: from the main menu to an ending with the keys of the game, saving all the way."""
    start_new_game(app)
    stand_next_to(app, "wand")
    press(app, pygame.K_e)
    read_all(app)
    walk_into(app, "deck_to_cabin")
    for generator in ("generator_a", "generator_c"):
        stand_next_to(app, generator)
        press(app, pygame.K_e)  # a single action: pull the lever
    assert dialog_text(app) == story.CIRCUITS["cabin_circuit"]["solved_text"]
    read_all(app)
    stand_next_to(app, "key")
    press(app, pygame.K_e)
    read_all(app)
    walk_into(app, "cabin_to_deck")
    walk_into(app, "deck_to_hold")
    for tile in TILE_SEQUENCE:
        walk_onto(app, tile)  # on foot: the movement triggers do the rest
    assert dialog_text(app) == story.FLOOR_PUZZLES["hold_tiles"]["solved_text"]
    read_all(app)
    stand_next_to(app, "second_key")
    press(app, pygame.K_e)
    read_all(app)
    walk_into(app, "hold_to_infirmary")
    # The green tincture in the infirmary, then the three it scatters around the ship.
    route = [("infirmary", "green_tincture", "infirmary_to_corridor"), ("corridor", "blue_tincture", "corridor_to_infirmary")]
    for room, tincture, way_out in route:
        assert app["state"]["room"] == room
        stand_next_to(app, tincture)
        press(app, pygame.K_e)
        read_all(app)
        walk_into(app, way_out)
    for way_out in ("infirmary_to_hold", "hold_to_deck", "deck_to_cabin", "cabin_to_galley"):
        walk_into(app, way_out)
    for tincture, ways_out in (("red_tincture", ("galley_to_cabin", "cabin_to_helm")),
                               ("gold_tincture", ("helm_to_cabin", "cabin_to_deck", "deck_to_hold", "hold_to_infirmary"))):
        stand_next_to(app, tincture)
        press(app, pygame.K_e)
        read_all(app)
        for way_out in ways_out:
            walk_into(app, way_out)
    assert app["state"]["room"] == "infirmary"
    for tincture in story.POTION_PUZZLES["remedy"]["recipe"]:
        stand_next_to(app, "cauldron")
        press(app, pygame.K_e)
        choose_in_menu(app, "use_item", tincture)
        poured = dialog_text(app)  # the text box tells how the mixture changes
        read_all(app)
    assert poured == story.POTION_PUZZLES["remedy"]["solved_text"]
    stand_next_to(app, "potion")
    press(app, pygame.K_e)
    read_all(app)
    stand_next_to(app, "doctor")
    press(app, pygame.K_e)
    choose_in_menu(app, "use_item", "potion")
    read_all(app)
    walk_into(app, "infirmary_to_hold")
    walk_into(app, "hold_to_deck")
    walk_into(app, "deck_to_cabin")
    walk_into(app, "cabin_to_east_room")
    stand_next_to(app, "anvil")
    press(app, pygame.K_e)
    choose_in_menu(app, "use_item", "key")  # either half fuses both
    assert dialog_text(app) == story.OBJECTS["anvil"]["fuse_text"]
    read_all(app)
    walk_into(app, "east_room_to_cabin")
    walk_into(app, "cabin_to_deck")
    p1(app)["pos"] = main.spawn_in_front_of(door)
    press(app, pygame.K_e)
    choose_in_menu(app, "use_item", "fused_key")
    read_all(app)
    walk_into(app, door)
    stand_next_to(app, character)
    press(app, pygame.K_e)
    choose_in_menu(app, "use_item", "wand")
    press(app, pygame.K_UP, pygame.K_RETURN)  # "Sì"
    assert app["scene"] == "play"  # first the text of what happens...
    read_all(app)
    main.update(app, 0, 0)
    assert app["scene"] == "ending"  # ...then the ending
    assert app["state"]["ending"] == ending
    assert engine.restore_state(save.load_game()) == app["state"]


# --- The tiles of the hold: movement triggers (M5) ---------------------------------------


@pytest.fixture
def in_hold(app):
    """The interface in the hold with the first half of the key, at the entry: no tile lit yet."""
    playing(app, IN_THE_HOLD)
    return app


@pytest.fixture
def heard(monkeypatch):
    """The names of the sounds played, in order."""
    played = []
    monkeypatch.setattr(sounds, "play", played.append)
    return played


def lit_tiles(state):
    """The numbers of the lit tiles, in order: "125" is tiles 1, 2 and 5 lit."""
    numbers = ""
    for thing in engine.things_here(state):
        if thing["kind"] == "tile" and thing["status"] == "lit":
            numbers += story.OBJECTS[thing["id"]]["label"]
    return numbers


def test_walking_onto_a_tile_steps_on_it_once(in_hold, heard):
    """The trigger fires when the player arrives on the tile: standing on it, or moving on it, does not repeat it."""
    app = in_hold
    walk_onto(app, "tile_1")
    assert lit_tiles(app["state"]) == "1"
    assert app["banner"] == story.FLOOR_PUZZLES["hold_tiles"]["lit_text"].format(label="1")
    assert heard == ["blip"]
    assert engine.restore_state(save.load_game()) == app["state"]
    for _ in range(30):
        main.update(app, 0, 0)
    for _ in range(4):
        main.update(app, 1, 0)  # six pixels: still on the tile
    assert heard == ["blip"]


def test_stepping_back_onto_the_tile_lit_last_is_silent(in_hold, heard):
    app = in_hold
    walk_onto(app, "tile_1")
    before = app["state"]
    walk_onto(app, "tile_1")  # up into the lane, and back down onto it
    assert heard == ["blip"]
    assert app["state"] == before


def test_each_outcome_of_the_tiles_has_its_sound_and_text(in_hold, heard):
    """A blip for each lit tile, a ding and the next phase's name at the end of a phase, BZZZ for a mistake."""
    app = in_hold
    puzzle = story.FLOOR_PUZZLES["hold_tiles"]
    for tile in TILE_SEQUENCE[:5]:
        walk_onto(app, tile)
    assert heard == ["blip"] * 4 + ["ding"]
    assert app["banner"] == puzzle["phase_text"].format(number=2, name=puzzle["phases"][1]["name"])
    assert lit_tiles(app["state"]) == "5"
    walk_onto(app, "tile_2")  # wrong: the return goes 5, 3, 1
    assert heard[-1] == "buzz"
    assert app["banner"] == puzzle["wrong_text"]
    assert app["flash_frames"] == main.FLASH_FRAMES
    assert lit_tiles(app["state"]) == ""
    assert engine.restore_state(save.load_game()) == app["state"]


def test_walking_out_of_the_zone_starts_the_phase_over(in_hold, heard):
    app = in_hold
    walk_onto(app, "tile_1")
    walk_onto(app, "tile_2")
    zone = main.zone_rect("hold_tiles")
    walk_until(app, lambda x, y: not zone.collidepoint(x, y), lambda x, y: (0, -1))
    assert heard == ["blip", "blip", "buzz"]
    assert app["banner"] == story.FLOOR_PUZZLES["hold_tiles"]["left_text"]
    assert app["state"]["flags"]["hold_step"] == 0
    assert engine.restore_state(save.load_game()) == app["state"]


def test_crossing_the_zone_with_nothing_lit_is_just_walking(in_hold, heard):
    """Down between two tiles and out of the zone: no tile stepped on, nothing to start over, no sound."""
    app = in_hold
    before = app["state"]
    gap = (main.thing_rect("tile_1").right + main.thing_rect("tile_2").left) // 2
    walk_until(app, lambda x, y: abs(x - gap) <= 1, lambda x, y: (1 if gap > x else -1, 0))
    zone = main.zone_rect("hold_tiles")
    walk_until(app, lambda x, y: y > zone.bottom + 2, lambda x, y: (0, 1))
    assert heard == []
    assert app["state"] == before


def test_the_last_tile_opens_the_text_box_with_a_fanfare(app, heard):
    playing(app, TILES_SOLVED[:-1])  # phase 3, one tile to go
    walk_onto(app, TILE_SEQUENCE[-1])
    assert heard == ["fanfare"]
    assert dialog_text(app) == story.FLOOR_PUZZLES["hold_tiles"]["solved_text"]
    assert app["banner_frames"] == 0
    assert engine.restore_state(save.load_game()) == app["state"]
    read_all(app)
    assert "hold_barrier" not in [thing["id"] for thing in engine.things_here(app["state"])]
    assert main.thing_rect("hold_barrier") not in main.solid_rects(app["state"])  # its collision is gone


def test_the_triggers_remember_where_the_player_already_is(in_hold, heard):
    """Appearing on a tile (settle_on_floor) is not stepping on it; arriving on it is."""
    app = in_hold
    body = pygame.Rect(0, 0, main.PLAYER_SIZE, main.PLAYER_SIZE)
    body.center = main.thing_rect("tile_1").center
    p1(app)["pos"] = (body.x, body.y)
    main.settle_on_floor(app, p1(app))
    main.update(app, 0, 0)
    assert heard == []
    p1(app)["on_tile"] = None  # forget it: the same spot now counts as arriving on the tile
    main.update(app, 0, 0)
    assert heard == ["blip"]


def test_tiles_are_floor_not_things(in_hold):
    """The player walks over the tiles, and E never acts on them: standing on one, E does nothing."""
    state = in_hold["state"]
    solids = main.solid_rects(state)
    for tile in puzzle_tiles("hold_tiles"):
        rect = main.thing_rect(tile)
        assert rect.collidelist(solids) == -1, tile
        on_it = (rect.centerx - main.PLAYER_SIZE // 2, rect.centery - main.PLAYER_SIZE // 2)
        assert main.nearest_target(state, on_it) is None, tile
        assert main.prompt(state, on_it) == "", tile


def test_a_mistake_makes_the_tiles_blink_red_then_go_dark(in_hold):
    app = in_hold
    walk_onto(app, "tile_2")  # wrong: the wave starts from 1
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    corner = main.thing_rect("tile_5").move(3, 3).topleft  # inside the tile, away from its number
    colors = []
    for _ in range(main.FLASH_FRAMES + 2):
        main.draw(app, screen)
        colors.append(tuple(screen.get_at(corner))[:3])
        main.update(app, 0, 0)
    red, dark = sprites.PALETTE["r"], sprites.PALETTE["d"]
    assert colors[0] == red
    assert colors[main.FLASH_BLINK] == dark
    assert colors[2 * main.FLASH_BLINK] == red
    assert colors[-1] == dark


def test_every_floor_outcome_has_a_sound():
    """The events step_on, leave_zone, pour and travel accept each have a sound, and every sound exists."""
    assert set(main.EVENT_SOUNDS) == {"tile_lit", "phase_complete", "tiles_complete", "tiles_reset",
                                      "potion_poured", "potion_spoiled", "potion_ready", "teleported"}
    for effect in main.EVENT_SOUNDS.values():
        assert effect in sounds.EFFECTS


def test_banner_texts_fit_on_one_line():
    """The banner has room for one line: every text it can show fits on the screen, with its margins."""
    font = main.load_fonts()["text"]
    texts = [room["name"] for room in story.ROOMS.values()]
    texts += [info["toggle_text"] for info in story.OBJECTS.values() if info["kind"] == "switch"]
    for puzzle_id, puzzle in story.FLOOR_PUZZLES.items():
        texts += [puzzle["wrong_text"], puzzle["left_text"]]
        for number, phase in enumerate(puzzle["phases"], start=1):
            texts.append(puzzle["phase_text"].format(number=number, name=phase["name"]))
        for tile in puzzle_tiles(puzzle_id):
            texts.append(puzzle["lit_text"].format(label=story.OBJECTS[tile]["label"]))
    for text in texts:
        assert font.size(text)[0] + 20 <= main.WIDTH, text


# --- Drawing ------------------------------------------------------------------------


def test_every_scene_and_room_can_be_drawn(app):
    """A smoke test: drawing every scene, every room and every door state raises no error."""
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    main.draw(app, screen)
    start_new_game(app)
    states = [in_room(room) for room in story.ROOMS]
    states.append(play(CRAB_DOOR_OPEN))  # the crab's door open, the angel's still locked, the key fused
    states.append(play(IN_THE_CABIN[:1]))  # on the deck: the hold barred
    states.append(play(CIRCUIT_COMPLETE[:-1]))  # in the cabin: one generator pulled, the barrier up
    states.append(play(CIRCUIT_COMPLETE))  # in the cabin: the circuit complete, the key on the altar
    states.append(play(TILES_SOLVED[:-4]))  # in the hold: phase 3, two tiles lit, the barrier up
    states.append(play(TILES_SOLVED))  # in the hold: every tile lit, the second half on the anvil
    states.append(play(KEY_FUSED + [act("use_item", "deck_to_angel", "fused_key"), act("enter", "deck_to_angel")]))
    for state in states:
        app["state"] = state
        p1(app)["pos"] = main.spawn_at_entry(state["room"])
        main.show_banner(app, "banner")
        main.say(app, story.MESSAGES["intro"])
        app["actions"] = engine.actions_for(state, state["room"])
        for scene in ("play", "pause", "confirm", "actions", "inventory"):
            main.set_scene(app, scene)
            main.draw(app, screen)
        app["dialog"] = []
        main.set_scene(app, "play")
        main.draw(app, screen)  # with the hint of what E does
    for ending_path in (TO_THE_CRAB_ENDING, TO_THE_ANGEL_ENDING):
        app["state"] = play(ending_path)
        app["confirm_back"] = "ending"
        for scene in ("ending", "confirm"):
            main.set_scene(app, scene)
            main.draw(app, screen)


# --- Small helpers -------------------------------------------------------------------


def test_wrap_keeps_lines_within_the_width():
    assert main.wrap("uno due tre quattro cinque", 9, len) == ["uno due", "tre", "quattro", "cinque"]


def test_wrap_gives_a_too_long_word_its_own_line():
    assert main.wrap("a lunghissima b", 5, len) == ["a", "lunghissima", "b"]


def test_pages_group_lines():
    assert main.pages(["1", "2", "3", "4", "5"], 2) == [["1", "2"], ["3", "4"], ["5"]]


def test_arrows_and_wasd_give_the_same_directions():
    held = collections.defaultdict(bool, {pygame.K_a: True, pygame.K_UP: True})
    assert main.held_direction(held) == (-1, -1)
    held = collections.defaultdict(bool, {pygame.K_LEFT: True, pygame.K_d: True})
    assert main.held_direction(held) == (0, 0)  # opposite keys cancel out




# --- The map ----------------------------------------------------------------------


def test_map_layout_lines_up_every_door_with_its_way_back():
    """The search over the doors puts each room against the wall of its door, with the two openings facing."""
    layout = main.room_layout()
    assert set(layout) == set(story.ROOMS)
    for door, info in story.DOORS.items():
        back = main.return_door(info["to"], info["room"])
        x, y = layout[info["room"]]
        col, row, width, height = main.door_tiles(door)
        other_x, other_y = layout[info["to"]]
        back_col, back_row, _, _ = main.door_tiles(back)
        if info["side"] in ("N", "S"):
            assert x + col == other_x + back_col, door
        else:
            assert y + row == other_y + back_row, door


def test_map_rooms_never_overlap_on_the_ship():
    layout = main.room_layout()
    areas = {room: pygame.Rect(layout[room], main.room_size(room)) for room in story.ROOMS}
    rooms = list(areas)
    for index, room in enumerate(rooms):
        for other in rooms[index + 1:]:
            assert not areas[room].colliderect(areas[other]), (room, other)


def test_map_fits_in_the_corner_of_the_bar():
    corner = main.map_rect()
    assert corner.top >= 0 and corner.bottom <= main.HUD_HEIGHT and corner.right <= main.WIDTH
    for room in story.ROOMS:
        assert corner.contains(main.map_area(room)), room


def test_map_dot_follows_the_player_inside_the_current_room(app):
    start_new_game(app)
    for room in ("deck", "corridor", "cabin"):
        area = main.map_area(room)
        columns, rows = main.room_size(room)
        for col, row in ((1, 1), (columns - 2, rows - 2), (columns // 2, rows // 2)):
            x, y = main.map_dot(room, main.tile_rect(col, row).topleft)
            assert area.collidepoint(x, y), (room, col, row)
    top = main.map_dot("deck", main.tile_rect(7, 1).topleft)
    bottom = main.map_dot("deck", main.tile_rect(7, 22).topleft)
    assert top[1] < bottom[1]


def test_map_gives_no_hints(app):
    """The map never blinks on a room: not while the anvil waits, nor while the tinctures are scattered."""
    start_new_game(app)
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    found_green = BOTH_HALVES + [act("enter", "hold_to_infirmary"), act("pick_up", "green_tincture")]
    for actions in (found_green, DOCTOR_AT_PEACE):
        app["state"] = play(actions)
        p1(app)["pos"] = main.spawn_at_entry(app["state"]["room"])
        corner = main.map_rect().inflate(4, 4)
        for frame in range(0, main.FPS, 5):
            app["frame"] = frame
            main.draw_hud(app, screen)
            for x in range(corner.left, corner.right):
                for y in range(max(corner.top, 0), min(corner.bottom, main.HUD_HEIGHT)):
                    assert tuple(screen.get_at((x, y)))[:3] != main.COLORS["error"], (actions[-1], frame, x, y)


def test_map_is_drawn_in_every_room(app):
    start_new_game(app)
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    for room in story.ROOMS:
        app["state"] = in_room(room)
        p1(app)["pos"] = main.spawn_at_entry(room)
        main.draw_hud(app, screen)


# --- Big rooms and the camera -------------------------------------------------------


def test_camera_stays_still_in_a_room_the_size_of_the_screen():
    for col, row in ((1, 1), (14, 10), (7, 5)):
        assert main.camera("galley", main.tile_rect(col, row).topleft) == (0, 0)


def test_camera_follows_the_player_along_the_tall_deck_and_stops_at_its_edges():
    top = main.camera("deck", main.tile_rect(7, 1).topleft)
    middle = main.camera("deck", main.tile_rect(7, 12).topleft)
    bottom = main.camera("deck", main.tile_rect(7, 22).topleft)
    columns, rows = main.room_size("deck")
    assert top == (0, 0)
    assert bottom == (0, rows * main.TILE - main.VIEW.height)
    assert top[1] < middle[1] < bottom[1]


def test_camera_scrolls_sideways_in_the_corridor_and_centres_its_low_ceiling():
    columns, rows = main.room_size("corridor")
    west = main.camera("corridor", main.tile_rect(2, 3).topleft)
    east = main.camera("corridor", main.tile_rect(columns - 3, 3).topleft)
    assert west[0] == 0 and east[0] == columns * main.TILE - main.VIEW.width
    assert west[1] == east[1] == (rows * main.TILE - main.VIEW.height) // 2  # less than a screen: black above and below


def test_the_player_is_always_on_screen(app):
    """Wherever the player stands in a big room, the camera keeps them inside the view."""
    for room in ("deck", "corridor", "mine"):
        columns, rows = main.room_size(room)
        for col in range(1, columns - 1, 3):
            for row in range(1, rows - 1, 3):
                position = main.tile_rect(col, row).topleft
                x, y = main.camera(room, position)
                body = main.player_rect(position).move(-x, -y)
                assert main.VIEW.contains(body), (room, col, row)


# --- The portal ---------------------------------------------------------------------


def test_walking_into_the_portal_leads_to_the_mine_and_back(app):
    start_new_game(app)
    app["state"] = in_room("corridor_end")
    stand_next_to(app, "corridor_portal")  # just below the ring
    walk_until(app, lambda x, y: app["state"]["room"] == "mine", lambda x, y: (0, -1), limit=60)
    assert p1(app)["pos"] == main.spawn_by_portal("mine_portal")
    assert app["banner"] == story.ROOMS["mine"]["name"]
    assert engine.restore_state(save.load_game())["room"] == "mine"  # saved at once
    walk_until(app, lambda x, y: app["state"]["room"] == "corridor_end", lambda x, y: (0, -1), limit=60)
    assert p1(app)["pos"] == main.spawn_by_portal("corridor_portal")


def test_arriving_by_a_portal_lands_on_free_floor():
    for portal, info in story.OBJECTS.items():
        if info["kind"] == "portal":
            spot = main.player_rect(main.spawn_by_portal(portal))
            assert spot.collidelist(main.solid_rects(in_room(info["room"]))) == -1, portal
            assert main.portal_touched(in_room(info["room"]), spot.topleft) is None, portal


def test_big_rooms_are_drawn_through_the_camera(app):
    start_new_game(app)
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    for room in story.ROOMS:
        app["state"] = in_room(room)
        p1(app)["pos"] = main.spawn_at_entry(room)
        main.draw_play_screen(app, screen)


def test_the_mine_portal_takes_the_player_to_the_helm_and_not_back(app, heard):
    """At the bottom of the mine a portal leads to the helm. The ring in the helm does nothing, on foot or with E."""
    start_new_game(app)
    app["state"] = in_room("mine")
    stand_next_to(app, "mine_exit")  # just below the ring
    walk_until(app, lambda x, y: app["state"]["room"] == "helm", lambda x, y: (0, -1), limit=60)
    assert p1(app)["pos"] == main.spawn_by_portal("helm_portal")
    assert heard == ["ding"]
    assert engine.restore_state(save.load_game())["room"] == "helm"
    saved = save.load_game()
    walk_until(app, lambda x, y: main.portal_touched(app["state"], p1(app)["pos"]) == "helm_portal",
               lambda x, y: (0, -1), limit=60)  # straight back into the ring
    for _ in range(30):
        main.update(app, 0, 0)  # and standing in it
    assert app["state"]["room"] == "helm"
    assert heard == ["ding"] and save.load_game() == saved and app["dialog"] == []
    assert main.prompt(app["state"], p1(app)["pos"]) == ""
    press(app, pygame.K_e)
    assert app["scene"] == "play" and app["dialog"] == []


def test_the_helm_portal_is_far_from_the_ladder_and_the_wheel():
    """Arriving in the helm puts the player on free floor, away from the door down to the cabin."""
    spot = main.player_rect(main.spawn_by_portal("helm_portal"))
    assert spot.collidelist(main.solid_rects(in_room("helm"))) == -1
    assert main.door_touched("helm", spot.topleft, 0, 0) is None


def test_the_cabin_is_half_as_big_again_and_the_camera_follows():
    assert main.room_size("cabin") == (main.COLUMNS * 3 // 2, main.ROWS * 3 // 2)
    top_left = main.camera("cabin", main.tile_rect(1, 1).topleft)
    bottom_right = main.camera("cabin", main.tile_rect(22, 16).topleft)
    assert top_left == (0, 0)
    assert bottom_right == (24 * main.TILE - main.VIEW.width, 18 * main.TILE - main.VIEW.height)


def test_the_corridor_is_two_tiles_lower():
    assert main.room_size("corridor") == (48, 6)


def test_the_sea_is_a_storm_except_in_the_good_ending(app):
    """Four darker pictures of the sea, all different, one after the other; the good ending keeps a calm sea."""
    storm = [sprites.image(f"wall_deck_{k}") for k in range(main.SEA_PICTURES)]
    pictures = {pygame.image.tobytes(picture, "RGBA") for picture in storm}
    assert len(pictures) == main.SEA_PICTURES
    seen = set()
    for frame in range(main.SEA_PICTURES * main.WAVE_FRAMES):
        app["frame"] = frame
        seen.add(main.wave_frame(app))
    assert seen == set(range(main.SEA_PICTURES))

    def brightness(picture):
        width, height = picture.get_size()
        return sum(sum(picture.get_at((x, y))[:3]) for x in range(width) for y in range(height))
    assert brightness(storm[0]) < brightness(sprites.image("sea_calm_0"))
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    app["state"] = play(TO_THE_CRAB_ENDING)
    main.set_scene(app, "ending")
    app["frame"] = 0
    main.draw(app, screen)
    calm = sprites.image("sea_calm_0")
    sea_y = main.ENDING_HORIZON + 8
    assert tuple(screen.get_at((2, sea_y)))[:3] == tuple(calm.get_at((2, sea_y - main.ENDING_HORIZON)))[:3]


# --- The choice of the character ---------------------------------------------------


def test_new_game_lets_the_player_choose_among_four_characters(app):
    """Right, then Enter: the game starts with the second character, saved, and Resume keeps it."""
    press(app, pygame.K_RETURN, pygame.K_RETURN)  # "New game", "1 player"
    assert app["scene"] == "character" and main.character_entries() == ["wizard", "nurse", "ghost", "flash"]
    assert main.character_entries()[app["menu_index"]] == "wizard"
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    for _ in range(4):
        lines = main.character_lines(app, main.character_entries()[app["menu_index"]])
        assert lines[-1] == story.MESSAGES["abilities_for_two"]  # alone, the character is only a look
        assert 116 + len(lines) * app["fonts"]["text"].get_linesize() < main.HEIGHT - 30  # above the hint
        main.draw(app, screen)
        press(app, pygame.K_RIGHT)
    press(app, pygame.K_RIGHT)
    assert main.character_entries()[app["menu_index"]] == "nurse"
    press(app, pygame.K_RETURN)
    assert app["scene"] == "play"
    assert app["state"]["flags"]["character"] == "nurse"
    assert main.player_picture(app, p1(app)) is sprites.image("nurse_down_0")
    assert engine.restore_state(save.load_game())["flags"]["character"] == "nurse"
    again = relaunch()
    press(again, pygame.K_DOWN, pygame.K_RETURN)  # "Resume"
    assert main.player_picture(again, p1(again)) is sprites.image("nurse_down_0")


def test_the_choice_wraps_around_and_esc_goes_back(app):
    press(app, pygame.K_RETURN, pygame.K_RETURN)  # "New game", "1 player"
    press(app, pygame.K_LEFT)  # from the first, left goes round to the last
    assert main.character_entries()[app["menu_index"]] == "flash"
    press(app, pygame.K_d)  # WASD works too
    assert main.character_entries()[app["menu_index"]] == "wizard"
    press(app, pygame.K_ESCAPE)
    assert app["scene"] == "mode"  # one step back: the choice of the mode
    press(app, pygame.K_ESCAPE)
    assert app["scene"] == "menu" and app["state"] is None
    assert save.load_game() is None  # nothing was started


def test_restarting_from_the_pause_menu_also_asks_for_a_character(app):
    """Restart asks first, then the choice; Esc from the choice goes back to the pause menu, game untouched."""
    start_new_game(app)
    before = app["state"]
    press(app, pygame.K_ESCAPE, pygame.K_DOWN, pygame.K_RETURN)  # "Restart"
    press(app, pygame.K_UP, pygame.K_RETURN, pygame.K_RETURN)  # "Yes", "1 player"
    assert app["scene"] == "character"
    press(app, pygame.K_ESCAPE)
    assert app["scene"] == "mode"
    press(app, pygame.K_ESCAPE)
    assert app["scene"] == "pause" and app["state"] == before
    press(app, pygame.K_DOWN, pygame.K_RETURN, pygame.K_UP, pygame.K_RETURN, pygame.K_RETURN, pygame.K_RIGHT,
          pygame.K_RETURN)
    assert app["scene"] == "play" and app["state"]["flags"]["character"] == "nurse"


def test_the_four_characters_look_different_in_every_picture():
    """Each character has its own pictures: no two share one, standing or walking, in any direction."""
    for direction in ("down", "up", "right"):
        for step in range(3):
            pictures = [tuple(sprites.SPRITES[f"{info['sprite']}_{direction}_{step}"])
                        for info in story.CHARACTERS.values()]
            assert len(set(pictures)) == len(story.CHARACTERS), (direction, step)
    for info in story.CHARACTERS.values():
        assert info["name"] and info["ability"]


def test_the_choice_screen_can_be_drawn(app):
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    press(app, pygame.K_RETURN, pygame.K_RETURN)
    for index in range(len(main.character_entries())):
        app["menu_index"] = index
        main.draw(app, screen)


# --- The inventory: clues on the left, items on the right ------------------------------


def test_inventory_shows_the_clues_left_and_the_items_right(app):
    playing(app, IN_THE_HOLD + [act("use_item", "hold_puzzle", "wand")])
    clues, items = main.inventory_columns()
    assert clues.right < items.left  # two columns, the clues first
    assert main.clue_lines(app["state"]) == [("text", story.CLUES["crab_truthful"])]
    assert main.item_lines(app["state"])[0] == ("name", story.ITEMS["wand"]["name"])
    assert main.clue_lines(engine.new_game()) == [("dim", story.MESSAGES["clues_none"])]
    press(app, pygame.K_i)
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    main.draw(app, screen)


def test_a_long_inventory_scrolls_one_item_at_a_time(app):
    """With seven items the list does not fit: down jumps to the next item, never past the end; up goes back."""
    playing(app, TINCTURES_FOUND[:-1])
    press(app, pygame.K_i)
    assert app["scene"] == "inventory" and app["inventory_scroll"] == 0
    limit = main.inventory_scroll_limit(app)
    assert limit > 0
    _, items = main.inventory_columns()
    rows = main.column_rows(app, main.item_lines(app["state"]), items.width)
    press(app, pygame.K_DOWN)
    assert rows[app["inventory_scroll"]] == ("name", story.ITEMS["key"]["name"])
    for _ in range(20):
        press(app, pygame.K_DOWN)
    assert app["inventory_scroll"] == limit  # the last item is in view, no further
    press(app, pygame.K_UP)
    assert 0 < app["inventory_scroll"] < limit
    for _ in range(20):
        press(app, pygame.K_w)
    assert app["inventory_scroll"] == 0
    press(app, pygame.K_DOWN, pygame.K_i, pygame.K_i)  # closing and opening again starts at the top
    assert app["scene"] == "inventory" and app["inventory_scroll"] == 0


def test_a_new_clue_chimes_and_glows_on_the_barrel(app, heard):
    playing(app, IN_THE_HOLD)
    stand_next_to(app, "hold_puzzle")
    press(app, pygame.K_e)
    choose_in_menu(app, "use_item", "wand")
    assert "clue" in heard
    assert app["fx"]["clue"]["rect"] == main.thing_rect("hold_puzzle")
    read_all(app)
    for _ in range(main.effects.CLUE_FRAMES):
        main.update(app, 0, 0)
    assert app["fx"]["clue"] is None
    press(app, pygame.K_e)  # the clue is already known: using the wand again is refused, and nothing glows
    choose_in_menu(app, "use_item", "wand")
    assert app["fx"]["clue"] is None and heard.count("clue") == 1


def test_the_clue_sound_exists():
    assert "clue" in sounds.EFFECTS


# --- The players: for now one, in app["players"] -------------------------------------------


def test_a_new_app_has_one_player_with_the_old_starting_values(app):
    assert len(app["players"]) == 1
    assert p1(app) == {"pos": (0, 0), "facing": (0, 1), "touching": None, "walk": 0, "moving": False,
                       "on_tile": None, "zones": set()}
    assert main.new_player((5, 7))["pos"] == (5, 7)
    for key in ("player", "facing", "touching", "walk", "moving", "on_tile", "zones"):
        assert key not in app, key  # they all live in the player now


def test_new_players_never_share_their_state():
    first, second = main.new_player(), main.new_player()
    first["zones"].add("hold_tiles")
    assert second["zones"] == set()


# --- Two players: the mode menu ---------------------------------------------------------


def test_the_mode_menu_offers_one_or_two_players(app):
    press(app, pygame.K_RETURN)
    assert app["scene"] == "mode"
    assert main.menu_entries(app) == ["one_player", "two_players"]
    assert main.menu_labels(app) == [story.MESSAGES["menu_one_player"], story.MESSAGES["menu_two_players"]]
    assert main.menu_entries(app)[app["menu_index"]] == "one_player"  # one player is the first choice
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    main.draw(app, screen)
    press(app, pygame.K_DOWN, pygame.K_RETURN)
    assert app["scene"] == "character" and app["two_players"]
    main.draw(app, screen)  # "Player 1: choose"
    press(app, pygame.K_ESCAPE, pygame.K_ESCAPE)
    assert app["scene"] == "menu" and app["state"] is None


def test_one_player_keeps_the_keys_of_always():
    assert main.KEYS_1P[0]["act"] == (pygame.K_e,) and main.KEYS_1P[0]["inventory"] == (pygame.K_i,)
    both = collections.defaultdict(bool, {pygame.K_UP: True, pygame.K_d: True})
    assert main.held_direction(both) == (1, -1)  # arrows and WASD move the one player
    assert main.held_direction(both, main.KEYS_1P[0]) == (1, -1)
    assert not hasattr(main, "KEYS_2P")  # each player has their own computer, and its keyboard


# --- Two computers on the same network (step B) --------------------------------------------


def pump(host, guest, until, frames=300, host_move=(0, 0), guest_move=(0, 0)):
    """Run both games frame by frame, each with its own direction held, until `until()` is true.

    The messages go through a real connection on this computer: they may take a moment.
    """
    for _ in range(frames):
        if until():
            return
        main.update(host, *host_move)
        main.update(guest, *guest_move)
        time.sleep(0.001)
    assert until(), "the two computers never got there"


def mine(app):
    """The player on this computer."""
    return main.local_player(app)


@pytest.fixture
def two_computers(app, monkeypatch):
    """A game for two: `app` hosts it (New game, Host game, first character), a second app joins it
    over the network of this computer. Both have read the opening scene."""
    monkeypatch.setattr(main, "NET_PORT", 0)  # any free port: the tests never clash with a real game
    press(app, pygame.K_RETURN, pygame.K_DOWN, pygame.K_RETURN, pygame.K_RETURN)
    assert app["scene"] == "lobby"
    monkeypatch.setattr(main, "NET_PORT", app["net"]["host"].port)
    guest = relaunch()
    press(guest, pygame.K_DOWN, pygame.K_RETURN)  # "Join game"
    assert guest["scene"] == "join"
    main.join(guest, "127.0.0.1")
    pump(app, guest, lambda: guest["scene"] == "character")  # the host is the wizard: the guest chooses
    press(guest, pygame.K_RETURN)  # the first one free: the nurse
    pump(app, guest, lambda: app["scene"] == "play" and guest["scene"] == "play")
    read_all(app)
    read_all(guest)
    yield app, guest
    main.end_network(app)
    main.end_network(guest)


def test_the_main_menu_offers_to_join_a_game(app):
    assert main.menu_labels(app)[1] == story.MESSAGES["menu_join_game"]
    press(app, pygame.K_DOWN, pygame.K_RETURN)
    assert app["scene"] == "join" and app["net"] is None
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    app["join_text"] = ""
    press(app, pygame.K_1, pygame.K_9, pygame.K_2, pygame.K_PERIOD, pygame.K_KP1, pygame.K_a, pygame.K_BACKSPACE)
    assert app["join_text"] == "192."  # digits and dots only: letters are not part of an address
    main.draw(app, screen)
    press(app, pygame.K_ESCAPE)
    assert app["scene"] == "menu"


def test_nobody_at_the_address_says_so(app, monkeypatch):
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    free = probe.getsockname()[1]
    probe.close()  # a port where nobody waits
    monkeypatch.setattr(main, "NET_PORT", free)
    main.open_join(app)
    app["join_text"] = "127.0.0.1"
    press(app, pygame.K_RETURN)
    assert app["scene"] == "join" and app["join_error"] == story.MESSAGES["cannot_join"] and app["net"] is None
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))
    press(app, pygame.K_1)
    assert app["join_error"] == ""  # typing again clears it


def test_hosting_shows_the_address_and_esc_stops_waiting(app, monkeypatch):
    monkeypatch.setattr(main, "NET_PORT", 0)
    press(app, pygame.K_RETURN, pygame.K_DOWN, pygame.K_RETURN, pygame.K_RETURN)
    assert app["scene"] == "lobby" and app["net"]["role"] == "host"
    assert app["net"]["address"] == net.local_address()
    for _ in range(5):
        main.update(app, 0, 0)  # nobody joins: it keeps waiting
    assert app["scene"] == "lobby"
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))
    port = app["net"]["host"].port
    press(app, pygame.K_ESCAPE)
    assert app["scene"] == "menu" and app["net"] is None
    with pytest.raises(OSError):
        net.connect("127.0.0.1", port, timeout=0.5)  # the port is closed again


def test_a_computer_that_cannot_host_says_so(app, monkeypatch):
    def refuse(port):
        raise OSError("port taken")
    monkeypatch.setattr(main.net, "Host", refuse)
    press(app, pygame.K_RETURN, pygame.K_DOWN, pygame.K_RETURN, pygame.K_RETURN)
    assert app["scene"] == "menu" and app["notice"] == story.MESSAGES["cannot_host"]
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))  # the notice under the title
    press(app, pygame.K_DOWN)
    assert app["notice"] == ""  # gone at the first key


def joining(app, monkeypatch, host_keys=()):
    """`app` hosts a new game for two (its character chosen with `host_keys`); a second app joins it
    and is shown the choice of the character. Returns that second app."""
    monkeypatch.setattr(main, "NET_PORT", 0)
    press(app, pygame.K_RETURN, pygame.K_DOWN, pygame.K_RETURN, *host_keys, pygame.K_RETURN)
    monkeypatch.setattr(main, "NET_PORT", app["net"]["host"].port)
    guest = relaunch()
    main.join(guest, "127.0.0.1")
    pump(app, guest, lambda: guest["scene"] == "character")
    return guest


def test_the_player_who_joins_chooses_any_character_but_the_hosts(app, monkeypatch):
    guest = joining(app, monkeypatch, host_keys=(pygame.K_RIGHT,))  # the host is the nurse
    assert guest["taken"] == "nurse" and app["scene"] == "lobby"
    assert main.character_entries()[guest["menu_index"]] == "wizard"
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    main.draw(guest, screen)  # "Player 2: choose", the nurse dark
    main.draw(app, screen)    # "Player 2 is choosing a character"
    press(guest, pygame.K_RIGHT)  # over the nurse, to the ghost
    assert main.character_entries()[guest["menu_index"]] == "ghost"
    press(guest, pygame.K_LEFT, pygame.K_LEFT)  # back over her, and round to the last
    assert main.character_entries()[guest["menu_index"]] == "flash"
    press(guest, pygame.K_RETURN)
    pump(app, guest, lambda: app["scene"] == "play" and guest["scene"] == "play")
    for one in (app, guest):
        assert one["state"]["flags"]["character"] == "nurse" and one["state"]["flags"]["partner_character"] == "flash"
    assert main.player_picture(guest, mine(guest)) is sprites.image("flash_down_0")
    main.end_network(app)
    main.end_network(guest)


def test_the_host_refuses_its_own_character_and_asks_again(app, monkeypatch):
    guest = joining(app, monkeypatch)
    main.send(guest, {"t": "picked", "character": "wizard"})  # the host's own: not through the menu
    guest["taken"] = None
    main.set_scene(guest, "join")
    pump(app, guest, lambda: guest["scene"] == "character")
    assert guest["taken"] == "wizard" and app["scene"] == "lobby"
    main.end_network(app)
    main.end_network(guest)


def test_if_the_player_who_joined_gives_up_the_host_waits_again(app, monkeypatch):
    guest = joining(app, monkeypatch)
    press(guest, pygame.K_ESCAPE)
    assert guest["scene"] == "menu" and guest["net"] is None
    pump(app, guest, lambda: app["net"] is not None and app["net"]["conn"] is None and app["scene"] == "lobby")
    other = relaunch()  # someone else can join now
    main.join(other, "127.0.0.1")
    pump(app, other, lambda: other["scene"] == "character")
    main.end_network(app)
    main.end_network(other)


def test_two_computers_play_the_same_game_each_as_their_player(two_computers):
    host, guest = two_computers
    assert host["state"] == guest["state"] and host["state"]["flags"]["two_players"]
    assert main.my_number(host) == 1 and main.my_number(guest) == 2
    assert len(host["players"]) == len(guest["players"]) == 2
    assert engine.restore_state(save.load_game()) == host["state"]  # only the host keeps the game
    assert main.player_picture(guest, mine(guest)) is sprites.image("nurse_down_0")  # the one the guest chose
    assert main.player_picture(guest, guest["players"][0]) is sprites.image("wizard_down_0")
    assert main.player_picture(host, host["players"][1]) is sprites.image("nurse_down_0")
    assert engine.restore_state(save.load_game())["flags"]["partner_character"] == "nurse"


def test_each_computer_moves_only_its_own_player_and_sees_the_other(two_computers):
    host, guest = two_computers
    host_start, guest_start = mine(host)["pos"], mine(guest)["pos"]
    for _ in range(20):
        main.update(host, 1, 0)   # the host walks right
        main.update(guest, 0, 1)  # the guest walks down
    pump(host, guest, lambda: host["players"][1]["pos"] == mine(guest)["pos"]
         and guest["players"][0]["pos"] == mine(host)["pos"])
    assert mine(host)["pos"][0] > host_start[0] and mine(host)["pos"][1] == host_start[1]
    assert mine(guest)["pos"][1] > guest_start[1] and mine(guest)["pos"][0] == guest_start[0]


def test_each_player_goes_through_doors_alone(two_computers):
    host, guest = two_computers
    mine(guest)["pos"] = main.spawn_in_front_of("deck_to_cabin")
    mine(guest)["touching"] = None
    pump(host, guest, lambda: engine.player_room(host["state"], 2) == "cabin", guest_move=(0, -1))
    assert host["state"]["room"] == "deck"  # the host stays on the deck
    assert main.view(guest)["room"] == "cabin" and main.view(host)["room"] == "deck"
    pump(host, guest, lambda: guest["state"] == host["state"])
    assert not main.same_room(host, host["players"][1]) and not main.same_room(guest, guest["players"][0])
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    for app in (host, guest):
        main.draw(app, screen)  # each draws their own room, and the map with both


def test_the_guest_picks_up_an_item_through_the_host(two_computers):
    host, guest = two_computers
    wand = main.thing_rect("wand")
    mine(guest)["pos"] = (wand.centerx - main.PLAYER_SIZE // 2, wand.centery - main.PLAYER_SIZE // 2)
    mine(guest)["touching"] = None
    press(guest, pygame.K_e)
    pump(host, guest, lambda: engine.carries(guest["state"], "wand", 2))
    assert engine.carries(host["state"], "wand", 2) and not engine.carries(host["state"], "wand", 1)
    assert engine.carries(engine.restore_state(save.load_game()), "wand", 2)
    assert main.carried(guest["state"], 2) == ["wand"] and main.carried(host["state"], 1) == []
    read_all(guest)
    press(guest, pygame.K_i)
    assert guest["scene"] == "inventory" and guest["inventory_player"] == 2
    main.draw(guest, pygame.Surface((main.WIDTH, main.HEIGHT)))


def test_an_item_handed_over_reaches_the_other_computer(two_computers):
    host, guest = two_computers
    stand_next_to(host, "wand")
    press(host, pygame.K_e)  # the host picks up the wand
    read_all(host)
    mine(guest)["pos"] = (mine(host)["pos"][0] + main.PLAYER_SIZE + 2, mine(host)["pos"][1])
    pump(host, guest, lambda: host["players"][1]["pos"] == mine(guest)["pos"])
    press(host, pygame.K_e)  # next to the guest: the only thing E offers is to give the wand
    assert dialog_text(host) == story.MESSAGES["given"].format(item=story.ITEMS["wand"]["name"])
    pump(host, guest, lambda: engine.carries(guest["state"], "wand", 2))
    assert main.carried(host["state"], 1) == []


def test_the_tiles_start_over_only_when_both_players_are_out_of_the_zone(two_computers, heard):
    host, guest = two_computers
    state = play(IN_THE_HOLD)
    state["flags"]["two_players"] = True
    state["flags"]["partner_room"] = "hold"  # both in the hold
    host["state"], guest["state"] = state, engine.restore_state(state)  # both in the hold before anyone moves
    main.place_at_entry(host)
    main.place_at_entry(guest)
    tile_2 = main.thing_rect("tile_2")
    mine(guest)["pos"] = (tile_2.centerx - main.PLAYER_SIZE // 2, tile_2.top - main.TILE // 2 - main.PLAYER_SIZE // 2)
    main.settle_on_floor(guest, mine(guest))  # the guest waits in the zone, above tile 2
    walk_onto(host, "tile_1")  # the host lights tile 1
    pump(host, guest, lambda: guest["state"]["flags"]["hold_step"] == 1 and host["players"][1]["pos"] == mine(guest)["pos"])
    pump(host, guest, lambda: host["state"]["flags"]["hold_step"] == 2, guest_move=(0, 1))
    assert host["state"]["flags"]["hold_step"] == 2  # the guest stepped on tile 2: any player lights tiles
    zone = main.zone_rect("hold_tiles")
    pump(host, guest, lambda: not zone.collidepoint(main.player_rect(mine(host)["pos"]).center), host_move=(0, -1))
    for _ in range(30):
        main.update(host, 0, -1)
        main.update(guest, 0, 0)
    assert host["state"]["flags"]["hold_step"] == 2 and "buzz" not in heard  # the guest is still in the zone
    pump(host, guest, lambda: guest["state"]["flags"]["hold_step"] == 0, frames=400, guest_move=(0, -1))
    assert host["state"]["flags"]["hold_step"] == 0 and "buzz" in heard


def test_the_lower_player_is_drawn_in_front(two_computers):
    """Two players on the same spot, one a little lower: the lower one covers the other."""
    host, _ = two_computers  # the host is the wizard (purple), the guest the nurse (white)
    host["fade"] = 0
    x, y = main.tile_rect(4, 8).topleft
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))

    def shirt_color(lower):
        first, second = host["players"]
        first["pos"], second["pos"] = ((x, y + 6), (x, y)) if lower == "p1" else ((x, y), (x, y + 6))
        for one in host["players"]:
            one["facing"], one["moving"] = (0, 1), False
        main.draw(host, screen)
        cam_x, cam_y = main.camera("deck", main.view_position(host))
        body = main.player_rect((first if lower == "p1" else second)["pos"])
        return tuple(screen.get_at((body.centerx - cam_x, body.bottom + 1 - 5 - cam_y)))[:3]
    assert shirt_color("p1") == sprites.PALETTE["p"]  # the host, in purple, in front
    assert shirt_color("p2") == sprites.PALETTE["w"]  # the guest, in white, in front


def test_in_a_game_for_two_the_pause_menu_does_not_stop_the_game(two_computers):
    host, guest = two_computers
    press(host, pygame.K_ESCAPE)
    assert host["scene"] == "pause" and main.menu_entries(host) == ["continue", "main_menu", "quit"]
    start = mine(guest)["pos"]
    for _ in range(10):
        main.update(guest, 0, 1)  # the guest keeps walking...
    pump(host, guest, lambda: host["players"][1]["pos"] == mine(guest)["pos"])  # ...and the host still sees it
    assert mine(guest)["pos"] != start


def test_when_one_computer_leaves_the_other_goes_back_to_the_menu(two_computers):
    host, guest = two_computers
    press(guest, pygame.K_ESCAPE)
    choose = main.menu_entries(guest).index("main_menu")
    press(guest, *([pygame.K_DOWN] * choose), pygame.K_RETURN)
    assert guest["scene"] == "menu" and guest["net"] is None
    pump(host, guest, lambda: host["scene"] == "menu")
    assert host["notice"] == story.MESSAGES["partner_left"] and host["net"] is None
    main.draw(host, pygame.Surface((main.WIDTH, main.HEIGHT)))
    assert engine.restore_state(save.load_game())["flags"]["two_players"]  # the game is kept: it can be hosted again


def test_a_game_for_two_is_resumed_by_hosting_it_again(two_computers, monkeypatch):
    host, guest = two_computers
    main.end_network(guest)
    pump(host, guest, lambda: host["scene"] == "menu")
    again = relaunch()
    press(again, pygame.K_DOWN, pygame.K_RETURN)  # "Resume"
    assert again["scene"] == "lobby"
    monkeypatch.setattr(main, "NET_PORT", again["net"]["host"].port)
    other = relaunch()
    main.join(other, "127.0.0.1")
    pump(again, other, lambda: again["scene"] == "play" and other["scene"] == "play")
    assert other["state"] == again["state"] and other["dialog"] == []  # the room's name, no opening scene
    assert other["state"]["flags"]["partner_character"] == "nurse"  # the characters of the first time: no choice
    main.end_network(again)
    main.end_network(other)


def test_alone_there_is_no_partner_to_give_to(app):
    start_new_game(app)
    stand_next_to(app, "wand")
    press(app, pygame.K_e)
    read_all(app)
    assert main.give_actions(app, p1(app)) == []


# --- The crab, in a game for two (step C) ---------------------------------------------------


def two_playing(app, actions, partner_room=None):
    """This computer hosts a game for two in the middle (no network: player 2 stands where the test puts them).

    The actions are played by player 1; player 2 is in `partner_room` (player 1's room if None).
    """
    state = engine.new_game(two_players=True)
    for action in actions:
        state, outcome = engine.perform(state, action)
        assert outcome["ok"], (action, outcome)
    state["flags"]["partner_room"] = partner_room or state["room"]
    app["state"] = state
    main.set_up_players(app)
    main.place_at_entry(app)
    main.reset_crab(app)
    main.set_scene(app, "play")
    app["dialog"] = []


def free_spot(app, col, row, room=None):
    """The free floor nearest to a tile of the room on screen: where a test can put a player."""
    state = main.room_state(app["state"], room or app["state"]["room"])
    for distance in range(12):
        for dc in range(-distance, distance + 1):
            for dr in range(-distance, distance + 1):
                rect = pygame.Rect(0, 0, main.PLAYER_SIZE, main.PLAYER_SIZE)
                rect.center = main.tile_rect(col + dc, row + dr).center
                if main.is_free_floor(state, rect.topleft):
                    return rect.topleft
    raise AssertionError("no free floor near there")


def awake_crab(app, wait=0):
    """One frame, so the crab wakes; then it moves at once (or after `wait` frames)."""
    main.update(app, 0, 0)
    assert app["crab"] is not None
    app["crab"]["wait"] = wait


def distance(one, other):
    return pygame.Vector2(main.player_rect(one).center).distance_to(main.player_rect(other).center)


def test_the_crab_wakes_on_the_deck_when_the_cabin_is_solved(app, heard):
    two_playing(app, IN_THE_CABIN)
    for _ in range(30):
        main.update(app, 0, 0)
    assert app["crab"] is None
    app["state"] = play_two(CIRCUIT_COMPLETE, partner_room="cabin")  # the generators were just pulled
    main.update(app, 0, 0)
    crab = app["crab"]
    assert crab["room"] == "deck" and crab["wait"] > 0
    assert crab["pos"] == main.new_crab()["pos"] and main.is_free_floor(main.room_state(app["state"], "deck"), crab["pos"])
    assert app["banner"] == story.MESSAGES["crab_wakes"] and "crab_wake" in heard
    assert engine.statue_broken(app["state"]) and sprites.image("decor_crab_rubble") is not None
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))


def play_two(actions, partner_room=None):
    state = engine.new_game(two_players=True)
    for action in actions:
        state, outcome = engine.perform(state, action)
        assert outcome["ok"], (action, outcome)
    state["flags"]["partner_room"] = partner_room or state["room"]
    return state


def test_alone_the_crab_never_wakes(app):
    start_new_game(app)
    playing(app, FIRST_HALF)
    for _ in range(60):
        main.update(app, 0, 0)
    assert app["crab"] is None and app["downed"] == {}


def test_the_crab_chases_the_nearest_player_slowly_and_knocks_them_down(app, heard):
    two_playing(app, FIRST_HALF)  # both on the deck: the cabin is solved, the key not fused yet
    awake_crab(app)
    start = app["crab"]["pos"]
    p1(app)["pos"] = free_spot(app, 4, 14)    # near the crab
    app["players"][1]["pos"] = free_spot(app, 14, 3)  # far away
    before = distance(app["crab"]["pos"], p1(app)["pos"])
    for _ in range(10):
        last = app["crab"]["pos"]
        main.update(app, 0, 0)
        step = pygame.Vector2(app["crab"]["pos"]) - pygame.Vector2(last)
        assert step.length() <= main.CRAB_SPEED + 0.01  # slower than a player
    assert main.CRAB_SPEED < main.PLAYER_SPEED
    assert distance(app["crab"]["pos"], p1(app)["pos"]) < before and app["crab"]["pos"] != start
    for _ in range(600):
        if app["downed"]:
            break
        main.update(app, 0, 0)
    assert list(app["downed"]) == [1] and app["downed"][1] <= main.DOWN_FRAMES
    assert "knocked" in heard
    where = p1(app)["pos"]
    for _ in range(10):
        main.update(app, 1, 0)  # down: the keys do nothing
    assert p1(app)["pos"] == where
    press(app, pygame.K_e)
    assert app["scene"] == "play" and app["dialog"] == []
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))  # lying down, with the time left


def test_holding_e_next_to_the_partner_down_helps_them_up(app, heard):
    two_playing(app, FIRST_HALF)
    awake_crab(app, wait=10 ** 6)  # the crab stays where it is
    p1(app)["pos"] = free_spot(app, 4, 4)
    app["players"][1]["pos"] = (p1(app)["pos"][0] + main.PLAYER_SIZE + 2, p1(app)["pos"][1])
    app["downed"] = {2: main.DOWN_FRAMES}
    press(app, pygame.K_e)  # next to a player down, E does not open the menu to give items
    assert app["scene"] == "play" and app["dialog"] == []
    for _ in range(main.REVIVE_FRAMES - 10):
        main.update(app, 0, 0, True)
    assert 2 in app["downed"] and app["revive"][2] > 0
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))  # the green bar of the help
    main.update(app, 0, 0, False)  # let go: the help starts over
    assert app["revive"][2] == 0 and 2 in app["downed"]
    for _ in range(main.REVIVE_FRAMES):
        main.update(app, 0, 0, True)
    assert app["downed"] == {} and app["banner"] == story.MESSAGES["helped_up"] and "revived" in heard


def test_e_held_from_too_far_does_not_help(app):
    two_playing(app, FIRST_HALF)
    awake_crab(app, wait=10 ** 6)
    p1(app)["pos"] = free_spot(app, 4, 4)
    app["players"][1]["pos"] = free_spot(app, 14, 4)
    app["downed"] = {2: main.DOWN_FRAMES}
    for _ in range(main.REVIVE_FRAMES + 5):
        main.update(app, 0, 0, True)
    assert 2 in app["downed"] and app["revive"][2] == 0


def test_a_player_left_down_for_a_minute_is_out_and_their_items_pass_on(app, heard):
    two_playing(app, FIRST_HALF)
    app["state"]["flags"]["holder_wand"] = 2  # player 2 carries the wand
    awake_crab(app, wait=10 ** 6)
    app["downed"] = {2: 2}
    main.update(app, 0, 0)
    assert 2 in app["downed"]
    main.update(app, 0, 0)
    assert app["downed"] == {} and engine.is_out(app["state"], 2)
    assert engine.carries(app["state"], "wand", 1)
    assert engine.restore_state(save.load_game()) == app["state"]  # saved at once
    assert app["banner"] == story.MESSAGES["partner_eliminated"] and "knocked_out" in heard
    assert main.active_players(app) == [1]  # the crab only hunts the one left
    assert main.partner_near(app, p1(app)) is None
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))


def test_the_player_out_watches_the_other_one(app):
    two_playing(app, FIRST_HALF + [act("enter", "deck_to_cabin")], partner_room="deck")
    app["state"] = engine.knock_out(app["state"], 2)[0]
    app["me"] = 1  # this computer is player 2's
    main.reset_crab(app)
    assert main.view(app)["room"] == "cabin"  # player 1's room
    assert main.view_position(app) == p1(app)["pos"]
    where = app["players"][1]["pos"]
    for _ in range(10):
        main.update(app, 1, 0)
    assert app["players"][1]["pos"] == where  # out: no more walking
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))


def test_when_the_crab_catches_both_players_the_game_is_over(app, heard):
    two_playing(app, FIRST_HALF)
    awake_crab(app)
    app["downed"] = {2: main.DOWN_FRAMES}  # player 2 is already down...
    app["players"][1]["pos"] = free_spot(app, 14, 3)
    p1(app)["pos"] = app["crab"]["pos"]  # ...and the crab catches player 1
    main.update(app, 0, 0)
    assert app["state"]["ending"] == "caught"
    assert engine.restore_state(save.load_game())["ending"] == "caught"  # saved, like the other endings
    assert app["scene"] == "shatter" and app["dialog"] == []  # the giant claw first...
    main.update(app, 0, 0)
    assert app["crab"] is None and app["downed"] == {}  # the game is over: the crab is gone
    for _ in range(main.SHATTER_FRAMES):
        main.update(app, 0, 0)
    assert app["scene"] == "ending"  # ...then the third ending
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    for frames in (0, main.CRAB_RISE_FRAMES // 2, main.CRAB_RISE_FRAMES + 10):
        app["scene_frames"] = frames
        main.draw(app, screen)
    assert main.menu_entries(app) == ["new_game", "main_menu"]
    assert main.ending_number_label("caught") == story.MESSAGES["ending_number"].format(number=3, total=3)


def test_the_last_player_in_the_game_caught_is_the_end_too(app):
    two_playing(app, FIRST_HALF)
    app["state"] = engine.knock_out(app["state"], 2)[0]  # player 2 is already out
    main.reset_crab(app)
    awake_crab(app)
    p1(app)["pos"] = app["crab"]["pos"]
    main.update(app, 0, 0)
    assert app["state"]["ending"] == "caught"


def test_one_player_down_is_not_the_end(app):
    two_playing(app, FIRST_HALF)
    awake_crab(app)
    app["players"][1]["pos"] = free_spot(app, 14, 3)
    p1(app)["pos"] = app["crab"]["pos"]
    main.update(app, 0, 0)
    assert list(app["downed"]) == [1] and app["state"]["ending"] is None


def test_the_crab_follows_the_players_through_the_doors(app):
    two_playing(app, FIRST_HALF + [act("enter", "deck_to_cabin")])  # both in the cabin, the crab wakes on the deck
    awake_crab(app)
    for _ in range(3000):
        if app["crab"]["room"] == "cabin":
            break
        main.update(app, 0, 0)
    assert app["crab"]["room"] == "cabin" and app["crab"]["away"] > 0  # out of sight for a moment
    assert app["crab"]["pos"] == main.spawn_in_front_of("cabin_to_deck")
    assert not main.crab_here(app)
    for _ in range(main.CRAB_TRANSIT_FRAMES):
        main.update(app, 0, 0)
    assert main.crab_here(app)


def test_the_crab_cannot_follow_through_a_shut_door(app):
    """The players go back to the deck and the door to the hold is barred: nobody to reach, the crab waits."""
    two_playing(app, IN_THE_HOLD)  # the hold is open: the crab can come
    awake_crab(app)
    assert main.crab_target(app) == ("door", "deck_to_hold")
    assert main.door_toward(app["state"], "deck", {"mine"}) is None  # only a portal leads to the mine


def test_the_crab_turns_back_to_stone_once_the_key_is_fused(app, heard):
    two_playing(app, FIRST_HALF)
    awake_crab(app)
    app["downed"] = {2: main.DOWN_FRAMES}
    app["state"] = play_two(KEY_FUSED)
    main.update(app, 0, 0)
    assert app["crab"] is None and app["downed"] == {}
    assert app["banner"] == story.MESSAGES["crab_sleeps"]
    assert not engine.is_out(app["state"], 2)


def test_the_crab_banners_fit_on_one_line():
    font = pixel_font_for_banners()
    for key in ("crab_wakes", "crab_sleeps", "partner_down", "back_up", "helped_up", "partner_eliminated",
                "spectator"):
        assert font.size(story.MESSAGES[key])[0] + 20 <= main.WIDTH, key


def pixel_font_for_banners():
    pygame.font.init()
    return main.load_fonts()["text"]


def test_the_crab_and_the_players_down_reach_the_other_computer(two_computers):
    host, guest = two_computers
    state = play_two(FIRST_HALF)
    host["state"], guest["state"] = state, engine.restore_state(state)
    for app in (host, guest):
        main.place_at_entry(app)
        main.reset_crab(app)
    pump(host, guest, lambda: guest["crab"] is not None)
    host["crab"]["wait"] = 10 ** 6
    host["downed"] = {1: main.DOWN_FRAMES}  # the host is down
    mine(guest)["pos"] = (mine(host)["pos"][0] + main.PLAYER_SIZE + 2, mine(host)["pos"][1])
    pump(host, guest, lambda: 1 in guest["downed"] and host["players"][1]["pos"] == mine(guest)["pos"])
    assert guest["crab"]["room"] == "deck" and guest["banner"] == story.MESSAGES["partner_down"]
    main.draw(guest, pygame.Surface((main.WIDTH, main.HEIGHT)))
    for _ in range(main.REVIVE_FRAMES * 3):  # the guest holds E next to the host
        if not host["downed"]:
            break
        main.update(guest, 0, 0, True)
        main.update(host, 0, 0)
        time.sleep(0.001)
    assert host["downed"] == {}
    pump(host, guest, lambda: guest["downed"] == {})
    assert host["banner"] == story.MESSAGES["back_up"]


# --- The abilities of the characters (Space, once in a game for two) -------------------------


def as_characters(app, first, second):
    """Change who the two players of the game on screen are."""
    app["state"]["flags"]["character"] = first
    app["state"]["flags"]["partner_character"] = second


def test_the_wizards_spell_stuns_the_crab_for_five_seconds_wherever_it_is(app, heard):
    two_playing(app, FIRST_HALF + [act("enter", "deck_to_cabin")], partner_room="deck")  # the wizard is in the cabin
    awake_crab(app)  # the crab is on the deck, with player 2
    app["players"][1]["pos"] = free_spot(app, 4, 3, "deck")
    press(app, pygame.K_SPACE)
    assert app["crab"]["stun"] == main.STUN_FRAMES and "ability" in heard
    assert app["banner"] == story.CHARACTERS["wizard"]["power"]["text"]
    assert engine.restore_state(save.load_game())["flags"]["ability_used_1"] is True
    where = app["crab"]["pos"]
    app["players"][1]["pos"] = where  # player 2 walks right onto it
    for _ in range(main.STUN_FRAMES):
        main.update(app, 0, 0)
        assert app["crab"]["pos"] == where and app["downed"] == {}  # still, and harmless
    app["state"]["room"] = "deck"
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))  # the stars above it (the last frame of the spell)
    main.update(app, 0, 0)
    main.update(app, 0, 0)
    assert 2 in app["downed"]  # the spell is over
    press(app, pygame.K_SPACE)  # once only
    assert app["crab"]["stun"] == 0 and main.ability_hint(app) is None


def test_an_ability_used_while_the_crab_is_a_statue_is_wasted(app):
    two_playing(app, [])
    assert main.ability_hint(app) == (story.MESSAGES["hint_ability"].format(label="Spell"), main.COLORS["highlight"])
    press(app, pygame.K_SPACE)
    assert app["state"]["flags"]["ability_used_1"] is True and app["crab"] is None
    assert app["banner"] == story.MESSAGES["ability_wasted"]
    assert main.ability_hint(app) is None


def test_alone_space_does_nothing(app):
    start_new_game(app)
    before = app["state"]
    press(app, pygame.K_SPACE)
    assert app["state"] is before and app["banner_frames"] == 0
    assert main.ability_hint(app) is None
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))


def test_the_nurse_helps_a_player_up_in_one_second_and_the_others_in_four(app):
    assert main.REVIVE_FRAMES == 4 * main.FPS and main.NURSE_REVIVE_FRAMES == main.FPS
    two_playing(app, FIRST_HALF)
    as_characters(app, "nurse", "flash")
    assert main.ability_hint(app) == (story.MESSAGES["hint_nurse"], main.COLORS["dim_text"])
    awake_crab(app, wait=10 ** 6)
    p1(app)["pos"] = free_spot(app, 4, 4)
    app["players"][1]["pos"] = (p1(app)["pos"][0] + main.PLAYER_SIZE + 2, p1(app)["pos"][1])
    app["downed"] = {2: main.DOWN_FRAMES}
    for _ in range(main.NURSE_REVIVE_FRAMES - 1):
        main.update(app, 0, 0, True)
    assert 2 in app["downed"]
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))
    main.update(app, 0, 0, True)
    assert app["downed"] == {}
    press(app, pygame.K_SPACE)  # nothing to use
    assert app["state"]["flags"]["ability_used_1"] is False


def test_the_crab_cannot_see_the_ghost_and_goes_for_the_other_player(app):
    two_playing(app, FIRST_HALF)
    as_characters(app, "ghost", "wizard")
    awake_crab(app)
    p1(app)["pos"] = free_spot(app, 6, 14)            # the ghost, near the crab
    app["players"][1]["pos"] = free_spot(app, 14, 3)  # the other one, far away
    assert main.crab_target(app) == ("player", 1)
    press(app, pygame.K_SPACE)
    assert app["hidden"] == {1: main.HIDDEN_FRAMES}
    assert main.crab_target(app) == ("player", 2)
    p1(app)["pos"] = app["crab"]["pos"]  # it walks straight through the ghost
    main.update(app, 0, 0)
    assert app["downed"] == {}
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))  # half there
    app["players"][1]["pos"] = free_spot(app, 14, 3)
    p1(app)["pos"] = free_spot(app, 2, 2)
    for _ in range(main.HIDDEN_FRAMES):
        main.update(app, 0, 0)
    assert app["hidden"] == {}  # five seconds later it sees the ghost again
    assert 2 in app["downed"]   # meanwhile it went for the other player, and got them
    assert main.crab_target(app) == ("player", 1)


def test_with_nobody_else_to_hunt_the_crab_runs_from_the_hidden_ghost(app):
    two_playing(app, FIRST_HALF)
    as_characters(app, "ghost", "wizard")
    awake_crab(app)
    app["downed"] = {2: main.DOWN_FRAMES}  # the other player is down
    app["players"][1]["pos"] = free_spot(app, 14, 3)
    p1(app)["pos"] = free_spot(app, 6, 14)
    press(app, pygame.K_SPACE)
    assert main.crab_target(app) == ("flee", 1)
    before = distance(app["crab"]["pos"], p1(app)["pos"])
    for _ in range(120):
        main.update(app, 0, 0)
    assert distance(app["crab"]["pos"], p1(app)["pos"]) > before + 60
    assert app["crab"]["room"] == "deck"  # it does not leave the room
    assert app["state"]["ending"] is None and 1 not in app["downed"]


def test_the_crab_stays_put_when_the_hidden_ghost_is_in_another_room(app):
    two_playing(app, FIRST_HALF + [act("enter", "deck_to_cabin")], partner_room="deck")
    as_characters(app, "ghost", "wizard")
    app["state"] = engine.knock_out(app["state"], 2)[0]  # the other player is out
    main.reset_crab(app)
    awake_crab(app)
    assert main.crab_target(app) == ("door", "deck_to_cabin")
    press(app, pygame.K_SPACE)
    assert main.crab_target(app) is None
    where = app["crab"]["pos"]
    for _ in range(30):
        main.update(app, 0, 0)
    assert app["crab"]["pos"] == where and app["crab"]["room"] == "deck"


def flash_game(app, actions=()):
    two_playing(app, list(actions))
    as_characters(app, "flash", "wizard")


def test_flash_dashes_five_tiles_the_way_they_face(app, heard):
    flash_game(app)
    p1(app)["pos"] = free_spot(app, 3, 6)
    main.update(app, 1, 0)  # facing right
    start = p1(app)["pos"]
    press(app, pygame.K_SPACE)
    assert p1(app)["pos"] == (start[0] + main.DASH_TILES * main.TILE, start[1])
    assert app["dash_trail"] is not None and "ability" in heard
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))  # the streak
    for _ in range(main.DASH_TRAIL_FRAMES):
        main.update(app, 0, 0)
    assert app["dash_trail"] is None
    where = p1(app)["pos"]
    press(app, pygame.K_SPACE)  # once only
    assert p1(app)["pos"] == where


def test_the_dash_stops_against_a_wall(app):
    flash_game(app)
    p1(app)["pos"] = free_spot(app, 3, 6)
    main.update(app, -1, 0)  # facing left, three tiles from the railing
    press(app, pygame.K_SPACE)
    body = main.player_rect(p1(app)["pos"])
    assert body.left == main.tile_rect(1, 0).left and body.collidelist(main.solid_rects(app["state"])) == -1
    assert app["state"]["room"] == "deck"


def test_the_dash_goes_through_an_open_door_on_its_way(app):
    flash_game(app)
    p1(app)["pos"] = main.spawn_in_front_of("deck_to_cabin")
    p1(app)["pos"] = (p1(app)["pos"][0], p1(app)["pos"][1] + 2 * main.TILE)  # two tiles below the door
    p1(app)["facing"] = (0, -1)
    press(app, pygame.K_SPACE)
    assert app["state"]["room"] == "cabin"
    assert p1(app)["pos"] == main.spawn_in_front_of("cabin_to_deck")  # where anyone comes in


def test_the_dash_stops_at_a_shut_door_which_says_why(app):
    flash_game(app)
    p1(app)["pos"] = main.spawn_in_front_of("deck_to_hold")
    p1(app)["pos"] = (p1(app)["pos"][0], p1(app)["pos"][1] - 2 * main.TILE)
    p1(app)["facing"] = (0, 1)
    press(app, pygame.K_SPACE)
    assert app["state"]["room"] == "deck" and dialog_text(app) == " ".join(
        main.wrap(story.DOORS["deck_to_hold"]["barred_text"], main.DIALOG_TEXT_WIDTH, main.text_width(app["fonts"]["text"])))


def test_the_dash_takes_a_portal_on_its_way(app):
    flash_game(app)
    app["state"]["room"] = "corridor_end"
    app["state"]["flags"]["partner_room"] = "corridor_end"
    ring = main.thing_rect("corridor_portal")
    p1(app)["pos"] = (ring.centerx - main.PLAYER_SIZE // 2, ring.bottom + main.TILE)
    p1(app)["facing"] = (0, -1)
    press(app, pygame.K_SPACE)
    assert app["state"]["room"] == "mine"


def test_the_dash_carries_flash_past_the_crab(app):
    flash_game(app, FIRST_HALF)
    as_characters(app, "flash", "wizard")
    awake_crab(app, wait=0)
    app["players"][1]["pos"] = free_spot(app, 14, 3)
    crab = app["crab"]["pos"]
    p1(app)["pos"] = (crab[0] - 2 * main.TILE, crab[1])  # the crab two tiles to the right
    p1(app)["facing"] = (1, 0)
    press(app, pygame.K_SPACE)
    assert p1(app)["pos"][0] > crab[0] + main.TILE  # on its other side
    main.update(app, 0, 0)
    assert app["downed"] == {}


def test_the_dash_lights_only_the_tile_it_lands_on(app, heard):
    flash_game(app, IN_THE_HOLD)
    as_characters(app, "flash", "wizard")
    first, last = main.thing_rect("tile_1"), main.thing_rect("tile_3")
    lane = first.centery - main.PLAYER_SIZE // 2
    p1(app)["pos"] = (first.centerx - main.PLAYER_SIZE // 2 - (main.DASH_TILES * main.TILE - (last.centerx - first.centerx)), lane)
    main.settle_on_floor(app, p1(app))
    p1(app)["facing"] = (1, 0)
    press(app, pygame.K_SPACE)  # over tile 1 and tile 2, landing on tile 3
    assert main.tile_under(app["state"], p1(app)["pos"]) == "tile_3"
    main.update(app, 0, 0)
    assert "blip" not in heard and app["state"]["flags"]["hold_step"] == 0  # tile 3 is not the first of the wave


def test_abilities_reach_the_host_from_the_other_computer(two_computers):
    host, guest = two_computers  # the host is the wizard; the guest becomes the ghost
    state = play_two(FIRST_HALF)
    state["flags"]["partner_character"] = "ghost"
    host["state"], guest["state"] = state, engine.restore_state(state)
    for app in (host, guest):
        main.place_at_entry(app)
        main.reset_crab(app)
    pump(host, guest, lambda: guest["crab"] is not None)
    press(guest, pygame.K_SPACE)
    pump(host, guest, lambda: 2 in guest["hidden"])
    assert 2 in host["hidden"] and host["state"]["flags"]["ability_used_2"] is True
    assert main.ability_hint(guest) is None
    press(host, pygame.K_SPACE)
    pump(host, guest, lambda: guest["crab"]["stun"] > 0)
    main.draw(guest, pygame.Surface((main.WIDTH, main.HEIGHT)))


# --- Dropping items (Q) and the heart of the mine ----------------------------------------------


def test_q_drops_the_last_item_where_the_player_stands_and_e_picks_it_up_again(app, heard):
    start_new_game(app)
    stand_next_to(app, "wand")
    press(app, pygame.K_e)
    read_all(app)
    p1(app)["pos"] = free_spot(app, 11, 4)
    press(app, pygame.K_q)
    assert app["state"]["inventory"] == [] and "drop" in heard
    assert engine.item_place(app["state"], "wand") == ("deck", main.tile_of(p1(app)["pos"]))
    assert app["banner"] == story.MESSAGES["dropped"].format(item=story.ITEMS["wand"]["name"])
    assert engine.restore_state(save.load_game()) == app["state"]
    lying = [thing for thing in engine.things_here(app["state"]) if thing["id"] == "wand"][0]
    assert main.place_rect(lying) == main.tile_rect(*main.tile_of(p1(app)["pos"]))
    assert main.place_rect(lying) != main.thing_rect("wand")  # not where the story put it
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))
    assert main.prompt(app["state"], p1(app)["pos"]) != ""  # E picks it up, right there
    press(app, pygame.K_e)
    assert app["state"]["inventory"] == ["wand"]
    read_all(app)
    p1(app)["pos"] = main.spawn_at_entry("deck")
    press(app, pygame.K_q, pygame.K_q)  # the second time the hands are empty: nothing, silently
    assert app["state"]["inventory"] == [] and app["dialog"] == [] and heard.count("drop") == 2


def test_the_title_says_what_q_does(app):
    assert "Q" in story.MESSAGES["controls_2"]
    font = app["fonts"]["text"]
    assert font.size(story.MESSAGES["controls_2"])[0] <= main.WIDTH - 16


def in_the_mine_together(app):
    """Both players in the mine, the crab awake somewhere else."""
    two_playing(app, FIRST_HALF)
    app["state"]["room"] = "mine"
    app["state"]["flags"]["partner_room"] = "mine"
    main.place_at_entry(app)
    main.reset_crab(app)
    awake_crab(app, wait=10 ** 6)


def test_the_heart_helps_a_player_down_up_at_once(app, heard):
    in_the_mine_together(app)
    app["downed"] = {2: main.DOWN_FRAMES}
    main.update(app, 0, 0)  # the game has seen them down
    stand_next_to(app, "heart")
    press(app, pygame.K_e)
    assert app["downed"] == {} and app["state"]["flags"]["heart_used"] is True
    assert "heart" not in app["state"]["inventory"]
    read_all(app)
    main.update(app, 0, 0)
    assert "revived" in heard


def test_the_heart_is_wasted_when_everyone_is_on_their_feet(app):
    in_the_mine_together(app)
    stand_next_to(app, "heart")
    press(app, pygame.K_e)
    assert dialog_text(app) == " ".join(main.wrap(story.ITEMS["heart"]["pickup_text"], main.DIALOG_TEXT_WIDTH,
                                                    main.text_width(app["fonts"]["text"])))
    assert app["state"]["flags"]["heart_used"] is True and app["state"]["flags"]["out_player"] == 0


def test_the_heart_brings_the_player_out_back_next_to_the_one_who_took_it(two_computers, heard):
    host, guest = two_computers
    state = engine.knock_out(play_two(FIRST_HALF), 2)[0]  # the guest is out, and watches
    state["room"] = "mine"
    host["state"], guest["state"] = state, engine.restore_state(state)
    for app in (host, guest):
        main.place_at_entry(app)
        main.reset_crab(app)
    stand_next_to(host, "heart")
    press(host, pygame.K_e)
    pump(host, guest, lambda: not engine.is_out(guest["state"], 2) and guest["banner"] == story.MESSAGES["back_in_game"])
    assert engine.player_room(guest["state"], 2) == "mine" and main.can_move(guest)
    assert distance(mine(guest)["pos"], mine(host)["pos"]) <= main.PLAYER_SIZE + 4  # right next to the host
    assert main.is_free_floor(main.view(guest), mine(guest)["pos"])
    assert main.view_position(guest) == mine(guest)["pos"]  # their own screen again


# --- The opening lightning, the anvil in the empty room, the broken statue ---------------------


def test_a_bolt_of_lightning_opens_a_new_game_then_the_player_can_move(app, heard, monkeypatch):
    monkeypatch.setattr(main, "LIGHTNING_FRAMES", main.FPS)  # the tests play without it: here it is back
    press(app, pygame.K_RETURN, pygame.K_RETURN, pygame.K_RETURN)
    assert app["lightning"] == 0 and app["lightning_due"]  # not while the opening text is on screen
    main.update(app, 1, 0)
    assert "thunder" not in heard
    read_all(app)
    start = p1(app)["pos"]
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    quiet = pygame.Surface((main.WIDTH, main.HEIGHT))
    app["fade"] = 0  # the room is out of the dark already
    main.draw(app, quiet)
    changed = 0
    for _ in range(main.FPS):
        main.update(app, 1, 0)
        main.draw(app, screen)
        changed += screen.get_at(main.LIGHTNING_BOLT[3]) != quiet.get_at(main.LIGHTNING_BOLT[3])
    assert heard.count("thunder") == 1 and changed > main.FPS // 2  # the screen is torn for a second
    assert p1(app)["pos"] == start  # nobody moves while it strikes
    main.update(app, 1, 0)
    assert p1(app)["pos"][0] > start[0] and app["lightning"] == 0
    main.draw(app, screen)
    assert screen.get_at(main.LIGHTNING_BOLT[3]) == quiet.get_at(main.LIGHTNING_BOLT[3])  # as before


def test_no_lightning_when_a_game_is_resumed(app, heard, monkeypatch):
    monkeypatch.setattr(main, "LIGHTNING_FRAMES", main.FPS)
    start_new_game(app)
    again = relaunch()
    press(again, pygame.K_DOWN, pygame.K_RETURN)  # "Resume"
    main.update(again, 1, 0)
    assert again["lightning"] == 0 and not again["lightning_due"] and again["players"][0]["moving"]


def test_the_bolt_goes_from_the_top_of_the_screen_to_the_bottom():
    for path in (main.LIGHTNING_BOLT, main.LIGHTNING_BRANCH):
        assert all(0 <= x < main.WIDTH and 0 <= y <= main.HEIGHT for x, y in path)
    assert main.LIGHTNING_BOLT[0][1] == 0 and main.LIGHTNING_BOLT[-1][1] == main.HEIGHT
    assert main.lightning_path((0, 0), (10, 100), seed=5) == main.lightning_path((0, 0), (10, 100), seed=5)


def test_the_anvil_appears_in_the_middle_of_the_empty_room_with_red_sparks(app):
    anvil = story.OBJECTS["anvil"]
    columns, rows = main.room_size("east_room")
    assert anvil["room"] == "east_room"
    assert anvil["pos"] in [(col, row) for col in (columns // 2 - 1, columns // 2) for row in (rows // 2 - 1, rows // 2)]
    start_new_game(app)
    to_the_room = [act("enter", door) for door in ("infirmary_to_hold", "hold_to_deck", "deck_to_cabin",
                                                    "cabin_to_east_room")]

    def red_sparks(actions):
        playing(app, actions)
        app["fx"]["particles"].clear()
        for _ in range(60):
            main.update(app, 0, 0)
        near = main.thing_rect("anvil").inflate(40, 60)
        return [one for one in app["fx"]["particles"] if one["color"] in effects.RED and near.collidepoint(one["x"], one["y"])]
    assert red_sparks(TINCTURES_FOUND + to_the_room) == []  # no anvil yet
    assert red_sparks(DOCTOR_AT_PEACE + to_the_room)        # it waits for the key
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))
    fused = DOCTOR_AT_PEACE + to_the_room + [act("use_item", "anvil", "second_key")]
    playing(app, fused)
    for _ in range(200):
        main.update(app, 0, 0)  # the sparks of the welding die out
    app["fx"]["particles"].clear()
    for _ in range(60):
        main.update(app, 0, 0)
    assert [one for one in app["fx"]["particles"] if one["color"] in effects.RED] == []  # its work is done


def test_the_statue_lies_in_pieces_once_the_crab_is_out_and_for_good(app):
    start_new_game(app)
    playing(app, FIRST_HALF)
    assert not engine.statue_broken(app["state"])  # alone, the statue stands
    statue = main.thing_rect("deck_statue")
    assert sprites.image("decor_crab_rubble").get_size() == statue.size  # the same tiles as the statue
    two_playing(app, IN_THE_CABIN)
    whole = pygame.Surface((main.WIDTH, main.HEIGHT))
    app["state"]["room"] = "deck"
    app["state"]["flags"]["partner_room"] = "deck"
    main.place_at_entry(app)
    main.update(app, 0, 0)  # the effects settle on the deck
    app["fade"] = 0
    main.draw(app, whole)
    app["state"] = play_two(FIRST_HALF)
    app["fx"]["particles"].clear()
    main.update(app, 0, 0)  # the crab is breaking out: the statue trembles, then bursts
    for _ in range(main.CRUMBLE_BREAK + 1):
        main.update(app, 0, 0)
    assert len([one for one in app["fx"]["particles"] if one["color"] in main.RUBBLE_COLORS]) >= 30
    assert statue.collidelist(main.solid_rects(app["state"])) != -1  # still in the way, as before
    for _ in range(main.CRUMBLE_FRAMES):
        main.update(app, 0, 0)  # the ship stops shaking
    app["fx"]["particles"].clear()
    app["banner_frames"] = 0
    broken = pygame.Surface((main.WIDTH, main.HEIGHT))
    main.draw(app, broken)
    cam_x, cam_y = main.camera("deck", main.view_position(app))
    top = (statue.left + 3 - cam_x, statue.top + 5 - cam_y)  # where a claw of the statue was
    assert whole.get_at(top) != broken.get_at(top)
    app["state"] = play_two(KEY_FUSED)  # the crab turns to stone and vanishes: the pieces stay
    main.update(app, 0, 0)
    assert app["crab"] is None and engine.statue_broken(app["state"])


def test_the_crab_vanishes_in_a_puff_of_dust(app):
    two_playing(app, FIRST_HALF)
    awake_crab(app)
    main.update(app, 0, 0)
    where = main.player_rect(app["crab"]["pos"]).center
    state = play_two(KEY_FUSED)
    state["room"], state["flags"]["partner_room"] = "deck", "deck"
    app["state"] = state
    app["fx"]["particles"].clear()
    main.update(app, 0, 0)
    dust = [one for one in app["fx"]["particles"] if one["color"] in main.RUBBLE_COLORS]
    assert len(dust) >= 20 and all(abs(one["x"] - where[0]) < 12 and abs(one["y"] - where[1]) < 12 for one in dust)


# --- The whole screen (F11) -----------------------------------------------------------------


def test_the_picture_fills_the_screen_in_whole_multiples_and_stays_in_the_middle():
    assert main.picture_area((main.WIDTH * main.SCALE, main.HEIGHT * main.SCALE)).topleft == (0, 0)  # the window
    for size in ((1920, 1080), (1366, 768), (2560, 1440), (1280, 800), (3840, 2160)):
        area = main.picture_area(size)
        zoom = area.width // main.WIDTH
        assert area.size == (main.WIDTH * zoom, main.HEIGHT * zoom)  # never stretched: every pixel a square
        assert pygame.Rect((0, 0), size).contains(area) and area.center == (size[0] // 2, size[1] // 2)
        assert (main.WIDTH * (zoom + 1) > size[0]) or (main.HEIGHT * (zoom + 1) > size[1])  # as big as fits
    assert main.picture_area((100, 100)).size == (main.WIDTH, main.HEIGHT)  # never smaller than the game


def test_showing_the_game_on_a_bigger_screen_leaves_black_around_it():
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    screen.fill((200, 10, 10))
    window = pygame.Surface((1366, 768))
    window.fill((0, 0, 255))
    pygame.display.set_mode((1, 1))
    main.show(screen, window)
    area = main.picture_area(window.get_size())
    assert tuple(window.get_at(area.center))[:3] == (200, 10, 10)
    assert tuple(window.get_at((2, 2)))[:3] == main.COLORS["black"]
    assert main.FULLSCREEN_KEY == pygame.K_F11 and "F11" in story.MESSAGES["window_title"]


# --- The statue shaking and crumbling ---------------------------------------------------------


def on_deck_before_the_crab(app):
    """A game for two with both players on the deck, the cabin not solved yet: the statue stands."""
    two_playing(app, IN_THE_CABIN)
    app["state"]["room"] = "deck"
    app["state"]["flags"]["partner_room"] = "deck"
    main.place_at_entry(app)
    p1(app)["pos"] = free_spot(app, 4, 12)  # near the statue: it is on screen
    main.update(app, 0, 0)
    app["fade"] = 0
    app["banner_frames"] = 0


def wake_the_crab(app):
    """The cabin has just been solved: the next frame the crab comes alive."""
    state = play_two(FIRST_HALF)
    state["room"], state["flags"]["partner_room"] = app["state"]["room"], app["state"]["flags"]["partner_room"]
    app["state"] = state
    main.update(app, 0, 0)


def test_the_ship_shakes_less_and_less_while_the_statue_crumbles(app, heard):
    on_deck_before_the_crab(app)
    assert main.room_shake(app) == (0, 0)
    wake_the_crab(app)
    assert 35 <= main.CRUMBLE_FRAMES <= 45 and app["crumble"] == main.CRUMBLE_FRAMES - 1
    assert heard.count("crumble") == 1 and "crab_wake" in heard  # the low rumble, with the crab's notes
    shakes = []
    for _ in range(main.CRUMBLE_FRAMES):
        shakes.append(main.room_shake(app))
        main.update(app, 0, 0)
    strength = [abs(dx) + abs(dy) for dx, dy in shakes]
    assert max(strength[:10]) >= 3 and max(strength[:10]) > max(strength[-10:])  # hard at first, then dying down
    assert len(set(shakes[:15])) > 6 and any(dx != 0 for dx, dy in shakes) and any(dy != 0 for dx, dy in shakes)
    assert app["crumble"] == 0 and main.room_shake(app) == (0, 0)
    assert heard.count("crumble") == 1


def test_the_shake_moves_the_room_but_not_the_bar_on_top(app):
    on_deck_before_the_crab(app)
    still = pygame.Surface((main.WIDTH, main.HEIGHT))
    main.draw(app, still)
    wake_the_crab(app)
    app["banner_frames"] = 0
    shaken = pygame.Surface((main.WIDTH, main.HEIGHT))
    moved = 0
    for _ in range(10):
        dx, dy = main.room_shake(app)
        main.draw(app, shaken)
        name = pygame.Rect(0, 0, 90, 14)  # the name of the room, in the bar (the wand's icon glows on its own)
        assert all(shaken.get_at((x, y)) == still.get_at((x, y)) for x in range(name.width) for y in range(name.height))
        if (dx, dy) != (0, 0):
            wall = (2, main.HUD_HEIGHT + 60)  # a pixel of the wall on the left, far from the statue and the players
            moved += shaken.get_at((wall[0] + 8 + dx, wall[1] + dy)) == still.get_at((wall[0] + 8, wall[1]))
        main.update(app, 0, 0)
    assert moved >= 5  # the room is the same picture, pushed aside


def test_the_statue_trembles_whole_then_bursts_and_only_then_the_crab_is_out(app):
    on_deck_before_the_crab(app)
    statue = main.thing_rect("deck_statue")
    wake_the_crab(app)
    assert engine.statue_broken(app["state"]) and main.statue_trembles(app)
    assert app["crab"] is not None and not main.crab_here(app)  # still inside its statue
    drawn = []
    monkey = main.draw_trembling_statue

    def spy(app, screen):
        drawn.append(app["crumble"])
        monkey(app, screen)
    main.draw_trembling_statue = spy
    try:
        screen = pygame.Surface((main.WIDTH, main.HEIGHT))
        looks = set()
        cam_x, cam_y = main.camera("deck", main.view_position(app))
        for frame in range(main.CRUMBLE_BREAK - 1):
            assert main.statue_trembles(app), frame
            main.draw(app, screen)
            dx, dy = main.room_shake(app)
            shell = (statue.centerx - cam_x + dx, statue.centery + 2 - cam_y + dy)  # the middle of its shell
            looks.add(tuple(screen.get_at(shell))[:3])
            falling = [one for one in app["fx"]["particles"] if one["color"] in main.RUBBLE_COLORS]
            main.update(app, 0, 0)
        assert len(drawn) == main.CRUMBLE_BREAK - 1  # the whole statue, every one of those frames
        assert len(looks) >= 2  # it flashes pale now and then
        assert falling and all(one["vy"] >= 0 or one["gravity"] > 0 for one in falling)  # stones and dust come down
        assert all(statue.left - 12 <= one["x"] <= statue.right + 12 for one in falling)  # around the statue
        before = len(falling)
        for _ in range(3):
            main.update(app, 0, 0)
        assert not main.statue_trembles(app) and main.crab_here(app)  # it has burst: the crab is out
        assert len([one for one in app["fx"]["particles"] if one["color"] in main.RUBBLE_COLORS]) >= before + 30
        main.draw(app, screen)
        assert len(drawn) == main.CRUMBLE_BREAK - 1  # rubble from now on
    finally:
        main.draw_trembling_statue = monkey


def test_far_from_the_deck_the_ship_still_shakes_but_no_stones_fall(app, heard):
    two_playing(app, IN_THE_CABIN)  # both in the cabin, where the generators are: nobody sees the statue
    main.update(app, 0, 0)
    app["state"] = play_two(CIRCUIT_COMPLETE)
    app["fx"]["particles"].clear()
    main.update(app, 0, 0)
    assert app["crumble"] > 0 and "crumble" in heard
    assert any(main.room_shake(app) != (0, 0) or main.update(app, 0, 0) for _ in range(5))
    for _ in range(main.CRUMBLE_FRAMES):
        main.update(app, 0, 0)
    assert [one for one in app["fx"]["particles"] if one["color"] in main.RUBBLE_COLORS] == []


def test_without_the_effect_the_statue_bursts_at_once_as_before(app, heard, monkeypatch):
    monkeypatch.setitem(effects.FX, "crumble", False)
    on_deck_before_the_crab(app)
    app["fx"]["particles"].clear()
    wake_the_crab(app)
    assert app["crumble"] == 0 and "crumble" not in heard and main.room_shake(app) == (0, 0)
    assert len([one for one in app["fx"]["particles"] if one["color"] in main.RUBBLE_COLORS]) >= 30
    assert main.crab_here(app)


def test_a_new_game_starts_without_anything_left_of_the_crumbling(app):
    on_deck_before_the_crab(app)
    wake_the_crab(app)
    assert app["crumble"] > 0
    press(app, pygame.K_ESCAPE)
    choose = main.menu_entries(app).index("main_menu")
    press(app, *([pygame.K_DOWN] * choose), pygame.K_RETURN)
    assert app["scene"] == "menu" and app["crumble"] == 0
    press(app, pygame.K_RETURN, pygame.K_RETURN, pygame.K_RETURN, pygame.K_RETURN)  # New game, Yes, 1 player, the wizard
    read_all(app)
    assert app["scene"] == "play" and app["crumble"] == 0 and main.room_shake(app) == (0, 0)
    main.update(app, 0, 0)
    assert app["crab"] is None


# --- The giant claw that breaks the screen ----------------------------------------------------


def caught_both(app):
    """A game for two at the moment the crab catches the second player: the claw sequence has just started."""
    two_playing(app, FIRST_HALF)
    awake_crab(app)
    for _ in range(main.CRUMBLE_FRAMES):
        main.update(app, 0, 0)
    app["crab"]["wait"] = 0
    app["fade"] = 0
    app["banner_frames"] = 0
    app["downed"] = {2: main.DOWN_FRAMES}
    app["players"][1]["pos"] = free_spot(app, 12, 6)
    p1(app)["pos"] = app["crab"]["pos"]
    main.update(app, 0, 0)
    assert app["scene"] == "shatter"


def colors(screen, step=4):
    return [tuple(screen.get_at((x, y)))[:3] for x in range(0, main.WIDTH, step) for y in range(0, main.HEIGHT, step)]


def test_the_claw_breaks_a_copy_of_the_last_picture_of_the_game(app):
    caught_both(app)
    shatter = app["shatter"]
    assert shatter["frozen"].get_size() == (main.WIDTH, main.HEIGHT)  # the small screen, before it is enlarged
    again = pygame.Surface((main.WIDTH, main.HEIGHT))
    main.draw_play_screen(app, again, overlays=False)
    room = tuple(shatter["frozen"].get_at((20, main.HUD_HEIGHT + 100)))[:3]
    assert room != main.COLORS["black"] and room == sprites.PALETTE["b"] or room in sprites.PALETTE.values()
    assert len(set(colors(shatter["frozen"]))) > 8  # the room, the bar, the players: a real picture
    assert len(shatter["shards"]) == len(shatter["pieces"]) >= 20 and shatter["hit"] == (main.WIDTH // 2, main.HEIGHT // 2)
    frozen_before = colors(shatter["frozen"])
    for _ in range(40):
        main.update(app, 0, 0)
    assert colors(shatter["frozen"]) == frozen_before  # frozen: the game behind it has stopped


def test_the_three_parts_of_the_sequence_come_at_their_frames_with_their_sounds(app, heard):
    caught_both(app)
    assert main.CLAW_ATTACK == 15 and main.CLAW_IMPACT == 27 and 80 <= main.SHATTER_FRAMES <= 90
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    frozen = app["shatter"]["frozen"]
    corner = (6, main.HEIGHT - 6)  # far from the claw and from the middle
    black, played = {}, {}
    del heard[:]
    while app["scene"] == "shatter":
        age = app["shatter"]["age"]
        main.draw(app, screen)
        black[age] = sum(1 for color in colors(screen) if color == main.COLORS["black"])
        if age < main.CLAW_ATTACK:
            assert screen.get_at(corner) == frozen.get_at(corner), age  # the picture, still, under the claw
        if age in (main.CLAW_ATTACK, main.CLAW_ATTACK + 1):
            assert tuple(screen.get_at(corner))[:3] != tuple(frozen.get_at(corner))[:3], age  # the white flash
            assert sum(tuple(screen.get_at(corner))[:3]) > 500
        before = len(heard)
        main.update(app, 0, 0)
        for name in heard[before:]:
            played[name] = age + 1
    assert played == {"snap": main.CLAW_ATTACK, "shatter": main.CLAW_IMPACT}  # the snap at the hit, the glass after
    assert heard == ["snap", "shatter"]
    whole = (main.WIDTH // 4) * (main.HEIGHT // 4)
    assert black[main.CLAW_IMPACT - 1] < whole // 10           # cracked, but still in one piece
    falling = [black[age] for age in range(main.CLAW_IMPACT, main.SHATTER_FRAMES)]
    assert falling[5] < falling[25] < falling[45]                # more and more black behind the pieces
    assert falling[-1] > whole * 0.9                             # at the end almost nothing is left
    assert app["scene"] == "ending" and app["shatter"] is None and app["scene_frames"] == 0


def test_the_sequence_uses_the_limb_of_claw_with_its_own_frames():
    for age in (0, main.CLAW_REACH, main.CLAW_ATTACK, main.CLAW_IMPACT, main.SHATTER_FRAMES):
        assert main.claw_pose(age) == claw.pose(age, (main.WIDTH, main.HEIGHT), main.CLAW_REACH, main.CLAW_ATTACK,
                                                main.CLAW_IMPACT, main.CLAW_RETREAT)
    middle = (main.WIDTH / 2, main.HEIGHT / 2)
    assert main.claw_pose(main.CLAW_ATTACK - 1)["tip"] == pytest.approx(middle)  # where the cracks start
    assert not hasattr(main, "claw_jaws") and sprites.image("giant_claw") is None  # no picture enlarged any more


def shadow_pixels(age):
    """How many pixels of a white screen the claw's shadow darkens at this frame, where the limb is not."""
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    screen.fill((255, 255, 255))
    main.draw_giant_claw(screen, age)
    tones = {claw.OUTLINE, claw.SHADOW, claw.BASE, claw.LIGHT, claw.PLATE, claw.TOOTH, (255, 255, 255)}
    grey = [tuple(screen.get_at((x, y)))[:3] for x in range(main.WIDTH) for y in range(main.HEIGHT)]
    grey = [color for color in grey if color not in tones]
    assert all(color[0] == color[1] == color[2] and 90 < color[0] < 200 for color in grey)  # see-through black
    return len(grey)


def test_the_shadow_of_the_claw_closes_in_on_it_and_touches_it_at_the_hit():
    pygame.display.set_mode((1, 1))
    seen = [shadow_pixels(age) for age in (6, 9, 12, main.CLAW_ATTACK - 1)]
    assert seen[0] > 300 and seen[1] > seen[2] > seen[3] == 0  # less and less of it shows; then none: they touch
    assert shadow_pixels(main.CLAW_ATTACK + 3) == 0  # and it stays under the claw while the screen cracks
    assert shadow_pixels(main.CLAW_IMPACT + 3) == 0  # no shadow on a screen that is falling apart


def test_sparks_fly_from_the_grip_when_the_jaws_shut(app):
    caught_both(app)
    while app["shatter"]["age"] < main.CLAW_ATTACK - 1:
        main.update(app, 0, 0)
    assert app["shatter"]["sparks"] == []
    main.update(app, 0, 0)  # the snap
    sparks = app["shatter"]["sparks"]
    tip = main.claw_pose(main.CLAW_ATTACK)["tip"]
    assert len(sparks) == main.CLAW_SPARKS >= 12
    assert all(abs(one["x"] - tip[0]) < 1 and abs(one["y"] - tip[1]) < 1 for one in sparks)  # from where the jaws meet
    assert len({(round(one["vx"], 2), round(one["vy"], 2)) for one in sparks}) > main.CLAW_SPARKS // 2  # every way
    assert {one["color"] for one in sparks} <= set(effects.SPARK) | {claw.LIGHT, claw.BASE}
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    main.update(app, 0, 0)
    main.update(app, 0, 0)
    main.update(app, 0, 0)
    assert max(abs(one["x"] - tip[0]) + abs(one["y"] - tip[1]) for one in sparks) > 6  # flying off
    main.draw(app, screen)
    while app["scene"] == "shatter" and app["shatter"]["age"] < main.CLAW_ATTACK + 26:
        main.update(app, 0, 0)
    assert app["shatter"]["sparks"] == []  # burnt out long before the screen has fallen apart


def test_a_second_defeat_starts_the_claw_from_scratch(app):
    caught_both(app)
    for _ in range(main.CLAW_ATTACK + 2):
        main.update(app, 0, 0)
    assert app["shatter"]["sparks"]
    main.open_main_menu(app)
    assert app["shatter"] is None
    caught_both(app)  # another game, lost again
    assert app["shatter"]["age"] == 1 and app["shatter"]["sparks"] == []
    assert main.claw_pose(app["shatter"]["age"])["shadow"] > 0.9  # the claw is high above the screen again


def test_the_cracked_screen_shakes_hard_at_the_hit(app):
    caught_both(app)
    for _ in range(main.CLAW_ATTACK):
        main.update(app, 0, 0)
    frozen = app["shatter"]["frozen"]
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    moved = 0
    for _ in range(main.CLAW_FLASH, main.CLAW_IMPACT - main.CLAW_ATTACK - 1):
        while app["shatter"]["age"] < main.CLAW_ATTACK + main.CLAW_FLASH:
            main.update(app, 0, 0)
        main.draw(app, screen)
        corner = (8, main.HEIGHT - 20)
        moved += any(screen.get_at((corner[0] + dx, corner[1] + dy)) == frozen.get_at(corner) and (dx, dy) != (0, 0)
                     for dx in range(-main.CLAW_SHAKE, main.CLAW_SHAKE + 1) for dy in range(-main.CLAW_SHAKE, main.CLAW_SHAKE + 1))
        main.update(app, 0, 0)
    assert moved >= 3


def test_no_key_does_anything_while_the_claw_breaks_the_screen(app):
    caught_both(app)
    age = app["shatter"]["age"]
    for key in (pygame.K_ESCAPE, pygame.K_e, pygame.K_RETURN, pygame.K_i, pygame.K_q, pygame.K_SPACE):
        press(app, key)
        assert app["scene"] == "shatter" and app["shatter"]["age"] == age
    main.update(app, 1, 0, True)
    assert app["shatter"]["age"] == age + 1
    assert engine.restore_state(save.load_game())["ending"] == "caught"  # the ending is already saved


def test_after_the_claw_a_new_game_starts_clean(app):
    caught_both(app)
    for _ in range(main.SHATTER_FRAMES):
        main.update(app, 0, 0)
    assert app["scene"] == "ending" and app["shatter"] is None
    press(app, pygame.K_RETURN, pygame.K_UP, pygame.K_RETURN, pygame.K_RETURN, pygame.K_RETURN)  # New game, Yes, 1 player, wizard
    read_all(app)
    assert app["scene"] == "play" and app["state"]["ending"] is None
    assert app["shatter"] is None and app["crumble"] == 0 and app["crab"] is None and app["downed"] == {}
    start = p1(app)["pos"]
    main.update(app, 1, 0)
    assert p1(app)["pos"][0] > start[0]  # playing again, nothing in the way
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    main.draw(app, screen)


def test_leaving_in_the_middle_of_the_sequence_leaves_nothing_behind(app):
    caught_both(app)
    for _ in range(30):
        main.update(app, 0, 0)
    main.open_main_menu(app)
    assert app["scene"] == "menu" and app["shatter"] is None
    main.update(app, 0, 0)
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))
    again = relaunch()
    press(again, pygame.K_DOWN, pygame.K_RETURN)  # "Resume": straight to the ending, no claw again
    assert again["scene"] == "ending" and again["shatter"] is None


def test_without_the_effect_the_text_comes_first_as_before(app, heard, monkeypatch):
    monkeypatch.setitem(effects.FX, "shatter", False)
    two_playing(app, FIRST_HALF)
    awake_crab(app)
    app["downed"] = {2: main.DOWN_FRAMES}
    app["players"][1]["pos"] = free_spot(app, 14, 3)
    p1(app)["pos"] = app["crab"]["pos"]
    main.update(app, 0, 0)
    assert app["scene"] == "play" and app["shatter"] is None
    assert dialog_text(app) == story.MESSAGES["crab_ending"] and "knocked_out" in heard
    read_all(app)
    main.update(app, 0, 0)
    assert app["scene"] == "ending"


def test_the_sequence_is_drawn_on_the_small_screen_whatever_the_size_of_the_window(app):
    caught_both(app)
    small = pygame.Surface((main.WIDTH, main.HEIGHT))
    pygame.display.set_mode((1, 1))
    for size in ((main.WIDTH * main.SCALE, main.HEIGHT * main.SCALE), (1920, 1080), (1366, 768)):
        window = pygame.Surface(size)
        for age in (5, main.CLAW_ATTACK + 4, main.CLAW_IMPACT + 20):
            app["shatter"]["age"] = age
            main.draw(app, small)
            main.show(small, window)
            area = main.picture_area(size)
            zoom = area.width // main.WIDTH
            for x, y in ((10, 200), (128, 112), (240, 40)):
                assert window.get_at((area.left + x * zoom + zoom // 2, area.top + y * zoom + zoom // 2)) == small.get_at((x, y))


def test_both_computers_see_the_claw_and_then_the_ending(two_computers, heard):
    host, guest = two_computers
    state = play_two(FIRST_HALF)
    host["state"], guest["state"] = state, engine.restore_state(state)
    for app in (host, guest):
        main.place_at_entry(app)
        main.reset_crab(app)
    pump(host, guest, lambda: guest["crab"] is not None)
    host["crab"]["wait"] = 0
    host["crumble"] = guest["crumble"] = 0
    host["downed"] = {2: main.DOWN_FRAMES}  # the guest is down, and the crab gets the host
    mine(host)["pos"] = host["crab"]["pos"]
    pump(host, guest, lambda: host["scene"] == "shatter" and guest["scene"] == "shatter")
    assert guest["shatter"]["frozen"].get_size() == (main.WIDTH, main.HEIGHT)
    main.draw(guest, pygame.Surface((main.WIDTH, main.HEIGHT)))
    pump(host, guest, lambda: host["scene"] == "ending" and guest["scene"] == "ending")
    assert guest["state"]["ending"] == "caught" and guest["shatter"] is None and host["shatter"] is None


# --- Dark rooms, and the light in them --------------------------------------------------------


DARK_ROOMS = {"corridor", "corridor_end", "mine"}


def in_the_dark(app, room, tile=None, facing=(0, 1)):
    """A game alone, moved to a room, the player on a free tile, looking one way. A few frames have passed."""
    start_new_game(app)
    state = play(BOTH_HALVES)
    state["room"] = room
    app["state"] = state
    p1(app)["pos"] = free_spot(app, *tile) if tile else main.spawn_at_entry(room)
    p1(app)["facing"] = facing
    for _ in range(3):
        main.update(app, 0, 0)
    app["fade"] = 0
    app["banner_frames"] = 0


def lights(app):
    state = main.view(app)
    return main.room_lights(app, state, engine.things_here(state))


def room_picture(app):
    """The whole room as it is drawn now, in room pixels."""
    surface = pygame.Surface(main.room_surface(main.view(app)["room"]).get_size())
    main.draw_room(app, surface)
    return surface


def brightness(color):
    return sum(tuple(color)[:3])


def test_the_rooms_under_the_hold_are_dark_and_the_others_are_not():
    assert {room for room, info in story.ROOMS.items() if info.get("dark")} == DARK_ROOMS
    for room in DARK_ROOMS:
        assert 100 <= story.ROOMS[room]["dark"] < 255 and main.room_darkness(room) == story.ROOMS[room]["dark"]
    assert story.ROOMS["mine"]["dark"] > story.ROOMS["corridor"]["dark"]  # the deepest, the darkest
    assert main.room_darkness("deck") == 0 and main.room_darkness("cabin") == 0


def test_a_dark_room_is_dark_but_for_the_light_around_the_player(app, monkeypatch):
    in_the_dark(app, "mine", (7, 12), (1, 0))
    dark = room_picture(app)
    monkeypatch.setitem(effects.FX, "darkness", False)
    lit = room_picture(app)
    monkeypatch.setitem(effects.FX, "darkness", True)
    x, y = main.player_rect(p1(app)["pos"]).center
    floor = main.floor_rect("mine")
    spots = [(fx, fy) for fx in range(floor.left + 4, floor.right - 4, 6) for fy in range(floor.top + 4, floor.bottom - 4, 6)]
    far = max(spots, key=lambda spot: min(pygame.Vector2(spot).distance_to(light[1]) for light in lights(app)))
    assert min(pygame.Vector2(far).distance_to(light[1]) for light in lights(app)) > 50  # nothing gives light there
    assert brightness(dark.get_at(far)) < brightness(lit.get_at(far)) * 0.6  # much darker
    assert brightness(dark.get_at((x, y + 9))) >= brightness(lit.get_at((x, y + 9)))  # at the player's feet: as lit
    ahead, behind = (x + 34, y + 3), (x - 34, y + 3)
    assert brightness(dark.get_at(ahead)) > brightness(dark.get_at(behind))  # the cone in front, the dark behind
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))


def test_the_cone_of_a_player_points_the_way_they_face(app):
    in_the_dark(app, "mine", (7, 12))
    middle = main.player_rect(p1(app)["pos"]).center
    for facing, angle in (((1, 0), 0), ((0, 1), 90), ((-1, 0), 180), ((0, -1), -90)):
        p1(app)["facing"] = facing
        mine_lights = [light for light in lights(app) if light[1] == middle]
        assert ("glow", middle, main.PLAYER_LIGHT) in mine_lights
        assert ("cone", middle, angle, main.PLAYER_CONE[0], main.PLAYER_CONE[1]) in mine_lights
    start = p1(app)["pos"]
    main.update(app, -1, 0)  # walking left: the light goes with the player, and turns
    moved = main.player_rect(p1(app)["pos"]).center
    assert moved != middle and ("cone", moved, 180, main.PLAYER_CONE[0], main.PLAYER_CONE[1]) in lights(app)


def test_lanterns_throw_a_glow_and_a_cone_down_that_sways_with_them(app):
    in_the_dark(app, "mine")
    lanterns = [name for name, info in story.OBJECTS.items() if info["room"] == "mine" and info.get("picture") == "decor_lantern"]
    assert len(lanterns) == 3
    cones = [light for light in lights(app) if light[0] == "cone" and light[3] == main.LANTERN_CONE[0]]
    glows = [light for light in lights(app) if light[0] == "glow" and light[2] >= main.LANTERN_LIGHT]
    assert len(cones) == 3 and len(glows) == 3
    for cone in cones:
        assert abs(cone[2] - 90) <= effects.LANTERN_SWING  # downwards, a little to one side or the other
        assert any(glow[1] == cone[1] for glow in glows)   # from the flame
    angles, sizes = set(), set()
    for _ in range(200):
        main.update(app, 0, 0)
        angles |= {light[2] for light in lights(app) if light[0] == "cone" and light[3] == main.LANTERN_CONE[0]}
        sizes |= {light[2] for light in lights(app) if light[0] == "glow" and light[2] >= main.LANTERN_LIGHT}
    assert len(angles) >= 5 and min(angles) < 90 < max(angles)  # it sways
    assert sizes == {main.LANTERN_LIGHT, main.LANTERN_LIGHT + 2}  # and the flame jumps


def test_crystals_portals_and_the_heart_glow(app):
    in_the_dark(app, "mine")
    centers = {light[1]: light[2] for light in lights(app) if light[0] == "glow"}
    crystals = [name for name, info in story.OBJECTS.items() if info["room"] == "mine" and info.get("picture") == "decor_crystal"]
    portals = [name for name, info in story.OBJECTS.items() if info["room"] == "mine" and info["kind"] == "portal"]
    assert len(crystals) == 4 and len(portals) == 2
    for crystal in crystals:
        assert main.CRYSTAL_LIGHT[0] <= centers[main.thing_rect(crystal).center] <= main.CRYSTAL_LIGHT[1]
    for portal in portals:
        assert centers[main.thing_rect(portal).center] in (main.PORTAL_LIGHT, main.PORTAL_LIGHT + 1)
    heart = main.thing_rect("heart").center
    assert main.HEART_LIGHT[0] <= centers[heart] <= main.HEART_LIGHT[1]
    seen = {name: set() for name in crystals + ["heart"]}
    for _ in range(160):
        main.update(app, 0, 0)
        now = {light[1]: light[2] for light in lights(app) if light[0] == "glow"}
        for name in seen:
            seen[name].add(now[main.thing_rect(name).center])
    assert all(len(sizes) >= 3 for sizes in seen.values())  # they pulse
    stand_next_to(app, "heart")
    press(app, pygame.K_e)  # picked up: used, gone, and its light with it
    read_all(app)
    p1(app)["pos"] = main.spawn_at_entry("mine")  # away from where it was
    assert heart not in {light[1] for light in lights(app)}


def test_only_players_in_the_room_and_in_the_game_give_light(app):
    two_playing(app, FIRST_HALF)
    app["state"]["room"] = "mine"
    app["state"]["flags"]["partner_room"] = "mine"
    main.place_at_entry(app)
    main.update(app, 0, 0)

    def cones():
        return [light for light in lights(app) if light[0] == "cone" and light[3] == main.PLAYER_CONE[0]]
    assert len(cones()) == 2  # each with their own
    partner = main.player_rect(app["players"][1]["pos"]).center
    app["downed"] = {2: main.DOWN_FRAMES}
    assert len(cones()) == 1 and ("glow", partner, main.DOWNED_LIGHT) in lights(app)  # down: a small glow only
    app["downed"] = {}
    app["state"]["flags"]["partner_room"] = "deck"
    assert len(cones()) == 1 and partner not in {light[1] for light in lights(app)}  # elsewhere: no light here
    app["state"]["flags"]["partner_room"] = "mine"
    app["state"] = engine.knock_out(app["state"], 2)[0]
    assert len(cones()) == 1  # out of the game: gone
    main.draw(app, pygame.Surface((main.WIDTH, main.HEIGHT)))


def test_a_lit_room_is_drawn_exactly_as_before(app, monkeypatch):
    start_new_game(app)
    playing(app, IN_THE_CABIN)
    main.update(app, 0, 0)
    with_it = room_picture(app)
    monkeypatch.setitem(effects.FX, "darkness", False)
    without = room_picture(app)
    size = with_it.get_size()
    assert all(with_it.get_at((x, y)) == without.get_at((x, y)) for x in range(0, size[0], 3) for y in range(0, size[1], 3))


def test_without_the_effect_the_dark_rooms_are_lit_as_before(app, monkeypatch):
    monkeypatch.setitem(effects.FX, "darkness", False)
    in_the_dark(app, "corridor")
    assert main.room_darkness("corridor") == 0
    calls = []
    monkeypatch.setattr(effects, "darkness", lambda size, dark: calls.append(size))
    room_picture(app)
    assert calls == []


def test_every_dark_room_can_be_walked_and_drawn(app):
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    for room in sorted(DARK_ROOMS):
        in_the_dark(app, room)
        for direction in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            for _ in range(12):
                main.update(app, *direction)
                main.draw(app, screen)
        assert len(lights(app)) >= 4, room  # never left in the dark: lanterns and the player at least
