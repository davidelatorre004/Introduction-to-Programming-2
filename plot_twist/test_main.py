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
import story

OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}

# The crab's path, from a new game to its ending.
TO_THE_CRAB_ENDING = [
    {"verb": "pick_up", "target": "wand"},
    {"verb": "enter", "target": "deck_to_cabin"},
    {"verb": "use_item", "target": "cabin_puzzle", "item": "wand"},
    {"verb": "pick_up", "target": "key"},
    {"verb": "enter", "target": "cabin_to_deck"},
    {"verb": "use_item", "target": "deck_to_crab", "item": "key"},
    {"verb": "enter", "target": "deck_to_crab"},
    {"verb": "use_item", "target": "crab", "item": "wand"},
]


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
    """Put the player within reach of a thing: on it if it is an item on the floor, else just below it."""
    rect = main.thing_rect(thing)
    body = pygame.Rect(0, 0, main.PLAYER_SIZE, main.PLAYER_SIZE)
    if thing in story.ITEMS:
        body.center = rect.center
    else:
        body.midtop = (rect.centerx, rect.bottom + 2)
    app["player"] = (body.x, body.y)
    app["touching"] = None


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
        assert outcome["ok"], outcome
    return state


# --- The layout in story.py -------------------------------------------------------


def on_the_floor(tile):
    col, row = tile
    return 1 <= col <= main.COLUMNS - 2 and 1 <= row <= main.ROWS - 2


def test_layout_everything_stands_on_the_floor():
    for room_id, room in story.ROOMS.items():
        assert on_the_floor(room["entry"]), room_id
    for thing_id, info in list(story.ITEMS.items()) + list(story.OBJECTS.items()):
        assert on_the_floor(info["pos"]), thing_id


def test_layout_nothing_shares_a_tile():
    for room in story.ROOMS:
        tiles = [story.ROOMS[room]["entry"]]
        for info in list(story.ITEMS.values()) + list(story.OBJECTS.values()):
            if info["room"] == room:
                tiles.append(info["pos"])
        assert len(tiles) == len(set(tiles)), room


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
    for door, room in [("deck_to_cabin", "cabin"), ("cabin_to_deck", "deck"),
                       ("deck_to_hold", "hold"), ("hold_to_deck", "deck")]:
        came_from = app["state"]["room"]
        walk_into(app, door)
        assert app["state"]["room"] == room
        assert app["player"] == main.spawn_in_front_of(main.return_door(room, came_from))
        assert app["banner"] == story.ROOMS[room]["name"]
        assert engine.restore_state(save.load_game()) == app["state"]


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
    """Close the game in the hold and launch it again: "Riprendi" goes back to the hold's entry."""
    start_new_game(app)
    walk_into(app, "deck_to_hold")
    for _ in range(40):
        main.update(app, 1, 1)
    again = relaunch()
    press(again, pygame.K_DOWN, pygame.K_RETURN)  # "Riprendi"
    assert again["scene"] == "play"
    assert again["state"]["room"] == "hold"
    assert again["player"] == main.spawn_at_entry("hold")


def test_new_game_over_a_save_asks_first(app):
    """A6 on screen: "No" keeps the save as it is; "Sì" replaces it with a new game."""
    start_new_game(app)
    walk_into(app, "deck_to_hold")
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
    with_wand_in_cabin = play(TO_THE_CRAB_ENDING[:2])
    drawer = main.thing_rect("cabin_puzzle")
    below_drawer = (drawer.centerx - main.PLAYER_SIZE // 2, drawer.bottom + 2)
    assert main.prompt(with_wand_in_cabin, below_drawer) == hint(story.OBJECTS["cabin_puzzle"]["name"])


def test_the_nearest_thing_is_the_one_e_acts_on(app):
    """With the open drawer and the key side by side, E picks whichever is closer."""
    state = play(TO_THE_CRAB_ENDING[:3])  # in the cabin, drawer open, key on the floor
    app["state"] = state
    stand_next_to(app, "cabin_puzzle")
    assert main.nearest_target(state, app["player"]) == "cabin_puzzle"
    stand_next_to(app, "key")
    assert main.nearest_target(state, app["player"]) == "key"


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
    stand_next_to(app, "cabin_puzzle")
    press(app, pygame.K_e)
    assert app["scene"] == "actions"
    use_wand = story.MESSAGES["label_use"].format(item=story.ITEMS["wand"]["name"])
    assert main.menu_labels(app) == [story.MESSAGES["label_examine"], use_wand]
    press(app, pygame.K_ESCAPE)
    assert app["scene"] == "play"
    assert app["dialog"] == []


def test_a_choice_that_cannot_be_undone_asks_first(app):
    """Opening a final door asks for confirmation; "No" changes nothing, not even the save."""
    app["state"] = play(TO_THE_CRAB_ENDING[:5])  # back on the deck with the key
    main.set_scene(app, "play")
    save.save_game(app["state"])
    saved = save.load_game()
    app["player"] = main.spawn_in_front_of("deck_to_crab")
    press(app, pygame.K_e)
    choose_in_menu(app, "use_item", "key")
    assert app["scene"] == "confirm"
    assert main.menu_entries(app)[app["menu_index"]] == "no"
    press(app, pygame.K_RETURN)  # "No"
    assert app["scene"] == "play"
    assert engine.door_status(app["state"], "deck_to_crab") == "locked"
    assert save.load_game() == saved


def test_the_sealed_door_explains_itself(app):
    """PT04 on screen: after choosing the crab, the angel's door refuses even the key, and says why."""
    app["state"] = play(TO_THE_CRAB_ENDING[:6])  # the crab's door just opened
    main.set_scene(app, "play")
    app["player"] = main.spawn_in_front_of("deck_to_angel")
    press(app, pygame.K_e)
    choose_in_menu(app, "use_item", "key")
    assert dialog_text(app) == story.DOORS["deck_to_angel"]["sealed_text"]
    read_all(app)
    walk_into(app, "deck_to_angel")
    assert app["state"]["room"] == "deck"
    assert dialog_text(app) == story.DOORS["deck_to_angel"]["sealed_text"]


def test_inventory_shows_items_and_clues(app):
    """PT03: I opens the inventory with the items and their descriptions, and the clues found."""
    start_new_game(app)
    press(app, pygame.K_i)
    assert app["scene"] == "inventory"
    assert main.inventory_lines(app["state"]) == [("text", story.MESSAGES["inventory_empty"])]
    press(app, pygame.K_i)
    assert app["scene"] == "play"
    found_clue = play([TO_THE_CRAB_ENDING[0], {"verb": "enter", "target": "deck_to_hold"},
                       {"verb": "use_item", "target": "hold_puzzle", "item": "wand"}])
    assert main.inventory_lines(found_clue) == [
        ("name", story.ITEMS["wand"]["name"]),
        ("text", story.ITEMS["wand"]["description"]),
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
    stand_next_to(app, "cabin_puzzle")
    press(app, pygame.K_e)
    choose_in_menu(app, "use_item", "wand")
    read_all(app)
    stand_next_to(app, "key")
    press(app, pygame.K_e)
    read_all(app)
    walk_into(app, "cabin_to_deck")
    app["player"] = main.spawn_in_front_of(door)
    press(app, pygame.K_e)
    choose_in_menu(app, "use_item", "key")
    press(app, pygame.K_UP, pygame.K_RETURN)  # "Sì"
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


# --- Drawing ------------------------------------------------------------------------


def test_every_scene_and_room_can_be_drawn(app):
    """A smoke test: drawing every scene, every room and every door state raises no error."""
    screen = pygame.Surface((main.WIDTH, main.HEIGHT))
    main.draw(app, screen)
    start_new_game(app)
    states = [in_room(room) for room in story.ROOMS]
    states.append(play(TO_THE_CRAB_ENDING[:6]))  # the crab's door open, the angel's sealed, the key taken
    states.append(play(TO_THE_CRAB_ENDING[:3]))  # in the cabin: the drawer open, the key on the floor
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
    for ending_path in (TO_THE_CRAB_ENDING, TO_THE_CRAB_ENDING[:5] + [
            {"verb": "use_item", "target": "deck_to_angel", "item": "key"},
            {"verb": "enter", "target": "deck_to_angel"},
            {"verb": "use_item", "target": "angel", "item": "wand"}]):
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
