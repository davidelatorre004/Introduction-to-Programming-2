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
the player, the engine decides whether an action is allowed and what it changes.
An id that does not exist is a bug in the calling code, not a player's mistake,
so it raises ValueError instead of being refused.
"""

import copy

import story

# The keys of a game state, and of a valid saved game.
STATE_KEYS = {"room", "inventory", "flags", "ending"}


# --- Starting, restarting and resuming ---------------------------------------


def new_game():
    """Return the state of a brand-new game: on the deck, empty-handed, nothing decided."""
    return {
        "room": story.START_ROOM,
        "inventory": [],
        # A copy: changing this game's flags must never change story.FLAGS.
        "flags": copy.deepcopy(story.FLAGS),
        "ending": None,
    }


def start_new_game(existing, confirmed=False):
    """Start a new game, asking for confirmation first if there is progress to lose.

    `existing` is the current or saved game, or None if there is none. Without
    confirmation it comes back untouched, with the question to ask the player.
    """
    if existing is not None and not confirmed:
        return _refuse(existing, "needs_confirmation", story.MESSAGES["confirm_restart"])
    return _accept(new_game(), "started", story.MESSAGES["intro"])


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

    flags = data["flags"]
    if not isinstance(flags, dict):
        return None
    for flag, value in flags.items():
        if flag not in story.FLAGS or not _is_allowed(flag, value):
            return None

    ending = data["ending"]
    if ending is not None and not _is_id(ending, story.ENDINGS):
        return None

    state = new_game()
    state["room"] = data["room"]
    state["inventory"] = list(inventory)
    state["flags"].update(flags)
    state["ending"] = ending
    return state


# --- Looking at the game (nothing changes) -----------------------------------


def is_over(state):
    """True once an ending has been reached."""
    return state["ending"] is not None


def has_item(state, item):
    """True if the item is in the inventory."""
    return item in state["inventory"]


def door_status(state, door):
    """Return "open", "locked" or "sealed".

    A door without a lock is always open. A locked door remembers being opened
    in its choice flag: it is open if the flag holds this door, sealed if it
    holds another door sharing the flag, and locked while the flag is None.
    """
    _expect(door, "door")
    info = story.DOORS[door]
    if info["requires"] is None:
        return "open"
    chosen = state["flags"][info["choice_flag"]]
    if chosen is None:
        return "locked"
    if chosen == door:
        return "open"
    return "sealed"


def things_here(state):
    """List what is in the current room right now, as dicts with "id", "kind" and "status".

    Items are listed only while they lie on the floor. The status is "on_floor"
    for items, "solved" or "unsolved" for puzzles, "present" for characters and
    "open", "locked" or "sealed" for doors.
    """
    room = state["room"]
    things = []
    for item in story.ITEMS:
        if _on_floor(state, item):
            things.append({"id": item, "kind": "item", "status": "on_floor"})
    for thing, info in story.OBJECTS.items():
        if info["room"] != room:
            continue
        if info["kind"] == "puzzle":
            status = "solved" if _is_solved(state, thing) else "unsolved"
        else:
            status = "present"
        things.append({"id": thing, "kind": info["kind"], "status": status})
    for door, info in story.DOORS.items():
        if info["room"] == room:
            things.append({"id": door, "kind": "door", "status": door_status(state, door)})
    return things


def actions_for(state, target):
    """List the actions the E key offers near a target: anything in the room, or the room itself.

    Each action is a dict with "verb", "target", "item", "label" and
    "irreversible", and perform() accepts it as it is. Using or giving is offered
    for every item in the inventory, not only the right one, so the menu does not
    give the solution away. After an ending nothing is offered.
    """
    kind = _kind(target)
    if is_over(state) or not _is_here(state, target):
        return []

    if kind == "room":
        return [_action("examine", target, story.MESSAGES["label_look_around"])]
    if kind == "item":
        label = story.MESSAGES["label_pick_up"].format(item=story.ITEMS[target]["name"])
        return [_action("pick_up", target, label)]
    if kind == "door" and door_status(state, target) == "open":
        destination = story.ROOMS[story.DOORS[target]["to"]]["name"]
        label = story.MESSAGES["label_enter"].format(room=destination)
        return [_action("enter", target, label)]

    # A closed door, a puzzle or a character: look at it, or use an item on it.
    if kind == "character":
        actions = [_action("examine", target, story.MESSAGES["label_talk"])]
        use_label = story.MESSAGES["label_give"]
    else:
        actions = [_action("examine", target, story.MESSAGES["label_examine"])]
        use_label = story.MESSAGES["label_use"]
    for item in state["inventory"]:
        label = use_label.format(item=story.ITEMS[item]["name"])
        irreversible = _is_irreversible(state, item, target)
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


def pick_up(state, item):
    """Pick up an item lying on the floor of the current room."""
    _expect(item, "item")
    if is_over(state):
        return _refuse(state, "game_over", story.MESSAGES["game_over"])
    if has_item(state, item):
        return _refuse(state, "already_have", story.MESSAGES["already_have"])
    if not _on_floor(state, item):
        return _refuse(state, "not_here", story.MESSAGES["not_here"])
    new = copy.deepcopy(state)
    new["inventory"].append(item)
    return _accept(new, "picked_up", story.ITEMS[item]["pickup_text"])


def enter(state, door):
    """Go through a door of the current room, if it is open."""
    _expect(door, "door")
    if is_over(state):
        return _refuse(state, "game_over", story.MESSAGES["game_over"])
    info = story.DOORS[door]
    if info["room"] != state["room"]:
        return _refuse(state, "not_here", story.MESSAGES["not_here"])
    status = door_status(state, door)
    if status == "locked":
        return _refuse(state, "locked", info["locked_text"])
    if status == "sealed":
        return _refuse(state, "sealed", info["sealed_text"])
    new = copy.deepcopy(state)
    new["room"] = info["to"]
    return _accept(new, "entered", story.ROOMS[info["to"]]["name"])


def use_item(state, item, target):
    """Use an item from the inventory on something in the room: a door, a puzzle or a character.

    The item is never used up: it stays in the inventory, even after giving it away.
    """
    _expect(item, "item")
    kind = _kind(target)
    if is_over(state):
        return _refuse(state, "game_over", story.MESSAGES["game_over"])
    if not has_item(state, item):
        return _refuse(state, "no_item", story.MESSAGES["no_item"])
    if not _is_here(state, target):
        return _refuse(state, "not_here", story.MESSAGES["not_here"])
    if kind == "door":
        return _use_on_door(state, item, target)
    if kind == "puzzle" or kind == "character":
        return _use_on_object(state, item, target)
    return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])


def examine(state, target):
    """Look at something in the room, or at the room itself, and return what the player sees.

    Nothing changes, but the action is accepted: it shows new information.
    """
    kind = _kind(target)
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


def perform(state, action):
    """Carry out an action given as data, such as one returned by actions_for().

    The action is a dict with a "verb" ("pick_up", "enter", "use_item" or
    "examine"), a "target" and, for "use_item", an "item".
    """
    verb = action["verb"]
    if verb == "pick_up":
        return pick_up(state, action["target"])
    if verb == "enter":
        return enter(state, action["target"])
    if verb == "use_item":
        return use_item(state, action["item"], action["target"])
    if verb == "examine":
        return examine(state, action["target"])
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
    """Return what an id names: "room", "item", "door", "puzzle" or "character"."""
    if thing in story.ROOMS:
        return "room"
    if thing in story.ITEMS:
        return "item"
    if thing in story.DOORS:
        return "door"
    if thing in story.OBJECTS:
        return story.OBJECTS[thing]["kind"]
    raise ValueError(f"Unknown id: {thing!r}")


def _expect(thing, kind):
    """Raise ValueError unless the id names a thing of this kind."""
    if _kind(thing) != kind:
        raise ValueError(f"{thing!r} is not a {kind}")


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
    return story.OBJECTS[thing]["room"] == state["room"]


def _on_floor(state, item):
    """True if the item lies in the current room: it belongs here, it has appeared, nobody took it."""
    info = story.ITEMS[item]
    if info["room"] != state["room"]:
        return False
    if info["appears_if"] is not None and not state["flags"][info["appears_if"]]:
        return False
    return not has_item(state, item)


def _reaction_done(state, reaction):
    """True if a reaction that sets a flag has already set it."""
    return state["flags"][reaction["set_flag"]] == reaction["value"]


def _is_solved(state, puzzle):
    """True once every reaction of a puzzle has done its job."""
    for reaction in story.OBJECTS[puzzle]["reactions"].values():
        if not _reaction_done(state, reaction):
            return False
    return True


def _door_text(state, door):
    """What the player reads when examining a door."""
    info = story.DOORS[door]
    status = door_status(state, door)
    if status == "locked":
        return info["locked_text"]
    if status == "sealed":
        return info["sealed_text"]
    destination = story.ROOMS[info["to"]]["name"]
    return story.MESSAGES["door_open"].format(room=destination)


def _use_on_door(state, item, door):
    """Open a locked door with the item it needs. Opening a choice door seals the others."""
    info = story.DOORS[door]
    status = door_status(state, door)
    if status == "open":
        return _refuse(state, "already_open", story.MESSAGES["already_open"])
    if status == "sealed":
        return _refuse(state, "sealed", info["sealed_text"])
    if item != info["requires"]:
        return _refuse(state, "nothing_happens", story.MESSAGES["nothing_happens"])
    new = copy.deepcopy(state)
    new["flags"][info["choice_flag"]] = door
    return _accept(new, "door_opened", info["open_text"])


def _use_on_object(state, item, thing):
    """Apply the reaction a puzzle or a character has to this item, if it has one."""
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
    return _accept(new, "flag_set", reaction["text"])


def _is_irreversible(state, item, target):
    """True if using the item on the target would open a choice door or end the game.

    Actions never change the state they receive, so we can simply try it.
    """
    _, outcome = use_item(state, item, target)
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
    """Every value a flag can take in valid play: its starting value, and what doors and reactions write."""
    values = [story.FLAGS[flag]]
    for door, info in story.DOORS.items():
        if info["choice_flag"] == flag:
            values.append(door)
    for info in story.OBJECTS.values():
        for reaction in info["reactions"].values():
            if reaction.get("set_flag") == flag:
                values.append(reaction["value"])
    return values


def _is_allowed(flag, value):
    """True if the flag can hold this value. The types must match too, because in Python 1 == True."""
    for allowed in _allowed_values(flag):
        if value == allowed and type(value) is type(allowed):
            return True
    return False
