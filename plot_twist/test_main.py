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



def act(verb, target, item=None):
    return {"verb": verb, "target": target, "item": item}


# The crab's path, from a new game to its ending, in stages.
IN_THE_CABIN = [act("pick_up", "wand"), act("enter", "deck_to_cabin")]  # with the wand, the barrier up
CIRCUIT_COMPLETE = IN_THE_CABIN + [act("activate", "generator_a"), act("activate", "generator_d")]
FIRST_HALF = CIRCUIT_COMPLETE + [act("pick_up", "key"), act("enter", "cabin_to_deck")]  # back on the deck
IN_THE_HOLD = FIRST_HALF + [act("enter", "deck_to_hold")]
TILE_SEQUENCE = ["tile_1", "tile_2", "tile_3", "tile_4", "tile_5", "tile_3", "tile_1", "tile_5", "tile_2", "tile_4", "tile_3"]
TILES_SOLVED = IN_THE_HOLD + [act("step_on", tile) for tile in TILE_SEQUENCE]
BOTH_HALVES = TILES_SOLVED + [act("pick_up", "second_key")]  # in the hold, not fused yet
KEY_FUSED = BOTH_HALVES + [act("use_item", "anvil", "second_key"), act("enter", "hold_to_deck")]  # back on the deck
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
    """Choose "Nuova partita" on a menu without saves, and read the opening scene."""
    press(app, pygame.K_RETURN)
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
    app["player"] = (body.x, body.y)
    app["touching"] = None


def walk_until(app, arrived, direction, limit=300):
    """Hold the direction that direction(x, y) gives, frame by frame, until arrived(x, y) is true.

    (x, y) is the middle of the player's body. Fails instead of walking forever.
    """
    for _ in range(limit):
        x, y = main.player_rect(app["player"]).center
        if arrived(x, y):
            return
        main.update(app, *direction(x, y))
    raise AssertionError(f"the player never arrived; now at {app['player']}")


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
    app["player"] = main.spawn_in_front_of(door)
    app["touching"] = None
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


def on_the_floor(tile):
    col, row = tile
    return 1 <= col <= main.COLUMNS - 2 and 1 <= row <= main.ROWS - 2


def test_layout_everything_stands_on_the_floor():
    for room_id, room in story.ROOMS.items():
        assert on_the_floor(room["entry"]), room_id
    for thing_id, info in list(story.ITEMS.items()) + list(story.OBJECTS.items()):
        if info["room"] is None:
            continue  # made at the anvil: it never lies anywhere
        assert on_the_floor(info["pos"]), thing_id
        width, height = info.get("size", (1, 1))
        last_tile = (info["pos"][0] + width - 1, info["pos"][1] + height - 1)
        assert on_the_floor(last_tile), thing_id


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
    for x in range(main.TILE, main.WIDTH - main.TILE, 2):
        for y in range(main.HUD_HEIGHT + main.TILE, main.HEIGHT - main.TILE, 2):
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


def test_layout_each_wall_has_at_most_one_door():
    for room in story.ROOMS:
        sides = [story.DOORS[door]["side"] for door in main.doors_in(room)]
        assert len(sides) == len(set(sides)), room


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


# --- Room geometry ------------------------------------------------------------------


def test_doors_are_in_the_middle_of_their_wall():
    for door_id, door in story.DOORS.items():
        rect = main.door_rect(door_id)
        if door["side"] in ("N", "S"):
            assert rect.centerx == main.WIDTH // 2, door_id
        else:
            assert rect.centery == main.HUD_HEIGHT + main.ROWS * main.TILE // 2, door_id


def test_walls_close_the_room_except_at_the_doors():
    """Every tile of the border is wall or door, and no wall covers a door."""
    for room in story.ROOMS:
        walls = main.wall_rects(room)
        openings = [main.door_rect(door) for door in main.doors_in(room)]
        for opening in openings:
            assert opening.collidelist(walls) == -1, room
        for col in range(main.COLUMNS):
            for row in range(main.ROWS):
                if col in (0, main.COLUMNS - 1) or row in (0, main.ROWS - 1):
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
    room_area = main.tile_rect(0, 0, main.COLUMNS, main.ROWS)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            app["state"] = engine.new_game()
            app["player"] = main.spawn_at_entry("deck")
            app["touching"] = None
            for _ in range(300):
                main.update(app, dx, dy)
                read_all(app)
                rect = main.player_rect(app["player"])
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
            assert app["player"] == main.spawn_in_front_of(main.return_door(room, came_from))
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
    app["player"] = (main.tile_rect(1, 1).x, main.tile_rect(1, 1).y)  # top-left corner, against the top wall
    for _ in range(150):
        main.update(app, 1, 0)  # walk right, past the cabin door
    assert app["state"]["room"] == "deck"
    assert main.player_rect(app["player"]).left > main.door_rect("deck_to_cabin").right


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
    press(app, pygame.K_RETURN)  # the opening scene is on screen
    before = app["player"]
    for _ in range(30):
        main.update(app, 1, 0)
    assert app["player"] == before
    read_all(app)
    for _ in range(30):
        main.update(app, 1, 0)
    assert app["player"] != before


# --- Menus and saving (PT01, PT05, A6) -------------------------------------------------


def test_menu_offers_resume_only_when_a_game_is_saved(app):
    assert main.menu_entries(app) == ["new_game", "quit"]
    start_new_game(app)
    assert main.menu_entries(relaunch()) == ["new_game", "resume", "quit"]


def test_new_game_shows_the_opening_scene_and_saves_at_once(app):
    press(app, pygame.K_RETURN)
    assert app["scene"] == "play"
    assert dialog_text(app) == story.MESSAGES["intro"]
    assert app["player"] == main.spawn_at_entry(story.START_ROOM)
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
    assert again["player"] == main.spawn_at_entry("cabin")


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
    press(again, pygame.K_RETURN, pygame.K_UP, pygame.K_RETURN)  # "Nuova partita", then "Sì"
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
    press(app, pygame.K_RETURN)
    assert app["scene"] == "play"
    assert story.MESSAGES["save_failed"] in dialog_text(app)


# --- Acting with E, the inventory and the endings (M4) -----------------------------------


def test_prompt_says_what_e_does_here():
    """PT02: the bar at the top shows the action E would do, or the name of the thing if there are several."""
    def hint(action):
        return story.MESSAGES["prompt"].format(action=action)

    state = engine.new_game()
    assert main.prompt(state, main.spawn_at_entry("deck")) == hint(story.MESSAGES["label_look_around"])
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
    """In the corner between generator A and the barrier both are in reach: E picks the closer generator.

    On the very same tile, the key lying on the altar comes before the altar itself.
    """
    state = play(IN_THE_CABIN)  # with the wand, the barrier still up
    generator, barrier = main.thing_rect("generator_a"), main.thing_rect("barrier")
    body = pygame.Rect(0, 0, main.PLAYER_SIZE, main.PLAYER_SIZE)
    body.bottomleft = (generator.right + 2, generator.top - 2)
    reach = body.inflate(2 * main.REACH, 2 * main.REACH)
    assert reach.colliderect(generator) and reach.colliderect(barrier)
    assert main.nearest_target(state, body.topleft) == "generator_a"
    solved = play(CIRCUIT_COMPLETE)  # the key free on the altar
    app["state"] = solved
    stand_next_to(app, "key")
    assert main.nearest_target(solved, app["player"]) == "key"


def test_e_with_nothing_near_describes_the_room(app):
    start_new_game(app)
    press(app, pygame.K_e)
    assert dialog_text(app) == story.ROOMS["deck"]["description"]


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
        app["player"] = main.spawn_in_front_of(door)
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
    app["player"] = main.spawn_in_front_of("deck_to_crab")
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
    for generator in ("generator_a", "generator_d"):
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
    stand_next_to(app, "anvil")
    press(app, pygame.K_e)
    choose_in_menu(app, "use_item", "key")  # either half fuses both
    assert dialog_text(app) == story.OBJECTS["anvil"]["fuse_text"]
    read_all(app)
    walk_into(app, "hold_to_deck")
    app["player"] = main.spawn_in_front_of(door)
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
    app["player"] = (body.x, body.y)
    main.settle_on_floor(app)
    main.update(app, 0, 0)
    assert heard == []
    app["on_tile"] = None  # forget it: the same spot now counts as arriving on the tile
    main.update(app, 0, 0)
    assert heard == ["blip"]


def test_tiles_are_floor_not_things(in_hold):
    """The player walks over the tiles, and E never acts on them: standing on one, E looks around."""
    state = in_hold["state"]
    solids = main.solid_rects(state)
    look_around = story.MESSAGES["prompt"].format(action=story.MESSAGES["label_look_around"])
    for tile in puzzle_tiles("hold_tiles"):
        rect = main.thing_rect(tile)
        assert rect.collidelist(solids) == -1, tile
        on_it = (rect.centerx - main.PLAYER_SIZE // 2, rect.centery - main.PLAYER_SIZE // 2)
        assert main.nearest_target(state, on_it) is None, tile
        assert main.prompt(state, on_it) == look_around, tile


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
    """The events step_on and leave_zone accept each have a sound, and every sound exists."""
    assert set(main.EVENT_SOUNDS) == {"tile_lit", "phase_complete", "tiles_complete", "tiles_reset"}
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
        app["player"] = main.spawn_at_entry(state["room"])
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
