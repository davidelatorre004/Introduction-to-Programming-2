"""Plot Twist on screen: the window, the menus, the rooms and the player.

Run it with:  uv run python main.py

Everything is drawn on a small 256 x 224 screen, then blown up three times
without smoothing, which gives the 8-bit look. Until the sprites arrive (M6),
everything is a colored rectangle.

The rules are not here: main.py asks engine.py what happens, and saves through
save.py after every accepted action. The interface keeps its own small state in
a dict called `app`: which scene is showing, where the player stands, what the
text box says. The game itself is app["state"], the engine's state.
"""

import pygame

import engine
import save
import story

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
BANNER_FRAMES = 2 * FPS    # how long the room name stays up after entering a room
DIALOG_LINES = 4           # lines of text per page of the text box
DIALOG_PADDING = 8
DIALOG_TEXT_WIDTH = WIDTH - 4 * DIALOG_PADDING  # margin and padding on both sides of the box

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
}

# Floor and wall color of each room.
ROOM_COLORS = {
    "deck": ((165, 115, 65), COLORS["sea"]),
    "cabin": ((120, 80, 50), (70, 45, 30)),
    "hold": ((70, 60, 55), (40, 32, 30)),
    "crab_room": ((60, 110, 110), (30, 60, 65)),
    "angel_room": ((225, 220, 200), (170, 165, 150)),
}
DEFAULT_ROOM_COLORS = ((100, 100, 100), (50, 50, 50))

# The color of each item, puzzle and character. An id missing here is drawn in
# magenta, so something new in story.py shows up even before it has a color.
THING_COLORS = {
    "wand": (180, 110, 255),
    "key": (250, 210, 70),
    "cabin_puzzle": (150, 100, 55),
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
    """The tile of an item, a puzzle or a character."""
    if thing in story.ITEMS:
        col, row = story.ITEMS[thing]["pos"]
    else:
        col, row = story.OBJECTS[thing]["pos"]
    return tile_rect(col, row)


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
    """Everything the player cannot walk through right now: walls, closed doors, puzzles and characters.

    Items on the floor are not solid: the player can walk over them.
    """
    solids = wall_rects(state["room"])
    for thing in engine.things_here(state):
        if thing["kind"] == "door":
            if thing["status"] != "open":
                solids.append(door_rect(thing["id"]))
        elif thing["kind"] != "item":
            solids.append(thing_rect(thing["id"]))
    return solids


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
        "scene": "menu",         # "menu", "confirm", "play", "pause" or "ending"
        "menu_index": 0,         # the highlighted entry of the menu on screen
        "existing": None,        # the saved game found when the main menu opened, or None
        "state": None,           # the game being played (the engine's state), or None in the main menu
        "player": (0, 0),        # top-left corner of the player, in pixels
        "facing": (0, 1),        # the direction the player looks at
        "touching": None,        # the door the player is walking into: enter fires once per contact
        "dialog": [],            # pages of text waiting to be read; the player cannot move meanwhile
        "banner": "",            # room name shown for a moment after entering a room
        "banner_frames": 0,
        "question": "",          # what the confirm scene asks
        "confirm_back": "menu",  # the scene to go back to if the answer is no
    }
    open_main_menu(app)
    return app


def set_scene(app, scene, menu_index=0):
    app["scene"] = scene
    app["menu_index"] = menu_index


def open_main_menu(app):
    """Show the main menu. "Riprendi" is offered only if the save file holds a valid game."""
    app["state"] = None
    app["existing"] = engine.restore_state(save.load_game())
    app["dialog"] = []
    app["banner_frames"] = 0
    set_scene(app, "menu")


def menu_entries(app):
    """The entries of the menu showing in the current scene."""
    scene = app["scene"]
    if scene == "menu":
        return engine.menu_options(app["existing"]) + ["quit"]
    if scene == "pause":
        return ["continue", "restart", "main_menu", "quit"]
    if scene == "confirm":
        return ["yes", "no"]
    if scene == "ending":
        return ["new_game", "main_menu"]
    return []


def choose(app, entry):
    """Do what a menu entry says."""
    if entry == "new_game" or entry == "restart":
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
        confirm_new_game(app)
    elif entry == "no":
        set_scene(app, app["confirm_back"])


def go_back(app):
    """What Esc does in a menu."""
    scene = app["scene"]
    if scene == "pause":
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


def place_after_door(app, came_from):
    """Put the player in front of the door that leads back where they came from."""
    room = app["state"]["room"]
    door = return_door(room, came_from)
    if door is None:
        app["player"] = spawn_at_entry(room)
    else:
        app["player"] = spawn_in_front_of(door)
    app["touching"] = None


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
    show_banner(app, outcome["text"])


def handle_key(app, key):
    """React to one key press."""
    if app["scene"] == "play":
        if key == pygame.K_ESCAPE:
            set_scene(app, "pause")
        elif key in CONFIRM_KEYS and app["dialog"]:
            app["dialog"].pop(0)
        return
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
    if app["banner_frames"] > 0:
        app["banner_frames"] -= 1
    if app["scene"] != "play" or app["dialog"]:
        return
    if dy != 0:
        app["facing"] = (0, dy)
    elif dx != 0:
        app["facing"] = (dx, 0)
    speed = PLAYER_SPEED
    if dx != 0 and dy != 0:
        speed = PLAYER_SPEED * 0.7071  # the same speed on diagonals
    app["player"] = move(app["player"], dx * speed, dy * speed, solid_rects(app["state"]))
    door = door_touched(app["state"]["room"], app["player"], dx, dy)
    if door is None:
        app["touching"] = None
    elif door != app["touching"]:
        app["touching"] = door
        go_through(app, door)


# --- Drawing -------------------------------------------------------------------------


def load_fonts():
    """The two fonts of the game: pygame's built-in one, at two sizes."""
    return {"text": pygame.font.Font(None, 16), "title": pygame.font.Font(None, 32)}


def draw_text(screen, font, text, color, position, align="left"):
    """Write one line of text. `position` is its top-left, top-middle or top-right corner, as `align` says."""
    image = font.render(text, False, color)  # False: no smoothing, the pixels stay sharp
    rect = image.get_rect()
    if align == "center":
        rect.midtop = position
    elif align == "right":
        rect.topright = position
    else:
        rect.topleft = position
    screen.blit(image, rect)


def darker(color):
    return (color[0] * 4 // 5, color[1] * 4 // 5, color[2] * 4 // 5)


def dim(screen):
    """Darken whatever is on screen, to put a menu or a question on top of it."""
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 150))
    screen.blit(shade, (0, 0))


def draw_box(screen, rect):
    pygame.draw.rect(screen, COLORS["box"], rect)
    pygame.draw.rect(screen, COLORS["text"], rect, 1)


def draw_menu(app, screen, top):
    """The entries of the current menu, one per line from `top`, the highlighted one in color."""
    font = app["fonts"]["text"]
    for index, entry in enumerate(menu_entries(app)):
        label = story.MESSAGES["menu_" + entry]
        color = COLORS["text"]
        if index == app["menu_index"]:
            label = "> " + label + " <"
            color = COLORS["highlight"]
        draw_text(screen, font, label, color, (WIDTH // 2, top + index * (font.get_linesize() + 4)), "center")


def draw_title_screen(app, screen):
    screen.fill(COLORS["sea"])
    for row in range(8):
        for col in range(9):
            x = col * 32 + (row % 2) * 16
            y = 12 + row * 28
            pygame.draw.line(screen, COLORS["foam"], (x, y), (x + 8, y))
    draw_text(screen, app["fonts"]["title"], story.MESSAGES["title"], COLORS["text"], (WIDTH // 2, 48), "center")
    draw_text(screen, app["fonts"]["text"], story.MESSAGES["subtitle"], COLORS["foam"], (WIDTH // 2, 80), "center")


def draw_door(screen, door, status):
    rect = door_rect(door)
    if status == "open":
        pygame.draw.rect(screen, COLORS["black"], rect)
    elif status == "locked":
        pygame.draw.rect(screen, COLORS["door_locked"], rect)
        keyhole = pygame.Rect(0, 0, 4, 4)
        keyhole.center = rect.center
        pygame.draw.rect(screen, COLORS["keyhole"], keyhole)
    else:
        pygame.draw.rect(screen, COLORS["door_sealed"], rect)
        pygame.draw.line(screen, COLORS["black"], rect.topleft, rect.bottomright, 2)
        pygame.draw.line(screen, COLORS["black"], rect.topright, rect.bottomleft, 2)


def draw_thing(screen, thing):
    """An item, a puzzle or a character, as colored rectangles."""
    rect = thing_rect(thing["id"])
    color = THING_COLORS.get(thing["id"], MISSING_COLOR)
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


def draw_player(app, screen):
    rect = player_rect(app["player"])
    pygame.draw.rect(screen, COLORS["player"], rect)
    fx, fy = app["facing"]
    for side in (-1, 1):
        # Two eyes side by side, on the side the player is looking at.
        eye = pygame.Rect(0, 0, 2, 2)
        eye.center = (rect.centerx + fx * 3 + side * 3 * abs(fy), rect.centery + fy * 3 + side * 3 * abs(fx))
        pygame.draw.rect(screen, COLORS["black"], eye)


def draw_room(app, screen):
    room = app["state"]["room"]
    floor, wall = ROOM_COLORS.get(room, DEFAULT_ROOM_COLORS)
    screen.fill(COLORS["black"])
    pygame.draw.rect(screen, wall, tile_rect(0, 0, COLUMNS, ROWS))
    inside = tile_rect(1, 1, COLUMNS - 2, ROWS - 2)
    pygame.draw.rect(screen, floor, inside)
    for y in range(inside.top + TILE // 2, inside.bottom, TILE // 2):
        pygame.draw.line(screen, darker(floor), (inside.left, y), (inside.right - 1, y))  # planks
    if story.ROOMS[room]["outdoor"]:
        pygame.draw.rect(screen, COLORS["railing"], inside.inflate(4, 4), 2)
    for thing in engine.things_here(app["state"]):
        if thing["kind"] == "door":
            draw_door(screen, thing["id"], thing["status"])
        else:
            draw_thing(screen, thing)
    draw_player(app, screen)


def draw_hud(app, screen):
    font = app["fonts"]["text"]
    pygame.draw.rect(screen, COLORS["hud"], (0, 0, WIDTH, HUD_HEIGHT))
    room_name = story.ROOMS[app["state"]["room"]]["name"]
    draw_text(screen, font, room_name, COLORS["text"], (8, 10))
    draw_text(screen, font, story.MESSAGES["hint_menu"], COLORS["dim_text"], (WIDTH - 8, 10), "right")


def draw_banner(app, screen):
    if app["banner_frames"] <= 0:
        return
    image = app["fonts"]["text"].render(app["banner"], False, COLORS["text"])
    box = image.get_rect(center=(WIDTH // 2, HUD_HEIGHT + 28)).inflate(16, 8)
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
    if pygame.time.get_ticks() // 400 % 2 == 0:
        # A blinking arrow: press E to go on.
        x, y = box.right - 10, box.bottom - 6
        pygame.draw.polygon(screen, COLORS["highlight"], [(x - 3, y - 4), (x + 3, y - 4), (x, y - 1)])


def draw_play_screen(app, screen):
    draw_room(app, screen)
    draw_hud(app, screen)


def draw_ending_screen(app, screen):
    ending_id = app["state"]["ending"]
    ending = story.ENDINGS[ending_id]
    font = app["fonts"]["text"]
    screen.fill(COLORS["good_ending"] if ending["good"] else COLORS["bad_ending"])
    number = list(story.ENDINGS).index(ending_id) + 1
    label = story.MESSAGES["ending_number"].format(number=number, total=len(story.ENDINGS))
    draw_text(screen, font, label, COLORS["dim_text"], (WIDTH // 2, 20), "center")
    draw_text(screen, app["fonts"]["title"], ending["title"], COLORS["highlight"], (WIDTH // 2, 36), "center")
    y = 76
    for paragraph in ending["text"]:
        for line in wrap(paragraph, WIDTH - 32, text_width(font)):
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
    elif scene == "pause":
        draw_play_screen(app, screen)
        dim(screen)
        box = pygame.Rect(WIDTH // 2 - 64, 60, 128, 92)
        draw_box(screen, box)
        draw_text(screen, app["fonts"]["text"], story.MESSAGES["pause"], COLORS["dim_text"], (WIDTH // 2, box.top + 8), "center")
        draw_menu(app, screen, box.top + 28)
    elif scene == "ending":
        draw_ending_screen(app, screen)
        draw_menu(app, screen, 172)
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
