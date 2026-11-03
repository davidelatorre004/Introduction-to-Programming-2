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

import pygame

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
COLUMNS, ROWS = 16, 12     # a room in tiles, walls included

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
WAVE_FRAMES = FPS // 2     # frames between the two pictures of the sea
BARRIER_FRAMES = 6         # frames between the two pictures of a barrier's energy
FLASH_FRAMES = FPS // 2    # how long the tiles blink red after a mistake, before going dark
FLASH_BLINK = 6            # frames between two blinks
ALTAR_LIFT = 5             # how much higher an item lying on an altar is drawn
ENDING_SCENE_HEIGHT = 64   # the picture at the top of the ending screen
ENDING_HORIZON = 40        # where the sea starts in that picture
ENDING_MENU_TOP = 186
EXPLOSION_DELAY = 12       # frames before the ship blows up in the bad ending

# Where the opening of a door is on each wall: first tile (column, row), then width and height in tiles.
DOOR_OPENINGS = {
    "N": (7, 0, 2, 1),
    "S": (7, ROWS - 1, 2, 1),
    "W": (0, 5, 1, 2),
    "E": (COLUMNS - 1, 5, 1, 2),
}

# The direction to walk in to go through a door on each wall.
TOWARD = {"N": (0, -1), "S": (0, 1), "W": (-1, 0), "E": (1, 0)}

# --- Keys --------------------------------------------------------------------------

UP_KEYS = (pygame.K_UP, pygame.K_w)
DOWN_KEYS = (pygame.K_DOWN, pygame.K_s)
LEFT_KEYS = (pygame.K_LEFT, pygame.K_a)
RIGHT_KEYS = (pygame.K_RIGHT, pygame.K_d)
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_e)

# --- Colors ------------------------------------------------------------------------

COLORS = {
    "black": (12, 12, 20),
    "text": (240, 236, 220),
    "dim_text": (150, 150, 165),
    "highlight": (255, 205, 80),
    "hud": (24, 22, 34),
    "box": (16, 16, 30),
    "sea": (34, 78, 150),
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
HOLDERS = ("altar", "anvil")

# The sound each outcome of a floor puzzle plays (see sounds.py).
EVENT_SOUNDS = {
    "tile_lit": "blip",
    "phase_complete": "ding",
    "tiles_complete": "fanfare",
    "tiles_reset": "buzz",
}

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


def door_rect(door):
    """The opening of a door, in the middle of its wall."""
    col, row, width, height = DOOR_OPENINGS[story.DOORS[door]["side"]]
    return tile_rect(col, row, width, height)


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
    """The solid parts of the walls of a room: the four sides, with a gap where each door is."""
    sides = {
        "N": tile_rect(0, 0, COLUMNS, 1),
        "S": tile_rect(0, ROWS - 1, COLUMNS, 1),
        "W": tile_rect(0, 0, 1, ROWS),
        "E": tile_rect(COLUMNS - 1, 0, 1, ROWS),
    }
    walls = []
    for side, wall in sides.items():
        opening = None
        for door in doors_in(room):
            if story.DOORS[door]["side"] == side:
                opening = door_rect(door)
        if opening is None:
            walls.append(wall)
        elif side == "N" or side == "S":
            walls.append(pygame.Rect(wall.left, wall.top, opening.left - wall.left, wall.height))
            walls.append(pygame.Rect(opening.right, wall.top, wall.right - opening.right, wall.height))
        else:
            walls.append(pygame.Rect(wall.left, wall.top, wall.width, opening.top - wall.top))
            walls.append(pygame.Rect(wall.left, opening.bottom, wall.width, wall.bottom - opening.bottom))
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
    """True for decor lying on the floor, like a coil of rope: the player walks over it."""
    info = story.OBJECTS.get(thing)
    return info is not None and info["kind"] == "decor" and not info["solid"]


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

    The numbered tiles do not count: they are part of the floor, and the feet act on them.
    """
    body = player_rect(position)
    reach = body.inflate(2 * REACH, 2 * REACH)
    nearest = None
    nearest_distance = 0
    for thing in engine.things_here(state):
        if thing["kind"] == "tile":
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
    """What E would act on, and the actions it offers: the nearest thing, or else the room itself."""
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
    lines = []
    if not state["inventory"]:
        lines.append(("text", story.MESSAGES["inventory_empty"]))
    for item in state["inventory"]:
        lines.append(("name", story.ITEMS[item]["name"]))
        lines.append(("text", story.ITEMS[item]["description"]))
    found = engine.clues(state)
    if found:
        lines.append(("heading", story.MESSAGES["clues"]))
        for clue in found:
            lines.append(("text", clue))
    return lines


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


def new_app(fonts):
    """The state of the interface, starting on the main menu."""
    app = {
        "running": True,
        "fonts": fonts,
        "scene": "menu",         # "menu", "confirm", "play", "actions", "inventory", "pause" or "ending"
        "menu_index": 0,         # the highlighted entry of the menu on screen
        "existing": None,        # the saved game found when the main menu opened, or None
        "state": None,           # the game being played (the engine's state), or None in the main menu
        "player": (0, 0),        # top-left corner of the player, in pixels
        "facing": (0, 1),        # the direction the player looks at
        "touching": None,        # the door the player is walking into: enter fires once per contact
        "dialog": [],            # pages of text waiting to be read; the player cannot move meanwhile
        "banner": "",            # room name shown for a moment after entering a room
        "banner_frames": 0,
        "actions": [],           # what the E menu offers (the "actions" scene)
        "actions_title": "",     # the name of the thing the E menu is about
        "question": "",          # what the confirm scene asks
        "confirming": "new_game",  # what "Yes" does: start a new game, or the action waiting for it
        "confirm_back": "menu",  # the scene to go back to if the answer is no
        "frame": 0,              # frames since the game started, for everything that moves on screen
        "scene_frames": 0,       # frames since the current scene started
        "walk": 0,               # frames the player has spent walking, for the walking animation
        "moving": False,         # whether the player moved in the last frame
        "fade": 0,               # frames left before the room is out of the dark
        "on_tile": None,         # the numbered tile the player stood on in the last frame
        "zones": set(),          # the floor puzzles whose zone the player was in, in the last frame
        "flash_frames": 0,       # frames left of the tiles blinking red after a mistake
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


def go_back(app):
    """What Esc does in a menu."""
    scene = app["scene"]
    if scene == "pause" or scene == "actions":
        set_scene(app, "play")
    elif scene == "confirm":
        set_scene(app, app["confirm_back"])
    elif scene == "ending":
        open_main_menu(app)


def progress(app):
    """The game a new game would replace: the one being played, or else the saved one."""
    if app["state"] is not None:
        return app["state"]
    return app["existing"]


def request_new_game(app):
    """Start a new game, but ask first if there is progress to lose."""
    state, outcome = engine.start_new_game(progress(app))
    if outcome["event"] == "needs_confirmation":
        app["question"] = outcome["text"]
        app["confirming"] = "new_game"
        app["confirm_back"] = app["scene"]
        set_scene(app, "confirm", menu_index=1)  # "No" is highlighted: the safe answer
    else:
        begin_game(app, state, outcome["text"])


def confirm_new_game(app):
    """The player said yes: replace the progress with a new game."""
    state, outcome = engine.start_new_game(progress(app), confirmed=True)
    begin_game(app, state, outcome["text"])


def begin_game(app, state, opening_text):
    """Play a brand-new game: put the player at the start, show the opening scene, save at once."""
    app["state"] = state
    app["dialog"] = []
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


def place_at_entry(app):
    app["player"] = spawn_at_entry(app["state"]["room"])
    app["touching"] = None
    settle_on_floor(app)


def place_after_door(app, came_from):
    """Put the player in front of the door that leads back where they came from."""
    room = app["state"]["room"]
    door = return_door(room, came_from)
    if door is None:
        app["player"] = spawn_at_entry(room)
    else:
        app["player"] = spawn_in_front_of(door)
    app["touching"] = None
    settle_on_floor(app)


def settle_on_floor(app):
    """Appearing somewhere is not walking there: where the player appears fires no movement trigger."""
    app["on_tile"] = tile_under(app["state"], app["player"])
    app["zones"] = zones_around(app["state"], app["player"])


def go_through(app, door):
    """The player walks into a door: ask the engine, then change room or explain why not."""
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


def floor_triggers(app):
    """The movement triggers of the room, checked in every frame after the player moves.

    Walking onto a numbered tile steps on it, and walking out of the zone around
    the tiles leaves it. Each one fires once, when it happens: standing still on
    a tile does not step on it again. The engine decides what it means.
    """
    state = app["state"]
    tile = tile_under(state, app["player"])
    zones = zones_around(state, app["player"])
    stepped_on = tile if tile is not None and tile != app["on_tile"] else None
    left = sorted(app["zones"] - zones)
    app["on_tile"] = tile
    app["zones"] = zones
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
    if outcome["event"] == "tiles_reset":
        app["flash_frames"] = FLASH_FRAMES
    if outcome["event"] == "tiles_complete":
        app["banner_frames"] = 0
        say(app, outcome["text"])
    else:
        show_banner(app, outcome["text"])
    app["state"] = state
    save_progress(app)


def interact(app):
    """E: act on the nearest thing, or look around. Several possible actions open a small menu."""
    target, actions = target_and_actions(app["state"], app["player"])
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
    if outcome["event"] == "toggled":
        show_banner(app, outcome["text"])  # a generator clicks: no text box to close every time
    else:
        app["banner_frames"] = 0  # the text box takes over from an older banner
        say(app, outcome["text"])
    if outcome["ok"]:
        app["state"] = state
        save_progress(app)


def handle_key(app, key):
    """React to one key press."""
    scene = app["scene"]
    if scene == "play":
        handle_play_key(app, key)
    elif scene == "inventory":
        if key == pygame.K_i or key == pygame.K_ESCAPE or key in CONFIRM_KEYS:
            set_scene(app, "play")
    else:
        handle_menu_key(app, key)


def handle_play_key(app, key):
    """Keys while playing: E acts (or turns the page of the text box), I opens the inventory, Esc pauses."""
    if key == pygame.K_ESCAPE:
        set_scene(app, "pause")
    elif app["dialog"]:
        if key in CONFIRM_KEYS:
            app["dialog"].pop(0)
    elif key == pygame.K_e:
        interact(app)
    elif key == pygame.K_i:
        set_scene(app, "inventory")


def handle_menu_key(app, key):
    """Keys in a menu: up and down to move, E or Enter to choose, Esc to go back."""
    entries = menu_entries(app)
    if key in UP_KEYS:
        app["menu_index"] = (app["menu_index"] - 1) % len(entries)
    elif key in DOWN_KEYS:
        app["menu_index"] = (app["menu_index"] + 1) % len(entries)
    elif key in CONFIRM_KEYS:
        choose(app, entries[app["menu_index"]])
    elif key == pygame.K_ESCAPE:
        go_back(app)


def is_held(pressed, keys):
    for key in keys:
        if pressed[key]:
            return True
    return False


def held_direction(pressed):
    """The direction (dx, dy) that the arrow keys or WASD are pushing, each -1, 0 or 1."""
    dx = 0
    dy = 0
    if is_held(pressed, LEFT_KEYS):
        dx -= 1
    if is_held(pressed, RIGHT_KEYS):
        dx += 1
    if is_held(pressed, UP_KEYS):
        dy -= 1
    if is_held(pressed, DOWN_KEYS):
        dy += 1
    return (dx, dy)


def update(app, dx, dy):
    """Move the game on by one frame. (dx, dy) is the direction held on the keyboard."""
    app["frame"] += 1
    app["scene_frames"] += 1
    app["moving"] = False
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
    if dy != 0:
        app["facing"] = (0, dy)
    elif dx != 0:
        app["facing"] = (dx, 0)
    speed = PLAYER_SPEED
    if dx != 0 and dy != 0:
        speed = PLAYER_SPEED * 0.7071  # the same speed on diagonals
    before = app["player"]
    app["player"] = move(app["player"], dx * speed, dy * speed, solid_rects(app["state"]))
    if app["player"] != before:
        app["moving"] = True
        app["walk"] += 1
    door = door_touched(app["state"]["room"], app["player"], dx, dy)
    if door is None:
        app["touching"] = None
    elif door != app["touching"]:
        app["touching"] = door
        go_through(app, door)
    floor_triggers(app)


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
    """Which of the two frames of the moving tiles (the sea) to show now."""
    return (app["frame"] // WAVE_FRAMES) % 2


def draw_sea(app, screen, area):
    """Fill an area with moving sea."""
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
    draw_sea(app, screen, screen.get_rect())
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


def player_picture(app):
    """The player's sprite for the direction they face, standing (0) or in one of the two walking steps."""
    fx, fy = app["facing"]
    if fy > 0:
        direction = "down"
    elif fy < 0:
        direction = "up"
    else:
        direction = "right"  # left is right, mirrored
    step = 0
    if app["moving"]:
        step = 1 + (app["walk"] // WALK_STEP_FRAMES) % 2
    return sprites.image("player_" + direction + "_" + str(step), flip=fx < 0)


def draw_player(app, screen):
    body = player_rect(app["player"])
    picture = player_picture(app)
    if picture is not None:
        # The sprite is taller than the body: it stands on it, feet on the bottom edge.
        screen.blit(picture, picture.get_rect(midbottom=(body.centerx, body.bottom + 1)))
        return
    pygame.draw.rect(screen, COLORS["player"], body)
    fx, fy = app["facing"]
    for side in (-1, 1):
        # Two eyes side by side, on the side the player is looking at.
        eye = pygame.Rect(0, 0, 2, 2)
        eye.center = (body.centerx + fx * 3 + side * 3 * abs(fy), body.centery + fy * 3 + side * 3 * abs(fx))
        pygame.draw.rect(screen, COLORS["black"], eye)


def draw_railing(screen):
    """The ship's wooden railing around the deck, with a post on every tile."""
    rail = tile_rect(1, 1, COLUMNS - 2, ROWS - 2).inflate(4, 4)
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


def draw_cables(screen, state):
    """The cables between the generators of the room, along the sides of their square.

    A cable joins two generators that switch each other over, and lights up when both are on.
    """
    for switch, info in story.OBJECTS.items():
        if info["kind"] != "switch" or info["room"] != state["room"]:
            continue
        for flag in info["toggles"]:
            other = switch_of_flag(flag)
            if other is None or other <= switch:
                continue  # itself, or a cable already drawn from the other end
            lit = state["flags"][info["flag"]] and state["flags"][flag]
            color = COLORS["highlight"] if lit else COLORS["cable"]
            pygame.draw.line(screen, color, thing_rect(switch).center, thing_rect(other).center, 2)


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
    for col in range(COLUMNS):
        for row in range(ROWS):
            inside = 1 <= col <= COLUMNS - 2 and 1 <= row <= ROWS - 2
            picture = floor if inside else wall
            if picture is None:
                pygame.draw.rect(screen, floor_color if inside else wall_color, tile_rect(col, row))
            else:
                screen.blit(picture, tile_rect(col, row))
    if story.ROOMS[room]["outdoor"]:
        draw_railing(screen)
    things = engine.things_here(state)
    draw_floor_puzzles(app, screen, things)
    draw_cables(screen, state)
    standing = []
    for thing in things:
        if thing["kind"] == "door":
            draw_door(screen, thing["id"], thing["status"])
        elif thing["kind"] in HOLDERS or is_flat(thing["id"]):
            draw_thing(screen, thing)  # low furniture and flat decor, drawn before what lies on it
        elif thing["kind"] not in ("item", "tile"):
            standing.append(thing)
    for thing in things:
        if thing["kind"] == "item":
            draw_thing(screen, thing, ALTAR_LIFT if on_an_altar(state, thing["id"]) else 0)
    # From the back of the room to the front: what stands lower on screen covers the rest.
    feet = player_rect(app["player"]).bottom
    for thing in standing:
        if thing_rect(thing["id"]).bottom <= feet:
            draw_standing(app, screen, thing)
    draw_player(app, screen)
    for thing in standing:
        if thing_rect(thing["id"]).bottom > feet:
            draw_standing(app, screen, thing)
    # The letter of each generator, on the floor above it.
    for thing in things:
        if thing["kind"] == "switch":
            rect = thing_rect(thing["id"])
            label = story.OBJECTS[thing["id"]]["label"]
            draw_text(screen, app["fonts"]["text"], label, COLORS["text"], (rect.centerx, rect.top - 10), "center", True)


def draw_standing(app, screen, thing):
    """A puzzle, character, switch or barrier: the barrier has its own way of being drawn."""
    if thing["kind"] == "barrier":
        draw_barrier(app, screen, thing)
    else:
        draw_thing(screen, thing)


def draw_hud(app, screen):
    """The bar at the top: the room and the inventory key, then what E does here and the items carried."""
    font = app["fonts"]["text"]
    state = app["state"]
    pygame.draw.rect(screen, COLORS["hud"], (0, 0, WIDTH, HUD_HEIGHT))
    pygame.draw.line(screen, COLORS["dim_text"], (0, HUD_HEIGHT - 1), (WIDTH, HUD_HEIGHT - 1))
    draw_text(screen, font, story.ROOMS[state["room"]]["name"], COLORS["text"], (8, 4))
    draw_text(screen, font, story.MESSAGES["hint_inventory"], COLORS["dim_text"], (WIDTH - 8, 4), "right")
    if app["scene"] == "play" and not app["dialog"]:
        hint = prompt(state, app["player"])
        if hint:
            draw_text(screen, font, hint, COLORS["highlight"], (8, 18))
    x = WIDTH - 4
    for item in reversed(state["inventory"]):
        x -= 18
        picture = sprites.image(item)
        if picture is None:
            pygame.draw.rect(screen, THING_COLORS.get(item, MISSING_COLOR), (x + 4, 19, 8, 8))
        else:
            screen.blit(picture, (x, 14))


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


def draw_play_screen(app, screen):
    draw_room(app, screen)
    if app["fade"] > 0:
        # Just through a door: the room comes out of the dark.
        shade(screen, tile_rect(0, 0, COLUMNS, ROWS), 255 * app["fade"] // FADE_FRAMES)
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


def draw_inventory(app, screen):
    """The inventory screen: the items carried, what they look like, and the clues found."""
    font = app["fonts"]["text"]
    colors = {"name": COLORS["highlight"], "text": COLORS["text"], "heading": COLORS["dim_text"]}
    box = pygame.Rect(16, HUD_HEIGHT + 8, WIDTH - 32, HEIGHT - HUD_HEIGHT - 24)
    draw_box(screen, box)
    draw_text(screen, font, story.MESSAGES["inventory"], COLORS["dim_text"], (WIDTH // 2, box.top + 8), "center")
    y = box.top + 24
    for style, text in inventory_lines(app["state"]):
        if style != "text":
            y += 4  # a little space before each item and before the clues
        for line in wrap(text, box.width - 20, text_width(font)):
            draw_text(screen, font, line, colors[style], (box.left + 10, y))
            y += font.get_linesize()
    draw_text(screen, font, story.MESSAGES["close_hint"], COLORS["dim_text"], (WIDTH // 2, box.bottom - 18), "center")


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
    draw_sea(app, scene, pygame.Rect(0, horizon, WIDTH, ENDING_SCENE_HEIGHT - horizon))
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
    if blast < 16:
        flash = pygame.Surface(scene.get_size(), pygame.SRCALPHA)
        flash.fill((255, 255, 255, 255 - blast * 16))  # the blast lights everything up
        scene.blit(flash, (0, 0))


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
        dx, dy = held_direction(pygame.key.get_pressed())
        update(app, dx, dy)
        draw(app, screen)
        pygame.transform.scale(screen, window.get_size(), window)  # plain scaling: sharp pixels
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    main()


