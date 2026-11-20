"""The visual effects of Plot Twist: particles, glows, dissolves, ripples and the portal warp.

None of this changes the game: the engine decides what happens, main.py tells this
module when something worth showing happened (on_outcome) and calls update() once
per frame and the draw_... functions while drawing. Everything here is presentation.

How it works, in short:
- A particle is a small dict (position, speed, life, colour). update() moves every
  particle and drops the dead ones; draw_particles() paints each one as a pixel.
  Particles live in room pixels, like the things of the room, so the camera moves
  them with everything else.
- A glow is a round, banded spot of light, added to the colours under it
  (BLEND_RGB_ADD): the 8-bit look keeps three or four bands instead of a smooth fade.
- A dissolve hides the pixels of a picture one by one, in a fixed scattered order:
  each pixel has its own threshold, and it disappears once the progress passes it.
- The randomness comes from one seeded generator, so every run looks the same
  (and the tests always see the same thing).

Each effect can be switched off in FX, and its timing and size are constants below.
"""

import math
import random

import pygame

# --- Switches: set one to False to turn that effect off --------------------------------

FX = {
    "generators": True,     # glowing lamps, sparks from the levers, shaking when one is missing
    "cables": True,         # current running along the cables
    "barriers": True,       # energy on the edges, and the pixel dissolve when they open
    "cauldron": True,       # coloured liquid, bubbles, glow of the fire and of the remedy
    "portals": True,        # turning light on the ring, ripples on the floor, the warp
    "tiles": True,          # a wave when a tile lights up, red sparks after a mistake
    "anvil": True,          # sparks, flash and the halves welding together
    "wand": True,           # the spark up the arm, the glow on the inventory icon
    "dust": True,           # dust and salt floating in the rooms indoors
    "lights": True,         # swinging lanterns, pulsing crystals
    "clues": True,          # a glow and twinkles on the thing that gave a new clue
    "crumble": True,        # the crab statue shaking the ship, trembling and dropping stones before it breaks
    "shatter": True,        # the giant claw that breaks the screen when the crab has caught both players
    "darkness": True,       # the dark rooms, lit only around lanterns, crystals, portals and the players
    "scenery": True,        # floors and walls with details, walls with depth, shading and shadows of the furniture
    "ambient": True,        # small things that move: steam, drops from the ceiling, flames, a glint on puddles
    "atmosphere": True,     # the colour of the light in each room, and soft lights around what shines
    "weather": True,        # the storm that grows with the puzzles: clouds, wind, rain, lightning, thunder (weather.py)
}

# --- Timing and sizes (frames are 1/60 of a second) --------------------------------------

SEED = 7                     # the seed of the randomness of the effects
DARK_COLOR = (6, 8, 22)      # what the dark of a dark room looks like: almost black, a little blue
LIGHT_REACH = (1.0, 0.82, 0.64, 0.46)  # how far each step of a light reaches, of its radius: the last is fully lit
LIGHT_BANDS = len(LIGHT_REACH)         # a light fades into the dark in this many hard steps, not smoothly
CONE_BANDS = 3               # and a cone of light in this many, along its length
DRIP_COLOR = (150, 196, 236)  # a drop of water from the ceiling
DRIP_GRAVITY = 0.12
SHARD_GRAVITY = 0.2          # pixels per frame, per frame: how fast the pieces of a broken screen fall
SHARD_PUSH = 1.6             # how hard they are pushed away from where the screen was hit
SHARD_SPIN = 5               # degrees per frame, at most, either way
SHARD_STAGGER = 14           # pixels from the hit for each frame a piece waits before it falls
SHARD_EDGE = (214, 240, 255)  # the light on the edges of a piece, and on the cracks
CRACK_DARK = (12, 12, 20)
MAX_PARTICLES = 400          # never more than this many at once

GENERATOR_SPARK_EVERY = 26   # frames between two sparks of a generator that is on (on average)
GENERATOR_GLOW = 7           # radius of the glow of a lamp that is on
CABLE_PULSE = 0.08           # how fast the lit cables pulse
CABLE_CURRENT = 0.012        # how fast the spot of current runs along a cable (part of it per frame)

BARRIER_FADE_FRAMES = 60     # how long a barrier takes to dissolve (one second)
BARRIER_SPARKS = 3           # sparks per frame while it dissolves
BARRIER_EDGE_SPOTS = 6       # spots of energy running around a barrier that stands

CAULDRON_BUBBLE_EVERY = 14   # frames between two bubbles of a cauldron with something in it
POUR_BUBBLES = 14            # bubbles when a tincture goes in
FIRE_GLOW = 18               # radius of the light of the blue fire

PORTAL_SPIN = 0.035          # how fast the light turns around the ring (radians per frame)
PORTAL_RIPPLE = 1            # how many pixels the floor sways around a ring
WARP_FRAMES = 50             # how long the purple warp lasts after a portal

TILE_WAVE_FRAMES = 24        # how long the wave of a lit tile lasts
MISTAKE_SPARKS = 18          # red sparks after a wrong tile

FUSE_FRAMES = 80             # how long the halves of the key take to weld
FUSE_SPARKS = 40             # sparks when they meet
FLASH_FRAMES = 14            # how long a white flash lasts

WAND_RISE_FRAMES = 40        # how long the spark climbs up the arm

CLUE_FRAMES = 75             # how long the glow of a new clue lasts (a bit more than a second)
CLUE_SPARKS = 22             # the twinkles thrown at the start
CLUE_TWINKLE_EVERY = 5       # frames between two twinkles after that
CLUE_GLOW = 16               # radius of the glow

DUST_PER_TILES = 14          # one speck of dust for this many tiles of floor
DUST_MAX = 70

LANTERN_SWING = 7            # degrees a lantern swings either way
LANTERN_GLOW = 14
CRYSTAL_GLOW = 13

# --- Colours ------------------------------------------------------------------------------

SPARK = [(255, 236, 140), (255, 255, 255), (255, 190, 80)]
ENERGY = [(112, 232, 255), (210, 250, 255), (56, 148, 200)]
PURPLE = [(186, 116, 255), (230, 200, 255), (112, 62, 176)]
RED = [(255, 90, 70), (214, 64, 52), (255, 170, 120)]
CLUE = [(255, 236, 140), (255, 255, 255), (150, 230, 255)]  # gold, white and a touch of magic
WELD = [(255, 255, 255), (255, 230, 120), (255, 150, 50), (255, 110, 40)]
LIQUID = {                    # the cauldron, for each step of the recipe
    0: (54, 70, 78),          # nothing yet: dark water
    1: (52, 128, 80),         # the green one: seaweed
    2: (120, 72, 40),         # the red one: brown
    3: (252, 214, 80),        # the gold one: bright gold
    "ready": (190, 245, 255), # the blue one, last: clear and glowing
}
DUST_COLORS = {"mine": (34, 26, 18), "corridor": (22, 26, 30), "hold": (24, 26, 28), "infirmary": (14, 18, 18)}
DUST_DEFAULT = (26, 22, 16)


# --- The state of the effects -----------------------------------------------------------


def new_fx():
    """Everything the effects remember from frame to frame. main.py keeps it in app["fx"]."""
    return {
        "rng": random.Random(SEED),
        "particles": [],     # sparks, bubbles... in room pixels
        "screen": [],        # particles on the screen itself (the warp)
        "dust": [],          # the specks floating in the room
        "room": None,        # the room the dust and the dissolves belong to
        "fading": [],        # barriers dissolving: {"rect", "frames"}
        "waves": [],         # rings spreading from a lit tile: {"center", "age"}
        "fuse": None,        # the halves welding: {"center", "age"}
        "wand_rise": None,   # the spark up the arm: {"age"}
        "clue": None,        # the glow on what gave a new clue: {"rect", "age"}
        "warp": 0,           # frames left of the purple warp
        "flash": 0,          # frames left of the white flash
        "drips": [],         # drops falling from the ceiling: {"x", "y", "land", "vy"}
    }


def reset_room(fx, room, floor, indoor):
    """A new room: forget what belonged to the old one, and scatter the dust of this one."""
    fx["room"] = room
    fx["particles"] = []
    fx["fading"] = []
    fx["waves"] = []
    fx["fuse"] = None
    fx["clue"] = None
    fx["dust"] = []
    fx["drips"] = []
    if not (FX["dust"] and indoor):
        return
    rng = random.Random(f"{SEED}-{room}")  # the same dust every time the room is entered
    count = min(DUST_MAX, (floor.width // 16) * (floor.height // 16) // DUST_PER_TILES)
    for _ in range(count):
        fx["dust"].append({
            "x": rng.uniform(floor.left, floor.right), "y": rng.uniform(floor.top, floor.bottom),
            "phase": rng.uniform(0, 2 * math.pi), "speed": rng.uniform(0.04, 0.12),
            "bounds": floor, "color": DUST_COLORS.get(room, DUST_DEFAULT),
        })


# --- Particles --------------------------------------------------------------------------


def spawn(fx, x, y, count, colors, speed=1.0, life=30, gravity=0.0, up=0.0, spread=math.pi * 2, angle=0.0,
          layer="particles"):
    """Throw `count` particles from (x, y), in random directions within `spread` around `angle`.

    `up` adds a push upwards, `gravity` pulls them down a little each frame.
    """
    rng = fx["rng"]
    particles = fx[layer]
    for _ in range(count):
        if len(particles) >= MAX_PARTICLES:
            return
        direction = angle + rng.uniform(-spread / 2, spread / 2)
        strength = speed * rng.uniform(0.3, 1.0)
        span = int(life * rng.uniform(0.6, 1.0))
        particles.append({
            "x": float(x), "y": float(y),
            "vx": math.cos(direction) * strength, "vy": math.sin(direction) * strength - up,
            "life": span, "max_life": span, "gravity": gravity, "color": rng.choice(colors),
        })


def update_particles(particles):
    """Move every particle one frame, and drop the ones whose life is over."""
    alive = []
    for p in particles:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vy"] += p["gravity"]
        p["life"] -= 1
        if p["life"] > 0:
            alive.append(p)
    particles[:] = alive


def draw_particles(surface, particles):
    """Each particle is one pixel, two for the young ones; it darkens as it dies."""
    for p in particles:
        fade = p["life"] / p["max_life"]
        color = tuple(int(c * (0.35 + 0.65 * fade)) for c in p["color"])
        x, y = int(p["x"]), int(p["y"])
        surface.fill(color, (x, y, 1, 1))
        if fade > 0.7:
            surface.fill(color, (x + 1, y, 1, 1))


def update(fx):
    """Move every effect on by one frame."""
    update_particles(fx["particles"])
    update_particles(fx["screen"])
    for speck in fx["dust"]:
        speck["phase"] += 0.02
        speck["x"] += math.sin(speck["phase"]) * speck["speed"]
        speck["y"] -= speck["speed"] * 0.5
        bounds = speck["bounds"]
        if speck["y"] < bounds.top:
            speck["y"] = bounds.bottom - 1  # drifted out of the top: it comes back from below
    for fading in fx["fading"]:
        fading["frames"] -= 1
    fx["fading"] = [fading for fading in fx["fading"] if fading["frames"] > 0]
    for wave in fx["waves"]:
        wave["age"] += 1
    fx["waves"] = [wave for wave in fx["waves"] if wave["age"] < TILE_WAVE_FRAMES]
    if fx["fuse"] is not None:
        fx["fuse"]["age"] += 1
        if fx["fuse"]["age"] >= FUSE_FRAMES:
            fx["fuse"] = None
    if fx["wand_rise"] is not None:
        fx["wand_rise"]["age"] += 1
        if fx["wand_rise"]["age"] >= WAND_RISE_FRAMES:
            fx["wand_rise"] = None
    if fx["clue"] is not None:
        fx["clue"]["age"] += 1
        if fx["clue"]["age"] >= CLUE_FRAMES:
            fx["clue"] = None
    if fx["warp"] > 0:
        fx["warp"] -= 1
    if fx["flash"] > 0:
        fx["flash"] -= 1


def draw_dust(surface, fx, frame):
    """The specks of dust: faint, and twinkling a little."""
    for speck in fx["dust"]:
        shine = 0.6 + 0.4 * math.sin(frame * 0.05 + speck["phase"] * 3)
        color = tuple(int(c * shine) for c in speck["color"])
        surface.fill(color, (int(speck["x"]), int(speck["y"]), 1, 1), special_flags=pygame.BLEND_RGB_ADD)


# --- Light ------------------------------------------------------------------------------

_glows = {}


def glow_picture(radius, color):
    """A round spot of light in four bands, brightest in the middle: drawn once, then kept."""
    key = (radius, color)
    if key not in _glows:
        size = radius * 2 + 1
        picture = pygame.Surface((size, size))
        picture.fill((0, 0, 0))
        for y in range(size):
            for x in range(size):
                distance = math.hypot(x - radius, y - radius) / max(radius, 1)
                if distance < 1:
                    band = math.ceil((1 - distance) * 4) / 4  # four steps, not a smooth fade
                    picture.set_at((x, y), tuple(int(c * band * band) for c in color))
        _glows[key] = picture
    return _glows[key]


def glow(surface, center, radius, color, strength=1.0):
    """Add a spot of light to the surface, centred on `center`. `strength` from 0 to 1 dims it."""
    strength = max(0.0, min(1.0, strength))
    if strength <= 0 or radius < 1:
        return
    dimmed = tuple(int(c * strength) for c in color)
    picture = glow_picture(radius, dimmed)
    surface.blit(picture, (center[0] - radius, center[1] - radius), special_flags=pygame.BLEND_RGB_ADD)


def pulse(frame, speed, low=0.0, high=1.0, phase=0.0):
    """A value going smoothly between low and high and back, `speed` radians per frame."""
    return low + (high - low) * (0.5 + 0.5 * math.sin(frame * speed + phase))


# --- Dissolving pictures pixel by pixel ----------------------------------------------------

_thresholds = {}


def threshold(x, y):
    """A fixed number between 0 and 1 for each pixel, scattered: the order pixels dissolve in."""
    key = (x, y)
    if key not in _thresholds:
        value = (x * 73856093) ^ (y * 19349663) ^ 0x5bd1e995
        _thresholds[key] = (value % 9973) / 9973
    return _thresholds[key]


def dissolved(picture, progress, appearing=False):
    """A copy of a picture with part of its pixels gone: none at progress 0, all at 1.

    With `appearing`, the other way round: the picture builds up, pixel by pixel.
    """
    result = pygame.Surface(picture.get_size(), pygame.SRCALPHA)
    result.blit(picture, (0, 0))
    width, height = result.get_size()
    for y in range(height):
        for x in range(width):
            gone = threshold(x, y) < progress
            if appearing:
                gone = not gone
            if gone:
                result.set_at((x, y), (0, 0, 0, 0))
    return result


# --- The floor swaying around a portal ------------------------------------------------------


def ripple(surface, area, frame, amplitude=PORTAL_RIPPLE):
    """Shift the rows of an area of the surface sideways in a slow wave: the floor sways.

    Neighbouring rows move almost together, so lines on the floor bend instead of
    breaking; the top and bottom rows of the area stay still, so its edges never show.
    """
    area = area.clip(surface.get_rect())
    if area.width <= 0 or area.height <= 0 or amplitude <= 0:
        return
    copy = surface.subsurface(area).copy()
    for row in range(area.height):
        calm = math.sin(math.pi * row / max(area.height - 1, 1))  # 0 at the edges, 1 in the middle
        shift = round(amplitude * calm * math.sin(frame * 0.08 + row * 0.22))
        if shift:
            surface.blit(copy, (area.left + shift, area.top + row), pygame.Rect(0, row, area.width, 1))


def draw_ring_light(surface, center, radius, frame, speed=PORTAL_SPIN):
    """Three bright arcs turning slowly around a ring, and sparkles turning the other way inside it."""
    for arc in range(3):
        start = frame * speed + arc * 2 * math.pi / 3
        for step in range(7):
            angle = start - step * 0.09
            x = center[0] + round(radius * math.cos(angle))
            y = center[1] + round(radius * math.sin(angle))
            color = PURPLE[1] if step < 2 else PURPLE[0]
            surface.fill(color, (x, y, 1, 1))
    for spark in range(5):
        angle = -frame * speed * 1.6 + spark * 2 * math.pi / 5
        x = center[0] + round(radius * 0.45 * math.cos(angle))
        y = center[1] + round(radius * 0.45 * math.sin(angle))
        surface.fill(ENERGY[1], (x, y, 1, 1))


def draw_warp(screen, view, fx):
    """The purple warp after a portal: the view waves, a purple veil fades, particles fly out."""
    if fx["warp"] <= 0:
        return
    left = fx["warp"] / WARP_FRAMES  # from 1, just arrived, down to 0
    amplitude = round(6 * left)
    if amplitude:
        copy = screen.subsurface(view).copy()
        for row in range(view.height):
            shift = round(amplitude * math.sin(row * 0.18 + fx["warp"] * 0.5))
            screen.blit(copy, (view.left + shift, view.top + row), pygame.Rect(0, row, view.width, 1))
    veil = pygame.Surface(view.size, pygame.SRCALPHA)
    veil.fill((112, 40, 176, int(200 * left)))
    screen.blit(veil, view.topleft)
    if fx["warp"] % 2 == 0:
        spawn(fx, view.centerx, view.centery, 6, PURPLE, speed=3.0, life=26, layer="screen")
    draw_particles(screen, fx["screen"])


def draw_clue_glow(surface, fx):
    """A new clue: a soft glow on the thing that gave it, swelling then fading, and four short rays
    turning around it like a twinkling star."""
    clue = fx["clue"]
    if clue is None:
        return
    progress = clue["age"] / CLUE_FRAMES
    strength = math.sin(math.pi * min(1.0, progress * 1.4))  # swells quickly, fades slowly
    center = clue["rect"].center
    glow(surface, center, CLUE_GLOW, (110, 95, 40), strength)
    length = round(3 + 6 * strength)
    turn = clue["age"] * 0.06
    for ray in range(4):
        angle = turn + ray * math.pi / 2
        for step in range(2, length):
            x = center[0] + round(step * math.cos(angle))
            y = center[1] + round(step * math.sin(angle))
            surface.fill(CLUE[1] if step < length - 1 else CLUE[0], (x, y, 1, 1))


def draw_flash(screen, view, fx, color=(255, 255, 255)):
    """A short white flash over the view, fading out."""
    if fx["flash"] <= 0:
        return
    veil = pygame.Surface(view.size, pygame.SRCALPHA)
    veil.fill(color + (int(220 * fx["flash"] / FLASH_FRAMES),))
    screen.blit(veil, view.topleft)


# --- Shaking, and a screen that breaks into pieces --------------------------------------


def shake_offset(frame, left, total, power):
    """How far the picture is pushed aside in this frame of a shake: (dx, dy) in pixels.

    The push goes any way, looks random but is always the same for the same
    frame, and dies down: `power` pixels at most when the shake starts (`left`
    equal to `total` frames), nothing when it is over.
    """
    if left <= 0 or total <= 0:
        return (0, 0)
    reach = power * left / total
    x = math.sin(frame * 12.9898) * 43758.5453
    y = math.sin(frame * 78.233 + 1.7) * 24634.6345
    x -= math.floor(x)  # the part after the point: a number from 0 to 1 that jumps around
    y -= math.floor(y)
    return (round((2 * x - 1) * reach), round((2 * y - 1) * reach))


def crack_web(size, center, seed, rays=11, rings=(0.28, 0.6)):
    """Break a picture of this size into polygons, like glass hit at `center`: a web of cracks.

    Rays run from the hit to the edges, at uneven angles, and rings cross them at
    uneven distances. Returns the pieces between them as lists of (x, y) corners:
    a fan of triangles around the hit, then a band of pieces for each ring, the
    last reaching the edges. Together they cover the whole picture, and the same
    seed always gives the same web.
    """
    rng = random.Random(seed)
    width, height = size
    cx, cy = center
    angles = sorted(2 * math.pi * ray / rays + rng.uniform(-0.2, 0.2) for ray in range(rays))

    def at_the_edge(angle):
        dx, dy = math.cos(angle), math.sin(angle)
        reaches = []
        if dx > 1e-9:
            reaches.append((width - cx) / dx)
        elif dx < -1e-9:
            reaches.append(-cx / dx)
        if dy > 1e-9:
            reaches.append((height - cy) / dy)
        elif dy < -1e-9:
            reaches.append(-cy / dy)
        reach = min(reaches)
        return (min(max(cx + dx * reach, 0), width), min(max(cy + dy * reach, 0), height))

    def along_the_edge(point):
        """How far a point of the edge is from the top left corner, going round clockwise."""
        x, y = point
        if y <= 0.5:
            return x
        if x >= width - 0.5:
            return width + y
        if y >= height - 0.5:
            return width + height + (width - x)
        return 2 * width + height + (height - y)

    corners = [((width, 0), width), ((width, height), width + height), ((0, height), 2 * width + height),
               ((0, 0), 2 * width + 2 * height)]
    around = 2 * width + 2 * height
    edges = [at_the_edge(angle) for angle in angles]
    bands = []
    for share in rings:
        band = []
        for x, y in edges:
            part = share * rng.uniform(0.8, 1.2)
            band.append((cx + (x - cx) * part, cy + (y - cy) * part))
        bands.append(band)
    pieces = []
    for ray in range(rays):
        after = (ray + 1) % rays
        pieces.append([(cx, cy), bands[0][ray], bands[0][after]])
        for inner, outer in zip(bands, bands[1:]):
            pieces.append([inner[ray], outer[ray], outer[after], inner[after]])
        start = along_the_edge(edges[ray])
        span = (along_the_edge(edges[after]) - start) % around
        between = sorted(((where - start) % around, corner) for corner, where in corners)
        piece = [bands[-1][ray], edges[ray]]
        piece += [corner for gap, corner in between if 0 < gap < span]  # the corners of the picture on the way
        piece += [edges[after], bands[-1][after]]
        pieces.append(piece)
    return [[(round(x), round(y)) for x, y in piece] for piece in pieces]


def cut_shards(picture, pieces, center, seed):
    """Cut a picture into the pieces of a crack_web, ready to fall: a list of shards.

    Each shard has its own "picture" (the part of the picture inside its piece,
    with light on its edges), the "rect" it came from, and how it will move: a push
    away from `center` ("vx", "vy"), a "spin" in degrees per frame, and the frames
    it waits before falling ("delay": the pieces near the hit go first).
    """
    rng = random.Random(seed)
    whole = picture.get_rect()
    shards = []
    for piece in pieces:
        xs = [x for x, y in piece]
        ys = [y for x, y in piece]
        rect = pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1).clip(whole)
        if rect.width <= 0 or rect.height <= 0:
            continue
        local = [(x - rect.x, y - rect.y) for x, y in piece]
        cut = pygame.Surface(rect.size, pygame.SRCALPHA)
        cut.blit(picture, (0, 0), rect)
        shape = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.polygon(shape, (255, 255, 255, 255), local)
        cut.blit(shape, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)  # nothing left outside the piece
        pygame.draw.lines(cut, SHARD_EDGE, True, local, 1)
        dx, dy = rect.centerx - center[0], rect.centery - center[1]
        far = math.hypot(dx, dy) or 1.0
        push = SHARD_PUSH * rng.uniform(0.5, 1.5)
        shards.append({"picture": cut, "rect": rect,
                       "vx": dx / far * push + rng.uniform(-0.3, 0.3), "vy": dy / far * push - rng.uniform(0.0, 1.0),
                       "spin": rng.uniform(-SHARD_SPIN, SHARD_SPIN), "delay": int(far / SHARD_STAGGER)})
    return shards


def shard_position(shard, age):
    """The middle of a shard `age` frames after the screen broke, and how far it has turned (degrees)."""
    time = age - shard["delay"]
    x, y = shard["rect"].center
    if time <= 0:
        return (x, y), 0.0
    return (x + shard["vx"] * time, y + shard["vy"] * time + SHARD_GRAVITY * time * time / 2), shard["spin"] * time


def draw_shards(surface, shards, age, offset=(0, 0)):
    """The pieces of the broken screen, `age` frames after it broke: falling, pushed outwards, turning."""
    bottom = surface.get_height()
    for shard in shards:
        (x, y), angle = shard_position(shard, age)
        picture = shard["picture"]
        if angle != 0.0:
            picture = pygame.transform.rotate(picture, angle)
        place = picture.get_rect(center=(round(x) + offset[0], round(y) + offset[1]))
        if place.top < bottom:
            surface.blit(picture, place)


def draw_cracks(surface, pieces, center, reach, offset=(0, 0)):
    """The cracks between the pieces, as far as `reach` pixels from the hit: a dark line with light beside it."""
    for piece in pieces:
        for start, end in zip(piece, piece[1:] + piece[:1]):
            near, far = sorted((start, end), key=lambda point: math.hypot(point[0] - center[0], point[1] - center[1]))
            near_gap = math.hypot(near[0] - center[0], near[1] - center[1])
            far_gap = math.hypot(far[0] - center[0], far[1] - center[1])
            if near_gap > reach:
                continue
            if far_gap > reach and far_gap > near_gap:
                part = (reach - near_gap) / (far_gap - near_gap)  # the crack has not got to the far end yet
                far = (near[0] + (far[0] - near[0]) * part, near[1] + (far[1] - near[1]) * part)
            a = (round(near[0]) + offset[0], round(near[1]) + offset[1])
            b = (round(far[0]) + offset[0], round(far[1]) + offset[1])
            pygame.draw.line(surface, SHARD_EDGE, (a[0] + 1, a[1]), (b[0] + 1, b[1]), 1)
            pygame.draw.line(surface, CRACK_DARK, a, b, 1)


# --- Dark rooms: a layer of darkness with holes of light in it -----------------------------
#
# The room is drawn as usual, and a layer as big as the room goes over it: see-through
# dark everywhere, clear where there is light. A light is a picture of a hole: clear in
# the middle, and darker ring by ring out to the full dark at its edge, in hard steps
# (no smooth fade: these are big pixels). Each hole is stamped on the layer keeping, for
# every pixel, the clearer of the two: so two lights next to each other join, and one
# never darkens what the other has lit.
#
# The idea of a dark layer with a stepped hole in it comes from the "punch_a_hole" sample
# of Mekire's pygame-samples (github.com/Mekire/pygame-samples); the code here is ours.

_dark_layers = {}  # size -> the layer for rooms of that size, made once
_holes = {}        # (radius, dark) -> the picture of a round hole
_cones = {}        # (length, half angle, angle, dark) -> the picture of a cone-shaped hole


def darkness(size, dark):
    """A layer of this size, all dark: `dark` from 0 (clear) to 255 (pitch black). Stamp lights on it
    with punch(), then blit it over the room."""
    if size not in _dark_layers:
        _dark_layers[size] = pygame.Surface(size, pygame.SRCALPHA)
    layer = _dark_layers[size]
    layer.fill(DARK_COLOR + (dark,))
    return layer


def band_alpha(dark, band, bands):
    """How dark the `band`-th step of a light is, from the outside (0) in: the last one is clear."""
    return round(dark * (bands - 1 - band) / bands)


def light_hole(radius, dark):
    """The picture of a round light in a darkness of `dark`: rings from almost as dark as the room
    at the edge to clear in the middle."""
    key = (radius, dark)
    if key not in _holes:
        size = radius * 2 + 1
        picture = pygame.Surface((size, size), pygame.SRCALPHA)
        picture.fill(DARK_COLOR + (dark,))
        for band in range(LIGHT_BANDS):
            reach = round(radius * LIGHT_REACH[band])
            pygame.draw.circle(picture, DARK_COLOR + (band_alpha(dark, band, LIGHT_BANDS),), (radius, radius), reach)
        _holes[key] = picture
    return _holes[key]


def cone_points(origin, angle, length, half, steps=6):
    """The corners of a cone of light: its point at `origin`, opening `half` degrees either side of
    `angle` (degrees, 0 to the right, 90 down), `length` pixels long, with a round far end."""
    points = [origin]
    for step in range(steps + 1):
        turn = math.radians(angle - half + 2 * half * step / steps)
        points.append((origin[0] + length * math.cos(turn), origin[1] + length * math.sin(turn)))
    return [(round(x), round(y)) for x, y in points]


def light_cone(length, half, angle, dark):
    """The picture of a cone of light in a darkness of `dark`, its point in the middle of the picture:
    clear near the point, darker step by step along its length."""
    key = (length, half, angle, dark)
    if key not in _cones:
        size = length * 2 + 1
        picture = pygame.Surface((size, size), pygame.SRCALPHA)
        picture.fill(DARK_COLOR + (dark,))
        for band in range(CONE_BANDS):
            reach = round(length * (CONE_BANDS - band) / CONE_BANDS)
            pygame.draw.polygon(picture, DARK_COLOR + (band_alpha(dark, band, CONE_BANDS),),
                                cone_points((length, length), angle, reach, half))
        _cones[key] = picture
    return _cones[key]


def punch(layer, picture, center):
    """Stamp a light (a light_hole or a light_cone) on a layer of darkness, centred there: every
    pixel keeps the clearer of the two."""
    place = picture.get_rect(center=(round(center[0]), round(center[1])))
    layer.blit(picture, place, special_flags=pygame.BLEND_RGBA_MIN)


# --- Drops from the ceiling ----------------------------------------------------------------


def add_drip(fx, x, y, land):
    """A drop leaves the ceiling at (x, y) and falls until it lands at the height `land`."""
    fx["drips"].append({"x": x, "y": float(y), "land": land, "vy": 0.0})


def update_drips(fx):
    """Drops fall faster and faster; when one lands it splashes in a few tiny drops."""
    falling = []
    for drip in fx["drips"]:
        drip["vy"] += DRIP_GRAVITY
        drip["y"] += drip["vy"]
        if drip["y"] >= drip["land"]:
            spawn(fx, drip["x"], drip["land"], 4, [DRIP_COLOR, (210, 236, 255)], speed=0.9, life=9,
                  gravity=0.12, up=0.7, spread=math.pi * 0.8, angle=-math.pi / 2)
        else:
            falling.append(drip)
    fx["drips"] = falling


def draw_drips(surface, fx):
    """Each falling drop is a streak of two pixels."""
    for drip in fx["drips"]:
        surface.fill(DRIP_COLOR, (int(drip["x"]), int(drip["y"]) - 1, 1, 2))


# --- Atmosphere: the colour of the light in a room, and soft lights -----------------------------
#
# Two layers over a room, the way old consoles did it with few colours:
# - a lightmap, multiplied into the room (BLEND_RGB_MULT): one colour for the whole room
#   (white changes nothing, a pale blue makes it cold), and around some things a disc
#   of another colour (warmer near a fire, violet near a portal);
# - soft lights, added on top (BLEND_RGB_ADD): bright in the middle, then fainter in
#   hard steps, with a dither between the steps so the edge is pixelated, not blurred.

_lightmaps = {}   # size -> the lightmap for rooms of that size, made once and filled every frame
_tints = {}       # (radius, colour) -> a disc of tint, fading to white at its edge
_soft = {}        # (radius, colour) -> a soft light
SOFT_LEVELS = 8   # how many strengths a soft light can have, as it flickers or pulses


def lightmap(size, color):
    """A lightmap of this size, all of one colour: tint discs go on it, then it is multiplied into the room."""
    if size not in _lightmaps:
        _lightmaps[size] = pygame.Surface(size)
    layer = _lightmaps[size]
    layer.fill(color)
    return layer


def stepped(distance, steps, x, y):
    """How much of a light (or a tint) there is at `distance` from its middle (0 to 1, past 1 nothing),
    in `steps` hard steps, with every other pixel taking the next step down where two steps meet."""
    if distance >= 1:
        return 0.0
    level = (1 - distance) * steps
    band = math.ceil(level)
    if band - level > 0.5 and (x + y) % 2 == 0:
        band -= 1  # half way between two steps: a dither
    return max(band, 0) / steps


def tint_disc(radius, color, steps=4):
    """A disc of a tint, for a lightmap: `color` in the middle, white (no change) at its edge."""
    key = (radius, color)
    if key not in _tints:
        size = radius * 2 + 1
        picture = pygame.Surface((size, size))
        picture.fill((255, 255, 255))
        for x in range(size):
            for y in range(size):
                share = stepped(math.hypot(x - radius, y - radius) / max(radius, 1), steps, x, y)
                if share:
                    picture.set_at((x, y), tuple(int(255 + (c - 255) * share) for c in color))
        _tints[key] = picture
    return _tints[key]


def tint(layer, center, radius, color):
    """Lay a disc of a tint on a lightmap: where it falls, the lightmap is multiplied by it."""
    disc = tint_disc(radius, color)
    layer.blit(disc, (round(center[0]) - radius, round(center[1]) - radius), special_flags=pygame.BLEND_RGB_MULT)


def soft_light_picture(radius, color):
    """A soft light: `color` in the middle, fainter in four hard steps out to its edge, dithered between them."""
    key = (radius, color)
    if key not in _soft:
        size = radius * 2 + 1
        picture = pygame.Surface((size, size))
        picture.fill((0, 0, 0))
        for x in range(size):
            for y in range(size):
                share = stepped(math.hypot(x - radius, y - radius) / max(radius, 1), 4, x, y)
                if share:
                    picture.set_at((x, y), tuple(int(c * share * share) for c in color))
        _soft[key] = picture
    return _soft[key]


def soft_light(surface, center, radius, color, strength=1.0):
    """Add a soft light to the surface. `strength` from 0 to 1 dims it (for flickering and pulsing)."""
    strength = round(max(0.0, min(1.0, strength)) * SOFT_LEVELS) / SOFT_LEVELS  # a few levels: few pictures to keep
    if strength <= 0 or radius < 1:
        return
    dimmed = tuple(int(c * strength) for c in color)
    picture = soft_light_picture(radius, dimmed)
    surface.blit(picture, (round(center[0]) - radius, round(center[1]) - radius), special_flags=pygame.BLEND_RGB_ADD)
