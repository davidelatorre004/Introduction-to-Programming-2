"""The rules of Plot Twist: what the player can do, and what changes when they do it.

A game state is a dict that holds exactly what gets saved:

    room       id of the current room
    inventory  ids of the collected items, in the order they were picked up
    flags      the current value of every flag in story.FLAGS
    ending     id of the ending reached, or None while the game goes on

Everything else (what lies on the floor, which doors are open, which puzzles are
solved) is worked out from those four keys and from story.py. That is why an item
can never be collected twice: once it is in the inventory, it is no longer on the floor.

Every action returns (state, outcome) and never changes the state it receives:
an accepted action returns a changed copy, a refused one returns the same state.
The outcome is a dict:

    ok     True if the action was accepted; main.py saves the game only then
    event  a short code for the tests and the screens, e.g. "picked_up" or "locked"
    text   what to show the player; never empty

The engine knows nothing about pixels, keys or files: main.py decides what is near
the player, and tells the engine when the player steps onto a numbered tile or
walks out of the zone around the tiles; the engine decides whether an action is
allowed and what it changes.
An id that does not exist is a bug in the calling code, not a player's mistake,
so it raises ValueError instead of being refused.
"""

import copy

import story

# The keys of a game state, and of a valid saved game.
STATE_KEYS = {"room", "inventory", "flags", "ending"}


# --- Starting, restarting and resuming ---------------------------------------


def new_game(character=None, two_players=False):
    """Return the state of a brand-new game: on the deck, empty-handed, nothing decided.

    `character` is one of story.CHARACTERS; without it, the first one. With
    `two_players`, it is a game for two: player 2 starts as the first character
    player 1 did not take, until they choose their own (choose_partner_character).
    """
    state = {
        "room": story.START_ROOM,
        "inventory": [],
        # A copy: changing this game's flags must never change story.FLAGS.
        "flags": copy.deepcopy(story.FLAGS),
        "ending": None,
    }
    if character is not None:
        if character not in story.CHARACTERS:
            raise ValueError(f"Unknown character: {character!r}")
        state["flags"]["character"] = character
    state["flags"]["two_players"] = bool(two_players)
    if state["flags"]["partner_character"] == state["flags"]["character"]:
        state["flags"]["partner_character"] = _another_character(state["flags"]["character"])
    return state


def _another_character(character):
    """The first character of story.CHARACTERS that is not `character`."""
    for other in story.CHARACTERS:
        if other != character:
            return other
    raise ValueError("There is only one character")


def start_new_game(existing, confirmed=False, character=None, two_players=False):
    """Start a new game, asking for confirmation first if there is progress to lose.

    `existing` is the current or saved game, or None if there is none. Without
    confirmation it comes back untouched, with the question to ask the player.
    `character` is the character chosen for the new game, and `two_players`
    whether it is a game for two.
    """
    if existing is not None and not confirmed:
        return _refuse(existing, "needs_confirmation", story.MESSAGES["confirm_restart"])
    return _accept(new_game(character, two_players), "started", story.MESSAGES["intro"])


def menu_options(existing):
    """Return the entries of the start menu: "resume" only when there is a game to resume."""
    options = ["new_game"]
    if existing is not None:
        options.append("resume")
    return options


def restore_state(data):
    """Check a game read from a save file and return a clean copy of it, or None if it is not valid.

    Flags missing from the save (because they were added to the story later)
    get their starting value. Anything unknown makes the whole save invalid.
    """
    if not isinstance(data, dict) or set(data) != STATE_KEYS:
        return None
    if not _is_id(data["room"], story.ROOMS):
        return None

    inventory = data["inventory"]
    if not isinstance(inventory, list):
        return None
    for item in inventory:
        if not _is_id(item, story.ITEMS):
            return None
    if len(set(inventory)) != len(inventory):
        return None
    for item in inventory:
        if story.ITEMS[item]["part_of"] in inventory:
            return None  # a part next to the item it was fused into: impossible

    flags = data["flags"]
    if not isinstance(flags, dict):
        return None
    for flag, value in flags.items():
        if flag not in story.FLAGS or not _is_allowed(flag, value):
            return None

    ending = data["ending"]
    if ending is not None and not _is_id(ending, story.ENDINGS):
        return None

    for item in inventory:
        if flags.get("dropped_" + item) is not None:
            return None  # an item cannot be in hand and on the floor
        gone_if = story.ITEMS[item].get("gone_if")
        if gone_if is not None and flags.get(gone_if, story.FLAGS[gone_if]):
            return None  # an item used up for good cannot be carried
        appears_if = story.ITEMS[item]["appears_if"]
        if appears_if is not None and not flags.get(appears_if, story.FLAGS[appears_if]):
            return None  # nor one that has not appeared yet
    state = new_game()
    state["room"] = data["room"]
    state["inventory"] = list(inventory)
    state["flags"].update(flags)
    state["ending"] = ending
    if state["flags"]["partner_character"] == state["flags"]["character"]:
        if state["flags"]["two_players"]:
            return None  # the two players never play the same character
        state["flags"]["partner_character"] = _another_character(state["flags"]["character"])
    if not _floor_puzzles_consistent(state["flags"]):
        return None
    if not _potion_puzzles_consistent(state["flags"]):
        return None
    return state


# --- Looking at the game (nothing changes) -----------------------------------


def is_over(state):
    """True once an ending has been reached."""
    return state["ending"] is not None


def partner_character(state):
    """Player 2's character, in a game for two."""
    return state["flags"]["partner_character"]


def character_of(state, player=1):
    """The character `player` (1 or 2) plays."""
    return state["flags"]["character"] if player == 1 else state["flags"]["partner_character"]


def choose_partner_character(state, character):
    """Player 2 chooses their character, before a game for two starts: any but player 1's."""
    if not state["flags"]["two_players"] or character not in story.CHARACTERS \
            or character == state["flags"]["character"]:
        return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])
    new = copy.deepcopy(state)
    new["flags"]["partner_character"] = character
    return _accept(new, "character_chosen", story.CHARACTERS[character]["name"])


def has_item(state, item):
    """True if the item is in the inventory: someone has picked it up (in a game for two, either player)."""
    return item in state["inventory"]


def carries(state, item, player=1):
    """True if `player` (1 or 2) carries the item. Alone, player 1 carries the whole inventory."""
    if not has_item(state, item):
        return False
    if not state["flags"]["two_players"]:
        return player == 1
    return state["flags"]["holder_" + item] == player


def is_out(state, player):
    """True if the crab has knocked `player` out of a game for two for good."""
    return state["flags"]["out_player"] == player


def key_fused(state):
    """True once the two halves of the key have been fused (the key may have opened a door since)."""
    flags = state["flags"]
    return _made(state, "fused_key") or flags["crab_door"] is not None or flags["angel_door"] is not None


def statue_broken(state):
    """True once the crab has broken out of its statue on the deck: in a game for two, from the
    solved cabin on. The statue stays in pieces even after the crab has turned to stone and vanished."""
    return state["flags"]["two_players"] and state["flags"]["cabin_solved"]


def crab_awake(state):
    """True while the crab statue hunts the players: only in a game for two, from the
    solved cabin until the key is fused, and never after an ending."""
    flags = state["flags"]
    return flags["two_players"] and flags["cabin_solved"] and not key_fused(state) and not is_over(state)


def knock_out(state, player):
    """The crab has knocked `player` out for good: they are out until the other finishes,
    and everything they carry passes to the other player."""
    if not state["flags"]["two_players"] or state["flags"]["out_player"] != 0:
        return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])
    new = copy.deepcopy(state)
    new["flags"]["out_player"] = player
    for item in new["inventory"]:
        if new["flags"]["holder_" + item] == player:
            new["flags"]["holder_" + item] = 3 - player
    return _accept(new, "knocked_out", story.MESSAGES["partner_eliminated"])


def crab_catches_everyone(state):
    """The crab has caught every player still in the game: nobody is left to help. The game ends ("caught")."""
    if not crab_awake(state):
        return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])
    new = copy.deepcopy(state)
    new["ending"] = "caught"
    return _accept(new, "ending", story.MESSAGES["crab_ending"])


def can_use_ability(state, player=1):
    """True if `player` still has the ability used with Space: in a game for two, once, and not for
    a character whose ability is always on. Not after an ending, nor once out of the game."""
    if not state["flags"]["two_players"] or is_over(state) or is_out(state, player):
        return False
    if story.CHARACTERS[character_of(state, player)]["power"] is None:
        return False
    return not state["flags"]["ability_used_" + str(player)]


def use_ability(state, player=1):
    """`player` uses their ability: it is used up for the whole game. What it does on screen
    (stunning the crab, vanishing, dashing) is main.py's part."""
    if not state["flags"]["two_players"]:
        return _refuse(state, "nothing_happens", story.MESSAGES["abilities_for_two"])
    if not can_use_ability(state, player):
        if state["flags"]["ability_used_" + str(player)]:
            return _refuse(state, "ability_used", story.MESSAGES["ability_used"])
        return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])
    new = copy.deepcopy(state)
    new["flags"]["ability_used_" + str(player)] = True
    return _accept(new, "ability", story.CHARACTERS[character_of(state, player)]["power"]["text"])


def item_place(state, item):
    """Where an item lies when it is on the floor: (room, (column, row)). Where a player dropped it,
    or else where the story put it."""
    dropped = state["flags"]["dropped_" + item]
    if dropped is not None:
        room, col, row = dropped.split(",")
        return room, (int(col), int(row))
    return story.ITEMS[item]["room"], story.ITEMS[item]["pos"]


def last_item(state, player=1):
    """The item `player` got last, picked up or handed over: the one Q drops. None with empty hands."""
    for item in reversed(state["inventory"]):
        if carries(state, item, player):
            return item
    return None


def drop(state, tile, player=1):
    """`player` drops the item they got last on the floor of their room, on `tile` (column, row).

    Anyone can pick it up again there. An item that opened a door no longer does while it lies on the floor.
    """
    if is_over(state):
        return _refuse(state, "game_over", story.MESSAGES["game_over"])
    item = last_item(state, player)
    if item is None or not _is_tile(tile):
        return _refuse(state, "nothing_to_drop", story.MESSAGES["nothing_to_drop"])
    new = copy.deepcopy(state)
    new["inventory"].remove(item)
    _forget_holder(new, item)
    new["flags"]["dropped_" + item] = f"{new['room']},{tile[0]},{tile[1]}"
    return _accept(new, "dropped", story.MESSAGES["dropped"].format(item=story.ITEMS[item]["name"]))


def _is_tile(tile):
    """True for a (column, row) pair of small whole numbers, as it may come from another computer."""
    return (isinstance(tile, (list, tuple)) and len(tile) == 2
            and all(type(number) is int and 0 <= number < 100 for number in tile))


def _is_drop(value):
    """True for a valid value of a "dropped_<item>" flag: None, or "room,column,row"."""
    if value is None:
        return True
    if not isinstance(value, str) or value.count(",") != 2:
        return False
    room, col, row = value.split(",")
    return room in story.ROOMS and col.isdigit() and row.isdigit() and int(col) < 100 and int(row) < 100


def _made(state, item):
    """True if an item exists by now: someone carries it, or it was dropped somewhere."""
    return has_item(state, item) or state["flags"]["dropped_" + item] is not None


def player_room(state, player=1):
    """The room a player is in: "room" for player 1, the flag "partner_room" for player 2."""
    return state["room"] if player == 1 else state["flags"]["partner_room"]


def seen_by(state, player):
    """The game as `player` sees it: their room in "room", the other player's in "partner_room".

    For player 1 it is the state itself. For player 2 the two rooms swap places, so
    every rule written for "the current room" works for them too; swapping again
    gives the state back.
    """
    if player == 1:
        return state
    view = copy.deepcopy(state)
    view["room"], view["flags"]["partner_room"] = state["flags"]["partner_room"], state["room"]
    return view


def door_status(state, door):
    """Return "open", "barred", "locked" or "sealed".

    A barred door stays shut until the player carries the item it "opens_with",
    or what that item was fused into; then it is open. A door without a lock is always open. A locked door
    remembers being opened in its choice flag: it is open if the flag holds this
    door, sealed if it holds another door sharing the flag, and locked while the
    flag is None.
    """
    _expect(door, "door")
    info = story.DOORS[door]
    if info["opens_with"] is not None and not _has_or_fused(state, info["opens_with"]):
        return "barred"
    if not info["requires"]:
        return "open"
    chosen = state["flags"][info["choice_flag"]]
    if chosen is None:
        return "locked"
    if chosen == door:
        return "open"
    return "sealed"


def things_here(state, player=1):
    """List what is in the room of `player` right now, as dicts with "id", "kind" and "status".

    Items are listed only while they lie on the floor, and a barrier only while
    it stands. The status is "on_floor" for items, or "guarded" if they cannot be
    picked up yet; "solved" or "unsolved" for puzzles; "on" or "off" for switches;
    "lit" or "dark" for tiles; "up" for barriers; "present" for characters and
    altars; and "open", "barred", "locked" or "sealed" for doors.
    """
    state = seen_by(state, player)
    room = state["room"]
    things = []
    for item in story.ITEMS:
        if _on_floor(state, item):
            status = "on_floor" if _is_free(state, item) else "guarded"
            things.append({"id": item, "kind": "item", "status": status, "pos": item_place(state, item)[1]})
    for thing, info in story.OBJECTS.items():
        if info["room"] == room and _is_standing(state, thing):
            things.append({"id": thing, "kind": info["kind"], "status": _object_status(state, thing)})
    for door, info in story.DOORS.items():
        if info["room"] == room:
            things.append({"id": door, "kind": "door", "status": door_status(state, door)})
    return things


def actions_for(state, target, player=1):
    """List the actions the E key offers near a target: anything in the room, or the room itself.

    Each action is a dict with "verb", "target", "item", "label" and
    "irreversible", and perform() accepts it as it is. Using or giving is offered
    for every item in the inventory, not only the right one, so the menu does not
    give the solution away. After an ending nothing is offered.

    E only acts on what matters to the story: the room itself and decor offer
    nothing, so E does nothing there. Decor that is a "clue" (the doctor's notes)
    can still be read. In a game for two, `player` is who presses E: what is near
    them, and the items they carry.
    """
    state = seen_by(state, player)
    kind = _kind(target)
    if kind == "floor" or is_over(state) or not _is_here(state, target):
        return []  # a floor puzzle is not for E: the player's feet act on its tiles

    if kind == "room":
        return []  # far from everything, E does nothing
    if kind == "item":
        if not _is_free(state, target):
            return [_action("examine", target, story.MESSAGES["label_examine"])]
        label = story.MESSAGES["label_pick_up"].format(item=story.ITEMS[target]["name"])
        return [_action("pick_up", target, label)]
    if kind == "switch":
        label = story.MESSAGES["label_activate"].format(name=story.OBJECTS[target]["name"])
        return [_action("activate", target, label)]
    if kind == "portal" and story.OBJECTS[target]["to"] is None:
        return []  # a portal that only receives: nothing happens near it
    if kind == "decor":
        if story.OBJECTS[target].get("clue"):
            return [_action("examine", target, story.MESSAGES["label_examine"])]  # a note to read
        return []  # just furniture: E ignores it
    if kind == "portal":
        return [_action("examine", target, story.MESSAGES["label_examine"])]  # a portal is for the feet
    if kind == "door" and door_status(state, target) == "open":
        destination = story.ROOMS[story.DOORS[target]["to"]]["name"]
        label = story.MESSAGES["label_enter"].format(room=destination)
        return [_action("enter", target, label)]

    # A closed door, a puzzle, a character, a barrier or an altar: look at it, or use an item on it.
    if kind == "character":
        actions = [_action("examine", target, story.MESSAGES["label_talk"])]
        use_label = story.MESSAGES["label_give"]
    else:
        actions = [_action("examine", target, story.MESSAGES["label_examine"])]
        use_label = story.MESSAGES["label_use"]
    for item in state["inventory"]:
        if not carries(state, item, player):
            continue  # the other player's
        label = use_label.format(item=story.ITEMS[item]["name"])
        if kind == "cauldron" and _potion_puzzle_of(item) is not None:
            label = story.MESSAGES["label_pour"].format(name=story.ITEMS[item]["name"])
        irreversible = _is_irreversible(state, item, target, player)
        actions.append(_action("use_item", target, label, item, irreversible))
    return actions


def clues(state):
    """Return the texts of the clues found so far, to show in the inventory."""
    found = []
    for flag, text in story.CLUES.items():
        if state["flags"][flag]:
            found.append(text)
    return found


# --- Actions: each one returns (state, outcome) ------------------------------


def pick_up(state, item, player=1):
    """Pick up an item lying on the floor of the current room. In a game for two, `player` carries it."""
    _expect(item, "item")
    if is_over(state):
        return _refuse(state, "game_over", story.MESSAGES["game_over"])
    if has_item(state, item):
        return _refuse(state, "already_have", story.MESSAGES["already_have"])
    if not _on_floor(state, item):
        return _refuse(state, "not_here", story.MESSAGES["not_here"])
    if not _is_free(state, item):
        return _refuse(state, "guarded", story.MESSAGES["guarded"])
    new = copy.deepcopy(state)
    info = story.ITEMS[item]
    new["flags"]["dropped_" + item] = None  # in hand again
    flag = info.get("sets_flag")
    if flag is not None:
        new["flags"][flag] = True  # the green tincture: the other three appear around the ship
    if info.get("consumed"):
        return _use_up(new, item, player)
    new["inventory"].append(item)
    if new["flags"]["two_players"]:
        new["flags"]["holder_" + item] = player
    return _accept(new, "picked_up", info["pickup_text"])


def _use_up(new, item, player):
    """An item that is used the moment it is picked up, and never carried: the heart of the mine.

    In a game for two it brings back the other player, if the crab had knocked them out for
    good: they are in the game again, next to the one who picked it up. (A player who is only
    down gets up too, but who is down is main.py's to know.) With nobody to help, it is wasted.
    Changes the state given, a copy.
    """
    info = story.ITEMS[item]
    if new["flags"]["two_players"] and new["flags"]["out_player"] == 3 - player:
        new["flags"]["out_player"] = 0
        new["flags"]["partner_room"] = new["room"]  # the state as `player` sees it: the other one comes here
        return _accept(new, "revived", info["revive_text"])
    return _accept(new, "used_up", info["pickup_text"])


def enter(state, door):
    """Go through a door of the current room, if it is open."""
    _expect(door, "door")
    if is_over(state):
        return _refuse(state, "game_over", story.MESSAGES["game_over"])
    info = story.DOORS[door]
    if info["room"] != state["room"]:
        return _refuse(state, "not_here", story.MESSAGES["not_here"])
    status = door_status(state, door)
    if status == "barred":
        return _refuse(state, "barred", info["barred_text"])
    if status == "locked":
        return _refuse(state, "locked", info["locked_text"])
    if status == "sealed":
        return _refuse(state, "sealed", info["sealed_text"])
    new = copy.deepcopy(state)
    if not _partner_in(new, new["room"]):
        _leave_floor_puzzles(new)  # walking out of a room is walking out of its tile zones
    new["room"] = info["to"]
    new["flags"]["visited_" + info["to"]] = True  # for the map
    if not _partner_in(new, new["room"]):
        _reset_circuits(new)  # with the partner already there, the generators are as they left them
    return _accept(new, "entered", story.ROOMS[info["to"]]["name"])


def activate(state, switch):
    """Activate a generator: it and the generators wired to it switch over.

    Activating flips (NOT) every flag in the generator's "toggles": its own and
    those of the two generators next to it. Then the whole circuit is checked:
    if every generator is on at the same time, the circuit is complete, its flag
    is set (so the barrier it feeds dissolves) and the generators stay on from
    then on. The flags are plain booleans: True is on, False is off.
    """
    _expect(switch, "switch")
    if is_over(state):
        return _refuse(state, "game_over", story.MESSAGES["game_over"])
    if not _is_here(state, switch):
        return _refuse(state, "not_here", story.MESSAGES["not_here"])
    circuit = _circuit_of(switch)
    if state["flags"][circuit["solved_flag"]]:
        return _refuse(state, "already_done", story.MESSAGES["circuit_done"])
    new = copy.deepcopy(state)
    for flag in story.OBJECTS[switch]["toggles"]:
        new["flags"][flag] = not new["flags"][flag]
    if _circuit_complete(new, circuit):
        new["flags"][circuit["solved_flag"]] = True
        return _accept(new, "circuit_complete", circuit["solved_text"])
    return _accept(new, "toggled", story.OBJECTS[switch]["toggle_text"])


def step_on(state, tile):
    """The player walks onto a numbered tile of a floor puzzle: main.py calls this when it happens.

    The puzzle is a small state machine. Its state is two flags: the phase being
    played (from 1) and the step, that is how many tiles of the phase's sequence
    are already lit. Walking onto:
    - the next tile of the sequence lights it up ("tile_lit");
    - the last tile of the sequence completes the phase ("phase_complete"): the
      next phase starts from this tile, which stays lit. After the last phase the
      puzzle is solved ("tiles_complete"), and the barrier it feeds dissolves;
    - the tile lit last changes nothing ("already_lit"): the player only stepped
      back onto it;
    - any other tile is a mistake ("tiles_reset"): the lights go out and the
      phase starts over from its first tile.
    """
    _expect(tile, "tile")
    if is_over(state):
        return _refuse(state, "game_over", story.MESSAGES["game_over"])
    if not _is_here(state, tile):
        return _refuse(state, "not_here", story.MESSAGES["not_here"])
    puzzle = _floor_puzzle_of(tile)
    if state["flags"][puzzle["solved_flag"]]:
        return _refuse(state, "already_done", story.MESSAGES["tiles_done"])
    phase = state["flags"][puzzle["phase_flag"]]
    step = state["flags"][puzzle["step_flag"]]
    sequence = puzzle["phases"][phase - 1]["steps"]
    if step > 0 and tile == sequence[step - 1]:
        return _refuse(state, "already_lit", story.MESSAGES["already_lit"])

    new = copy.deepcopy(state)
    if tile != sequence[step]:
        # A wrong tile: the lights go out, and the same phase starts over.
        new["flags"][puzzle["step_flag"]] = 0
        return _accept(new, "tiles_reset", puzzle["wrong_text"])
    step += 1
    new["flags"][puzzle["step_flag"]] = step
    if step < len(sequence):
        label = story.OBJECTS[tile]["label"]
        return _accept(new, "tile_lit", puzzle["lit_text"].format(label=label))
    if phase == len(puzzle["phases"]):
        # The last tile of the last phase.
        new["flags"][puzzle["solved_flag"]] = True
        return _accept(new, "tiles_complete", puzzle["solved_text"])
    # The phase is complete: the next one starts from this tile, already lit.
    following = puzzle["phases"][phase]  # phases count from 1, the list from 0: this is the next one
    new["flags"][puzzle["phase_flag"]] = phase + 1
    new["flags"][puzzle["step_flag"]] = 1 if following["steps"][0] == tile else 0
    text = puzzle["phase_text"].format(number=phase + 1, name=following["name"])
    return _accept(new, "phase_complete", text)


def leave_zone(state, floor_puzzle):
    """The player walks out of the zone around a floor puzzle's tiles: main.py calls this when it happens.

    It is a mistake like a wrong tile: the lights go out and the phase starts
    over ("tiles_reset"). If no tile of the phase is lit, there is nothing to
    start over, and nothing happens.
    """
    _expect(floor_puzzle, "floor")
    if is_over(state):
        return _refuse(state, "game_over", story.MESSAGES["game_over"])
    puzzle = story.FLOOR_PUZZLES[floor_puzzle]
    if puzzle["room"] != state["room"]:
        return _refuse(state, "not_here", story.MESSAGES["not_here"])
    if state["flags"][puzzle["solved_flag"]]:
        return _refuse(state, "already_done", story.MESSAGES["tiles_done"])
    if state["flags"][puzzle["step_flag"]] == 0:
        return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])
    new = copy.deepcopy(state)
    new["flags"][puzzle["step_flag"]] = 0
    return _accept(new, "tiles_reset", puzzle["left_text"])


def use_item(state, item, target, player=1):
    """Use an item from the inventory on something in the room: a door, a puzzle, a character,
    the anvil or the cauldron.

    On anything else (a generator, a tile, a barrier, an altar) nothing happens.

    The item stays in the inventory, even after giving it away or opening a door
    with it. Only the anvil (it fuses parts into a whole), the cauldron (the
    finished remedy uses up its tinctures) and a reaction that "consumes" change it.
    """
    _expect(item, "item")
    kind = _kind(target)
    _not_a_floor_puzzle(target)
    if is_over(state):
        return _refuse(state, "game_over", story.MESSAGES["game_over"])
    if not carries(state, item, player):
        return _refuse(state, "no_item", story.MESSAGES["no_item"])
    if not _is_here(state, target):
        return _refuse(state, "not_here", story.MESSAGES["not_here"])
    if kind == "door":
        return _use_on_door(state, item, target, player)
    if kind == "puzzle" or kind == "character":
        return _use_on_object(state, item, target)
    if kind == "anvil":
        return _use_on_anvil(state, item, target, player)
    if kind == "cauldron":
        return _use_on_cauldron(state, item, target)
    return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])


def examine(state, target):
    """Look at something in the room, or at the room itself, and return what the player sees.

    Nothing changes, but the action is accepted: it shows new information.
    """
    kind = _kind(target)
    _not_a_floor_puzzle(target)
    if is_over(state):
        return _refuse(state, "game_over", story.MESSAGES["game_over"])
    if not _is_here(state, target):
        return _refuse(state, "not_here", story.MESSAGES["not_here"])
    if kind == "room":
        text = story.ROOMS[target]["description"]
    elif kind == "item":
        text = story.ITEMS[target]["description"]
    elif kind == "door":
        text = _door_text(state, target)
    elif kind == "puzzle" and _is_solved(state, target):
        text = story.OBJECTS[target]["done_text"]
    else:
        text = story.OBJECTS[target]["look_text"]
    return _accept(state, "info", text)


def travel(state, portal):
    """The player walks into a portal: main.py calls this when it happens.

    It takes them to the room of the portal it is linked to ("to"), as a door
    would: the floor puzzles they were in start over, and the room goes on the map.
    A portal that only receives ("to" is None, like the one in the helm) goes nowhere.
    """
    _expect(portal, "portal")
    if is_over(state):
        return _refuse(state, "game_over", story.MESSAGES["game_over"])
    if not _is_here(state, portal):
        return _refuse(state, "not_here", story.MESSAGES["not_here"])
    if story.OBJECTS[portal]["to"] is None:
        return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])
    destination = story.OBJECTS[story.OBJECTS[portal]["to"]]["room"]
    new = copy.deepcopy(state)
    if not _partner_in(new, new["room"]):
        _leave_floor_puzzles(new)
    new["room"] = destination
    new["flags"]["visited_" + destination] = True
    if not _partner_in(new, new["room"]):
        _reset_circuits(new)
    return _accept(new, "teleported", story.MESSAGES["portal_text"])


def give(state, item, player=1):
    """In a game for two, hand an item to the other player, who must be in the same room.

    main.py decides whether they stand close enough; the engine checks the rest.
    """
    _expect(item, "item")
    if is_over(state):
        return _refuse(state, "game_over", story.MESSAGES["game_over"])
    if not state["flags"]["two_players"]:
        return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])
    if not carries(state, item, player):
        return _refuse(state, "no_item", story.MESSAGES["no_item"])
    if is_out(state, 3 - player):
        return _refuse(state, "partner_out", story.MESSAGES["partner_is_out"])
    if player_room(state, 1) != player_room(state, 2):
        return _refuse(state, "not_here", story.MESSAGES["no_partner"])
    new = copy.deepcopy(state)
    new["flags"]["holder_" + item] = 3 - player
    new["inventory"].remove(item)
    new["inventory"].append(item)  # the last one the other player got: the one their Q drops
    return _accept(new, "given", story.MESSAGES["given"].format(item=story.ITEMS[item]["name"]))


def visited_rooms(state):
    """The rooms the player has been in, the current one included: what the map shows."""
    rooms = []
    for room in story.ROOMS:
        if state["flags"]["visited_" + room] or room == state["room"]:
            rooms.append(room)
    return rooms


def is_standing(state, thing):
    """True if an object stands in its room right now: it has appeared and it is not gone."""
    return _is_standing(state, thing)


def perform(state, action, player=1):
    """Carry out an action given as data, such as one returned by actions_for().

    The action is a dict with a "verb" ("pick_up", "enter", "use_item",
    "examine", "activate", "step_on", "leave_zone", "travel" or "give"), a
    "target" and, for "use_item" and "give", an "item". The target of
    "leave_zone" is a floor puzzle. `player` (1 or 2) is who does it: player 2
    acts in their own room, with the items they carry.
    """
    if is_out(state, player):
        return _refuse(state, "out", story.MESSAGES["you_are_out"])
    view = seen_by(state, player)
    new, outcome = _perform(view, action, player)
    if new is view:
        return state, outcome  # refused: the very state it received
    return seen_by(new, player), outcome


def _perform(state, action, player):
    """perform(), on the game as the player sees it."""
    verb = action["verb"]
    if verb == "pick_up":
        return pick_up(state, action["target"], player)
    if verb == "enter":
        return enter(state, action["target"])
    if verb == "use_item":
        return use_item(state, action["item"], action["target"], player)
    if verb == "give":
        return give(state, action["item"], player)
    if verb == "ability":
        return use_ability(state, player)
    if verb == "drop":
        return drop(state, action.get("at"), player)
    if verb == "examine":
        return examine(state, action["target"])
    if verb == "activate":
        return activate(state, action["target"])
    if verb == "step_on":
        return step_on(state, action["target"])
    if verb == "leave_zone":
        return leave_zone(state, action["target"])
    if verb == "travel":
        return travel(state, action["target"])
    raise ValueError(f"Unknown verb: {verb!r}")


# --- Helpers ------------------------------------------------------------------


def _accept(state, event, text):
    """An accepted action: return the new state and its outcome."""
    return state, {"ok": True, "event": event, "text": text}


def _refuse(state, event, text):
    """A refused action: return the state untouched and the explanation."""
    return state, {"ok": False, "event": event, "text": text}


def _action(verb, target, label, item=None, irreversible=False):
    """Build an action in the shape perform() expects, with what the menu needs to show it."""
    return {"verb": verb, "target": target, "item": item, "label": label, "irreversible": irreversible}


def _kind(thing):
    """Return what an id names: "room", "item", "door", "floor" (a floor puzzle) or the kind of an object."""
    if thing in story.ROOMS:
        return "room"
    if thing in story.ITEMS:
        return "item"
    if thing in story.DOORS:
        return "door"
    if thing in story.FLOOR_PUZZLES:
        return "floor"
    if thing in story.OBJECTS:
        return story.OBJECTS[thing]["kind"]
    raise ValueError(f"Unknown id: {thing!r}")


def _expect(thing, kind):
    """Raise ValueError unless the id names a thing of this kind."""
    if _kind(thing) != kind:
        raise ValueError(f"{thing!r} is not a {kind}")


def _not_a_floor_puzzle(target):
    """Raise ValueError if the target is a floor puzzle: one walks on its tiles, one does not look at it or use things on it."""
    if _kind(target) == "floor":
        raise ValueError(f"{target!r} is a floor puzzle: the player walks on its tiles")


def _is_id(value, table):
    """True if the value is one of the ids of a story table (used to check saved data)."""
    return isinstance(value, str) and value in table


def _is_here(state, thing):
    """True if the player can see the thing in the current room right now (the room itself included)."""
    kind = _kind(thing)
    if kind == "room":
        return thing == state["room"]
    if kind == "item":
        return _on_floor(state, thing)
    if kind == "door":
        return story.DOORS[thing]["room"] == state["room"]
    if kind == "floor":
        return story.FLOOR_PUZZLES[thing]["room"] == state["room"]
    return story.OBJECTS[thing]["room"] == state["room"] and _is_standing(state, thing)


def _partner_in(state, room):
    """True if, in a game for two, the other player is in `room` (the state as one player sees it).

    A player knocked out of the game is not there any more: only the other one still acts.
    """
    flags = state["flags"]
    return flags["two_players"] and flags["out_player"] == 0 and flags["partner_room"] == room


def _forget_holder(state, item):
    """An item has left the inventory: whoever carried it, nobody does now. Changes the state given."""
    state["flags"]["holder_" + item] = 1


def _has_or_fused(state, item):
    """True if the player carries the item, or the whole it was fused into exists (carried or dropped)."""
    whole = story.ITEMS[item]["part_of"]
    return has_item(state, item) or (whole is not None and _made(state, whole))


def _on_floor(state, item):
    """True if the item lies in the current room: it belongs here, it has appeared, nobody took it.

    A part fused into a whole is gone for good, even though it is no longer in the inventory.
    """
    info = story.ITEMS[item]
    if info.get("gone_if") is not None and state["flags"][info["gone_if"]]:
        return False  # used up for good, like the remedy once drunk
    if state["flags"]["dropped_" + item] is not None:
        return item_place(state, item)[0] == state["room"]  # where a player dropped it
    if info["room"] != state["room"]:
        return False
    if info["appears_if"] is not None and not state["flags"][info["appears_if"]]:
        return False
    return not _has_or_fused(state, item)


def _reaction_done(state, reaction):
    """True if a reaction that sets a flag has already set it."""
    return state["flags"][reaction["set_flag"]] == reaction["value"]


def _is_solved(state, puzzle):
    """True once every reaction of a puzzle has done its job."""
    for reaction in story.OBJECTS[puzzle]["reactions"].values():
        if not _reaction_done(state, reaction):
            return False
    return True


def _is_free(state, item):
    """True if nothing keeps the player from picking up the item (its "free_if" flag, if any, is true)."""
    flag = story.ITEMS[item]["free_if"]
    if state["flags"]["dropped_" + item] is not None:
        return True  # dropped by a player: out of whatever guarded it
    return flag is None or bool(state["flags"][flag])


def _is_standing(state, thing):
    """True if an object is in its room now.

    A barrier is gone once open. Any object can also wait for a flag before it
    appears ("appears_if", the anvil) or go away once a flag is set ("gone_if", the doctor).
    """
    info = story.OBJECTS[thing]
    if info["kind"] == "barrier":
        return not state["flags"][info["open_if"]]
    if info.get("appears_if") is not None and not state["flags"][info["appears_if"]]:
        return False
    if info.get("gone_if") is not None and state["flags"][info["gone_if"]]:
        return False
    return True


def _object_status(state, thing):
    """The status of an object, as things_here() lists it."""
    info = story.OBJECTS[thing]
    if info["kind"] == "puzzle":
        return "solved" if _is_solved(state, thing) else "unsolved"
    if info["kind"] == "switch":
        return "on" if state["flags"][info["flag"]] else "off"
    if info["kind"] == "tile":
        return "lit" if _tile_is_lit(state, thing) else "dark"
    if info["kind"] == "barrier":
        return "up"
    return "present"


def _circuit_of(switch):
    """The circuit a switch belongs to."""
    for circuit in story.CIRCUITS.values():
        if switch in circuit["switches"]:
            return circuit
    raise ValueError(f"{switch!r} is not in any circuit")


def _circuit_complete(state, circuit):
    """True when every switch of the circuit is on at the same time."""
    for switch in circuit["switches"]:
        if not state["flags"][story.OBJECTS[switch]["flag"]]:
            return False
    return True


def _reset_circuits(state):
    """Put back the starting configuration of the circuits in the current room that are not complete.

    It changes the state it is given, so it is used only on the copy an accepted action is building.
    """
    for circuit in story.CIRCUITS.values():
        if circuit["room"] == state["room"] and not state["flags"][circuit["solved_flag"]]:
            for switch in circuit["switches"]:
                flag = story.OBJECTS[switch]["flag"]
                state["flags"][flag] = story.FLAGS[flag]


def _floor_puzzle_of(tile):
    """The floor puzzle a tile belongs to."""
    for puzzle in story.FLOOR_PUZZLES.values():
        for phase in puzzle["phases"]:
            if tile in phase["steps"]:
                return puzzle
    raise ValueError(f"{tile!r} is not in any floor puzzle")


def _tile_is_lit(state, tile):
    """True if the tile was stepped on in the phase being played, or if its puzzle is solved."""
    puzzle = _floor_puzzle_of(tile)
    flags = state["flags"]
    if flags[puzzle["solved_flag"]]:
        return True
    sequence = puzzle["phases"][flags[puzzle["phase_flag"]] - 1]["steps"]
    return tile in sequence[:flags[puzzle["step_flag"]]]


def _leave_floor_puzzles(state):
    """Switch off the lit tiles of the unsolved floor puzzles in the current room: their phase starts over.

    It changes the state it is given, so it is used only on the copy an accepted action is building.
    """
    for puzzle in story.FLOOR_PUZZLES.values():
        if puzzle["room"] == state["room"] and not state["flags"][puzzle["solved_flag"]]:
            state["flags"][puzzle["step_flag"]] = 0


def _floor_puzzles_consistent(flags):
    """True if every unsolved floor puzzle has fewer lit tiles than the sequence of its phase."""
    for puzzle in story.FLOOR_PUZZLES.values():
        if flags[puzzle["solved_flag"]]:
            continue
        sequence = puzzle["phases"][flags[puzzle["phase_flag"]] - 1]["steps"]
        if flags[puzzle["step_flag"]] >= len(sequence):
            return False
    return True


def _potion_puzzles_consistent(flags):
    """True if a solved potion puzzle has an empty cauldron: the remedy has been bottled."""
    for puzzle in story.POTION_PUZZLES.values():
        if flags[puzzle["solved_flag"]] and flags[puzzle["step_flag"]] != 0:
            return False
    return True


def _door_text(state, door):
    """What the player reads when examining a door."""
    info = story.DOORS[door]
    status = door_status(state, door)
    if status == "barred":
        return info["barred_text"]
    if status == "locked":
        return info["locked_text"]
    if status == "sealed":
        return info["sealed_text"]
    destination = story.ROOMS[info["to"]]["name"]
    return story.MESSAGES["door_open"].format(room=destination)


def _use_on_door(state, item, door, player=1):
    """Open a locked door with the items it needs. Opening a choice door seals the others.

    The item must be one the lock "requires", and the player must carry all of
    them. A part of a required item (half of the key) does not turn: it has to
    be fused first, and the refusal says so.
    """
    info = story.DOORS[door]
    status = door_status(state, door)
    if status == "open":
        return _refuse(state, "already_open", story.MESSAGES["already_open"])
    if status == "sealed":
        return _refuse(state, "sealed", info["sealed_text"])
    if item not in info["requires"]:
        if story.ITEMS[item]["part_of"] in info["requires"]:
            return _refuse(state, "not_fused", story.MESSAGES["not_fused"])
        return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])
    for needed in info["requires"]:
        if not carries(state, needed, player):
            return _refuse(state, "missing_item", story.MESSAGES["missing_item"])
    new = copy.deepcopy(state)
    new["flags"][info["choice_flag"]] = door
    return _accept(new, "door_opened", info["open_text"])


def _use_on_anvil(state, item, anvil, player=1):
    """Fuse the parts of an item into the whole: one part is used on the anvil, and the player carries them all.

    The parts leave the inventory for good, and the whole takes the place of the first one.
    """
    whole = story.ITEMS[item]["part_of"]
    if whole is None:
        return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])
    parts = [part for part, info in story.ITEMS.items() if info["part_of"] == whole]
    for part in parts:
        if not carries(state, part, player):
            return _refuse(state, "missing_item", story.MESSAGES["missing_item"])
    new = copy.deepcopy(state)
    first = min(new["inventory"].index(part) for part in parts)
    new["inventory"] = [held for held in new["inventory"] if held not in parts]
    new["inventory"].insert(first, whole)
    for part in parts:
        _forget_holder(new, part)
    if new["flags"]["two_players"]:
        new["flags"]["holder_" + whole] = player  # the one who fused them
    return _accept(new, "fused", story.OBJECTS[anvil]["fuse_text"])


def _potion_puzzle_of(item):
    """The potion puzzle whose recipe has this item, or None."""
    for puzzle in story.POTION_PUZZLES.values():
        if item in puzzle["recipe"]:
            return puzzle
    return None


def _use_on_cauldron(state, item, cauldron):
    """Pour a tincture into the cauldron of its potion puzzle.

    Like the tiles, it is a small state machine, with one flag: how many
    ingredients of the recipe are in, in the right order. Pouring:
    - the next one of the recipe adds it ("potion_poured");
    - the last one of the recipe makes the remedy ("potion_ready"): it appears in
      the cauldron, the tinctures are used up, and the puzzle is done;
    - any other one spoils the mixture ("potion_spoiled"): the cauldron is empty
      again, and the recipe starts over. The bottles stay in hand, so the player
      can always try again.
    Anything that is not one of its tinctures does nothing.
    """
    puzzle = _potion_puzzle_of(item)
    if puzzle is None or puzzle["cauldron"] != cauldron:
        return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])
    if state["flags"][puzzle["solved_flag"]]:
        return _refuse(state, "already_done", story.MESSAGES["potion_done"])
    recipe = puzzle["recipe"]
    step = state["flags"][puzzle["step_flag"]]
    new = copy.deepcopy(state)
    if item != recipe[step]:
        new["flags"][puzzle["step_flag"]] = 0
        name = story.ITEMS[item]["name"].lower()
        return _accept(new, "potion_spoiled", puzzle["wrong_text"].format(name=name))
    step += 1
    if step == len(recipe):
        new["flags"][puzzle["step_flag"]] = 0  # the cauldron is empty: the remedy is in the bottle
        new["flags"][puzzle["solved_flag"]] = True
        new["inventory"] = [held for held in new["inventory"] if held not in recipe]  # used up
        for tincture in recipe:
            _forget_holder(new, tincture)
        return _accept(new, "potion_ready", puzzle["solved_text"])
    new["flags"][puzzle["step_flag"]] = step
    return _accept(new, "potion_poured", puzzle["pour_texts"][item])


def _use_on_object(state, item, thing):
    """Apply the reaction a puzzle or a character has to this item, if it has one.

    A reaction with "consumes" takes the item out of the inventory (the doctor drinks the remedy).
    """
    reaction = story.OBJECTS[thing]["reactions"].get(item)
    if reaction is None:
        return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])
    if "ending" in reaction:
        new = copy.deepcopy(state)
        new["ending"] = reaction["ending"]
        return _accept(new, "ending", reaction["text"])
    if _reaction_done(state, reaction):
        return _refuse(state, "already_done", story.MESSAGES["already_done"])
    new = copy.deepcopy(state)
    new["flags"][reaction["set_flag"]] = reaction["value"]
    if reaction.get("consumes"):
        new["inventory"].remove(item)  # drunk, eaten, used up: it is gone
        _forget_holder(new, item)
    return _accept(new, "flag_set", reaction["text"])


def _is_irreversible(state, item, target, player=1):
    """True if using the item on the target would open a choice door or end the game.

    Actions never change the state they receive, so we can simply try it.
    """
    _, outcome = use_item(state, item, target, player)
    if outcome["event"] == "ending":
        return True
    return outcome["event"] == "door_opened" and _is_choice_door(target)


def _is_choice_door(door):
    """True if opening this door seals another one, because the two share a choice flag."""
    flag = story.DOORS[door]["choice_flag"]
    if flag is None:
        return False
    sharing = 0
    for info in story.DOORS.values():
        if info["choice_flag"] == flag:
            sharing += 1
    return sharing > 1


def _allowed_values(flag):
    """Every value a flag can take in valid play: its starting value, and what doors, reactions,
    switches, circuits, floor and potion puzzles and the map write."""
    values = [story.FLAGS[flag]]
    for door, info in story.DOORS.items():
        if info["choice_flag"] == flag:
            values.append(door)
    for info in story.OBJECTS.values():
        for reaction in info["reactions"].values():
            if reaction.get("set_flag") == flag:
                values.append(reaction["value"])
        if flag in info.get("toggles", []):
            values += [True, False]  # a switch flips it both ways
    for circuit in story.CIRCUITS.values():
        if circuit["solved_flag"] == flag:
            values.append(True)
    for puzzle in story.FLOOR_PUZZLES.values():
        if puzzle["phase_flag"] == flag:
            values += list(range(1, len(puzzle["phases"]) + 1))
        if puzzle["step_flag"] == flag:
            longest = max(len(phase["steps"]) for phase in puzzle["phases"])
            values += list(range(longest + 1))
        if puzzle["solved_flag"] == flag:
            values.append(True)
    for puzzle in story.POTION_PUZZLES.values():
        if puzzle["step_flag"] == flag:
            values += list(range(len(puzzle["recipe"])))  # never the whole recipe: then it is solved
        if puzzle["solved_flag"] == flag:
            values.append(True)
    for room in story.ROOMS:
        if flag == "visited_" + room:
            values.append(True)
    for info in story.ITEMS.values():
        if info.get("sets_flag") == flag:
            values.append(True)
    if flag in ("ability_used_1", "ability_used_2"):
        values.append(True)
    if flag == "partner_character":
        values += list(story.CHARACTERS)
    if flag == "character":
        values += list(story.CHARACTERS)
    if flag == "two_players":
        values.append(True)
    if flag == "partner_room":
        values += list(story.ROOMS)
    if flag == "out_player":
        values += [1, 2]
    if flag.startswith("holder_") and flag[len("holder_"):] in story.ITEMS:
        values.append(2)
    return values


def _is_allowed(flag, value):
    """True if the flag can hold this value. The types must match too, because in Python 1 == True."""
    if flag.startswith("dropped_") and flag[len("dropped_"):] in story.ITEMS:
        return _is_drop(value)
    for allowed in _allowed_values(flag):
        if value == allowed and type(value) is type(allowed):
            return True
    return False


