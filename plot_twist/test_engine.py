"""Tests for the Plot Twist engine: the acceptance scenarios and the requirements of the brief.

Each test name starts with the id of what it demonstrates: test_a1_... for the
scenarios, test_pt01_... for the required capabilities, test_r1_... for the
business rules, test_story_... for the story data. The tests check events and
states, never the wording, so the texts in story.py can be rewritten freely.

The tests that save the game write to a temporary folder (see conftest.py).
"""

import copy
import json

import pytest

import engine
import save
import story


# --- Actions and paths through the story --------------------------------------


def act(verb, target, item=None):
    """Build an action in the shape engine.perform() expects."""
    return {"verb": verb, "target": target, "item": item}


TAKE_WAND = act("pick_up", "wand")
TAKE_KEY = act("pick_up", "key")
TAKE_SECOND_KEY = act("pick_up", "second_key")
TO_CABIN = act("enter", "deck_to_cabin")
TO_HOLD = act("enter", "deck_to_hold")
TO_CRAB = act("enter", "deck_to_crab")
TO_ANGEL = act("enter", "deck_to_angel")
CABIN_TO_DECK = act("enter", "cabin_to_deck")
HOLD_TO_DECK = act("enter", "hold_to_deck")
CRAB_TO_DECK = act("enter", "crab_to_deck")
TO_INFIRMARY = act("enter", "hold_to_infirmary")
INFIRMARY_TO_HOLD = act("enter", "infirmary_to_hold")
CABIN_TO_GALLEY = act("enter", "cabin_to_galley")
GALLEY_TO_CABIN = act("enter", "galley_to_cabin")
CABIN_TO_HELM = act("enter", "cabin_to_helm")
HELM_TO_CABIN = act("enter", "helm_to_cabin")
TO_CORRIDOR = act("enter", "infirmary_to_corridor")
CORRIDOR_TO_INFIRMARY = act("enter", "corridor_to_infirmary")
TAKE_GREEN = act("pick_up", "green_tincture")
TAKE_RED = act("pick_up", "red_tincture")
TAKE_GOLD = act("pick_up", "gold_tincture")
TAKE_BLUE = act("pick_up", "blue_tincture")
TAKE_POTION = act("pick_up", "potion")
GIVE_TO_DOCTOR = act("use_item", "doctor", item="potion")
ACTIVATE_A = act("activate", "generator_a")
ACTIVATE_B = act("activate", "generator_b")
ACTIVATE_C = act("activate", "generator_c")
ACTIVATE_D = act("activate", "generator_d")
ACTIVATE_E = act("activate", "generator_e")
WAND_ON_BARREL = act("use_item", "hold_puzzle", item="wand")
FUSE = act("use_item", "anvil", item="second_key")
OPEN_CRAB = act("use_item", "deck_to_crab", item="fused_key")
OPEN_ANGEL = act("use_item", "deck_to_angel", item="fused_key")
GIVE_TO_CRAB = act("use_item", "crab", item="wand")
GIVE_TO_ANGEL = act("use_item", "angel", item="wand")
LEAVE_TILES = act("leave_zone", "hold_tiles")


def step(number):
    """Walk onto the numbered tile of the hold."""
    return act("step_on", f"tile_{number}")


# The cabin's eight generators start with H, A, C and D off: A then C turns all eight on.
SOLVE_CABIN = [ACTIVATE_A, ACTIVATE_C]
# The tiles of the hold. Phase 1, the wave: 1 to 5. Phase 2, the return, from 5:
# 3, then 1. Phase 3, the short circuit, from 1: 5, 2, 4, 3. Each phase starts on
# the tile the one before ended on, already lit.
PHASE_1 = [step(1), step(2), step(3), step(4), step(5)]
PHASE_2 = [step(3), step(1)]
PHASE_3 = [step(5), step(2), step(4), step(3)]
SOLVE_TILES = PHASE_1 + PHASE_2 + PHASE_3
# The tinctures, from the hold and back: the green one in the infirmary makes the
# others appear, in the corridor, the galley and the helm.
GATHER_TINCTURES = [TO_INFIRMARY, TAKE_GREEN, TO_CORRIDOR, TAKE_BLUE, CORRIDOR_TO_INFIRMARY, INFIRMARY_TO_HOLD,
                    HOLD_TO_DECK, TO_CABIN, CABIN_TO_GALLEY, TAKE_RED, GALLEY_TO_CABIN, CABIN_TO_HELM, TAKE_GOLD,
                    HELM_TO_CABIN, CABIN_TO_DECK, TO_HOLD]
# The remedy: the tinctures poured into the cauldron in the right order, then the doctor drinks it.
RECIPE = [act("use_item", "cauldron", item=tincture) for tincture in story.POTION_PUZZLES["remedy"]["recipe"]]
CALM_THE_DOCTOR = GATHER_TINCTURES + [TO_INFIRMARY] + RECIPE + [TAKE_POTION, GIVE_TO_DOCTOR, INFIRMARY_TO_HOLD]
# From the deck to the galley and back: the anvil is there once the doctor is at peace.
FUSE_IN_THE_GALLEY = [TO_CABIN, CABIN_TO_GALLEY, FUSE, GALLEY_TO_CABIN, CABIN_TO_DECK]
# Wand, cabin puzzle, the first half of the key, and back on the deck.
GET_KEY = [TAKE_WAND, TO_CABIN] + SOLVE_CABIN + [TAKE_KEY, CABIN_TO_DECK]
# Then the hold, no longer barred: the tiles, the second half, the remedy for the
# doctor, back on the deck, and the two halves fused on the anvil in the galley.
GET_FUSED_KEY = (GET_KEY + [TO_HOLD] + SOLVE_TILES + [TAKE_SECOND_KEY] + CALM_THE_DOCTOR
                 + [HOLD_TO_DECK] + FUSE_IN_THE_GALLEY)
# The shortest way to each ending: the barrel of the hold is optional.
CRAB_ENDING = GET_FUSED_KEY + [OPEN_CRAB, TO_CRAB, GIVE_TO_CRAB]
ANGEL_ENDING = GET_FUSED_KEY + [OPEN_ANGEL, TO_ANGEL, GIVE_TO_ANGEL]
# The long way: read the clue on the barrel too.
CLUE_THEN_CRAB = (GET_KEY + [TO_HOLD, WAND_ON_BARREL] + SOLVE_TILES
                  + [TAKE_SECOND_KEY] + CALM_THE_DOCTOR + [HOLD_TO_DECK] + FUSE_IN_THE_GALLEY
                  + [OPEN_CRAB, TO_CRAB, GIVE_TO_CRAB])
# Open both doors, go in one, come back and wander around without ending the game.
CHOOSE_AND_WANDER = GET_FUSED_KEY + [OPEN_CRAB, OPEN_ANGEL, TO_CRAB, CRAB_TO_DECK, TO_CABIN]
# Flip some generators, walk out and back in (they start over), flip another one.
TOGGLE_AND_LEAVE = [TAKE_WAND, TO_CABIN, ACTIVATE_B, ACTIVATE_C, CABIN_TO_DECK, TO_CABIN, ACTIVATE_C]
# Mistakes on the tiles: a wrong tile, walking out of the zone, walking out of the
# hold in the middle of phase 2; each time the phase starts over.
TILE_MISTAKES = (GET_KEY + [TO_HOLD, step(1), step(2), step(4), step(1), step(2), LEAVE_TILES]
                 + PHASE_1 + [step(3), HOLD_TO_DECK, TO_HOLD, step(5), step(3)])


def play(steps, state=None):
    """Play the steps from a new game (or from `state`) and return the final state.

    Checks that each step is accepted and leaves the state it received untouched:
    otherwise two moments of the same game could end up being one shared dict.
    """
    if state is None:
        state = engine.new_game()
    for step in steps:
        before = copy.deepcopy(state)
        new_state, outcome = engine.perform(state, step)
        assert outcome["ok"], f"{step} was refused: {outcome}"
        assert state == before, f"{step} modified the state it received"
        state = new_state
    return state


def states_along(steps):
    """Every state met while playing the steps from a new game, the first and the last included."""
    state = engine.new_game()
    states = [state]
    for step in steps:
        state = play([step], state)
        states.append(state)
    return states


def sample_states():
    """A good spread of moments in a game: every step of five different paths."""
    return (states_along(CLUE_THEN_CRAB) + states_along(ANGEL_ENDING) + states_along(CHOOSE_AND_WANDER)
            + states_along(TOGGLE_AND_LEAVE) + states_along(TILE_MISTAKES))


def every_action():
    """Every action the engine understands, on every id of the story. Most of them get refused."""
    targets = list(story.ROOMS) + list(story.ITEMS) + list(story.DOORS) + list(story.OBJECTS)
    actions = []
    for item in story.ITEMS:
        actions.append(act("pick_up", item))
    for door in story.DOORS:
        actions.append(act("enter", door))
    for thing, info in story.OBJECTS.items():
        if info["kind"] == "switch":
            actions.append(act("activate", thing))
        if info["kind"] == "tile":
            actions.append(act("step_on", thing))
        if info["kind"] == "portal":
            actions.append(act("travel", thing))
    for puzzle in story.FLOOR_PUZZLES:
        actions.append(act("leave_zone", puzzle))
    for target in targets:
        actions.append(act("examine", target))
        for item in story.ITEMS:
            actions.append(act("use_item", target, item=item))
    return actions


def reopen(state):
    """What the app gets back after saving, closing and reopening: the state goes through JSON."""
    return engine.restore_state(json.loads(json.dumps(state)))


def offered(state, target):
    """The (verb, item) of each action the E key offers near the target."""
    return [(action["verb"], action["item"]) for action in engine.actions_for(state, target)]


def assert_same_routes(resumed, played):
    """The resumed game offers exactly the doors and the actions of the game that was played."""
    for door in story.DOORS:
        assert engine.door_status(resumed, door) == engine.door_status(played, door)
    for thing in engine.things_here(played):
        assert engine.actions_for(resumed, thing["id"]) == engine.actions_for(played, thing["id"])


# --- The save file, used the way main.py uses it --------------------------------


def save_if_accepted(result):
    """main.py's rule: after an action or a new game, save if it was accepted, and only then."""
    state, outcome = result
    if outcome["ok"]:
        save.save_game(state)
    return state, outcome


def play_saving(steps):
    """Start a new game and play the steps the way the app does, saving after each one."""
    state, _ = save_if_accepted(engine.start_new_game(None))
    for step in steps:
        state, outcome = save_if_accepted(engine.perform(state, step))
        assert outcome["ok"], f"{step} was refused: {outcome}"
    return state


def resume():
    """What the app does when it opens: read the save file and check it. None if there is nothing to resume."""
    return engine.restore_state(save.load_game())


# --- Acceptance scenarios A1-A6 ------------------------------------------------


def test_a1_locked_route_is_rejected_and_nothing_moves():
    """A1: without the key, the final doors refuse; the player stays on the deck with the same inventory."""
    for state in (engine.new_game(), play([TAKE_WAND])):
        for door in ("deck_to_crab", "deck_to_angel"):
            after, outcome = engine.enter(state, door)
            assert not outcome["ok"]
            assert outcome["event"] == "locked"
            assert after["room"] == "deck"
            assert after["inventory"] == state["inventory"]
            assert after == state
            assert ("enter", None) not in offered(state, door)


@pytest.mark.parametrize("open_door, go_in, room", [
    (OPEN_CRAB, TO_CRAB, "crab_room"),
    (OPEN_ANGEL, TO_ANGEL, "angel_room"),
])
def test_a2_key_opens_the_route_and_stays_in_inventory(open_door, go_in, room):
    """A2: with the fused key, the locked route leads to its room, and the key is not used up."""
    state = play(GET_FUSED_KEY + [open_door, go_in])
    assert state["room"] == room
    assert engine.has_item(state, "fused_key")


def test_a3_wand_cannot_be_collected_twice():
    """A3: back where the wand was, picking it up again is refused; there is still one wand."""
    state = play([TAKE_WAND, TO_CABIN, CABIN_TO_DECK])
    after, outcome = engine.pick_up(state, "wand")
    assert not outcome["ok"]
    assert outcome["event"] == "already_have"
    assert after["inventory"].count("wand") == 1


def test_a3_revisited_cabin_offers_no_second_key():
    """A3: back in the cabin, the altar is empty and the generators do not make another key."""
    state = play(GET_KEY + [TO_CABIN])
    ids_here = [thing["id"] for thing in engine.things_here(state)]
    assert "key" not in ids_here
    _, outcome = engine.pick_up(state, "key")
    assert not outcome["ok"]
    after, outcome = engine.activate(state, "generator_a")
    assert outcome["event"] == "already_done"
    assert after["inventory"].count("key") == 1


def test_a3_revisited_hold_offers_no_third_key():
    """A3: back in the hold, the altar is empty, and the tiles and the altar do not make another key."""
    state = play(GET_FUSED_KEY + [TO_HOLD])
    assert "second_key" not in [thing["id"] for thing in engine.things_here(state)]
    _, outcome = engine.pick_up(state, "second_key")
    assert not outcome["ok"]
    after, outcome = engine.step_on(state, "tile_1")
    assert outcome["event"] == "already_done"
    after, outcome = engine.use_item(state, "fused_key", "hold_altar")
    assert outcome["event"] == "nothing_happens"
    assert after["inventory"] == ["wand", "fused_key"]


def test_a4_resume_restores_scene_items_and_choice():
    """A4: collect items, make the choice, close and reopen: the same game, with the same routes.

    Here the game only goes through JSON in memory; the next test uses the real save file.
    """
    state = play(GET_FUSED_KEY + [OPEN_CRAB])
    resumed = reopen(state)
    assert resumed == state
    assert resumed["room"] == "deck"
    assert resumed["inventory"] == ["wand", "fused_key"]
    assert resumed["flags"]["crab_door"] == "deck_to_crab"
    assert engine.door_status(resumed, "deck_to_crab") == "open"
    assert engine.door_status(resumed, "deck_to_angel") == "locked"  # still to open, with the same key
    assert_same_routes(resumed, state)


def test_a4_resume_through_the_save_file():
    """A4 with the real file: every accepted action is saved, and reopening the app reads only the file."""
    played = play_saving(GET_FUSED_KEY + [OPEN_CRAB, TO_CRAB])
    resumed = resume()
    assert resumed == played
    assert resumed["room"] == "crab_room"
    assert resumed["inventory"] == ["wand", "fused_key"]
    assert resumed["flags"]["crab_door"] == "deck_to_crab"
    assert_same_routes(resumed, played)


@pytest.mark.parametrize("steps, ending", [
    (CRAB_ENDING, "saved"),
    (ANGEL_ENDING, "explosion"),
])
def test_a5_each_path_reaches_its_own_ending(steps, ending):
    """A5: two valid paths from two new games reach two different endings."""
    state = play(steps)
    assert state["ending"] == ending
    assert engine.is_over(state)


@pytest.mark.parametrize("steps", [CRAB_ENDING, ANGEL_ENDING])
def test_a5_finished_game_cannot_change(steps):
    """A5: after an ending every story action is refused, also after reopening the game."""
    finished = play(steps)
    for state in (finished, reopen(finished)):
        for action in every_action():
            after, outcome = engine.perform(state, action)
            assert not outcome["ok"]
            assert outcome["event"] == "game_over"
            assert after == finished


def test_a6_cancelled_restart_keeps_progress():
    """A6: without confirmation, starting over changes nothing."""
    progress = play(GET_FUSED_KEY + [OPEN_CRAB])
    after, outcome = engine.start_new_game(progress)
    assert not outcome["ok"]
    assert outcome["event"] == "needs_confirmation"
    assert after == progress


def test_a6_confirmed_restart_restores_the_opening():
    """A6: once confirmed, the game is back to the opening scene, empty-handed, nothing decided."""
    progress = play(GET_FUSED_KEY + [OPEN_CRAB])
    fresh, outcome = engine.start_new_game(progress, confirmed=True)
    assert outcome["ok"]
    assert outcome["event"] == "started"
    assert fresh["room"] == story.START_ROOM
    assert fresh["inventory"] == []
    assert fresh["flags"] == story.FLAGS
    assert fresh["ending"] is None


def test_a6_restart_through_the_save_file(save_file):
    """A6 with the real file: cancelling leaves the save as it was; confirming replaces it with a new game."""
    play_saving(GET_FUSED_KEY + [OPEN_CRAB])
    saved_bytes = save_file.read_bytes()
    progress = resume()

    _, outcome = save_if_accepted(engine.start_new_game(progress))
    assert outcome["event"] == "needs_confirmation"
    assert save_file.read_bytes() == saved_bytes
    assert resume() == progress

    _, outcome = save_if_accepted(engine.start_new_game(progress, confirmed=True))
    assert outcome["ok"]
    assert resume() == engine.new_game()


# --- PT01-PT05: required capabilities -----------------------------------------


def test_pt01_resume_is_offered_only_when_a_game_exists():
    assert engine.menu_options(None) == ["new_game"]
    assert engine.menu_options(engine.new_game()) == ["new_game", "resume"]


def test_pt01_first_game_needs_no_confirmation():
    state, outcome = engine.start_new_game(None)
    assert outcome["ok"]
    assert outcome["text"] == story.MESSAGES["intro"]
    assert state == engine.new_game()


def test_pt01_restart_after_an_ending_also_asks():
    """A finished game is still progress: replacing it needs confirmation too."""
    finished = play(CRAB_ENDING)
    after, outcome = engine.start_new_game(finished)
    assert outcome["event"] == "needs_confirmation"
    assert after == finished


def test_pt02_the_scene_lists_its_things_and_their_actions():
    """The opening scene shows the wand and four doors, and E offers the right action for each."""
    state = engine.new_game()
    here = {thing["id"]: thing["status"] for thing in engine.things_here(state) if thing["kind"] != "decor"}
    assert here == {
        "wand": "on_floor",
        "deck_to_cabin": "open",
        "deck_to_hold": "barred",
        "deck_to_crab": "locked",
        "deck_to_angel": "locked",
    }
    assert offered(state, "wand") == [("pick_up", None)]
    assert offered(state, "deck_to_cabin") == [("enter", None)]
    assert offered(state, "deck") == []  # far from everything, E does nothing


def test_e_ignores_decor_except_the_notes_to_read():
    """Furniture is not part of the story: even with items in hand, E offers nothing on it.

    The notes ("clue") can still be read: they tell the order of the tinctures.
    """
    state = play([TAKE_WAND])
    clues = []
    for thing, info in story.OBJECTS.items():
        if info["kind"] == "decor":
            state["room"] = info["room"]
            if info.get("clue"):
                clues.append(thing)
                assert offered(state, thing) == [("examine", None)], thing
                _, outcome = engine.examine(state, thing)
                assert outcome["ok"] and outcome["text"] == info["look_text"], thing
            else:
                assert offered(state, thing) == [], thing
    assert sorted(clues) == ["cabin_notes", "galley_notes", "infirmary_notes"]


def test_pt02_accepted_actions_show_a_result():
    """Every accepted action, at any moment of the game, gives the player something to read."""
    for state in sample_states():
        for action in every_action():
            _, outcome = engine.perform(state, action)
            if outcome["ok"]:
                assert outcome["text"].strip(), f"{action} gave no visible result"


def test_pt03_the_key_unlocks_opening_the_door():
    """Without the key, E only lets you look at the door; with the fused key, it opens it."""
    assert ("use_item", "fused_key") not in offered(play([TAKE_WAND]), "deck_to_crab")
    with_key = play(GET_FUSED_KEY)
    for door in ("deck_to_crab", "deck_to_angel"):
        assert ("use_item", "fused_key") in offered(with_key, door)
        _, outcome = engine.use_item(with_key, "fused_key", door)
        assert outcome["event"] == "door_opened"


@pytest.mark.parametrize("steps, half", [
    pytest.param(GET_KEY, "key", id="only the first half"),
    pytest.param(GET_KEY + [TO_HOLD] + SOLVE_TILES + [TAKE_SECOND_KEY, HOLD_TO_DECK], "second_key", id="both, not fused"),
])
def test_pt03_the_halves_do_not_open_the_doors(steps, half):
    """PT04 too: a half refuses to turn, says it must be fused on the anvil, and nothing changes."""
    state = play(steps)
    for door in ("deck_to_crab", "deck_to_angel"):
        after, outcome = engine.use_item(state, half, door)
        assert not outcome["ok"]
        assert outcome["event"] == "not_fused"
        assert outcome["text"] == story.MESSAGES["not_fused"]
        assert after == state
        assert engine.door_status(state, door) == "locked"


def test_pt03_the_anvil_fuses_the_two_halves():
    """Either half on the anvil, with both in hand: the halves become the fused key, in the first half's place."""
    with_both = play(GET_KEY + [TO_HOLD] + SOLVE_TILES + [TAKE_SECOND_KEY] + CALM_THE_DOCTOR
                     + [HOLD_TO_DECK, TO_CABIN, CABIN_TO_GALLEY])
    assert with_both["inventory"] == ["wand", "key", "second_key"]
    for half in ("key", "second_key"):
        fused, outcome = engine.use_item(with_both, half, "anvil")
        assert outcome["event"] == "fused"
        assert outcome["text"] == story.OBJECTS["anvil"]["fuse_text"]
        assert fused["inventory"] == ["wand", "fused_key"]
    _, outcome = engine.use_item(with_both, "wand", "anvil")
    assert outcome["event"] == "nothing_happens"
    halves_first = play([TO_CABIN] + SOLVE_CABIN + [TAKE_KEY, CABIN_TO_DECK, TAKE_WAND, TO_HOLD] + SOLVE_TILES
                        + [TAKE_SECOND_KEY] + CALM_THE_DOCTOR + [HOLD_TO_DECK] + FUSE_IN_THE_GALLEY)
    assert halves_first["inventory"] == ["fused_key", "wand"]  # the order things were found in is kept


def test_pt03_one_half_alone_cannot_be_fused():
    """The anvil needs both halves: the refusal says the other one is missing, and nothing changes."""
    state = play(GET_KEY + [TO_HOLD] + CALM_THE_DOCTOR + [HOLD_TO_DECK, TO_CABIN, CABIN_TO_GALLEY])
    after, outcome = engine.use_item(state, "key", "anvil")
    assert outcome["event"] == "missing_item"
    assert outcome["text"] == story.MESSAGES["missing_item"]
    assert after == state


def test_pt03_fused_halves_never_come_back():
    """R2: the halves are gone for good: not on the altar, not on the anvil, and the hold stays open."""
    state = play(GET_FUSED_KEY)
    assert engine.door_status(state, "deck_to_hold") == "open"
    for room, half in (("cabin", "key"), ("hold", "second_key")):
        there = dict(state, room=room)
        assert half not in [thing["id"] for thing in engine.things_here(there)]
        _, outcome = engine.pick_up(there, half)
        assert not outcome["ok"]


def test_pt03_a_lock_needing_several_items_wants_them_all(monkeypatch):
    """The engine's rule for any lock: every item it requires must be carried, or it explains what is missing."""
    monkeypatch.setitem(story.DOORS["deck_to_crab"], "requires", ["fused_key", "wand"])
    without_wand = play([TO_CABIN] + SOLVE_CABIN + [TAKE_KEY, CABIN_TO_DECK, TO_HOLD] + SOLVE_TILES
                        + [TAKE_SECOND_KEY] + CALM_THE_DOCTOR + [HOLD_TO_DECK] + FUSE_IN_THE_GALLEY)
    after, outcome = engine.use_item(without_wand, "fused_key", "deck_to_crab")
    assert outcome["event"] == "missing_item"
    assert after == without_wand
    _, outcome = engine.use_item(play([TAKE_WAND], without_wand), "fused_key", "deck_to_crab")
    assert outcome["event"] == "door_opened"


def test_pt04_the_fused_key_opens_both_doors():
    """Opening one final door no longer seals the other: the fused key stays, and opens it too."""
    state = play(CHOOSE_AND_WANDER + [CABIN_TO_DECK])
    assert engine.door_status(state, "deck_to_crab") == "open"
    assert engine.door_status(state, "deck_to_angel") == "open"
    assert engine.has_item(state, "fused_key")
    after, outcome = engine.perform(state, TO_ANGEL)
    assert outcome["event"] == "entered"


def test_pt04_doors_sharing_a_choice_flag_seal_each_other(monkeypatch):
    """The engine still knows choices between doors: with one flag for both, opening one seals the other."""
    monkeypatch.setitem(story.DOORS["deck_to_angel"], "choice_flag", "crab_door")
    monkeypatch.setitem(story.DOORS["deck_to_angel"], "sealed_text", "Sigillata.")
    with_key = play(GET_FUSED_KEY)
    assert engine.actions_for(with_key, "deck_to_crab")[-1]["irreversible"]
    state = play([OPEN_CRAB], with_key)
    assert engine.door_status(state, "deck_to_angel") == "sealed"
    for action in (TO_ANGEL, OPEN_ANGEL):
        after, outcome = engine.perform(state, action)
        assert outcome["event"] == "sealed"
        assert after == state
    _, outcome = engine.examine(state, "deck_to_angel")
    assert outcome["text"] == "Sigillata."


def test_pt04_refused_actions_are_explained():
    """Every refused action, at any moment of the game, tells the player why."""
    for state in sample_states():
        for action in every_action():
            _, outcome = engine.perform(state, action)
            if not outcome["ok"]:
                assert outcome["text"].strip(), f"{action} was refused without an explanation"


def test_pt04_irreversible_actions_are_flagged():
    """Giving the wand asks for confirmation; opening a door, fusing or solving a puzzle does not."""
    with_half = play(GET_KEY)
    flags = {action["item"]: action["irreversible"] for action in engine.actions_for(with_half, "deck_to_crab")}
    assert flags == {None: False, "wand": False, "key": False}  # half a key opens nothing

    with_key = play(GET_FUSED_KEY)
    flags = {action["item"]: action["irreversible"] for action in engine.actions_for(with_key, "deck_to_crab")}
    assert flags == {None: False, "wand": False, "fused_key": False}  # the other door stays open to choose

    near_crab = play(GET_FUSED_KEY + [OPEN_CRAB, TO_CRAB])
    flags = {action["item"]: action["irreversible"] for action in engine.actions_for(near_crab, "crab")}
    assert flags == {None: False, "wand": True, "fused_key": False}

    in_cabin = play([TAKE_WAND, TO_CABIN])
    for action in engine.actions_for(in_cabin, "generator_a") + engine.actions_for(in_cabin, "barrier"):
        assert not action["irreversible"]
    in_hold = play(GET_KEY + [TO_HOLD])
    for thing in ("tile_1", "hold_barrier", "hold_puzzle"):
        for action in engine.actions_for(in_hold, thing):
            assert not action["irreversible"], thing


def test_pt05_endings_are_clearly_identified():
    titles = [ending["title"] for ending in story.ENDINGS.values()]
    assert len(set(titles)) == len(titles)


def test_pt05_after_an_ending_nothing_is_offered():
    finished = play(CRAB_ENDING)
    assert engine.actions_for(finished, finished["room"]) == []
    for thing in engine.things_here(finished):
        assert engine.actions_for(finished, thing["id"]) == []


def test_pt05_finished_game_resumes_on_its_ending():
    """The outcome can be reviewed after reopening the app: the save remembers the ending."""
    play_saving(CRAB_ENDING)
    resumed = resume()
    assert engine.is_over(resumed)
    assert resumed["ending"] == "saved"
    assert engine.menu_options(resumed) == ["new_game", "resume"]


# --- R1-R4: business rules -----------------------------------------------------


def test_r1_actions_need_the_right_scene_and_conditions():
    on_deck = play([TAKE_WAND])
    for action in (ACTIVATE_A, WAND_ON_BARREL, GIVE_TO_CRAB, GIVE_TO_ANGEL, CABIN_TO_DECK, step(1), LEAVE_TILES):
        _, outcome = engine.perform(on_deck, action)
        assert outcome["event"] == "not_here"
    without_wand = play([TO_CABIN] + SOLVE_CABIN + [TAKE_KEY, CABIN_TO_DECK, TO_HOLD])
    _, outcome = engine.perform(without_wand, WAND_ON_BARREL)
    assert outcome["event"] == "no_item"


def test_r1_the_hold_is_barred_until_the_first_half_of_the_key():
    """The gate of the hold opens by itself as soon as the player has the first half: no action needed."""
    for state in (engine.new_game(), play([TAKE_WAND, TO_CABIN] + SOLVE_CABIN + [CABIN_TO_DECK])):
        assert engine.door_status(state, "deck_to_hold") == "barred"
        after, outcome = engine.enter(state, "deck_to_hold")
        assert outcome["event"] == "barred"
        assert outcome["text"] == story.DOORS["deck_to_hold"]["barred_text"]
        assert after == state
        assert offered(state, "deck_to_hold") == [("examine", None)] + [("use_item", item) for item in state["inventory"]]
        _, outcome = engine.examine(state, "deck_to_hold")
        assert outcome["text"] == story.DOORS["deck_to_hold"]["barred_text"]
    with_half = play(GET_KEY)
    assert engine.door_status(with_half, "deck_to_hold") == "open"
    assert engine.enter(with_half, "deck_to_hold")[0]["room"] == "hold"


def test_r1_refused_actions_change_nothing():
    for state in sample_states():
        for action in every_action():
            after, outcome = engine.perform(state, action)
            if not outcome["ok"]:
                assert after == state, f"{action} was refused but changed the game"


def test_r1_actions_never_modify_the_state_they_receive():
    for state in sample_states():
        before = copy.deepcopy(state)
        for action in every_action():
            engine.perform(state, action)
            assert state == before, f"{action} modified the state it received"


def test_r2_items_can_be_collected_only_where_the_story_puts_them():
    in_cabin = play([TO_CABIN])
    _, outcome = engine.pick_up(in_cabin, "key")
    assert outcome["event"] == "guarded"  # the barrier still stands
    _, outcome = engine.pick_up(in_cabin, "wand")
    assert outcome["event"] == "not_here"  # the wand lies on the deck
    _, outcome = engine.pick_up(in_cabin, "second_key")
    assert outcome["event"] == "not_here"  # the second half is in the hold
    in_hold = play(GET_KEY + [TO_HOLD] + PHASE_1 + PHASE_2)
    _, outcome = engine.pick_up(in_hold, "second_key")
    assert outcome["event"] == "guarded"  # two phases are not enough


def test_r2_using_items_does_not_consume_them():
    """After opening a door and giving the wand away, the wand and the key are still there.

    Only the anvil changes the inventory: the two halves become the fused key.
    """
    assert play(CRAB_ENDING)["inventory"] == ["wand", "fused_key"]


def test_r3_revisited_cabin_remembers_the_complete_circuit():
    """Back in the cabin: the generators are still on, the barrier is still gone, the altar is empty."""
    state = play(GET_KEY + [TO_CABIN])
    here = {thing["id"]: thing["status"] for thing in engine.things_here(state)}
    for generator in GENERATORS:
        assert here[generator] == "on"
    assert "barrier" not in here
    assert "key" not in here
    assert here["altar"] == "present"


def test_r3_revisited_hold_remembers_the_solved_barrel():
    """Back in the hold: the barrel shows the solved puzzle, and using the wand again does nothing."""
    state = play(GET_KEY + [TO_HOLD, WAND_ON_BARREL, HOLD_TO_DECK, TO_HOLD])
    here = {thing["id"]: thing["status"] for thing in engine.things_here(state)}
    assert here["hold_puzzle"] == "solved"
    _, outcome = engine.examine(state, "hold_puzzle")
    assert outcome["text"] == story.OBJECTS["hold_puzzle"]["done_text"]
    after, outcome = engine.use_item(state, "wand", "hold_puzzle")
    assert outcome["event"] == "already_done"
    assert after == state


def test_r2_an_item_can_wait_for_a_flag_to_appear(monkeypatch):
    """An item with "appears_if" is not there until its flag is true: here the wand waits for the clue."""
    monkeypatch.setitem(story.ITEMS["wand"], "appears_if", "crab_truthful")
    state = engine.new_game()
    assert "wand" not in [thing["id"] for thing in engine.things_here(state)]
    _, outcome = engine.pick_up(state, "wand")
    assert outcome["event"] == "not_here"
    state["flags"]["crab_truthful"] = True
    assert "wand" in [thing["id"] for thing in engine.things_here(state)]


def test_r3_revisited_hold_remembers_the_solved_tiles():
    """Back in the hold: every tile still lit, the barrier still gone, the altar empty."""
    state = play(GET_FUSED_KEY + [TO_HOLD])
    here = {thing["id"]: thing["status"] for thing in engine.things_here(state)}
    assert [here[f"tile_{number}"] for number in range(1, 6)] == ["lit"] * 5
    assert "hold_barrier" not in here
    assert "second_key" not in here
    assert here["hold_altar"] == "present"


def test_r3_found_clue_is_remembered():
    state = play(GET_KEY + [TO_HOLD, WAND_ON_BARREL, HOLD_TO_DECK])
    assert engine.clues(state) == [story.CLUES["crab_truthful"]]
    assert engine.clues(reopen(state)) == [story.CLUES["crab_truthful"]]
    assert engine.clues(engine.new_game()) == []


def test_r4_new_game_resets_progress_but_not_the_story():
    """Playing, resuming and restarting never change story.py."""
    tables = [story.START_ROOM, story.FLAGS, story.ROOMS, story.ITEMS, story.DOORS, story.OBJECTS,
              story.CIRCUITS, story.FLOOR_PUZZLES, story.ENDINGS, story.CLUES, story.MESSAGES]
    story_before = copy.deepcopy(tables)
    first_game = copy.deepcopy(engine.new_game())
    for state in sample_states():
        reopen(state)
        engine.start_new_game(state, confirmed=True)
        for action in every_action():
            engine.perform(state, action)
            engine.actions_for(state, action["target"])
    assert tables == story_before
    assert engine.new_game() == first_game


def test_r4_each_new_game_is_independent():
    """Changing one game must not leak into the story, or into the next new game."""
    game = engine.new_game()
    game["inventory"].append("wand")
    game["flags"]["cabin_solved"] = True
    assert story.FLAGS["cabin_solved"] is False
    assert engine.new_game()["inventory"] == []
    assert engine.new_game()["flags"]["cabin_solved"] is False


def test_r4_every_ending_is_reachable_from_a_new_game():
    reached = set()
    for steps in (CRAB_ENDING, ANGEL_ENDING, CLUE_THEN_CRAB):
        reached.add(play(steps)["ending"])
    assert reached == set(story.ENDINGS)


# --- M5: the generators of the captain's cabin -----------------------------------------

GENERATORS = ["generator_a", "generator_b", "generator_c", "generator_d",
              "generator_e", "generator_f", "generator_g", "generator_h"]
START = "aBcdEFGh"  # H, A, C and D off; B, E, F and G on
ALL_ON = "ABCDEFGH"


def generators(state):
    """The eight generators as their letters, capital when on: "aBcdEFGh" is the start."""
    letters = ""
    for generator in GENERATORS:
        letter = story.OBJECTS[generator]["label"]
        letters += letter if state["flags"][generator] else letter.lower()
    return letters


def test_m5_the_generators_start_with_h_a_c_and_d_off():
    """The starting configuration the puzzle asks for, with the barrier up and the key behind it."""
    in_cabin = play([TO_CABIN])
    assert generators(in_cabin) == START
    here = {thing["id"]: thing["status"] for thing in engine.things_here(in_cabin)}
    assert here["barrier"] == "up"
    assert here["key"] == "guarded"


def test_m5_the_generators_are_wired_in_a_ring():
    """Each generator is wired to itself and to the two next to it in the ring A, B, ... H, and back to A."""
    for index, generator in enumerate(GENERATORS):
        neighbours = {GENERATORS[index - 1], GENERATORS[(index + 1) % len(GENERATORS)]}
        toggles = story.OBJECTS[generator]["toggles"]
        assert toggles[0] == generator and set(toggles[1:]) == neighbours, generator


@pytest.mark.parametrize("generator, after", [
    ("generator_a", "AbcdEFGH"),  # H, A and B flip
    ("generator_b", "AbCdEFGh"),  # A, B and C flip
    ("generator_c", "abCDEFGh"),  # B, C and D flip
    ("generator_d", "aBCDeFGh"),  # C, D and E flip
    ("generator_e", "aBcDefGh"),  # D, E and F flip
    ("generator_f", "aBcdefgh"),  # E, F and G flip
    ("generator_g", "aBcdEfgH"),  # F, G and H flip
    ("generator_h", "ABcdEFgH"),  # G, H and A flip
])
def test_m5_a_generator_flips_itself_and_the_two_next_to_it(generator, after):
    """From the start, each generator flips itself and its two neighbours in the ring, and no other."""
    in_cabin = play([TO_CABIN])
    state, outcome = engine.activate(in_cabin, generator)
    assert outcome["event"] == "toggled"
    assert generators(state) == after
    assert not state["flags"]["cabin_solved"]


def test_m5_activating_a_generator_twice_undoes_it():
    in_cabin = play([TO_CABIN])
    for generator in GENERATORS:
        once, _ = engine.activate(in_cabin, generator)
        twice, _ = engine.activate(once, generator)
        assert generators(twice) == START, generator


@pytest.mark.parametrize("first, last", [(ACTIVATE_A, ACTIVATE_C), (ACTIVATE_C, ACTIVATE_A)])
def test_m5_all_eight_on_dissolves_the_barrier(first, last):
    """Two levers, as with four generators: the message, the barrier gone, and the key can be taken from the altar."""
    state = play([TO_CABIN, first])
    assert not state["flags"]["cabin_solved"]  # one generator is not enough
    state, outcome = engine.perform(state, last)
    assert outcome["event"] == "circuit_complete"
    assert outcome["text"] == story.CIRCUITS["cabin_circuit"]["solved_text"]
    assert generators(state) == ALL_ON
    here = {thing["id"]: thing["status"] for thing in engine.things_here(state)}
    assert "barrier" not in here
    assert here["key"] == "on_floor"
    _, outcome = engine.pick_up(state, "key")
    assert outcome["event"] == "picked_up"


def test_m5_the_fewest_levers_are_two():
    """The difficulty did not grow with the generators: no single lever solves it, and two do."""
    in_cabin = play([TO_CABIN])
    for generator in GENERATORS:
        _, outcome = engine.activate(in_cabin, generator)
        assert outcome["event"] == "toggled", generator


def test_m5_every_configuration_of_the_generators_can_be_completed():
    """Whatever the player does, the circuit can still be completed: the puzzle has no dead ends.

    Pulling a lever twice undoes it, so the levers can be walked back. A search
    from the start that never goes past the complete circuit still reaches every
    one of the 256 configurations: from each of them there is a way to all eight on.
    On the way, every pull is checked: the circuit is complete exactly when all eight are on.
    """
    start = play([TO_CABIN])
    seen = {generators(start)}
    frontier = [start]
    while frontier:
        further = []
        for state in frontier:
            for generator in GENERATORS:
                after, outcome = engine.activate(state, generator)
                assert (outcome["event"] == "circuit_complete") == (generators(after) == ALL_ON)
                if generators(after) not in seen:
                    seen.add(generators(after))
                    if outcome["event"] != "circuit_complete":
                        further.append(after)
        frontier = further
    assert len(seen) == 2 ** len(GENERATORS)


def test_m5_a_complete_circuit_stays_on():
    complete = play([TO_CABIN] + SOLVE_CABIN)
    for generator in GENERATORS:
        after, outcome = engine.activate(complete, generator)
        assert outcome["event"] == "already_done"
        assert after == complete


def test_m5_walking_back_in_finds_the_starting_configuration():
    """Until the circuit is complete, entering the cabin always finds H, A, C and D off."""
    state = play([TO_CABIN, ACTIVATE_B, ACTIVATE_C])
    assert generators(state) != START
    state = play([CABIN_TO_DECK, TO_CABIN], state)
    assert generators(state) == START


def test_m5_a_complete_circuit_is_remembered():
    state = play([TO_CABIN] + SOLVE_CABIN + [CABIN_TO_DECK, TO_CABIN])
    assert generators(state) == ALL_ON
    assert state["flags"]["cabin_solved"]


def test_m5_resuming_keeps_the_generators_as_they_were():
    """A4: reopening the game is not walking in again: the generators are as the player left them."""
    state = play([TO_CABIN, ACTIVATE_B])
    assert generators(reopen(state)) == generators(state)


def test_m5_the_key_waits_behind_the_barrier():
    """R2 and PT04: the key can be seen but not taken, the reason is given, and E only lets you look at it."""
    in_cabin = play([TO_CABIN])
    after, outcome = engine.pick_up(in_cabin, "key")
    assert outcome["event"] == "guarded"
    assert outcome["text"].strip()
    assert after == in_cabin
    assert offered(in_cabin, "key") == [("examine", None)]
    _, outcome = engine.examine(in_cabin, "barrier")
    assert outcome["text"] == story.OBJECTS["barrier"]["look_text"]


def test_m5_a_dissolved_barrier_is_gone():
    complete = play([TO_CABIN] + SOLVE_CABIN)
    _, outcome = engine.examine(complete, "barrier")
    assert outcome["event"] == "not_here"
    assert offered(complete, "barrier") == []


# --- M5: the tiles of the hold ---------------------------------------------------------

TILES = ["tile_1", "tile_2", "tile_3", "tile_4", "tile_5"]
IN_HOLD = GET_KEY + [TO_HOLD]


def lit(state):
    """The numbers of the lit tiles, in order: "125" is tiles 1, 2 and 5 lit."""
    numbers = ""
    for thing in engine.things_here(state):
        if thing["kind"] == "tile" and thing["status"] == "lit":
            numbers += story.OBJECTS[thing["id"]]["label"]
    return numbers


def phase_and_step(state):
    return state["flags"]["hold_phase"], state["flags"]["hold_step"]


def test_m5_the_tiles_start_dark_with_the_barrier_up():
    in_hold = play(IN_HOLD)
    assert phase_and_step(in_hold) == (1, 0)
    assert lit(in_hold) == ""
    here = {thing["id"]: thing["status"] for thing in engine.things_here(in_hold)}
    assert here["hold_barrier"] == "up"
    assert here["second_key"] == "guarded"


def test_m5_phase_1_lights_the_wave_one_tile_at_a_time():
    """1, 2, 3, 4, 5: each tile lights up; the fifth completes the phase, and only it stays lit for phase 2."""
    state = play(IN_HOLD)
    for number in range(1, 5):
        state, outcome = engine.perform(state, step(number))
        assert outcome["event"] == "tile_lit"
        assert lit(state) == "1234"[:number]
    state, outcome = engine.perform(state, step(5))
    assert outcome["event"] == "phase_complete"
    puzzle = story.FLOOR_PUZZLES["hold_tiles"]
    assert outcome["text"] == puzzle["phase_text"].format(number=2, name=puzzle["phases"][1]["name"])
    assert phase_and_step(state) == (2, 1)
    assert lit(state) == "5"


def test_m5_phase_2_returns_from_5_to_1():
    state = play(IN_HOLD + PHASE_1)
    state, outcome = engine.perform(state, step(3))
    assert outcome["event"] == "tile_lit"
    assert lit(state) == "35"
    state, outcome = engine.perform(state, step(1))
    assert outcome["event"] == "phase_complete"
    assert phase_and_step(state) == (3, 1)
    assert lit(state) == "1"


def test_m5_phase_3_short_circuits_and_dissolves_the_barrier():
    """1, 5, 2, 4, 3: the last tile solves the puzzle: the message, the barrier gone, the second half free."""
    state = play(IN_HOLD + PHASE_1 + PHASE_2 + PHASE_3[:-1])
    assert lit(state) == "1245"
    assert not state["flags"]["hold_solved"]
    state, outcome = engine.perform(state, PHASE_3[-1])
    assert outcome["event"] == "tiles_complete"
    assert outcome["text"] == story.FLOOR_PUZZLES["hold_tiles"]["solved_text"]
    assert state["flags"]["hold_solved"]
    assert lit(state) == "12345"
    here = {thing["id"]: thing["status"] for thing in engine.things_here(state)}
    assert "hold_barrier" not in here
    assert here["second_key"] == "on_floor"
    _, outcome = engine.pick_up(state, "second_key")
    assert outcome["event"] == "picked_up"


@pytest.mark.parametrize("done, wrong", [
    pytest.param([step(1), step(2)], step(4), id="phase 1"),
    pytest.param(PHASE_1 + [step(3)], step(5), id="phase 2, back on a tile lit earlier"),
    pytest.param(PHASE_1 + PHASE_2 + [step(5)], step(3), id="phase 3"),
])
def test_m5_a_wrong_tile_starts_the_same_phase_over(done, wrong):
    """BZZZ: the lights go out and the phase starts over from its first tile; the phases before stay done."""
    state = play(IN_HOLD + done)
    phase, _ = phase_and_step(state)
    after, outcome = engine.perform(state, wrong)
    assert outcome["event"] == "tiles_reset"
    assert outcome["text"] == story.FLOOR_PUZZLES["hold_tiles"]["wrong_text"]
    assert phase_and_step(after) == (phase, 0)
    assert lit(after) == ""
    first = story.FLOOR_PUZZLES["hold_tiles"]["phases"][phase - 1]["steps"][0]
    again, outcome = engine.step_on(after, first)
    assert outcome["event"] == "tile_lit"
    assert phase_and_step(again) == (phase, 1)


def test_m5_a_wrong_tile_before_the_first_one_is_a_mistake_too():
    """Nothing is lit yet, but the player still hears and reads that the tile is wrong."""
    state = play(IN_HOLD)
    after, outcome = engine.perform(state, step(3))
    assert outcome["ok"]
    assert outcome["event"] == "tiles_reset"
    assert phase_and_step(after) == (1, 0)


@pytest.mark.parametrize("done", [
    pytest.param([step(1), step(2)], id="back onto 2"),
    pytest.param(PHASE_1, id="back onto 5, where phase 2 starts"),
    pytest.param(PHASE_1 + PHASE_2, id="back onto 1, where phase 3 starts"),
])
def test_m5_stepping_back_onto_the_tile_lit_last_changes_nothing(done):
    state = play(IN_HOLD + done)
    after, outcome = engine.perform(state, done[-1])
    assert not outcome["ok"]
    assert outcome["event"] == "already_lit"
    assert after == state


def test_m5_walking_out_of_the_zone_starts_the_phase_over():
    state = play(IN_HOLD + PHASE_1 + [step(3)])
    after, outcome = engine.perform(state, LEAVE_TILES)
    assert outcome["event"] == "tiles_reset"
    assert outcome["text"] == story.FLOOR_PUZZLES["hold_tiles"]["left_text"]
    assert phase_and_step(after) == (2, 0)
    assert lit(after) == ""


def test_m5_walking_out_with_nothing_lit_changes_nothing():
    state = play(IN_HOLD + [step(1), step(3)])  # a mistake: nothing is lit any more
    after, outcome = engine.perform(state, LEAVE_TILES)
    assert not outcome["ok"]
    assert after == state


def test_m5_walking_out_of_the_hold_starts_the_phase_over():
    """The engine does not need main.py for this: walking out of the room is walking out of the zone."""
    state = play(IN_HOLD + PHASE_1 + [step(3), HOLD_TO_DECK, TO_HOLD])
    assert phase_and_step(state) == (2, 0)
    assert lit(state) == ""


def test_m5_the_only_shortest_way_through_the_tiles_is_the_three_sequences():
    """Every tile tried at every moment: the puzzle has no shortcut and no other solution.

    The fewest steps that solve it are 1 2 3 4 5, then 3 1, then 5 2 4 3, and no
    other path of that length solves it.
    """
    start = play(IN_HOLD)
    paths = {phase_and_step(start): [[]]}  # every shortest path found to each moment of the puzzle
    frontier = [start]
    solutions = []
    while frontier and not solutions:
        found = {}
        for state in frontier:
            for path in paths[phase_and_step(state)]:
                for tile in TILES:
                    after, outcome = engine.step_on(state, tile)
                    if outcome["event"] == "tiles_complete":
                        solutions.append(path + [tile])
                    elif phase_and_step(after) not in paths:
                        found.setdefault(phase_and_step(after), (after, []))[1].append(path + [tile])
        for moment, (state, moment_paths) in found.items():
            paths[moment] = moment_paths
        frontier = [state for state, _ in found.values()]
    assert solutions == [[f"tile_{number}" for number in (1, 2, 3, 4, 5, 3, 1, 5, 2, 4, 3)]]


def test_m5_from_any_moment_the_rest_of_the_sequences_solves_it():
    """No dead ends: in any phase, with any number of tiles lit, finishing the sequences solves the puzzle."""
    phases = story.FLOOR_PUZZLES["hold_tiles"]["phases"]
    for phase, info in enumerate(phases, start=1):
        for done in range(len(info["steps"])):
            state = play(IN_HOLD)
            state["flags"]["hold_phase"] = phase
            state["flags"]["hold_step"] = done
            rest = info["steps"][done:]
            for later in phases[phase:]:
                rest = rest + later["steps"][1:]  # each later phase starts on the tile lit last
            for tile in rest:
                state, outcome = engine.step_on(state, tile)
                assert outcome["ok"], (phase, done, tile, outcome)
            assert state["flags"]["hold_solved"], (phase, done)


def test_m5_solved_tiles_stay_lit_and_do_nothing_more():
    solved = play(IN_HOLD + SOLVE_TILES)
    for action in [step(number) for number in range(1, 6)] + [LEAVE_TILES]:
        after, outcome = engine.perform(solved, action)
        assert outcome["event"] == "already_done"
        assert after == solved


def test_m5_resuming_keeps_the_phase_and_the_lit_tiles():
    """A4: closing the game in the middle of a phase and reopening it gives back the same moment."""
    state = play(IN_HOLD + PHASE_1 + [step(3)])
    resumed = reopen(state)
    assert resumed == state
    assert lit(resumed) == "35"


# --- Saving and resuming -----------------------------------------------------------


def test_persistence_every_accepted_action_survives_a_restart():
    """Progress is saved after each accepted action: reopening at any moment gives back the game in play."""
    for state in sample_states():
        for action in every_action():
            new_state, outcome = save_if_accepted(engine.perform(state, action))
            if outcome["ok"]:
                assert resume() == new_state, f"{action} was not saved"


def test_persistence_refused_actions_leave_the_file_untouched(save_file):
    """Rejected actions leave existing data unchanged, and the game on screen still matches the file."""
    state = play_saving(GET_FUSED_KEY + [OPEN_CRAB])
    saved_bytes = save_file.read_bytes()
    for action in (TO_ANGEL, OPEN_CRAB, TAKE_WAND, WAND_ON_BARREL, GIVE_TO_CRAB, step(1), LEAVE_TILES):
        state, outcome = save_if_accepted(engine.perform(state, action))
        assert not outcome["ok"]
        assert save_file.read_bytes() == saved_bytes
        assert resume() == state


def test_persistence_resume_needs_a_usable_save(save_file):
    """No file, a broken file or an impossible game: the menu offers only a new game."""
    assert engine.menu_options(resume()) == ["new_game"]
    save_file.write_text("{ not json", encoding="utf-8")
    assert engine.menu_options(resume()) == ["new_game"]
    save_file.write_text(json.dumps({"version": save.VERSION, "state": {"room": "bridge"}}), encoding="utf-8")
    assert engine.menu_options(resume()) == ["new_game"]
    play_saving([TAKE_WAND])
    assert engine.menu_options(resume()) == ["new_game", "resume"]


def test_save_state_survives_json_unchanged():
    """No tuples or sets: what goes into the save file comes back identical."""
    for state in sample_states():
        assert reopen(state) == state


def restorable(**changes):
    """A valid saved game, with some keys replaced."""
    data = {"room": "deck", "inventory": [], "flags": dict(story.FLAGS), "ending": None}
    data.update(changes)
    return data


def without(key):
    """A valid saved game with one key missing."""
    data = restorable()
    del data[key]
    return data


@pytest.mark.parametrize("data", [
    pytest.param(None, id="nothing"),
    pytest.param([], id="not a dict"),
    pytest.param(without("ending"), id="missing key"),
    pytest.param(restorable(position=[3, 4]), id="unknown key"),
    pytest.param(restorable(room="bridge"), id="unknown room"),
    pytest.param(restorable(room=["deck"]), id="room of the wrong type"),
    pytest.param(restorable(inventory="wand"), id="inventory not a list"),
    pytest.param(restorable(inventory=["sword"]), id="unknown item"),
    pytest.param(restorable(inventory=["wand", "wand"]), id="duplicate item"),
    pytest.param(restorable(flags=[]), id="flags not a dict"),
    pytest.param(restorable(flags={"lucky": True}), id="unknown flag"),
    pytest.param(restorable(flags={"cabin_solved": "yes"}), id="wrong flag value"),
    pytest.param(restorable(flags={"cabin_solved": 1}), id="1 is not True"),
    pytest.param(restorable(flags={"crab_door": "deck_to_cabin"}), id="not a choice door"),
    pytest.param(restorable(flags={"crab_door": "deck_to_angel"}), id="the angel's door in the crab's flag"),
    pytest.param(restorable(inventory=["key", "fused_key"]), id="a half next to the fused key"),
    pytest.param(restorable(flags={"hold_phase": 4}), id="no phase 4"),
    pytest.param(restorable(flags={"hold_phase": "1"}), id="phase as text"),
    pytest.param(restorable(flags={"hold_step": 6}), id="more steps than any phase"),
    pytest.param(restorable(flags={"hold_step": True}), id="True is not a step"),
    pytest.param(restorable(flags={"hold_phase": 2, "hold_step": 3}), id="phase 2 has only three steps"),
    pytest.param(restorable(flags={"hold_step": 5}), id="a finished phase that did not go on"),
    pytest.param(restorable(ending="happy"), id="unknown ending"),
])
def test_restore_state_rejects_broken_saves(data):
    assert engine.restore_state(data) is None


def test_restore_state_fills_in_missing_flags():
    """A save made before a flag existed still loads, with the flag at its starting value."""
    data = restorable(flags={"cabin_solved": True})
    restored = engine.restore_state(data)
    expected = dict(story.FLAGS)
    expected["cabin_solved"] = True
    assert restored["flags"] == expected


def test_restore_state_accepts_every_moment_of_the_tiles():
    """Any phase with fewer lit tiles than its sequence is a valid saved game, and so is the solved puzzle."""
    for phase, info in enumerate(story.FLOOR_PUZZLES["hold_tiles"]["phases"], start=1):
        for lit in range(len(info["steps"])):
            data = restorable(flags={"hold_phase": phase, "hold_step": lit})
            assert engine.restore_state(data) is not None, (phase, lit)
    assert engine.restore_state(restorable(flags={"hold_phase": 3, "hold_step": 5, "hold_solved": True})) is not None


def test_restore_state_returns_a_copy():
    data = play(GET_KEY)
    restored = engine.restore_state(data)
    restored["inventory"].clear()
    restored["flags"]["cabin_solved"] = False
    assert data == play(GET_KEY)


# --- Bugs in the calling code are not refusals ----------------------------------


def test_unknown_ids_raise_errors():
    state = engine.new_game()
    with pytest.raises(ValueError):
        engine.pick_up(state, "sword")
    with pytest.raises(ValueError):
        engine.enter(state, "wand")  # an item is not a door
    with pytest.raises(ValueError):
        engine.use_item(state, "wand", "sword")
    with pytest.raises(ValueError):
        engine.perform(state, act("jump", "deck"))
    with pytest.raises(ValueError):
        engine.activate(state, "crab")  # a character is not a generator
    with pytest.raises(ValueError):
        engine.step_on(state, "generator_a")  # a generator is not a tile
    with pytest.raises(ValueError):
        engine.leave_zone(state, "hold")  # a room is not a floor puzzle
    with pytest.raises(ValueError):
        engine.examine(state, "hold_tiles")  # a floor puzzle is walked on, not looked at
    with pytest.raises(ValueError):
        engine.use_item(state, "wand", "hold_tiles")
    assert engine.actions_for(state, "hold_tiles") == []


# --- The story data --------------------------------------------------------------


def all_ids():
    return list(story.ROOMS) + list(story.ITEMS) + list(story.DOORS) + list(story.OBJECTS) + list(story.FLOOR_PUZZLES)


def test_story_has_what_the_first_release_needs():
    """At least five scenes, two collectible items and two endings."""
    assert len(story.ROOMS) >= 5
    assert len(story.ITEMS) >= 2
    assert len(story.ENDINGS) >= 2


def test_story_ids_are_unique():
    assert len(all_ids()) == len(set(all_ids()))


def test_story_references_exist():
    assert story.START_ROOM in story.ROOMS
    for item_id, item in story.ITEMS.items():
        made = [part for part, info in story.ITEMS.items() if info["part_of"] == item_id]
        if made:  # made at the anvil from at least two parts, never lying around
            assert len(made) >= 2 and item["room"] is None and item["pos"] is None, item_id
        else:
            assert item["room"] in story.ROOMS, item_id
        assert item["part_of"] is None or item["part_of"] in story.ITEMS, item_id
        assert item["appears_if"] is None or item["appears_if"] in story.FLAGS
        assert item["free_if"] is None or item["free_if"] in story.FLAGS
    for door in story.DOORS.values():
        assert door["room"] in story.ROOMS
        assert door["to"] in story.ROOMS
        for item in door["requires"]:
            assert item in story.ITEMS
        assert door["opens_with"] is None or door["opens_with"] in story.ITEMS
        assert door["choice_flag"] is None or door["choice_flag"] in story.FLAGS
    for thing in story.OBJECTS.values():
        assert thing["room"] in story.ROOMS
        for item, reaction in thing["reactions"].items():
            assert item in story.ITEMS
            if "ending" in reaction:
                assert reaction["ending"] in story.ENDINGS
            else:
                assert reaction["set_flag"] in story.FLAGS
    for flag in story.CLUES:
        assert flag in story.FLAGS
    for circuit_id, circuit in story.CIRCUITS.items():
        assert circuit["room"] in story.ROOMS, circuit_id
        assert circuit["solved_flag"] in story.FLAGS, circuit_id
        for switch in circuit["switches"]:
            assert story.OBJECTS[switch]["kind"] == "switch", (circuit_id, switch)
            assert story.OBJECTS[switch]["room"] == circuit["room"], (circuit_id, switch)
    for puzzle_id, puzzle in story.FLOOR_PUZZLES.items():
        assert puzzle["room"] in story.ROOMS, puzzle_id
        for key in ("phase_flag", "step_flag", "solved_flag"):
            assert puzzle[key] in story.FLAGS, (puzzle_id, key)
        for phase in puzzle["phases"]:
            for tile in phase["steps"]:
                assert story.OBJECTS[tile]["kind"] == "tile", (puzzle_id, tile)
                assert story.OBJECTS[tile]["room"] == puzzle["room"], (puzzle_id, tile)


def test_story_every_door_has_a_way_back():
    links = set()
    for door in story.DOORS.values():
        links.add((door["room"], door["to"]))
    for room, to in links:
        assert (to, room) in links, f"no way back from {to} to {room}"


def test_story_every_room_can_be_reached():
    """Through doors or portals, every room can be reached from the start."""
    links = [(door["room"], door["to"]) for door in story.DOORS.values()]
    for info in story.OBJECTS.values():
        if info["kind"] == "portal" and info["to"] is not None:
            links.append((info["room"], story.OBJECTS[info["to"]]["room"]))
    reached = {story.START_ROOM}
    grew = True
    while grew:
        grew = False
        for room, to in links:
            if room in reached and to not in reached:
                reached.add(to)
                grew = True
    assert reached == set(story.ROOMS)


def test_story_portals_come_in_pairs():
    """Each portal leads to another portal, in another room: one that leads back, or one that only receives.

    A portal that only receives is the end of exactly one portal.
    """
    for portal, info in story.OBJECTS.items():
        if info["kind"] != "portal":
            continue
        if info["to"] is None:
            senders = [other for other, more in story.OBJECTS.items() if more.get("to") == portal]
            assert len(senders) == 1, portal
            continue
        twin = story.OBJECTS[info["to"]]
        assert twin["kind"] == "portal" and twin["to"] in (portal, None), portal
        assert twin["room"] != info["room"], portal


def test_the_mine_portal_leads_one_way_to_the_helm():
    """From the bottom of the mine to the helm; from the helm, the ring does nothing at all."""
    state = engine.new_game()
    state["room"] = "mine"
    there, outcome = engine.travel(state, "mine_exit")
    assert outcome["event"] == "teleported" and there["room"] == "helm"
    assert "helm" in engine.visited_rooms(there)
    after, outcome = engine.travel(there, "helm_portal")
    assert not outcome["ok"] and outcome["event"] == "nothing_happens"
    assert after == there
    assert engine.actions_for(there, "helm_portal") == []  # E offers nothing either
    assert "helm_portal" in [thing["id"] for thing in engine.things_here(there)]  # but it is there to see


def test_travel_through_the_portal_and_back():
    state = engine.new_game()
    state["room"] = "corridor_end"
    there, outcome = engine.travel(state, "corridor_portal")
    assert outcome["event"] == "teleported" and there["room"] == "mine"
    assert "mine" in engine.visited_rooms(there)
    back, _ = engine.travel(there, "mine_portal")
    assert back["room"] == "corridor_end"
    _, outcome = engine.travel(state, "mine_portal")
    assert outcome["event"] == "not_here"
    assert offered(state, "corridor_portal") == [("examine", None)]


def test_story_locked_doors_are_complete():
    """A door with a lock has a choice flag and its texts; a door without one has neither.

    The sealed text is needed only when doors share a choice flag. A barred door says what bars it.
    """
    for door_id, door in story.DOORS.items():
        assert isinstance(door["requires"], list), door_id
        locked = bool(door["requires"])
        assert (door["choice_flag"] is not None) == locked, door_id
        if locked:
            for key in ("locked_text", "open_text"):
                assert door[key].strip(), f"{door_id} has no {key}"
            sharing = [other for other in story.DOORS.values() if other["choice_flag"] == door["choice_flag"]]
            if len(sharing) > 1:
                assert door["sealed_text"].strip(), f"{door_id} has no sealed_text"
        barred = door["opens_with"] is not None
        assert (door["barred_text"] is not None) == barred, door_id
        if barred:
            assert door["barred_text"].strip(), door_id


def test_story_objects_are_well_formed():
    for thing_id, thing in story.OBJECTS.items():
        assert thing["kind"] in ("puzzle", "character", "switch", "tile", "barrier", "altar", "anvil", "decor",
                                 "cauldron", "portal"), thing_id
        for key in ("appears_if", "gone_if"):
            assert thing.get(key) is None or thing[key] in story.FLAGS, (thing_id, key)
        if thing["kind"] == "decor":
            assert isinstance(thing["solid"], bool), thing_id
            assert thing["picture"].startswith("decor_"), thing_id
            assert not thing["reactions"], f"{thing_id} is decor: it reacts to nothing"
        assert thing["name"].strip()
        assert thing["look_text"].strip()
        if thing["kind"] in ("puzzle", "character"):
            assert thing["reactions"], f"{thing_id} reacts to nothing"
        if thing["kind"] == "switch":
            assert thing["flag"] in story.FLAGS, thing_id
            assert thing["flag"] in thing["toggles"], f"{thing_id} must switch itself over"
            for flag in thing["toggles"]:
                assert flag in story.FLAGS, (thing_id, flag)
            assert thing["toggle_text"].strip() and thing["label"].strip(), thing_id
            in_circuits = [c for c in story.CIRCUITS.values() if thing_id in c["switches"]]
            assert len(in_circuits) == 1, f"{thing_id} must be in exactly one circuit"
        if thing["kind"] == "tile":
            assert thing["label"].strip(), thing_id
            puzzles = [puzzle for puzzle in story.FLOOR_PUZZLES.values()
                       if any(thing_id in phase["steps"] for phase in puzzle["phases"])]
            assert len(puzzles) == 1, f"{thing_id} must be in exactly one floor puzzle"
        if thing["kind"] == "barrier":
            assert thing["open_if"] in story.FLAGS, thing_id
        if thing["kind"] == "anvil":
            assert thing["fuse_text"].strip(), thing_id
        for reaction in thing["reactions"].values():
            # Exactly one effect: set a flag or end the game.
            assert ("ending" in reaction) != ("set_flag" in reaction), thing_id
            assert reaction["text"].strip()
        if thing["kind"] == "puzzle":
            assert thing["done_text"].strip(), f"{thing_id} has no done_text"
            for reaction in thing["reactions"].values():
                assert "set_flag" in reaction, f"{thing_id} is a puzzle: it sets a flag, it does not end the game"


def test_story_floor_puzzles_are_well_formed():
    """Flags that start at phase 1 with nothing lit, and phases that each start on the tile the one before ended on."""
    for puzzle_id, puzzle in story.FLOOR_PUZZLES.items():
        assert type(story.FLAGS[puzzle["phase_flag"]]) is int and story.FLAGS[puzzle["phase_flag"]] == 1, puzzle_id
        assert type(story.FLAGS[puzzle["step_flag"]]) is int and story.FLAGS[puzzle["step_flag"]] == 0, puzzle_id
        assert story.FLAGS[puzzle["solved_flag"]] is False, puzzle_id
        for index, phase in enumerate(puzzle["phases"]):
            assert phase["name"].strip() and phase["steps"], (puzzle_id, index)
            if index > 0:
                assert phase["steps"][0] == puzzle["phases"][index - 1]["steps"][-1], (puzzle_id, index)


def test_story_texts_are_not_empty():
    for room in story.ROOMS.values():
        assert room["name"].strip()
        assert room["description"].strip()
    for item in story.ITEMS.values():
        assert item["name"].strip()
        assert item["description"].strip()
        if item["room"] is not None:  # only what lies somewhere is picked up
            assert item["pickup_text"].strip()
    for ending in story.ENDINGS.values():
        assert ending["title"].strip()
        assert ending["text"]
        for line in ending["text"]:
            assert line.strip()
    for text in story.CLUES.values():
        assert text.strip()
    for circuit in story.CIRCUITS.values():
        assert circuit["solved_text"].strip()
    for puzzle in story.FLOOR_PUZZLES.values():
        for key in ("lit_text", "phase_text", "wrong_text", "left_text", "solved_text"):
            assert puzzle[key].strip()
    for text in story.MESSAGES.values():
        assert text.strip()




# --- The infirmary: the remedy, the doctor and his gift ----------------------------

IN_INFIRMARY = GET_KEY + [TO_HOLD, TO_INFIRMARY]  # nothing found yet
WITH_THE_TINCTURES = GET_KEY + [TO_HOLD] + GATHER_TINCTURES + [TO_INFIRMARY]  # all four in hand
TINCTURES = story.POTION_PUZZLES["remedy"]["recipe"]
SCATTERED = {"red_tincture": "galley", "gold_tincture": "helm", "blue_tincture": "corridor"}


def lies_in_its_room(state, item):
    """True if the item lies on the floor of its room right now, for a player standing there."""
    there = dict(state, room=story.ITEMS[item]["room"])
    return item in [thing["id"] for thing in engine.things_here(there)]


def test_tinctures_the_green_one_waits_in_the_infirmary_and_the_others_hide():
    """At first only the green tincture can be found; the other three are nowhere on the ship."""
    state = play(IN_INFIRMARY)
    assert "green_tincture" in [thing["id"] for thing in engine.things_here(state)]
    for tincture, room in SCATTERED.items():
        assert story.ITEMS[tincture]["room"] == room
        assert not lies_in_its_room(state, tincture), tincture
        elsewhere = dict(state, room=room)
        assert tincture not in [thing["id"] for thing in engine.things_here(elsewhere)], tincture
        _, outcome = engine.pick_up(elsewhere, tincture)
        assert outcome["event"] == "not_here", tincture


def test_tinctures_picking_up_the_green_one_scatters_the_others():
    """With the green tincture in hand, the other three appear in the galley, the helm and the corridor."""
    state = play(IN_INFIRMARY + [TAKE_GREEN])
    assert state["flags"]["tinctures_scattered"]
    for tincture, room in SCATTERED.items():
        assert lies_in_its_room(state, tincture), tincture
        elsewhere = dict(state, room=room)
        assert tincture in [thing["id"] for thing in engine.things_here(elsewhere)], tincture
    assert play(GET_KEY + [TO_HOLD] + GATHER_TINCTURES)["inventory"][-4:] == [
        "green_tincture", "blue_tincture", "red_tincture", "gold_tincture"]


def test_potion_the_recipe_in_order_makes_the_remedy():
    """Each tincture of the recipe moves the cauldron on; the last one makes the remedy appear in it."""
    puzzle = story.POTION_PUZZLES["remedy"]
    state = play(WITH_THE_TINCTURES)
    assert "potion" not in [thing["id"] for thing in engine.things_here(state)]
    for number, tincture in enumerate(TINCTURES, start=1):
        state, outcome = engine.use_item(state, tincture, "cauldron")
        if number < len(TINCTURES):
            assert outcome["event"] == "potion_poured"
            assert outcome["text"] == puzzle["pour_texts"][tincture]
            assert state["flags"]["potion_step"] == number
            assert tincture in state["inventory"]  # still in hand until the remedy is made
    assert outcome["event"] == "potion_ready"
    assert outcome["text"] == puzzle["solved_text"]
    assert state["flags"]["potion_solved"] and state["flags"]["potion_step"] == 0
    assert "potion" in [thing["id"] for thing in engine.things_here(state)]
    for tincture in TINCTURES:
        assert tincture not in state["inventory"], tincture  # used up
        assert not lies_in_its_room(state, tincture), tincture


def test_potion_a_wrong_tincture_spoils_the_mixture_but_keeps_the_bottles():
    """Out of order, the cauldron empties and the recipe starts over; the bottles stay in hand to try again."""
    green, red, gold, blue = TINCTURES
    state = play(WITH_THE_TINCTURES + [act("use_item", "cauldron", item=green), act("use_item", "cauldron", item=red)])
    after, outcome = engine.use_item(state, blue, "cauldron")  # the gold had to come first
    assert outcome["ok"] and outcome["event"] == "potion_spoiled"
    assert after["flags"]["potion_step"] == 0
    assert not after["flags"]["potion_solved"]
    assert after["inventory"] == state["inventory"]
    assert play(RECIPE, after)["flags"]["potion_solved"]  # starting over still works
    _, outcome = engine.use_item(play(IN_INFIRMARY + [TAKE_GREEN, TO_CORRIDOR, TAKE_BLUE, CORRIDOR_TO_INFIRMARY]),
                                 blue, "cauldron")
    assert outcome["event"] == "potion_spoiled"  # a wrong first one spoils it too


def test_potion_the_cauldron_wants_only_its_tinctures():
    state = play(WITH_THE_TINCTURES)
    after, outcome = engine.use_item(state, "wand", "cauldron")
    assert outcome["event"] == "nothing_happens" and after == state
    after, outcome = engine.use_item(state, "green_tincture", "doctor")
    assert outcome["event"] == "nothing_happens" and after == state


def test_potion_the_cauldron_is_done_once_the_remedy_is_made():
    state = play(WITH_THE_TINCTURES + RECIPE)
    offered_items = [action["item"] for action in engine.actions_for(state, "cauldron")]
    assert not set(offered_items) & set(TINCTURES)  # the bottles are used up: nothing left to pour
    for item in state["inventory"]:
        after, outcome = engine.use_item(state, item, "cauldron")
        assert not outcome["ok"] and after == state


def test_potion_pouring_is_offered_on_the_cauldron_for_each_tincture():
    state = play(WITH_THE_TINCTURES)
    labels = {action["item"]: action["label"] for action in engine.actions_for(state, "cauldron")}
    for tincture in TINCTURES:
        assert labels[tincture] == story.MESSAGES["label_pour"].format(name=story.ITEMS[tincture]["name"])
    assert labels["wand"] == story.MESSAGES["label_use"].format(item=story.ITEMS["wand"]["name"])


def test_heart_waits_in_the_mine():
    state = engine.new_game()
    state["room"] = "mine"
    assert "heart" in [thing["id"] for thing in engine.things_here(state)]
    after, outcome = engine.pick_up(state, "heart")
    assert outcome["event"] == "picked_up" and after["inventory"] == ["heart"]


def test_doctor_drinks_the_remedy_vanishes_and_the_anvil_appears_in_the_galley():
    before = play(WITH_THE_TINCTURES + RECIPE + [TAKE_POTION])
    in_galley = play([INFIRMARY_TO_HOLD, HOLD_TO_DECK, TO_CABIN, CABIN_TO_GALLEY], before)
    assert "anvil" not in [thing["id"] for thing in engine.things_here(in_galley)]
    after, outcome = engine.use_item(before, "potion", "doctor")
    assert outcome["event"] == "flag_set" and after["flags"]["doctor_at_peace"]
    here = [thing["id"] for thing in engine.things_here(after)]
    assert "doctor" not in here and "potion" not in here  # gone, and the cauldron gives no second remedy
    assert "potion" not in after["inventory"]  # drunk
    in_galley = play([INFIRMARY_TO_HOLD, HOLD_TO_DECK, TO_CABIN, CABIN_TO_GALLEY], after)
    assert "anvil" in [thing["id"] for thing in engine.things_here(in_galley)]


def test_doctor_wants_nothing_but_the_remedy():
    state = play(IN_INFIRMARY)
    after, outcome = engine.use_item(state, "wand", "doctor")
    assert outcome["event"] == "nothing_happens"
    assert after == state


def test_restore_rejects_an_impossible_cauldron_or_remedy():
    good = play(WITH_THE_TINCTURES + RECIPE + [TAKE_POTION])
    assert engine.restore_state(good) == good
    for flags in ({"potion_step": 4}, {"potion_step": 2, "potion_solved": True}, {"doctor_at_peace": True}):
        broken = copy.deepcopy(good)
        broken["flags"].update(flags)
        assert engine.restore_state(broken) is None, flags


def test_restore_rejects_impossible_tinctures():
    """A tincture carried before it appeared, or after the remedy used it up, cannot be in a save."""
    holding_green = play(IN_INFIRMARY + [TAKE_GREEN])
    assert engine.restore_state(holding_green) == holding_green
    early = copy.deepcopy(holding_green)
    early["inventory"].append("red_tincture")
    early["flags"]["tinctures_scattered"] = False
    assert engine.restore_state(early) is None
    late = copy.deepcopy(holding_green)
    late["flags"]["potion_solved"] = True
    assert engine.restore_state(late) is None


def test_entering_a_room_marks_it_on_the_map():
    state = engine.new_game()
    assert engine.visited_rooms(state) == ["deck"]
    state = play([TO_CABIN, CABIN_TO_GALLEY], state)
    assert set(engine.visited_rooms(state)) == {"deck", "cabin", "galley"}
    for room in story.ROOMS:
        assert story.FLAGS["visited_" + room] == (room == story.START_ROOM), room


def test_a_new_game_remembers_the_character_chosen():
    assert engine.new_game()["flags"]["character"] == "green"
    state, outcome = engine.start_new_game(None, character="red")
    assert outcome["ok"] and state["flags"]["character"] == "red"
    assert reopen(state)["flags"]["character"] == "red"
    with pytest.raises(ValueError):
        engine.new_game("blue")
    assert engine.restore_state(restorable(flags={"character": "blue"})) is None
