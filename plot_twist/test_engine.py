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
TO_CABIN = act("enter", "deck_to_cabin")
TO_HOLD = act("enter", "deck_to_hold")
TO_CRAB = act("enter", "deck_to_crab")
TO_ANGEL = act("enter", "deck_to_angel")
CABIN_TO_DECK = act("enter", "cabin_to_deck")
HOLD_TO_DECK = act("enter", "hold_to_deck")
CRAB_TO_DECK = act("enter", "crab_to_deck")
ACTIVATE_A = act("activate", "generator_a")
ACTIVATE_B = act("activate", "generator_b")
ACTIVATE_C = act("activate", "generator_c")
ACTIVATE_D = act("activate", "generator_d")
SOLVE_HOLD = act("use_item", "hold_puzzle", item="wand")
OPEN_CRAB = act("use_item", "deck_to_crab", item="key")
OPEN_ANGEL = act("use_item", "deck_to_angel", item="key")
GIVE_TO_CRAB = act("use_item", "crab", item="wand")
GIVE_TO_ANGEL = act("use_item", "angel", item="wand")

# The cabin's generators start A off, B on, C on, D off: A then D turns all four on.
SOLVE_CABIN = [ACTIVATE_A, ACTIVATE_D]
# Wand, cabin puzzle, key, and back on the deck.
GET_KEY = [TAKE_WAND, TO_CABIN] + SOLVE_CABIN + [TAKE_KEY, CABIN_TO_DECK]
# The shortest way to each ending: the hold is optional.
CRAB_ENDING = GET_KEY + [OPEN_CRAB, TO_CRAB, GIVE_TO_CRAB]
ANGEL_ENDING = GET_KEY + [OPEN_ANGEL, TO_ANGEL, GIVE_TO_ANGEL]
# The long way: read the clue in the hold first.
CLUE_THEN_CRAB = [TAKE_WAND, TO_HOLD, SOLVE_HOLD, HOLD_TO_DECK] + GET_KEY[1:] + [OPEN_CRAB, TO_CRAB, GIVE_TO_CRAB]
# Open a door, go in, come back and wander around without ending the game.
CHOOSE_AND_WANDER = GET_KEY + [OPEN_CRAB, TO_CRAB, CRAB_TO_DECK, TO_CABIN]
# Flip some generators, walk out and back in (they start over), flip another one.
TOGGLE_AND_LEAVE = [TAKE_WAND, TO_CABIN, ACTIVATE_B, ACTIVATE_C, CABIN_TO_DECK, TO_CABIN, ACTIVATE_C]


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
    """A good spread of moments in a game: every step of four different paths."""
    return (states_along(CLUE_THEN_CRAB) + states_along(ANGEL_ENDING) + states_along(CHOOSE_AND_WANDER)
            + states_along(TOGGLE_AND_LEAVE))


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
    """A2: with the key, the locked route leads to its room, and the key is not used up."""
    state = play(GET_KEY + [open_door, go_in])
    assert state["room"] == room
    assert engine.has_item(state, "key")


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


def test_a4_resume_restores_scene_items_and_choice():
    """A4: collect items, make the choice, close and reopen: the same game, with the same routes.

    Here the game only goes through JSON in memory; the next test uses the real save file.
    """
    state = play(GET_KEY + [OPEN_CRAB])
    resumed = reopen(state)
    assert resumed == state
    assert resumed["room"] == "deck"
    assert resumed["inventory"] == ["wand", "key"]
    assert resumed["flags"]["chosen_door"] == "deck_to_crab"
    assert engine.door_status(resumed, "deck_to_angel") == "sealed"
    assert_same_routes(resumed, state)


def test_a4_resume_through_the_save_file():
    """A4 with the real file: every accepted action is saved, and reopening the app reads only the file."""
    played = play_saving(GET_KEY + [OPEN_CRAB, TO_CRAB])
    resumed = resume()
    assert resumed == played
    assert resumed["room"] == "crab_room"
    assert resumed["inventory"] == ["wand", "key"]
    assert resumed["flags"]["chosen_door"] == "deck_to_crab"
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
    progress = play(GET_KEY + [OPEN_CRAB])
    after, outcome = engine.start_new_game(progress)
    assert not outcome["ok"]
    assert outcome["event"] == "needs_confirmation"
    assert after == progress


def test_a6_confirmed_restart_restores_the_opening():
    """A6: once confirmed, the game is back to the opening scene, empty-handed, nothing decided."""
    progress = play(GET_KEY + [OPEN_CRAB])
    fresh, outcome = engine.start_new_game(progress, confirmed=True)
    assert outcome["ok"]
    assert outcome["event"] == "started"
    assert fresh["room"] == story.START_ROOM
    assert fresh["inventory"] == []
    assert fresh["flags"] == story.FLAGS
    assert fresh["ending"] is None


def test_a6_restart_through_the_save_file(save_file):
    """A6 with the real file: cancelling leaves the save as it was; confirming replaces it with a new game."""
    play_saving(GET_KEY + [OPEN_CRAB])
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
    here = {thing["id"]: thing["status"] for thing in engine.things_here(state)}
    assert here == {
        "wand": "on_floor",
        "deck_to_cabin": "open",
        "deck_to_hold": "open",
        "deck_to_crab": "locked",
        "deck_to_angel": "locked",
    }
    assert offered(state, "wand") == [("pick_up", None)]
    assert offered(state, "deck_to_cabin") == [("enter", None)]
    assert offered(state, "deck") == [("examine", None)]


def test_pt02_accepted_actions_show_a_result():
    """Every accepted action, at any moment of the game, gives the player something to read."""
    for state in sample_states():
        for action in every_action():
            _, outcome = engine.perform(state, action)
            if outcome["ok"]:
                assert outcome["text"].strip(), f"{action} gave no visible result"


def test_pt03_the_key_unlocks_opening_the_door():
    """Without the key, E only lets you look at the door; with it, it offers to open it."""
    assert ("use_item", "key") not in offered(play([TAKE_WAND]), "deck_to_crab")
    with_key = play(GET_KEY)
    assert ("use_item", "key") in offered(with_key, "deck_to_crab")
    _, outcome = engine.use_item(with_key, "key", "deck_to_crab")
    assert outcome["event"] == "door_opened"


def test_pt04_choosing_a_door_seals_the_other_forever():
    """The remembered choice blocks the other door, even with the key and after walking around."""
    state = play(CHOOSE_AND_WANDER + [CABIN_TO_DECK])
    assert engine.door_status(state, "deck_to_crab") == "open"
    assert engine.door_status(state, "deck_to_angel") == "sealed"
    for action in (TO_ANGEL, OPEN_ANGEL):
        after, outcome = engine.perform(state, action)
        assert outcome["event"] == "sealed"
        assert after == state


def test_pt04_refused_actions_are_explained():
    """Every refused action, at any moment of the game, tells the player why."""
    for state in sample_states():
        for action in every_action():
            _, outcome = engine.perform(state, action)
            if not outcome["ok"]:
                assert outcome["text"].strip(), f"{action} was refused without an explanation"


def test_pt04_irreversible_actions_are_flagged():
    """Opening a final door and giving the wand ask for confirmation; solving a puzzle does not."""
    with_key = play(GET_KEY)
    flags = {action["item"]: action["irreversible"] for action in engine.actions_for(with_key, "deck_to_crab")}
    assert flags == {None: False, "wand": False, "key": True}

    near_crab = play(GET_KEY + [OPEN_CRAB, TO_CRAB])
    flags = {action["item"]: action["irreversible"] for action in engine.actions_for(near_crab, "crab")}
    assert flags == {None: False, "wand": True, "key": False}

    in_cabin = play([TAKE_WAND, TO_CABIN])
    for action in engine.actions_for(in_cabin, "generator_a") + engine.actions_for(in_cabin, "barrier"):
        assert not action["irreversible"]


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
    for action in (ACTIVATE_A, SOLVE_HOLD, GIVE_TO_CRAB, GIVE_TO_ANGEL, CABIN_TO_DECK):
        _, outcome = engine.perform(on_deck, action)
        assert outcome["event"] == "not_here"
    empty_handed = play([TO_HOLD])
    _, outcome = engine.perform(empty_handed, SOLVE_HOLD)
    assert outcome["event"] == "no_item"


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


def test_r2_using_items_does_not_consume_them():
    """After the cabin's circuit, opening a door and giving the wand away, both items are still there."""
    assert play(CRAB_ENDING)["inventory"] == ["wand", "key"]


def test_r3_revisited_cabin_remembers_the_complete_circuit():
    """Back in the cabin: the generators are still on, the barrier is still gone, the altar is empty."""
    state = play(GET_KEY + [TO_CABIN])
    here = {thing["id"]: thing["status"] for thing in engine.things_here(state)}
    for generator in ("generator_a", "generator_b", "generator_c", "generator_d"):
        assert here[generator] == "on"
    assert "barrier" not in here
    assert "key" not in here
    assert here["altar"] == "present"


def test_r3_revisited_hold_remembers_the_solved_barrel():
    """Back in the hold: the barrel shows the solved puzzle, and using the wand again does nothing."""
    state = play([TAKE_WAND, TO_HOLD, SOLVE_HOLD, HOLD_TO_DECK, TO_HOLD])
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


def test_r3_found_clue_is_remembered():
    state = play([TAKE_WAND, TO_HOLD, SOLVE_HOLD, HOLD_TO_DECK])
    assert engine.clues(state) == [story.CLUES["crab_truthful"]]
    assert engine.clues(reopen(state)) == [story.CLUES["crab_truthful"]]
    assert engine.clues(engine.new_game()) == []


def test_r4_new_game_resets_progress_but_not_the_story():
    """Playing, resuming and restarting never change story.py."""
    tables = [story.START_ROOM, story.FLAGS, story.ROOMS, story.ITEMS, story.DOORS,
              story.OBJECTS, story.ENDINGS, story.CLUES, story.MESSAGES]
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

GENERATORS = ["generator_a", "generator_b", "generator_c", "generator_d"]


def generators(state):
    """The four generators as their letters, capital when on: "aBCd" is A off, B on, C on, D off."""
    letters = ""
    for generator in GENERATORS:
        letter = story.OBJECTS[generator]["label"]
        letters += letter if state["flags"][generator] else letter.lower()
    return letters


def test_m5_the_generators_start_a_off_b_on_c_on_d_off():
    """The starting configuration the puzzle asks for, with the barrier up and the key behind it."""
    in_cabin = play([TO_CABIN])
    assert generators(in_cabin) == "aBCd"
    here = {thing["id"]: thing["status"] for thing in engine.things_here(in_cabin)}
    assert here["barrier"] == "up"
    assert here["key"] == "guarded"


@pytest.mark.parametrize("generator, after", [
    ("generator_a", "Abcd"),  # A, B and C flip
    ("generator_b", "AbCD"),  # B, A and D flip
    ("generator_c", "ABcD"),  # C, A and D flip
    ("generator_d", "abcD"),  # D, B and C flip
])
def test_m5_a_generator_flips_itself_and_the_two_next_to_it(generator, after):
    """From aBCd, each generator flips itself and its two neighbours along the sides, never the one across."""
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
        assert generators(twice) == "aBCd", generator


@pytest.mark.parametrize("first, last", [(ACTIVATE_A, ACTIVATE_D), (ACTIVATE_D, ACTIVATE_A)])
def test_m5_all_four_on_dissolves_the_barrier(first, last):
    """As soon as all four are on: the message, the barrier gone, and the key can be taken from the altar."""
    state = play([TO_CABIN, first])
    assert not state["flags"]["cabin_solved"]  # one generator is not enough
    state, outcome = engine.perform(state, last)
    assert outcome["event"] == "circuit_complete"
    assert outcome["text"] == story.CIRCUITS["cabin_circuit"]["solved_text"]
    assert generators(state) == "ABCD"
    here = {thing["id"]: thing["status"] for thing in engine.things_here(state)}
    assert "barrier" not in here
    assert here["key"] == "on_floor"
    _, outcome = engine.pick_up(state, "key")
    assert outcome["event"] == "picked_up"


def test_m5_every_configuration_of_the_generators_can_be_completed():
    """Whatever the player does, the circuit can still be completed: the puzzle has no dead ends.

    On the way, every press is checked: the circuit is complete exactly when all four are on.
    """
    for number in range(16):
        start = play([TO_CABIN])
        for index, generator in enumerate(GENERATORS):
            start["flags"][generator] = bool(number >> index & 1)
        seen = {generators(start)}
        frontier = [start]
        completed = False
        while frontier and not completed:  # all the configurations one press further, then two...
            further = []
            for state in frontier:
                for generator in GENERATORS:
                    after, outcome = engine.activate(state, generator)
                    assert (outcome["event"] == "circuit_complete") == (generators(after) == "ABCD")
                    if outcome["event"] == "circuit_complete":
                        completed = True
                    elif generators(after) not in seen:
                        seen.add(generators(after))
                        further.append(after)
            frontier = further
        assert completed, generators(start)


def test_m5_a_complete_circuit_stays_on():
    complete = play([TO_CABIN] + SOLVE_CABIN)
    for generator in GENERATORS:
        after, outcome = engine.activate(complete, generator)
        assert outcome["event"] == "already_done"
        assert after == complete


def test_m5_walking_back_in_finds_the_starting_configuration():
    """Until the circuit is complete, entering the cabin always finds A off, B on, C on, D off."""
    state = play([TO_CABIN, ACTIVATE_B, ACTIVATE_C])
    assert generators(state) != "aBCd"
    state = play([CABIN_TO_DECK, TO_CABIN], state)
    assert generators(state) == "aBCd"


def test_m5_a_complete_circuit_is_remembered():
    state = play([TO_CABIN] + SOLVE_CABIN + [CABIN_TO_DECK, TO_CABIN])
    assert generators(state) == "ABCD"
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
    state = play_saving(GET_KEY + [OPEN_CRAB])
    saved_bytes = save_file.read_bytes()
    for action in (TO_ANGEL, OPEN_ANGEL, TAKE_WAND, SOLVE_HOLD, GIVE_TO_CRAB):
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
    pytest.param(restorable(flags={"chosen_door": "deck_to_cabin"}), id="not a choice door"),
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


# --- The story data --------------------------------------------------------------


def all_ids():
    return list(story.ROOMS) + list(story.ITEMS) + list(story.DOORS) + list(story.OBJECTS)


def test_story_has_what_the_first_release_needs():
    """At least five scenes, two collectible items and two endings."""
    assert len(story.ROOMS) >= 5
    assert len(story.ITEMS) >= 2
    assert len(story.ENDINGS) >= 2


def test_story_ids_are_unique():
    assert len(all_ids()) == len(set(all_ids()))


def test_story_references_exist():
    assert story.START_ROOM in story.ROOMS
    for item in story.ITEMS.values():
        assert item["room"] in story.ROOMS
        assert item["appears_if"] is None or item["appears_if"] in story.FLAGS
        assert item["free_if"] is None or item["free_if"] in story.FLAGS
    for door in story.DOORS.values():
        assert door["room"] in story.ROOMS
        assert door["to"] in story.ROOMS
        assert door["requires"] is None or door["requires"] in story.ITEMS
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


def test_story_every_door_has_a_way_back():
    links = set()
    for door in story.DOORS.values():
        links.add((door["room"], door["to"]))
    for room, to in links:
        assert (to, room) in links, f"no way back from {to} to {room}"


def test_story_every_room_can_be_reached():
    reached = {story.START_ROOM}
    grew = True
    while grew:
        grew = False
        for door in story.DOORS.values():
            if door["room"] in reached and door["to"] not in reached:
                reached.add(door["to"])
                grew = True
    assert reached == set(story.ROOMS)


def test_story_locked_doors_are_complete():
    """A door with a lock has a choice flag and all three texts; a door without one has neither."""
    for door_id, door in story.DOORS.items():
        locked = door["requires"] is not None
        assert (door["choice_flag"] is not None) == locked, door_id
        if locked:
            for key in ("locked_text", "sealed_text", "open_text"):
                assert door[key].strip(), f"{door_id} has no {key}"


def test_story_objects_are_well_formed():
    for thing_id, thing in story.OBJECTS.items():
        assert thing["kind"] in ("puzzle", "character", "switch", "barrier", "altar"), thing_id
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
        if thing["kind"] == "barrier":
            assert thing["open_if"] in story.FLAGS, thing_id
        for reaction in thing["reactions"].values():
            # Exactly one effect: set a flag or end the game.
            assert ("ending" in reaction) != ("set_flag" in reaction), thing_id
            assert reaction["text"].strip()
        if thing["kind"] == "puzzle":
            assert thing["done_text"].strip(), f"{thing_id} has no done_text"
            for reaction in thing["reactions"].values():
                assert "set_flag" in reaction, f"{thing_id} is a puzzle: it sets a flag, it does not end the game"


def test_story_texts_are_not_empty():
    for room in story.ROOMS.values():
        assert room["name"].strip()
        assert room["description"].strip()
    for item in story.ITEMS.values():
        assert item["name"].strip()
        assert item["description"].strip()
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
    for text in story.MESSAGES.values():
        assert text.strip()
