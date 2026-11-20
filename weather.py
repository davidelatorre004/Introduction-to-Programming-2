"""The weather of Plot Twist: one storm that grows through the whole adventure.

The bolt that opens a new game is its first sign. Then, as the three puzzles of the
ship are solved (the generators of the cabin, the tiles of the hold, the remedy of the
infirmary), the storm comes closer: the sky darkens and clouds gather, the wind rises,
the rain starts and grows heavier, lightning flashes nearer and nearer and the thunder
follows it sooner. It is at its worst just before the last puzzle is solved, and it
stays that way until the end.

How strong the storm is, is one number, the "level": 0 is the calm before the storm,
1 the storm at its worst. storm_level() says where the level should be for the
progress of the player; the level then moves there slowly, one small step a frame,
so that the weather never jumps. It only goes up: a puzzle that starts over (a wrong
tile, the generators going back when the player walks into the cabin) does not calm
the storm. Everything else (how dark, how much rain, how strong the wind, how often
lightning strikes) is worked out from the level.

None of this changes the game: like effects.py, this module knows nothing about the
rules. main.py tells it where the level should be (set_goal), calls update() once a
frame, plays the thunder update() returns, and calls the draw_... functions.

Before the rain, seagulls fly over the deck in a pattern that repeats (GULL_FLIGHTS); once
it starts to rain no new ones come (the ones in the air fly on and away).

Everything is drawn in hard pixels, like the rest of the game: rain drops are lines one
pixel wide, the clouds are blocks of four pixels with a chequered edge, the seagulls
pictures of sprites.py, the puddles plain ellipses. The randomness comes from a seeded generator, as in effects.py.
"""

import math
import random

import pygame

import scenery
import sprites

# --- How the level follows the progress of the player -------------------------------------

SEED = 11                  # the seed of the randomness of the weather
LEVEL_SPEED = 1 / (8 * 60)  # how far the level moves in a frame: from calm to the worst storm in 8 seconds
START = 0.08               # the level once the player has walked into the room of the first puzzle
SOLVE_STEP = 0.06          # what solving a puzzle adds at once: the storm takes a step forward

# --- What the level does: from which level each thing starts ------------------------------

RAIN_FROM = 0.3            # the rain starts with the second puzzle (the first one is solved at 1/3)
THUNDER_FROM = 0.3         # the thunder is heard from the second puzzle on
NEAR_FROM = 0.62           # from here the thunder is near: a crack, then the rumble
BOLT_FROM = 0.55           # from here a bolt can be seen across the sky of the deck
SHAKE_FROM = 0.75          # from here the strongest thunder makes the ship shake
LIGHTNING_FROM = 0.05      # below this, no lightning at all: the calm before the storm
PUDDLE_FROM = 0.45         # from here puddles form on the deck

# --- Sizes, speeds and colours ---------------------------------------------------------------

MAX_DROPS = 170            # rain drops on screen in the worst of the storm
DROPS_PER_FRAME = 3        # how many new drops can join in a frame: the rain thickens, it never pops in
MAX_SPLASHES = 60
SPLASH_FRAMES = 5          # how long a drop's splash stays on the floor
WIND_SLANT = 2.4           # pixels a drop is pushed sideways in a frame, in the strongest wind
NEAR_DROP = (174, 194, 226)  # a drop near the eye: long, fast, light
FAR_DROP = (118, 136, 172)   # a drop far away: short, slow, darker
SPLASH_COLOR = (196, 212, 236)
# The seagulls fly over the deck in a pattern that repeats: each flight is (how far down the sky
# its line is, from 0 at the top to 1 at the bottom; -1 flying left or 1 flying right; how many).
GULL_FLIGHTS = [
    (0.15, -1, 3),
    (0.55, 1, 2),
    (0.85, -1, 3),
    (0.35, 1, 1),
]
GULL_V = [(0, 0), (14, -9), (14, 9)]  # where each one of a flight flies: (behind the leader, above or below)
GULL_EVERY = 300           # frames between two flights (five seconds)
GULL_FIRST = 120           # frames before the first flight of a game
GULL_LAG = 4               # frames each one flaps after the one in front of it
GULL_SPEED = 0.8           # pixels a frame
GULL_WAVE = 4              # pixels each one rises and sinks as it flies...
GULL_WAVE_SPEED = 0.04     # ...this slowly
GULL_FLAP = 6              # frames each picture of the wings lasts
GULL_WINGS = [0, 1, 2, 1]  # the pictures of a flap: up, level, down, level...
GULL_GLIDE = 6             # ...then it glides, wings level, for this many pictures
GULL_SIZE = 16             # the pictures are a tile, the seagull in the middle of it

CLOUD_CELL = 4             # the clouds are drawn in blocks of this many pixels: big, chunky pixels
CLOUD_SIZE = (96, 72)      # cells of the picture of the clouds, which repeats (384 x 288 pixels)
CLOUD_STEPS = 20           # the clouds are made once for each of this many levels
CLOUD_DRIFT = 0.5          # pixels a frame the clouds move, in the strongest wind
CLOUD_LIGHT = (238, 240, 248)  # the shadow of a cloud in the calm (multiplied: a little darker)...
CLOUD_DARK = (200, 204, 222)   # ...and in the storm
CLOUD_EDGE = 0.05          # how wide the chequered edge of a cloud is, in noise

SKY_DARK = (168, 174, 204)  # what the storm does to the deck at its worst (multiplied): darker, and blue
FLASH_COLOR = (64, 68, 84)  # what a flash of lightning adds to the deck at its strongest
INDOOR_FLASH = 0.4          # inside the ship a flash comes through the portholes: weaker
SOFT_FLASH = 0.3            # with soft lightning (F10), a flash is this much as strong, and flickers once
BOLT_GLOW = (150, 196, 236)
BOLT_CORE = (244, 240, 228)
WAVE_RUSH = 1.0             # how much faster the waves of the sea move in the worst storm

# A flash of lightning flickers: (first frame, last frame, strength) of each flicker.
FLICKERS = [(0, 2, 1.0), (5, 7, 0.55)]
SOFT_FLICKERS = [(0, 3, 1.0)]
FLASH_LENGTH = 8            # frames from the first flicker to the end of the last
THUNDER_DELAY = 100         # frames between flash and thunder when the storm is far (it shortens as it comes)
SHAKE_FRAMES = 18           # how long the ship shakes after the strongest thunder
SHAKE_POWER = 2             # pixels, on the deck (one inside)

PUDDLE_COLOR = (72, 86, 116)    # a puddle on the deck: the dark sky in it
PUDDLE_LIGHT = (150, 170, 206)  # the light on its edge
RIPPLE_EVERY = 23               # frames between two rings on a puddle (each puddle has its own moment)

_cloud_noise = []          # the noise of the clouds, made once: one row of numbers for each row of cells
_clouds = {}               # step of the level -> the picture of the clouds for it, made once


# --- The level ------------------------------------------------------------------------------


def clamp01(value):
    """The number held between 0 and 1."""
    return max(0.0, min(1.0, value))


def mix(low, high, share):
    """The number `share` of the way from `low` to `high`."""
    return low + (high - low) * share


def mix_color(one, two, share):
    """The colour `share` of the way from `one` to `two`, in whole numbers."""
    return tuple(round(mix(one[index], two[index], share)) for index in range(3))


def storm_level(solved, total, share, started):
    """Where the level should be: `solved` puzzles out of `total` are solved, `share` (from 0 to 1)
    is how far the player has got in the next one, and `started` is True once the player has
    walked into the room of a puzzle.

    Each puzzle has its part of the way from 0 to 1. Solving one takes the storm a step forward
    (SOLVE_STEP); working on one moves it on bit by bit. In the last puzzle the storm reaches 1
    as soon as the last step is all that is left, just before the end. With every puzzle solved,
    it stays at 1.
    """
    if total <= 0:
        return 0.0
    if solved >= total:
        return 1.0
    bottom = solved / total
    top = (solved + 1) / total
    if solved == 0:
        bottom = START if started else 0.0  # before that, the calm: the bolt of the opening was only a sign
    if solved < total - 1:
        top -= SOLVE_STEP  # the rest of the way is the step taken when the puzzle is solved
    return mix(bottom, top, clamp01(share))


def darkness(level):
    """How much of SKY_DARK the storm puts on the deck, from 0 to 1."""
    return clamp01(level)


def rain_amount(level):
    """How heavy the rain is, from 0 (none) to 1 (the downpour)."""
    return clamp01((level - RAIN_FROM) / (1 - RAIN_FROM))


def wind_strength(level):
    """How strong the wind blows, from a breath in the calm to 1 in the storm (gusts aside)."""
    return clamp01(0.1 + 0.9 * level)


def lightning_gap(level):
    """The fewest and the most frames between two strikes of lightning: shorter as the storm comes."""
    share = clamp01((level - LIGHTNING_FROM) / (1 - LIGHTNING_FROM))
    return round(mix(840, 150, share)), round(mix(1560, 360, share))


# --- The weather and its changes, frame by frame ----------------------------------------------


def new_weather(seed=SEED):
    """The weather at rest: no storm yet. A dict, like the effects (see the comments of its keys)."""
    return {
        "rng": random.Random(seed),
        "fresh": True,           # nothing seen yet: the first goal is taken at once, without moving to it
        "level": 0.0,            # how strong the storm is now, from 0 to 1
        "goal": 0.0,             # where the level is going: the highest the progress has asked for
        "soft": False,           # soft lightning (F10): weaker flashes, one flicker, no shaking
        "frame": 0,              # frames of weather so far
        "waves": 0.0,            # how far the waves of the sea have moved: faster in the storm
        "wind": 0.0,             # how strong the wind blows in this frame, gusts included
        "cloud_x": 0.0,          # how far the clouds have drifted
        "cloud_y": 0.0,
        "drops": [],             # the rain drops on screen: dicts, in pixels of the view
        "splashes": [],          # where drops have just hit the floor: [x, y, age]
        "gulls": [],             # the seagulls in the air: dicts, in pixels of the room (the deck)
        "flight": 0,             # the next flight of GULL_FLIGHTS
        "next_flight": GULL_FIRST,  # frames before it takes off
        "next_strike": 0,        # frames before the next lightning (0: not chosen yet)
        "flash": -1,             # frames since the last lightning, while it flashes; -1 otherwise
        "power": 0.0,            # how strong that lightning is, from 0 to 1
        "bolt": None,            # the points of its bolt, if it can be seen, in pixels of the view
        "thunders": [],          # the thunder on its way, one for each strike: {"in": frames left, "name", "volume", "shake"}
        "shake": 0,              # frames left of the ship shaking
    }


def reset(weather):
    """Back to the calm, for a new game or one that is resumed: the next goal is taken at once.
    Soft lightning stays as the player chose it."""
    soft = weather["soft"]
    weather.clear()
    weather.update(new_weather())
    weather["soft"] = soft


def set_goal(weather, target):
    """Where the progress of the player puts the storm. The first time, the level goes there at
    once (a saved game resumes in its own weather); after that it moves there slowly, and only up."""
    if weather["fresh"]:
        weather["fresh"] = False
        weather["level"] = target
        weather["goal"] = target
        return
    weather["goal"] = max(weather["goal"], target)


def update(weather, view_size, sky=None):
    """Move the weather on by one frame. `view_size` is the size of the view of the room on screen,
    where the rain falls; `sky` is the deck, in pixels of the room, where the seagulls fly (None: no
    seagulls). Returns the thunder to play now, as a dict ("name", "volume"), or None."""
    weather["frame"] += 1
    if weather["level"] < weather["goal"]:
        weather["level"] = min(weather["goal"], weather["level"] + LEVEL_SPEED)
    level = weather["level"]
    weather["waves"] += 1 + WAVE_RUSH * level
    weather["wind"] = wind_now(weather)
    weather["cloud_x"] += CLOUD_DRIFT * (0.25 + weather["wind"])
    weather["cloud_y"] += CLOUD_DRIFT * 0.2
    update_rain(weather, view_size)
    update_gulls(weather, sky)
    if weather["shake"] > 0:
        weather["shake"] -= 1
    return update_lightning(weather, view_size)


def wind_now(weather):
    """The wind of this frame: its strength for the level, rising and falling in slow gusts."""
    frame = weather["frame"]
    gust = 0.75 + 0.15 * math.sin(frame * 0.013) + 0.1 * math.sin(frame * 0.051 + 1.3)
    return wind_strength(weather["level"]) * gust * 1.1


def new_drop(weather, width, height, top):
    """A rain drop starting somewhere above the view (or anywhere in it, when `top` is False).
    Some are near (long, fast, light), the others far (short, slow, darker)."""
    rng = weather["rng"]
    near = rng.random() < 0.45
    return {
        "x": rng.uniform(-10, width + 70),  # also to the right of the view: the wind blows them left
        "y": rng.uniform(-24, -4) if top else rng.uniform(0, height),
        "speed": rng.uniform(5.0, 6.2) if near else rng.uniform(3.4, 4.4),
        "length": rng.randint(5, 7) if near else rng.randint(3, 4),
        "color": NEAR_DROP if near else FAR_DROP,
        "land": rng.uniform(height * 0.15, height),  # where it hits the floor
    }


def update_rain(weather, view_size):
    """The drops fall, slanted by the wind; each one that reaches its spot on the floor splashes
    and starts again above the view. As the rain grows, a few new drops join each frame; as there
    should be fewer, the drops that land are not replaced."""
    width, height = view_size
    wanted = round(MAX_DROPS * rain_amount(weather["level"]))
    drops = weather["drops"]
    joined = 0
    while len(drops) < wanted and joined < DROPS_PER_FRAME:
        drops.append(new_drop(weather, width, height, top=True))
        joined += 1
    slant = -WIND_SLANT * weather["wind"]
    for drop in list(drops):
        drop["y"] += drop["speed"]
        drop["x"] += slant * drop["speed"] / 5
        if drop["y"] >= drop["land"]:
            if len(weather["splashes"]) < MAX_SPLASHES:
                weather["splashes"].append([round(drop["x"]), round(drop["land"]), 0])
            drops.remove(drop)
            if len(drops) < wanted:
                drops.append(new_drop(weather, width, height, top=True))
    for splash in list(weather["splashes"]):
        splash[2] += 1
        if splash[2] >= SPLASH_FRAMES:
            weather["splashes"].remove(splash)


def start_flight(weather, sky):
    """The next flight of the pattern takes off: its seagulls in a V, the leader in front, coming in
    from one side of the sky (just outside it) on its line."""
    height_share, heading, count = GULL_FLIGHTS[weather["flight"] % len(GULL_FLIGHTS)]
    weather["flight"] += 1
    if heading < 0:
        x = sky.right + GULL_SIZE
    else:
        x = sky.left - 2 * GULL_SIZE
    y = sky.top + round(height_share * (sky.height - GULL_SIZE))
    for index in range(count):
        back, side = GULL_V[index]
        weather["gulls"].append({
            "x": x - heading * back,  # the others behind the leader...
            "line": y + side,         # ...and above or below it
            "y": y + side,
            "heading": heading,
            "age": index * GULL_LAG,  # each one flaps a little after the one in front
        })


def update_gulls(weather, sky):
    """Before the rain, the seagulls fly over the deck in a fixed pattern (GULL_FLIGHTS), one flight
    every GULL_EVERY frames. Once it rains no new flight takes off; the seagulls in the air fly on
    until they have left the sky. They fly in pixels of the room (`sky` is the deck), so they keep
    their way when the player walks and the view scrolls: they leave the view like the ship does."""
    gulls = weather["gulls"]
    if sky is None:
        gulls.clear()
        return
    if rain_amount(weather["level"]) == 0:
        weather["next_flight"] -= 1
        if weather["next_flight"] <= 0:
            start_flight(weather, sky)
            weather["next_flight"] = GULL_EVERY
    for gull in list(gulls):
        gull["age"] += 1
        gull["x"] += gull["heading"] * GULL_SPEED
        gull["y"] = gull["line"] + round(GULL_WAVE * math.sin(gull["age"] * GULL_WAVE_SPEED))  # a gentle wave
        if gull["x"] < sky.left - 3 * GULL_SIZE or gull["x"] > sky.right + 3 * GULL_SIZE:
            gulls.remove(gull)


def gull_wings(gull):
    """Which picture of the wings a seagull shows now: a few flaps, then a glide."""
    step = (gull["age"] // GULL_FLAP) % (len(GULL_WINGS) + GULL_GLIDE)
    if step < len(GULL_WINGS):
        return GULL_WINGS[step]
    return 1


def update_lightning(weather, view_size):
    """Lightning at irregular moments, more often as the storm comes, and its thunder after it:
    late and soft while the storm is far, sooner and louder as it comes near. Returns the thunder
    to play in this frame, or None."""
    rng = weather["rng"]
    level = weather["level"]
    if weather["flash"] >= 0:
        weather["flash"] += 1
        if weather["flash"] > FLASH_LENGTH:
            weather["flash"] = -1
            weather["bolt"] = None
    heard = None
    for thunder in list(weather["thunders"]):  # first the thunder already on its way...
        thunder["in"] -= 1
        if thunder["in"] <= 0:
            weather["thunders"].remove(thunder)
            if thunder["shake"] and not weather["soft"]:
                weather["shake"] = SHAKE_FRAMES
            if heard is None or thunder["volume"] > heard["volume"]:
                heard = {"name": thunder["name"], "volume": thunder["volume"]}  # two at once: the louder one
    if level >= LIGHTNING_FROM:  # ...then, maybe, a new lightning
        if weather["next_strike"] <= 0:
            weather["next_strike"] = rng.randint(*lightning_gap(level))  # the first one waits too
        else:
            weather["next_strike"] -= 1
            if weather["next_strike"] == 0:
                strike(weather, view_size)
                weather["next_strike"] = rng.randint(*lightning_gap(level))
                if rng.random() < 0.25 * level:
                    weather["next_strike"] = rng.randint(40, 70)  # now and then a second strike follows close
    return heard


def strike(weather, view_size):
    """A lightning strikes now: the flash starts, a bolt may be seen, and its thunder is on its way."""
    rng = weather["rng"]
    level = weather["level"]
    weather["power"] = rng.uniform(0.4, 1.0) * mix(0.35, 1.0, level)
    weather["flash"] = 0
    weather["bolt"] = None
    if level >= BOLT_FROM and rng.random() < (level - 0.45) * 1.4:
        width, height = view_size
        start = (rng.randint(width // 6, width * 5 // 6), 0)
        end = (start[0] + rng.randint(-60, 60), rng.randint(height * 2 // 5, height * 9 // 10))
        weather["bolt"] = bolt_path(start, end, rng)
    if level >= THUNDER_FROM:
        near = level >= NEAR_FROM and weather["power"] > 0.55
        weather["thunders"].append({
            "in": 3 + round(THUNDER_DELAY * (1 - level) * rng.uniform(0.6, 1.0)),
            "name": "thunder_near" if near else "thunder_far",
            "volume": min(1.0, 0.3 + 0.7 * weather["power"] * level),
            "shake": level >= SHAKE_FROM and weather["power"] > 0.7,
        })


def bolt_path(start, end, rng, steps=10, sway=10):
    """The points of a jagged bolt from `start` to `end`."""
    points = [start]
    for step in range(1, steps):
        along = step / steps
        x = start[0] + (end[0] - start[0]) * along + rng.uniform(-sway, sway)
        y = start[1] + (end[1] - start[1]) * along
        points.append((round(x), round(y)))
    points.append(end)
    return points


def flash_strength(weather):
    """How bright the lightning is in this frame, from 0 (no flash) to 1: its power, in flickers."""
    age = weather["flash"]
    if age < 0:
        return 0.0
    flickers = SOFT_FLICKERS if weather["soft"] else FLICKERS
    for first, last, strength in flickers:
        if first <= age <= last:
            fading = 1 - 0.4 * (age - first) / (last - first + 1)  # each flicker dims as it goes
            soft = SOFT_FLASH if weather["soft"] else 1.0
            return weather["power"] * strength * fading * soft
    return 0.0


def shake(weather, frame, power):
    """How far the ship is pushed aside in this frame by the thunder: (dx, dy) in pixels, `power` at most."""
    if weather["shake"] <= 0 or power <= 0:
        return (0, 0)
    reach = power * weather["shake"] / SHAKE_FRAMES
    x = math.sin(frame * 12.9898 + 0.5) * 43758.5453
    y = math.sin(frame * 78.233 + 2.1) * 24634.6345
    x -= math.floor(x)
    y -= math.floor(y)
    return (round((2 * x - 1) * reach), round((2 * y - 1) * reach))


def wave_frame(weather, frames_per_picture, pictures):
    """Which picture of the stormy sea to show: the waves move faster as the storm grows."""
    return int(weather["waves"] // frames_per_picture) % pictures


# --- The clouds ---------------------------------------------------------------------------------


def periodic_noise(x, y, size, seed):
    """Smooth noise from 0 to 1, like scenery.value_noise, but its grid wraps around at the edges of
    CLOUD_SIZE: the picture of the clouds can be repeated with no seam."""
    columns, rows = CLOUD_SIZE[0] // size, CLOUD_SIZE[1] // size
    gx, gy = x / size, y / size
    x0, y0 = math.floor(gx), math.floor(gy)
    fx, fy = gx - x0, gy - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    left, right = x0 % columns, (x0 + 1) % columns
    up, down = y0 % rows, (y0 + 1) % rows
    top = mix(scenery.hash01(left, up, seed), scenery.hash01(right, up, seed), fx)
    bottom = mix(scenery.hash01(left, down, seed), scenery.hash01(right, down, seed), fx)
    return mix(top, bottom, fy)


def cloud_noise():
    """The noise of the clouds, one number for each cell, made once: big shapes, and smaller ones on them."""
    if not _cloud_noise:
        for y in range(CLOUD_SIZE[1]):
            row = []
            for x in range(CLOUD_SIZE[0]):
                row.append(0.65 * periodic_noise(x, y, 24, SEED) + 0.35 * periodic_noise(x, y, 8, SEED + 1))
            _cloud_noise.append(row)
    return _cloud_noise


def cloud_picture(level):
    """The shadows of the clouds over the deck for this level, to multiply into it: white where
    there is no cloud. More clouds and darker ones as the storm grows. Made once for each step."""
    step = round(clamp01(level) * CLOUD_STEPS)
    if step not in _clouds:
        share = step / CLOUD_STEPS
        line = mix(0.66, 0.38, share)  # the noise above this is cloud: lower and lower, more and more clouds
        shadow = mix_color(CLOUD_LIGHT, CLOUD_DARK, share)
        cells = pygame.Surface(CLOUD_SIZE)
        cells.fill((255, 255, 255))
        noise = cloud_noise()
        for y in range(CLOUD_SIZE[1]):
            for x in range(CLOUD_SIZE[0]):
                value = noise[y][x]
                if value > line + CLOUD_EDGE or (value > line and (x + y) % 2 == 0):
                    cells.set_at((x, y), shadow)  # the edge is chequered: half a shadow, the 8-bit way
        size = (CLOUD_SIZE[0] * CLOUD_CELL, CLOUD_SIZE[1] * CLOUD_CELL)
        _clouds[step] = pygame.transform.scale(cells, size)  # no smoothing: big square pixels
    return _clouds[step]


def draw_clouds(screen, view, weather, camera):
    """The shadows of the clouds drifting over the deck. They move with the wind and stay put on the
    ship when the view scrolls: `camera` is where the view is in the room."""
    picture = cloud_picture(weather["level"])
    width, height = picture.get_size()
    x = round(weather["cloud_x"] + camera[0]) % width
    y = round(weather["cloud_y"] + camera[1]) % height
    for dx in (0, width):
        for dy in (0, height):
            screen.blit(picture, (view.left - x + dx, view.top - y + dy), special_flags=pygame.BLEND_RGB_MULT)


# --- Drawing ----------------------------------------------------------------------------------


def sky_tint(level, exposure):
    """What the storm multiplies into the view: white in the calm, darker and bluer as it grows.
    `exposure` is how much of the weather reaches the room: 1 on the deck, less inside the ship."""
    return mix_color((255, 255, 255), SKY_DARK, darkness(level) * exposure)


def draw(screen, view, weather, outdoor, exposure, camera):
    """The weather over the view of the room on screen: the darker sky, and on the deck the clouds,
    the rain, the bolts and the seagulls; everywhere, the flashes of lightning. `exposure` (from 0 to 1)
    is how much of it reaches the room: nothing at all in the mine, deep in the rock."""
    if exposure <= 0:
        return
    screen.set_clip(view)
    tint = sky_tint(weather["level"], exposure)
    if tint != (255, 255, 255):
        screen.fill(tint, view, special_flags=pygame.BLEND_RGB_MULT)
    if outdoor:
        draw_clouds(screen, view, weather, camera)
        draw_rain(screen, view, weather)
        draw_bolt(screen, view, weather)
        draw_gulls(screen, weather, camera)
    strength = flash_strength(weather) * (exposure if outdoor else exposure * INDOOR_FLASH)
    if strength > 0:
        add = tuple(round(part * strength) for part in FLASH_COLOR)
        screen.fill(add, view, special_flags=pygame.BLEND_RGB_ADD)
    screen.set_clip(None)


def draw_rain(screen, view, weather):
    """Each drop is a short slanted line, one pixel wide; each splash a dot, then a little crown."""
    slant = -WIND_SLANT * weather["wind"]
    for drop in weather["drops"]:
        x = view.left + drop["x"]
        y = view.top + drop["y"]
        dx = slant * drop["speed"] / 5 * drop["length"] / drop["speed"]
        tail = (round(x - dx), round(y - drop["length"]))
        pygame.draw.line(screen, drop["color"], tail, (round(x), round(y)))
    for x, y, age in weather["splashes"]:
        x += view.left
        y += view.top
        if age < 2:
            screen.fill(SPLASH_COLOR, (x, y, 1, 1))
        else:
            screen.fill(SPLASH_COLOR, (x - 2, y, 1, 1))
            screen.fill(SPLASH_COLOR, (x + 2, y, 1, 1))
            screen.fill(SPLASH_COLOR, (x, y - 1, 1, 1))


def draw_gulls(screen, weather, camera):
    """The seagulls, flapping and gliding. They are in pixels of the room, like everything on the
    deck: `camera` is where the view is in the room, so they stay on their way when it scrolls."""
    for gull in weather["gulls"]:
        picture = sprites.image("seagull_" + str(gull_wings(gull)), flip=gull["heading"] > 0)
        if picture is None:
            continue
        screen.blit(picture, (round(gull["x"]) - camera[0], round(gull["y"]) - camera[1]))


def draw_bolt(screen, view, weather):
    """The bolt of a lightning, while it flickers: a pale glow and a white core, in hard pixels."""
    if weather["bolt"] is None or flash_strength(weather) <= 0:
        return
    points = [(view.left + x, view.top + y) for x, y in weather["bolt"]]
    pygame.draw.lines(screen, BOLT_GLOW, False, points, 3)
    pygame.draw.lines(screen, BOLT_CORE, False, points, 1)


def draw_puddles(surface, spots, level, frame):
    """The puddles on the deck, in room pixels: they form as the rain grows and spread as it pours,
    and now and then a drop rings on them. `spots` are the tiles where they lie."""
    wet = clamp01((level - PUDDLE_FROM) / (1 - PUDDLE_FROM))
    if wet <= 0:
        return
    for index, spot in enumerate(spots):
        grow = wet * (0.6 + 0.4 * scenery.hash01(index, 3, 17))  # each puddle its own size
        area = pygame.Rect(0, 0, max(2, round(12 * grow)), max(1, round(5 * grow)))
        area.center = spot.center
        pygame.draw.ellipse(surface, PUDDLE_COLOR, area)
        if area.width >= 6:
            surface.fill(PUDDLE_LIGHT, (area.left + 2, area.top, area.width // 3, 1))  # the light on its edge
            moment = (frame + index * 13) % RIPPLE_EVERY
            if moment < 6:  # a drop falls in it: a ring that opens
                ring = pygame.Rect(0, 0, 1 + moment, 1 + moment // 3)
                ring.center = (area.left + 2 + round(scenery.hash01(index, frame // RIPPLE_EVERY, 5) * (area.width - 4)),
                               area.centery)
                pygame.draw.rect(surface, PUDDLE_LIGHT, ring, 1)
