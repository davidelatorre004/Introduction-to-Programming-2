"""The story of Plot Twist: every room, item, door, object, ending and text of the game.

This file is only data. The rules that read it are in engine.py, and nothing here
changes while the game runs. Ids and texts are in English.
"""

# Where every new game starts.
START_ROOM = "deck"

# The characters the player can choose from when a new game starts, in the order
# the choice shows them. They look the same, except for the colour of the shirt:
# "sprite" is the start of the names of their pictures in sprites.py.
# "ability" is what the choice screen says. "power" is the ability used with Space,
# once in a game for two ("label" names it in the corner of the screen, "text" is
# what the banner says when it is used); None for an ability that is always on.
CHARACTERS = {
    "wizard": {"sprite": "wizard", "name": "Wizard",
               "ability": "Spell: the crab stands stunned for 5 seconds.",
               "power": {"label": "Spell", "text": "A spell! The crab is stunned"}},
    "nurse": {"sprite": "nurse", "name": "Nurse",
              "ability": "Always: helps a player up in 1 second.",
              "power": None},
    "ghost": {"sprite": "ghost", "name": "Ghost",
              "ability": "Vanish: the crab cannot see you for 5 seconds.",
              "power": {"label": "Vanish", "text": "You vanish: the crab cannot see you"}},
    "flash": {"sprite": "flash", "name": "Flash",
              "ability": "Dash: a lightning sprint of 8 tiles, through doors too. Three times a game.",
              "power": {"label": "Dash", "text": "A lightning dash!", "uses": 3}},
}

# How the crab hunts in a game for two, chosen by the player who hosts it ("text" is what the
# choice screen says about it). Hard is the crab of always; easy is a crab like the ghosts of
# an arcade maze: it only sees its own room, turns only where the floor lets it, never back,
# and now and then wanders off to a corner.
DIFFICULTIES = {
    "easy": {"name": "Easy",
             "text": "The crab only sees its own room. It turns only at crossings, never back, and now and then wanders off to a corner."},
    "hard": {"name": "Hard",
             "text": "The crab always knows where you are, and takes the shortest way to you, through the whole ship."},
}

# What the game remembers about the player's progress and choices, with the
# value each flag has at the start of a new game.
FLAGS = {
    # The character chosen for this game (one of CHARACTERS): player 1's, in a game for two.
    "character": "wizard",
    # In a game for two, the character player 2 chose: never the same as player 1's.
    "partner_character": "nurse",
    # The heart of the mine has been picked up: it is used up, whether it helped anyone or not.
    "heart_used": False,
    # In a game for two, each player's ability (Space) works once: True once it is used.
    "ability_used_1": False,
    "ability_used_2": False,
    # How many times each player has used their ability: Flash can dash three times, the others
    # use theirs once ("uses" in CHARACTERS). Once they are all used, "ability_used_" is True.
    "ability_count_1": 0,
    "ability_count_2": 0,
    # A game for two players: player 2 is the other character.
    "two_players": False,
    # In a game for two, how the crab hunts (one of DIFFICULTIES). Games saved before
    # there was a choice had the hard one.
    "crab_difficulty": "hard",
    # In a game for two, the room player 2 is in ("room" in the state is player 1's).
    "partner_room": "deck",
    # In a game for two, the player the crab has knocked out for good (1 or 2), or 0:
    # they watch until the other finishes, and their items have passed to the other.
    "out_player": 0,
    # The eight generators of the captain's cabin, in a ring: True is on, False is
    # off. The puzzle starts with H, A, C and D off and B, E, F and G on, and goes
    # back to that every time the player walks into the cabin, until the circuit
    # is complete. Pulling A, then C (or C, then A) turns them all on.
    "generator_a": False,
    "generator_b": True,
    "generator_c": False,
    "generator_d": False,
    "generator_e": True,
    "generator_f": True,
    "generator_g": True,
    "generator_h": False,
    # All eight generators were on at once: the barrier in the cabin has dissolved.
    "cabin_solved": False,
    # The numbered tiles of the hold: the phase being played (1, 2 or 3) and how
    # many tiles of its sequence are lit. Then all three phases are done: the
    # barrier around the altar of the second key has dissolved.
    "hold_phase": 1,
    "hold_step": 0,
    "hold_solved": False,
    # The hold puzzle is solved: the player has learned that the crab tells the truth.
    "crab_truthful": False,
    # The final doors, each with its own memory: the door's id once it has been
    # opened, None while it is locked. Opening one does not seal the other.
    "crab_door": None,
    "angel_door": None,
    # The green tincture has been found in the infirmary: the other three have
    # appeared, scattered around the ship (the galley, the helm, the corridor).
    "tinctures_scattered": False,
    # The cauldron of the infirmary: how many ingredients of the recipe are in it,
    # in the right order; then the remedy is ready (and the cauldron empty again).
    "potion_step": 0,
    "potion_solved": False,
    # The doctor drank the remedy: his ghost is gone, and the anvil has appeared in the empty room.
    "doctor_at_peace": False,
    # The rooms the player has been in, for the map in the corner of the screen.
    "visited_deck": True,
    "visited_cabin": False,
    "visited_hold": False,
    "visited_crab_room": False,
    "visited_angel_room": False,
    "visited_infirmary": False,
    "visited_galley": False,
    "visited_helm": False,
    "visited_east_room": False,
    "visited_corridor": False,
    "visited_corridor_end": False,
    "visited_mine": False,
}

# "floor" is what the floor is made of, for the details drawn on it: "wood", "stone",
# "tiles" or "earth". "damp" (optional) stains a room with damp, and water drips from
# its ceiling.
# "dark" (optional) makes a room dark, from 1 to 255: only lanterns, crystals, portals
# and the players light it. Without it the room is fully lit.
# "outdoor" tells the screen to draw the sea around the room. "entry" is the tile
# (column, row) where the player appears when a game starts or resumes in the room.
# A room is 16 x 12 tiles, walls included: the floor goes from (1, 1) to (14, 10).
ROOMS = {
    "deck": {
        "floor": "wood",
        "name": "Deck",
        "description": (
            "The deck of a ship adrift. All around, nothing but ocean. "
            "One door leads to the captain's cabin and one to the hold; "
            "two more have a lock. In the middle stands a stone statue of a giant crab."
        ),
        "outdoor": True,
        "entry": (6, 5),
        "size": (16, 24),  # twice as tall as the screen: the view scrolls with the player
    },
    "cabin": {
        "floor": "wood",
        "name": "Captain's cabin",
        "description": (
            "A wide cabin. Sea charts scattered on the floor, and eight generators humming around a square, "
            "joined by cables. At the back, an energy barrier guards a small altar. "
            "Doors lead to the galley, to an empty room and, up a ladder, to the helm."
        ),
        "outdoor": False,
        "entry": (11, 15),
        "size": (24, 18),  # half as wide and half as long again as the screen: the view scrolls
    },
    "hold": {
        "floor": "stone",
        "damp": True,
        "name": "Hold",
        "description": (
            "Dark, overturned crates and the smell of brine. Five numbered tiles shine in the floor, "
            "from 1 to 5. At the back, an altar wrapped in a barrier; "
            "in a corner, a barrel covered in symbols. A narrow door leads to the infirmary."
        ),
        "outdoor": False,
        "entry": (7, 2),
    },
    "crab_room": {
        "floor": "tiles",
        "name": "Crab's room",
        "description": "A damp room full of shells. A huge crab watches you in silence.",
        "outdoor": False,
        "entry": (2, 5),
    },
    "angel_room": {
        "floor": "tiles",
        "name": "Angel's room",
        "description": "A room flooded with white light. In the middle, an angel smiles at you.",
        "outdoor": False,
        "entry": (13, 5),
    },
    "infirmary": {
        "floor": "tiles",
        "name": "Infirmary",
        "description": (
            "Empty beds with grey sheets, a cabinet full of bottles. "
            "The air is cold, and something in here does not want you to stay. "
            "A low passage opens in the south wall."
        ),
        "outdoor": False,
        "entry": (13, 5),
    },
    "galley": {
        "floor": "wood",
        "name": "Galley",
        "description": "Pots hanging from the ceiling, a cold stove and a table laid for a meal nobody ate.",
        "outdoor": False,
        "entry": (13, 5),
    },
    "helm": {
        "floor": "wood",
        "name": "Helm",
        "description": (
            "The ship's wheel turns slowly on its own. Through the windows, only fog. "
            "On the floor, a faint ring of purple light."
        ),
        "outdoor": False,
        "entry": (11, 8),
    },
    "east_room": {
        "floor": "wood",
        "name": "Empty room",
        "description": "An empty room. Marks on the floor show where furniture used to stand.",
        "outdoor": False,
        "entry": (2, 5),
    },
    "corridor": {
        "floor": "stone",
        "damp": True,
        "name": "Corridor",
        "description": "A long, cramped corridor under the hold. Water drips from the low ceiling.",
        "outdoor": False,
        "entry": (12, 3),
        "size": (48, 6),  # long and cramped: the view scrolls sideways
        "dark": 150,
    },
    "corridor_end": {
        "floor": "stone",
        "damp": True,
        "name": "End of the corridor",
        "description": "The corridor ends here, in front of a ring of purple light that hums softly.",
        "outdoor": False,
        "entry": (7, 8),
        "dark": 160,
    },
    "mine": {
        "floor": "earth",
        "damp": True,
        "name": "Mine",
        "description": (
            "A mine dug deep into the rock, far from the sea. Rails lead into the dark, "
            "down to a second ring of light at the far end."
        ),
        "outdoor": False,
        "entry": (7, 7),
        "size": (16, 24),
        "dark": 185,  # deep in the rock: the darkest place of all
        # Only a portal leads here: no door says where it lies, so the map is told.
        "map_pos": (34, 20),
    },
}

# Items the player can collect. An item lies in its room, on tile "pos", until it
# is picked up. If "appears_if" names a flag, it shows up only once that flag is true.
# If "free_if" names a flag, it can be seen but not picked up until that flag is true.
# An item with "gone_if" is used up for good once that flag is set.
# An item with "sets_flag" sets that flag when it is picked up (the green tincture
# makes the other three appear).
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
        "pos": (16, 1),  # on the altar, behind the barrier
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
        "pos": (7, 10),  # on the altar, behind the barrier
        "appears_if": None,
        "part_of": "fused_key",
        "free_if": "hold_solved",
        "pickup_text": (
            "You take the second key from the altar. It matches the central key: "
            "somewhere on this ship there must be an anvil to fuse the two together."
        ),
    },
    # The remedy brewed in the infirmary's cauldron: the doctor's ghost is waiting for it.
    "potion": {
        "name": "Remedy",
        "description": "A small bottle of clear, softly glowing liquid. It smells of the sea and of honey.",
        "room": "infirmary",
        "pos": (7, 6),  # in the cauldron
        "appears_if": "potion_solved",
        "gone_if": "doctor_at_peace",  # drunk: it never comes back
        "part_of": None,
        "free_if": None,
        "pickup_text": "You fill a small bottle with the remedy. It is warm in your hand.",
    },
    # The four tinctures of the remedy. The green one waits in the infirmary; when
    # it is picked up, the other three appear around the ship. They are poured into
    # the cauldron with "Use", and stay in the inventory until the remedy is made.
    "green_tincture": {
        "name": "Green tincture",
        "description": "A bottle of green tincture. It smells of seaweed.",
        "room": "infirmary",
        "pos": (5, 9),
        "appears_if": None,
        "gone_if": "potion_solved",
        "sets_flag": "tinctures_scattered",
        "part_of": None,
        "free_if": None,
        "pickup_text": (
            "You pick up the green tincture. As you lift it, glass clinks far away: "
            "the doctor's other tinctures are somewhere on the ship."
        ),
    },
    "red_tincture": {
        "name": "Red tincture",
        "description": "A bottle of red tincture. It burns the nose like pepper.",
        "room": "galley",
        "pos": (12, 3),
        "appears_if": "tinctures_scattered",
        "gone_if": "potion_solved",
        "part_of": None,
        "free_if": None,
        "pickup_text": "You pick up the red tincture, hidden among the spices.",
    },
    "gold_tincture": {
        "name": "Gold tincture",
        "description": "A bottle of gold tincture, thick and sweet like honey.",
        "room": "helm",
        "pos": (4, 3),
        "appears_if": "tinctures_scattered",
        "gone_if": "potion_solved",
        "part_of": None,
        "free_if": None,
        "pickup_text": "You pick up the gold tincture, rolling back and forth under the wheel.",
    },
    "blue_tincture": {
        "name": "Blue tincture",
        "description": "A bottle of blue tincture. It is cold, like sea water at night.",
        "room": "corridor",
        "pos": (30, 3),
        "appears_if": "tinctures_scattered",
        "gone_if": "potion_solved",
        "part_of": None,
        "free_if": None,
        "pickup_text": "You pick up the blue tincture from a puddle in the corridor.",
    },
    # Found in the mine. It has no use yet.
    "heart": {
        "name": "Heart",
        "description": "A heart of red crystal, as big as a fist. It beats, slowly, in your hand.",
        "room": "mine",
        "pos": (4, 9),
        "appears_if": None,
        "part_of": None,
        "free_if": None,
        # It is never carried: picking it up uses it at once, and it is gone for good.
        "consumed": True,
        "sets_flag": "heart_used",
        "gone_if": "heart_used",
        "pickup_text": "You pick up the heart of red crystal. It beats once in your hand, and crumbles to dust.",
        # In a game for two: what it says when it brings the other player back into the game.
        "revive_text": "The heart beats once in your hand, and crumbles to dust. Your partner is back, right next to you!",
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

# Who carries each item in a game for two: 1 or 2 ("holder_<item>"). Alone, it stays 1.
for _item in ITEMS:
    FLAGS["holder_" + _item] = 1
    # Where an item lies after a player dropped it: "room,column,row", or None while
    # it is where the story put it (or in someone's hands).
    FLAGS["dropped_" + _item] = None

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
    "hold_to_infirmary": {
        "room": "hold", "to": "infirmary", "side": "W",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "infirmary_to_hold": {
        "room": "infirmary", "to": "hold", "side": "E",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "cabin_to_galley": {
        "room": "cabin", "to": "galley", "side": "W",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "galley_to_cabin": {
        "room": "galley", "to": "cabin", "side": "E",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "cabin_to_east_room": {
        "room": "cabin", "to": "east_room", "side": "E",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "east_room_to_cabin": {
        "room": "east_room", "to": "cabin", "side": "W",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "cabin_to_helm": {
        "room": "cabin", "to": "helm", "side": "N", "at": 11,
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "helm_to_cabin": {
        "room": "helm", "to": "cabin", "side": "S", "at": 11,
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "infirmary_to_corridor": {
        "room": "infirmary", "to": "corridor", "side": "S", "at": 12,
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "corridor_to_infirmary": {
        "room": "corridor", "to": "infirmary", "side": "N", "at": 12,
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "corridor_to_end": {
        "room": "corridor", "to": "corridor_end", "side": "N", "at": 39,
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "end_to_corridor": {
        "room": "corridor_end", "to": "corridor", "side": "S",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
}

# A door is in the middle of its wall, unless "at" says on which tile its
# opening starts (counted along the wall): a wall can then have more than one door.

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
# - "cauldron" is where a potion puzzle is brewed: the tinctures of its recipe
#   (items) are used on it, one at a time. The remedy lies in it when ready.
# - Any object can have "appears_if" (it stands only once the flag is set, like
#   the anvil) and "gone_if" (it is gone once the flag is set, like the doctor).
# - "portal" is a ring of light on the floor: walking into it takes the player
#   to the portal named in "to", in another room, wherever that is. A portal
#   whose "to" is None only receives: nothing happens near it.
# - "decor" is furniture: E ignores it, unless it is a "clue" (a note to read),
#   which E offers to "Examine". It blocks the way if "solid" is true; if not, the
#   player walks over it (a rope on the floor). "picture" names its sprite, so
#   many pieces can share one.
# The barrel of the hold is still a simple puzzle: it only asks for the wand.
OBJECTS = {
    # The generators of the cabin, in a ring around a square: A top left, B top
    # middle, C top right, then D, E, F, G and H on round the square. Each one is
    # wired to the two next to it in the ring, and to no other.
    "generator_a": {
        "kind": "switch",
        "name": "Generator A",
        "label": "A",
        "room": "cabin",
        "pos": (6, 4),
        "flag": "generator_a",
        "toggles": ["generator_a", "generator_h", "generator_b"],
        "toggle_text": "Click! A, H and B switch over.",
        "look_text": "A generator with a big lever. Its plate says \"A\".",
        "done_text": None,
        "reactions": {},
    },
    "generator_b": {
        "kind": "switch",
        "name": "Generator B",
        "label": "B",
        "room": "cabin",
        "pos": (12, 4),
        "flag": "generator_b",
        "toggles": ["generator_b", "generator_a", "generator_c"],
        "toggle_text": "Click! B, A and C switch over.",
        "look_text": "A generator with a big lever. Its plate says \"B\".",
        "done_text": None,
        "reactions": {},
    },
    "generator_c": {
        "kind": "switch",
        "name": "Generator C",
        "label": "C",
        "room": "cabin",
        "pos": (18, 4),
        "flag": "generator_c",
        "toggles": ["generator_c", "generator_b", "generator_d"],
        "toggle_text": "Click! C, B and D switch over.",
        "look_text": "A generator with a big lever. Its plate says \"C\".",
        "done_text": None,
        "reactions": {},
    },
    "generator_d": {
        "kind": "switch",
        "name": "Generator D",
        "label": "D",
        "room": "cabin",
        "pos": (18, 9),
        "flag": "generator_d",
        "toggles": ["generator_d", "generator_c", "generator_e"],
        "toggle_text": "Click! D, C and E switch over.",
        "look_text": "A generator with a big lever. Its plate says \"D\".",
        "done_text": None,
        "reactions": {},
    },
    "generator_e": {
        "kind": "switch",
        "name": "Generator E",
        "label": "E",
        "room": "cabin",
        "pos": (18, 14),
        "flag": "generator_e",
        "toggles": ["generator_e", "generator_d", "generator_f"],
        "toggle_text": "Click! E, D and F switch over.",
        "look_text": "A generator with a big lever. Its plate says \"E\".",
        "done_text": None,
        "reactions": {},
    },
    "generator_f": {
        "kind": "switch",
        "name": "Generator F",
        "label": "F",
        "room": "cabin",
        "pos": (12, 14),
        "flag": "generator_f",
        "toggles": ["generator_f", "generator_e", "generator_g"],
        "toggle_text": "Click! F, E and G switch over.",
        "look_text": "A generator with a big lever. Its plate says \"F\".",
        "done_text": None,
        "reactions": {},
    },
    "generator_g": {
        "kind": "switch",
        "name": "Generator G",
        "label": "G",
        "room": "cabin",
        "pos": (6, 14),
        "flag": "generator_g",
        "toggles": ["generator_g", "generator_f", "generator_h"],
        "toggle_text": "Click! G, F and H switch over.",
        "look_text": "A generator with a big lever. Its plate says \"G\".",
        "done_text": None,
        "reactions": {},
    },
    "generator_h": {
        "kind": "switch",
        "name": "Generator H",
        "label": "H",
        "room": "cabin",
        "pos": (6, 9),
        "flag": "generator_h",
        "toggles": ["generator_h", "generator_g", "generator_a"],
        "toggle_text": "Click! H, G and A switch over.",
        "look_text": "A generator with a big lever. Its plate says \"H\".",
        "done_text": None,
        "reactions": {},
    },
    # The barrier fed by the generators, in front of the altar and around it.
    "barrier": {
        "kind": "barrier",
        "name": "Energy barrier",
        "room": "cabin",
        "pos": (15, 1),
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
        "pos": (16, 1),
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
    # The barrier fed by the tiles, around the altar against the bottom wall.
    "hold_barrier": {
        "kind": "barrier",
        "name": "Energy barrier",
        "room": "hold",
        "pos": (6, 9),
        "size": (3, 2),
        "open_if": "hold_solved",
        "look_text": (
            "An energy barrier wraps a small altar. Carved in its block: "
            "\"The Wave, The Return, The Short Circuit.\""
        ),
        "done_text": None,
        "reactions": {},
    },
    "hold_altar": {
        "kind": "altar",
        "name": "Altar",
        "room": "hold",
        "pos": (7, 10),
        "look_text": "A small stone altar, carved with waves.",
        "done_text": None,
        "reactions": {},
    },
    # The doctor's gift: it appears in the middle of the empty room, east of the
    # cabin, once he is at peace. Red sparks fly around it until the key is fused.
    "anvil": {
        "kind": "anvil",
        "name": "Anvil",
        "room": "east_room",
        "pos": (7, 5),
        "appears_if": "doctor_at_peace",
        "look_text": (
            "A black anvil, still warm, with a tag tied to it: \"For the one who finished my remedy.\" "
            "Here two halves of something could become one again."
        ),
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
    # The infirmary: the doctor's ghost, his cauldron and the four tinctures.
    "doctor": {
        "kind": "character",
        "name": "The doctor",
        "room": "infirmary",
        "pos": (3, 5),
        "size": (1, 2),
        "gone_if": "doctor_at_peace",
        "look_text": (
            "The ghost of the ship's doctor, pale and shaking with fever. He mutters over and over: "
            "\"The remedy... I never finished the remedy...\""
        ),
        "done_text": None,
        "reactions": {
            "potion": {
                "set_flag": "doctor_at_peace",
                "value": True,
                "consumes": True,
                "text": (
                    "The doctor drinks. The fever leaves his face, and for the first time he smiles. "
                    "\"Thank you. I have left you a gift, in the empty room beside the captain's cabin.\" "
                    "He fades like breath on a window. Far away, above deck, something heavy lands with a clang."
                ),
            },
        },
    },
    "cauldron": {
        "kind": "cauldron",
        "name": "Cauldron",
        "room": "infirmary",
        "pos": (7, 6),
        "look_text": "A copper cauldron over a weak blue flame. The doctor's four tinctures go in here.",
        "done_text": None,
        "reactions": {},
    },
    # The portal at the end of the corridor and its twin in the mine.
    "corridor_portal": {
        "kind": "portal", "name": "Portal", "room": "corridor_end", "pos": (7, 4), "size": (2, 2),
        "picture": "portal", "to": "mine_portal",
        "look_text": "A ring of purple light, humming softly. Through it you glimpse rock and rails.",
        "done_text": None, "reactions": {},
    },
    "mine_portal": {
        "kind": "portal", "name": "Portal", "room": "mine", "pos": (7, 3), "size": (2, 2),
        "picture": "portal", "to": "corridor_portal",
        "look_text": "The way back: through the light you can see the corridor of the ship.",
        "done_text": None, "reactions": {},
    },
    # A one-way portal: from the bottom of the mine straight to the helm. The ring
    # in the helm only receives ("to" is None): walking into it, or pressing E by
    # it, does nothing at all.
    "mine_exit": {
        "kind": "portal", "name": "Portal", "room": "mine", "pos": (7, 20), "size": (2, 2),
        "picture": "portal", "to": "helm_portal",
        "look_text": "A second ring of light, at the bottom of the mine. Through it you glimpse a ship's wheel.",
        "done_text": None, "reactions": {},
    },
    "helm_portal": {
        "kind": "portal", "name": "Portal", "room": "helm", "pos": (4, 6), "size": (2, 2),
        "picture": "portal", "to": None,
        "look_text": "A faint ring of purple light on the floor. It only leads here.",
        "done_text": None, "reactions": {},
    },
    # Decor: nothing to solve, but the rooms feel lived in.
    "deck_barrel_1": {
        "kind": "decor", "name": "Barrel", "room": "deck", "pos": (2, 2),
        "picture": "decor_barrel", "solid": True,
        "look_text": "A barrel of fresh water. Empty.",
        "done_text": None, "reactions": {},
    },
    "deck_barrel_2": {
        "kind": "decor", "name": "Barrel", "room": "deck", "pos": (3, 2),
        "picture": "decor_barrel", "solid": True,
        "look_text": "A barrel of salted fish. The smell is terrible.",
        "done_text": None, "reactions": {},
    },
    "deck_crate_1": {
        "kind": "decor", "name": "Crate", "room": "deck", "pos": (12, 2),
        "picture": "decor_crate", "solid": True,
        "look_text": "A crate from the port of Lisbon.",
        "done_text": None, "reactions": {},
    },
    "deck_crate_2": {
        "kind": "decor", "name": "Crate", "room": "deck", "pos": (13, 2),
        "picture": "decor_crate", "solid": True,
        "look_text": "A crate nailed shut. Something inside rattles.",
        "done_text": None, "reactions": {},
    },
    "deck_barrel_3": {
        "kind": "decor", "name": "Barrel", "room": "deck", "pos": (2, 21),
        "picture": "decor_barrel", "solid": True,
        "look_text": "A barrel of tar, sticky to the touch.",
        "done_text": None, "reactions": {},
    },
    "deck_rope": {
        "kind": "decor", "name": "Coiled rope", "room": "deck", "pos": (12, 21),
        "picture": "decor_rope", "solid": False,
        "look_text": "A coil of wet rope. Nobody tied up the sails.",
        "done_text": None, "reactions": {},
    },
    "cabin_shelf_1": {
        "kind": "decor", "name": "Bookshelf", "room": "cabin", "pos": (1, 1),
        "picture": "decor_bookshelf", "solid": True,
        "look_text": "Logbooks. The last page of each one is torn out.",
        "done_text": None, "reactions": {},
    },
    "cabin_shelf_2": {
        "kind": "decor", "name": "Bookshelf", "room": "cabin", "pos": (2, 1),
        "picture": "decor_bookshelf", "solid": True,
        "look_text": "Old atlases, swollen with damp.",
        "done_text": None, "reactions": {},
    },
    "cabin_table": {
        "kind": "decor", "name": "Chart table", "room": "cabin", "pos": (22, 1),
        "picture": "decor_table", "solid": True,
        "look_text": "A sea chart, pinned down by a compass. The course is marked in red.",
        "done_text": None, "reactions": {},
    },
    "hold_crate_1": {
        "kind": "decor", "name": "Crate", "room": "hold", "pos": (1, 1),
        "picture": "decor_crate", "solid": True,
        "look_text": "Overturned crates of ship's biscuits.",
        "done_text": None, "reactions": {},
    },
    "hold_crate_2": {
        "kind": "decor", "name": "Crate", "room": "hold", "pos": (2, 1),
        "picture": "decor_crate", "solid": True,
        "look_text": "A crate of candles, all burned down.",
        "done_text": None, "reactions": {},
    },
    "hold_crate_3": {
        "kind": "decor", "name": "Crate", "room": "hold", "pos": (13, 1),
        "picture": "decor_crate", "solid": True,
        "look_text": "A heavy crate. It will not move.",
        "done_text": None, "reactions": {},
    },
    "hold_sack": {
        "kind": "decor", "name": "Sack", "room": "hold", "pos": (14, 1),
        "picture": "decor_sack", "solid": True,
        "look_text": "A sack of flour, chewed open by rats.",
        "done_text": None, "reactions": {},
    },
    "crab_rock_1": {
        "kind": "decor", "name": "Rock", "room": "crab_room", "pos": (13, 2),
        "picture": "decor_rock", "solid": True,
        "look_text": "A rock covered in barnacles.",
        "done_text": None, "reactions": {},
    },
    "crab_rock_2": {
        "kind": "decor", "name": "Rock", "room": "crab_room", "pos": (13, 9),
        "picture": "decor_rock", "solid": True,
        "look_text": "A slippery rock. Something lives under it.",
        "done_text": None, "reactions": {},
    },
    "crab_shells_1": {
        "kind": "decor", "name": "Shells", "room": "crab_room", "pos": (5, 2),
        "picture": "decor_shells", "solid": False,
        "look_text": "Empty shells, cracked open.",
        "done_text": None, "reactions": {},
    },
    "crab_shells_2": {
        "kind": "decor", "name": "Shells", "room": "crab_room", "pos": (6, 9),
        "picture": "decor_shells", "solid": False,
        "look_text": "A heap of shells, arranged almost like a spiral.",
        "done_text": None, "reactions": {},
    },
    "angel_candle_1": {
        "kind": "decor", "name": "Candle", "room": "angel_room", "pos": (3, 2),
        "picture": "decor_candle", "solid": True,
        "look_text": "A tall candle. Its flame does not move.",
        "done_text": None, "reactions": {},
    },
    "angel_candle_2": {
        "kind": "decor", "name": "Candle", "room": "angel_room", "pos": (3, 9),
        "picture": "decor_candle", "solid": True,
        "look_text": "A tall candle. It gives no heat.",
        "done_text": None, "reactions": {},
    },
    "angel_candle_3": {
        "kind": "decor", "name": "Candle", "room": "angel_room", "pos": (8, 2),
        "picture": "decor_candle", "solid": True,
        "look_text": "A tall candle. The wax flows upwards.",
        "done_text": None, "reactions": {},
    },
    "angel_candle_4": {
        "kind": "decor", "name": "Candle", "room": "angel_room", "pos": (8, 9),
        "picture": "decor_candle", "solid": True,
        "look_text": "A tall candle, white as bone.",
        "done_text": None, "reactions": {},
    },
    "infirmary_bed_1": {
        "kind": "decor", "name": "Bed", "room": "infirmary", "pos": (2, 1),
        "picture": "decor_bed", "solid": True,
        "look_text": "A narrow bed. The sheets are cold.",
        "done_text": None, "reactions": {},
    },
    "infirmary_bed_2": {
        "kind": "decor", "name": "Bed", "room": "infirmary", "pos": (4, 1),
        "picture": "decor_bed", "solid": True,
        "look_text": "A narrow bed. Someone left a dent in the pillow.",
        "done_text": None, "reactions": {},
    },
    "infirmary_bed_3": {
        "kind": "decor", "name": "Bed", "room": "infirmary", "pos": (6, 1),
        "picture": "decor_bed", "solid": True,
        "look_text": "A narrow bed, its sheets torn to strips.",
        "done_text": None, "reactions": {},
    },
    "infirmary_notes": {
        "kind": "decor", "name": "Doctor's notes", "room": "infirmary", "pos": (8, 1),
        "picture": "decor_notes", "solid": True, "clue": True,
        "look_text": "The doctor's notes, in a shaky hand: \"Fever remedy. Begin with the green. The blue must always go in last.\"",
        "done_text": None, "reactions": {},
    },
    "infirmary_cabinet_1": {
        "kind": "decor", "name": "Medicine cabinet", "room": "infirmary", "pos": (10, 1),
        "picture": "decor_cabinet", "solid": True,
        "look_text": "Bottles with faded labels. Most are empty.",
        "done_text": None, "reactions": {},
    },
    "infirmary_cabinet_2": {
        "kind": "decor", "name": "Medicine cabinet", "room": "infirmary", "pos": (11, 1),
        "picture": "decor_cabinet", "solid": True,
        "look_text": "Bandages, scissors, a broken syringe.",
        "done_text": None, "reactions": {},
    },
    "galley_stove_1": {
        "kind": "decor", "name": "Stove", "room": "galley", "pos": (2, 1),
        "picture": "decor_stove", "solid": True,
        "look_text": "A cast-iron stove. The ashes are still warm.",
        "done_text": None, "reactions": {},
    },
    "galley_stove_2": {
        "kind": "decor", "name": "Stove", "room": "galley", "pos": (3, 1),
        "picture": "decor_stove", "solid": True,
        "look_text": "A pot of soup, gone cold long ago.",
        "done_text": None, "reactions": {},
    },
    "galley_table_1": {
        "kind": "decor", "name": "Table", "room": "galley", "pos": (6, 5),
        "picture": "decor_table", "solid": True,
        "look_text": "Plates for six. Six chairs pushed back in a hurry.",
        "done_text": None, "reactions": {},
    },
    "galley_table_2": {
        "kind": "decor", "name": "Table", "room": "galley", "pos": (7, 5),
        "picture": "decor_table", "solid": True,
        "look_text": "Someone carved a wing and a claw into the wood.",
        "done_text": None, "reactions": {},
    },
    "galley_notes": {
        "kind": "decor", "name": "Recipe", "room": "galley", "pos": (11, 1),
        "picture": "decor_notes", "solid": True, "clue": True,
        "look_text": "A page pinned to the wall, in the doctor's hand: \"As with pepper and honey: the red goes in before the gold.\"",
        "done_text": None, "reactions": {},
    },
    "galley_barrel": {
        "kind": "decor", "name": "Barrel", "room": "galley", "pos": (14, 1),
        "picture": "decor_barrel", "solid": True,
        "look_text": "A barrel of wine. Half empty.",
        "done_text": None, "reactions": {},
    },
    "galley_sack_1": {
        "kind": "decor", "name": "Sack", "room": "galley", "pos": (1, 10),
        "picture": "decor_sack", "solid": True,
        "look_text": "A sack of potatoes, sprouting.",
        "done_text": None, "reactions": {},
    },
    "galley_sack_2": {
        "kind": "decor", "name": "Sack", "room": "galley", "pos": (2, 10),
        "picture": "decor_sack", "solid": True,
        "look_text": "A sack of salt.",
        "done_text": None, "reactions": {},
    },
    "helm_wheel": {
        "kind": "decor", "name": "Ship's wheel", "room": "helm", "pos": (13, 5),
        "picture": "decor_wheel", "solid": True,
        "look_text": "The wheel turns by itself, a little at a time. It will not obey you.",
        "done_text": None, "reactions": {},
    },
    "helm_table": {
        "kind": "decor", "name": "Chart table", "room": "helm", "pos": (13, 1),
        "picture": "decor_table", "solid": True,
        "look_text": "A compass whose needle spins and spins.",
        "done_text": None, "reactions": {},
    },
    "helm_shelf": {
        "kind": "decor", "name": "Bookshelf", "room": "helm", "pos": (14, 1),
        "picture": "decor_bookshelf", "solid": True,
        "look_text": "Signal flags, folded with care.",
        "done_text": None, "reactions": {},
    },
    "deck_statue": {
        "kind": "decor", "name": "Crab statue", "room": "deck", "pos": (7, 11), "size": (2, 2),
        "picture": "decor_crab_statue", "solid": True,
        "look_text": "A stone statue of a giant crab, taller than you. Its eyes seem to follow you around the deck.",
        "done_text": None, "reactions": {},
    },
    "deck_crate_3": {
        "kind": "decor", "name": "Crate", "room": "deck", "pos": (13, 21),
        "picture": "decor_crate", "solid": True,
        "look_text": "A crate full of rusty chains.",
        "done_text": None, "reactions": {},
    },
    "deck_barrel_4": {
        "kind": "decor", "name": "Barrel", "room": "deck", "pos": (3, 21),
        "picture": "decor_barrel", "solid": True,
        "look_text": "A barrel of rainwater. Something moves at the bottom.",
        "done_text": None, "reactions": {},
    },
    "deck_rope_2": {
        "kind": "decor", "name": "Coiled rope", "room": "deck", "pos": (3, 15),
        "picture": "decor_rope", "solid": False,
        "look_text": "More rope, tangled into knots nobody could untie.",
        "done_text": None, "reactions": {},
    },
    "corridor_barrel_1": {
        "kind": "decor", "name": "Barrel", "room": "corridor", "pos": (5, 1),
        "picture": "decor_barrel", "solid": True,
        "look_text": "An empty barrel, its staves split open.",
        "done_text": None, "reactions": {},
    },
    "corridor_crate_1": {
        "kind": "decor", "name": "Crate", "room": "corridor", "pos": (20, 4),
        "picture": "decor_crate", "solid": True,
        "look_text": "A crate marked with a skull. You leave it closed.",
        "done_text": None, "reactions": {},
    },
    "corridor_lantern_1": {
        "kind": "decor", "name": "Lantern", "room": "corridor", "pos": (28, 1),
        "picture": "decor_lantern", "solid": True,
        "look_text": "A lantern that burns without oil.",
        "done_text": None, "reactions": {},
    },
    "corridor_crate_2": {
        "kind": "decor", "name": "Crate", "room": "corridor", "pos": (33, 4),
        "picture": "decor_crate", "solid": True,
        "look_text": "Empty bottles packed in straw.",
        "done_text": None, "reactions": {},
    },
    "corridor_lantern_2": {
        "kind": "decor", "name": "Lantern", "room": "corridor", "pos": (45, 1),
        "picture": "decor_lantern", "solid": True,
        "look_text": "A lantern. Its flame leans towards the portal.",
        "done_text": None, "reactions": {},
    },
    "end_lantern_1": {
        "kind": "decor", "name": "Lantern", "room": "corridor_end", "pos": (4, 2),
        "picture": "decor_lantern", "solid": True,
        "look_text": "A lantern with a purple flame.",
        "done_text": None, "reactions": {},
    },
    "end_lantern_2": {
        "kind": "decor", "name": "Lantern", "room": "corridor_end", "pos": (11, 2),
        "picture": "decor_lantern", "solid": True,
        "look_text": "A lantern with a purple flame.",
        "done_text": None, "reactions": {},
    },
    "mine_rails_1": {
        "kind": "decor", "name": "Rails", "room": "mine", "pos": (7, 9),
        "picture": "decor_rails", "solid": False,
        "look_text": "Rusty rails, still shiny where something passed recently.",
        "done_text": None, "reactions": {},
    },
    "mine_rails_2": {
        "kind": "decor", "name": "Rails", "room": "mine", "pos": (7, 10),
        "picture": "decor_rails", "solid": False,
        "look_text": "Rusty rails.",
        "done_text": None, "reactions": {},
    },
    "mine_rails_3": {
        "kind": "decor", "name": "Rails", "room": "mine", "pos": (7, 11),
        "picture": "decor_rails", "solid": False,
        "look_text": "Rusty rails.",
        "done_text": None, "reactions": {},
    },
    "mine_rails_4": {
        "kind": "decor", "name": "Rails", "room": "mine", "pos": (7, 12),
        "picture": "decor_rails", "solid": False,
        "look_text": "Rusty rails.",
        "done_text": None, "reactions": {},
    },
    "mine_rails_5": {
        "kind": "decor", "name": "Rails", "room": "mine", "pos": (7, 13),
        "picture": "decor_rails", "solid": False,
        "look_text": "Rusty rails.",
        "done_text": None, "reactions": {},
    },
    "mine_rails_6": {
        "kind": "decor", "name": "Rails", "room": "mine", "pos": (7, 14),
        "picture": "decor_rails", "solid": False,
        "look_text": "Rusty rails.",
        "done_text": None, "reactions": {},
    },
    "mine_rails_7": {
        "kind": "decor", "name": "Rails", "room": "mine", "pos": (7, 15),
        "picture": "decor_rails", "solid": False,
        "look_text": "Rusty rails.",
        "done_text": None, "reactions": {},
    },
    "mine_rails_8": {
        "kind": "decor", "name": "Rails", "room": "mine", "pos": (7, 16),
        "picture": "decor_rails", "solid": False,
        "look_text": "Rusty rails, vanishing into the rock.",
        "done_text": None, "reactions": {},
    },
    "mine_cart": {
        "kind": "decor", "name": "Mine cart", "room": "mine", "pos": (7, 17),
        "picture": "decor_minecart", "solid": True,
        "look_text": "A mine cart full of black stones that are warm to the touch.",
        "done_text": None, "reactions": {},
    },
    "mine_lantern_1": {
        "kind": "decor", "name": "Lantern", "room": "mine", "pos": (2, 2),
        "picture": "decor_lantern", "solid": True,
        "look_text": "A miner's lantern, hanging from a beam.",
        "done_text": None, "reactions": {},
    },
    "mine_lantern_2": {
        "kind": "decor", "name": "Lantern", "room": "mine", "pos": (13, 2),
        "picture": "decor_lantern", "solid": True,
        "look_text": "A miner's lantern, swinging slowly.",
        "done_text": None, "reactions": {},
    },
    "mine_crystal_1": {
        "kind": "decor", "name": "Crystal", "room": "mine", "pos": (2, 12),
        "picture": "decor_crystal", "solid": True,
        "look_text": "A purple crystal, the same colour as the portal.",
        "done_text": None, "reactions": {},
    },
    "mine_crystal_2": {
        "kind": "decor", "name": "Crystal", "room": "mine", "pos": (13, 8),
        "picture": "decor_crystal", "solid": True,
        "look_text": "A purple crystal. It hums when you get close.",
        "done_text": None, "reactions": {},
    },
    "mine_crystal_3": {
        "kind": "decor", "name": "Crystal", "room": "mine", "pos": (12, 19),
        "picture": "decor_crystal", "solid": True,
        "look_text": "A cluster of crystals growing out of the wall.",
        "done_text": None, "reactions": {},
    },
    "mine_rock_1": {
        "kind": "decor", "name": "Rock", "room": "mine", "pos": (3, 18),
        "picture": "decor_rock", "solid": True,
        "look_text": "A boulder fallen from the ceiling.",
        "done_text": None, "reactions": {},
    },
    "mine_rock_2": {
        "kind": "decor", "name": "Rock", "room": "mine", "pos": (11, 13),
        "picture": "decor_rock", "solid": True,
        "look_text": "A rock with a pickaxe stuck in it.",
        "done_text": None, "reactions": {},
    },
    "mine_crate_1": {
        "kind": "decor", "name": "Crate", "room": "mine", "pos": (2, 21),
        "picture": "decor_crate", "solid": True,
        "look_text": "A crate of candles and matches.",
        "done_text": None, "reactions": {},
    },
    "mine_crate_2": {
        "kind": "decor", "name": "Crate", "room": "mine", "pos": (13, 21),
        "picture": "decor_crate", "solid": True,
        "look_text": "A crate of dynamite. Very, very old dynamite.",
        "done_text": None, "reactions": {},
    },
    # More decor, so that the rooms do not look empty.
    "deck_anchor": {
        "kind": "decor", "name": "Anchor", "room": "deck", "pos": (1, 7),
        "picture": "decor_anchor", "solid": True,
        "look_text": "A spare anchor, red with rust. Nobody has dropped one in a long time.",
        "done_text": None, "reactions": {},
    },
    "deck_net": {
        "kind": "decor", "name": "Fishing net", "room": "deck", "pos": (5, 18),
        "picture": "decor_net", "solid": False,
        "look_text": "A fishing net spread out to dry. It is still wet.",
        "done_text": None, "reactions": {},
    },
    "deck_barrel_5": {
        "kind": "decor", "name": "Barrel", "room": "deck", "pos": (13, 14),
        "picture": "decor_barrel", "solid": True,
        "look_text": "A barrel of gunpowder, its lid nailed down twice.",
        "done_text": None, "reactions": {},
    },
    "deck_barrel_6": {
        "kind": "decor", "name": "Barrel", "room": "deck", "pos": (13, 15),
        "picture": "decor_barrel", "solid": True,
        "look_text": "A barrel of apples, all of them gone soft.",
        "done_text": None, "reactions": {},
    },
    "deck_crate_4": {
        "kind": "decor", "name": "Crate", "room": "deck", "pos": (1, 17),
        "picture": "decor_crate", "solid": True,
        "look_text": "A crate of spare sails, folded wet.",
        "done_text": None, "reactions": {},
    },
    "deck_lantern": {
        "kind": "decor", "name": "Lantern", "room": "deck", "pos": (14, 6),
        "picture": "decor_lantern", "solid": True,
        "look_text": "A storm lantern, swinging with the waves.",
        "done_text": None, "reactions": {},
    },
    "cabin_shelf_3": {
        "kind": "decor", "name": "Bookshelf", "room": "cabin", "pos": (1, 3),
        "picture": "decor_bookshelf", "solid": True,
        "look_text": "Books on knots, stars and currents.",
        "done_text": None, "reactions": {},
    },
    "cabin_shelf_4": {
        "kind": "decor", "name": "Bookshelf", "room": "cabin", "pos": (1, 4),
        "picture": "decor_bookshelf", "solid": True,
        "look_text": "A row of empty bottles, each with a little ship inside.",
        "done_text": None, "reactions": {},
    },
    "cabin_notes": {
        "kind": "decor", "name": "Captain's log", "room": "cabin", "pos": (5, 1),
        "picture": "decor_notes", "solid": True, "clue": True,
        "look_text": "The captain's log. The last entry reads: \"The wand must not fall into the wrong hands.\"",
        "done_text": None, "reactions": {},
    },
    "cabin_lantern": {
        "kind": "decor", "name": "Lantern", "room": "cabin", "pos": (8, 1),
        "picture": "decor_lantern", "solid": True,
        "look_text": "A brass lantern. Its light trembles with the generators.",
        "done_text": None, "reactions": {},
    },
    "cabin_desk_1": {
        "kind": "decor", "name": "Desk", "room": "cabin", "pos": (11, 8),
        "picture": "decor_table", "solid": True,
        "look_text": "The captain's desk, covered in sea charts.",
        "done_text": None, "reactions": {},
    },
    "cabin_desk_2": {
        "kind": "decor", "name": "Desk", "room": "cabin", "pos": (12, 8),
        "picture": "decor_table", "solid": True,
        "look_text": "A compass and a half-written letter, never sent.",
        "done_text": None, "reactions": {},
    },
    "cabin_chair": {
        "kind": "decor", "name": "Chair", "room": "cabin", "pos": (12, 10),
        "picture": "decor_chair", "solid": True,
        "look_text": "The captain's chair. It is still warm.",
        "done_text": None, "reactions": {},
    },
    "cabin_barrel_1": {
        "kind": "decor", "name": "Barrel", "room": "cabin", "pos": (1, 15),
        "picture": "decor_barrel", "solid": True,
        "look_text": "A barrel of the captain's best rum.",
        "done_text": None, "reactions": {},
    },
    "cabin_barrel_2": {
        "kind": "decor", "name": "Barrel", "room": "cabin", "pos": (1, 16),
        "picture": "decor_barrel", "solid": True,
        "look_text": "Another barrel of rum. This one is empty.",
        "done_text": None, "reactions": {},
    },
    "cabin_crate_1": {
        "kind": "decor", "name": "Crate", "room": "cabin", "pos": (22, 15),
        "picture": "decor_crate", "solid": True,
        "look_text": "A crate of maps, rolled and tied.",
        "done_text": None, "reactions": {},
    },
    "cabin_crate_2": {
        "kind": "decor", "name": "Crate", "room": "cabin", "pos": (22, 16),
        "picture": "decor_crate", "solid": True,
        "look_text": "A crate of spare cables for the generators.",
        "done_text": None, "reactions": {},
    },
    "hold_barrel_1": {
        "kind": "decor", "name": "Barrel", "room": "hold", "pos": (14, 4),
        "picture": "decor_barrel", "solid": True,
        "look_text": "A barrel of salted pork.",
        "done_text": None, "reactions": {},
    },
    "hold_barrel_2": {
        "kind": "decor", "name": "Barrel", "room": "hold", "pos": (14, 5),
        "picture": "decor_barrel", "solid": True,
        "look_text": "A barrel that sloshes when the ship rolls.",
        "done_text": None, "reactions": {},
    },
    "hold_sack_2": {
        "kind": "decor", "name": "Sack", "room": "hold", "pos": (14, 7),
        "picture": "decor_sack", "solid": True,
        "look_text": "A sack of dried beans.",
        "done_text": None, "reactions": {},
    },
    "hold_crate_4": {
        "kind": "decor", "name": "Crate", "room": "hold", "pos": (1, 9),
        "picture": "decor_crate", "solid": True,
        "look_text": "A crate of tools: hammers, nails, a saw.",
        "done_text": None, "reactions": {},
    },
    "hold_crate_5": {
        "kind": "decor", "name": "Crate", "room": "hold", "pos": (1, 10),
        "picture": "decor_crate", "solid": True,
        "look_text": "A crate stamped with a crab and a wing.",
        "done_text": None, "reactions": {},
    },
    "hold_rope": {
        "kind": "decor", "name": "Coiled rope", "room": "hold", "pos": (3, 8),
        "picture": "decor_rope", "solid": False,
        "look_text": "A thick rope, coiled on the floor.",
        "done_text": None, "reactions": {},
    },
    "hold_lantern": {
        "kind": "decor", "name": "Lantern", "room": "hold", "pos": (11, 1),
        "picture": "decor_lantern", "solid": True,
        "look_text": "A lantern hanging from a hook. It barely lights the hold.",
        "done_text": None, "reactions": {},
    },
    "crab_rock_3": {
        "kind": "decor", "name": "Rock", "room": "crab_room", "pos": (1, 9),
        "picture": "decor_rock", "solid": True,
        "look_text": "A rock scratched by claws.",
        "done_text": None, "reactions": {},
    },
    "crab_shells_3": {
        "kind": "decor", "name": "Shells", "room": "crab_room", "pos": (11, 9),
        "picture": "decor_shells", "solid": False,
        "look_text": "Shells, sorted by size.",
        "done_text": None, "reactions": {},
    },
    "crab_puddle": {
        "kind": "decor", "name": "Puddle", "room": "crab_room", "pos": (4, 7),
        "picture": "decor_puddle", "solid": False,
        "look_text": "A puddle of sea water. Tiny crabs scuttle in it.",
        "done_text": None, "reactions": {},
    },
    "angel_candle_5": {
        "kind": "decor", "name": "Candle", "room": "angel_room", "pos": (12, 2),
        "picture": "decor_candle", "solid": True,
        "look_text": "A tall candle. It smells of nothing at all.",
        "done_text": None, "reactions": {},
    },
    "angel_candle_6": {
        "kind": "decor", "name": "Candle", "room": "angel_room", "pos": (12, 9),
        "picture": "decor_candle", "solid": True,
        "look_text": "A tall candle. Its light is cold.",
        "done_text": None, "reactions": {},
    },
    "infirmary_lantern": {
        "kind": "decor", "name": "Lantern", "room": "infirmary", "pos": (14, 1),
        "picture": "decor_lantern", "solid": True,
        "look_text": "A lantern with a green glass.",
        "done_text": None, "reactions": {},
    },
    "infirmary_chair": {
        "kind": "decor", "name": "Chair", "room": "infirmary", "pos": (9, 3),
        "picture": "decor_chair", "solid": True,
        "look_text": "The doctor's chair, by the beds.",
        "done_text": None, "reactions": {},
    },
    "infirmary_bed_4": {
        "kind": "decor", "name": "Bed", "room": "infirmary", "pos": (1, 9),
        "picture": "decor_bed", "solid": True,
        "look_text": "A bed pushed against the wall, its blanket folded.",
        "done_text": None, "reactions": {},
    },
    "galley_chair_1": {
        "kind": "decor", "name": "Chair", "room": "galley", "pos": (5, 5),
        "picture": "decor_chair", "solid": True,
        "look_text": "A chair, pushed back in a hurry.",
        "done_text": None, "reactions": {},
    },
    "galley_chair_2": {
        "kind": "decor", "name": "Chair", "room": "galley", "pos": (8, 5),
        "picture": "decor_chair", "solid": True,
        "look_text": "A chair with one leg shorter than the others.",
        "done_text": None, "reactions": {},
    },
    "galley_chair_3": {
        "kind": "decor", "name": "Chair", "room": "galley", "pos": (6, 4),
        "picture": "decor_chair", "solid": True,
        "look_text": "A chair with a coat still hanging on it.",
        "done_text": None, "reactions": {},
    },
    "galley_chair_4": {
        "kind": "decor", "name": "Chair", "room": "galley", "pos": (7, 6),
        "picture": "decor_chair", "solid": True,
        "look_text": "A chair, knocked sideways.",
        "done_text": None, "reactions": {},
    },
    "galley_barrel_2": {
        "kind": "decor", "name": "Barrel", "room": "galley", "pos": (14, 10),
        "picture": "decor_barrel", "solid": True,
        "look_text": "A barrel of flour.",
        "done_text": None, "reactions": {},
    },
    "galley_sack_3": {
        "kind": "decor", "name": "Sack", "room": "galley", "pos": (3, 10),
        "picture": "decor_sack", "solid": True,
        "look_text": "A sack of onions.",
        "done_text": None, "reactions": {},
    },
    "helm_table_2": {
        "kind": "decor", "name": "Chart table", "room": "helm", "pos": (1, 1),
        "picture": "decor_table", "solid": True,
        "look_text": "Charts of a coast nobody on board has ever seen.",
        "done_text": None, "reactions": {},
    },
    "helm_lantern": {
        "kind": "decor", "name": "Lantern", "room": "helm", "pos": (14, 9),
        "picture": "decor_lantern", "solid": True,
        "look_text": "A lantern. Its flame points always north.",
        "done_text": None, "reactions": {},
    },
    "helm_barrel": {
        "kind": "decor", "name": "Barrel", "room": "helm", "pos": (1, 10),
        "picture": "decor_barrel", "solid": True,
        "look_text": "A barrel of fresh water for the helmsman.",
        "done_text": None, "reactions": {},
    },
    "corridor_puddle_1": {
        "kind": "decor", "name": "Puddle", "room": "corridor", "pos": (8, 3),
        "picture": "decor_puddle", "solid": False,
        "look_text": "Water dripping from the ceiling.",
        "done_text": None, "reactions": {},
    },
    "corridor_puddle_2": {
        "kind": "decor", "name": "Puddle", "room": "corridor", "pos": (36, 2),
        "picture": "decor_puddle", "solid": False,
        "look_text": "A puddle that reflects a purple light.",
        "done_text": None, "reactions": {},
    },
    "corridor_lantern_3": {
        "kind": "decor", "name": "Lantern", "room": "corridor", "pos": (18, 1),
        "picture": "decor_lantern", "solid": True,
        "look_text": "A lantern, nearly out.",
        "done_text": None, "reactions": {},
    },
    "corridor_sack": {
        "kind": "decor", "name": "Sack", "room": "corridor", "pos": (25, 4),
        "picture": "decor_sack", "solid": True,
        "look_text": "A wet sack of coal.",
        "done_text": None, "reactions": {},
    },
    "corridor_barrel_2": {
        "kind": "decor", "name": "Barrel", "room": "corridor", "pos": (43, 4),
        "picture": "decor_barrel", "solid": True,
        "look_text": "A barrel blocking half the corridor.",
        "done_text": None, "reactions": {},
    },
    "end_crystal_1": {
        "kind": "decor", "name": "Crystal", "room": "corridor_end", "pos": (2, 9),
        "picture": "decor_crystal", "solid": True,
        "look_text": "A purple crystal growing through the planks.",
        "done_text": None, "reactions": {},
    },
    "end_crystal_2": {
        "kind": "decor", "name": "Crystal", "room": "corridor_end", "pos": (13, 9),
        "picture": "decor_crystal", "solid": True,
        "look_text": "A purple crystal. It hums like the portal.",
        "done_text": None, "reactions": {},
    },
    "end_rock": {
        "kind": "decor", "name": "Rock", "room": "corridor_end", "pos": (12, 5),
        "picture": "decor_rock", "solid": True,
        "look_text": "A rock that has no business being on a ship.",
        "done_text": None, "reactions": {},
    },
    "mine_rock_3": {
        "kind": "decor", "name": "Rock", "room": "mine", "pos": (10, 5),
        "picture": "decor_rock", "solid": True,
        "look_text": "A rock with a vein of something shiny.",
        "done_text": None, "reactions": {},
    },
    "mine_crystal_4": {
        "kind": "decor", "name": "Crystal", "room": "mine", "pos": (4, 15),
        "picture": "decor_crystal", "solid": True,
        "look_text": "A crystal as tall as your hand, glowing faintly.",
        "done_text": None, "reactions": {},
    },
    "mine_rock_4": {
        "kind": "decor", "name": "Rock", "room": "mine", "pos": (12, 16),
        "picture": "decor_rock", "solid": True,
        "look_text": "A pile of stones, left by the miners.",
        "done_text": None, "reactions": {},
    },
    "mine_lantern_3": {
        "kind": "decor", "name": "Lantern", "room": "mine", "pos": (1, 7),
        "picture": "decor_lantern", "solid": True,
        "look_text": "A lantern nailed to a beam.",
        "done_text": None, "reactions": {},
    },
}

# Circuits of generators. When every switch of a circuit is on at the same time,
# the circuit is complete: "solved_flag" becomes true and "solved_text" is shown.
# From then on its switches stay on. Until then, they go back to their starting
# value (in FLAGS) every time the player walks into "room".
CIRCUITS = {
    "cabin_circuit": {
        "room": "cabin",
        "switches": ["generator_a", "generator_b", "generator_c", "generator_d",
                     "generator_e", "generator_f", "generator_g", "generator_h"],
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

# The endings. "good" lets the final screen pick its colors; "scene" is the
# picture above the text: the rescue at dawn, the explosion, or the crab.
ENDINGS = {
    "saved": {
        "title": "Everyone saved",
        "text": [
            "The crab taps the wand on the deck, and the sea grows calm.",
            "At dawn, a coast appears on the horizon.",
            "The ship docks: everyone on board is safe.",
        ],
        "good": True,
        "scene": "rescue",
    },
    "explosion": {
        "title": "The ship explodes",
        "text": [
            "The angel snaps the wand in two.",
            "A blinding light, then a roar.",
            "Of the ship, only smoke on the water remains.",
        ],
        "good": False,
        "scene": "explosion",
    },
    # Only in a game for two: the crab statue caught both players.
    "caught": {
        "title": "Caught by the crab",
        "text": [
            "The crab drags you both below deck, one in each claw.",
            "Then it climbs back onto its stand and turns to stone.",
            "The ship sails on into the storm, with nobody at the helm.",
        ],
        "good": False,
        "scene": "crab",
    },
}

# Potion puzzles. The ingredients are items: the player uses them on the
# cauldron one at a time, and the order matters. The next one of the "recipe"
# moves the "step_flag" on; any other spoils the mixture, and it starts over
# from an empty cauldron, the bottles still in hand. With the whole recipe in,
# the "solved_flag" is set: the bottles are used up, the remedy appears in the
# cauldron (an item with "appears_if" on that flag), and the cauldron stays done.
POTION_PUZZLES = {
    "remedy": {
        "room": "infirmary",
        "cauldron": "cauldron",
        "recipe": ["green_tincture", "red_tincture", "gold_tincture", "blue_tincture"],
        # What the player reads when a tincture goes in at the right moment (the last
        # one shows "solved_text" instead).
        "pour_texts": {
            "green_tincture": "You pour the green tincture. The mixture bubbles and turns the colour of seaweed.",
            "red_tincture": "You pour the red tincture. The mixture hisses and turns brown.",
            "gold_tincture": "You pour the gold tincture. The mixture thickens and starts to shine.",
            "blue_tincture": "You pour the blue tincture.",
        },
        "step_flag": "potion_step",
        "solved_flag": "potion_solved",
        "wrong_text": (
            "The {name} hits the mixture with a hiss, and the cauldron spits everything out. "
            "It is empty again: you have to start over."
        ),
        "solved_text": (
            "You pour the blue tincture last. The mixture goes still, turns clear, and glows softly. "
            "The remedy is ready, in the cauldron."
        ),
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
    "not_fused": "It is only half of the key, and it does not turn on its own: fuse it with the other half on an anvil.",
    "already_lit": "The tile is already lit.",
    "tiles_done": "The tiles stay lit: the hold's system is unlocked.",
    # What an open door shows when examined.
    "door_open": "An open door to: {room}.",
    # Labels of the actions offered by the E key.
    "label_pick_up": "Pick up: {item}",
    "label_enter": "Enter: {room}",
    "label_examine": "Examine",
    "label_pour": "Pour: {name}",
    "portal_text": "The light swallows you, and spits you out somewhere else.",
    "potion_done": "The remedy is ready: the cauldron needs nothing more.",
    "label_talk": "Talk",
    "label_use": "Use: {item}",
    "label_give": "Give: {item}",
    "label_activate": "Activate: {name}",
    # The window title and the menus.
    "title": "Plot Twist",
    "window_title": "Plot Twist · F11: full screen",
    "subtitle": "A mystery in the middle of the sea",
    "menu_new_game": "New game",
    "menu_resume": "Resume",
    "menu_quit": "Quit",
    "menu_continue": "Continue",
    "menu_restart": "Restart",
    "menu_main_menu": "Main menu",
    "menu_yes": "Yes",
    # The choice of the mode, after "New game", then of the character.
    "choose_mode": "How many players?",
    "menu_one_player": "1 player",
    "menu_two_players": "Host game for 2",
    "choose_character": "Choose your character",
    "choose_character_p1": "Player 1: choose",
    "choose_character_p2": "Player 2: choose",
    "character_taken": "Taken by the other player",
    "choose_waiting": "Waiting for the other player to choose...",
    "choose_difficulty": "How does the crab hunt?",
    "menu_easy": "Easy",
    "menu_hard": "Hard",
    "lobby_difficulty": "Crab: {difficulty}",
    "abilities_for_two": "Abilities only work in a game for two.",
    "ability_used": "You have already used your ability.",
    "dashes_left": "A lightning dash! {left} left",
    "dashes_none": "A lightning dash! That was the last one",
    "hint_ability": "Space: {label}",
    "hint_nurse": "Nurse: quick help",
    "ability_wasted": "Nothing happens: the crab is still a statue",
    # A game for two, on two computers on the same network: one hosts, the other joins.
    "menu_join_game": "Join game",
    "lobby_title": "Waiting for player 2",
    "lobby_address": "Your address: {address}",
    "lobby_hint": "On the other computer: Join game",
    "join_title": "Join game",
    "join_prompt": "Address of the host:",
    "join_hint": "Type the address · Enter: join · Esc: back",
    "joining": "Joining...",
    "cannot_host": "Could not host a game on this computer.",
    "cannot_join": "No game found at that address.",
    "partner_left": "The connection with the other player was lost.",
    # Handing an item to the other player, in a game for two.
    "partner": "Partner",
    "label_hand": "Give to partner: {item}",
    "given": "You hand over: {item}.",
    # Q drops the item picked up last, on the floor where the player stands.
    "dropped": "You drop: {item}",
    "nothing_to_drop": "You have nothing to drop.",
    "heart_helps": "The heart helps your partner up!",
    "back_in_game": "You are back in the game!",
    "no_partner": "Your partner is not here.",
    "partner_is_out": "Your partner is out of the game.",
    "you_are_out": "You are out of the game.",
    # The crab, in a game for two: awake from the solved cabin until the key is fused.
    "crab_wakes": "The crab statue comes alive!",
    "crab_sleeps": "The crab turns back to stone.",
    "you_are_down": "The crab got you!",
    "down_hint": "Your partner can help you up",
    "partner_down": "Your partner is down! Hold E next to them",
    "back_up": "Back on your feet!",
    "helped_up": "You helped your partner up!",
    "partner_eliminated": "Your partner is out. Their items are yours.",
    "spectator": "You are out: watch your partner",
    "crab_ending": "The crab got you both! Nobody is left to help...",
    "choose_hint": "Left/Right: choose · E: confirm · Esc: back",
    "menu_no": "No",
    "pause": "Paused",
    "hint_inventory": "I: inventory",
    # The controls, at the bottom of the title screen: one line each.
    "controls_1": "Arrows or WASD: move · E: interact",
    "controls_2": "I: inventory · Q: drop · Esc: menu",
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
    "scroll_hint": "Up/Down: scroll · I or Esc: close",
    "clues_none": "No clues yet.",
    # Shown if the save file cannot be written (for example, the disk is full).
    "save_failed": "The game cannot be saved: progress from here on could be lost.",
}


