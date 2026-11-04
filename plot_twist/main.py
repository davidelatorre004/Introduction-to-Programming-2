"""Plot Twist on screen: the window, the menus, the rooms and the player.

Run it with:  uv run python main.py

Everything is drawn on a small 256 x 224 screen, then blown up three times
without smoothing, which gives the 8-bit look. The pictures come from sprites.py
and the letters from pixel_font.py; a thing without a picture is drawn as a
colored rectangle.

The rules are not here: main.py asks engine.py what happens, and saves through
save.py after every accepted action. Most actions start from the E key; the
floor puzzles start from the player's feet, with the movement triggers checked
after each step (see floor_triggers). The sound effects come from sounds.py.
The interface keeps its own small state in a dict called `app`: which scene is
showing, where the player stands, what the text box says. The game itself is
app["state"], the engine's state.
"""

import math

import pygame

import effects
import engine
import save
import sounds
import sprites
import story
from pixel_font import PixelFont

# --- Sizes -----------------------------------------------------------------------

WIDTH, HEIGHT = 256, 224   # the small screen everything is drawn on
SCALE = 3                  # the window is three times bigger
FPS = 60
TILE = 16
HUD_HEIGHT = 2 * TILE      # the bar at the top, above the room
COLUMNS, ROWS = 16, 12     # the screen in tiles below the bar, and the size of a room unless story.py says otherwise
VIEW = pygame.Rect(0, HUD_HEIGHT, COLUMNS * TILE, ROWS * TILE)  # where the room is shown on screen

PLAYER_SIZE = 12
PLAYER_SPEED = 1.5         # pixels per frame
SPAWN_GAP = 4              # how far from a door the player appears after walking through it
REACH = 8                  # how close the player must be to a thing to act on it with E
BANNER_FRAMES = 2 * FPS    # how long the room name stays up after entering a room
DIALOG_LINES = 4           # lines of text per page of the text box
DIALOG_PADDING = 8
DIALOG_TEXT_WIDTH = WIDTH - 4 * DIALOG_PADDING  # margin and padding on both sides of the box
FADE_FRAMES = FPS // 4     # how long a room takes to come out of the dark after a door
WALK_STEP_FRAMES = 8       # frames per step of the walking animation
WAVE_FRAMES = FPS // 6     # frames between two pictures of the stormy sea (four of them)
SEA_PICTURES = 4           # pictures of the stormy sea, shown one after the other
CALM_FRAMES = FPS // 2     # frames between the two pictures of the calm sea of the good ending
BARRIER_FRAMES = 6         # frames between the two pictures of a barrier's energy
FLASH_FRAMES = FPS         # how long the tiles blink red after a mistake, before going dark
FLASH_BLINK = 6            # frames between two blinks
ALTAR_LIFT = 5             # how much higher an item lying on an altar is drawn
ENDING_SCENE_HEIGHT = 64   # the picture at the top of the ending screen
ENDING_HORIZON = 40        # where the sea starts in that picture
ENDING_MENU_TOP = 186
EXPLOSION_DELAY = 12       # frames before the ship blows up in the bad ending
EXPLOSION_WHITE = 20       # frames of the white flash of the blast
EXPLOSION_RED = 40         # frames of the red glare after it

# The direction to walk in to go through a door on each wall.
TOWARD = {"N": (0, -1), "S": (0, 1), "W": (-1, 0), "E": (1, 0)}

# --- Keys --------------------------------------------------------------------------

UP_KEYS = (pygame.K_UP, pygame.K_w)
DOWN_KEYS = (pygame.K_DOWN, pygame.K_s)
LEFT_KEYS = (pygame.K_LEFT, pygame.K_a)
RIGHT_KEYS = (pygame.K_RIGHT, pygame.K_d)
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_e)

# The keys of each player: to move, to act (E) and to open the inventory.
# Alone, the arrows and WASD both move the one player, as always.
KEYS_1P = [
    {"up": UP_KEYS, "down": DOWN_KEYS, "left": LEFT_KEYS, "right": RIGHT_KEYS,
     "act": (pygame.K_e,), "inventory": (pygame.K_i,)},
]
# Two players on one keyboard: player 1 on the left of it, player 2 on the right.
KEYS_2P = [
    {"up": (pygame.K_w,), "down": (pygame.K_s,), "left": (pygame.K_a,), "right": (pygame.K_d,),
     "act": (pygame.K_e,), "inventory": (pygame.K_q,)},
    {"up": (pygame.K_UP,), "down": (pygame.K_DOWN,), "left": (pygame.K_LEFT,), "right": (pygame.K_RIGHT,),
     "act": (pygame.K_RSHIFT,), "inventory": (pygame.K_p,)},
]

# --- Colors ------------------------------------------------------------------------

COLORS = {
    "black": (12, 12, 20),
    "text": (240, 236, 220),
    "dim_text": (150, 150, 165),
    "highlight": (255, 205, 80),
    "hud": (24, 22, 34),
    "box": (16, 16, 30),
    "sea": (20, 36, 72),
    "foam": (120, 170, 220),
    "railing": (95, 60, 30),
    "player": (90, 200, 120),
    "door_locked": (130, 85, 35),
    "keyhole": (250, 215, 90),
    "door_sealed": (115, 30, 35),
    "seal": (110, 230, 255),
    "good_ending": (24, 50, 90),
    "bad_ending": (80, 20, 20),
    "dawn": (250, 180, 120),
    "dawn_light": (252, 214, 160),
    "land": (52, 128, 80),
    "night": (40, 24, 40),
    "cable": (60, 60, 72),
    "error": (214, 64, 52),
}

# The fallback colors of the numbered tiles, if they have no picture.
TILE_COLORS = {"lit": COLORS["highlight"], "dark": COLORS["cable"], "error": COLORS["error"]}

# The kinds of object an item can lie on: drawn low, before the item, which sits a little higher.
HOLDERS = ("altar", "anvil", "cauldron")

# The sound each outcome of a floor puzzle plays (see sounds.py).
EVENT_SOUNDS = {
    "tile_lit": "blip",
    "phase_complete": "ding",
    "tiles_complete": "fanfare",
    "tiles_reset": "buzz",
    "potion_poured": "blip",
    "potion_spoiled": "buzz",
    "potion_ready": "fanfare",
    "teleported": "ding",
}

# --- The map in the corner ------------------------------------------------------------

INVENTORY_ROOM = 108  # pixels of the bar for the items carried, left of the map
MAP_SCALE = 3        # one pixel of the map for every three tiles of the ship
MAP_HALO = (70, 70, 100)  # the soft border around a room already visited

# Floor and wall color of each room.
ROOM_COLORS = {
    "deck": ((165, 115, 65), COLORS["sea"]),
    "cabin": ((120, 80, 50), (70, 45, 30)),
    "hold": ((70, 60, 55), (40, 32, 30)),
    "crab_room": ((60, 110, 110), (30, 60, 65)),
    "angel_room": ((225, 220, 200), (170, 165, 150)),
    "infirmary": ((200, 210, 205), (110, 125, 120)),
    "galley": ((120, 80, 50), (40, 32, 30)),
    "helm": ((120, 80, 50), (70, 45, 30)),
    "east_room": ((120, 80, 50), (70, 45, 30)),
    "corridor": ((70, 60, 55), (40, 32, 30)),
    "corridor_end": ((70, 60, 55), (40, 32, 30)),
    "mine": ((90, 70, 55), (50, 40, 35)),
}
DEFAULT_ROOM_COLORS = ((100, 100, 100), (50, 50, 50))

# The color of each item and of each thing standing in a room, for when it has no
# sprite. Generators need none: they are bright when on and dim when off. An id
# missing here is drawn in magenta, so something new in story.py shows up even
# before it has a color.
THING_COLORS = {
    "wand": (180, 110, 255),
    "key": (250, 210, 70),
    "second_key": (250, 210, 70),
    "barrier": (110, 230, 255),
    "hold_barrier": (110, 230, 255),
    "altar": (176, 176, 190),
    "anvil": (60, 60, 72),
    "fused_key": (250, 210, 70),
    "hold_puzzle": (110, 75, 45),
    "crab": (230, 90, 55),
    "angel": (250, 250, 235),
}
MISSING_COLOR = (255, 0, 255)


# --- Room geometry: where things are and how the player moves ------------------------


def tile_rect(col, row, width=1, height=1):
    """The rectangle on screen, in pixels, covering some tiles of the room grid."""
    return pygame.Rect(col * TILE, HUD_HEIGHT + row * TILE, width * TILE, height * TILE)


def doors_in(room):
    """The ids of the doors of a room."""
    doors = []
    for door, info in story.DOORS.items():
        if info["room"] == room:
            doors.append(door)
    return doors


def room_size(room):
    """A room's size in tiles, walls included: one screen, unless story.py gives it a "size"."""
    return story.ROOMS[room].get("size", (COLUMNS, ROWS))


def door_tiles(door):
    """The opening of a door in tiles: (column, row, width, height) in its room.

    Two tiles wide, in the middle of its wall, or from tile "at" along the wall.
    """
    info = story.DOORS[door]
    columns, rows = room_size(info["room"])
    side = info["side"]
    if side == "N" or side == "S":
        start = info.get("at", (columns - 2) // 2)
        return (start, 0 if side == "N" else rows - 1, 2, 1)
    start = info.get("at", (rows - 2) // 2)
    return (0 if side == "W" else columns - 1, start, 1, 2)


def door_rect(door):
    """The opening of a door, in pixels."""
    return tile_rect(*door_tiles(door))


def thing_rect(thing):
    """The tiles an item or an object covers: one, or "size" tiles from "pos" (like the barrier)."""
    if thing in story.ITEMS:
        col, row = story.ITEMS[thing]["pos"]
        return tile_rect(col, row)
    info = story.OBJECTS[thing]
    col, row = info["pos"]
    width, height = info.get("size", (1, 1))
    return tile_rect(col, row, width, height)


def wall_rects(room):
    """The solid parts of the walls of a room: the four sides, with a gap where each door is.

    A wall is cut into pieces at its doors, from one end to the other.
    """
    columns, rows = room_size(room)
    sides = {
        "N": tile_rect(0, 0, columns, 1),
        "S": tile_rect(0, rows - 1, columns, 1),
        "W": tile_rect(0, 0, 1, rows),
        "E": tile_rect(columns - 1, 0, 1, rows),
    }
    walls = []
    for side, wall in sides.items():
        openings = sorted(door_rect(door) for door in doors_in(room) if story.DOORS[door]["side"] == side)
        across = side == "N" or side == "S"  # the wall runs left to right, else top to bottom
        start = wall.left if across else wall.top
        for opening in openings + [None]:
            end = (wall.right if across else wall.bottom) if opening is None else (opening.left if across else opening.top)
            if end > start:
                if across:
                    walls.append(pygame.Rect(start, wall.top, end - start, wall.height))
                else:
                    walls.append(pygame.Rect(wall.left, start, wall.width, end - start))
            if opening is not None:
                start = opening.right if across else opening.bottom
    return walls


def solid_rects(state):
    """Everything the player cannot walk through right now: walls, closed doors and whatever stands in the room.

    That is puzzles, characters, generators, altars, and a barrier until it dissolves.

    Items on the floor, the numbered tiles and flat decor are not solid: the player walks over them.
    """
    solids = wall_rects(state["room"])
    for thing in engine.things_here(state):
        if thing["kind"] == "door":
            if thing["status"] != "open":
                solids.append(door_rect(thing["id"]))
        elif thing["kind"] not in ("item", "tile") and not is_flat(thing["id"]):
            solids.append(thing_rect(thing["id"]))
    return solids


def is_flat(thing):
    """True for what lies on the floor and is walked over: a portal, or flat decor like a coil of rope."""
    info = story.OBJECTS.get(thing)
    if info is None:
        return False
    return info["kind"] == "portal" or (info["kind"] == "decor" and not info["solid"])


def player_rect(position):
    """The player's rectangle, from the position of its top-left corner."""
    return pygame.Rect(round(position[0]), round(position[1]), PLAYER_SIZE, PLAYER_SIZE)


def move(position, dx, dy, solids):
    """Move the player by (dx, dy) pixels and return the new position, stopping against solids.

    It moves along x first and then along y, so the player slides along a wall
    instead of sticking to it when walking diagonally.
    """
    x, y = position
    if dx != 0:
        x += dx
        rect = player_rect((x, y))
        for solid in solids:
            if rect.colliderect(solid):
                if dx > 0:
                    rect.right = solid.left
                else:
                    rect.left = solid.right
                x = rect.x
    if dy != 0:
        y += dy
        rect = player_rect((x, y))
        for solid in solids:
            if rect.colliderect(solid):
                if dy > 0:
                    rect.bottom = solid.top
                else:
                    rect.top = solid.bottom
                y = rect.y
    return (x, y)


def sign(number):
    """-1, 0 or 1, like the direction of a movement."""
    if number > 0:
        return 1
    if number < 0:
        return -1
    return 0


def door_touched(room, position, dx, dy):
    """The door the player is walking into, or None.

    That is a door whose opening the player stands in, or one they push against:
    one pixel further in the direction they are going would overlap it. Walking
    along a wall past a door does not count.
    """
    rect = player_rect(position)
    probe = rect.move(sign(dx), sign(dy))
    for door in doors_in(room):
        opening = door_rect(door)
        if rect.colliderect(opening) or probe.colliderect(opening):
            return door
    return None


def spawn_in_front_of(door):
    """Where the player appears after walking through a door: just in front of the door back, not touching it."""
    opening = door_rect(door)
    rect = pygame.Rect(0, 0, PLAYER_SIZE, PLAYER_SIZE)
    side = story.DOORS[door]["side"]
    if side == "N":
        rect.midtop = (opening.centerx, opening.bottom + SPAWN_GAP)
    elif side == "S":
        rect.midbottom = (opening.centerx, opening.top - SPAWN_GAP)
    elif side == "W":
        rect.midleft = (opening.right + SPAWN_GAP, opening.centery)
    else:
        rect.midright = (opening.left - SPAWN_GAP, opening.centery)
    return (rect.x, rect.y)


def spawn_by_portal(portal):
    """Where the player appears after a portal: just below the portal they arrive at, not touching it."""
    ring = thing_rect(portal)
    rect = pygame.Rect(0, 0, PLAYER_SIZE, PLAYER_SIZE)
    rect.midtop = (ring.centerx, ring.bottom + SPAWN_GAP)
    return (rect.x, rect.y)


def portal_touched(state, position):
    """The portal the player has stepped into, or None: their middle is inside its ring."""
    center = player_rect(position).center
    for thing in engine.things_here(state):
        if thing["kind"] == "portal" and thing_rect(thing["id"]).inflate(-8, -8).collidepoint(center):
            return thing["id"]
    return None


def camera(room, position):
    """The top-left corner, in room pixels, of the part of the room on screen.

    A room the size of the screen does not move. A bigger one follows the player
    and stops at its edges; a smaller one is centred, with black around it.
    """
    columns, rows = room_size(room)
    center = player_rect(position).center
    corner = []
    for size, view, middle in ((columns * TILE, VIEW.width, center[0]), (rows * TILE, VIEW.height, center[1] - HUD_HEIGHT)):
        if size <= view:
            corner.append((size - view) // 2)
        else:
            corner.append(min(max(middle - view // 2, 0), size - view))
    return (corner[0], corner[1])


def spawn_at_entry(room):
    """Where the player appears when a game starts or resumes in a room: the middle of its entry tile."""
    col, row = story.ROOMS[room]["entry"]
    rect = pygame.Rect(0, 0, PLAYER_SIZE, PLAYER_SIZE)
    rect.center = tile_rect(col, row).center
    return (rect.x, rect.y)


def return_door(room, came_from):
    """The door of `room` that leads back to the room the player came from, or None."""
    for door in doors_in(room):
        if story.DOORS[door]["to"] == came_from:
            return door
    return None


# --- The floor puzzles: numbered tiles, and the zone around them -----------------------


def floor_puzzles_in(room):
    """The ids of the floor puzzles of a room."""
    return [puzzle for puzzle, info in story.FLOOR_PUZZLES.items() if info["room"] == room]


def zone_rect(puzzle):
    """The zone around a floor puzzle's tiles: walking out of it starts the phase over."""
    col, row, width, height = story.FLOOR_PUZZLES[puzzle]["zone"]
    return tile_rect(col, row, width, height)


def tile_under(state, position):
    """The numbered tile the player stands on, the one under the middle of their body, or None."""
    middle = player_rect(position).center
    for thing in engine.things_here(state):
        if thing["kind"] == "tile" and thing_rect(thing["id"]).collidepoint(middle):
            return thing["id"]
    return None


def zones_around(state, position):
    """The floor puzzles of the room whose zone has the middle of the player's body in it."""
    middle = player_rect(position).center
    return {puzzle for puzzle in floor_puzzles_in(state["room"]) if zone_rect(puzzle).collidepoint(middle)}


# --- What the player can act on with E -----------------------------------------------


def reach_rect(thing):
    """Where a thing is, to tell whether the player can reach it: its tile, or the opening of a door."""
    if thing in story.DOORS:
        return door_rect(thing)
    return thing_rect(thing)


def nearest_target(state, position):
    """The thing within reach of the player that is closest to them, or None.

    Only things E can act on count: not the numbered tiles (the feet act on them),
    nor plain decor or a portal that only receives. So a barrel next to the
    generator never gets in the way of the lever.
    """
    body = player_rect(position)
    reach = body.inflate(2 * REACH, 2 * REACH)
    nearest = None
    nearest_distance = 0
    for thing in engine.things_here(state):
        if thing["kind"] == "tile" or not engine.actions_for(state, thing["id"]):
            continue
        rect = reach_rect(thing["id"])
        if not reach.colliderect(rect):
            continue
        distance = (rect.centerx - body.centerx) ** 2 + (rect.centery - body.centery) ** 2
        if nearest is None or distance < nearest_distance:
            nearest = thing["id"]
            nearest_distance = distance
    return nearest


def target_and_actions(state, position):
    """What E would act on, and the actions it offers: the nearest thing, or else the room (which offers nothing)."""
    target = nearest_target(state, position)
    if target is None:
        target = state["room"]
    return target, engine.actions_for(state, target)


def target_name(target):
    """The name of a thing as the player sees it."""
    if target in story.ITEMS:
        return story.ITEMS[target]["name"]
    if target in story.OBJECTS:
        return story.OBJECTS[target]["name"]
    if target in story.DOORS:
        return story.MESSAGES["door"]
    return story.ROOMS[target]["name"]


def prompt(state, position):
    """The hint at the top of the screen: what E does here. With several actions, the thing's name."""
    target, actions = target_and_actions(state, position)
    if not actions:
        return ""
    if len(actions) == 1:
        return story.MESSAGES["prompt"].format(action=actions[0]["label"])
    return story.MESSAGES["prompt"].format(action=target_name(target))


def inventory_lines(state):
    """What the inventory screen lists, as (style, text) pairs: the items and their descriptions, then the clues."""
    lines = item_lines(state)
    found = engine.clues(state)
    if found:
        lines.append(("heading", story.MESSAGES["clues"]))
        for clue in found:
            lines.append(("text", clue))
    return lines


def item_lines(state):
    """The items carried, as (style, text) pairs: each name, then its description."""
    if not state["inventory"]:
        return [("text", story.MESSAGES["inventory_empty"])]
    lines = []
    for item in state["inventory"]:
        lines.append(("name", story.ITEMS[item]["name"]))
        lines.append(("text", story.ITEMS[item]["description"]))
    return lines


def clue_lines(state):
    """The clues found, as (style, text) pairs, in the order of story.CLUES."""
    found = engine.clues(state)
    if not found:
        return [("dim", story.MESSAGES["clues_none"])]
    return [("text", clue) for clue in found]


# --- Text ----------------------------------------------------------------------------


def wrap(text, width, measure):
    """Split a text into lines no wider than `width` pixels. `measure(line)` gives a line's width.

    A single word longer than the width gets a line of its own.
    """
    lines = []
    line = ""
    for word in text.split():
        candidate = word if line == "" else line + " " + word
        if line == "" or measure(candidate) <= width:
            line = candidate
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def pages(lines, per_page):
    """Group lines into the pages of the text box."""
    grouped = []
    for start in range(0, len(lines), per_page):
        grouped.append(lines[start:start + per_page])
    return grouped


def text_width(font):
    """A function that measures how wide a line of text is in this font."""
    def measure(line):
        return font.size(line)[0]
    return measure


# --- The interface state and what happens in each scene ------------------------------


def new_player(position=(0, 0)):
    """One player walking around the ship: where they are and what their feet and eyes are doing."""
    return {
        "pos": position,         # top-left corner of the player, in pixels
        "facing": (0, 1),        # the direction the player looks at
        "touching": None,        # the door the player is walking into: enter fires once per contact
        "walk": 0,               # frames the player has spent walking, for the walking animation
        "moving": False,         # whether the player moved in the last frame
        "on_tile": None,         # the numbered tile the player stood on in the last frame
        "zones": set(),          # the floor puzzles whose zone the player was in, in the last frame
    }


def new_app(fonts):
    """The state of the interface, starting on the main menu."""
    app = {
        "running": True,
        "fonts": fonts,
        "scene": "menu",         # "menu", "confirm", "mode", "character", "play", "actions", "inventory", "pause" or "ending"
        "menu_index": 0,         # the highlighted entry of the menu on screen
        "existing": None,        # the saved game found when the main menu opened, or None
        "state": None,           # the game being played (the engine's state), or None in the main menu
        "players": [new_player()],  # who walks around the ship: for now one player (see new_player)
        "dialog": [],            # pages of text waiting to be read; the player cannot move meanwhile
        "banner": "",            # room name shown for a moment after entering a room
        "banner_frames": 0,
        "actions": [],           # what the E menu offers (the "actions" scene)
        "actions_title": "",     # the name of the thing the E menu is about
        "question": "",          # what the confirm scene asks
        "confirming": "new_game",  # what "Yes" does: start a new game, or the action waiting for it
        "confirm_back": "menu",  # the scene to go back to if the answer is no
        "character_back": "menu",  # the scene Esc goes back to from the choice of the character
        "mode_back": "menu",     # the scene Esc goes back to from the choice of the mode
        "two_players": False,    # the mode chosen for the new game, until it starts
        "frame": 0,              # frames since the game started, for everything that moves on screen
        "scene_frames": 0,       # frames since the current scene started
        "fade": 0,               # frames left before the room is out of the dark
        "flash_frames": 0,       # frames left of the tiles blinking red after a mistake
        "fx": effects.new_fx(),  # the visual effects: particles, dissolves, the warp (see effects.py)
        "inventory_scroll": 0,   # how many rows the list of items is scrolled down
    }
    open_main_menu(app)
    return app


def set_scene(app, scene, menu_index=0):
    app["scene"] = scene
    app["menu_index"] = menu_index
    app["scene_frames"] = 0


def open_main_menu(app):
    """Show the main menu. "Riprendi" is offered only if the save file holds a valid game."""
    app["state"] = None
    app["existing"] = engine.restore_state(save.load_game())
    app["dialog"] = []
    app["banner_frames"] = 0
    set_scene(app, "menu")


def menu_entries(app):
    """The entries of the menu showing in the current scene: ids, or the actions of the E menu."""
    scene = app["scene"]
    if scene == "menu":
        return engine.menu_options(app["existing"]) + ["quit"]
    if scene == "pause":
        return ["continue", "restart", "main_menu", "quit"]
    if scene == "confirm":
        return ["yes", "no"]
    if scene == "ending":
        return ["new_game", "main_menu"]
    if scene == "mode":
        return ["one_player", "two_players"]
    if scene == "actions":
        return app["actions"]
    return []


def menu_labels(app):
    """What the entries of the current menu say on screen."""
    if app["scene"] == "actions":
        return [action["label"] for action in app["actions"]]
    return [story.MESSAGES["menu_" + entry] for entry in menu_entries(app)]


def choose(app, entry):
    """Do what a menu entry says."""
    if app["scene"] == "actions":
        choose_action(app, entry)
    elif entry == "new_game" or entry == "restart":
        request_new_game(app)
    elif entry == "resume":
        resume_game(app)
    elif entry == "continue":
        set_scene(app, "play")
    elif entry == "main_menu":
        open_main_menu(app)
    elif entry == "quit":
        app["running"] = False
    elif entry == "yes":
        if app["confirming"] == "new_game":
            confirm_new_game(app)
        else:
            set_scene(app, "play")
            do_action(app, app["confirming"])
    elif entry == "no":
        set_scene(app, app["confirm_back"])
    elif entry == "one_player" or entry == "two_players":
        app["two_players"] = entry == "two_players"
        choose_character(app, "mode")  # Esc on the characters comes back to the mode


def go_back(app):
    """What Esc does in a menu."""
    scene = app["scene"]
    if scene == "pause" or scene == "actions":
        set_scene(app, "play")
    elif scene == "confirm":
        set_scene(app, app["confirm_back"])
    elif scene == "ending":
        open_main_menu(app)
    elif scene == "character":
        set_scene(app, app["character_back"])
    elif scene == "mode":
        set_scene(app, app["mode_back"])


def progress(app):
    """The game a new game would replace: the one being played, or else the saved one."""
    if app["state"] is not None:
        return app["state"]
    return app["existing"]


def request_new_game(app):
    """Start a new game, but ask first if there is progress to lose. Then the mode, then the character."""
    _, outcome = engine.start_new_game(progress(app))
    if outcome["event"] == "needs_confirmation":
        app["question"] = outcome["text"]
        app["confirming"] = "new_game"
        app["confirm_back"] = app["scene"]
        set_scene(app, "confirm", menu_index=1)  # "No" is highlighted: the safe answer
    else:
        choose_mode(app, app["scene"])


def confirm_new_game(app):
    """The player said yes: the progress can go. Now the mode and the character; Esc takes them back."""
    choose_mode(app, app["confirm_back"])


def choose_mode(app, back):
    """Show the choice between one and two players. Nothing is replaced yet: Esc goes back to `back`."""
    app["mode_back"] = back
    set_scene(app, "mode")


def choose_character(app, back):
    """Show the choice of the character. Nothing is replaced yet: Esc goes back to `back`."""
    app["character_back"] = back
    set_scene(app, "character")


def character_entries():
    """The characters the player can choose from, in order."""
    return list(story.CHARACTERS)


def start_with_character(app, character):
    """The character is chosen: the new game replaces the progress and starts."""
    state, outcome = engine.start_new_game(progress(app), confirmed=True, character=character,
                                           two_players=app["two_players"])
    begin_game(app, state, outcome["text"])


def begin_game(app, state, opening_text):
    """Play a brand-new game: put the player at the start, show the opening scene, save at once."""
    app["state"] = state
    app["dialog"] = []
    set_up_players(app)
    place_at_entry(app)
    app["fade"] = FADE_FRAMES
    say(app, opening_text)
    save_progress(app)
    set_scene(app, "play")


def resume_game(app):
    """Go back to the saved game: to its ending if it is over, otherwise to the entry of its room."""
    app["state"] = app["existing"]
    app["dialog"] = []
    if engine.is_over(app["state"]):
        set_scene(app, "ending")
        return
    set_up_players(app)
    place_at_entry(app)
    app["fade"] = FADE_FRAMES
    show_banner(app, story.ROOMS[app["state"]["room"]]["name"])
    set_scene(app, "play")


def save_progress(app):
    """Save the game after an accepted action. If the disk refuses, tell the player instead of crashing."""
    try:
        save.save_game(app["state"])
    except OSError:
        say(app, story.MESSAGES["save_failed"])


def say(app, text):
    """Queue a text in the text box, split into lines and pages that fit."""
    lines = wrap(text, DIALOG_TEXT_WIDTH, text_width(app["fonts"]["text"]))
    app["dialog"].extend(pages(lines, DIALOG_LINES))


def show_banner(app, text):
    app["banner"] = text
    app["banner_frames"] = BANNER_FRAMES


def set_up_players(app):
    """As many players as the game has: one, or two in a game for two."""
    count = 2 if app["state"]["flags"]["two_players"] else 1
    app["players"] = [new_player() for _ in range(count)]


def place_at_entry(app):
    """Put player 1 at the entry of the room, and player 2 next to them."""
    first = app["players"][0]
    first["pos"] = spawn_at_entry(app["state"]["room"])
    place_beside(app, first)


def place_beside(app, leader):
    """Put the other players next to `leader`, and let everyone settle: arriving is not walking."""
    for player in app["players"]:
        if player is not leader:
            player["pos"] = beside(app["state"], leader["pos"])
        player["touching"] = None
        settle_on_floor(app, player)


def is_free_floor(state, position):
    """True if a player can stand here: inside the room, touching nothing solid, no door and no portal."""
    body = player_rect(position)
    if not tile_rect(0, 0, *room_size(state["room"])).contains(body) or body.collidelist(solid_rects(state)) != -1:
        return False
    return door_touched(state["room"], position, 0, 0) is None and portal_touched(state, position) is None


def beside(state, position):
    """Where a second player stands next to the one at `position`: on the right, else on the left."""
    x, y = position
    for dx in (PLAYER_SIZE + 2, -(PLAYER_SIZE + 2)):
        if is_free_floor(state, (x + dx, y)):
            return (x + dx, y)
    return position  # nowhere free: on the same spot (players do not block each other)


def place_after_door(app, came_from):
    """Put the players in front of the door that leads back where they came from, side by side."""
    room = app["state"]["room"]
    door = return_door(room, came_from)
    if door is None:
        place_at_entry(app)
        return
    place_at(app, door_arrivals(app["state"], door))


def place_at(app, positions):
    """Put each player on their own position, and let everyone settle: arriving is not walking."""
    for player, position in zip(app["players"], positions):
        player["pos"] = position
        player["touching"] = None
        settle_on_floor(app, player)


def side_by_side(state, first, along):
    """Where the players arrive: player 1 on `first`, player 2 next to them, PLAYER_SIZE + 2 pixels
    along the direction `along` (a unit (x, y)), on whichever side is free floor."""
    step = PLAYER_SIZE + 2
    for sign in (1, -1):
        second = (first[0] + sign * step * along[0], first[1] + sign * step * along[1])
        if is_free_floor(state, second):
            return [first, second]
    return [first, first]  # nowhere free: on the same spot (players do not block each other)


def door_arrivals(state, door):
    """Where the players arrive through `door`, the door they will see behind them: in front of it,
    side by side along its wall. Player 1 is where a player alone appears (spawn_in_front_of)."""
    along = (1, 0) if story.DOORS[door]["side"] in ("N", "S") else (0, 1)
    return side_by_side(state, spawn_in_front_of(door), along)


def portal_arrivals(state, portal):
    """Where the players arrive by `portal`: just below the ring, side by side. Player 1 is where a
    player alone appears (spawn_by_portal)."""
    return side_by_side(state, spawn_by_portal(portal), (1, 0))


def settle_on_floor(app, player):
    """Appearing somewhere is not walking there: where the player appears fires no movement trigger."""
    player["on_tile"] = tile_under(app["state"], player["pos"])
    player["zones"] = zones_around(app["state"], player["pos"])


def go_through(app, door):
    """The players walk into a door: ask the engine, then change room or explain why not."""
    came_from = app["state"]["room"]
    state, outcome = engine.perform(app["state"], {"verb": "enter", "target": door})
    if not outcome["ok"]:
        say(app, outcome["text"])
        return
    app["state"] = state
    save_progress(app)
    place_after_door(app, came_from)
    app["fade"] = FADE_FRAMES
    show_banner(app, outcome["text"])


def go_through_portal(app, portal):
    """The players step into a portal: the engine moves them, and they appear by the twin portal, side by side."""
    state, outcome = engine.perform(app["state"], {"verb": "travel", "target": portal})
    if not outcome["ok"]:
        return
    sounds.play(EVENT_SOUNDS.get(outcome["event"]))
    app["state"] = state
    save_progress(app)
    place_at(app, portal_arrivals(state, story.OBJECTS[portal]["to"]))
    if effects.FX["portals"]:
        app["fx"]["warp"] = effects.WARP_FRAMES  # a purple warp instead of the dark fade
    else:
        app["fade"] = FADE_FRAMES
    show_banner(app, story.ROOMS[state["room"]]["name"])


def floor_triggers(app, player):
    """The movement triggers of the room, checked in every frame after a player moves.

    Walking onto a numbered tile steps on it, whoever walks there. Walking out of
    the zone around the tiles leaves it, but only when no player is left in it.
    Each one fires once, when it happens: standing still on a tile does not step on
    it again. The engine decides what it means.
    """
    state = app["state"]
    tile = tile_under(state, player["pos"])
    zones = zones_around(state, player["pos"])
    stepped_on = tile if tile is not None and tile != player["on_tile"] else None
    # The zones of all the players together: a zone is left only when nobody is in it any more.
    others = set()
    for other in app["players"]:
        if other is not player:
            others |= other["zones"]
    left = sorted(player["zones"] - zones - others)
    player["on_tile"] = tile
    player["zones"] = zones
    for puzzle in left:
        floor_action(app, {"verb": "leave_zone", "target": puzzle})
    if stepped_on is not None:
        floor_action(app, {"verb": "step_on", "target": stepped_on})


def floor_action(app, action):
    """Tell the engine what the player's feet did, then play and show what happens, without stopping them.

    Refusals stay silent: walking around is not a request. The other outcomes
    play their sound and show in the banner, except the solved puzzle, which
    opens the text box. A mistake also makes the tiles blink red.
    """
    state, outcome = engine.perform(app["state"], action)
    if not outcome["ok"]:
        return
    sounds.play(EVENT_SOUNDS.get(outcome["event"]))
    show_outcome(app, action, app["state"], state, outcome)
    if outcome["event"] == "tiles_reset":
        app["flash_frames"] = FLASH_FRAMES
    if outcome["event"] == "tiles_complete":
        app["banner_frames"] = 0
        say(app, outcome["text"])
    else:
        show_banner(app, outcome["text"])
    app["state"] = state
    save_progress(app)


def interact(app, player=None):
    """E: act on the thing nearest to the player who pressed it (player 1 if not said).
    Several possible actions open a small menu."""
    player = player or app["players"][0]
    target, actions = target_and_actions(app["state"], player["pos"])
    if len(actions) == 1:
        choose_action(app, actions[0])
    elif actions:
        app["actions"] = actions
        app["actions_title"] = target_name(target)
        set_scene(app, "actions")


def choose_action(app, action):
    """Carry out an action, but ask first if it cannot be undone."""
    if action["irreversible"]:
        app["question"] = story.MESSAGES["confirm_choice"].format(action=action["label"])
        app["confirming"] = action
        app["confirm_back"] = "play"
        set_scene(app, "confirm", menu_index=1)  # "No" is highlighted: the safe answer
        return
    set_scene(app, "play")
    do_action(app, action)


def do_action(app, action):
    """Ask the engine to do an action and show what happens. An accepted action is saved at once."""
    if action["verb"] == "enter":
        go_through(app, action["target"])
        return
    state, outcome = engine.perform(app["state"], action)
    sounds.play(EVENT_SOUNDS.get(outcome["event"]))
    if outcome["event"] == "toggled":
        show_banner(app, outcome["text"])  # a generator clicks: no text box to close every time
    else:
        app["banner_frames"] = 0  # the text box takes over from an older banner
        say(app, outcome["text"])
    if outcome["ok"]:
        show_outcome(app, action, app["state"], state, outcome)
        app["state"] = state
        save_progress(app)


def handle_key(app, key):
    """React to one key press."""
    scene = app["scene"]
    if scene == "play":
        handle_play_key(app, key)
    elif scene == "inventory":
        if key in inventory_keys(app) or key == pygame.K_ESCAPE or key in confirm_keys(app):
            set_scene(app, "play")
        elif key in UP_KEYS or key in DOWN_KEYS:
            scroll_inventory(app, -1 if key in UP_KEYS else 1)
    elif scene == "character":
        handle_character_key(app, key)
    else:
        handle_menu_key(app, key)


def controls(app):
    """The keys of each player, in the order of app["players"]."""
    state = app["state"]
    if state is not None and state["flags"]["two_players"]:
        return KEYS_2P
    return KEYS_1P


def confirm_keys(app):
    """The keys that choose in a menu or turn the page of the text box: everyone's."""
    keys = list(CONFIRM_KEYS)
    for player_keys in controls(app):
        keys += [key for key in player_keys["act"] if key not in keys]
    return keys


def inventory_keys(app):
    """The keys that open and close the inventory: everyone's."""
    return [key for player_keys in controls(app) for key in player_keys["inventory"]]


def handle_character_key(app, key):
    """Keys on the choice of the character: left and right to move, E or Enter to choose, Esc to go back."""
    entries = character_entries()
    if key in LEFT_KEYS:
        app["menu_index"] = (app["menu_index"] - 1) % len(entries)
    elif key in RIGHT_KEYS:
        app["menu_index"] = (app["menu_index"] + 1) % len(entries)
    elif key in confirm_keys(app):
        start_with_character(app, entries[app["menu_index"]])
    elif key == pygame.K_ESCAPE:
        go_back(app)


def handle_play_key(app, key):
    """Keys while playing: a player's action key acts (or turns the page of the text box), their
    inventory key opens the inventory, Esc pauses. Alone: E and I, as always."""
    if key == pygame.K_ESCAPE:
        set_scene(app, "pause")
    elif app["dialog"]:
        if key in confirm_keys(app):
            app["dialog"].pop(0)
        return
    for player, keys in zip(app["players"], controls(app)):
        if key in keys["act"]:
            interact(app, player)
            return
        if key in keys["inventory"]:
            app["inventory_scroll"] = 0  # the list of items always opens at the top
            set_scene(app, "inventory")
            return


def handle_menu_key(app, key):
    """Keys in a menu: up and down to move, E or Enter to choose, Esc to go back."""
    entries = menu_entries(app)
    if key in UP_KEYS:
        app["menu_index"] = (app["menu_index"] - 1) % len(entries)
    elif key in DOWN_KEYS:
        app["menu_index"] = (app["menu_index"] + 1) % len(entries)
    elif key in confirm_keys(app):
        choose(app, entries[app["menu_index"]])
    elif key == pygame.K_ESCAPE:
        go_back(app)


def is_held(pressed, keys):
    for key in keys:
        if pressed[key]:
            return True
    return False


def held_direction(pressed, keys=KEYS_1P[0]):
    """The direction (dx, dy) that a player's keys are pushing, each -1, 0 or 1.

    `keys` is the set of keys of that player (see KEYS_1P and KEYS_2P): alone, the
    arrows and WASD.
    """
    dx = 0
    dy = 0
    if is_held(pressed, keys["left"]):
        dx -= 1
    if is_held(pressed, keys["right"]):
        dx += 1
    if is_held(pressed, keys["up"]):
        dy -= 1
    if is_held(pressed, keys["down"]):
        dy += 1
    return (dx, dy)


def update(app, dx, dy, dx2=0, dy2=0):
    """Move the game on by one frame. (dx, dy) is the direction held by player 1, (dx2, dy2) by player 2.

    Each player moves with their own direction; they do not block each other.
    """
    app["frame"] += 1
    app["scene_frames"] += 1
    update_effects(app)
    for player in app["players"]:
        player["moving"] = False
    if app["banner_frames"] > 0:
        app["banner_frames"] -= 1
    if app["fade"] > 0:
        app["fade"] -= 1
    if app["flash_frames"] > 0:
        app["flash_frames"] -= 1
    if app["scene"] != "play" or app["dialog"]:
        return
    if engine.is_over(app["state"]):
        set_scene(app, "ending")  # the last text has been read: on to the ending
        return
    room = app["state"]["room"]
    for player, (pdx, pdy) in zip(app["players"], [(dx, dy), (dx2, dy2)]):
        if app["state"]["room"] != room or app["scene"] != "play":
            return  # someone went through: the others have been placed by them
        move_player(app, player, pdx, pdy)


def move_player(app, player, dx, dy):
    """One player's frame: walk, go through a door, step on the tiles, walk into a portal.

    Alone, a door or a portal is taken as soon as the player walks into it. Two players
    go through together: only when both touch the same door, or stand in the same portal.
    """
    if dy != 0:
        player["facing"] = (0, dy)
    elif dx != 0:
        player["facing"] = (dx, 0)
    speed = PLAYER_SPEED
    if dx != 0 and dy != 0:
        speed = PLAYER_SPEED * 0.7071  # the same speed on diagonals
    before = player["pos"]
    player["pos"] = move(player["pos"], dx * speed, dy * speed, solid_rects(app["state"]))
    together = len(app["players"]) > 1
    if together:
        keep_in_room(app, player)  # waiting in a door's opening, a player does not walk out of the room
    if player["pos"] != before:
        player["moving"] = True
        player["walk"] += 1
    door = door_touched(app["state"]["room"], player["pos"], dx, dy)
    portal = portal_touched(app["state"], player["pos"])
    if not together:
        if door is None:
            player["touching"] = None
        elif door != player["touching"]:
            player["touching"] = door
            go_through(app, door)
        floor_triggers(app, player)
        portal = portal_touched(app["state"], player["pos"])
        if portal is not None:
            go_through_portal(app, portal)
        return
    # Two players: "touching" is the door or the portal the player is at.
    contact = door or (portal if portal is not None and story.OBJECTS[portal]["to"] is not None else None)
    if contact is None:
        player["touching"] = None
    elif contact != player["touching"]:
        player["touching"] = contact
        if all(other["touching"] == contact for other in app["players"]):
            if door is not None:
                go_through(app, door)
            else:
                go_through_portal(app, portal)
            return
        show_banner(app, story.MESSAGES["wait_partner"])  # once for each contact
    floor_triggers(app, player)


def keep_in_room(app, player):
    """Keep a player's body inside the room: an open door's opening is in the wall, not beyond it."""
    body = player_rect(player["pos"])
    inside = body.clamp(tile_rect(0, 0, *room_size(app["state"]["room"])))
    if inside.topleft != body.topleft:
        player["pos"] = (player["pos"][0] + inside.x - body.x, player["pos"][1] + inside.y - body.y)


# --- Visual effects: what happens on screen when something happens in the game -----------
#
# effects.py has the tools (particles, glows, dissolves, the warp) and the switches;
# here they are tied to the things of the game. Nothing here changes the game.

FUSE_MEET = 28        # frame of the welding when the two halves meet
FUSE_RISE = 30        # how many pixels above the anvil the halves weld (above the text box)


def floor_rect(room):
    """The floor of a room, in room pixels: inside its walls."""
    columns, rows = room_size(room)
    return tile_rect(1, 1, columns - 2, rows - 2)


def standing_barriers(state):
    return {thing["id"] for thing in engine.things_here(state) if thing["kind"] == "barrier"}


def show_outcome(app, action, before, after, outcome):
    """Something was accepted: start the effects that show it. `before` and `after` are the states."""
    fx = app["fx"]
    event = outcome["event"]
    target = action.get("target")
    if len(engine.clues(after)) > len(engine.clues(before)):
        show_new_clue(app, action)
    if effects.FX["barriers"] and after["room"] == before["room"]:
        for barrier in standing_barriers(before) - standing_barriers(after):
            fx["fading"].append({"rect": thing_rect(barrier), "frames": effects.BARRIER_FADE_FRAMES})
    if event == "picked_up" and target == "wand" and effects.FX["wand"]:
        fx["wand_rise"] = {"age": 0}
    elif event == "fused" and effects.FX["anvil"]:
        anvil = thing_rect(target)
        fx["fuse"] = {"center": (anvil.centerx, anvil.top - FUSE_RISE), "age": 0}
    elif event in ("potion_poured", "potion_spoiled", "potion_ready") and effects.FX["cauldron"]:
        x, y = liquid_center(target)
        if event == "potion_poured":
            color = cauldron_color(after)
            effects.spawn(fx, x, y, effects.POUR_BUBBLES, [color, lighter(color)], speed=0.5, life=40, up=0.5,
                          spread=math.pi / 2, angle=-math.pi / 2)
        elif event == "potion_spoiled":
            effects.spawn(fx, x, y, 24, [(70, 60, 50), (40, 36, 30), (120, 100, 70)], speed=2.2, life=30,
                          gravity=0.12, up=1.2)
        else:
            effects.spawn(fx, x, y, 30, [effects.LIQUID["ready"], (255, 255, 255)], speed=1.4, life=50, up=0.6)
    elif event in ("tile_lit", "phase_complete", "tiles_complete") and effects.FX["tiles"]:
        fx["waves"].append({"center": thing_rect(target).center, "age": 0})
        if event == "tiles_complete":
            for thing in engine.things_here(after):
                if thing["kind"] == "tile":
                    x, y = thing_rect(thing["id"]).center
                    effects.spawn(fx, x, y, 8, effects.SPARK, speed=1.5, life=30, up=0.5)
    elif event == "tiles_reset" and effects.FX["tiles"]:
        if action["verb"] == "step_on":
            x, y = thing_rect(target).center
        else:
            x, y = player_rect(app["players"][0]["pos"]).center
        effects.spawn(fx, x, y, effects.MISTAKE_SPARKS, effects.RED, speed=1.8, life=24, gravity=0.05)


def show_new_clue(app, action):
    """A clue was just found: the chime, and a glow with twinkles on the thing that gave it."""
    sounds.play("clue")
    target = action.get("target")
    if not effects.FX["clues"] or target not in story.OBJECTS and target not in story.ITEMS:
        return
    rect = thing_rect(target)
    app["fx"]["clue"] = {"rect": rect, "age": 0}
    effects.spawn(app["fx"], rect.centerx, rect.centery, effects.CLUE_SPARKS, effects.CLUE, speed=1.6, life=40,
                  up=0.4)


def lighter(color, amount=60):
    return tuple(min(255, c + amount) for c in color)


def cauldron_color(state):
    """The colour of the liquid in the cauldron: it follows the recipe, then glows when the remedy is ready."""
    puzzle = story.POTION_PUZZLES["remedy"]
    if state["flags"][puzzle["solved_flag"]]:
        return effects.LIQUID["ready"]
    return effects.LIQUID[min(state["flags"][puzzle["step_flag"]], 3)]


def liquid_center(cauldron):
    """The middle of the liquid, on top of the cauldron's picture."""
    rect = thing_rect(cauldron)
    return (rect.left + 8, rect.top + 4)


def update_effects(app):
    """Move the effects on by one frame, and add the particles that keep coming (sparks, bubbles)."""
    fx = app["fx"]
    state = app["state"]
    if state is None:
        effects.update(fx)
        return
    room = state["room"]
    if fx["room"] != room:
        effects.reset_room(fx, room, floor_rect(room), not story.ROOMS[room]["outdoor"])
    rng = fx["rng"]
    frame = app["frame"]
    if app["scene"] in ("play", "actions", "inventory"):
        for thing in engine.things_here(state):
            rect = thing_rect(thing["id"]) if thing["kind"] != "door" else None
            if thing["kind"] == "switch" and thing["status"] == "on" and effects.FX["generators"]:
                if rng.random() < 1 / effects.GENERATOR_SPARK_EVERY:
                    effects.spawn(fx, rect.left + 14, rect.top + 1, rng.randint(1, 2), effects.SPARK, speed=0.8,
                                  life=18, gravity=0.06, up=0.8, spread=math.pi / 2, angle=-math.pi / 2)
            elif thing["kind"] == "cauldron" and effects.FX["cauldron"]:
                flags = state["flags"]
                if (flags["potion_step"] or flags["potion_solved"]) and frame % effects.CAULDRON_BUBBLE_EVERY == 0:
                    color = cauldron_color(state)
                    x, y = liquid_center(thing["id"])
                    effects.spawn(fx, x + rng.randint(-4, 4), y, 1, [lighter(color)], speed=0.1, life=36, up=0.35)
        for fading in fx["fading"]:
            area = fading["rect"]
            for _ in range(effects.BARRIER_SPARKS):
                effects.spawn(fx, rng.uniform(area.left, area.right), rng.uniform(area.top, area.bottom), 1,
                              effects.ENERGY, speed=1.2, life=16)
        if fx["wand_rise"] is not None:
            player = app["players"][0]
            body = player_rect(player["pos"])
            climb = fx["wand_rise"]["age"] / effects.WAND_RISE_FRAMES
            side = 1 if player["facing"][0] >= 0 else -1
            effects.spawn(fx, body.centerx + side * 5, body.bottom - 3 - climb * 12, 1, [(255, 236, 140), (186, 116, 255)],
                          speed=0.2, life=16, up=0.5)
        clue = fx["clue"]
        if clue is not None and clue["age"] % effects.CLUE_TWINKLE_EVERY == 0:
            area = clue["rect"].inflate(10, 10)
            effects.spawn(fx, rng.uniform(area.left, area.right), rng.uniform(area.top, area.bottom), 1, effects.CLUE,
                          speed=0.3, life=22, up=0.3)
        if fx["fuse"] is not None and fx["fuse"]["age"] == FUSE_MEET:
            x, y = fx["fuse"]["center"]
            effects.spawn(fx, x, y, effects.FUSE_SPARKS, effects.WELD, speed=2.6, life=36, gravity=0.08, up=0.6)
            fx["flash"] = effects.FLASH_FRAMES
    effects.update(fx)


def draw_portal_light(app, surface, thing):
    """The light turning around a ring of a portal."""
    rect = thing_rect(thing["id"])
    effects.draw_ring_light(surface, (rect.left + 16, rect.top + 15), 12, app["frame"])


def draw_cauldron_liquid(app, surface, thing):
    """The liquid in the cauldron, coloured by the recipe so far; the ready remedy glows softly."""
    state = app["state"]
    rect = thing_rect(thing["id"])
    color = cauldron_color(state)
    surface.fill(color, (rect.left + 2, rect.top + 3, 12, 1))
    surface.fill(lighter(color, 30), (rect.left + 3, rect.top + 4, 10, 1))
    wave = (app["frame"] // 10) % 8
    surface.fill(lighter(color, 80), (rect.left + 4 + wave, rect.top + 3, 1, 1))  # light on the surface
    if state["flags"]["potion_solved"]:
        effects.glow(surface, (rect.left + 8, rect.top + 4), 12, (90, 150, 170), effects.pulse(app["frame"], 0.05, 0.5, 1))


def draw_generator(app, surface, thing):
    """A generator. When on, its lamp glows and pulses. When all the others are on, the one
    still off trembles and blushes red: one more lever and the circuit is complete."""
    state = app["state"]
    rect = thing_rect(thing["id"])
    almost = effects.FX["generators"] and thing["status"] == "off" and _almost_complete(state, thing["id"])
    shake = ((app["frame"] // 3) % 3) - 1 if almost else 0
    picture = thing_picture(thing)
    if picture is None:
        draw_thing(surface, thing)
    else:
        surface.blit(picture, rect.move(shake, 0))
    if not effects.FX["generators"]:
        return
    if thing["status"] == "on":
        effects.glow(surface, (rect.left + 7, rect.top + 4), effects.GENERATOR_GLOW, (120, 100, 30),
                     effects.pulse(app["frame"], 0.09, 0.45, 1.0, rect.left * 0.1))
    elif almost:
        effects.glow(surface, rect.center, 8, (120, 30, 20), effects.pulse(app["frame"], 0.2, 0.3, 1.0))


def _almost_complete(state, switch):
    """True when every other generator of the circuit is on and only this one is off."""
    circuit = next(c for c in story.CIRCUITS.values() if switch in c["switches"])
    if state["flags"][circuit["solved_flag"]] or state["flags"][story.OBJECTS[switch]["flag"]]:
        return False
    on = sum(1 for other in circuit["switches"] if state["flags"][story.OBJECTS[other]["flag"]])
    return on == len(circuit["switches"]) - 1


def draw_barrier_energy(app, surface, thing):
    """Spots of energy running around the edge of a barrier that stands, and a flash now and then."""
    area = thing_rect(thing["id"])
    perimeter = 2 * (area.width + area.height)
    for spot in range(effects.BARRIER_EDGE_SPOTS):
        along = (app["frame"] * 1.3 + spot * perimeter / effects.BARRIER_EDGE_SPOTS) % perimeter
        x, y = point_on_edge(area, along)
        surface.fill(effects.ENERGY[1], (x, y, 2, 1))
    if (app["frame"] // 7) % 11 == 0:  # a short flash every couple of seconds
        effects.glow(surface, area.center, max(area.width, area.height) // 2, (20, 60, 70), 0.8)


def point_on_edge(area, along):
    """The point `along` pixels around the edge of a rectangle, clockwise from its top-left corner."""
    if along < area.width:
        return area.left + along, area.top
    along -= area.width
    if along < area.height:
        return area.right - 1, area.top + along
    along -= area.height
    if along < area.width:
        return area.right - 1 - along, area.bottom - 1
    along -= area.width
    return area.left, area.bottom - 1 - along


def draw_fading_barriers(app, surface):
    """The barriers that just opened, dissolving pixel by pixel."""
    tile = sprites.image("barrier_" + str((app["frame"] // BARRIER_FRAMES) % 2))
    for fading in app["fx"]["fading"]:
        area = fading["rect"]
        progress = 1 - fading["frames"] / effects.BARRIER_FADE_FRAMES
        whole = pygame.Surface(area.size, pygame.SRCALPHA)
        if tile is None:
            pygame.draw.rect(whole, THING_COLORS["barrier"], whole.get_rect(), 2)
        else:
            for x in range(0, area.width, TILE):
                for y in range(0, area.height, TILE):
                    whole.blit(tile, (x, y))
        surface.blit(effects.dissolved(whole, progress), area.topleft)


def draw_fusing_key(app, surface):
    """The two halves of the key flying together above the anvil, then the fused key building up."""
    fuse = app["fx"]["fuse"]
    if fuse is None:
        return
    x, y = fuse["center"]
    age = fuse["age"]
    halves = [sprites.image("key"), sprites.image("second_key")]
    whole = sprites.image("fused_key")
    if age < FUSE_MEET:
        gap = round(14 * (1 - age / FUSE_MEET))
        for picture, side in zip(halves, (-1, 1)):
            if picture is not None:
                surface.blit(picture, picture.get_rect(center=(x + side * gap, y)))
    elif whole is not None:
        progress = min(1.0, (age - FUSE_MEET) / 24)
        if progress < 1:
            for picture in halves:
                if picture is not None:
                    surface.blit(effects.dissolved(picture, progress), picture.get_rect(center=(x, y)))
        surface.blit(effects.dissolved(whole, progress, appearing=True), whole.get_rect(center=(x, y)))
        effects.glow(surface, (x, y), 10, (120, 90, 30), 1 - (age - FUSE_MEET) / (effects.FUSE_FRAMES - FUSE_MEET))


def draw_lights(app, surface, things):
    """The light of the room, added on top: lanterns, crystals, the blue fire of the cauldron."""
    if not effects.FX["lights"] and not effects.FX["cauldron"]:
        return
    frame = app["frame"]
    for thing in things:
        info = story.OBJECTS.get(thing["id"])
        if info is None:
            continue
        rect = thing_rect(thing["id"])
        picture = info.get("picture")
        if picture == "decor_lantern" and effects.FX["lights"]:
            flicker = effects.pulse(frame, 0.23, 0.55, 0.8, rect.left) + 0.15 * ((frame // 5 + rect.top) % 3 == 0)
            effects.glow(surface, (rect.centerx + lantern_swing(app, thing["id"])[1], rect.top + 7), effects.LANTERN_GLOW,
                         (70, 50, 20), flicker)
        elif picture == "decor_crystal" and effects.FX["lights"]:
            effects.glow(surface, rect.center, effects.CRYSTAL_GLOW, (100, 45, 150),
                         effects.pulse(frame, 0.045, 0.2, 1.0, rect.left * 0.3 + rect.top))
        elif info["kind"] == "cauldron" and effects.FX["cauldron"]:
            flicker = effects.pulse(frame, 0.3, 0.6, 0.9) + 0.1 * ((frame // 4) % 2)
            effects.glow(surface, (rect.centerx, rect.top + 13), effects.FIRE_GLOW, (20, 50, 90), flicker)


def lantern_swing(app, lantern):
    """How a lantern swings now: an angle in degrees, and how far its light moves sideways."""
    rect = thing_rect(lantern)
    angle = effects.LANTERN_SWING * math.sin(app["frame"] * 0.05 + rect.left * 0.13)
    return angle, round(angle / effects.LANTERN_SWING * 2)


_swung = {}


def draw_lantern(app, surface, thing):
    """A lantern hanging from its hook, swinging a little with the ship."""
    picture = thing_picture(thing)
    rect = thing_rect(thing["id"])
    if picture is None or not effects.FX["lights"]:
        draw_thing(surface, thing)
        return
    angle, _ = lantern_swing(app, thing["id"])
    key = round(angle)
    if key not in _swung:
        _swung[key] = pygame.transform.rotate(picture, key)
    turned = _swung[key]
    # It turns around its hook at the top: the top middle stays where it is.
    hook = (rect.centerx, rect.top + 1)
    offset = (math.sin(math.radians(-key)) * 7, (1 - math.cos(math.radians(key))) * 7)
    surface.blit(turned, turned.get_rect(center=(round(hook[0] + offset[0]), round(hook[1] + 7 - offset[1]))))


def draw_tile_effects(app, surface, things):
    """The lit tiles glow softly; a wave spreads from a tile just lit."""
    if not effects.FX["tiles"]:
        return
    for thing in things:
        if thing["kind"] == "tile" and thing["status"] == "lit" and app["flash_frames"] == 0:
            effects.glow(surface, thing_rect(thing["id"]).center, 10, (60, 50, 10),
                         effects.pulse(app["frame"], 0.08, 0.4, 0.8, thing_rect(thing["id"]).left * 0.05))
    for wave in app["fx"]["waves"]:
        progress = wave["age"] / effects.TILE_WAVE_FRAMES
        color = effects.SPARK[0] if progress < 0.4 else (effects.SPARK[2] if progress < 0.7 else (150, 110, 40))
        pygame.draw.circle(surface, color, wave["center"], 4 + round(progress * 18), 1)


def draw_wand_glow(app, screen, x, y):
    """A soft magic glow behind the wand in the bar, with a sparkle turning around it."""
    if not effects.FX["wand"]:
        return
    effects.glow(screen, (x + 8, y + 8), 8, (70, 40, 110), effects.pulse(app["frame"], 0.07, 0.4, 1.0))
    angle = app["frame"] * 0.08
    screen.fill(effects.PURPLE[1], (x + 8 + round(6 * math.cos(angle)), y + 8 + round(6 * math.sin(angle)), 1, 1))


# --- Drawing -------------------------------------------------------------------------

# The door pictures are drawn for the north wall: quarter turns (counterclockwise) for each wall.
DOOR_TURNS = {"N": 0, "W": 1, "S": 2, "E": 3}


def load_fonts():
    """The pixel font of the game at three sizes: for text, for titles, and for the big title."""
    return {"text": PixelFont(1), "title": PixelFont(2), "big": PixelFont(3)}


def draw_text(screen, font, text, color, position, align="left", shadow=False):
    """Write one line of text. `position` is its top-left, top-middle or top-right corner, as `align` says.

    With `shadow`, a dark copy just below and to the right keeps it readable over pictures.
    """
    image = font.render(text, False, color)
    rect = image.get_rect()
    if align == "center":
        rect.midtop = position
    elif align == "right":
        rect.topright = position
    else:
        rect.topleft = position
    if shadow:
        screen.blit(font.render(text, False, COLORS["black"]), rect.move(font.scale, font.scale))
    screen.blit(image, rect)


def shade(screen, area, alpha):
    """Darken an area of the screen: alpha 0 changes nothing, 255 makes it black."""
    veil = pygame.Surface(area.size, pygame.SRCALPHA)
    veil.fill((0, 0, 0, alpha))
    screen.blit(veil, area.topleft)


def dim(screen):
    """Darken whatever is on screen, to put a menu or a question on top of it."""
    shade(screen, screen.get_rect(), 150)


def draw_box(screen, rect):
    """A box for text, with a double border like old console games."""
    pygame.draw.rect(screen, COLORS["box"], rect)
    pygame.draw.rect(screen, COLORS["text"], rect, 1)
    pygame.draw.rect(screen, COLORS["dim_text"], rect.inflate(-4, -4), 1)


def draw_menu(app, screen, top):
    """The entries of the current menu, one per line from `top`, the highlighted one in color."""
    font = app["fonts"]["text"]
    for index, label in enumerate(menu_labels(app)):
        color = COLORS["text"]
        if index == app["menu_index"]:
            label = "> " + label + " <"
            color = COLORS["highlight"]
        position = (WIDTH // 2, top + index * (font.get_linesize() + 4))
        draw_text(screen, font, label, color, position, "center", shadow=True)


def wave_frame(app):
    """Which picture of the moving tiles (the stormy sea) to show now."""
    return (app["frame"] // WAVE_FRAMES) % SEA_PICTURES


def draw_sea(app, screen, area, calm=False):
    """Fill an area with moving sea: the storm, or the calm sea of the good ending."""
    if calm:
        tile = sprites.image("sea_calm_" + str((app["frame"] // CALM_FRAMES) % 2))
    else:
        tile = sprites.image("wall_deck_" + str(wave_frame(app)))
    if tile is None:
        pygame.draw.rect(screen, COLORS["sea"], area)
        return
    for x in range(area.left, area.right, TILE):
        for y in range(area.top, area.bottom, TILE):
            part = pygame.Rect(0, 0, min(TILE, area.right - x), min(TILE, area.bottom - y))
            screen.blit(tile, (x, y), part)


def bob(app):
    """How far a floating ship sways: 0 or 1 pixel, back and forth."""
    return (app["frame"] // 20) % 2


def draw_title_screen(app, screen):
    draw_sea(app, screen, screen.get_rect(), calm=True)  # the title keeps the calm sea
    ship = sprites.image("ship")
    if ship is not None:
        screen.blit(ship, ship.get_rect(center=(WIDTH // 2, 104 + bob(app))))
    font = app["fonts"]["text"]
    draw_text(screen, app["fonts"]["big"], story.MESSAGES["title"], COLORS["text"], (WIDTH // 2, 32), "center", True)
    draw_text(screen, font, story.MESSAGES["subtitle"], COLORS["foam"], (WIDTH // 2, 68), "center", True)
    lines = []
    for key in ("controls_1", "controls_2"):
        lines.extend(wrap(story.MESSAGES[key], WIDTH - 16, text_width(font)))
    for index, line in enumerate(lines):
        y = HEIGHT - 6 - (len(lines) - index) * font.get_linesize()
        draw_text(screen, font, line, COLORS["foam"], (WIDTH // 2, y), "center", True)


def draw_door(screen, door, status):
    rect = door_rect(door)
    picture = sprites.image("door_" + status, turns=DOOR_TURNS[story.DOORS[door]["side"]])
    if picture is not None:
        screen.blit(picture, rect)
        return
    # No picture: colored rectangles.
    if status == "open":
        pygame.draw.rect(screen, COLORS["black"], rect)
    elif status == "barred":
        pygame.draw.rect(screen, COLORS["black"], rect)
        for offset in range(3, max(rect.width, rect.height), 6):  # iron bars across the opening
            if rect.width > rect.height:
                pygame.draw.line(screen, COLORS["dim_text"], (rect.left + offset, rect.top), (rect.left + offset, rect.bottom - 1))
            else:
                pygame.draw.line(screen, COLORS["dim_text"], (rect.left, rect.top + offset), (rect.right - 1, rect.top + offset))
    elif status == "locked":
        pygame.draw.rect(screen, COLORS["door_locked"], rect)
        keyhole = pygame.Rect(0, 0, 4, 4)
        keyhole.center = rect.center
        pygame.draw.rect(screen, COLORS["keyhole"], keyhole)
    else:
        pygame.draw.rect(screen, COLORS["door_sealed"], rect)
        pygame.draw.line(screen, COLORS["black"], rect.topleft, rect.bottomright, 2)
        pygame.draw.line(screen, COLORS["black"], rect.topright, rect.bottomleft, 2)


def thing_picture(thing):
    """The sprite of a thing as it is now, or None.

    It tries the shared "picture" of decor ("decor_barrel"), the id with the status
    ("hold_puzzle_solved"), the id alone ("crab"), the kind with the status
    ("switch_on") and the kind alone ("altar").
    """
    names = [thing["id"] + "_" + thing["status"], thing["id"], thing["kind"] + "_" + thing["status"], thing["kind"]]
    shared = story.OBJECTS.get(thing["id"], {}).get("picture")
    if shared is not None:
        names.insert(0, shared)  # decor: many pieces share one picture
    for name in names:
        picture = sprites.image(name)
        if picture is not None:
            return picture
    return None


def draw_thing(screen, thing, lift=0):
    """A thing of the room: its sprite, or colored rectangles if it has none. `lift` raises it a little."""
    rect = thing_rect(thing["id"]).move(0, -lift)
    picture = thing_picture(thing)
    if picture is not None:
        screen.blit(picture, rect)
        return
    color = THING_COLORS.get(thing["id"], MISSING_COLOR)
    if thing["kind"] == "switch":
        color = COLORS["highlight"] if thing["status"] == "on" else COLORS["dim_text"]
    if thing["kind"] == "item":
        pygame.draw.rect(screen, color, rect.inflate(-8, -8))  # small: it lies on the floor
        return
    pygame.draw.rect(screen, color, rect.inflate(-2, -2))
    if thing["kind"] == "puzzle" and thing["status"] == "unsolved":
        pygame.draw.rect(screen, COLORS["seal"], rect.inflate(-10, -10))  # the magic seal glows
    elif thing["kind"] == "character":
        for side in (-1, 1):
            eye = pygame.Rect(0, 0, 2, 2)
            eye.center = (rect.centerx + side * 3, rect.centery - 2)
            pygame.draw.rect(screen, COLORS["black"], eye)


def player_character(app, player):
    """The character a player plays: player 1 the one chosen, player 2 the other one."""
    if player is app["players"][0]:
        return app["state"]["flags"]["character"]
    return engine.partner_character(app["state"])


def player_picture(app, player):
    """The player's sprite for the direction they face, standing (0) or in one of the two walking steps."""
    fx, fy = player["facing"]
    if fy > 0:
        direction = "down"
    elif fy < 0:
        direction = "up"
    else:
        direction = "right"  # left is right, mirrored
    step = 0
    if player["moving"]:
        step = 1 + (player["walk"] // WALK_STEP_FRAMES) % 2
    character = story.CHARACTERS[player_character(app, player)]["sprite"]
    return sprites.image(character + "_" + direction + "_" + str(step), flip=fx < 0)


def draw_player(app, screen, player):
    body = player_rect(player["pos"])
    picture = player_picture(app, player)
    if picture is not None:
        # The sprite is taller than the body: it stands on it, feet on the bottom edge.
        screen.blit(picture, picture.get_rect(midbottom=(body.centerx, body.bottom + 1)))
        return
    pygame.draw.rect(screen, COLORS["player"], body)
    fx, fy = player["facing"]
    for side in (-1, 1):
        # Two eyes side by side, on the side the player is looking at.
        eye = pygame.Rect(0, 0, 2, 2)
        eye.center = (body.centerx + fx * 3 + side * 3 * abs(fy), body.centery + fy * 3 + side * 3 * abs(fx))
        pygame.draw.rect(screen, COLORS["black"], eye)


def draw_railing(screen, room):
    """The ship's wooden railing around the deck, with a post on every tile."""
    columns, rows = room_size(room)
    rail = tile_rect(1, 1, columns - 2, rows - 2).inflate(4, 4)
    pygame.draw.rect(screen, COLORS["railing"], rail, 2)
    for x in range(rail.left + TILE - 1, rail.right - 2, TILE):
        pygame.draw.rect(screen, COLORS["railing"], (x, rail.top - 2, 2, 4))
        pygame.draw.rect(screen, COLORS["railing"], (x, rail.bottom - 2, 2, 4))
    for y in range(rail.top + TILE - 1, rail.bottom - 2, TILE):
        pygame.draw.rect(screen, COLORS["railing"], (rail.left - 2, y, 4, 2))
        pygame.draw.rect(screen, COLORS["railing"], (rail.right - 2, y, 4, 2))


def draw_barrier(app, screen, thing):
    """A barrier: its flickering energy over every tile it covers."""
    area = thing_rect(thing["id"])
    tile = sprites.image("barrier_" + str((app["frame"] // BARRIER_FRAMES) % 2))
    if tile is None:
        pygame.draw.rect(screen, THING_COLORS["barrier"], area, 2)
        return
    for x in range(area.left, area.right, TILE):
        for y in range(area.top, area.bottom, TILE):
            screen.blit(tile, (x, y))


def switch_of_flag(flag):
    """The switch (generator) whose own state is this flag, or None."""
    for switch, info in story.OBJECTS.items():
        if info["kind"] == "switch" and info["flag"] == flag:
            return switch
    return None


def draw_cables(screen, state, frame=0):
    """The cables between the generators of the room, along the sides of their square.

    A cable joins two generators that switch each other over, and lights up when both are on.
    A lit cable pulses, and a spot of current runs along it.
    """
    for switch, info in story.OBJECTS.items():
        if info["kind"] != "switch" or info["room"] != state["room"]:
            continue
        for flag in info["toggles"]:
            other = switch_of_flag(flag)
            if other is None or other <= switch:
                continue  # itself, or a cable already drawn from the other end
            lit = state["flags"][info["flag"]] and state["flags"][flag]
            start, end = thing_rect(switch).center, thing_rect(other).center
            color = COLORS["highlight"] if lit else COLORS["cable"]
            if lit and effects.FX["cables"]:
                bright = effects.pulse(frame, effects.CABLE_PULSE, 0, 1, start[0] * 0.02)
                color = tuple(round(a + (b - a) * bright) for a, b in zip(COLORS["highlight"], (255, 245, 190)))
            pygame.draw.line(screen, color, start, end, 2)
            if lit and effects.FX["cables"]:
                along = (frame * effects.CABLE_CURRENT + (start[0] + start[1]) * 0.01) % 1
                spot = (round(start[0] + (end[0] - start[0]) * along), round(start[1] + (end[1] - start[1]) * along))
                screen.fill((255, 255, 255), (spot[0] - 1, spot[1] - 1, 3, 3))


def draw_floor_puzzles(app, screen, things):
    """The zones of the room's floor puzzles, then their numbered tiles: lit, dark, or blinking red after a mistake."""
    plate = sprites.image("zone")
    for puzzle in floor_puzzles_in(app["state"]["room"]):
        area = zone_rect(puzzle)
        if plate is None:
            pygame.draw.rect(screen, COLORS["cable"], area, 1)
            continue
        for x in range(area.left, area.right, TILE):
            for y in range(area.top, area.bottom, TILE):
                screen.blit(plate, (x, y))
    font = app["fonts"]["text"]
    for thing in things:
        if thing["kind"] != "tile":
            continue
        status = thing["status"]
        if app["flash_frames"] > 0:
            blinked = (FLASH_FRAMES - app["flash_frames"]) // FLASH_BLINK  # red first, then dark, then red...
            status = "error" if blinked % 2 == 0 else "dark"
        rect = thing_rect(thing["id"])
        picture = sprites.image("tile_" + status)
        if picture is None:
            pygame.draw.rect(screen, TILE_COLORS[status], rect.inflate(-2, -2))
        else:
            screen.blit(picture, rect)
        label = story.OBJECTS[thing["id"]]["label"]
        color = COLORS["black"] if status == "lit" else COLORS["text"]
        draw_text(screen, font, label, color, (rect.centerx, rect.centery - font.size(label)[1] // 2), "center")


def on_an_altar(state, item):
    """True if an item lies on the tile of an altar (or of the anvil) of its room."""
    for thing, info in story.OBJECTS.items():
        if info["kind"] in HOLDERS and info["room"] == state["room"] and info["pos"] == story.ITEMS[item]["pos"]:
            return True
    return False


def draw_room(app, screen):
    state = app["state"]
    room = state["room"]
    floor_color, wall_color = ROOM_COLORS.get(room, DEFAULT_ROOM_COLORS)
    floor = sprites.image("floor_" + room)
    wall = sprites.image("wall_" + room + "_" + str(wave_frame(app)))
    if wall is None:
        wall = sprites.image("wall_" + room)
    screen.fill(COLORS["black"])
    columns, rows = room_size(room)
    for col in range(columns):
        for row in range(rows):
            inside = 1 <= col <= columns - 2 and 1 <= row <= rows - 2
            picture = floor if inside else wall
            if picture is None:
                pygame.draw.rect(screen, floor_color if inside else wall_color, tile_rect(col, row))
            else:
                screen.blit(picture, tile_rect(col, row))
    if story.ROOMS[room]["outdoor"]:
        draw_railing(screen, room)
    things = engine.things_here(state)
    if effects.FX["portals"]:
        for thing in things:
            if thing["kind"] == "portal":
                effects.ripple(screen, thing_rect(thing["id"]).inflate(20, 20), app["frame"])  # the floor sways
    draw_floor_puzzles(app, screen, things)
    draw_tile_effects(app, screen, things)
    draw_cables(screen, state, app["frame"])
    standing = []
    for thing in things:
        if thing["kind"] == "door":
            draw_door(screen, thing["id"], thing["status"])
        elif thing["kind"] in HOLDERS or is_flat(thing["id"]):
            draw_thing(screen, thing)  # low furniture, portals and flat decor, drawn before what lies on it
            if thing["kind"] == "cauldron" and effects.FX["cauldron"]:
                draw_cauldron_liquid(app, screen, thing)
            elif thing["kind"] == "portal" and effects.FX["portals"]:
                draw_portal_light(app, screen, thing)
        elif thing["kind"] not in ("item", "tile"):
            standing.append(thing)
    for thing in things:
        if thing["kind"] == "item":
            draw_thing(screen, thing, ALTAR_LIFT if on_an_altar(state, thing["id"]) else 0)
    # From the back of the room to the front: what stands lower on screen covers the rest.
    # The players go in order of their feet, the lower one in front.
    drawn = set()
    for player in sorted(app["players"], key=lambda one: player_rect(one["pos"]).bottom):
        feet = player_rect(player["pos"]).bottom
        for thing in standing:
            if thing["id"] not in drawn and thing_rect(thing["id"]).bottom <= feet:
                draw_standing(app, screen, thing)
                drawn.add(thing["id"])
        draw_player(app, screen, player)
    for thing in standing:
        if thing["id"] not in drawn:
            draw_standing(app, screen, thing)
    # The effects on top: barriers dissolving, the key welding, particles, dust, and the light.
    draw_fading_barriers(app, screen)
    draw_fusing_key(app, screen)
    effects.draw_clue_glow(screen, app["fx"])
    effects.draw_particles(screen, app["fx"]["particles"])
    effects.draw_dust(screen, app["fx"], app["frame"])
    draw_lights(app, screen, things)
    # The letter of each generator, on the floor above it.
    for thing in things:
        if thing["kind"] == "switch":
            rect = thing_rect(thing["id"])
            label = story.OBJECTS[thing["id"]]["label"]
            draw_text(screen, app["fonts"]["text"], label, COLORS["text"], (rect.centerx, rect.top - 10), "center", True)


def draw_standing(app, screen, thing):
    """A puzzle, character, switch or barrier: barriers, generators and lanterns have their own way of being drawn."""
    if thing["kind"] == "barrier":
        draw_barrier(app, screen, thing)
        if effects.FX["barriers"]:
            draw_barrier_energy(app, screen, thing)
    elif thing["kind"] == "switch":
        draw_generator(app, screen, thing)
    elif story.OBJECTS.get(thing["id"], {}).get("picture") == "decor_lantern":
        draw_lantern(app, screen, thing)
    else:
        draw_thing(screen, thing)


def draw_hud(app, screen):
    """The bar at the top: the room and the inventory key, then what E does here and the items carried.

    The map of the ship takes the top right corner.
    """
    font = app["fonts"]["text"]
    state = app["state"]
    pygame.draw.rect(screen, COLORS["hud"], (0, 0, WIDTH, HUD_HEIGHT))
    pygame.draw.line(screen, COLORS["dim_text"], (0, HUD_HEIGHT - 1), (WIDTH, HUD_HEIGHT - 1))
    draw_text(screen, font, story.ROOMS[state["room"]]["name"], COLORS["text"], (8, 4))
    right = map_rect().left - 6  # the map takes the right corner: the rest moves left of it
    inventory_hint = story.MESSAGES["hint_inventory_2p" if state["flags"]["two_players"] else "hint_inventory"]
    draw_text(screen, font, inventory_hint, COLORS["dim_text"], (right, 4), "right")
    if app["scene"] == "play" and not app["dialog"]:
        hint = prompt(state, app["players"][0]["pos"])
        if hint:
            draw_text(screen, font, hint, COLORS["highlight"], (8, 18))
    x = right + 4
    # 18 pixels for each item; with many items they move closer, so they never reach the hint on the left.
    gap = min(18, max(10, INVENTORY_ROOM // max(len(state["inventory"]), 1)))
    for item in reversed(state["inventory"]):
        x -= gap
        picture = sprites.image(item)
        if item == "wand":
            draw_wand_glow(app, screen, x, 14)
        if picture is None:
            pygame.draw.rect(screen, THING_COLORS.get(item, MISSING_COLOR), (x + 4, 19, 8, 8))
        else:
            screen.blit(picture, (x, 14))
    draw_map(app, screen)


def room_layout():
    """Where each room lies on the ship, in tiles: the top-left corner of each one.

    Nobody writes it down: a search from the starting room follows the doors and
    puts the next room against the wall of the door, so that the two openings
    meet. A new room in story.py lands on the map by itself. A room only a portal
    leads to has no door to follow: story.py gives its "map_pos".
    """
    places = {story.START_ROOM: (0, 0)}
    waiting = [story.START_ROOM]
    while waiting:
        room = waiting.pop(0)
        x, y = places[room]
        columns, rows = room_size(room)
        for door in doors_in(room):
            info = story.DOORS[door]
            other = info["to"]
            back = return_door(other, room)
            if other in places or back is None:
                continue
            col, row, _, _ = door_tiles(door)
            back_col, back_row, _, _ = door_tiles(back)
            other_columns, other_rows = room_size(other)
            if info["side"] == "N":
                places[other] = (x + col - back_col, y - other_rows)
            elif info["side"] == "S":
                places[other] = (x + col - back_col, y + rows)
            elif info["side"] == "W":
                places[other] = (x - other_columns, y + row - back_row)
            else:
                places[other] = (x + columns, y + row - back_row)
            waiting.append(other)
    for room, info in story.ROOMS.items():
        if room not in places:
            places[room] = info["map_pos"]
    return places


def map_rect():
    """The whole map, in the top right corner of the bar."""
    layout = room_layout()
    left = min(x for x, y in layout.values())
    top = min(y for x, y in layout.values())
    right = max(x + room_size(room)[0] for room, (x, y) in layout.items())
    bottom = max(y + room_size(room)[1] for room, (x, y) in layout.items())
    width = (right - left + MAP_SCALE - 1) // MAP_SCALE
    height = (bottom - top + MAP_SCALE - 1) // MAP_SCALE
    return pygame.Rect(WIDTH - 4 - width, (HUD_HEIGHT - height) // 2, width, height)


def map_area(room):
    """The little rectangle of a room on the map: its place on the ship, made MAP_SCALE times smaller.

    One pixel less on the right and at the bottom leaves a gap between rooms that touch.
    """
    layout = room_layout()
    left = min(x for x, y in layout.values())
    top = min(y for x, y in layout.values())
    corner = map_rect()
    x, y = layout[room]
    columns, rows = room_size(room)
    x0 = corner.left + (x - left) // MAP_SCALE
    y0 = corner.top + (y - top) // MAP_SCALE
    x1 = corner.left + (x - left + columns) // MAP_SCALE
    y1 = corner.top + (y - top + rows) // MAP_SCALE
    return pygame.Rect(x0, y0, max(x1 - x0 - 1, 1), max(y1 - y0 - 1, 1))


def map_dot(room, position):
    """Where the player is on the map: inside the room's rectangle, where they stand in the room."""
    area = map_area(room)
    columns, rows = room_size(room)
    floor = tile_rect(1, 1, columns - 2, rows - 2)
    body = player_rect(position)
    across = min(max((body.centerx - floor.left) / floor.width, 0), 1)
    down = min(max((body.centery - floor.top) / floor.height, 0), 1)
    return (area.left + round(across * (area.width - 1)), area.top + round(down * (area.height - 1)))


def draw_map(app, screen):
    """The map of the ship: only the rooms visited so far, the doors out of them, and the player."""
    state = app["state"]
    visited = engine.visited_rooms(state)
    for room in visited:
        # A visited room has a soft halo around it; the one the player is in, a halo that pulses.
        halo = map_area(room).inflate(2, 2)
        if room == state["room"]:
            strength = effects.pulse(app["frame"], 0.1, 0.3, 1.0)
            halo_color = tuple(round(c * strength) for c in COLORS["highlight"])
        else:
            halo_color = MAP_HALO
        pygame.draw.rect(screen, halo_color, halo, 1)
    for room in visited:
        color = COLORS["highlight"] if room == state["room"] else COLORS["dim_text"]
        pygame.draw.rect(screen, color, map_area(room))
    # Once the doctor is at peace, a little anvil marks the galley, if the player has seen it.
    anvil = story.OBJECTS["anvil"]
    if engine.is_standing(state, "anvil") and anvil["room"] in visited:
        area = map_area(anvil["room"])
        x, y = area.center
        screen.fill(COLORS["black"], (x - 1, y - 1, 3, 1))  # the top of the anvil...
        screen.fill(COLORS["black"], (x, y, 1, 1))          # ...and its foot
    for door, info in story.DOORS.items():
        if info["room"] in visited:  # an exit out of a known room, even towards an unknown one
            area = map_area(info["room"])
            columns, rows = room_size(info["room"])
            col, row, width, height = door_tiles(door)
            x = area.left + (col * area.width) // columns  # where the door is along its wall
            y = area.top + (row * area.height) // rows
            side = info["side"]
            if side == "N":
                y = area.top - 1
            elif side == "S":
                y = area.bottom
            elif side == "W":
                x = area.left - 1
            else:
                x = area.right
            pygame.draw.rect(screen, COLORS["dim_text"], (x, y, 1, 1))
    for player in app["players"]:
        x, y = map_dot(state["room"], player["pos"])
        pygame.draw.rect(screen, COLORS["black"], (x, y, 1, 1))


def draw_banner(app, screen):
    if app["banner_frames"] <= 0:
        return
    image = app["fonts"]["text"].render(app["banner"], False, COLORS["text"])
    box = image.get_rect(center=(WIDTH // 2, HUD_HEIGHT + 28)).inflate(20, 12)
    draw_box(screen, box)
    screen.blit(image, image.get_rect(center=box.center))


def draw_dialog(app, screen):
    if not app["dialog"]:
        return
    font = app["fonts"]["text"]
    line_height = font.get_linesize()
    height = DIALOG_LINES * line_height + 2 * DIALOG_PADDING
    box = pygame.Rect(DIALOG_PADDING, HEIGHT - DIALOG_PADDING - height, WIDTH - 2 * DIALOG_PADDING, height)
    draw_box(screen, box)
    for index, line in enumerate(app["dialog"][0]):
        position = (box.left + DIALOG_PADDING, box.top + DIALOG_PADDING + index * line_height)
        draw_text(screen, font, line, COLORS["text"], position)
    if (app["frame"] // 24) % 2 == 0:
        # A blinking arrow: press E to go on.
        x, y = box.right - 12, box.bottom - 7
        pygame.draw.polygon(screen, COLORS["highlight"], [(x - 3, y - 4), (x + 3, y - 4), (x, y - 1)])


# One drawing surface per room size, kept from frame to frame.
_room_surfaces = {}


def room_surface(room):
    """A surface as big as the whole room (with the bar's height above it, like the screen)."""
    columns, rows = room_size(room)
    size = (columns * TILE, HUD_HEIGHT + rows * TILE)
    if size not in _room_surfaces:
        _room_surfaces[size] = pygame.Surface(size)
    return _room_surfaces[size]


def view_position(app):
    """Where the camera looks: at the player, or half way between the two players."""
    players = app["players"]
    return (sum(one["pos"][0] for one in players) / len(players), sum(one["pos"][1] for one in players) / len(players))


def draw_play_screen(app, screen):
    """The room, seen through the camera, then the bar on top.

    The whole room is drawn on its own surface, in room pixels, so nothing else
    needs to know about the camera: walls, things and the player keep their places.
    """
    room = app["state"]["room"]
    whole = room_surface(room)
    draw_room(app, whole)
    x, y = camera(room, view_position(app))
    screen.fill(COLORS["black"])
    screen.set_clip(VIEW)
    screen.blit(whole, (-x, -y))
    screen.set_clip(None)
    if app["fade"] > 0:
        # Just through a door: the room comes out of the dark.
        shade(screen, VIEW, 255 * app["fade"] // FADE_FRAMES)
    effects.draw_warp(screen, VIEW, app["fx"])   # just through a portal: the purple warp
    effects.draw_flash(screen, VIEW, app["fx"])  # the white flash of the anvil
    draw_hud(app, screen)


def draw_actions(app, screen):
    """The small menu E opens when a thing offers several actions."""
    font = app["fonts"]["text"]
    line_height = font.get_linesize() + 4
    height = (len(app["actions"]) + 1) * line_height + 2 * DIALOG_PADDING
    box = pygame.Rect(DIALOG_PADDING, HEIGHT - DIALOG_PADDING - height, WIDTH - 2 * DIALOG_PADDING, height)
    draw_box(screen, box)
    draw_text(screen, font, app["actions_title"], COLORS["dim_text"], (WIDTH // 2, box.top + DIALOG_PADDING), "center")
    draw_menu(app, screen, box.top + DIALOG_PADDING + line_height)


INVENTORY_BOX = pygame.Rect(16, HUD_HEIGHT + 8, WIDTH - 32, HEIGHT - HUD_HEIGHT - 24)
CLUE_COLUMN = 82      # width of the clues column, on the left
COLUMN_TOP = 24       # where the columns start, under the titles
COLUMN_BOTTOM = 22    # room left at the bottom for the hint


def column_rows(app, lines, width):
    """The lines of a column of the inventory, wrapped to its width, one (style, text) per row.

    Every item name after the first one gets an empty row above it, to keep the items apart.
    """
    measure = text_width(app["fonts"]["text"])
    rows = []
    for style, text in lines:
        if style == "name" and rows:
            rows.append(("space", ""))
        rows += [(style, line) for line in wrap(text, width, measure)]
    return rows


def inventory_columns():
    """The two columns of the inventory screen: the clues on the left, the items on the right."""
    box = INVENTORY_BOX
    clues = pygame.Rect(box.left + 8, box.top + COLUMN_TOP, CLUE_COLUMN - 8, box.height - COLUMN_TOP - COLUMN_BOTTOM)
    items = pygame.Rect(box.left + CLUE_COLUMN + 8, clues.top, box.right - 8 - (box.left + CLUE_COLUMN + 8), clues.height)
    return clues, items


def visible_rows(app, column):
    return column.height // app["fonts"]["text"].get_linesize()


def inventory_scroll_limit(app):
    """How far down the list of items can scroll: until its last row is in view."""
    _, items = inventory_columns()
    rows = column_rows(app, item_lines(app["state"]), items.width)
    return max(0, len(rows) - visible_rows(app, items))


def scroll_inventory(app, direction):
    """Up or down the list of items, one item at a time: the next item's name goes to the top."""
    _, items = inventory_columns()
    rows = column_rows(app, item_lines(app["state"]), items.width)
    starts = [index for index, (style, _) in enumerate(rows) if style == "name"] or [0]
    now = app["inventory_scroll"]
    if direction > 0:
        later = [start for start in starts if start > now]
        target = later[0] if later else now
    else:
        earlier = [start for start in starts if start < now]
        target = earlier[-1] if earlier else 0
    app["inventory_scroll"] = max(0, min(target, inventory_scroll_limit(app)))


def draw_column(app, screen, column, rows, first=0):
    """Draw the rows of a column from row `first`, as many as fit."""
    font = app["fonts"]["text"]
    colors = {"name": COLORS["highlight"], "text": COLORS["text"], "heading": COLORS["dim_text"], "dim": COLORS["dim_text"]}
    for index, (style, line) in enumerate(rows[first:first + visible_rows(app, column)]):
        if style != "space":
            draw_text(screen, font, line, colors[style], (column.left, column.top + index * font.get_linesize()))


def draw_inventory(app, screen):
    """The inventory screen: the clues found on the left, the items carried on the right.

    The items can be many: up and down scroll their column, and small arrows say
    there is more above or below.
    """
    font = app["fonts"]["text"]
    box = INVENTORY_BOX
    draw_box(screen, box)
    clues, items = inventory_columns()
    draw_text(screen, font, story.MESSAGES["clues"], COLORS["dim_text"], (clues.centerx, box.top + 8), "center")
    draw_text(screen, font, story.MESSAGES["inventory"], COLORS["dim_text"], (items.centerx, box.top + 8), "center")
    divider = box.left + CLUE_COLUMN
    pygame.draw.line(screen, COLORS["dim_text"], (divider, box.top + 8), (divider, box.bottom - COLUMN_BOTTOM))
    draw_column(app, screen, clues, column_rows(app, clue_lines(app["state"]), clues.width))
    rows = column_rows(app, item_lines(app["state"]), items.width)
    app["inventory_scroll"] = min(app["inventory_scroll"], inventory_scroll_limit(app))
    first = app["inventory_scroll"]
    draw_column(app, screen, items, rows, first)
    x = items.right - 3
    if first > 0:  # more above
        pygame.draw.polygon(screen, COLORS["highlight"], [(x - 3, items.top + 3), (x + 3, items.top + 3), (x, items.top)])
    if first < inventory_scroll_limit(app):  # more below
        y = items.bottom - 1
        pygame.draw.polygon(screen, COLORS["highlight"], [(x - 3, y - 3), (x + 3, y - 3), (x, y)])
    hint = story.MESSAGES["close_hint"]
    if inventory_scroll_limit(app) > 0:
        hint = story.MESSAGES["scroll_hint"]
    draw_text(screen, font, hint, COLORS["dim_text"], (WIDTH // 2, box.bottom - 16), "center")


def draw_rescue(app, scene, time):
    """The good ending: dawn, a coast on the horizon, the ship sailing towards it."""
    horizon = ENDING_HORIZON
    scene.fill(COLORS["dawn"])
    pygame.draw.rect(scene, COLORS["dawn_light"], (0, horizon - 12, WIDTH, 12))
    sun_y = horizon + 4 - min(time, 180) // 9  # the sun rises
    pygame.draw.circle(scene, COLORS["highlight"], (196, sun_y), 9)
    coast = [(160, horizon), (184, horizon - 6), (210, horizon - 9), (236, horizon - 5), (WIDTH, horizon - 7),
             (WIDTH, horizon)]
    pygame.draw.polygon(scene, COLORS["land"], coast)
    draw_sea(app, scene, pygame.Rect(0, horizon, WIDTH, ENDING_SCENE_HEIGHT - horizon), calm=True)
    ship = sprites.image("ship")
    if ship is not None:
        x = 40 + min(time, 320) // 4  # sailing towards the coast
        scene.blit(ship, ship.get_rect(midbottom=(x, horizon + 6 + bob(app))))


def draw_explosion(app, scene, time):
    """The bad ending: the ship blows up, then only smoke is left on the water."""
    horizon = ENDING_HORIZON
    scene.fill(COLORS["night"])
    draw_sea(app, scene, pygame.Rect(0, horizon, WIDTH, ENDING_SCENE_HEIGHT - horizon))
    center = (WIDTH // 2, horizon - 2)
    ship = sprites.image("ship")
    if time < EXPLOSION_DELAY:
        if ship is not None:
            scene.blit(ship, ship.get_rect(midbottom=(center[0], horizon + 6)))
        return
    blast = time - EXPLOSION_DELAY
    # Smoke rising from where the ship was: each puff grows, then stays, in a column.
    for puff in range(4):
        age = min(blast - puff * 15, 90 - puff * 15)
        if age > 0:
            radius = 3 + age // 10
            pygame.draw.circle(scene, sprites.PALETTE["d"], (center[0] - 3 + (puff % 2) * 6, horizon - age // 3), radius)
    # Rings of fire growing out of the ship.
    for index, letter in enumerate("yor"):
        radius = blast * 2 - index * 6
        if 0 < radius < 70:
            pygame.draw.circle(scene, sprites.PALETTE[letter], center, radius, 3)
    # Pieces of the ship flying away and falling back.
    for piece in range(12):
        x = center[0] + (piece - 5.5) * 0.6 * blast
        y = center[1] - (2.2 + (piece % 4) * 0.4) * blast + 0.06 * blast * blast
        if y < ENDING_SCENE_HEIGHT:
            pygame.draw.rect(scene, sprites.PALETTE["n"], (round(x), round(y), 2, 2))
    if blast < EXPLOSION_WHITE:
        flash = pygame.Surface(scene.get_size(), pygame.SRCALPHA)
        flash.fill((255, 255, 255, 255 - blast * 255 // EXPLOSION_WHITE))  # the blast lights everything up
        scene.blit(flash, (0, 0))
    elif blast < EXPLOSION_WHITE + EXPLOSION_RED:
        fire = pygame.Surface(scene.get_size(), pygame.SRCALPHA)
        left = EXPLOSION_WHITE + EXPLOSION_RED - blast
        fire.fill((255, 40, 20, 200 * left // EXPLOSION_RED))  # then a red glare that dies away
        scene.blit(fire, (0, 0))


def draw_ending_screen(app, screen):
    ending_id = app["state"]["ending"]
    ending = story.ENDINGS[ending_id]
    font = app["fonts"]["text"]
    screen.fill(COLORS["good_ending"] if ending["good"] else COLORS["bad_ending"])
    # How long the ending has been on screen. Behind a question, show how it ends.
    time = app["scene_frames"] if app["scene"] == "ending" else 10 ** 6
    scene = pygame.Surface((WIDTH, ENDING_SCENE_HEIGHT))
    if ending["good"]:
        draw_rescue(app, scene, time)
        screen.blit(scene, (0, 0))
    else:
        draw_explosion(app, scene, time)
        shake = (0, 0)
        if EXPLOSION_DELAY <= time < EXPLOSION_DELAY + 45:
            shake = ((time * 7) % 5 - 2, (time * 3) % 5 - 2)  # the screen trembles
        screen.blit(scene, shake)
    pygame.draw.line(screen, COLORS["text"], (0, ENDING_SCENE_HEIGHT), (WIDTH, ENDING_SCENE_HEIGHT))
    number = list(story.ENDINGS).index(ending_id) + 1
    label = story.MESSAGES["ending_number"].format(number=number, total=len(story.ENDINGS))
    draw_text(screen, font, label, COLORS["dim_text"], (WIDTH // 2, ENDING_SCENE_HEIGHT + 6), "center")
    title_position = (WIDTH // 2, ENDING_SCENE_HEIGHT + 18)
    draw_text(screen, app["fonts"]["title"], ending["title"], COLORS["highlight"], title_position, "center", True)
    y = ENDING_SCENE_HEIGHT + 42
    for paragraph in ending["text"]:
        for line in wrap(paragraph, WIDTH - 24, text_width(font)):
            draw_text(screen, font, line, COLORS["text"], (WIDTH // 2, y), "center")
            y += font.get_linesize()


CHARACTER_ZOOM = 3   # the characters are shown three times bigger on the choice screen
CHARACTER_GAP = 72   # pixels between the middles of two characters


def draw_character_choice(app, screen):
    """The choice of the character, over the calm sea of the title: the characters side by side,
    the highlighted one in a frame that blinks."""
    draw_sea(app, screen, screen.get_rect(), calm=True)
    font = app["fonts"]["text"]
    title = story.MESSAGES["choose_character_p1" if app["two_players"] else "choose_character"]
    draw_text(screen, app["fonts"]["title"], title, COLORS["text"], (WIDTH // 2, 36), "center", True)
    entries = character_entries()
    first = WIDTH // 2 - (len(entries) - 1) * CHARACTER_GAP // 2
    for index, character in enumerate(entries):
        picture = sprites.image(story.CHARACTERS[character]["sprite"] + "_down_0")
        center = (first + index * CHARACTER_GAP, 118)
        frame = pygame.Rect(0, 0, 16 * CHARACTER_ZOOM + 12, 16 * CHARACTER_ZOOM + 12)
        frame.center = center
        pygame.draw.rect(screen, COLORS["box"], frame)
        chosen = index == app["menu_index"]
        border = COLORS["highlight"] if chosen and (app["frame"] // 24) % 2 == 0 else COLORS["dim_text"]
        pygame.draw.rect(screen, border, frame, 2 if chosen else 1)
        if picture is not None:
            big = pygame.transform.scale(picture, (picture.get_width() * CHARACTER_ZOOM, picture.get_height() * CHARACTER_ZOOM))
            screen.blit(big, big.get_rect(center=center))
    lines = wrap(story.MESSAGES["choose_hint"], WIDTH - 16, text_width(font))
    for index, line in enumerate(lines):
        y = HEIGHT - 6 - (len(lines) - index) * font.get_linesize()
        draw_text(screen, font, line, COLORS["foam"], (WIDTH // 2, y), "center", True)


def draw_mode_choice(app, screen):
    """The choice between one and two players, over the calm sea of the title."""
    draw_sea(app, screen, screen.get_rect(), calm=True)
    draw_text(screen, app["fonts"]["title"], story.MESSAGES["choose_mode"], COLORS["text"], (WIDTH // 2, 36),
              "center", True)
    draw_menu(app, screen, 100)


def draw_question(app, screen):
    font = app["fonts"]["text"]
    lines = wrap(app["question"], DIALOG_TEXT_WIDTH, text_width(font))
    line_height = font.get_linesize()
    height = (len(lines) + 3) * line_height + 2 * DIALOG_PADDING
    box = pygame.Rect(DIALOG_PADDING, (HEIGHT - height) // 2, WIDTH - 2 * DIALOG_PADDING, height)
    draw_box(screen, box)
    for index, line in enumerate(lines):
        draw_text(screen, font, line, COLORS["text"], (WIDTH // 2, box.top + DIALOG_PADDING + index * line_height), "center")
    draw_menu(app, screen, box.top + DIALOG_PADDING + (len(lines) + 1) * line_height)


def draw(app, screen):
    """Draw the current scene on the small screen."""
    scene = app["scene"]
    if scene == "menu":
        draw_title_screen(app, screen)
        draw_menu(app, screen, 128)
    elif scene == "play":
        draw_play_screen(app, screen)
        draw_banner(app, screen)
        draw_dialog(app, screen)
    elif scene == "actions":
        draw_play_screen(app, screen)
        draw_actions(app, screen)
    elif scene == "inventory":
        draw_play_screen(app, screen)
        dim(screen)
        draw_inventory(app, screen)
    elif scene == "pause":
        draw_play_screen(app, screen)
        dim(screen)
        box = pygame.Rect(WIDTH // 2 - 64, 60, 128, 92)
        draw_box(screen, box)
        draw_text(screen, app["fonts"]["text"], story.MESSAGES["pause"], COLORS["dim_text"], (WIDTH // 2, box.top + 9), "center")
        draw_menu(app, screen, box.top + 28)
    elif scene == "ending":
        draw_ending_screen(app, screen)
        draw_menu(app, screen, ENDING_MENU_TOP)
    elif scene == "character":
        draw_character_choice(app, screen)
    elif scene == "mode":
        draw_mode_choice(app, screen)
    elif scene == "confirm":
        back = app["confirm_back"]
        if back == "menu":
            draw_title_screen(app, screen)
        elif back == "ending":
            draw_ending_screen(app, screen)
        else:
            draw_play_screen(app, screen)
        dim(screen)
        draw_question(app, screen)


# --- The main loop -------------------------------------------------------------------


def main():
    pygame.init()
    sounds.load()  # silent if the computer has no audio
    window = pygame.display.set_mode((WIDTH * SCALE, HEIGHT * SCALE))
    pygame.display.set_caption(story.MESSAGES["title"])
    screen = pygame.Surface((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    app = new_app(load_fonts())
    while app["running"]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                app["running"] = False
            elif event.type == pygame.KEYDOWN:
                handle_key(app, event.key)
        pressed = pygame.key.get_pressed()
        directions = [held_direction(pressed, keys) for keys in controls(app)] + [(0, 0)]
        (dx, dy), (dx2, dy2) = directions[0], directions[1]
        update(app, dx, dy, dx2, dy2)
        draw(app, screen)
        pygame.transform.scale(screen, window.get_size(), window)  # plain scaling: sharp pixels
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    main()


