"""The story of Plot Twist: every room, item, door, object, ending and text of the game.

This file is only data. The rules that read it are in engine.py, and nothing here
changes while the game runs. Ids and texts are in English.
"""

# Where every new game starts.
START_ROOM = "deck"

# What the game remembers about the player's progress and choices, with the
# value each flag has at the start of a new game.
FLAGS = {
    # The four generators of the captain's cabin: True is on, False is off. The
    # puzzle starts with A off, B on, C on, D off, and goes back to that every
    # time the player walks into the cabin, until the circuit is complete.
    "generator_a": False,
    "generator_b": True,
    "generator_c": True,
    "generator_d": False,
    # All four generators were on at once: the barrier in the cabin has dissolved.
    "cabin_solved": False,
    # The numbered tiles of the hold: the phase being played (1, 2 or 3) and how
    # many tiles of its sequence are lit. Then all three phases are done: the
    # barrier around the anvil has dissolved.
    "hold_phase": 1,
    "hold_step": 0,
    "hold_solved": False,
    # The hold puzzle is solved: the player has learned that the crab tells the truth.
    "crab_truthful": False,
    # The final doors, each with its own memory: the door's id once it has been
    # opened, None while it is locked. Opening one does not seal the other.
    "crab_door": None,
    "angel_door": None,
}

# "outdoor" tells the screen to draw the sea around the room. "entry" is the tile
# (column, row) where the player appears when a game starts or resumes in the room.
# A room is 16 x 12 tiles, walls included: the floor goes from (1, 1) to (14, 10).
ROOMS = {
    "deck": {
        "name": "Deck",
        "description": (
            "The deck of a ship adrift. All around, nothing but ocean. "
            "One door leads to the captain's cabin and one to the hold; "
            "two more have a lock."
        ),
        "outdoor": True,
        "entry": (6, 5),
    },
    "cabin": {
        "name": "Captain's cabin",
        "description": (
            "Sea charts scattered on the floor, and four generators humming at the corners of a square, "
            "joined by cables. At the back, an energy barrier guards a small altar."
        ),
        "outdoor": False,
        "entry": (7, 9),
    },
    "hold": {
        "name": "Hold",
        "description": (
            "Dark, overturned crates and the smell of brine. Five numbered tiles shine in the floor, "
            "from 1 to 5. At the back, an anvil wrapped in a barrier; "
            "in a corner, a barrel covered in symbols."
        ),
        "outdoor": False,
        "entry": (7, 2),
    },
    "crab_room": {
        "name": "Crab's room",
        "description": "A damp room full of shells. A huge crab watches you in silence.",
        "outdoor": False,
        "entry": (2, 5),
    },
    "angel_room": {
        "name": "Angel's room",
        "description": "A room flooded with white light. In the middle, an angel smiles at you.",
        "outdoor": False,
        "entry": (13, 5),
    },
}

# Items the player can collect. An item lies in its room, on tile "pos", until it
# is picked up. If "appears_if" names a flag, it shows up only once that flag is true.
# If "free_if" names a flag, it can be seen but not picked up until that flag is true.
# An item that is "part_of" another one is fused into it at the anvil: then the
# parts leave the inventory for good, and the whole item takes their place. An
# item that only comes from fusing has no room and no "pos".
ITEMS = {
    "wand": {
        "name": "Magic wand",
        "description": "A wand of dark wood, warm to the touch. It seems to answer to something magic.",
        "room": "deck",
        "pos": (8, 6),
        "appears_if": None,
        "part_of": None,
        "free_if": None,
        "pickup_text": "You pick up the magic wand. A spark runs up your arm.",
    },
    # The two halves of the key that opens the final doors.
    "key": {
        "name": "Central key",
        "description": "Half of a brass key, with a wave-shaped bow. On its own it opens nothing.",
        "room": "cabin",
        "pos": (7, 1),  # on the altar, behind the barrier
        "appears_if": None,
        "part_of": "fused_key",
        "free_if": "cabin_solved",
        "pickup_text": (
            "You take the central key from the altar: it is only half a key. "
            "Below deck, the gate of the hold creaks open."
        ),
    },
    "second_key": {
        "name": "Second key",
        "description": "The other half of the brass key. It matches the central key.",
        "room": "hold",
        "pos": (7, 10),  # on the anvil, behind the barrier
        "appears_if": None,
        "part_of": "fused_key",
        "free_if": "hold_solved",
        "pickup_text": (
            "You take the second key from the anvil. It matches the central key: "
            "on the anvil the two can be fused together."
        ),
    },
    # The two halves fused at the anvil: the key of the final doors.
    "fused_key": {
        "name": "Fused key",
        "description": "The two halves of the brass key, fused into one piece. It opens the doors of the crab and of the angel.",
        "room": None,
        "pos": None,
        "appears_if": None,
        "part_of": None,
        "free_if": None,
        "pickup_text": None,
    },
}

# Doors, one per direction: each door is in one room and leads to another, from the
# middle of one wall ("side": N, S, E or W). The way back is on the opposite wall.
# - A door that "requires" items stays locked until one of them is used on it while
#   the player carries them all. Opening it writes the door's id in its
#   "choice_flag". Doors sharing a choice flag would be a choice: opening one would
#   seal the others forever ("sealed_text"). The final doors have a flag each, so
#   both can be opened. Locked doors use "locked_text" and "open_text".
# - A door that "opens_with" an item is barred until the player carries that item,
#   and then it is simply open. "barred_text" says what bars it.
DOORS = {
    "deck_to_cabin": {
        "room": "deck", "to": "cabin", "side": "N",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "deck_to_hold": {
        "room": "deck", "to": "hold", "side": "S",
        "requires": [], "choice_flag": None, "opens_with": "key",
        "locked_text": None, "sealed_text": None, "open_text": None,
        "barred_text": "An iron gate bars the door of the hold. In its middle, a hollow shaped like half a key.",
    },
    "deck_to_crab": {
        "room": "deck", "to": "crab_room", "side": "E",
        "requires": ["fused_key"], "choice_flag": "crab_door", "opens_with": None,
        "locked_text": "A door with a claw carved in the wood. It is locked.",
        "sealed_text": None,
        "open_text": "The fused key turns easily, and the door with the claw opens.",
        "barred_text": None,
    },
    "deck_to_angel": {
        "room": "deck", "to": "angel_room", "side": "W",
        "requires": ["fused_key"], "choice_flag": "angel_door", "opens_with": None,
        "locked_text": "A door with a wing carved in the wood. It is locked.",
        "sealed_text": None,
        "open_text": "The fused key turns easily, and the door with the wing opens.",
        "barred_text": None,
    },
    "cabin_to_deck": {
        "room": "cabin", "to": "deck", "side": "S",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "hold_to_deck": {
        "room": "hold", "to": "deck", "side": "N",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "crab_to_deck": {
        "room": "crab_room", "to": "deck", "side": "W",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "angel_to_deck": {
        "room": "angel_room", "to": "deck", "side": "E",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
}

# The things that stand in the rooms. Each one stands on tile "pos" (and the
# tiles "size" covers, if it is bigger than one) and blocks the way, except the
# tiles of the floor. "kind" says what it does:
# - "puzzle" and "character" react when the player uses an item on them. A
#   reaction either sets a flag ("set_flag" and "value") or ends the game
#   ("ending"), and always has a "text". "done_text" replaces "look_text" once a
#   puzzle is solved.
# - "switch" is a generator of a circuit (see CIRCUITS): activating it flips the
#   flags in "toggles", its own included, and shows "toggle_text".
# - "tile" is a numbered tile of a floor puzzle (see FLOOR_PUZZLES): the player
#   walks on it, and it lights up when stepped on in the right order.
# - "barrier" stands in the way until its "open_if" flag is true, then it is gone.
# - "altar" holds an item: the cabin's altar.
# - "anvil" holds an item too, and fuses the parts of an item (see "part_of" in
#   ITEMS) when one of them is used on it while the player carries them all.
# The barrel of the hold is still a simple puzzle: it only asks for the wand.
OBJECTS = {
    # The generators of the cabin, at the corners of a square: A top left, B top
    # right, C bottom left, D bottom right. Each one is wired to the two next to
    # it along the sides of the square, never to the one across.
    "generator_a": {
        "kind": "switch",
        "name": "Generator A",
        "label": "A",
        "room": "cabin",
        "pos": (4, 4),
        "flag": "generator_a",
        "toggles": ["generator_a", "generator_b", "generator_c"],
        "toggle_text": "Click! A, B and C switch over.",
        "look_text": "A generator with a big lever. Its plate says \"A\".",
        "done_text": None,
        "reactions": {},
    },
    "generator_b": {
        "kind": "switch",
        "name": "Generator B",
        "label": "B",
        "room": "cabin",
        "pos": (11, 4),
        "flag": "generator_b",
        "toggles": ["generator_b", "generator_a", "generator_d"],
        "toggle_text": "Click! B, A and D switch over.",
        "look_text": "A generator with a big lever. Its plate says \"B\".",
        "done_text": None,
        "reactions": {},
    },
    "generator_c": {
        "kind": "switch",
        "name": "Generator C",
        "label": "C",
        "room": "cabin",
        "pos": (4, 7),
        "flag": "generator_c",
        "toggles": ["generator_c", "generator_a", "generator_d"],
        "toggle_text": "Click! C, A and D switch over.",
        "look_text": "A generator with a big lever. Its plate says \"C\".",
        "done_text": None,
        "reactions": {},
    },
    "generator_d": {
        "kind": "switch",
        "name": "Generator D",
        "label": "D",
        "room": "cabin",
        "pos": (11, 7),
        "flag": "generator_d",
        "toggles": ["generator_d", "generator_b", "generator_c"],
        "toggle_text": "Click! D, B and C switch over.",
        "look_text": "A generator with a big lever. Its plate says \"D\".",
        "done_text": None,
        "reactions": {},
    },
    # The barrier fed by the generators, in front of the altar and around it.
    "barrier": {
        "kind": "barrier",
        "name": "Energy barrier",
        "room": "cabin",
        "pos": (6, 1),
        "size": (3, 2),
        "open_if": "cabin_solved",
        "look_text": "An energy barrier crackles around the altar. It seems powered by the generators.",
        "done_text": None,
        "reactions": {},
    },
    "altar": {
        "kind": "altar",
        "name": "Altar",
        "room": "cabin",
        "pos": (7, 1),
        "look_text": "A small stone altar, against the back wall of the cabin.",
        "done_text": None,
        "reactions": {},
    },
    # The numbered tiles of the hold, in a row across the floor, one tile apart:
    # the player can walk around them, inside the zone, to skip from one to another.
    "tile_1": {
        "kind": "tile",
        "name": "Tile 1",
        "label": "1",
        "room": "hold",
        "pos": (3, 5),
        "look_text": "A metal tile with the number 1 carved in it.",
        "done_text": None,
        "reactions": {},
    },
    "tile_2": {
        "kind": "tile",
        "name": "Tile 2",
        "label": "2",
        "room": "hold",
        "pos": (5, 5),
        "look_text": "A metal tile with the number 2 carved in it.",
        "done_text": None,
        "reactions": {},
    },
    "tile_3": {
        "kind": "tile",
        "name": "Tile 3",
        "label": "3",
        "room": "hold",
        "pos": (7, 5),
        "look_text": "A metal tile with the number 3 carved in it.",
        "done_text": None,
        "reactions": {},
    },
    "tile_4": {
        "kind": "tile",
        "name": "Tile 4",
        "label": "4",
        "room": "hold",
        "pos": (9, 5),
        "look_text": "A metal tile with the number 4 carved in it.",
        "done_text": None,
        "reactions": {},
    },
    "tile_5": {
        "kind": "tile",
        "name": "Tile 5",
        "label": "5",
        "room": "hold",
        "pos": (11, 5),
        "look_text": "A metal tile with the number 5 carved in it.",
        "done_text": None,
        "reactions": {},
    },
    # The barrier fed by the tiles, around the anvil against the bottom wall.
    "hold_barrier": {
        "kind": "barrier",
        "name": "Energy barrier",
        "room": "hold",
        "pos": (6, 9),
        "size": (3, 2),
        "open_if": "hold_solved",
        "look_text": (
            "An energy barrier wraps the anvil. Carved in its block: "
            "\"The Wave, The Return, The Short Circuit.\""
        ),
        "done_text": None,
        "reactions": {},
    },
    "anvil": {
        "kind": "anvil",
        "name": "Anvil",
        "room": "hold",
        "pos": (7, 10),
        "look_text": "A black anvil, still warm. Here two halves of something could become one again.",
        "fuse_text": (
            "You lay the two halves on the anvil and strike them hard: the brass welds. "
            "Now you have a single, whole key: the fused key."
        ),
        "done_text": None,
        "reactions": {},
    },
    "hold_puzzle": {
        "kind": "puzzle",
        "name": "Barrel covered in symbols",
        "room": "hold",
        "pos": (12, 9),
        "look_text": "The symbols on the barrel pulse slowly, as if waiting for something.",
        "done_text": "The symbols on the barrel spell a sentence: \"The crab never lies.\"",
        "reactions": {
            "wand": {
                "set_flag": "crab_truthful",
                "value": True,
                "text": "You touch the barrel with the wand and the symbols rearrange: \"The crab never lies.\"",
            },
        },
    },
    "crab": {
        "kind": "character",
        "name": "Crab",
        "room": "crab_room",
        "pos": (10, 5),
        "size": (2, 2),
        "look_text": "\"Give me the wand and I will bring this ship to safety. Everyone on it.\"",
        "done_text": None,
        "reactions": {
            "wand": {
                "ending": "saved",
                "text": "You hand the wand to the crab, who grips it in its claws.",
            },
        },
    },
    "angel": {
        "kind": "character",
        "name": "Angel",
        "room": "angel_room",
        "pos": (5, 5),
        "size": (1, 2),
        "look_text": "\"Trust me with the wand. With me, you will all be safe.\"",
        "done_text": None,
        "reactions": {
            "wand": {
                "ending": "explosion",
                "text": "You hand the wand to the angel. Its smile widens.",
            },
        },
    },
}

# Circuits of generators. When every switch of a circuit is on at the same time,
# the circuit is complete: "solved_flag" becomes true and "solved_text" is shown.
# From then on its switches stay on. Until then, they go back to their starting
# value (in FLAGS) every time the player walks into "room".
CIRCUITS = {
    "cabin_circuit": {
        "room": "cabin",
        "switches": ["generator_a", "generator_b", "generator_c", "generator_d"],
        "solved_flag": "cabin_solved",
        "solved_text": "The electric flow is complete! The barrier has dissolved!",
    },
}

# Floor puzzles: numbered tiles to walk on in a given order, one phase after the
# other. Each phase is a sequence of "steps" (tile ids):
# - walking onto the next tile of the sequence lights it up ("lit_text");
# - at the end of a phase, the next one starts from the tile the player stands
#   on, which stays lit ("phase_text"); after the last one, "solved_flag" becomes
#   true and "solved_text" is shown;
# - walking onto any other tile ("wrong_text"), or out of the "zone" around the
#   tiles ("left_text"), switches the lights off: the phase starts over from its
#   first tile. Stepping back onto the tile lit last changes nothing.
# "phase_flag" holds the phase being played, from 1; "step_flag" how many tiles
# of its sequence are lit. The "zone" (column, row, width and height in tiles) is
# for main.py: the engine only hears that the player walked out of it.
FLOOR_PUZZLES = {
    "hold_tiles": {
        "room": "hold",
        "zone": (2, 4, 11, 3),
        "phases": [
            {"name": "The Wave", "steps": ["tile_1", "tile_2", "tile_3", "tile_4", "tile_5"]},
            {"name": "The Return", "steps": ["tile_5", "tile_3", "tile_1"]},
            {"name": "The Short Circuit", "steps": ["tile_1", "tile_5", "tile_2", "tile_4", "tile_3"]},
        ],
        "phase_flag": "hold_phase",
        "step_flag": "hold_step",
        "solved_flag": "hold_solved",
        # Short texts: they show in the banner while the player keeps walking.
        "lit_text": "Click! Tile {label} lit.",
        "phase_text": "Ding! Phase {number}: {name}.",
        "wrong_text": "BZZZ! Wrong tile.",
        "left_text": "BZZZ! You left the tiles.",
        "solved_text": "The hold's system unlocks! The barrier has dissolved!",
    },
}

# The endings. "good" lets the final screen pick its colors.
ENDINGS = {
    "saved": {
        "title": "Everyone saved",
        "text": [
            "The crab taps the wand on the deck, and the sea grows calm.",
            "At dawn, a coast appears on the horizon.",
            "The ship docks: everyone on board is safe.",
        ],
        "good": True,
    },
    "explosion": {
        "title": "The ship explodes",
        "text": [
            "The angel snaps the wand in two.",
            "A blinding light, then a roar.",
            "Of the ship, only smoke on the water remains.",
        ],
        "good": False,
    },
}

# Clues shown in the inventory once their flag is true.
CLUES = {
    "crab_truthful": "The crab never lies.",
}

# Texts that do not belong to a single room, item, door or object.
MESSAGES = {
    # The opening scene, shown when a new game starts.
    "intro": (
        "You wake up on the deck of a ship adrift. You do not remember how you got here. "
        "Next to you, on the floor, a wand is shining."
    ),
    # The question asked before a new game replaces existing progress.
    "confirm_restart": "There is already a saved game. Do you want to start over? Your progress will be lost.",
    # Explanations of refused actions.
    "game_over": "The story is over: you can watch the ending again or start a new game.",
    "not_here": "It is not here.",
    "already_have": "It is already in your inventory.",
    "no_item": "You do not have that item.",
    "already_open": "It is already open.",
    "already_done": "You have already done that.",
    "nothing_happens": "Nothing happens.",
    "guarded": "The barrier keeps you from taking it.",
    "circuit_done": "The circuit is complete: the generators stay on.",
    "missing_item": "On its own it is no use: this half needs the other one.",
    "not_fused": "It is only half of the key, and it does not turn on its own: fuse it with the other half on the anvil in the hold.",
    "already_lit": "The tile is already lit.",
    "tiles_done": "The tiles stay lit: the hold's system is unlocked.",
    # What an open door shows when examined.
    "door_open": "An open door to: {room}.",
    # Labels of the actions offered by the E key.
    "label_pick_up": "Pick up: {item}",
    "label_enter": "Enter: {room}",
    "label_look_around": "Look around",
    "label_examine": "Examine",
    "label_talk": "Talk",
    "label_use": "Use: {item}",
    "label_give": "Give: {item}",
    "label_activate": "Activate: {name}",
    # The window title and the menus.
    "title": "Plot Twist",
    "subtitle": "A mystery in the middle of the sea",
    "menu_new_game": "New game",
    "menu_resume": "Resume",
    "menu_quit": "Quit",
    "menu_continue": "Continue",
    "menu_restart": "Restart",
    "menu_main_menu": "Main menu",
    "menu_yes": "Yes",
    "menu_no": "No",
    "pause": "Paused",
    "hint_inventory": "I: inventory",
    # The controls, at the bottom of the title screen: one line each.
    "controls_1": "Arrows or WASD: move · E: interact",
    "controls_2": "I: inventory · Esc: menu",
    "ending_number": "Ending {number} of {total}",
    # What E does here, shown in the bar at the top.
    "prompt": "E: {action}",
    # How a door is called in that hint.
    "door": "Door",
    # Asked before an action that cannot be undone.
    "confirm_choice": "\"{action}\": are you sure? There is no going back.",
    # The inventory screen.
    "inventory": "Inventory",
    "inventory_empty": "You have not picked up anything yet.",
    "clues": "Clues",
    "close_hint": "I or Esc to close",
    # Shown if the save file cannot be written (for example, the disk is full).
    "save_failed": "The game cannot be saved: progress from here on could be lost.",
}
