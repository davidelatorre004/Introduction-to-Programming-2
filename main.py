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

import collections
import math
import random

import pygame

import claw
import crab as crab_look
import effects
import engine
import net
import save
import scenery
import sounds
import sprites
import story
import weather
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
LIGHTNING_FRAMES = FPS     # the bolt that tears the screen when a new game starts: one second
STEAM_EVERY = 9            # frames between two puffs of steam from a pot on a stove
STEAM = [(196, 196, 208), (160, 162, 178), (220, 220, 228)]
DRIP_EVERY = 45            # frames between two drops from the ceiling of a damp room (on average)
ANVIL_SPARK_EVERY = 2      # frames between two red sparks around the anvil that waits for the key
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

# The keys of the player: to move, to act (E) and to open the inventory. In a game
# for two, each computer has its own keyboard, and the same keys.
KEYS_1P = [
    {"up": UP_KEYS, "down": DOWN_KEYS, "left": LEFT_KEYS, "right": RIGHT_KEYS,
     "act": (pygame.K_e,), "inventory": (pygame.K_i,)},
]

# The keys that type an address on the "Join game" screen.
ADDRESS_KEYS = {getattr(pygame, f"K_{digit}"): str(digit) for digit in range(10)}
ADDRESS_KEYS.update({getattr(pygame, f"K_KP{digit}"): str(digit) for digit in range(10)})
ADDRESS_KEYS.update({pygame.K_PERIOD: ".", pygame.K_KP_PERIOD: "."})
ADDRESS_LENGTH = 15  # "255.255.255.255"

NET_PORT = net.PORT  # where the host waits (the tests use any free port)
SYNC_EVERY = 1       # frames between two messages with where the players are

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
    "danger": (214, 64, 52),  # the time left to a player the crab has knocked down
    "help": (96, 200, 120),   # the help given to them
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
        elif thing["id"] == "deck_statue" and engine.statue_broken(state):
            solids.append(rubble_rect())  # only the base of the pile: the stones above it are behind
        elif thing["kind"] not in ("item", "tile") and not is_flat(thing["id"]):
            solids.append(thing_rect(thing["id"]))
    return solids


def rubble_rect():
    """What the broken statue blocks: the base of its pile of rubble, not its whole 2 x 2 tiles."""
    statue = thing_rect("deck_statue")
    return pygame.Rect(statue.left + RUBBLE_BASE[0], statue.top + RUBBLE_BASE[1], RUBBLE_BASE[2], RUBBLE_BASE[3])


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


def place_rect(thing):
    """Where a thing of engine.things_here() is: an item where it lies now (a player may have
    dropped it somewhere else), anything else where the story put it."""
    if "pos" in thing:
        return tile_rect(*thing["pos"])
    return thing_rect(thing["id"])


def item_rect(state, item):
    """The tile an item lies on when it is on the floor."""
    return tile_rect(*engine.item_place(state, item)[1])


def reach_rect(thing):
    """Where a thing is, to tell whether the player can reach it: its tile, or the opening of a door."""
    if thing in story.DOORS:
        return door_rect(thing)
    return thing_rect(thing)


def nearest_target(state, position, player=1):
    """The thing within reach of the player that is closest to them, or None.

    Only things E can act on count: not the numbered tiles (the feet act on them),
    nor plain decor or a portal that only receives. So a barrel next to the
    generator never gets in the way of the lever.
    """
    body = player_rect(position)
    reach = body.inflate(2 * REACH, 2 * REACH)
    nearest = None
    nearest_distance = 0
    for thing in engine.things_here(state, player):
        if thing["kind"] == "tile" or not engine.actions_for(state, thing["id"], player):
            continue
        rect = place_rect(thing) if thing["kind"] == "item" else reach_rect(thing["id"])
        if not reach.colliderect(rect):
            continue
        distance = (rect.centerx - body.centerx) ** 2 + (rect.centery - body.centery) ** 2
        if nearest is None or distance < nearest_distance:
            nearest = thing["id"]
            nearest_distance = distance
    return nearest


def target_and_actions(state, position, player=1):
    """What E would act on, and the actions it offers: the nearest thing, or else the room (which offers nothing).

    `player` is who presses E (1 or 2): what is near them, and the items they carry.
    """
    target = nearest_target(state, position, player)
    if target is None:
        target = engine.player_room(state, player)
    return target, engine.actions_for(state, target, player)


def target_name(target):
    """The name of a thing as the player sees it."""
    if target in story.ITEMS:
        return story.ITEMS[target]["name"]
    if target in story.OBJECTS:
        return story.OBJECTS[target]["name"]
    if target in story.DOORS:
        return story.MESSAGES["door"]
    if target == "partner":
        return story.MESSAGES["partner"]
    return story.ROOMS[target]["name"]


def prompt(state, position, player=1):
    """The hint at the top of the screen: what E does here. With several actions, the thing's name."""
    target, actions = target_and_actions(state, position, player)
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


def carried(state, player=1):
    """The items a player carries, in the order they were found. Alone: the whole inventory."""
    return [item for item in state["inventory"] if engine.carries(state, item, player)]


def item_lines(state, player=1):
    """The items a player carries, as (style, text) pairs: each name, then its description."""
    items = carried(state, player)
    if not items:
        return [("text", story.MESSAGES["inventory_empty"])]
    lines = []
    for item in items:
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
        "dash": 0,               # frames left of Flash's dash (see dash)
        "dash_way": (0, 0),      # ...the way it goes
    }


def new_app(fonts):
    """The state of the interface, starting on the main menu."""
    app = {
        "running": True,
        "fonts": fonts,
        "scene": "menu",         # "menu", "confirm", "mode", "difficulty", "character", "lobby", "join", "play", "actions",
                                 # "inventory", "pause" or "ending"
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
        "difficulty": "hard",    # how the crab of the new game for two hunts (story.DIFFICULTIES), until it starts
        "frame": 0,              # frames since the game started, for everything that moves on screen
        "scene_frames": 0,       # frames since the current scene started
        "fade": 0,               # frames left before the room is out of the dark
        "flash_frames": 0,       # frames left of the tiles blinking red after a mistake
        "fx": effects.new_fx(),  # the visual effects: particles, dissolves, the warp (see effects.py)
        "weather": weather.new_weather(),  # the storm that grows with the puzzles (see weather.py)
        "inventory_scroll": 0,   # how many rows the list of items is scrolled down
        "inventory_player": 1,   # whose items the inventory screen shows: who opened it
        "actor": 1,              # who pressed E last: the player the chosen action is for
        "me": 0,                 # which of app["players"] plays on this computer: 0, or 1 for the one who joined
        "net": None,             # the connection to the other computer, in a game for two (see start_network)
        "lobby": None,           # the host's game waiting for the other computer: (state, opening text)
        "join_text": "",         # the address typed on the "Join game" screen
        "join_error": "",        # why the last try to join failed
        "notice": "",            # a line on the title screen: why the last game for two ended
        "taken": None,           # choosing the characters of a game for two: the one the other player took, or None
        "picked": None,          # ...and the one this player took, or None while they are still choosing
        "crab": None,            # the crab of a game for two while it is awake (see new_crab), or None
        "downed": {},            # the players the crab has knocked down: number -> frames left before they are out
        "revive": {},            # the help given to each of them: number -> frames E has been held so far
        "lightning": 0,          # frames left of the bolt of lightning that opens a new game
        "crumble": 0,            # frames left of the crab statue shaking and crumbling (see start_crumble)
        "shatter": None,         # the giant claw breaking the screen, while it lasts (see start_shatter)
        "lightning_due": False,  # a new game has just started: the bolt strikes once the opening text is read
        "hidden": {},            # the players the crab cannot see (the ghost's ability): number -> frames left
        "afterimages": [],       # the yellow copies a dashing Flash leaves behind, while they fade (see dash)
        "beams": [],             # the rays of the wizard's spell, while they last (see start_beam)
        "petrify": None,         # the crab turning to stone where it stands, while it lasts (see crab_news)
        "own_ending": False,     # the ending came from this computer's player: they read its text first
        "steps": {},             # each player's last footstep heard: number -> step of their walk (see footsteps)
        "charging": False,       # the crab is charging the player on this computer (see crab_audio)
        "charge_at": -10 ** 6,   # the frame its charge was last heard
        "crab_trail": [],        # where the crab's burning eyes were in the last frames of a charge
        "act_held": False,       # E is held down on this keyboard (to help a player up)
        "partner_reviving": False,  # E is held down on the other computer, as it said
        "seen": {},              # what this computer has already told about the crab (see crab_news)
    }
    open_main_menu(app)
    reset_crab(app)
    prepare_rooms()
    return app


def room_backdrop(room, wave=0):
    """The floor and walls of a room with their details and depth (scenery.py), or None without pictures."""
    floor = sprites.image("floor_" + room)
    wall = sprites.image("wall_" + room + "_" + str(wave)) or sprites.image("wall_" + room)
    if floor is None or wall is None:
        return None
    info = story.ROOMS[room]
    columns, rows = room_size(room)
    key = (room, wave if info["outdoor"] else 0)
    return scenery.background(key, columns, rows, floor, wall, info["floor"], info["outdoor"], scenery.seed_of(room),
                              stained=info.get("damp", False))


def prepare_rooms():
    """Build the floor and walls of every room now (a third of a second, once), not when a player
    first walks in: entering a room never stutters."""
    if effects.FX["scenery"]:
        for room in story.ROOMS:
            for wave in range(SEA_PICTURES if story.ROOMS[room]["outdoor"] else 1):  # each picture of the sea
                room_backdrop(room, wave)


def set_scene(app, scene, menu_index=0):
    app["scene"] = scene
    app["menu_index"] = menu_index
    app["scene_frames"] = 0


def open_main_menu(app):
    """Show the main menu. "Resume" is offered only if the save file holds a valid game.

    A game for two ends here: the connection to the other computer closes.
    """
    end_network(app)
    app["me"] = 0
    app["taken"] = None
    app["picked"] = None
    app["crumble"] = 0     # no animation of the last game left running
    app["shatter"] = None
    app["players"] = [new_player()]
    app["state"] = None
    app["existing"] = engine.restore_state(save.load_game())
    app["dialog"] = []
    app["banner_frames"] = 0
    set_scene(app, "menu")


def menu_entries(app):
    """The entries of the menu showing in the current scene: ids, or the actions of the E menu."""
    scene = app["scene"]
    if scene == "menu":
        return engine.menu_options(app["existing"]) + ["join_game", "quit"]
    if scene == "pause":
        if app["net"] is not None:
            return ["continue", "main_menu", "quit"]  # a game for two cannot restart from one side
        return ["continue", "restart", "main_menu", "quit"]
    if scene == "confirm":
        return ["yes", "no"]
    if scene == "ending":
        if app["net"] is not None:
            return ["main_menu"]  # a new game for two starts from the main menu, hosted again
        return ["new_game", "main_menu"]
    if scene == "mode":
        return ["one_player", "two_players"]
    if scene == "difficulty":
        return list(story.DIFFICULTIES)
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
    elif entry == "join_game":
        open_join(app)
    elif entry == "one_player":
        app["two_players"] = False
        choose_character(app, "mode")  # Esc on the characters comes back to the mode
    elif entry == "two_players":
        app["two_players"] = True
        set_scene(app, "difficulty", menu_index=list(story.DIFFICULTIES).index("hard"))  # the crab of always
    elif entry in story.DIFFICULTIES:
        app["difficulty"] = entry
        host_new_game(app)


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
        if app["net"] is not None:
            open_main_menu(app)  # a game for two: the one who gives up leaves it (the host waits again)
        else:
            set_scene(app, app["character_back"])
    elif scene == "mode":
        set_scene(app, app["mode_back"])
    elif scene == "difficulty":
        set_scene(app, "mode", menu_index=1)
    elif scene == "lobby" or scene == "join":
        open_main_menu(app)


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
    """The characters on the choice screen, in order."""
    return list(story.CHARACTERS)


def move_character_choice(app, step):
    """Highlight the next character to the left (-1) or right (1), going round, and skipping the one taken."""
    entries = character_entries()
    index = app["menu_index"]
    for _ in entries:
        index = (index + step) % len(entries)
        if entries[index] != app["taken"]:
            break
    app["menu_index"] = index


def open_choice_for_two(app):
    """Both computers are connected: each player chooses their character on their own screen, at the same time."""
    app["taken"] = None
    app["picked"] = None
    set_scene(app, "character")


def take_character(app, taken):
    """The other player has taken a character (or None: not yet). This player cannot take it:
    if they had, the host refused theirs, and they choose again."""
    app["taken"] = taken
    if app["picked"] is not None and app["picked"] == taken:
        app["picked"] = None
    if app["picked"] is None and character_entries()[app["menu_index"]] == taken:
        move_character_choice(app, 1)


def pick_character_for_two(app, character):
    """This player takes a character in a game for two, unless the other one has it. The host checks
    and starts the game once both have chosen; the computer that joined asks the host."""
    if app["picked"] is not None or character == app["taken"]:
        return
    app["picked"] = character
    if is_host(app):
        send(app, {"t": "pick", "taken": character})
        start_when_both_chose(app)
    else:
        send(app, {"t": "picked", "character": character})


def start_when_both_chose(app):
    """The host: once both players have their character, the game for two starts."""
    if app["picked"] is None or app["taken"] is None or app["lobby"] is None:
        return
    state, opening_text = app["lobby"]
    chosen, outcome = engine.choose_characters(state, app["picked"], app["taken"])
    if outcome["ok"]:
        app["lobby"] = (chosen, opening_text)
        start_for_two(app)


def start_with_character(app, character):
    """Alone: the character is chosen, the new game replaces the progress and starts."""
    state, outcome = engine.start_new_game(progress(app), confirmed=True, character=character)
    begin_game(app, state, outcome["text"])


def host_new_game(app):
    """A new game for two, with the crab chosen: it replaces the progress, then waits for the other
    computer. The characters are chosen once both are there."""
    state, outcome = engine.start_new_game(progress(app), confirmed=True, two_players=True,
                                           difficulty=app["difficulty"])
    open_lobby(app, state, outcome["text"])


def begin_game(app, state, opening_text):
    """Play a game: put the players at the start, show the opening scene, save at once.

    Without an opening text (a game for two that is resumed) the room's name shows instead.
    """
    app["state"] = state
    app["dialog"] = []
    app["own_ending"] = False
    app["taken"] = None
    app["picked"] = None
    set_up_players(app)
    place_at_entry(app)
    reset_crab(app)
    app["fade"] = FADE_FRAMES
    app["lightning"] = 0
    app["lightning_due"] = bool(opening_text)  # a new game, not one that is resumed
    if opening_text:
        say(app, opening_text)
    else:
        show_banner(app, story.ROOMS[engine.player_room(state, my_number(app))]["name"])
    save_progress(app)
    set_scene(app, "play")


def resume_game(app):
    """Go back to the saved game: to its ending if it is over, otherwise to the entry of its room."""
    app["state"] = app["existing"]
    app["dialog"] = []
    if engine.is_over(app["state"]):
        set_scene(app, "ending")
        return
    if app["state"]["flags"]["two_players"]:
        open_lobby(app, app["state"], None)  # a game for two goes on when the other computer joins
        return
    set_up_players(app)
    place_at_entry(app)
    app["fade"] = FADE_FRAMES
    show_banner(app, story.ROOMS[app["state"]["room"]]["name"])
    set_scene(app, "play")


def save_progress(app):
    """Save the game after an accepted action. If the disk refuses, tell the player instead of crashing.

    In a game for two only the host saves: the game is kept on its computer.
    """
    if app["net"] is not None and app["net"]["role"] == "client":
        return
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


def my_number(app):
    """The number of the player on this computer: 1, or 2 for the one who joined a game for two."""
    return app["me"] + 1


def local_player(app):
    """The player on this computer, moved by its keyboard."""
    return app["players"][app["me"]]


def eye_number(app):
    """Whose room this computer shows: its own player's, or the partner's once its player is out of the game."""
    number = my_number(app)
    if app["state"] is not None and engine.is_out(app["state"], number):
        return 3 - number
    return number


def view(app):
    """The game as the player on this computer sees it: their room is "room" (see engine.seen_by).

    Alone, or on the host, it is the game itself. A player out of the game watches the other one.
    """
    return engine.seen_by(app["state"], eye_number(app))


def same_room(app, player):
    """True if `player` is in the room this computer shows."""
    number = player_number(app, player)
    return engine.player_room(app["state"], number) == engine.player_room(app["state"], eye_number(app))


def is_playing(app, player):
    """True for a player still in the game and on their feet."""
    number = player_number(app, player)
    return not engine.is_out(app["state"], number) and number not in app["downed"]


def place_at_entry(app):
    """Put each player at the entry of their room; player 2 next to player 1 if they share it."""
    state = app["state"]
    first = app["players"][0]
    first["pos"] = spawn_at_entry(state["room"])
    for number, player in enumerate(app["players"], start=1):
        room = engine.player_room(state, number)
        if number > 1:
            if room == state["room"]:
                player["pos"] = beside(state, first["pos"])
            else:
                player["pos"] = spawn_at_entry(room)
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
    """Put the player on this computer in front of the door that leads back where they came from."""
    seen = view(app)
    door = return_door(seen["room"], came_from)
    player = local_player(app)
    player["pos"] = spawn_at_entry(seen["room"]) if door is None else spawn_in_front_of(door)
    player["touching"] = None
    settle_on_floor(app, player)


def settle_on_floor(app, player):
    """Appearing somewhere is not walking there: where the player appears fires no movement trigger."""
    seen = engine.seen_by(app["state"], player_number(app, player))
    player["on_tile"] = tile_under(seen, player["pos"])
    player["zones"] = zones_around(seen, player["pos"])


# --- Asking the engine: here, or the host --------------------------------------------------


def request(app, action, finish):
    """Ask the engine to do an action for the player on this computer, then call
    finish(app, action, before, state, outcome) with the result.

    Alone, and on the host, it happens at once. On the computer that joined, the
    host does it (the game is kept in one place only) and the answer comes back a
    moment later, with the new state.
    """
    before = app["state"]
    connection = app["net"]
    if connection is not None and connection["role"] == "client":
        connection["next_id"] += 1
        connection["pending"][connection["next_id"]] = (action, before, finish)
        send(app, {"t": "do", "id": connection["next_id"], "action": action})
        return
    state, outcome = engine.perform(before, action, my_number(app))
    finish(app, action, before, state, outcome)


def go_through(app, door):
    """The player walks into a door: ask the engine, then change room or explain why not."""
    request(app, {"verb": "enter", "target": door, "item": None}, finish_door)


def finish_door(app, action, before, state, outcome):
    if not outcome["ok"]:
        if outcome["event"] in ("locked", "barred", "sealed"):
            sounds.play("locked")  # a thud on the wood, and the bars or the lock rattle
        say(app, outcome["text"])
        return
    came_from = engine.player_room(before, my_number(app))
    app["state"] = state
    save_progress(app)
    place_after_door(app, came_from)
    app["fade"] = FADE_FRAMES
    show_banner(app, outcome["text"])


def go_through_portal(app, portal):
    """The player steps into a portal: the engine moves them, and they appear by the twin portal."""
    request(app, {"verb": "travel", "target": portal, "item": None}, finish_portal)


def finish_portal(app, action, before, state, outcome):
    if not outcome["ok"]:
        return
    sounds.play(EVENT_SOUNDS.get(outcome["event"]))
    app["state"] = state
    save_progress(app)
    player = local_player(app)
    player["pos"] = spawn_by_portal(story.OBJECTS[action["target"]]["to"])
    player["touching"] = None
    settle_on_floor(app, player)
    if effects.FX["portals"]:
        app["fx"]["warp"] = effects.WARP_FRAMES  # a purple warp instead of the dark fade
    else:
        app["fade"] = FADE_FRAMES
    show_banner(app, story.ROOMS[engine.player_room(state, my_number(app))]["name"])


def floor_triggers(app, player):
    """The movement triggers of the room, checked in every frame after the player moves.

    Walking onto a numbered tile steps on it, whoever walks there. Walking out of
    the zone around the tiles leaves it, but only when no player is left in it.
    Each one fires once, when it happens: standing still on a tile does not step on
    it again. The engine decides what it means.
    """
    state = view(app)
    tile = tile_under(state, player["pos"])
    zones = zones_around(state, player["pos"])
    stepped_on = tile if tile is not None and tile != player["on_tile"] else None
    # The zones of all the players in the room together: a zone is left only when nobody is in it any more.
    others = set()
    for other in app["players"]:
        if other is not player and same_room(app, other) and not engine.is_out(app["state"], player_number(app, other)):
            others |= zones_around(state, other["pos"])
    left = sorted(player["zones"] - zones - others)
    player["on_tile"] = tile
    player["zones"] = zones
    for puzzle in left:
        floor_action(app, {"verb": "leave_zone", "target": puzzle, "item": None})
    if stepped_on is not None:
        floor_action(app, {"verb": "step_on", "target": stepped_on, "item": None})


def floor_action(app, action, player=None):
    """Tell the engine what the player's feet did, then play and show what happens, without stopping them."""
    request(app, action, finish_floor)


def finish_floor(app, action, before, state, outcome):
    """Refusals stay silent: walking around is not a request. The other outcomes
    play their sound and show in the banner, except the solved puzzle, which
    opens the text box. A mistake also makes the tiles blink red."""
    if not outcome["ok"]:
        return
    sounds.play(EVENT_SOUNDS.get(outcome["event"]))
    show_outcome(app, action, before, state, outcome)
    if outcome["event"] == "tiles_reset":
        app["flash_frames"] = FLASH_FRAMES
    if outcome["event"] == "tiles_complete":
        app["banner_frames"] = 0
        say(app, outcome["text"])
    else:
        show_banner(app, outcome["text"])
    app["state"] = state
    save_progress(app)


def player_number(app, player):
    """1 for the first player, 2 for the second."""
    return app["players"].index(player) + 1


def partner_near(app, player):
    """The other player, if they are in the same room and within reach of `player`, or None."""
    reach = player_rect(player["pos"]).inflate(2 * REACH, 2 * REACH)
    for other in app["players"]:
        if other is not player and same_room(app, other) and reach.colliderect(player_rect(other["pos"])) \
                and is_playing(app, other):
            return other
    return None


def give_actions(app, player):
    """Next to the partner, E offers to hand them each item the player carries."""
    if partner_near(app, player) is None:
        return []
    number = player_number(app, player)
    actions = []
    for item in carried(app["state"], number):
        label = story.MESSAGES["label_hand"].format(item=story.ITEMS[item]["name"])
        actions.append({"verb": "give", "target": "partner", "item": item, "label": label, "irreversible": False})
    return actions


def interact(app, player=None):
    """E: act on the thing nearest to the player on this computer. Several possible actions
    open a small menu. Next to the partner, it also offers to give them items."""
    player = player or local_player(app)
    app["actor"] = player_number(app, player)
    target, actions = target_and_actions(app["state"], player["pos"], app["actor"])
    gifts = give_actions(app, player)
    if gifts:
        if not actions:
            target = "partner"
        actions = actions + gifts
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
    request(app, action, finish_action)


def finish_action(app, action, before, state, outcome):
    sounds.play(EVENT_SOUNDS.get(outcome["event"]))
    if outcome["event"] == "toggled":
        show_banner(app, outcome["text"])  # a generator clicks: no text box to close every time
    else:
        app["banner_frames"] = 0  # the text box takes over from an older banner
        say(app, outcome["text"])
    if outcome["ok"]:
        show_outcome(app, action, before, state, outcome)
        app["state"] = state
        app["own_ending"] = engine.is_over(state)  # this player reads the ending's text, then sees it
        save_progress(app)
        if is_host(app):
            heart_helps(app, outcome, my_number(app))


def drop_item(app):
    """Q: the player on this computer drops the item they got last, on the floor where they stand."""
    if not can_move(app):
        return
    tile = tile_of(local_player(app)["pos"])
    request(app, {"verb": "drop", "target": None, "item": None, "at": list(tile)}, finish_drop)


def finish_drop(app, action, before, state, outcome):
    """With empty hands nothing happens, silently."""
    if not outcome["ok"]:
        return
    app["state"] = state
    save_progress(app)
    sounds.play("drop")
    show_banner(app, outcome["text"])


def handle_key(app, key):
    """React to one key press."""
    scene = app["scene"]
    app["notice"] = ""  # the line about the last game for two goes away at the first key
    if scene == "shatter":
        return  # the claw is breaking the screen: no key does anything until it is over
    if scene == "play":
        handle_play_key(app, key)
    elif scene == "inventory":
        if key in inventory_keys(app) or key == pygame.K_ESCAPE or key in confirm_keys(app):
            set_scene(app, "play")
        elif key in UP_KEYS or key in DOWN_KEYS:
            scroll_inventory(app, -1 if key in UP_KEYS else 1)
    elif scene == "character":
        handle_character_key(app, key)
    elif scene == "join":
        handle_join_key(app, key)
    elif scene == "lobby":
        if key == pygame.K_ESCAPE:
            go_back(app)
    else:
        handle_menu_key(app, key)


def controls(app):
    """The keys of the player on this computer."""
    return KEYS_1P


def confirm_keys(app):
    """The keys that choose in a menu or turn the page of the text box."""
    return CONFIRM_KEYS


def inventory_keys(app):
    """The keys that open and close the inventory."""
    return KEYS_1P[0]["inventory"]


def handle_character_key(app, key):
    """Keys on the choice of the character: left and right to move, E or Enter to choose, Esc to go back."""
    entries = character_entries()
    if key in LEFT_KEYS and app["picked"] is None:
        move_character_choice(app, -1)
    elif key in RIGHT_KEYS and app["picked"] is None:
        move_character_choice(app, 1)
    elif key == pygame.K_ESCAPE:
        go_back(app)
    elif app["picked"] is not None:
        return  # chosen: waiting for the other player
    elif key in confirm_keys(app) and app["net"] is not None:
        pick_character_for_two(app, entries[app["menu_index"]])
    elif key in confirm_keys(app):
        start_with_character(app, entries[app["menu_index"]])


def handle_join_key(app, key):
    """Keys on the "Join game" screen: digits and dots type the address, Enter joins, Esc goes back."""
    if key in ADDRESS_KEYS and len(app["join_text"]) < ADDRESS_LENGTH:
        app["join_text"] += ADDRESS_KEYS[key]
        app["join_error"] = ""
    elif key == pygame.K_BACKSPACE:
        app["join_text"] = app["join_text"][:-1]
        app["join_error"] = ""
    elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        join(app, app["join_text"])
    elif key == pygame.K_ESCAPE:
        go_back(app)


def handle_play_key(app, key):
    """Keys while playing: E acts (or turns the page of the text box), I opens the inventory, Esc pauses.

    In a game for two the pause menu is only on this screen: the game goes on.
    """
    if key == pygame.K_ESCAPE:
        set_scene(app, "pause")
    elif app["dialog"]:
        if key in confirm_keys(app):
            app["dialog"].pop(0)
        return
    keys = controls(app)[0]
    player = local_player(app)
    if key in keys["act"]:
        if can_move(app) and downed_near(app, player) is None:  # next to a player down, E is held to help
            interact(app, player)
    elif key == pygame.K_SPACE:
        use_ability(app)
    elif key == pygame.K_q:
        drop_item(app)
    elif key in keys["inventory"]:
        app["inventory_scroll"] = 0  # the list of items always opens at the top
        app["inventory_player"] = my_number(app)
        set_scene(app, "inventory")


def handle_menu_key(app, key):
    """Keys in a menu: up and down to move, E or Enter to choose, Esc to go back.
    The two frames of the choice of the crab are side by side: left and right move too."""
    entries = menu_entries(app)
    if app["scene"] == "difficulty" and key in LEFT_KEYS + RIGHT_KEYS:
        key = UP_KEYS[0] if key in LEFT_KEYS else DOWN_KEYS[0]
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

    `keys` is the set of keys of that player (see KEYS_1P): alone, the
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


def update(app, dx, dy, act=False):
    """Move the game on by one frame. (dx, dy) is the direction held on this computer's keyboard,
    and `act` is True while E is held down (to help a player the crab has knocked down).

    In a game for two the crab moves on the host, whatever scene is on screen: the game never pauses.
    """
    app["frame"] += 1
    app["scene_frames"] += 1
    app["act_held"] = act and app["scene"] == "play" and not app["dialog"]
    pump_network(app)
    if is_host(app):
        update_crab(app)
    crab_news(app)
    ability_news(app)
    update_ability_effects(app)
    update_crumble(app)
    update_effects(app)
    update_weather(app)
    update_audio(app)
    update_crab_looks(app)
    if app["scene"] == "shatter":
        update_shatter(app)  # nothing else happens while the claw breaks the screen
        return
    for player in app["players"]:
        if player is local_player(app):
            player["moving"] = False
    if app["banner_frames"] > 0:
        app["banner_frames"] -= 1
    if app["fade"] > 0:
        app["fade"] -= 1
    if app["flash_frames"] > 0:
        app["flash_frames"] -= 1
    if partner_ended(app):
        app["dialog"] = []  # the other player has just reached an ending: here too, whatever is on screen
        set_scene(app, "ending")
        return
    if app["scene"] != "play" or app["dialog"]:
        return
    if engine.is_over(app["state"]):
        set_scene(app, "ending")  # the last text has been read: on to the ending
        return
    if app["lightning_due"]:
        app["lightning_due"] = False  # the opening text is read: a bolt tears the screen, then the game is on
        app["lightning"] = LIGHTNING_FRAMES
        if LIGHTNING_FRAMES > 0:
            sounds.play("thunder")
    if app["lightning"] > 0:
        app["lightning"] -= 1
        return  # nobody moves while it strikes
    if not can_move(app):
        return  # down, or out of the game
    if local_player(app)["dash"] > 0:
        dash_step(app)  # dashing: the keys wait
        return
    move_player(app, local_player(app), dx, dy)


def partner_ended(app):
    """True on one computer of a game for two when the other player has just reached an ending
    (not the crab's: both see the claw first), and this screen is not showing it yet."""
    state = app["state"]
    return (app["net"] is not None and state is not None and engine.is_over(state) and state["ending"] != "caught"
            and not app["own_ending"] and app["scene"] not in ("ending", "shatter"))


def move_player(app, player, dx, dy):
    """The frame of the player on this computer: walk, go through a door, step on the tiles,
    walk into a portal. Each player goes through doors and portals on their own."""
    if dy != 0:
        player["facing"] = (0, dy)
    elif dx != 0:
        player["facing"] = (dx, 0)
    speed = PLAYER_SPEED
    if dx != 0 and dy != 0:
        speed = PLAYER_SPEED * 0.7071  # the same speed on diagonals
    before = player["pos"]
    seen = view(app)
    player["pos"] = move(player["pos"], dx * speed, dy * speed, solid_rects(seen))
    if player["pos"] != before:
        player["moving"] = True
        player["walk"] += 1
    door = door_touched(seen["room"], player["pos"], dx, dy)
    if door is None:
        player["touching"] = None
    elif door != player["touching"]:
        player["touching"] = door
        go_through(app, door)
    floor_triggers(app, player)
    portal = portal_touched(view(app), player["pos"])
    if portal is not None:
        go_through_portal(app, portal)


# --- The crab: in a game for two, the statue of the deck hunts the players ------------------
#
# It wakes when the cabin is solved and turns back to stone once the key is fused
# (engine.crab_awake). It walks toward the nearest player in its room, slower than
# the players, and through the open doors toward them when nobody is in its room.
# A player it touches goes down: the other one has a minute to help them up, by
# holding E next to them for five seconds; otherwise they are out of the game
# (engine.knock_out). Once it has caught everyone still in the game, nobody is left
# to help: the game ends, the third ending (engine.crab_catches_everyone).
#
# The host moves the crab and keeps the timers; the computer that joined only draws
# what the host sends. Nothing of this is saved, only who is out of the game.
#
# The host also chooses how the crab hunts (engine.crab_difficulty). Hard is the crab
# described above: it always knows where everyone is and takes the shortest way.
# Easy is a crab like the ghosts of an arcade maze (move_easy_crab): it walks from the
# middle of one tile to the middle of the next, decides only there, never turns back
# unless the way ends, and picks the way whose next tile is nearest to its target in a
# straight line, which can take it the long way round. It only sees its own room: with
# nobody there it roams, heading for a door of the room taken at random (not the one
# toward the players: it does not know where they are), and looks in the next room.
# Now and then it gives up the chase and goes to its corner of the room for a while.

CRAB_SPEED = PLAYER_SPEED * 0.6    # pixels per frame: slower than the players
CRAB_LEG_FRAMES = 5                # frames each of the 4 pictures of its walk lasts
CRAB_CLAW_RHYTHM = (0.0, 0.25, 0.5, 0.25)  # how open its claws are as it chases, one after the other...
CRAB_CLAW_BEAT = 7                 # ...each for this many frames
CRAB_BREATH_FRAMES = 70            # standing still, it breathes in and out in this many frames
CRAB_SHADOW = (28, 8)              # the wide oval under it, on the floor
CRAB_DUST_EVERY = 6                # frames between two puffs from its legs as it runs
CRAB_DUST = [(190, 166, 130), (150, 130, 104), (214, 198, 170)]   # dust, on a dry floor
CRAB_FOAM = [(236, 244, 248), (196, 220, 236), (160, 196, 218)]   # foam, on a wet one
CRAB_EYE_GLOW = (90, 20, 8)        # the red glow of its eyes when it hunts
CRAB_TRAIL_FRAMES = 6              # how long the red streaks of its eyes stay behind when it charges
CRAB_WAKE_FRAMES = 3 * FPS         # still for a moment after waking: time to understand and run
CRAB_TRANSIT_FRAMES = FPS          # between two rooms, out of sight
CRAB_ARRIVE_FRAMES = FPS // 2      # still for a moment after coming through a door
CRAB_CATCH_FRAMES = 2 * FPS        # still for a moment after catching someone
DOWN_FRAMES = 60 * FPS             # how long a player can stay down before they are out
REVIVE_FRAMES = 4 * FPS            # how long E must be held next to a player down to help them up
NURSE_REVIVE_FRAMES = FPS          # ...and how long when the nurse helps: her ability, always on
STUN_FRAMES = 5 * FPS              # how long the wizard's spell keeps the crab still
HIDDEN_FRAMES = 5 * FPS            # how long the ghost stays out of the crab's sight
DASH_TILES = 8                     # how far Flash dashes
DASH_FRAMES = 8                    # how long the dash lasts: 16 pixels a frame, ten times a walk
DASH_STEP = 4                      # pixels at a time, so the dash stops at walls and finds doors
AFTERIMAGE_FRAMES = 12             # how long each yellow afterimage of a dashing Flash takes to fade
DASH_SPARKS = [(255, 236, 120), (255, 200, 60), (255, 255, 220)]
BEAM_FRAMES = 36                   # how long the ray of the wizard's spell stays on screen
BEAM_REACH = 8 * TILE              # how far it goes when the crab is not in the room
BEAM_COLORS = [(170, 100, 255), (120, 210, 255), (255, 255, 255)]  # its glow, its sparks, its core
PETRIFY_FRAMES = 96                # the crab turning to stone: grey, cracked, then dust
PETRIFY_CRACK = 48                 # the frame its stone cracks
PETRIFY_BURST = 78                 # the frame it bursts into dust
RUBBLE_BASE = (2, 18, 30, 13)      # the base of the pile of rubble, inside the statue's 2 x 2 tiles: what is solid


EASY_CHASE_FRAMES = 20 * FPS      # the easy crab chases this long...
EASY_SCATTER_FRAMES = 7 * FPS      # ...then goes to its corner this long, and so on
HEADINGS = [(0, -1), (-1, 0), (0, 1), (1, 0)]  # the ways the easy crab can go, in the order it prefers on a tie
EASY_ROAM_FRAMES = 20 * FPS        # roaming, the easy crab gives up a door it has not reached in this time


RUBBLE_COLORS = [(232, 226, 210), (190, 184, 168), (96, 96, 112)]  # the marble of the statue, in pieces


def new_crab():
    """The crab just awake: in front of its statue on the deck, still for a moment."""
    statue = thing_rect("deck_statue")
    body = pygame.Rect(0, 0, PLAYER_SIZE, PLAYER_SIZE)
    body.midtop = (statue.centerx, statue.bottom + 2)
    return {"room": "deck", "pos": (body.x, body.y), "facing": (0, 1), "moving": False, "walk": 0,
            "wait": CRAB_WAKE_FRAMES, "away": 0, "stun": 0,
            # Only for the easy crab: the way it goes, the tile it walks to, chasing or going to its
            # corner and for how long, the door it roams to when it sees nobody and for how long,
            # and how many doors it has taken at random.
            "heading": (0, 1), "next": None, "mode": "chase", "clock": 0,
            "roam": None, "roam_clock": 0, "turns": 0}


def is_host(app):
    """True on the computer that keeps the game: alone, or the host of a game for two."""
    return app["net"] is None or app["net"]["role"] == "host"


def room_state(state, room):
    """The game, with `room` as the current room: to look at a room nobody may be in. Read only."""
    return dict(state, room=room)


def active_players(app):
    """The numbers of the players the crab can catch: in the game, and not down."""
    state = app["state"]
    return [number for number in range(1, len(app["players"]) + 1)
            if not engine.is_out(state, number) and number not in app["downed"]]


def hunted_players(app):
    """The players the crab can see and catch: on their feet, and not hidden by the ghost's ability."""
    return [number for number in active_players(app) if number not in app["hidden"]]


def revive_frames(app, helper):
    """How long player `helper` must hold E to help the other one up: less for the nurse."""
    if engine.character_of(app["state"], helper) == "nurse":
        return NURSE_REVIVE_FRAMES
    return REVIVE_FRAMES


def crab_rect(crab):
    return player_rect(crab["pos"])


def free_tiles(state, room):
    """The tiles of a room the crab can walk on: the floor that nothing solid covers, and the open doors."""
    seen = room_state(state, room)
    solids = solid_rects(seen)
    columns, rows = room_size(room)
    free = set()
    for col in range(columns):
        for row in range(rows):
            if tile_rect(col, row).collidelist(solids) == -1:
                free.add((col, row))
    return free


def tile_of(position):
    """The tile of the room grid under the middle of a body (see tile_rect: the rooms start below the bar)."""
    x, y = player_rect(position).center
    return (x // TILE, (y - HUD_HEIGHT) // TILE)


def next_tile(free, start, goals):
    """The first tile to walk to on the shortest way from `start` to any of `goals`, or None.

    A plain search over the free tiles, in the four directions: rooms are small.
    """
    goals = set(goals)
    if start in goals:
        return start
    first = {start: None}
    queue = collections.deque([start])
    while queue:
        tile = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            near = (tile[0] + dx, tile[1] + dy)
            if near in free and near not in first:
                first[near] = near if tile == start else first[tile]
                if near in goals:
                    return first[near]
                queue.append(near)
    return None


def door_toward(state, room, rooms):
    """The open door of `room` on the shortest way (in rooms) to any of `rooms`, or None."""
    first = {room: None}
    queue = collections.deque([room])
    while queue:
        here = queue.popleft()
        if here in rooms and here != room:
            return first[here]
        for door in doors_in(here):
            there = story.DOORS[door]["to"]
            if there not in first and engine.door_status(state, door) == "open":
                first[there] = door if here == room else first[here]
                queue.append(there)
    return None


def crab_target(app):
    """Where the crab heads now: ("player", number) for a player in its room, ("door", id),
    ("flee", number) away from a hidden player when there is nobody else to hunt, or None."""
    crab = app["crab"]
    state = app["state"]
    hunted = hunted_players(app)
    if not hunted:
        for number in app["hidden"]:
            if number in active_players(app) and engine.player_room(state, number) == crab["room"]:
                return ("flee", number)  # it cannot see them, and it is afraid: as far as the room allows
        return None
    here = [number for number in hunted if engine.player_room(state, number) == crab["room"]]
    if here:
        center = pygame.Vector2(crab_rect(crab).center)
        nearest = min(here, key=lambda number: center.distance_to(player_rect(app["players"][number - 1]["pos"]).center))
        return ("player", nearest)
    door = door_toward(state, crab["room"], {engine.player_room(state, number) for number in hunted})
    return None if door is None else ("door", door)


def step_crab(crab, goal, solids, speed=CRAB_SPEED):
    """Move the crab one frame toward the middle of `goal` (a point in room pixels)."""
    x, y = crab_rect(crab).center
    dx, dy = goal[0] - x, goal[1] - y
    distance = math.hypot(dx, dy)
    if distance < 1:
        crab["moving"] = False
        return
    step = min(speed, distance)
    move_x = step * dx / distance
    move_y = step * dy / distance
    before = crab["pos"]
    crab["pos"] = move(crab["pos"], move_x, move_y, solids)
    crab["moving"] = crab["pos"] != before
    if crab["moving"]:
        crab["walk"] += 1
        crab["facing"] = (sign(dx), 0) if abs(dx) >= abs(dy) else (0, sign(dy))


def move_crab(app):
    """One frame of the crab: toward its target, through a door if that is the way."""
    if engine.crab_difficulty(app["state"]) == "easy":
        move_easy_crab(app)
        return
    crab = app["crab"]
    state = app["state"]
    crab["moving"] = False
    target = crab_target(app)
    if target is None:
        return  # nobody it can reach: it waits
    seen = room_state(state, crab["room"])
    free = free_tiles(state, crab["room"])
    start = tile_of(crab["pos"])
    if target[0] == "player":
        body = player_rect(app["players"][target[1] - 1]["pos"])
        goal_tile = tile_of(app["players"][target[1] - 1]["pos"])
        if goal_tile == start or goal_tile not in free:
            step_crab(crab, body.center, solid_rects(seen))
            return
        goals = [goal_tile]
    elif target[0] == "flee":
        goals = [farthest_tile(free, start, player_rect(app["players"][target[1] - 1]["pos"]).center, crab["room"])]
    else:
        door = target[1]
        if crab_rect(crab).colliderect(door_rect(door).inflate(2, 2)):
            go_through_crab(crab, door)
            return
        col, row, width, height = door_tiles(door)
        goals = [(col + dx, row + dy) for dx in range(width) for dy in range(height)]
    tile = next_tile(free, start, goals)
    if tile is None:
        return
    goal = tile_rect(*tile).center
    if tile == start and target[0] == "door":
        goal = door_rect(target[1]).center
    step_crab(crab, goal, solid_rects(seen))


def open_door_tiles(state, room):
    """The tiles of the open doors of a room: tile -> door."""
    tiles = {}
    for door in doors_in(room):
        if engine.door_status(state, door) == "open":
            col, row, width, height = door_tiles(door)
            for dx in range(width):
                for dy in range(height):
                    tiles[(col + dx, row + dy)] = door
    return tiles


def scatter_corner(room):
    """The easy crab's corner of a room, where it goes when it gives up the chase: the top right."""
    columns, _ = room_size(room)
    return (columns - 2, 1)


def easy_target(app):
    """What the easy crab heads for now: ("chase", tile) the nearest player it sees in its room,
    ("scatter", tile) its corner, ("flee", point) away from a hidden player, or ("roam", tile) the
    middle of the door it has taken at random, when it sees nobody."""
    crab = app["crab"]
    state = app["state"]
    here = [number for number in hunted_players(app) if engine.player_room(state, number) == crab["room"]]
    if not here:
        for number in app["hidden"]:
            if number in active_players(app) and engine.player_room(state, number) == crab["room"]:
                return ("flee", player_rect(app["players"][number - 1]["pos"]).center)
        door = roam_door(app)  # it cannot see anyone: it does not know where they are
        if door is None:
            return ("wait", None)
        col, row, _, _ = door_tiles(door)
        return ("roam", (col, row))
    if crab["mode"] == "scatter":
        return ("scatter", scatter_corner(crab["room"]))
    center = pygame.Vector2(crab_rect(crab).center)
    nearest = min(here, key=lambda number: center.distance_to(player_rect(app["players"][number - 1]["pos"]).center))
    return ("chase", tile_of(app["players"][nearest - 1]["pos"]))


def roam_door(app):
    """The door the easy crab roams to when it sees nobody: one of the open doors of its room, taken at
    random (better not the one it came in by), and another one if it has not got there in a while."""
    crab = app["crab"]
    open_doors = sorted(set(open_door_tiles(app["state"], crab["room"]).values()))
    if crab["roam"] in open_doors and crab["roam_clock"] < EASY_ROAM_FRAMES:
        return crab["roam"]
    if not open_doors:
        crab["roam"] = None
        return None
    choices = [door for door in open_doors if door != crab["roam"]] or open_doors
    crab["turns"] += 1
    crab["roam"] = choices[int(scenery.hash01(len(crab["room"]), crab["turns"], 11) * len(choices)) % len(choices)]
    crab["roam_clock"] = 0
    return crab["roam"]


def easy_heading(app, tile, free, doors):
    """Where the easy crab goes from the middle of `tile`: never back unless the way ends there;
    toward its target in a straight line (or away from it), through a door only the one it roams to."""
    crab = app["crab"]
    target = easy_target(app)
    if target[0] == "wait":
        return None
    through = crab["roam"] if target[0] == "roam" else None  # otherwise it keeps its prey in sight
    ways = [way for way in HEADINGS if (tile[0] + way[0], tile[1] + way[1]) in free
            and doors.get((tile[0] + way[0], tile[1] + way[1])) in (None, through)]
    back = (-crab["heading"][0], -crab["heading"][1])
    ways = [way for way in ways if way != back] or ways
    if not ways:
        return None

    def distance(way):
        middle = pygame.Vector2(tile_rect(tile[0] + way[0], tile[1] + way[1]).center)
        if target[0] == "flee":
            return -middle.distance_to(target[1])
        return middle.distance_to(tile_rect(*target[1]).center)
    return min(ways, key=distance)  # on a tie, the first of HEADINGS


def move_easy_crab(app):
    """One frame of the easy crab: to the middle of the next tile; there, it decides where to go next."""
    crab = app["crab"]
    state = app["state"]
    crab["moving"] = False
    crab["clock"] += 1
    crab["roam_clock"] += 1
    if crab["clock"] >= (EASY_CHASE_FRAMES if crab["mode"] == "chase" else EASY_SCATTER_FRAMES):
        crab["mode"] = "scatter" if crab["mode"] == "chase" else "chase"
        crab["clock"] = 0
    free = free_tiles(state, crab["room"])
    doors = open_door_tiles(state, crab["room"])
    solids = solid_rects(room_state(state, crab["room"]))
    if crab["next"] is None or tuple(crab["next"]) not in free:
        crab["next"] = tile_of(crab["pos"])  # first to the middle of the tile it is on
    tile = tuple(crab["next"])
    goal = tile_rect(*tile).center
    body = crab_rect(crab)
    if math.hypot(goal[0] - body.centerx, goal[1] - body.centery) > CRAB_SPEED:
        step_crab(crab, goal, solids)
        if not crab["moving"]:
            crab["next"] = None  # something in the way: it starts again from where it is
        return
    crab["pos"] = (crab["pos"][0] + goal[0] - body.centerx, crab["pos"][1] + goal[1] - body.centery)
    if tile in doors:
        door = doors[tile]
        go_through_crab(crab, door)
        back = return_door(story.DOORS[door]["to"], story.DOORS[door]["room"])
        if back is not None:
            away = TOWARD[story.DOORS[back]["side"]]
            crab["heading"] = (-away[0], -away[1])  # into the new room
        crab["next"] = None
        crab["roam"] = back  # in the new room it takes another door, better not the way back
        crab["roam_clock"] = EASY_ROAM_FRAMES
        return
    heading = easy_heading(app, tile, free, doors)
    if heading is None:
        return
    crab["heading"] = heading
    crab["next"] = (tile[0] + heading[0], tile[1] + heading[1])
    step_crab(crab, tile_rect(*crab["next"]).center, solids)


def farthest_tile(free, start, point, room):
    """The floor tile the crab can walk to that is farthest from `point` (room pixels)."""
    columns, rows = room_size(room)
    seen = {start}
    queue = collections.deque([start])
    while queue:
        tile = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            near = (tile[0] + dx, tile[1] + dy)
            if near in free and near not in seen and 1 <= near[0] <= columns - 2 and 1 <= near[1] <= rows - 2:
                seen.add(near)
                queue.append(near)
    return max(sorted(seen), key=lambda tile: pygame.Vector2(tile_rect(*tile).center).distance_to(point))


def go_through_crab(crab, door):
    """The crab leaves through a door: out of sight for a moment, then in front of the door back."""
    info = story.DOORS[door]
    back = return_door(info["to"], info["room"])
    crab["room"] = info["to"]
    crab["pos"] = spawn_at_entry(info["to"]) if back is None else spawn_in_front_of(back)
    crab["away"] = CRAB_TRANSIT_FRAMES
    crab["wait"] = CRAB_ARRIVE_FRAMES
    crab["moving"] = False


def catch_players(app):
    """A player the crab touches goes down; with everybody down, the game is over."""
    crab = app["crab"]
    state = app["state"]
    body = crab_rect(crab)
    for number in hunted_players(app):  # it walks through a hidden player
        player = app["players"][number - 1]
        if dashing(app, number):
            continue  # too fast to catch: Flash goes past it
        if engine.player_room(state, number) == crab["room"] and body.colliderect(player_rect(player["pos"])):
            app["downed"][number] = DOWN_FRAMES
            crab["wait"] = CRAB_CATCH_FRAMES
    if app["downed"] and not active_players(app):
        state, outcome = engine.crab_catches_everyone(app["state"])
        if outcome["ok"]:
            app["state"] = state
            save_progress(app)  # the ending is kept, like the others


def is_reviving(app, number):
    """True if player `number` is holding E: this computer's own key, or what the other computer said."""
    if number == my_number(app):
        return app["act_held"]
    return app["partner_reviving"]


def downed_near(app, player):
    """The number of a player down within reach of `player` in the same room, or None."""
    reach = player_rect(player["pos"]).inflate(2 * REACH, 2 * REACH)
    state = app["state"]
    number = player_number(app, player)
    for other in app["downed"]:
        if other != number and engine.player_room(state, other) == engine.player_room(state, number) \
                and reach.colliderect(player_rect(app["players"][other - 1]["pos"])):
            return other
    return None


def update_downed(app):
    """The timers of the players down: helped up after holding E long enough, out of the game after a minute."""
    for number in sorted(app["downed"]):
        helper = 3 - number
        helping = (helper in active_players(app) and is_reviving(app, helper)
                   and downed_near(app, app["players"][helper - 1]) == number)
        app["revive"][number] = app["revive"].get(number, 0) + 1 if helping else 0
        if app["revive"][number] >= revive_frames(app, helper):
            del app["downed"][number]
            del app["revive"][number]
            continue
        app["downed"][number] -= 1
        if app["downed"][number] <= 0:
            del app["downed"][number]
            app["revive"].pop(number, None)
            state, outcome = engine.knock_out(app["state"], number)
            if outcome["ok"]:
                app["state"] = state
                save_progress(app)


def update_crab(app):
    """The host's frame of the crab: wake it, move it, catch, and keep the timers of the players down."""
    if app["state"] is None or len(app["players"]) < 2:
        return
    if not engine.crab_awake(app["state"]):
        app["crab"] = None
        app["downed"] = {}
        app["revive"] = {}
        app["hidden"] = {}
        return
    if app["crab"] is None:
        app["crab"] = new_crab()
    crab = app["crab"]
    update_downed(app)
    app["hidden"] = {number: frames - 1 for number, frames in app["hidden"].items() if frames > 1}
    if crab["stun"] > 0:
        crab["stun"] -= 1  # the wizard's spell: it stands still, and harmless
        crab["moving"] = False
        return
    if crab["away"] > 0:
        crab["away"] -= 1
        return
    if crab["wait"] > 0:
        crab["wait"] -= 1
        crab["moving"] = False
        return
    move_crab(app)
    if crab["away"] == 0:
        catch_players(app)


def crab_news(app):
    """On every computer: tell the player what the crab has just done, from what changed since the last frame."""
    state = app["state"]
    if state is None:
        return
    awake = engine.crab_awake(state)
    me = my_number(app)
    caught = state["ending"] == "caught"
    if caught and not app["seen"]["caught"]:
        app["banner_frames"] = 0
        if effects.FX["shatter"]:
            start_shatter(app)  # the giant claw breaks the screen, then the ending
        else:
            sounds.play("knocked_out")
            say(app, story.MESSAGES["crab_ending"])  # then the ending, once it is read
    elif awake != app["seen"]["awake"] and not engine.is_over(state):
        if awake:
            sounds.play("crab_wake")
            start_crumble(app)  # the ship shakes, the statue trembles and bursts
        elif app["seen"]["crab_at"] is not None:
            room, pos, facing = app["seen"]["crab_at"]  # where it was: there it turns to stone, then to dust
            app["petrify"] = {"room": room, "pos": pos, "facing": facing, "age": 0}
            if room == view(app)["room"]:
                sounds.play("petrify")
        show_banner(app, story.MESSAGES["crab_wakes" if awake else "crab_sleeps"])
    downed = set(app["downed"])
    out = state["flags"]["out_player"]
    if not caught:
        for number in downed - app["seen"]["downed"]:
            sounds.play("knocked")
            if number != me:
                show_banner(app, story.MESSAGES["partner_down"])
        for number in app["seen"]["downed"] - downed:
            if out == number:
                continue
            if awake:
                sounds.play("revived")
                show_banner(app, story.MESSAGES["back_up" if number == me else "helped_up"])
    if app["seen"]["out"] == me and out == 0:
        come_back(app)
    if out != app["seen"]["out"] and out != 0:
        sounds.play("knocked_out")
        if out != me:
            show_banner(app, story.MESSAGES["partner_eliminated"])
    crab = app["crab"]
    app["seen"] = {"awake": awake, "downed": downed, "out": out, "caught": caught,
                   "abilities": app["seen"].get("abilities", {}),
                   "crab_at": None if crab is None else (crab["room"], crab["pos"], crab["facing"])}
    update_petrify(app)


def update_petrify(app):
    """The crab turning to stone: once it cracks, the floor trembles; then it bursts into dust."""
    stone = app["petrify"]
    if stone is None:
        return
    stone["age"] += 1
    if stone["age"] == PETRIFY_BURST and stone["room"] == view(app)["room"]:
        x, y = player_rect(stone["pos"]).center
        sounds.play("crumble")
        if effects.FX["crumble"]:
            effects.spawn(app["fx"], x, y, 40, RUBBLE_COLORS, speed=1.4, life=44, up=0.9, gravity=0.06)
    if stone["age"] >= PETRIFY_FRAMES:
        app["petrify"] = None


_stone_crabs = {}


def stone_crab(picture):
    """The crab's picture in grey stone: its shading kept, its colours gone."""
    key = id(picture)
    if key not in _stone_crabs:
        stone = pygame.transform.grayscale(picture)
        stone.fill((150, 146, 138), special_flags=pygame.BLEND_RGB_MULT)  # its shading, softer...
        stone.fill((96, 92, 84), special_flags=pygame.BLEND_RGB_ADD)      # ...on pale, warm marble, like the statue
        _stone_crabs[key] = stone
    return _stone_crabs[key]


def draw_petrify(app, screen):
    """The crab where it stood: its colour drains away into stone, the stone cracks and shivers,
    and at the end it is gone in a burst of dust (see update_petrify)."""
    stone = app["petrify"]
    if stone is None or stone["room"] != view(app)["room"] or stone["age"] >= PETRIFY_BURST:
        return
    small = crab_look.picture(crab_look.pose(legs=1, claws=0.0, eyes="calm", look=stone["facing"]))
    shiver = 0
    if stone["age"] >= PETRIFY_CRACK:
        shiver = (stone["age"] // 2) % 3 - 1  # cracked: it trembles before it bursts
    x, y = crab_place({"pos": stone["pos"]})
    place = small.get_rect(topleft=(x + shiver, y))
    screen.blit(small, place)
    grey = stone_crab(small).copy()
    grey.set_alpha(min(255, 255 * stone["age"] // PETRIFY_CRACK))  # the colour drains away
    screen.blit(grey, place)
    if stone["age"] >= PETRIFY_CRACK:
        cracks = 1 + 3 * (stone["age"] - PETRIFY_CRACK) // (PETRIFY_BURST - PETRIFY_CRACK)
        for index in range(cracks):
            x = place.left + 4 + round(scenery.hash01(index, 3, 21) * (place.width - 8))
            y = place.top + 5 + round(scenery.hash01(index, 7, 21) * (place.height - 10))
            pygame.draw.line(screen, RUBBLE_COLORS[2], (x, y), (x + 3 - 2 * (index % 2) * 3, y + 4), 1)
            pygame.draw.line(screen, RUBBLE_COLORS[2], (x, y), (x - 2, y - 3), 1)


# --- The statue crumbling, and the claw that breaks the screen ---------------------------
#
# Two short sequences, counted in frames like every animation. Neither is part of
# the game's state: the engine has already decided (the crab is awake, the crab has
# caught everyone), and these only show it.

CRUMBLE_FRAMES = 40    # how long the ship shakes when the crab statue comes alive
CRUMBLE_BREAK = 18     # how many of those frames the statue trembles, whole, before it bursts
CRUMBLE_SHAKE = 4      # pixels the room is pushed aside at the start of the shaking: then less and less

CLAW_ATTACK = 15       # frames the giant claw takes to come in from the corner and snap shut
CLAW_REACH = 10        # ...of which these to get to the middle of the screen; the rest to close
CLAW_IMPACT = 27       # the frame the cracked screen falls to pieces: until then the hit, the flash, the cracks
SHATTER_FRAMES = 86    # how long the whole sequence lasts: then the ending screen
CLAW_FLASH = 3         # frames of white flash when the claw hits
CLAW_SHAKE = 6         # pixels of shake at the hit, dying down until the screen falls apart
CLAW_RETREAT = 12      # frames the claw takes to pull back out once the screen breaks
CLAW_SHADOW = (12, 16)  # how far from the claw its shadow falls on the screen while it is still far above it
CLAW_SPARKS = 20       # sparks and chips thrown from where the jaws shut
SHATTER_SEED = 11      # the web of cracks is always the same one


def start_crumble(app):
    """The crab has just come alive: the ship shakes and the statue starts to crumble.

    With the effect switched off the statue simply bursts at once, as it did before.
    """
    if effects.FX["crumble"]:
        app["crumble"] = CRUMBLE_FRAMES
        sounds.play("crumble")
    else:
        burst_statue(app)


def statue_on_screen(app):
    """True if this computer shows the room of the crab statue."""
    return view(app)["room"] == story.OBJECTS["deck_statue"]["room"]


def burst_statue(app):
    """The statue bursts: dust and pieces fly (for whoever is on the deck to see it)."""
    if statue_on_screen(app):
        x, y = thing_rect("deck_statue").center
        effects.spawn(app["fx"], x, y, 40, RUBBLE_COLORS, speed=2.6, life=45, gravity=0.12, up=1.6)


def statue_trembles(app):
    """True in the first frames of the crumbling: the statue is still whole, shaking, about to burst."""
    return app["crumble"] > CRUMBLE_FRAMES - CRUMBLE_BREAK


def update_crumble(app):
    """One frame of the crumbling: stones and dust fall around the statue, and at the right moment it bursts."""
    if app["crumble"] <= 0:
        return
    age = CRUMBLE_FRAMES - app["crumble"]
    if age == CRUMBLE_BREAK:
        burst_statue(app)
    elif statue_on_screen(app) and app["state"] is not None:
        statue = thing_rect("deck_statue")
        rng = app["fx"]["rng"]
        for _ in range(2 if age < CRUMBLE_BREAK else 1):  # more while it is still breaking up
            effects.spawn(app["fx"], rng.uniform(statue.left - 6, statue.right + 6), rng.uniform(statue.top - 4, statue.centery),
                          1, RUBBLE_COLORS, speed=0.4, life=34, gravity=0.14, spread=math.pi / 2, angle=math.pi / 2)
    app["crumble"] -= 1


def room_shake(app):
    """How far the room is pushed aside in this frame: the ship shaking while the statue crumbles,
    or under the strongest thunder of the storm."""
    dx, dy = effects.shake_offset(app["frame"], app["crumble"], CRUMBLE_FRAMES, CRUMBLE_SHAKE)
    if effects.FX["weather"] and app["state"] is not None:
        tx, ty = weather.shake(app["weather"], app["frame"], thunder_shake(view(app)["room"]))
        dx, dy = dx + tx, dy + ty
    return (dx, dy)


def draw_trembling_statue(app, screen):
    """The statue in its last moments: jumping a pixel left and right, and flashing pale."""
    picture = sprites.image("decor_crab_statue")
    if picture is None:
        return
    rect = thing_rect("deck_statue")
    age = CRUMBLE_FRAMES - app["crumble"]
    if (age // 2) % 3 == 2:
        picture = picture.copy()
        picture.fill((90, 90, 90, 0), special_flags=pygame.BLEND_RGB_ADD)  # a pale flash: about to give way
    screen.blit(picture, rect.move((age % 2) * 2 - 1, 0))


def start_shatter(app):
    """The crab has caught both players. Keep the last picture of the game, cut it along a web
    of cracks, and start the sequence of the giant claw; the ending comes when it is over."""
    frozen = pygame.Surface((WIDTH, HEIGHT))
    draw_play_screen(app, frozen, overlays=False)  # the game as it was at that moment, on the small screen
    hit = (WIDTH // 2, HEIGHT // 2)
    pieces = effects.crack_web((WIDTH, HEIGHT), hit, SHATTER_SEED)
    app["shatter"] = {"age": 0, "frozen": frozen, "hit": hit, "pieces": pieces,
                      "shards": effects.cut_shards(frozen, pieces, hit, SHATTER_SEED),
                      "sparks": [], "rng": random.Random(SHATTER_SEED)}  # thrown when the jaws shut
    app["dialog"] = []
    app["crumble"] = 0
    sounds.play("knocked")
    set_scene(app, "shatter")


def update_shatter(app):
    """One frame of the claw breaking the screen. Nothing can be done meanwhile; then the ending."""
    shatter = app["shatter"]
    shatter["age"] += 1
    effects.update_particles(shatter["sparks"])
    if shatter["age"] == CLAW_ATTACK:
        sounds.play("snap")      # the claw snaps shut on the screen
        x, y = claw_pose(shatter["age"])["tip"]
        effects.spawn(shatter, x, y, CLAW_SPARKS, effects.SPARK + [claw.LIGHT, claw.BASE], speed=3.2, life=24,
                      gravity=0.14, up=0.6, layer="sparks")  # sparks and chips of shell fly from the grip
    elif shatter["age"] == CLAW_IMPACT:
        sounds.play("shatter")   # and the screen falls to pieces
    if shatter["age"] >= SHATTER_FRAMES:
        app["shatter"] = None
        set_scene(app, "ending")


def claw_pose(age):
    """Where the giant claw is `age` frames into the sequence (see claw.pose): it comes in from the
    top right corner, shuts on the middle of the screen, kicks back at the hit, holds, and pulls
    back out once the screen breaks."""
    return claw.pose(age, (WIDTH, HEIGHT), CLAW_REACH, CLAW_ATTACK, CLAW_IMPACT, CLAW_RETREAT)


def draw_giant_claw(screen, age, offset=(0, 0)):
    """The crab's limb, giant, with the shadow it casts on the game while the screen is still whole.

    The shadow lies down and to the right of the limb, far from it while the claw is high above
    the screen and closer as it comes down: at the hit the two touch.
    """
    limb = claw_pose(age)
    picture = claw.layer((WIDTH, HEIGHT), limb, offset)
    if age < CLAW_IMPACT:
        fall = (round(CLAW_SHADOW[0] * limb["shadow"]), round(CLAW_SHADOW[1] * limb["shadow"]))
        screen.blit(claw.shadow_of(picture), fall)
    screen.blit(picture, (0, 0))


def draw_shatter(app, screen):
    """The giant claw breaking the screen, in three parts: the claw comes in over the last picture
    of the game and snaps shut; a white flash, a hard shake and cracks all over; then the picture
    falls apart in pieces over black, and the claw pulls back."""
    shatter = app["shatter"]
    if shatter is None:
        screen.fill(COLORS["black"])
        return
    age = shatter["age"]
    shake = effects.shake_offset(app["frame"], CLAW_IMPACT - age, CLAW_IMPACT - CLAW_ATTACK, CLAW_SHAKE) \
        if age >= CLAW_ATTACK else (0, 0)
    screen.fill(COLORS["black"])
    if age < CLAW_IMPACT:
        screen.blit(shatter["frozen"], shake)
        if age >= CLAW_ATTACK:
            farthest = math.hypot(WIDTH, HEIGHT)
            grown = min((age - CLAW_ATTACK + 1) / (CLAW_IMPACT - CLAW_ATTACK - 4), 1.0)  # the cracks run outwards
            effects.draw_cracks(screen, shatter["pieces"], shatter["hit"], farthest * grown, shake)
    else:
        effects.draw_shards(screen, shatter["shards"], age - CLAW_IMPACT)
    draw_giant_claw(screen, age, shake)
    effects.draw_particles(screen, shatter["sparks"])
    if CLAW_ATTACK <= age < CLAW_ATTACK + CLAW_FLASH:
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((255, 255, 255, 255 - 70 * (age - CLAW_ATTACK)))  # the hit: everything stops in white
        screen.blit(veil, (0, 0))


def reset_crab(app):
    """A game starts or resumes: no crab in sight yet (it is not saved), nobody down."""
    app["crab"] = None
    app["downed"] = {}
    app["revive"] = {}
    app["hidden"] = {}
    app["afterimages"] = []
    app["beams"] = []
    app["crab_trail"] = []
    app["petrify"] = None
    app["crumble"] = 0
    app["shatter"] = None
    app["partner_reviving"] = False
    state = app["state"]
    app["seen"] = {"awake": state is not None and engine.crab_awake(state), "downed": set(),
                   "abilities": {} if state is None else abilities_used(state),
                   "out": 0 if state is None else state["flags"]["out_player"],
                   "caught": state is not None and state["ending"] == "caught", "crab_at": None}


def crab_info(app):
    """What the computer that joined needs to draw the crab and the players down."""
    return {"crab": app["crab"], "downed": {str(number): frames for number, frames in app["downed"].items()},
            "revive": {str(number): frames for number, frames in app["revive"].items()},
            "hidden": {str(number): frames for number, frames in app["hidden"].items()}}


def take_crab_info(app, info):
    """Copy what the host said about the crab and the players down."""
    crab = info.get("crab")
    if isinstance(crab, dict):
        crab = dict(crab, pos=tuple(crab["pos"]), facing=tuple(crab["facing"]))
    app["crab"] = crab
    app["downed"] = {int(number): frames for number, frames in info.get("downed", {}).items()}
    app["revive"] = {int(number): frames for number, frames in info.get("revive", {}).items()}
    app["hidden"] = {int(number): frames for number, frames in info.get("hidden", {}).items()}


def can_move(app):
    """False for the player on this computer while they are down or out of the game."""
    number = my_number(app)
    return number not in app["downed"] and not engine.is_out(app["state"], number)


def crab_target_player(app):
    """The player the crab is after in its room, the nearest one it can see, or None."""
    crab = app["crab"]
    state = app["state"]
    body = pygame.Vector2(crab_rect(crab).center)
    here = [number for number in hunted_players(app) if engine.player_room(state, number) == crab["room"]]
    if not here:
        return None
    return min(here, key=lambda number: body.distance_to(player_rect(app["players"][number - 1]["pos"]).center))


def crab_telegraph(app):
    """True when the crab is about to lunge: hunting, and a player is within CHARGE_DISTANCE."""
    crab = app["crab"]
    target = crab_target_player(app)
    if target is None or crab["stun"] > 0:
        return False
    body = crab_rect(crab).center
    other = player_rect(app["players"][target - 1]["pos"]).center
    return math.hypot(other[0] - body[0], other[1] - body[1]) < CHARGE_DISTANCE


def crab_pose(app):
    """How the crab looks now (see crab.py): its legs walk while it moves; its claws open and shut
    as it chases, and gape when it is about to lunge; it breathes when it stands still; its eyes
    burn when it hunts, and droop when the wizard has stunned it."""
    crab = app["crab"]
    if crab["stun"] > 0:
        return crab_look.pose(legs=1, claws=0.0, breath=(app["frame"] // (CRAB_BREATH_FRAMES * 2)) % 2,
                              eyes="dazed", look=(0, 1))
    target = crab_target_player(app)
    legs = (crab["walk"] // CRAB_LEG_FRAMES) % 4 if crab["moving"] else 1
    breath = 0 if crab["moving"] else (app["frame"] // (CRAB_BREATH_FRAMES // 2)) % 2
    if target is None:
        return crab_look.pose(legs, 0.25, breath, "calm", crab["facing"])
    body = crab_rect(crab).center
    other = player_rect(app["players"][target - 1]["pos"]).center
    look = (sign(other[0] - body[0]), sign(other[1] - body[1]))
    if crab_telegraph(app):
        claws = 1.0  # gaping: it is about to lunge
    elif crab["moving"]:
        claws = CRAB_CLAW_RHYTHM[(app["frame"] // CRAB_CLAW_BEAT) % len(CRAB_CLAW_RHYTHM)]
    else:
        claws = 0.25
    return crab_look.pose(legs, claws, breath, "hunt", look)


def crab_place(crab):
    """Where the crab's picture goes: its legs on the floor at the bottom of its body, its shell over the middle."""
    body = crab_rect(crab)
    return (body.centerx - crab_look.CENTER[0], body.bottom + 1 - crab_look.FEET)


def update_crab_looks(app):
    """On every computer, once a frame: the dust or foam its legs kick up as it runs, and the red
    streaks its burning eyes leave behind when it is about to lunge."""
    for streak in app["crab_trail"]:
        streak["age"] += 1
    app["crab_trail"] = [streak for streak in app["crab_trail"] if streak["age"] < CRAB_TRAIL_FRAMES]
    crab = app["crab"]
    if app["state"] is None or crab is None or crab["away"] > 0 or crab["room"] != view(app)["room"]:
        return
    if crab["moving"] and effects.FX["dust"] and app["frame"] % CRAB_DUST_EVERY == 0:
        info = story.ROOMS[crab["room"]]
        colors = CRAB_FOAM if info["outdoor"] or info.get("damp") or crab["room"] == "crab_room" else CRAB_DUST
        body = crab_rect(crab)
        side = 1 if (app["frame"] // CRAB_DUST_EVERY) % 2 else -1  # one side, then the other
        effects.spawn(app["fx"], body.centerx + side * 14, body.bottom, 3, colors, speed=0.5, life=16, up=0.5,
                      gravity=0.04)
    if crab["moving"] and crab_telegraph(app):
        x, y = crab_place(crab)
        points = [(x + px, y + py) for px, py in crab_look.eye_points(crab_pose(app))]
        app["crab_trail"].append({"room": crab["room"], "points": points, "age": 0})


def draw_crab(app, screen):
    """The crab: a wide shadow on the floor under it, the crab in its pose, a shiver when it is
    about to lunge, the glow and the streaks of its burning eyes, and stars when it is stunned."""
    crab = app["crab"]
    body = crab_rect(crab)
    shadow = shadow_picture(CRAB_SHADOW)
    screen.blit(shadow, shadow.get_rect(center=(body.centerx + 1, body.bottom - 1)))
    crab_pose_now = crab_pose(app)
    x, y = crab_place(crab)
    if crab_telegraph(app):
        x += 1 if (app["frame"] // 2) % 2 else -1  # it shivers, ready to lunge
    for streak in app["crab_trail"]:
        if streak["room"] == crab["room"]:
            fade = 1 - streak["age"] / CRAB_TRAIL_FRAMES
            color = tuple(round(channel * fade) for channel in crab_look.HUNT_EYE)
            for point in streak["points"]:
                screen.fill(color, (point[0], point[1], 2, 1), special_flags=pygame.BLEND_RGB_ADD)
    screen.blit(crab_look.picture(crab_pose_now), (x, y))
    if crab_pose_now["eyes"] == "hunt" and effects.FX["lights"]:
        for px, py in crab_look.eye_points(crab_pose_now):
            effects.glow(screen, (x + px, y + py), 5, CRAB_EYE_GLOW, effects.pulse(app["frame"], 0.15, 0.6, 1.0))
    if crab["stun"] > 0:  # stunned by the wizard: three stars turn above its head
        for star in range(3):
            angle = app["frame"] * 0.15 + star * 2 * math.pi / 3
            sx = body.centerx + round(8 * math.cos(angle))
            sy = y + 2 + round(3 * math.sin(angle))
            pygame.draw.rect(screen, COLORS["highlight"], (sx - 1, sy - 1, 3, 3))
            pygame.draw.rect(screen, COLORS["text"], (sx, sy, 1, 1))


def crab_here(app):
    """True if the crab is in sight in the room shown on this computer."""
    crab = app["crab"]
    if statue_trembles(app):
        return False  # still inside its statue
    return crab is not None and crab["away"] == 0 and crab["room"] == view(app)["room"]


def draw_bar(screen, center_x, top, width, filled, color):
    """A small bar of progress: `filled` from 0 to 1."""
    frame = pygame.Rect(0, 0, width + 2, 4)
    frame.midtop = (center_x, top)
    pygame.draw.rect(screen, COLORS["black"], frame)
    inside = frame.inflate(-2, -2)
    inside.width = round(inside.width * max(0.0, min(1.0, filled)))
    if inside.width > 0:
        pygame.draw.rect(screen, color, inside)


def draw_downed_bars(app, screen, player):
    """Above a player down: the time left (red), and the help being given (green)."""
    number = player_number(app, player)
    if number not in app["downed"]:
        return
    body = player_rect(player["pos"])
    draw_bar(screen, body.centerx, body.top - 12, 16, app["downed"][number] / DOWN_FRAMES, COLORS["danger"])
    progress = app["revive"].get(number, 0)
    if progress > 0:
        draw_bar(screen, body.centerx, body.top - 7, 16, progress / revive_frames(app, 3 - number), COLORS["help"])


def draw_crab_overlay(app, screen):
    """On the screen of a player down or out: what happened, and the time left."""
    number = my_number(app)
    font = app["fonts"]["text"]
    if engine.is_out(app["state"], number):
        draw_text(screen, font, story.MESSAGES["spectator"], COLORS["highlight"], (WIDTH // 2, HEIGHT - 14), "center", True)
    elif number in app["downed"]:
        dim(screen)
        draw_text(screen, app["fonts"]["title"], story.MESSAGES["you_are_down"], COLORS["text"], (WIDTH // 2, 70), "center", True)
        draw_text(screen, font, story.MESSAGES["down_hint"], COLORS["foam"], (WIDTH // 2, 96), "center", True)
        draw_bar(screen, WIDTH // 2, 112, 100, app["downed"][number] / DOWN_FRAMES, COLORS["danger"])
        progress = app["revive"].get(number, 0)
        if progress > 0:
            draw_bar(screen, WIDTH // 2, 120, 100, progress / revive_frames(app, 3 - number), COLORS["help"])


# --- The abilities of the characters, in a game for two: Space, once in a game -------------
#
# The wizard stuns the crab, the ghost hides from it, Flash dashes. The engine
# remembers that the ability is used up (engine.use_ability); what happens on
# screen is here. The crab's side of it (the stun, who it cannot see) is the
# host's, like the rest of the crab; the dash moves the player on their own computer.
# The nurse's ability is always on: see revive_frames.


def use_ability(app):
    """Space: the player on this computer uses their ability, if they still have it."""
    if app["state"] is None or not can_move(app) or not engine.can_use_ability(app["state"], my_number(app)):
        return
    request(app, {"verb": "ability", "target": None, "item": None}, finish_ability)


def finish_ability(app, action, before, state, outcome):
    if not outcome["ok"]:
        return
    app["state"] = state
    save_progress(app)
    number = my_number(app)
    character = engine.character_of(state, number)
    sounds.play("ability")
    wasted = character in ("wizard", "ghost") and not engine.crab_awake(state)
    show_banner(app, story.MESSAGES["ability_wasted"] if wasted else outcome["text"])
    if is_host(app):
        apply_ability(app, number)
    if character == "flash":
        dash(app)


def heart_helps(app, outcome, number):
    """The host's part of the heart of the mine: when player `number` picks it up, the other one,
    if they are down, is on their feet at once. (If they were out of the game, the engine has
    brought them back: see engine.pick_up.)"""
    if outcome["event"] in ("used_up", "revived"):
        app["downed"].pop(3 - number, None)
        app["revive"].pop(3 - number, None)


def come_back(app):
    """The player on this computer was out of the game and the heart brought them back: they
    appear next to the one who picked it up."""
    player = local_player(app)
    partner = app["players"][1 - app["me"]]
    player["pos"] = beside(view(app), partner["pos"])
    player["touching"] = None
    settle_on_floor(app, player)
    app["fade"] = FADE_FRAMES
    sounds.play("revived")
    show_banner(app, story.MESSAGES["back_in_game"])


def apply_ability(app, number):
    """The host's part of an ability player `number` has just used: the crab stunned, or a player hidden.

    With the crab still a statue there is nothing to stun or to hide from: the ability is wasted.
    """
    character = engine.character_of(app["state"], number)
    if not engine.crab_awake(app["state"]):
        return
    if character == "wizard":
        if app["crab"] is None:
            app["crab"] = new_crab()
        app["crab"]["stun"] = STUN_FRAMES  # wherever it is
    elif character == "ghost":
        app["hidden"][number] = HIDDEN_FRAMES


def dash(app):
    """Flash sprints DASH_TILES tiles the way they face, in DASH_FRAMES frames (see dash_step)."""
    player = local_player(app)
    player["dash"] = DASH_FRAMES
    player["dash_way"] = player["facing"]
    sounds.play("dash")


def dash_step(app):
    """One frame of Flash's dash: a few pixels at a time, stopped by anything solid, and through
    an open door or a portal on the way (a shut door stops them, and says why). The tiles of the
    floor only count where the dash ends."""
    player = local_player(app)
    dx, dy = player["dash_way"]
    player["dash"] -= 1
    player["moving"] = True
    player["walk"] += 1
    left = DASH_TILES * TILE // DASH_FRAMES
    while left > 0:
        step = min(DASH_STEP, left)
        left -= step
        seen = view(app)
        before = player["pos"]
        player["pos"] = move(player["pos"], dx * step, dy * step, solid_rects(seen))
        door = door_touched(seen["room"], player["pos"], dx, dy)
        if door is not None:
            if door != player["touching"]:
                player["touching"] = door
                go_through(app, door)
            player["dash"] = 0
            return
        portal = portal_touched(seen, player["pos"])
        if portal is not None:
            go_through_portal(app, portal)
            player["dash"] = 0
            return
        if player["pos"] == before:
            player["dash"] = 0  # against something solid
            return


def dashing(app, number):
    """True while player `number` is in the middle of Flash's dash."""
    return app["players"][number - 1]["dash"] > 0


def abilities_used(state):
    """Which player has used their ability: number -> True or False."""
    return {number: state["flags"]["ability_used_" + str(number)] for number in (1, 2)}


def ability_news(app):
    """On every computer: an ability has just been used, here or on the other computer. Show it:
    the ray of the wizard's spell, and the burst of Flash's start."""
    state = app["state"]
    if state is None:
        return
    used = abilities_used(state)
    for number, now in used.items():
        if not now or app["seen"].get("abilities", {}).get(number, False) or number > len(app["players"]):
            continue
        character = engine.character_of(state, number)
        if engine.player_room(state, number) != view(app)["room"]:
            continue  # elsewhere on the ship: nothing to see here
        body = player_rect(app["players"][number - 1]["pos"])
        if character == "wizard":
            start_beam(app, number)
        elif character == "flash" and effects.FX["wand"]:
            effects.spawn(app["fx"], body.centerx, body.centery, 16, DASH_SPARKS, speed=1.6, life=18)
    app["seen"]["abilities"] = used


def start_beam(app, number):
    """The wizard's spell: a ray from the wand to the crab, if it is in the room; otherwise the
    way the wizard faces, as far as a wall (the spell finds the crab wherever it is)."""
    player = app["players"][number - 1]
    room = engine.player_room(app["state"], number)
    body = player_rect(player["pos"])
    fx, fy = player["facing"]
    start = (body.centerx + fx * 7, body.centery - 6 + fy * 4)  # the tip of the wand
    crab = app["crab"]
    if crab is not None and crab["room"] == room:
        end = crab_rect(crab).center
    else:
        end = start
        walls = wall_rects(room)
        for _ in range(BEAM_REACH // 4):
            ahead = (end[0] + fx * 4, end[1] + fy * 4)
            if pygame.Rect(ahead[0] - 1, ahead[1] - 1, 2, 2).collidelist(walls) != -1:
                break
            end = ahead
    app["beams"].append({"room": room, "from": start, "to": end, "age": 0})
    sounds.play("zap")
    if effects.FX["wand"]:
        effects.spawn(app["fx"], end[0], end[1], 24, BEAM_COLORS, speed=1.4, life=26, up=0.3)


def update_ability_effects(app):
    """The afterimages of a dash and the rays of a spell: they fade, and a dashing Flash leaves new ones."""
    for image in app["afterimages"]:
        image["age"] += 1
    app["afterimages"] = [image for image in app["afterimages"] if image["age"] < AFTERIMAGE_FRAMES]
    for beam in app["beams"]:
        beam["age"] += 1
    app["beams"] = [beam for beam in app["beams"] if beam["age"] < BEAM_FRAMES]
    if app["state"] is None:
        return
    for number, player in enumerate(app["players"], start=1):
        if player["dash"] <= 0 or engine.player_room(app["state"], number) != view(app)["room"]:
            continue
        picture = player_picture(app, player)
        if picture is None:
            continue
        glow = picture.copy()
        glow.fill((255, 226, 90), special_flags=pygame.BLEND_RGB_MULT)  # a copy of Flash, in yellow
        glow.fill((70, 50, 0), special_flags=pygame.BLEND_RGB_ADD)
        body = player_rect(player["pos"])
        app["afterimages"].append({"picture": glow, "feet": (body.centerx, body.bottom + 1), "age": 0})
        if effects.FX["wand"]:
            effects.spawn(app["fx"], body.centerx, body.centery, 3, DASH_SPARKS, speed=0.6, life=14)


def draw_afterimages(app, screen):
    """The yellow copies a dashing Flash leaves behind, older ones fainter."""
    for image in app["afterimages"]:
        picture = image["picture"]
        picture.set_alpha(200 - 200 * image["age"] // AFTERIMAGE_FRAMES)
        screen.blit(picture, picture.get_rect(midbottom=image["feet"]))


def beam_points(beam, frame):
    """The zigzag of a ray: its ends fixed, the points between jumping sideways every few frames."""
    (x0, y0), (x1, y1) = beam["from"], beam["to"]
    length = math.hypot(x1 - x0, y1 - y0) or 1.0
    nx, ny = -(y1 - y0) / length, (x1 - x0) / length
    count = max(int(length // 10), 1)
    points = [(x0, y0)]
    for index in range(1, count):
        share = index / count
        jump = (scenery.hash01(index, frame // 3, 5) - 0.5) * 8
        points.append((x0 + (x1 - x0) * share + nx * jump, y0 + (y1 - y0) * share + ny * jump))
    points.append((x1, y1))
    return points


def draw_beams(app, screen):
    """The rays of the wizard's spell: a violet zigzag with a white core, thinner as it fades,
    and a ring that opens where it strikes."""
    for beam in app["beams"]:
        if beam["room"] != view(app)["room"]:
            continue
        left = 1 - beam["age"] / BEAM_FRAMES
        points = [(round(x), round(y)) for x, y in beam_points(beam, app["frame"])]
        if len(points) >= 2:
            if effects.FX["lights"]:
                for point in points[::2]:
                    effects.glow(screen, point, 8, (40, 20, 70), left)
            pygame.draw.lines(screen, BEAM_COLORS[0], False, points, max(1, round(5 * left)))
            pygame.draw.lines(screen, BEAM_COLORS[1], False, points, max(1, round(3 * left)))
            pygame.draw.lines(screen, BEAM_COLORS[2], False, points, 1)
        ring = 3 + beam["age"] // 2
        if left > 0.3:
            pygame.draw.circle(screen, BEAM_COLORS[1], (round(beam["to"][0]), round(beam["to"][1])), ring, 1)


def ability_hint(app):
    """What the corner of the screen says about the ability of the player on this computer, and its color.

    None alone, and once the ability is used up.
    """
    state = app["state"]
    number = my_number(app)
    if not state["flags"]["two_players"] or engine.is_out(state, number):
        return None
    if engine.character_of(state, number) == "nurse":
        return (story.MESSAGES["hint_nurse"], COLORS["dim_text"])
    if not engine.can_use_ability(state, number):
        return None
    label = story.CHARACTERS[engine.character_of(state, number)]["power"]["label"]
    return (story.MESSAGES["hint_ability"].format(label=label), COLORS["highlight"])


def draw_ability_hint(app, screen):
    hint = ability_hint(app)
    if hint is not None:
        draw_text(screen, app["fonts"]["text"], hint[0], hint[1], (4, HEIGHT - 12), "left", True)


# --- Two computers: hosting, joining, and keeping the two games in step ---------------------
#
# The host keeps the game: the rules run there, and only there is it saved. The
# computer that joined moves its own player and draws its own room; for anything
# else it asks the host (see request) and gets back the new state. Every frame each
# side tells the other where its player is.


def player_info(player):
    """What the other computer needs to draw a player."""
    return {"pos": list(player["pos"]), "facing": list(player["facing"]), "moving": player["moving"],
            "walk": player["walk"], "dash": player["dash"]}


def take_player_info(player, info):
    """Copy what the other computer said about its player."""
    player["pos"] = tuple(info["pos"])
    player["facing"] = tuple(info["facing"])
    player["moving"] = bool(info["moving"])
    player["walk"] = int(info["walk"])
    player["dash"] = int(info.get("dash", 0))


def send(app, message):
    connection = app["net"]
    if connection is not None and connection["conn"] is not None:
        connection["conn"].send(message)


def end_network(app):
    """Close the connection, and stop waiting for the other computer."""
    connection = app["net"]
    if connection is None:
        return
    if connection["conn"] is not None:
        connection["conn"].close()
    if connection.get("host") is not None:
        connection["host"].close()
    app["net"] = None
    app["lobby"] = None


def open_lobby(app, state, opening_text):
    """The host's game is ready: wait for the other computer to join, showing this computer's address."""
    try:
        host = net.Host(NET_PORT)
    except OSError:
        app["notice"] = story.MESSAGES["cannot_host"]
        open_main_menu(app)
        return
    app["net"] = {"role": "host", "host": host, "conn": None, "pending": {}, "next_id": 0, "sent_state": None,
                  "address": net.local_address()}
    app["lobby"] = (state, opening_text)
    app["taken"] = None
    app["picked"] = None
    set_scene(app, "lobby")


def open_join(app):
    """The "Join game" screen. The address starts with this computer's network, to save typing."""
    address = net.local_address()
    app["join_text"] = address[:address.rfind(".") + 1] if "." in address else ""
    app["join_error"] = ""
    set_scene(app, "join")


def join(app, address):
    """Try to join the game hosted at `address`; the game starts when the host sends it."""
    try:
        conn = net.connect(address, NET_PORT)
    except (OSError, ValueError):
        app["join_error"] = story.MESSAGES["cannot_join"]
        return
    app["net"] = {"role": "client", "host": None, "conn": conn, "pending": {}, "next_id": 0, "sent_state": None}
    app["join_error"] = story.MESSAGES["joining"]


def pump_network(app):
    """Every frame: let the other computer in, read what it said, and tell it where this player is."""
    connection = app["net"]
    if connection is None:
        return
    if connection["role"] == "host" and connection["conn"] is None:
        conn = connection["host"].accept()
        if conn is None:
            return
        connection["host"].close()  # one partner only: stop listening
        connection["host"] = None
        connection["conn"] = conn
        state, opening_text = app["lobby"]
        if opening_text is None:
            start_for_two(app)  # a game resumed: the characters are the ones of the first time
        else:
            send(app, {"t": "pick", "taken": None})  # both choose their character now
            open_choice_for_two(app)
    for message in connection["conn"].poll():
        handle_message(app, message)
        if app["net"] is None:
            return  # the message ended the game for two
    if connection["conn"].closed and app["lobby"] is not None:
        state, opening_text = app["lobby"]  # the other player left before the game started: wait again
        end_network(app)
        open_lobby(app, state, opening_text)
        return
    if connection["conn"].closed:
        app["notice"] = story.MESSAGES["partner_left"]
        open_main_menu(app)
        return
    if app["state"] is None or len(app["players"]) < 2:
        return
    message = {"t": "sync", "player": player_info(local_player(app))}
    if connection["role"] == "host":
        message.update(crab_info(app))
    else:
        message["reviving"] = app["act_held"]
    if connection["role"] == "host" and app["state"] is not connection["sent_state"]:
        message["state"] = app["state"]  # the game changed: the other computer gets the new one
        connection["sent_state"] = app["state"]
    if app["frame"] % SYNC_EVERY == 0 or "state" in message:
        send(app, message)


def start_for_two(app):
    """The host: both players are ready. Send the game to the other computer and start playing."""
    connection = app["net"]
    state, opening_text = app["lobby"]
    app["lobby"] = None
    send(app, {"t": "start", "state": state, "text": opening_text})
    connection["sent_state"] = state
    begin_game(app, state, opening_text)


def handle_message(app, message):
    """One message from the other computer."""
    kind = message.get("t")
    connection = app["net"]
    if kind == "pick" and connection["role"] == "client" and (message.get("taken") in story.CHARACTERS
                                                                 or message.get("taken") is None):
        if app["scene"] != "character":
            open_choice_for_two(app)  # the host is there: time to choose
        take_character(app, message["taken"])
        return
    if kind == "picked" and connection["role"] == "host" and app["lobby"] is not None:
        character = message.get("character")
        if character not in story.CHARACTERS or character == app["picked"]:
            send(app, {"t": "pick", "taken": app["picked"]})  # not that one: choose again
            return
        take_character(app, character)
        start_when_both_chose(app)
        return
    if kind == "start" and connection["role"] == "client":
        state = engine.restore_state(message.get("state"))
        if state is None:
            app["notice"] = story.MESSAGES["partner_left"]
            open_main_menu(app)
            return
        app["me"] = 1
        begin_game(app, state, message.get("text"))
    elif kind == "sync" and len(app["players"]) == 2:
        other = app["players"][1 - app["me"]]
        if isinstance(message.get("player"), dict):
            take_player_info(other, message["player"])
        if connection["role"] == "client" and "state" in message:
            state = engine.restore_state(message["state"])
            if state is not None:
                app["state"] = state
        if connection["role"] == "client":
            take_crab_info(app, message)
        else:
            app["partner_reviving"] = bool(message.get("reviving"))
    elif kind == "do" and connection["role"] == "host" and app["state"] is not None:
        # The other player asks for an action: the host plays it as player 2.
        state, outcome = engine.perform(app["state"], message["action"], 2)
        if outcome["ok"]:
            app["state"] = state
            save_progress(app)
            if message["action"].get("verb") == "ability":
                apply_ability(app, 2)
            heart_helps(app, outcome, 2)
        send(app, {"t": "done", "id": message.get("id"), "state": app["state"], "outcome": outcome})
        connection["sent_state"] = app["state"]
    elif kind == "done" and connection["role"] == "client":
        waiting = connection["pending"].pop(message.get("id"), None)
        state = engine.restore_state(message.get("state"))
        if waiting is None or state is None:
            return
        action, before, finish = waiting
        finish(app, action, before, state, message["outcome"])


# --- Sound: the rooms, the footsteps, and the crab wherever it is ----------------------------
#
# Every room has a quiet sound of its own, looping on channels of its own (sounds.loop): the
# sea on the deck, muffled inside the ship, water dripping in the damp rooms; and a machine's
# hum that grows as the player comes near a generator or a portal, from the side it is on.
# They fade into each other when the player changes room. Footsteps sound like the floor
# they fall on, or splash in a puddle. The crab's claws click on the floor, louder as it comes
# nearer, from its side of the screen, faster when it charges; in the next room, through an
# open door, they are muffled and come from that door. Each computer hears from its own
# player: nothing of this goes through the network, only what is already there.

SEA_VOLUME = 0.55        # the sea, on the deck
SEA_INSIDE_VOLUME = 0.3  # ...and from inside the ship
DRIPS_VOLUME = 0.6       # the water dripping in the damp rooms
HUM_VOLUME = 0.45        # a machine's hum, right next to it
HUM_RANGE = 6 * TILE     # how far it is heard
HUM_OFF = 0.35           # a generator that is off hums less
STEP_VOLUME = 0.3        # footsteps: soft
HEAR_RANGE = 16 * TILE   # how far something in the room is still heard, at its quietest
HEAR_QUIETEST = 0.2      # how quiet that is
PAN_WIDTH = 0.8          # how far to the side a sound can be put: never all in one ear
CRAB_VOLUME = 0.8        # the crab's claws, right next to the player
CLAW_CLICK_EVERY = 16    # frames between two clicks of its claws as it walks...
CHARGE_CLICK_EVERY = 9   # ...and as it charges
CHARGE_DISTANCE = 4 * TILE  # it charges when it is this close
CHARGE_PAUSE = 3 * FPS   # frames before its charge can be heard again
NEXT_ROOM_VOLUME = 0.35  # its claws in the next room, through the wall


def listener(app):
    """The player whose ears this computer uses: its own, or the partner's it watches once out."""
    state = app["state"]
    if engine.is_out(state, my_number(app)) and len(app["players"]) == 2:
        return app["players"][1 - app["me"]]
    return local_player(app)


def hearing(app, point):
    """How loud and from where a sound at `point` (room pixels) of the room on screen reaches the
    listener: (volume, pan). Quieter the farther it is, never silent in the room."""
    ear = player_rect(listener(app)["pos"]).center
    distance = math.hypot(point[0] - ear[0], point[1] - ear[1])
    volume = max(HEAR_QUIETEST, 1 - distance / HEAR_RANGE)
    pan = max(-1.0, min(1.0, (point[0] - ear[0]) / (WIDTH / 2))) * PAN_WIDTH
    return volume, pan


def ambience(app):
    """What loops in each slot now: (bed, volume) and (hum, volume, pan), or None outside the game."""
    state = app["state"]
    if state is None or engine.is_over(state) or app["scene"] in ("ending", "shatter"):
        return None, None
    seen = view(app)
    room = seen["room"]
    info = story.ROOMS[room]
    if info["outdoor"]:
        bed = ("sea", SEA_VOLUME)
    elif info.get("damp"):
        bed = ("drips", DRIPS_VOLUME)
    else:
        bed = ("sea_far", SEA_INSIDE_VOLUME)
    ear = player_rect(listener(app)["pos"]).center
    hum = None
    for thing in engine.things_here(seen):
        if thing["kind"] not in ("switch", "portal"):
            continue
        center = thing_rect(thing["id"]).center
        closeness = 1 - math.hypot(center[0] - ear[0], center[1] - ear[1]) / HUM_RANGE
        if thing["kind"] == "switch" and thing["status"] != "on":
            closeness *= HUM_OFF
        if closeness > 0 and (hum is None or closeness * HUM_VOLUME > hum[1]):
            pan = max(-1.0, min(1.0, (center[0] - ear[0]) / (WIDTH / 2))) * PAN_WIDTH
            hum = ("hum", closeness * HUM_VOLUME, pan)
    return bed, hum


def update_audio(app):
    """Once a frame, on every computer: the loops of the room, the footsteps, the crab."""
    bed, hum = ambience(app)
    sounds.loop("bed", *(bed or (None,)))
    sounds.loop("hum", *(hum or (None,)))
    rain, wind = weather_sounds(app)
    sounds.loop("rain", *(rain or (None,)))
    sounds.loop("wind", *(wind or (None,)))
    sounds.update_loops()
    if app["state"] is not None:
        footsteps(app)
        crab_audio(app)


def step_sound(seen, player):
    """The sound of a footstep: a splash in a puddle, else the floor of the room."""
    feet = player_rect(player["pos"]).midbottom
    for thing in engine.things_here(seen):
        if story.OBJECTS.get(thing["id"], {}).get("picture") == "decor_puddle" \
                and thing_rect(thing["id"]).inflate(0, 2).collidepoint(feet[0], feet[1] - 1):
            return "step_puddle"
    return "step_" + story.ROOMS[seen["room"]]["floor"]


def footsteps(app):
    """A footstep at each step of the walk of a player in the room on screen: the one on this
    computer in the middle, the other one from where they are."""
    state = app["state"]
    seen = view(app)
    for number, player in enumerate(app["players"], start=1):
        step = player["walk"] // WALK_STEP_FRAMES
        last = app["steps"].get(number)
        app["steps"][number] = step
        if last is None or step == last or not player["moving"] or player["dash"] > 0:
            continue
        if engine.player_room(state, number) != seen["room"] or engine.is_out(state, number):
            continue
        volume, pan = (1.0, 0.0) if player is listener(app) else hearing(app, player_rect(player["pos"]).center)
        sounds.play(step_sound(seen, player), volume * STEP_VOLUME, pan)


def door_between(state, room, other):
    """The open door of `room` that leads to `other`, or None."""
    for door in doors_in(room):
        if story.DOORS[door]["to"] == other and engine.door_status(state, door) == "open":
            return door
    return None


def crab_audio(app):
    """The crab's claws clicking as it walks: in the room, from where it is, louder and faster
    as it comes near (a hiss when it charges); in the next room, muffled, from the door."""
    crab = app["crab"]
    if crab is None or not crab["moving"] or crab["away"] > 0:
        app["charging"] = False
        return
    seen = view(app)
    if crab["room"] == seen["room"]:
        body = crab_rect(crab).center
        ear = player_rect(listener(app)["pos"]).center
        charging = math.hypot(body[0] - ear[0], body[1] - ear[1]) < CHARGE_DISTANCE
        volume, pan = hearing(app, body)
        if app["frame"] % (CHARGE_CLICK_EVERY if charging else CLAW_CLICK_EVERY) == 0:
            sounds.play("claw_click", min(1.0, volume * CRAB_VOLUME * (1.25 if charging else 1.0)), pan)
        if charging and not app["charging"] and app["frame"] - app["charge_at"] >= CHARGE_PAUSE:
            sounds.play("crab_charge", volume * CRAB_VOLUME, pan)
            app["charge_at"] = app["frame"]
        app["charging"] = charging
        return
    app["charging"] = False
    door = door_between(app["state"], seen["room"], crab["room"])
    if door is not None and app["frame"] % CLAW_CLICK_EVERY == 0:
        _, pan = hearing(app, door_rect(door).center)
        sounds.play("claw_click_far", NEXT_ROOM_VOLUME, pan)


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
    before, after = engine.seen_by(before, my_number(app)), engine.seen_by(after, my_number(app))  # in this room
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
            x, y = player_rect(local_player(app)["pos"]).center
        effects.spawn(fx, x, y, effects.MISTAKE_SPARKS, effects.RED, speed=1.8, life=24, gravity=0.05)


def show_new_clue(app, action):
    """A clue was just found: the chime, and a glow with twinkles on the thing that gave it."""
    sounds.play("clue")
    target = action.get("target")
    if not effects.FX["clues"] or target not in story.OBJECTS and target not in story.ITEMS:
        return
    rect = item_rect(view(app), target) if target in story.ITEMS else thing_rect(target)
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
    if app["state"] is None:
        effects.update(fx)
        return
    state = view(app)
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
            elif thing["kind"] == "anvil" and effects.FX["anvil"] and not engine.key_fused(state):
                if frame % ANVIL_SPARK_EVERY == 0:  # red sparks: this is where the key is made whole
                    effects.spawn(fx, rng.uniform(rect.left - 8, rect.right + 8), rng.uniform(rect.top - 4, rect.bottom + 4),
                                  1, effects.RED, speed=0.7, life=40, up=0.6)
            elif story.OBJECTS.get(thing["id"], {}).get("picture") == "decor_stove" and effects.FX["ambient"]:
                if (frame + rect.left) % STEAM_EVERY == 0:  # steam rising from the pot on the stove
                    effects.spawn(fx, rect.centerx + rng.randint(-3, 3), rect.top + 1, 1, STEAM, speed=0.12,
                                  life=55, up=0.32, spread=math.pi / 3, angle=-math.pi / 2)
            elif thing["kind"] == "cauldron" and effects.FX["cauldron"]:
                flags = state["flags"]
                if (flags["potion_step"] or flags["potion_solved"]) and frame % effects.CAULDRON_BUBBLE_EVERY == 0:
                    color = cauldron_color(state)
                    x, y = liquid_center(thing["id"])
                    effects.spawn(fx, x + rng.randint(-4, 4), y, 1, [lighter(color)], speed=0.1, life=36, up=0.35)
        chance = drip_chance(app, room)  # a drop from the ceiling: more of them in the rain
        if effects.FX["ambient"] and chance > 0 and rng.random() < chance:
            ceiling = floor_rect(room)  # a drop from the foot of the back wall, falling onto the floor
            x = rng.randint(ceiling.left + 2, ceiling.right - 3)
            effects.add_drip(fx, x, ceiling.top, ceiling.top + rng.randint(10, 46))
        for fading in fx["fading"]:
            area = fading["rect"]
            for _ in range(effects.BARRIER_SPARKS):
                effects.spawn(fx, rng.uniform(area.left, area.right), rng.uniform(area.top, area.bottom), 1,
                              effects.ENERGY, speed=1.2, life=16)
        if fx["wand_rise"] is not None:
            player = local_player(app)
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
    effects.update_drips(fx)
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


# --- Dark rooms: where the light is ----------------------------------------------------------
#
# effects.py has the tools (a layer of darkness, and holes of light stamped on it).
# Here is what gives light in the game, and how much: lanterns (a glow, and a cone
# down onto the floor that sways with them), crystals, portals, the heart of the mine,
# and the players, each with a glow around them and a cone the way they face.

LANTERN_LIGHT = 30          # radius of the glow of a lantern in a dark room, in pixels
LANTERN_CONE = (48, 34)     # the cone it throws down: how long, and half its angle in degrees
CRYSTAL_LIGHT = (14, 22)    # a crystal's glow, from its dimmest to its brightest
PORTAL_LIGHT = 26
HEART_LIGHT = (9, 12)       # the heart of the mine beats
PLAYER_LIGHT = 22           # the glow around a player...
PLAYER_CONE = (62, 27)      # ...and the cone in front of them: how long, and half its angle
DOWNED_LIGHT = 11           # a player on the floor gives only a little light


def room_darkness(room):
    """How dark a room is, from 0 (fully lit) to 255: story.py says it, and the switch can turn it off."""
    if not effects.FX["darkness"]:
        return 0
    return story.ROOMS[room].get("dark", 0)


def room_lights(app, state, things):
    """Every light in the room shown, as tuples: ("glow", centre, radius) for a round light and
    ("cone", point, angle in degrees, length, half angle) for a cone. In room pixels."""
    frame = app["frame"]
    lights = []
    for thing in things:
        info = story.OBJECTS.get(thing["id"])
        if thing["kind"] == "item":
            if thing["id"] == "heart":  # it beats, and glows a little with each beat
                beat = effects.pulse(frame, 0.12)
                lights.append(("glow", place_rect(thing).center, HEART_LIGHT[0] + round((HEART_LIGHT[1] - HEART_LIGHT[0]) * beat)))
            continue
        if info is None:
            continue
        rect = thing_rect(thing["id"])
        picture = info.get("picture")
        if picture == "decor_lantern":
            angle, sway = lantern_swing(app, thing["id"])
            flame = (rect.centerx + sway, rect.top + 7)
            flicker = 2 if (frame // 5 + rect.top) % 3 == 0 else 0  # the flame jumps now and then
            lights.append(("glow", flame, LANTERN_LIGHT + flicker))
            lights.append(("cone", flame, 90 + round(angle), LANTERN_CONE[0], LANTERN_CONE[1]))
        elif picture == "decor_crystal":
            glow = effects.pulse(frame, 0.045, 0.0, 1.0, rect.left * 0.3 + rect.top)  # in step with its colour
            lights.append(("glow", rect.center, CRYSTAL_LIGHT[0] + round((CRYSTAL_LIGHT[1] - CRYSTAL_LIGHT[0]) * glow)))
        elif info["kind"] == "portal":
            lights.append(("glow", rect.center, PORTAL_LIGHT + ((frame // 20) % 2)))
        elif info["kind"] == "cauldron":
            lights.append(("glow", (rect.centerx, rect.top + 13), effects.FIRE_GLOW + 6))
    for number, player in enumerate(app["players"], start=1):
        if not same_room(app, player) or engine.is_out(app["state"], number):
            continue
        middle = player_rect(player["pos"]).center
        if number in app["downed"]:
            lights.append(("glow", middle, DOWNED_LIGHT))
            continue
        lights.append(("glow", middle, PLAYER_LIGHT))
        fx, fy = player["facing"]
        lights.append(("cone", middle, round(math.degrees(math.atan2(fy, fx))), PLAYER_CONE[0], PLAYER_CONE[1]))
    return lights


def draw_darkness(app, surface, state, things):
    """In a dark room, lay the darkness over the room, with a hole for every light in it."""
    dark = room_darkness(state["room"])
    if dark <= 0:
        return
    layer = effects.darkness(surface.get_size(), dark)
    for light in room_lights(app, state, things):
        if light[0] == "glow":
            effects.punch(layer, effects.light_hole(light[2], dark), light[1])
        else:
            effects.punch(layer, effects.light_cone(light[3], light[4], light[2], dark), light[1])
    surface.blit(layer, (0, 0))


# --- The weather: one storm that grows with the puzzles (see weather.py) -----------------------
#
# The level of the storm follows the puzzles of story.py (the circuits, the floor puzzles and
# the potion puzzles): how many are solved, and how far the player has got in the others. The
# opening bolt is its first sign; the calm lasts until the player walks into the room of a
# puzzle. On the deck the whole storm is seen and heard: the clouds, the wind, the rain, the
# bolts and the puddles. Inside the ship it is the darker light, the flashes through the
# portholes, the rain and the wind muffled by the deck above, the thunder, and the ceiling
# leaking in the heavy rain. The mine is deep in the rock: nothing of the storm reaches it.
# Each computer of a game for two has its own storm, from the same progress.

WEATHER_INSIDE = 0.35        # how much of the weather reaches a room inside the ship
ROOM_WEATHER = {"mine": 0.0}  # rooms where it is different: none at all in the mine
RAIN_VOLUME = 0.5            # the rain on the deck, at its heaviest
WIND_VOLUME = 0.45           # the wind on the deck, at its strongest
WEATHER_INSIDE_VOLUME = 0.6  # rain, wind and thunder heard from inside the ship (muffled, too)
LEAK_FROM = 0.5              # rain heavier than this leaks through the deck into the rooms below
LANTERN_WIND = 1.2           # how much more a lantern on the deck swings in the strongest wind
PUDDLE_SHARE = 0.07          # how many tiles of the deck get a puddle in the rain, of the free ones

_puddles = {}                # room -> the tiles where its puddles form, found once


def puzzle_progress(state):
    """How far the player is with the puzzles: (solved, total, share), where `share` (from 0 to 1)
    is how far the player has got in the puzzle they are furthest on, of those not solved yet.

    A circuit counts the generators turned on since its start; a floor puzzle the tiles lit, phase
    after phase; a potion the ingredients found and poured in. Each one reaches 1 when only its
    last step is left, so the storm is at its worst just before the last puzzle is solved.
    """
    flags = state["flags"]
    solved = 0
    total = 0
    share = 0.0
    for circuit in story.CIRCUITS.values():
        total += 1
        if flags[circuit["solved_flag"]]:
            solved += 1
            continue
        on_at_start = 0
        on_now = 0
        for switch in circuit["switches"]:
            if story.FLAGS[switch]:
                on_at_start += 1
            if flags[switch]:
                on_now += 1
        left = len(circuit["switches"]) - 1 - on_at_start  # the last generator solves it
        if left > 0:
            share = max(share, (on_now - on_at_start) / left)
    for puzzle in story.FLOOR_PUZZLES.values():
        total += 1
        if flags[puzzle["solved_flag"]]:
            solved += 1
            continue
        steps = 0
        done = flags[puzzle["step_flag"]]
        for number, phase in enumerate(puzzle["phases"], start=1):
            steps += len(phase["steps"])
            if number < flags[puzzle["phase_flag"]]:
                done += len(phase["steps"])  # the phases already played
        if steps > 1:
            share = max(share, done / (steps - 1))
    for potion in story.POTION_PUZZLES.values():
        total += 1
        if flags[potion["solved_flag"]]:
            solved += 1
            continue
        found = 0
        for item in potion["recipe"]:
            if engine.has_item(state, item) or flags["dropped_" + item] is not None:
                found += 1
        units = 2 * len(potion["recipe"])  # each ingredient is found, then poured in
        share = max(share, (found + flags[potion["step_flag"]]) / (units - 1))
    return solved, total, max(0.0, min(1.0, share))


def puzzle_rooms():
    """The rooms where the puzzles are: walking into one of them, the storm begins to come."""
    rooms = []
    for table in (story.CIRCUITS, story.FLOOR_PUZZLES, story.POTION_PUZZLES):
        for puzzle in table.values():
            rooms.append(puzzle["room"])
    return rooms


def storm_target(state):
    """Where the progress of the player puts the storm, from 0 (the calm) to 1 (its worst)."""
    solved, total, share = puzzle_progress(state)
    started = False
    for room in puzzle_rooms():
        if state["flags"].get("visited_" + room):
            started = True
    return weather.storm_level(solved, total, share, started)


def weather_exposure(room):
    """How much of the weather reaches a room: all of it on the deck, less inside the ship."""
    if story.ROOMS[room]["outdoor"]:
        return 1.0
    return ROOM_WEATHER.get(room, WEATHER_INSIDE)


def thunder_shake(room):
    """How many pixels the strongest thunder shakes the room at most: more on the deck, none in the mine."""
    exposure = weather_exposure(room)
    if exposure <= 0:
        return 0
    return weather.SHAKE_POWER if exposure >= 1 else 1


def deck_sky():
    """Where the seagulls fly: the whole outdoor room (the deck and the sea around it), in pixels
    of the room. None if no room is outdoors."""
    for room, info in story.ROOMS.items():
        if info["outdoor"]:
            columns, rows = room_size(room)
            return tile_rect(0, 0, columns, rows)
    return None


def update_weather(app):
    """Once a frame: the storm moves toward where the progress puts it, and its thunder is heard.
    Outside a game the weather goes back to the calm, ready for the next one."""
    if not effects.FX["weather"]:
        return
    storm = app["weather"]
    state = app["state"]
    if state is None:
        if not storm["fresh"]:
            weather.reset(storm)
        weather.update(storm, VIEW.size, deck_sky())  # the sea of the title screen still moves
        return
    weather.set_goal(storm, storm_target(state))
    thunder = weather.update(storm, VIEW.size, deck_sky())
    if thunder is None or engine.is_over(state) or app["scene"] in ("ending", "shatter"):
        return
    room = view(app)["room"]
    if weather_exposure(room) <= 0:
        return
    if story.ROOMS[room]["outdoor"]:
        sounds.play(thunder["name"], thunder["volume"])
    else:
        sounds.play("thunder_inside", thunder["volume"] * WEATHER_INSIDE_VOLUME)


def weather_sounds(app):
    """What the rain and the wind loop now: (name, volume) each, or None."""
    state = app["state"]
    if not effects.FX["weather"] or state is None or engine.is_over(state) or app["scene"] in ("ending", "shatter"):
        return None, None
    room = view(app)["room"]
    if weather_exposure(room) <= 0:
        return None, None
    storm = app["weather"]
    rain = weather.rain_amount(storm["level"]) * RAIN_VOLUME
    wind = min(1.0, storm["wind"]) * WIND_VOLUME
    if story.ROOMS[room]["outdoor"]:
        return ("rain", rain) if rain > 0 else None, ("wind", wind)
    rain *= WEATHER_INSIDE_VOLUME
    wind *= WEATHER_INSIDE_VOLUME
    return ("rain_far", rain) if rain > 0 else None, ("wind_far", wind)


def draw_weather(app, screen, room, corner):
    """The storm over the part of the room on screen (`corner` is where the camera looks)."""
    if not effects.FX["weather"] or app["state"] is None:
        return
    columns, rows = room_size(room)
    area = pygame.Rect(-corner[0], HUD_HEIGHT - corner[1], columns * TILE, rows * TILE).clip(VIEW)
    outdoor = story.ROOMS[room]["outdoor"]
    weather.draw(screen, area, app["weather"], outdoor, weather_exposure(room), corner)


def drip_chance(app, room):
    """How likely a drop is to fall from the ceiling in this frame: in the damp rooms, more so in
    the rain; in the other rooms inside the ship, only once the rain is heavy enough to leak in."""
    damp = story.ROOMS[room].get("damp")
    usual = 1 / DRIP_EVERY if damp else 0.0
    if not effects.FX["weather"] or story.ROOMS[room]["outdoor"] or weather_exposure(room) <= 0:
        return usual
    rain = weather.rain_amount(app["weather"]["level"])
    if damp:
        return (1 + 2 * rain) / DRIP_EVERY
    if rain > LEAK_FROM:
        return (rain - LEAK_FROM) / DRIP_EVERY
    return 0.0


def lantern_wind(app, lantern):
    """How much more a lantern swings: in the wind on the deck, more as it blows harder."""
    if not effects.FX["weather"] or not story.ROOMS[story.OBJECTS[lantern]["room"]]["outdoor"]:
        return 1.0
    return 1 + LANTERN_WIND * app["weather"]["wind"]


def puddle_spots(room):
    """The tiles of a room where puddles form in the rain: a few free tiles of its floor, never
    under a thing, an item or in a doorway. Always the same ones."""
    if room not in _puddles:
        taken = [door_rect(door) for door in doors_in(room)]
        for name, info in story.OBJECTS.items():
            if info["room"] == room:
                taken.append(thing_rect(name))
        for name, info in story.ITEMS.items():
            if info["room"] == room:
                taken.append(thing_rect(name))
        spots = []
        columns, rows = room_size(room)
        for col in range(1, columns - 1):
            for row in range(1, rows - 1):
                tile = tile_rect(col, row)
                if scenery.hash01(col, row, 41) < PUDDLE_SHARE and tile.collidelist(taken) == -1:
                    spots.append(tile)
        _puddles[room] = spots
    return _puddles[room]


def toggle_soft_flashes(app):
    """F10: soft lightning (pale flashes, one flicker, no shaking), or back to the full storm."""
    storm = app["weather"]
    storm["soft"] = not storm["soft"]
    show_banner(app, story.MESSAGES["soft_flashes_on" if storm["soft"] else "soft_flashes_off"])


# --- Atmosphere: the colour of the light, and soft lights -----------------------------------
#
# Every room has the colour of its light, multiplied into it (effects.lightmap): cold and
# stormy on the deck, warm wood in the cabin, amber in the galley, violet in the infirmary
# and wherever a portal is. Around a fire or a lit generator the light turns warmer, around
# a portal or a crystal more violet. Then soft lights are added around what shines: lanterns,
# candles, crystals, stoves, portals, lit generators, and the light coming in through an
# open door. All of it stays pale: a room is never darker than READABLE, so every detail can
# still be seen (the dark rooms have their darkness for that).

READABLE = 200   # the darkest the light of a room may make anything, in brightness (0 to 255)
ROOM_AMBIENT = {
    "deck": (214, 224, 246),          # a storm: cold and grey-blue
    "cabin": (250, 240, 222),         # warm wood
    "galley": (252, 236, 212),        # amber, from the stoves
    "helm": (236, 232, 248),          # fog, and the violet of the ring
    "east_room": (238, 238, 244),
    "hold": (220, 226, 240),          # cool and damp
    "infirmary": (236, 226, 250),     # pale, a little spectral
    "crab_room": (216, 236, 236),     # the green of the sea
    "angel_room": (246, 242, 252),    # a pale, holy light
    "corridor": (222, 226, 240),
    "corridor_end": (236, 228, 248),  # the portal
    "mine": (244, 234, 220),          # earth
}
DEFAULT_AMBIENT = (240, 240, 240)
# What changes the colour of the light around it: (radius, tint), found by its picture or kind.
LOCAL_TINTS = {
    "decor_stove": (44, (255, 232, 198)),
    "decor_lantern": (34, (255, 234, 200)),
    "decor_candle": (22, (255, 232, 194)),
    "decor_crystal": (30, (238, 218, 255)),
    "portal": (52, (234, 214, 255)),
    "cauldron": (36, (204, 228, 255)),
    "switch_on": (30, (255, 232, 190)),
}
# What shines, softly: (radius, colour, how it changes: "flame", "pulse" or "steady").
SOFT_LIGHTS = {
    "decor_stove": (18, (60, 34, 10), "flame"),
    "decor_lantern": (22, (40, 30, 12), "flame"),
    "decor_candle": (12, (46, 34, 14), "flame"),
    "decor_crystal": (16, (54, 26, 78), "pulse"),
    "portal": (26, (38, 18, 58), "pulse"),
    "switch_on": (10, (40, 32, 8), "steady"),
}
DOOR_LIGHT = 18                  # the light that comes in through an open door: its radius...
DOOR_LIGHT_OUTSIDE = (24, 30, 44)  # ...cold from the storm outside
DOOR_LIGHT_INSIDE = (36, 28, 14)   # ...warm from another room
STORM_EVERY = 470                # frames between two flashes of distant lightning on the deck
STORM_FLASH = (12, 16, 26)       # added to the deck while it lasts
STORM_FRAMES = (0, 1, 4, 5)      # a flash in two flickers


def light_kind(thing):
    """What a thing is, for the light: its picture, "portal", "cauldron" or "switch_on" (a lit generator)."""
    if thing["kind"] == "switch":
        return "switch_on" if thing["status"] == "on" else None
    if thing["kind"] in ("portal", "cauldron"):
        return thing["kind"]
    return story.OBJECTS.get(thing["id"], {}).get("picture")


def light_center(app, thing):
    """Where the light of a thing comes from: the flame of a lantern (which swings), else its middle."""
    rect = thing_rect(thing["id"])
    if light_kind(thing) == "decor_lantern":
        return (rect.centerx + lantern_swing(app, thing["id"])[1], rect.top + 7)
    if light_kind(thing) == "decor_candle":
        return (rect.left + 7, rect.top + 2)
    return rect.center


def ambient_of(room):
    return ROOM_AMBIENT.get(room, DEFAULT_AMBIENT)


def draw_atmosphere(app, surface, state, things):
    """Multiply the room by the colour of its light, warmer or more violet around some things;
    on the deck, now and then, distant lightning brightens everything for an instant (when the
    storm of weather.py is off: otherwise its lightning does that)."""
    if not effects.FX["atmosphere"]:
        return
    room = state["room"]
    layer = effects.lightmap(surface.get_size(), ambient_of(room))
    for thing in things:
        tint = LOCAL_TINTS.get(light_kind(thing))
        if tint is not None:
            effects.tint(layer, light_center(app, thing), tint[0], tint[1])
    surface.blit(layer, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    if not effects.FX["weather"] and story.ROOMS[room]["outdoor"] and app["frame"] % STORM_EVERY in STORM_FRAMES:
        surface.fill(STORM_FLASH, special_flags=pygame.BLEND_RGB_ADD)


def light_strength(app, thing, change):
    """How bright a light is in this frame: a flame jumps, a crystal or a portal pulses slowly."""
    rect = thing_rect(thing["id"])
    if change == "flame":
        return 0.75 + 0.25 * scenery.hash01(app["frame"] // 4, rect.left * 31 + rect.top, 9)
    if change == "pulse":
        return effects.pulse(app["frame"], 0.05, 0.55, 1.0, rect.left * 0.3 + rect.top)
    return 1.0


def door_light(state, door):
    """Where the light of an open door falls, just inside the room, and its colour (cold from the deck)."""
    opening = door_rect(door)
    dx, dy = TOWARD[story.DOORS[door]["side"]]
    center = (opening.centerx - dx * (opening.width // 2 + 6), opening.centery - dy * (opening.height // 2 + 6))
    outside = story.ROOMS[story.DOORS[door]["to"]]["outdoor"]
    return center, DOOR_LIGHT_OUTSIDE if outside else DOOR_LIGHT_INSIDE


def draw_soft_lights(app, surface, state, things):
    """The soft lights of the room, added on top: around what shines, and through the open doors."""
    if not effects.FX["atmosphere"]:
        return
    for thing in things:
        if thing["kind"] == "door":
            if thing["status"] == "open" and not story.ROOMS[state["room"]]["outdoor"]:
                center, color = door_light(state, thing["id"])
                effects.soft_light(surface, center, DOOR_LIGHT, color)
            continue
        light = SOFT_LIGHTS.get(light_kind(thing))
        if light is not None:
            radius, color, change = light
            effects.soft_light(surface, light_center(app, thing), radius, color, light_strength(app, thing, change))


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
    angle = effects.LANTERN_SWING * lantern_wind(app, lantern) * math.sin(app["frame"] * 0.05 + rect.left * 0.13)
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
    """Which picture of the moving tiles (the stormy sea) to show now: faster as the storm grows."""
    if effects.FX["weather"]:
        return weather.wave_frame(app["weather"], WAVE_FRAMES, SEA_PICTURES)
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
    if app["notice"]:  # why the last game for two ended
        draw_text(screen, font, app["notice"], COLORS["highlight"], (WIDTH // 2, 84), "center", True)


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
            if effects.FX["scenery"] and is_furniture(thing, name):
                return scenery.shaded(name, picture)  # light on the top left, a coloured outline
            return picture
    return None


UNSHADED = ("decor_puddle", "decor_rails", "decor_notes", "portal")  # flat on the floor or on a wall: no volume


def is_furniture(thing, name):
    """True for the furniture and the machines of the rooms: what gets shaded like a solid thing."""
    if name in UNSHADED:
        return False
    return thing["kind"] in ("decor", "altar", "anvil", "cauldron", "puzzle")


def draw_thing(screen, thing, lift=0):
    """A thing of the room: its sprite, or colored rectangles if it has none. `lift` raises it a little."""
    rect = place_rect(thing).move(0, -lift)
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


# --- How a character stands: its shadow, its breath, its steps -----------------------------
#
# The picture of a character (16 x 24) is taller than its body (the 12 x 12 square that
# bumps into things): it stands with its feet on the body's bottom edge and rises
# above it. The room draws everything that stands from the back to the front by where
# its feet are (see draw_room), so the head of a character covers what is behind it,
# and what stands in front covers the character.

SHADOW_SIZE = (14, 4)        # the oval shadow under the feet of a character: a little wider than them
DOWNED_SHADOW_SIZE = (20, 5)  # ...and under a character lying on the floor
SHADOW_DARKNESS = 90         # how dark it is, from 0 to 255: the floor shows through
BREATH_FRAMES = 80           # a breath, in and out, while a character stands still
BREATH_OUT = 34              # ...of which these frames breathing out: the body sinks one pixel
GHOST_AURA = 11              # the radius of the faint glow around the ghost
_shadows = {}


def shadow_picture(size):
    """A dark oval, see-through: made once for each size."""
    if size not in _shadows:
        picture = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.ellipse(picture, (0, 0, 0, SHADOW_DARKNESS), picture.get_rect())
        _shadows[size] = picture
    return _shadows[size]


def breathing_out(app, player):
    """True while a character standing still breathes out: their body sinks one pixel onto their legs.

    Each player breathes in their own time, so two players standing together do not move together.
    """
    if player["moving"]:
        return False
    return (app["frame"] + 29 * player_number(app, player)) % BREATH_FRAMES >= BREATH_FRAMES - BREATH_OUT


def stride_rise(player):
    """How far a walking character rises (-1 pixel) or not (0): up at every stride, down between them."""
    if not player["moving"]:
        return 0
    return -1 if (player["walk"] // (WALK_STEP_FRAMES // 2)) % 2 == 1 else 0


def draw_character(screen, picture, feet, sink, rise):
    """Draw a character's picture standing at `feet` (the middle of its bottom edge): the legs where
    they are, the rest `sink` pixels lower (breathing out), all of it `rise` pixels higher (a stride)."""
    place = picture.get_rect(midbottom=(feet[0], feet[1] + rise))
    legs = pygame.Rect(0, sprites.LEGS_TOP, picture.get_width(), picture.get_height() - sprites.LEGS_TOP)
    screen.blit(picture, (place.x, place.y + sprites.LEGS_TOP), legs)
    above = pygame.Rect(0, 0, picture.get_width(), sprites.LEGS_TOP)
    screen.blit(picture, (place.x, place.y + sink), above)


def draw_player(app, screen, player):
    body = player_rect(player["pos"])
    number = player_number(app, player)
    picture = player_picture(app, player)
    feet = (body.centerx, body.bottom + 1)
    if picture is not None and number in app["hidden"]:
        picture = picture.copy()
        picture.set_alpha(110)  # hidden from the crab: half there
    if picture is not None and number in app["downed"]:
        shadow = shadow_picture(DOWNED_SHADOW_SIZE)
        screen.blit(shadow, shadow.get_rect(center=(feet[0], feet[1] - 2)))
        lying = pygame.transform.rotate(picture, 90)  # knocked down by the crab: on the floor
        screen.blit(lying, lying.get_rect(midbottom=feet))
        return
    if picture is not None:
        shadow = shadow_picture(SHADOW_SIZE)
        screen.blit(shadow, shadow.get_rect(center=(feet[0], feet[1] - 2)))  # on the floor: it does not bob
        if player_character(app, player) == "ghost" and effects.FX["lights"]:
            effects.glow(screen, (body.centerx, body.bottom - 9), GHOST_AURA, (36, 54, 70),
                         effects.pulse(app["frame"], 0.06, 0.45, 1.0, number))  # its aura
        draw_character(screen, picture, feet, 1 if breathing_out(app, player) else 0, stride_rise(player))
        return
    pygame.draw.rect(screen, COLORS["player"], body)
    fx, fy = player["facing"]
    for side in (-1, 1):
        # Two eyes side by side, on the side the player is looking at.
        eye = pygame.Rect(0, 0, 2, 2)
        eye.center = (body.centerx + fx * 3 + side * 3 * abs(fy), body.centery + fy * 3 + side * 3 * abs(fx))
        pygame.draw.rect(screen, COLORS["black"], eye)


def draw_railing_shadow(screen, room):
    """The shadow the railing casts on the deck, under its top rail and beside its left one."""
    columns, rows = room_size(room)
    rail = tile_rect(1, 1, columns - 2, rows - 2).inflate(4, 4)
    inside = rail.inflate(-4, -4)
    reach = scenery.WALL_SHADOW
    scenery.contact_shadow(screen, pygame.Rect(inside.left, inside.top, inside.width, reach[1]), "top", reach[1])
    scenery.contact_shadow(screen, pygame.Rect(inside.left, inside.top, reach[1] - 1, inside.height), "left",
                           reach[1] - 1)


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
    for puzzle in floor_puzzles_in(view(app)["room"]):
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
    room, pos = engine.item_place(state, item)
    for thing, info in story.OBJECTS.items():
        if info["kind"] in HOLDERS and info["room"] == room and info["pos"] == pos:
            return True
    return False


# What casts a shadow on the floor: whatever stands on it. Not what hangs on a wall
# (lanterns, notes), lies flat (rope, puddles, rails, portals), nor energy (barriers).
HANGING = ("decor_lantern", "decor_notes")


def casts_shadow(thing):
    """True for a thing that stands on the floor of its room."""
    if thing["kind"] in ("door", "tile", "barrier", "portal", "item") or is_flat(thing["id"]):
        return False
    return story.OBJECTS.get(thing["id"], {}).get("picture") not in HANGING


def draw_ground_shadows(screen, things):
    """An oval shadow under each thing standing on the floor, a little to the right (the light
    comes from the top left), drawn before any of them so that none shades another."""
    if not effects.FX["scenery"]:
        return
    for thing in things:
        if casts_shadow(thing):
            rect = thing_rect(thing["id"])
            width = max(rect.width - 2, 6)
            shadow = scenery.ground_shadow(width, 5 if rect.width <= TILE else 7)
            screen.blit(shadow, shadow.get_rect(center=(rect.centerx + 2, rect.bottom - 1)))
        elif thing["kind"] == "item" and thing["status"] == "on_floor":
            rect = place_rect(thing)
            shadow = scenery.ground_shadow(10, 3)
            screen.blit(shadow, shadow.get_rect(center=(rect.centerx + 1, rect.bottom - 2)))


def draw_room(app, screen):
    """The room of the player on this computer, with everything in it, the players who are there and the effects."""
    state = view(app)
    room = state["room"]
    floor_color, wall_color = ROOM_COLORS.get(room, DEFAULT_ROOM_COLORS)
    floor = sprites.image("floor_" + room)
    wall = sprites.image("wall_" + room + "_" + str(wave_frame(app)))
    if wall is None:
        wall = sprites.image("wall_" + room)
    screen.fill(COLORS["black"])
    columns, rows = room_size(room)
    if effects.FX["scenery"] and floor is not None and wall is not None:
        # The floor and the walls with their details and depth: built once for each room (see scenery.py).
        outdoor = story.ROOMS[room]["outdoor"]
        screen.blit(room_backdrop(room, wave_frame(app) if outdoor else 0), tile_rect(0, 0))
        if outdoor:
            draw_railing_shadow(screen, room)
    else:
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
        if effects.FX["weather"]:
            weather.draw_puddles(screen, puddle_spots(room), app["weather"]["level"], app["frame"])
    things = engine.things_here(state)
    if effects.FX["portals"]:
        for thing in things:
            if thing["kind"] == "portal":
                effects.ripple(screen, thing_rect(thing["id"]).inflate(20, 20), app["frame"])  # the floor sways
    draw_floor_puzzles(app, screen, things)
    draw_tile_effects(app, screen, things)
    draw_cables(screen, state, app["frame"])
    draw_ground_shadows(screen, things)
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
    if effects.FX["ambient"]:
        draw_puddle_glint(app, screen, things)
    for thing in things:
        if thing["kind"] == "item":
            draw_thing(screen, thing, ALTAR_LIFT if on_an_altar(state, thing["id"]) else 0)
    # From the back of the room to the front: what stands lower on screen covers the rest.
    # The players go in order of their feet, the lower one in front.
    # The crab goes among them, in a game for two.
    drawn = set()
    here = [player for player in app["players"]
            if same_room(app, player) and not engine.is_out(app["state"], player_number(app, player))]
    if crab_here(app):
        here.append(app["crab"])
    for player in sorted(here, key=lambda one: player_rect(one["pos"]).bottom):
        feet = player_rect(player["pos"]).bottom
        for thing in standing:
            if thing["id"] not in drawn and thing_rect(thing["id"]).bottom <= feet:
                draw_standing(app, screen, thing)
                drawn.add(thing["id"])
        if player is app["crab"]:
            draw_crab(app, screen)
        else:
            draw_player(app, screen, player)
    for player in app["players"]:
        if same_room(app, player):
            draw_downed_bars(app, screen, player)
    draw_petrify(app, screen)
    for thing in standing:
        if thing["id"] not in drawn:
            draw_standing(app, screen, thing)
    draw_afterimages(app, screen)
    draw_beams(app, screen)
    # The effects on top: barriers dissolving, the key welding, particles, dust, and the light.
    for thing in things:
        if thing["kind"] == "anvil" and effects.FX["anvil"] and not engine.key_fused(state):
            # A red glow that beats around the anvil while it waits for the two halves.
            effects.glow(screen, thing_rect(thing["id"]).center, 22, (120, 24, 16),
                         effects.pulse(app["frame"], 0.1, 0.45, 1.0))
    draw_fading_barriers(app, screen)
    draw_fusing_key(app, screen)
    effects.draw_clue_glow(screen, app["fx"])
    effects.draw_particles(screen, app["fx"]["particles"])
    effects.draw_drips(screen, app["fx"])
    effects.draw_dust(screen, app["fx"], app["frame"])
    draw_atmosphere(app, screen, state, things)  # the colour of the light in this room
    draw_darkness(app, screen, state, things)  # a dark room: dark, but for the holes of light
    draw_lights(app, screen, things)
    draw_soft_lights(app, screen, state, things)
    # The letter of each generator, on the floor above it.
    for thing in things:
        if thing["kind"] == "switch":
            rect = thing_rect(thing["id"])
            label = story.OBJECTS[thing["id"]]["label"]
            draw_text(screen, app["fonts"]["text"], label, COLORS["text"], (rect.centerx, rect.top - 10), "center", True)


FLAME_COLORS = ((252, 214, 80), (240, 140, 50), (244, 240, 228))  # yellow, orange, white: a flame


def flicker(app, thing, salt=0):
    """A number from 0 to 1 that jumps every few frames: different for every flame, never random."""
    rect = thing_rect(thing["id"])
    return scenery.hash01(app["frame"] // 4 + salt, rect.left * 31 + rect.top, 5)


def draw_flame(app, surface, thing):
    """The flame of a candle leaps a pixel up and changes colour; the fire in a stove flickers."""
    rect = thing_rect(thing["id"])
    if story.OBJECTS[thing["id"]]["picture"] == "decor_candle":
        tip = (rect.left + 7 + (1 if flicker(app, thing) > 0.5 else 0), rect.top - (1 if flicker(app, thing, 1) > 0.6 else 0))
        surface.fill(FLAME_COLORS[int(flicker(app, thing, 2) * 3) % 3], (tip[0], tip[1], 1, 1))
        return
    for spark in range(3):  # the stove: three pixels of its fire change colour
        x = rect.left + 4 + int(flicker(app, thing, spark) * 8)
        y = rect.top + 9 + int(flicker(app, thing, spark + 7) * 2)
        surface.fill(FLAME_COLORS[int(flicker(app, thing, spark + 3) * 2)], (x, y, 1, 1))


def draw_puddle_glint(app, surface, things):
    """A glint of light runs across each puddle now and then, as if a drop had just fallen in it."""
    for thing in things:
        if story.OBJECTS.get(thing["id"], {}).get("picture") != "decor_puddle":
            continue
        rect = thing_rect(thing["id"])
        phase = (app["frame"] + rect.left * 7) % PUDDLE_GLINT_EVERY
        if phase < 8:
            surface.fill((210, 236, 255), (rect.left + 4 + phase, rect.top + 7, 2, 1))


PUDDLE_GLINT_EVERY = 110


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
    elif story.OBJECTS.get(thing["id"], {}).get("picture") in ("decor_candle", "decor_stove"):
        draw_thing(screen, thing)
        if effects.FX["ambient"]:
            draw_flame(app, screen, thing)
    elif thing["id"] == "deck_statue" and statue_trembles(app):
        draw_trembling_statue(app, screen)  # the crab is breaking out: one more moment
    elif thing["id"] == "deck_statue" and engine.statue_broken(app["state"]):
        rubble = sprites.image("decor_crab_rubble")  # the crab broke out of it: stones and pieces, for good
        if rubble is not None:
            screen.blit(rubble, thing_rect("deck_statue"))
    else:
        draw_thing(screen, thing)


def draw_hud(app, screen):
    """The bar at the top: the room and the inventory key, then what E does here and the items carried.

    The map of the ship takes the top right corner.
    """
    font = app["fonts"]["text"]
    state = app["state"]
    number = my_number(app)
    pygame.draw.rect(screen, COLORS["hud"], (0, 0, WIDTH, HUD_HEIGHT))
    pygame.draw.line(screen, COLORS["dim_text"], (0, HUD_HEIGHT - 1), (WIDTH, HUD_HEIGHT - 1))
    draw_text(screen, font, story.ROOMS[engine.player_room(state, number)]["name"], COLORS["text"], (8, 4))
    right = map_rect().left - 6  # the map takes the right corner: the rest moves left of it
    draw_text(screen, font, story.MESSAGES["hint_inventory"], COLORS["dim_text"], (right, 4), "right")
    if app["scene"] == "play" and not app["dialog"]:
        hint = prompt(state, local_player(app)["pos"], number)
        if hint:
            draw_text(screen, font, hint, COLORS["highlight"], (8, 18))
    x = right + 4
    # 18 pixels for each item; with many items they move closer, so they never reach the hint on the left.
    shown = list(reversed(carried(state, number)))  # the items of the player on this computer
    gap = min(18, max(10, INVENTORY_ROOM // max(len(shown), 1)))
    for item in shown:
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
    """The map of the ship: only the rooms visited so far, the doors out of them, and the players."""
    state = view(app)
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
    for number, player in enumerate(app["players"], start=1):
        if engine.is_out(app["state"], number):
            continue
        x, y = map_dot(engine.player_room(app["state"], number), player["pos"])  # each in their own room
        pygame.draw.rect(screen, COLORS["black"], (x, y, 1, 1))
    crab = app["crab"]
    if crab is not None and crab["away"] == 0 and crab["room"] in visited:
        x, y = map_dot(crab["room"], crab["pos"])
        pygame.draw.rect(screen, COLORS["danger"], (x, y, 1, 1))  # the crab, in red


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
    """Where the camera looks: at the player on this computer (or at the partner, once out of the game)."""
    return app["players"][eye_number(app) - 1]["pos"]


def lightning_path(start, end, seed, steps=14, sway=14):
    """The points of a jagged bolt from `start` to `end`: always the same for the same seed."""
    rng = random.Random(seed)
    points = [start]
    for step in range(1, steps):
        along = step / steps
        x = start[0] + (end[0] - start[0]) * along + rng.uniform(-sway, sway)
        y = start[1] + (end[1] - start[1]) * along
        points.append((round(x), round(y)))
    points.append(end)
    return points


LIGHTNING_BOLT = lightning_path((WIDTH * 5 // 8, 0), (WIDTH * 3 // 8, HEIGHT), seed=7)
LIGHTNING_BRANCH = lightning_path(LIGHTNING_BOLT[6], (WIDTH - 20, HEIGHT * 3 // 4), seed=3, steps=6, sway=8)


def draw_lightning(app, screen):
    """The bolt that tears the screen when a new game starts: a white flash, the bolt from top to
    bottom with a branch, a second flicker, and the dark in between."""
    left = app["lightning"]
    if left <= 0:
        return
    age = LIGHTNING_FRAMES - left
    whole = screen.get_rect()
    shade(screen, whole, 150)  # the storm darkens everything
    struck = age < 22 or 30 <= age < 38  # the bolt, then a second, shorter flicker
    if struck and (age // 2) % 3 != 2:
        for path in (LIGHTNING_BOLT, LIGHTNING_BRANCH):
            pygame.draw.lines(screen, sprites.PALETTE["f"], False, path, 5)
            pygame.draw.lines(screen, COLORS["text"], False, path, 2)
    for start in (0, 30):
        if start <= age < start + 5:  # the flash: white, fading fast
            veil = pygame.Surface(whole.size, pygame.SRCALPHA)
            white = 230 - 45 * (age - start)
            if app["weather"]["soft"]:
                white = round(white * weather.SOFT_FLASH)  # soft lightning (F10): a much paler flash
            veil.fill((255, 255, 255, white))
            screen.blit(veil, (0, 0))


def draw_play_screen(app, screen, overlays=True):
    """The room, seen through the camera, then the bar on top.

    The whole room is drawn on its own surface, in room pixels, so nothing else
    needs to know about the camera: walls, things and the player keep their places.
    Without `overlays` it is the game alone, with no message over it (for the
    picture the giant claw breaks).
    """
    room = view(app)["room"]
    whole = room_surface(room)
    draw_room(app, whole)
    x, y = camera(room, view_position(app))
    screen.fill(COLORS["black"])
    shake_x, shake_y = room_shake(app)  # the ship shakes while the crab statue crumbles
    screen.set_clip(VIEW)
    screen.blit(whole, (-x + shake_x, -y + shake_y))
    screen.set_clip(None)
    draw_weather(app, screen, room, (x, y))  # the storm: over the room, under the bar and the texts
    if app["fade"] > 0:
        # Just through a door: the room comes out of the dark.
        shade(screen, VIEW, 255 * app["fade"] // FADE_FRAMES)
    effects.draw_warp(screen, VIEW, app["fx"])   # just through a portal: the purple warp
    effects.draw_flash(screen, VIEW, app["fx"])  # the white flash of the anvil
    draw_hud(app, screen)
    draw_ability_hint(app, screen)
    if overlays:
        draw_crab_overlay(app, screen)
        draw_lightning(app, screen)


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
    rows = column_rows(app, item_lines(app["state"], app["inventory_player"]), items.width)
    return max(0, len(rows) - visible_rows(app, items))


def scroll_inventory(app, direction):
    """Up or down the list of items, one item at a time: the next item's name goes to the top."""
    _, items = inventory_columns()
    rows = column_rows(app, item_lines(app["state"], app["inventory_player"]), items.width)
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
    rows = column_rows(app, item_lines(app["state"], app["inventory_player"]), items.width)
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


def ending_number_label(ending_id):
    """ "Ending 2 of 3": which ending this is, in the order of story.ENDINGS."""
    number = list(story.ENDINGS).index(ending_id) + 1
    return story.MESSAGES["ending_number"].format(number=number, total=len(story.ENDINGS))


CRAB_RISE_FRAMES = 120  # how long the giant crab takes to rise behind the ship


def draw_crab_ending(app, scene, time):
    """The crab's ending: the storm at night, and a giant crab rising behind the ship, claws open."""
    horizon = ENDING_HORIZON
    scene.fill(COLORS["night"])
    crab = sprites.image("crab")
    if crab is not None:
        big = pygame.transform.scale(crab, (crab.get_width() * 2, crab.get_height() * 2))
        risen = min(time, CRAB_RISE_FRAMES) / CRAB_RISE_FRAMES
        top = horizon + 4 - round(risen * (big.get_height() - 6))
        scene.blit(big, big.get_rect(midtop=(WIDTH // 2, top)))
    draw_sea(app, scene, pygame.Rect(0, horizon, WIDTH, ENDING_SCENE_HEIGHT - horizon))
    ship = sprites.image("ship")
    if ship is not None:
        scene.blit(ship, ship.get_rect(midbottom=(WIDTH // 2, horizon + 6 + bob(app))))


def draw_ending_screen(app, screen):
    ending_id = app["state"]["ending"]
    ending = story.ENDINGS[ending_id]
    font = app["fonts"]["text"]
    screen.fill(COLORS["good_ending"] if ending["good"] else COLORS["bad_ending"])
    # How long the ending has been on screen. Behind a question, show how it ends.
    time = app["scene_frames"] if app["scene"] == "ending" else 10 ** 6
    scene = pygame.Surface((WIDTH, ENDING_SCENE_HEIGHT))
    if ending["scene"] == "rescue":
        draw_rescue(app, scene, time)
        screen.blit(scene, (0, 0))
    elif ending["scene"] == "crab":
        draw_crab_ending(app, scene, time)
        screen.blit(scene, (0, 0))
    else:
        draw_explosion(app, scene, time)
        shake = (0, 0)
        if EXPLOSION_DELAY <= time < EXPLOSION_DELAY + 45:
            shake = ((time * 7) % 5 - 2, (time * 3) % 5 - 2)  # the screen trembles
        screen.blit(scene, shake)
    pygame.draw.line(screen, COLORS["text"], (0, ENDING_SCENE_HEIGHT), (WIDTH, ENDING_SCENE_HEIGHT))
    label = ending_number_label(ending_id)
    draw_text(screen, font, label, COLORS["dim_text"], (WIDTH // 2, ENDING_SCENE_HEIGHT + 6), "center")
    title_position = (WIDTH // 2, ENDING_SCENE_HEIGHT + 18)
    draw_text(screen, app["fonts"]["title"], ending["title"], COLORS["highlight"], title_position, "center", True)
    y = ENDING_SCENE_HEIGHT + 42
    for paragraph in ending["text"]:
        for line in wrap(paragraph, WIDTH - 24, text_width(font)):
            draw_text(screen, font, line, COLORS["text"], (WIDTH // 2, y), "center")
            y += font.get_linesize()


def draw_lines_at_bottom(app, screen, text):
    """A hint at the bottom of a screen over the sea, wrapped to its width."""
    font = app["fonts"]["text"]
    lines = wrap(text, WIDTH - 16, text_width(font))
    for index, line in enumerate(lines):
        y = HEIGHT - 6 - (len(lines) - index) * font.get_linesize()
        draw_text(screen, font, line, COLORS["foam"], (WIDTH // 2, y), "center", True)


def draw_lobby(app, screen):
    """The host waits for the other computer: its address, to type over there."""
    draw_sea(app, screen, screen.get_rect(), calm=True)
    font = app["fonts"]["text"]
    draw_text(screen, app["fonts"]["title"], story.MESSAGES["lobby_title"], COLORS["text"], (WIDTH // 2, 36),
              "center", True)
    address = app["net"]["address"] if app["net"] is not None else ""
    draw_text(screen, font, story.MESSAGES["lobby_address"].format(address=address), COLORS["highlight"],
              (WIDTH // 2, 96), "center", True)
    dots = "." * ((app["frame"] // 20) % 4)  # something moves: the game is waiting, not stuck
    draw_text(screen, font, dots, COLORS["text"], (WIDTH // 2, 112), "center", True)
    if app["lobby"] is not None:
        difficulty = story.DIFFICULTIES[engine.crab_difficulty(app["lobby"][0])]["name"]
        draw_text(screen, font, story.MESSAGES["lobby_difficulty"].format(difficulty=difficulty), COLORS["text"],
                  (WIDTH // 2, 128), "center", True)
    draw_lines_at_bottom(app, screen, story.MESSAGES["lobby_hint"])


def draw_join_screen(app, screen):
    """The address of the host, as it is being typed, and why the last try failed."""
    draw_sea(app, screen, screen.get_rect(), calm=True)
    font = app["fonts"]["text"]
    draw_text(screen, app["fonts"]["title"], story.MESSAGES["join_title"], COLORS["text"], (WIDTH // 2, 36),
              "center", True)
    draw_text(screen, font, story.MESSAGES["join_prompt"], COLORS["text"], (WIDTH // 2, 80), "center", True)
    box = pygame.Rect(WIDTH // 2 - 60, 94, 120, font.get_linesize() + 6)
    draw_box(screen, box)
    draw_text(screen, font, app["join_text"], COLORS["highlight"], (WIDTH // 2, box.top + 3), "center")
    if (app["frame"] // 24) % 2 == 0:  # a blinking bar after the address: the font has no "_"
        width, height = font.size(app["join_text"])
        pygame.draw.rect(screen, COLORS["highlight"], (WIDTH // 2 + width // 2 + 1, box.top + 3 + height - 1, 4, 1))
    if app["join_error"]:
        draw_text(screen, font, app["join_error"], COLORS["foam"], (WIDTH // 2, 124), "center", True)
    draw_lines_at_bottom(app, screen, story.MESSAGES["join_hint"])


CHARACTER_ZOOM = 2   # the characters are shown twice as big on the choice screen
CHARACTER_GAP = 56   # pixels between the middles of two characters
CHOICE_MIDDLE = 82   # where the middle of the characters' frames is, from the top of the screen
CHOICE_TEXT_TOP = 120  # where the name and the ability of the one highlighted start


def draw_character_choice(app, screen):
    """The choice of the character, over the calm sea of the title: the characters side by side,
    the highlighted one in a frame that blinks, with its name and its ability below.

    On the computer that joined a game for two, the character player 1 took is dark and cannot be chosen.
    """
    draw_sea(app, screen, screen.get_rect(), calm=True)
    font = app["fonts"]["text"]
    title = "choose_character"
    if app["net"] is not None:
        title = "choose_character_p1" if is_host(app) else "choose_character_p2"
    draw_text(screen, app["fonts"]["title"], story.MESSAGES[title], COLORS["text"], (WIDTH // 2, 30), "center", True)
    entries = character_entries()
    first = WIDTH // 2 - (len(entries) - 1) * CHARACTER_GAP // 2
    for index, character in enumerate(entries):
        picture = sprites.image(story.CHARACTERS[character]["sprite"] + "_down_0")
        center = (first + index * CHARACTER_GAP, CHOICE_MIDDLE)
        frame = pygame.Rect(0, 0, TILE * CHARACTER_ZOOM + 12, sprites.FIGURE_HEIGHT * CHARACTER_ZOOM + 12)
        frame.center = center
        pygame.draw.rect(screen, COLORS["box"], frame)
        chosen = index == app["menu_index"]
        blink = app["picked"] is None and (app["frame"] // 24) % 2 == 1  # once taken, it stops blinking
        border = COLORS["highlight"] if chosen and not blink else COLORS["dim_text"]
        pygame.draw.rect(screen, border, frame, 2 if chosen else 1)
        if picture is not None:
            big = pygame.transform.scale(picture, (picture.get_width() * CHARACTER_ZOOM, picture.get_height() * CHARACTER_ZOOM))
            screen.blit(big, big.get_rect(center=center))
        if character == app["taken"]:
            shade(screen, frame.inflate(-2, -2), 170)  # taken by the other player
    for index, line in enumerate(character_lines(app, entries[app["menu_index"]])):
        color = COLORS["highlight"] if index == 0 else COLORS["text"]
        draw_text(screen, font, line, color, (WIDTH // 2, CHOICE_TEXT_TOP + index * font.get_linesize()), "center", True)
    hint = story.MESSAGES["choose_waiting"] if app["picked"] is not None else story.MESSAGES["choose_hint"]
    draw_lines_at_bottom(app, screen, hint)


def character_lines(app, character):
    """What the choice screen says about a character: its name, then its ability, wrapped.

    Alone, a last line says that abilities are for a game for two: the character is only a look.
    """
    info = story.CHARACTERS[character]
    font = app["fonts"]["text"]
    lines = [info["name"]] + wrap(info["ability"], WIDTH - 24, text_width(font))
    if not app["two_players"] and app["net"] is None:
        lines += wrap(story.MESSAGES["abilities_for_two"], WIDTH - 24, text_width(font))
    return lines


DIFFICULTY_BOX = (108, 112)   # each of the two frames of the choice of the crab
DIFFICULTY_TOP = 46           # where they start, from the top of the screen
DIFFICULTY_GAP = 12           # the sea between them
DIFFICULTY_BACKS = {"easy": (22, 44, 70), "hard": (54, 14, 20)}  # the inside of each frame: sea, or blood
_portraits = {}


def claw_portrait(fierce, opening):
    """The claw in a frame of the choice of the crab, made once for each way it can be open."""
    key = (fierce, round(opening, 2))
    if key not in _portraits:
        _portraits[key] = claw.portrait((DIFFICULTY_BOX[0] - 8, DIFFICULTY_BOX[1] - 26), fierce, opening)
    return _portraits[key]


def difficulty_boxes():
    """The two frames of the choice of the crab, side by side: difficulty -> rect."""
    left = (WIDTH - 2 * DIFFICULTY_BOX[0] - DIFFICULTY_GAP) // 2
    return {difficulty: pygame.Rect(left + index * (DIFFICULTY_BOX[0] + DIFFICULTY_GAP), DIFFICULTY_TOP,
                                    *DIFFICULTY_BOX)
            for index, difficulty in enumerate(story.DIFFICULTIES)}


def draw_difficulty_choice(app, screen):
    """The choice of the crab of a game for two, over the calm sea of the title: two frames side by
    side, a common crab's claw for the easy one and the red claw of the end for the hard one. The
    highlighted one blinks and slowly opens and shuts its jaws; the other is dark. Under them, what
    the highlighted crab does."""
    draw_sea(app, screen, screen.get_rect(), calm=True)
    font = app["fonts"]["text"]
    draw_text(screen, app["fonts"]["title"], story.MESSAGES["choose_difficulty"], COLORS["text"], (WIDTH // 2, 22),
              "center", True)
    entries = menu_entries(app)
    chosen = entries[app["menu_index"] % len(entries)]
    for difficulty, frame in difficulty_boxes().items():
        here = difficulty == chosen
        pygame.draw.rect(screen, DIFFICULTY_BACKS[difficulty], frame)
        if here and difficulty == "hard" and effects.FX["lights"]:
            effects.glow(screen, (frame.centerx, frame.top + 46), 40, (90, 10, 10),
                         effects.pulse(app["frame"], 0.08, 0.5, 1.0))  # it beats, like blood
        opening = 0.2 + 0.12 * math.sin(app["frame"] * 0.07) if here else 0.2
        picture = claw_portrait(difficulty == "hard", round(opening * 20) / 20)
        screen.blit(picture, picture.get_rect(midtop=(frame.centerx, frame.top + 4)))
        name = story.MESSAGES["menu_" + difficulty]
        draw_text(screen, app["fonts"]["text"], name, COLORS["highlight"] if here else COLORS["dim_text"],
                  (frame.centerx, frame.bottom - 16), "center", True)
        blink = (app["frame"] // 24) % 2 == 1
        border = COLORS["highlight"] if here and not blink else COLORS["dim_text"]
        pygame.draw.rect(screen, border, frame, 2 if here else 1)
        if not here:
            shade(screen, frame.inflate(-2, -2), 130)
    text = story.DIFFICULTIES[chosen]["text"]
    top = DIFFICULTY_TOP + DIFFICULTY_BOX[1] + 8
    for index, line in enumerate(wrap(text, WIDTH - 24, text_width(font))):
        draw_text(screen, font, line, COLORS["text"], (WIDTH // 2, top + index * font.get_linesize()), "center", True)
    draw_lines_at_bottom(app, screen, story.MESSAGES["choose_hint"])


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
    elif scene == "shatter":
        draw_shatter(app, screen)
    elif scene == "character":
        draw_character_choice(app, screen)
    elif scene == "mode":
        draw_mode_choice(app, screen)
    elif scene == "difficulty":
        draw_difficulty_choice(app, screen)
    elif scene == "lobby":
        draw_lobby(app, screen)
    elif scene == "join":
        draw_join_screen(app, screen)
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


FULLSCREEN_KEY = pygame.K_F11
SOFT_FLASHES_KEY = pygame.K_F10  # soft lightning: for players who are bothered by flashing lights


def picture_area(window_size):
    """Where the game is drawn in a window of this size: as big as fits, in whole multiples of the
    small screen (so every pixel stays a sharp square), in the middle, with black around it."""
    width, height = window_size
    zoom = max(1, min(width // WIDTH, height // HEIGHT))
    area = pygame.Rect(0, 0, WIDTH * zoom, HEIGHT * zoom)
    area.center = (width // 2, height // 2)
    return area


def open_window(fullscreen):
    """The window of the game, or the whole screen."""
    if fullscreen:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)  # the size of the desktop
    return pygame.display.set_mode((WIDTH * SCALE, HEIGHT * SCALE))


def show(screen, window):
    """Put the small screen on the window, enlarged with plain scaling: sharp pixels."""
    area = picture_area(window.get_size())
    if area.size == window.get_size():
        pygame.transform.scale(screen, area.size, window)
    else:
        window.fill(COLORS["black"])
        window.blit(pygame.transform.scale(screen, area.size), area)
    pygame.display.flip()


def main():
    pygame.mixer.pre_init(22050, -16, 2, 512)  # the rate the sounds are made at, in stereo, and quick to start
    pygame.init()
    sounds.load()  # silent if the computer has no audio
    fullscreen = False
    window = open_window(fullscreen)
    pygame.display.set_caption(story.MESSAGES["window_title"])
    screen = pygame.Surface((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    app = new_app(load_fonts())
    while app["running"]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                app["running"] = False
            elif event.type == pygame.KEYDOWN and event.key == FULLSCREEN_KEY:
                fullscreen = not fullscreen  # F11: the whole screen, and back to the window
                window = open_window(fullscreen)
            elif event.type == pygame.KEYDOWN and event.key == SOFT_FLASHES_KEY:
                toggle_soft_flashes(app)  # F10: softer lightning, and back
            elif event.type == pygame.KEYDOWN:
                handle_key(app, event.key)
        pressed = pygame.key.get_pressed()
        dx, dy = held_direction(pressed, controls(app)[0])
        update(app, dx, dy, is_held(pressed, controls(app)[0]["act"]))
        draw(app, screen)
        show(screen, window)
        clock.tick(FPS)
    end_network(app)  # the other computer learns at once that this one has gone
    pygame.quit()


if __name__ == "__main__":
    main()
