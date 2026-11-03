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
}

# --- Timing and sizes (frames are 1/60 of a second) --------------------------------------

SEED = 7                     # the seed of the randomness of the effects
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
        "warp": 0,           # frames left of the purple warp
        "flash": 0,          # frames left of the white flash
    }


def reset_room(fx, room, floor, indoor):
    """A new room: forget what belonged to the old one, and scatter the dust of this one."""
    fx["room"] = room
    fx["particles"] = []
    fx["fading"] = []
    fx["waves"] = []
    fx["fuse"] = None
    fx["dust"] = []
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


def draw_flash(screen, view, fx, color=(255, 255, 255)):
    """A short white flash over the view, fading out."""
    if fx["flash"] <= 0:
        return
    veil = pygame.Surface(view.size, pygame.SRCALPHA)
    veil.fill(color + (int(220 * fx["flash"] / FLASH_FRAMES),))
    screen.blit(veil, view.topleft)
