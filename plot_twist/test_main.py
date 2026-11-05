"""Tests for main.py: the room layout, walking through doors, the menus and saving, without a window.

They drive the interface the way the main loop does: handle_key() for a key
press, update() once per frame with the direction held. conftest.py keeps the
save file in a temporary folder.
"""

import collections

import pygame
import pytest

import engine
import main
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
                               act("enter", "deck_to_cabin"), act("enter", "cabin_to_galley"),
                               act("use_item", "anvil", "second_key"),
                               act("enter", "galley_to_cabin"), act("enter", "cabin_to_deck")]  # back on the deck
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
    assert main.menu_entries(app) == ["new_game", "quit"]
    start_new_game(app)
    assert main.menu_entries(relaunch()) == ["new_game", "resume", "quit"]


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
    press(again, pygame.K_RETURN)  # "Nuova partita"
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
    press(again, pygame.K_RETURN)  # "Nuova partita"
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
    walk_into(app, "cabin_to_galley")
    stand_next_to(app, "anvil")
    press(app, pygame.K_e)
    choose_in_menu(app, "use_item", "key")  # either half fuses both
    assert dialog_text(app) == story.OBJECTS["anvil"]["fuse_text"]
    read_all(app)
    walk_into(app, "galley_to_cabin")
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


def test_new_game_lets_the_player_choose_the_red_character(app):
    """Right, then Enter: the game starts with the red character, saved, and Resume keeps it."""
    press(app, pygame.K_RETURN, pygame.K_RETURN)  # "New game", "1 player"
    assert app["scene"] == "character" and main.character_entries()[app["menu_index"]] == "green"
    press(app, pygame.K_RIGHT)
    assert main.character_entries()[app["menu_index"]] == "red"
    press(app, pygame.K_RETURN)
    assert app["scene"] == "play"
    assert app["state"]["flags"]["character"] == "red"
    assert main.player_picture(app, p1(app)) is sprites.image("player_red_down_0")
    assert engine.restore_state(save.load_game())["flags"]["character"] == "red"
    again = relaunch()
    press(again, pygame.K_DOWN, pygame.K_RETURN)  # "Resume"
    assert main.player_picture(again, p1(again)) is sprites.image("player_red_down_0")


def test_the_choice_wraps_around_and_esc_goes_back(app):
    press(app, pygame.K_RETURN, pygame.K_RETURN)  # "New game", "1 player"
    press(app, pygame.K_LEFT)  # from the first, left goes round to the last
    assert main.character_entries()[app["menu_index"]] == "red"
    press(app, pygame.K_d)  # WASD works too
    assert main.character_entries()[app["menu_index"]] == "green"
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
    assert app["scene"] == "play" and app["state"]["flags"]["character"] == "red"


def test_the_two_characters_differ_only_in_the_shirt():
    """Every picture of the red character is the green one with red where the shirt is green."""
    for name, rows in sprites.SPRITES.items():
        if name.startswith("player_") and not name.startswith("player_red_"):
            red = sprites.SPRITES["player_red_" + name[len("player_"):]]
            for row, red_row in zip(rows, red):
                for letter, red_letter in zip(row, red_row):
                    expected = {"g": "r", "G": "R"}.get(letter, letter)
                    assert red_letter == expected, name


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


def test_the_second_direction_of_update_changes_nothing_yet(app):
    """update takes a direction for a second player, but with one player it is ignored."""
    start_new_game(app)
    still, pushed = main.new_app(main.load_fonts()), main.new_app(main.load_fonts())
    for other in (still, pushed):
        press(other, pygame.K_RETURN, pygame.K_RETURN, pygame.K_RETURN)
        read_all(other)
    for _ in range(60):
        main.update(still, 1, 0)
        main.update(pushed, 1, 0, -1, 1)
    assert p1(still) == p1(pushed)
    assert still["state"] == pushed["state"]


# --- Two players (step 2: two players, for now the one who goes through a door takes the other) ---


def start_two_players(app, character_keys=()):
    """New game, "2 players", then the character of player 1 (the first, or as the keys say)."""
    press(app, pygame.K_RETURN, pygame.K_DOWN, pygame.K_RETURN, *character_keys, pygame.K_RETURN)
    read_all(app)


def p2(app):
    return app["players"][1]


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


def test_two_players_start_side_by_side_with_their_own_characters(app):
    start_two_players(app, (pygame.K_RIGHT,))  # player 1 takes the red one
    state = app["state"]
    assert state["flags"]["two_players"] and len(app["players"]) == 2
    assert engine.restore_state(save.load_game()) == state
    assert p1(app)["pos"] == main.spawn_at_entry("deck")
    assert main.player_rect(p2(app)["pos"]).colliderect(main.player_rect(p1(app)["pos"])) is False
    assert main.player_picture(app, p1(app)) is sprites.image("player_red_down_0")
    assert main.player_picture(app, p2(app)) is sprites.image("player_down_0")  # the partner: green
    again = relaunch()
    press(again, pygame.K_DOWN, pygame.K_RETURN)  # "Resume": two players again
    assert len(again["players"]) == 2


def test_one_player_keeps_the_keys_of_always():
    assert main.KEYS_1P[0]["act"] == (pygame.K_e,) and main.KEYS_1P[0]["inventory"] == (pygame.K_i,)
    both = collections.defaultdict(bool, {pygame.K_UP: True, pygame.K_d: True})
    assert main.held_direction(both) == (1, -1)  # arrows and WASD move the one player
    assert main.held_direction(both, main.KEYS_1P[0]) == (1, -1)


def test_two_players_have_their_own_keys():
    one, two = main.KEYS_2P
    pressed = collections.defaultdict(bool, {pygame.K_w: True, pygame.K_RIGHT: True})
    assert main.held_direction(pressed, one) == (0, -1)  # WASD: player 1
    assert main.held_direction(pressed, two) == (1, 0)   # arrows: player 2
    assert one["act"] == (pygame.K_e,) and one["inventory"] == (pygame.K_q,)
    assert two["act"] == (pygame.K_RSHIFT,) and two["inventory"] == (pygame.K_p,)


def test_in_two_players_each_action_key_acts_for_its_player(app):
    start_two_players(app)
    stand_next_to(app, "wand")  # player 1 on the wand, player 2 far away
    p2(app)["pos"] = main.spawn_at_entry("deck")
    press(app, pygame.K_RSHIFT)  # player 2 acts: nothing near them
    assert app["dialog"] == [] and app["state"]["inventory"] == []
    p2(app)["pos"], p1(app)["pos"] = p1(app)["pos"], main.spawn_at_entry("deck")
    press(app, pygame.K_e)  # player 1 acts: nothing near them either
    assert app["state"]["inventory"] == []
    press(app, pygame.K_RSHIFT)  # player 2 on the wand
    assert app["state"]["inventory"] == ["wand"]
    read_all(app)  # the text box turns with anyone's key
    for key, other in ((pygame.K_q, pygame.K_p), (pygame.K_p, pygame.K_q)):
        press(app, key)
        assert app["scene"] == "inventory"
        press(app, other)  # anyone's inventory key closes it
        assert app["scene"] == "play"
    press(app, pygame.K_i)  # I is only for one player
    assert app["scene"] == "play"


def test_menus_take_everyones_keys(app):
    start_two_players(app)
    press(app, pygame.K_ESCAPE)
    assert app["scene"] == "pause"
    press(app, pygame.K_RSHIFT)  # player 2's action key chooses "Continue"
    assert app["scene"] == "play"


def test_each_player_moves_with_their_own_direction_through_each_other(app):
    start_two_players(app)
    start_one, start_two = p1(app)["pos"], p2(app)["pos"]
    for _ in range(20):
        main.update(app, 0, 1, 0, -1)  # player 1 down, player 2 up
    assert p1(app)["pos"][1] > start_one[1] and p2(app)["pos"][1] < start_two[1]
    p2(app)["pos"] = p1(app)["pos"]
    for _ in range(20):
        main.update(app, 1, 0, -1, 0)  # straight through each other: they do not block
    assert p1(app)["pos"][0] > p2(app)["pos"][0] + 40


def walk_both(app, first, second, frames=40, until=None):
    """Hold a direction for each player, frame by frame, until `until(app)` is true (or the frames run out)."""
    for _ in range(frames):
        if until is not None and until(app):
            return
        main.update(app, *first, *second)


def at_door(app, player, door):
    player["pos"] = main.spawn_in_front_of(door)
    player["touching"] = None


def test_one_player_at_a_door_waits_for_the_partner(app):
    """Alone at the door the room does not change; the banner says to wait, once for each contact."""
    start_two_players(app)
    at_door(app, p1(app), "deck_to_cabin")
    walk_both(app, (0, -1), (0, 0))
    assert app["state"]["room"] == "deck"
    assert app["banner"] == story.MESSAGES["wait_partner"] and app["banner_frames"] > 0
    assert p1(app)["touching"] == "deck_to_cabin"
    assert main.tile_rect(0, 0, *main.room_size("deck")).contains(main.player_rect(p1(app)["pos"]))  # still on board
    app["banner_frames"] = 0
    walk_both(app, (0, -1), (0, 0))  # still there, still pushing: no new banner
    assert app["banner_frames"] == 0
    walk_both(app, (0, 1), (0, 0), until=lambda app: p1(app)["touching"] is None)  # stepping back out of the door...
    walk_both(app, (0, -1), (0, 0))  # ...and in again: a new contact, a new banner
    assert app["banner_frames"] > 0 and app["state"]["room"] == "deck"


def test_both_players_at_the_same_door_go_through_side_by_side(app):
    start_two_players(app)
    at_door(app, p1(app), "deck_to_cabin")
    walk_both(app, (0, -1), (0, 0))  # player 1 waits in the door
    at_door(app, p2(app), "deck_to_cabin")
    walk_both(app, (0, -1), (0, -1), until=lambda app: app["state"]["room"] == "cabin")
    assert app["state"]["room"] == "cabin"
    assert [p1(app)["pos"], p2(app)["pos"]] == main.door_arrivals(app["state"], "cabin_to_deck")
    assert p1(app)["pos"] == main.spawn_in_front_of("cabin_to_deck")  # where a player alone appears


def test_players_at_two_different_doors_stay(app):
    start_two_players(app)
    at_door(app, p1(app), "deck_to_cabin")
    at_door(app, p2(app), "deck_to_hold")
    walk_both(app, (0, -1), (0, 1))
    assert app["state"]["room"] == "deck"


def test_both_players_in_the_portal_travel_side_by_side(app):
    start_two_players(app)
    app["state"]["room"] = "corridor_end"
    ring = main.thing_rect("corridor_portal")
    below = (ring.centerx - main.PLAYER_SIZE // 2, ring.bottom + 2)
    p1(app)["pos"], p2(app)["pos"] = below, (main.spawn_at_entry("corridor_end")[0] + 40, below[1] + 30)
    for player in app["players"]:
        player["touching"] = None
    walk_both(app, (0, -1), (0, 0), until=lambda app: p1(app)["touching"] == "corridor_portal")  # player 1 alone in the ring
    walk_both(app, (0, 0), (0, 0), frames=10)  # and waiting there
    assert app["state"]["room"] == "corridor_end" and app["banner"] == story.MESSAGES["wait_partner"]
    p2(app)["pos"] = below
    walk_both(app, (0, 0), (0, -1), until=lambda app: app["state"]["room"] == "mine")
    assert app["state"]["room"] == "mine"
    assert [p1(app)["pos"], p2(app)["pos"]] == main.portal_arrivals(app["state"], "mine_portal")


def test_the_helm_portal_does_not_ask_to_wait(app):
    """The ring in the helm only receives: standing in it is not waiting for anyone."""
    start_two_players(app)
    app["state"]["room"] = "helm"
    ring = main.thing_rect("helm_portal")
    p1(app)["pos"] = (ring.centerx - main.PLAYER_SIZE // 2, ring.centery - main.PLAYER_SIZE // 2)
    app["banner_frames"] = 0
    walk_both(app, (0, 0), (0, 0), frames=5)
    assert app["banner_frames"] == 0 and app["state"]["room"] == "helm"


def test_arrivals_are_free_floor_side_by_side_for_every_door_and_portal():
    for door, info in story.DOORS.items():
        state = in_room(info["room"])
        first, second = main.door_arrivals(state, door)
        assert first == main.spawn_in_front_of(door), door
        for spot in (first, second):
            assert main.is_free_floor(state, spot), (door, spot)
        assert not main.player_rect(first).colliderect(main.player_rect(second)), door
    for portal, info in story.OBJECTS.items():
        if info["kind"] == "portal":
            state = in_room(info["room"])
            first, second = main.portal_arrivals(state, portal)
            assert first == main.spawn_by_portal(portal), portal
            for spot in (first, second):
                assert main.is_free_floor(state, spot), (portal, spot)
            assert not main.player_rect(first).colliderect(main.player_rect(second)), portal


def test_the_tiles_start_over_only_when_both_players_are_out_of_the_zone(app, heard):
    start_two_players(app)
    app["state"] = play(IN_THE_HOLD)
    app["state"]["flags"]["two_players"] = True
    app["state"]["flags"]["partner_room"] = "hold"  # player 2 is in the hold too
    main.place_at_entry(app)
    walk_onto(app, "tile_1")  # player 1 lights tile 1 (player 2 stands still)
    assert app["state"]["flags"]["hold_step"] == 1
    zone = main.zone_rect("hold_tiles")
    tile_2 = main.thing_rect("tile_2")
    p2(app)["pos"] = (tile_2.centerx - main.PLAYER_SIZE // 2, tile_2.top - main.TILE // 2 - main.PLAYER_SIZE // 2)
    main.settle_on_floor(app, p2(app))  # player 2 is in the zone too, above tile 2
    walk_both(app, (0, 1), (0, 1), until=lambda app: app["state"]["flags"]["hold_step"] == 2)
    assert app["state"]["flags"]["hold_step"] == 2  # player 2 stepped on tile 2: any player lights tiles
    walk_both(app, (0, -1), (0, 0), frames=60)  # player 1 walks out of the zone, player 2 stays in it
    assert not zone.collidepoint(main.player_rect(p1(app)["pos"]).center)
    assert app["state"]["flags"]["hold_step"] == 2 and "buzz" not in heard
    walk_both(app, (0, 0), (0, -1), frames=60)  # now player 2 walks out too
    assert app["state"]["flags"]["hold_step"] == 0 and heard[-1] == "buzz"


def test_player_two_appears_on_free_floor_in_every_room(app):
    start_two_players(app)
    for room in story.ROOMS:
        app["state"] = in_room(room)
        app["state"]["flags"]["two_players"] = True
        main.place_at_entry(app)
        one, two = main.player_rect(p1(app)["pos"]), main.player_rect(p2(app)["pos"])
        assert main.is_free_floor(app["state"], p2(app)["pos"]), room
        assert not one.colliderect(two), room
        assert abs(one.centerx - two.centerx) == main.PLAYER_SIZE + 2 and one.y == two.y, room


def test_the_lower_player_is_drawn_in_front(app):
    """Two players on the same spot, one a little lower: the lower one covers the other."""
    start_two_players(app, (pygame.K_RIGHT,))  # player 1 red, player 2 green
    app["fade"] = 0
    x, y = main.tile_rect(4, 8).topleft
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))

    def shirt_color(lower):
        p1(app)["pos"], p2(app)["pos"] = (x, y + 6), (x, y)
        if lower == "p2":
            p1(app)["pos"], p2(app)["pos"] = (x, y), (x, y + 6)
        for one in app["players"]:
            one["facing"], one["moving"] = (0, 1), False
        main.draw(app, screen)
        cam_x, cam_y = main.camera("deck", main.view_position(app))
        front = p1(app) if lower == "p1" else p2(app)
        body = main.player_rect(front["pos"])
        return tuple(screen.get_at((body.centerx - cam_x, body.bottom + 1 - 5 - cam_y)))[:3]
    assert shirt_color("p1") == sprites.PALETTE["r"]  # player 1, red, in front
    assert shirt_color("p2") == sprites.PALETTE["g"]  # player 2, green, in front


def test_e_near_the_partner_offers_to_give_and_each_sees_their_own_items(app):
    start_two_players(app)
    stand_next_to(app, "wand")
    press(app, pygame.K_e)  # player 1 picks up the wand
    read_all(app)
    assert engine.carries(app["state"], "wand", 1)
    p2(app)["pos"] = (p1(app)["pos"][0] + main.PLAYER_SIZE + 2, p1(app)["pos"][1])
    press(app, pygame.K_e)  # next to player 2: the only thing E offers is to give the wand
    assert dialog_text(app) == story.MESSAGES["given"].format(item=story.ITEMS["wand"]["name"])
    read_all(app)
    assert engine.carries(app["state"], "wand", 2)
    assert engine.restore_state(save.load_game()) == app["state"]
    assert main.item_lines(app["state"], 1) == [("text", story.MESSAGES["inventory_empty"])]
    assert main.item_lines(app["state"], 2)[0] == ("name", story.ITEMS["wand"]["name"])
    press(app, pygame.K_p)  # player 2's inventory
    assert app["scene"] == "inventory" and app["inventory_player"] == 2
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    main.draw(app, screen)


def test_alone_there_is_no_partner_to_give_to(app):
    start_new_game(app)
    stand_next_to(app, "wand")
    press(app, pygame.K_e)
    read_all(app)
    assert main.give_actions(app, p1(app)) == []
