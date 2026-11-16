"""The scenery of the rooms: floors, walls and the shading of the furniture, drawn in code.

The floor and wall pictures of sprites.py are one tile each: repeated in every
tile, the same plank seam or crack comes back every 16 pixels. Here the floor of a
whole room is built once, with details that depend on where they are (x, y): planks
of different lengths that do not line up, grain, knots and nails in the wood, cracks
and damp stains in the stone, pebbles in the earth. Everything comes from a hash of
the coordinates, never from chance: the same room always looks the same.

The walls get some depth (a "2.5D" look): the back wall shows its top edge and its
face, the others their top, and the walls cast a short shadow on the floor next to
them. The light comes from the top left, as for the giant claw and the characters.

The furniture is shaded the same way: a lighter edge where the light falls, a darker
one on the other side, and an outline that is not plain black but a dark shade of
the colour it surrounds, a little bluer (hue shifting: shadows are cool).

Some of the ways of doing it come from the examples of Pyxel (github.com/kitao/pyxel):
continuous noise cut into a few hard bands of colour, and half-transparency made with
a chequered dither. This module knows nothing about the game: main.py says which room
is made of what.
"""

import math

import pygame

TILE = 16
SHADOW = (10, 8, 26)          # the colour of every shadow: almost black, a little blue
SHADOW_ALPHA = 110            # how dark a shadow on the floor is, where it is solid
WALL_SHADOW = (4, 3)          # how far the shadow of the back wall and of the left wall reach onto the floor
CAP = 4                       # the top edge of the back wall, in pixels
DAMP = (0.64, 0.75)           # where the damp noise starts to stain: dithered, then solid
DAMP_TINT = (199, 210, 224)   # what damp does to a colour (multiplied): darker, and towards blue-green
SLAB_DARKER = (226, 228, 240)  # the same for a darker stone slab
SLAB_LIGHTER = (12, 10, 6)    # added to a lighter one
WALL_TOP_LIGHT = (14, 11, 6)  # added to the top of a wall: it catches the light

_backgrounds = {}             # (key) -> a room's floor and walls, made once
_shaded = {}                  # (name) -> a picture with its shading, made once
_ground = {}                  # (width, height) -> an oval shadow, made once


# --- Numbers from coordinates -------------------------------------------------------------


def hash01(x, y, seed=0):
    """A number from 0 to 1 that looks random but only depends on (x, y) and the seed."""
    n = (x * 374761393 + y * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65536


def seed_of(name):
    """A whole number from a name, always the same (Python's own hash() changes at every run)."""
    return sum((index + 1) * ord(letter) for index, letter in enumerate(name))


def value_noise(x, y, size, seed):
    """Smooth noise from 0 to 1: random values on a grid `size` pixels apart, blended in between."""
    gx, gy = x / size, y / size
    x0, y0 = math.floor(gx), math.floor(gy)
    fx, fy = gx - x0, gy - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    top = hash01(x0, y0, seed) * (1 - fx) + hash01(x0 + 1, y0, seed) * fx
    bottom = hash01(x0, y0 + 1, seed) * (1 - fx) + hash01(x0 + 1, y0 + 1, seed) * fx
    return top * (1 - fy) + bottom * fy


# --- Colours -------------------------------------------------------------------------------


def clamp(value):
    return max(0, min(255, int(round(value))))


def darker(color, amount):
    """A darker colour, a little bluer: the shadow side of something."""
    r, g, b = color[:3]
    keep = 1 - amount
    return (clamp(r * keep - 4 * amount), clamp(g * keep - 2 * amount), clamp(b * keep + 22 * amount))


def lighter(color, amount):
    """A lighter colour, a little warmer: the side the light falls on."""
    r, g, b = color[:3]
    return (clamp(r + (255 - r) * amount + 10 * amount), clamp(g + (255 - g) * amount + 4 * amount),
            clamp(b + (255 - b) * amount - 8 * amount))


def blend(one, two, share):
    return tuple(clamp(a + (b - a) * share) for a, b in zip(one[:3], two[:3]))


def brightness(color):
    r, g, b = color[:3]
    return 0.3 * r + 0.59 * g + 0.11 * b


_colors = {}


def colors_of(picture):
    """The colours of a picture, the most used first (worked out once for each picture)."""
    key = id(picture), picture.get_size()
    if key in _colors and _colors[key][0] is picture:
        return _colors[key][1]
    count = {}
    for x in range(picture.get_width()):
        for y in range(picture.get_height()):
            color = tuple(picture.get_at((x, y)))
            if color[3]:
                count[color[:3]] = count.get(color[:3], 0) + 1
    result = sorted(count, key=lambda color: -count[color])
    _colors[key] = (picture, result)
    return result


def dot(surface, x, y, color):
    if 0 <= x < surface.get_width() and 0 <= y < surface.get_height():
        surface.set_at((x, y), color)


# --- Floors --------------------------------------------------------------------------------


def wood_floor(surface, area, tile, seed):
    """Planks four pixels wide, of different lengths, their ends never lined up: grain, knots,
    nails at their ends, some a little darker or lighter than the others."""
    colors = colors_of(tile)
    plank = colors[0]
    seam = min(colors[:3], key=brightness)
    grain = blend(plank, seam, 0.4)
    worn = lighter(plank, 0.12)
    nail = blend(seam, (176, 176, 190), 0.55)
    surface.fill(plank, area)
    for strip, y in enumerate(range(area.top, area.bottom, 4)):
        surface.fill(seam, (area.left, y + 3, area.width, 1))  # the gap between two rows of planks
        x = area.left - int(hash01(strip, 0, seed) * 40)  # where the first plank of the row starts: never the same
        while x < area.right:
            length = 20 + int(hash01(x, strip, seed) * 36)
            mood = hash01(strip, x, seed + 1)
            plank_area = pygame.Rect(x + 1, y, length - 1, 3).clip(area)
            if mood < 0.22:
                for px in range(plank_area.left, plank_area.right):  # a darker plank: dithered, not flat
                    for py in range(plank_area.top, plank_area.bottom):
                        if (px + py) % 2 == 0:
                            surface.set_at((px, py), grain)
            elif mood > 0.82:
                surface.fill(worn, (plank_area.left, plank_area.top, plank_area.width, 1))  # worn by feet
            for streak in range(1 + int(hash01(x, strip, seed + 2) * 2)):  # the grain of the wood
                sx = x + 3 + int(hash01(x + streak, strip, seed + 3) * max(length - 10, 1))
                sy = y + int(hash01(x, strip + streak, seed + 4) * 3)
                span = 3 + int(hash01(sx, sy, seed + 5) * 6)
                surface.fill(grain, pygame.Rect(sx, sy, span, 1).clip(plank_area))
            if hash01(x, strip, seed + 6) < 0.12:  # a knot
                kx = x + 4 + int(hash01(strip, x, seed + 7) * max(length - 8, 1))
                if area.left <= kx < area.right - 2:
                    surface.fill(seam, (kx, y + 1, 2, 1))
                    dot(surface, kx - 1, y + 1, grain)
                    dot(surface, kx + 2, y + 1, grain)
            if area.left <= x < area.right:
                surface.fill(seam, (x, y, 1, 3))  # the end of the plank
                for nx in (x - 2, x + 2):  # a nail on each side of it
                    if area.left <= nx < area.right:
                        dot(surface, nx, y + 1, nail)
            x += length


def stone_floor(surface, area, tile, seed, polished=False):
    """The stone slabs of the picture, but each a little different: darker or lighter ones,
    cracks, chipped corners. Polished floors (marble, tiles) get only a few hairlines."""
    colors = colors_of(tile)
    mortar = min(colors[:3], key=brightness)
    for left in range(area.left, area.right, TILE):
        for top in range(area.top, area.bottom, TILE):
            surface.blit(tile, (left, top))
            col, row = left // TILE, top // TILE
            mood = hash01(col, row, seed)
            slab = pygame.Rect(left, top, TILE, TILE)
            if not polished and mood < 0.25:  # a slab darker than the others, a little bluer
                surface.fill(SLAB_DARKER, slab, special_flags=pygame.BLEND_RGB_MULT)
            elif not polished and mood > 0.8:  # or lighter, a little warmer
                surface.fill(SLAB_LIGHTER, slab, special_flags=pygame.BLEND_RGB_ADD)
            if not polished:
                chips(surface, left, top, col, row, seed, mortar)  # every slab: its own few chips
            if hash01(col, row, seed + 1) < (0.14 if polished else 0.32):
                crack(surface, left, top, seed + col * 7 + row * 13, mortar, polished)


def chips(surface, left, top, col, row, seed, dark):
    """Two or three chips in a tile: a dark pixel with a light one above it, where they fall depends
    on the tile. So no two tiles of the same floor are alike."""
    for chip in range(2 + int(hash01(col, row, seed + 40) * 2)):
        x = left + 1 + int(hash01(col, row, seed + 41 + chip) * 14)
        y = top + 2 + int(hash01(row, col, seed + 51 + chip) * 12)
        if y - 1 >= top:
            dot(surface, x, y - 1, lighter(tuple(surface.get_at((x, y - 1)))[:3], 0.2))
        dot(surface, x, y, dark)


def crack(surface, left, top, seed, color, short=False):
    """A thin crack across part of a tile: a zigzag, with a light chip beside it."""
    x = left + 3 + int(hash01(seed, 1) * 9)
    y = top + 2 + int(hash01(seed, 2) * 9)
    length = (3 if short else 5) + int(hash01(seed, 3) * 4)
    for step in range(length):
        if not (left < x < left + TILE - 1 and top < y < top + TILE - 1):
            break
        dot(surface, x, y, color)
        if step == 1:
            dot(surface, x + 1, y - 1, lighter(tuple(surface.get_at((x + 1, y - 1)))[:3], 0.25))
        x += 1
        y += 1 if hash01(seed, step + 10) < 0.5 else -1 if hash01(seed, step + 20) < 0.3 else 0


def earth_floor(surface, area, tile, seed):
    """Packed earth: the picture, with pebbles here and there, and cracks."""
    colors = colors_of(tile)
    dark = darker(colors[0], 0.35)
    for left in range(area.left, area.right, TILE):
        for top in range(area.top, area.bottom, TILE):
            surface.blit(tile, (left, top))
            col, row = left // TILE, top // TILE
            for pebble in range(int(hash01(col, row, seed) * 3)):
                px = left + 2 + int(hash01(col, row, seed + 10 + pebble) * 11)
                py = top + 2 + int(hash01(row, col, seed + 20 + pebble) * 11)
                surface.fill((96, 96, 112), (px, py, 2, 2))
                dot(surface, px, py, (176, 176, 190))  # lit from the top left
                dot(surface, px + 2, py + 1, dark)
                dot(surface, px + 1, py + 2, dark)
            chips(surface, left, top, col, row, seed, dark)
            if hash01(col, row, seed + 2) < 0.2:
                crack(surface, left, top, seed + col * 5 + row * 11, dark)


def damp(surface, area, seed, strength=1.0):
    """Stains of damp: smooth noise, cut into hard bands like on an old console (dithered where it
    starts, solid where it is wettest), darker and greener-blue where it is wet."""
    dither = pygame.Surface((2, 2))
    dither.fill((255, 255, 255))
    dither.set_at((0, 0), DAMP_TINT)
    dither.set_at((1, 1), DAMP_TINT)
    for y in range(area.top, area.bottom, 2):
        for x in range(area.left, area.right, 2):
            wet = value_noise(x, y, 26, seed) * 0.7 + value_noise(x, y, 9, seed + 3) * 0.3
            wet = wet * strength
            if wet < DAMP[0]:
                continue
            block = pygame.Rect(x, y, 2, 2).clip(area)
            if wet >= DAMP[1]:
                surface.fill(DAMP_TINT, block, special_flags=pygame.BLEND_RGB_MULT)  # wettest: solid
            else:
                surface.blit(dither, block, special_flags=pygame.BLEND_RGB_MULT)  # where it starts: every other pixel


# --- Walls ---------------------------------------------------------------------------------


def back_wall(surface, rect, wall, seed, stained=False):
    """A tile of the back wall, seen from the front: its top edge (light, with a dark line under
    it), its face with the picture of the wall, darker towards the floor; streaks of damp if stained."""
    surface.blit(wall, rect)
    colors = colors_of(wall)
    face = colors[0]
    top = lighter(max(colors[:3], key=brightness), 0.25)
    surface.fill(top, (rect.left, rect.top, rect.width, CAP - 1))
    surface.fill(lighter(top, 0.3), (rect.left, rect.top, rect.width, 1))
    surface.fill(darker(face, 0.55), (rect.left, rect.top + CAP - 1, rect.width, 1))
    for row, amount in ((rect.bottom - 3, 0.18), (rect.bottom - 2, 0.3), (rect.bottom - 1, 0.45)):
        for px in range(rect.left, rect.right):  # the foot of the wall, in the shade
            surface.set_at((px, row), darker(tuple(surface.get_at((px, row)))[:3], amount))
    if stained and hash01(rect.left // TILE, 0, seed) < 0.45:  # water running down from the top
        sx = rect.left + 2 + int(hash01(rect.left, 1, seed) * 12)
        for py in range(rect.top + CAP, rect.top + CAP + 4 + int(hash01(rect.left, 2, seed) * 8)):
            surface.set_at((sx, py), darker(tuple(surface.get_at((sx, py)))[:3], 0.3))


def wall_top(surface, rect, wall, inner):
    """A tile of a side or front wall, seen from above: the picture of the wall, lighter (its top
    catches the light), with a light line along the edge that faces the room (`inner`: "left",
    "right" or "top") and a dark one where the wall drops to the floor."""
    surface.blit(wall, rect)
    surface.fill(WALL_TOP_LIGHT, rect, special_flags=pygame.BLEND_RGB_ADD)
    top = lighter(colors_of(wall)[0], 0.35)
    edges = {"left": (rect.left, rect.top, 1, rect.height), "right": (rect.right - 1, rect.top, 1, rect.height),
             "top": (rect.left, rect.top, rect.width, 1)}
    surface.fill(top, edges[inner])


def contact_shadow(surface, area, side, reach):
    """The shadow a wall casts on the floor beside it: solid next to the wall, dithered further out."""
    shade = pygame.Surface(area.size, pygame.SRCALPHA)
    for step in range(reach):
        alpha = SHADOW_ALPHA if step < reach // 2 else SHADOW_ALPHA * 3 // 4
        dithered = step >= reach // 2
        if side == "top":
            for px in range(area.width):
                if not dithered or (px + step) % 2 == 0:
                    shade.set_at((px, step), SHADOW + (alpha,))
        else:
            for py in range(area.height):
                if not dithered or (py + step) % 2 == 0:
                    shade.set_at((step, py), SHADOW + (alpha,))
    surface.blit(shade, area.topleft)


def background(key, columns, rows, floor, wall, material, outdoor, seed, stained=False):
    """The floor and walls of a room, made once and kept: a picture of columns x rows tiles.

    `material` is "wood", "stone", "tiles" or "earth"; an outdoor room has no walls of its own
    (the sea is there), so it gets none of their depth.
    """
    if key in _backgrounds:
        return _backgrounds[key]
    picture = pygame.Surface((columns * TILE, rows * TILE))
    inside = pygame.Rect(TILE, TILE, (columns - 2) * TILE, (rows - 2) * TILE)
    if material == "wood":
        wood_floor(picture, inside, floor, seed)
    elif material == "earth":
        earth_floor(picture, inside, floor, seed)
    else:
        stone_floor(picture, inside, floor, seed, polished=material == "tiles")
    if stained:
        damp(picture, inside, seed)
    for col in range(columns):
        for row in range(rows):
            if inside.collidepoint(col * TILE, row * TILE):
                continue
            rect = pygame.Rect(col * TILE, row * TILE, TILE, TILE)
            if outdoor:
                picture.blit(wall, rect)
            elif row == 0:
                back_wall(picture, rect, wall, seed, stained)
            elif col == 0:
                wall_top(picture, rect, wall, "right")
            elif col == columns - 1:
                wall_top(picture, rect, wall, "left")
            else:
                wall_top(picture, rect, wall, "top")
    if not outdoor:
        contact_shadow(picture, pygame.Rect(inside.left, inside.top, inside.width, WALL_SHADOW[0]), "top",
                       WALL_SHADOW[0])
        contact_shadow(picture, pygame.Rect(inside.left, inside.top, WALL_SHADOW[1], inside.height), "left",
                       WALL_SHADOW[1])
    _backgrounds[key] = picture
    return picture


# --- Furniture ------------------------------------------------------------------------------


OUTLINE = (20, 16, 28)  # the plain outline of the pictures in sprites.py


def shaded(name, picture):
    """A picture of furniture with its shading, made once and kept under `name`.

    The plain black outline becomes a dark shade of the colour inside it, a little bluer.
    Inside, the pixels with the open air or the outline above or to the left of them get
    lighter (the light comes from the top left), those with it below or to the right darker:
    four tones in all, from the outline to the light edge.
    """
    if name in _shaded:
        return _shaded[name]
    width, height = picture.get_size()
    pixels = [[tuple(picture.get_at((x, y))) for y in range(height)] for x in range(width)]

    def at(x, y):
        if 0 <= x < width and 0 <= y < height:
            return pixels[x][y]
        return (0, 0, 0, 0)

    def solid(color):
        return color[3] > 0 and color[:3] != OUTLINE

    def edge(color):
        return color[3] == 0 or color[:3] == OUTLINE

    result = picture.copy()
    for x in range(width):
        for y in range(height):
            color = pixels[x][y]
            if not color[3]:
                continue
            if color[:3] == OUTLINE:
                near = [at(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
                near = [one for one in near if solid(one)]
                if not near:
                    near = [at(x + dx, y + dy) for dx in (-2, 0, 2) for dy in (-2, 0, 2)]
                    near = [one for one in near if solid(one)]
                if near:
                    inside = tuple(sum(one[index] for one in near) / len(near) for index in range(3))
                    dark = darker(inside, 0.68)
                    result.set_at((x, y), dark + (color[3],))
                continue
            lit = edge(at(x, y - 1)) or edge(at(x - 1, y))
            shade = edge(at(x, y + 1)) or edge(at(x + 1, y))
            if lit and not shade:
                result.set_at((x, y), lighter(color, 0.16) + (color[3],))
            elif shade and not lit:
                result.set_at((x, y), darker(color, 0.16) + (color[3],))
    _shaded[name] = result
    return result


def ground_shadow(width, height):
    """The shadow of something standing on the floor: an oval, solid in the middle and dithered
    around it (half-transparent, the old way)."""
    key = (width, height)
    if key not in _ground:
        picture = pygame.Surface((width, height), pygame.SRCALPHA)
        inner = pygame.Rect(0, 0, max(width - 4, 1), max(height - 2, 1))
        inner.center = (width // 2, height // 2)
        cx, cy = (width - 1) / 2, (height - 1) / 2
        for x in range(width):
            for y in range(height):
                outside = ((x - cx) / (width / 2)) ** 2 + ((y - cy) / (height / 2)) ** 2
                middle = ((x - cx) / (inner.width / 2)) ** 2 + ((y - cy) / (inner.height / 2)) ** 2
                if middle <= 1:
                    picture.set_at((x, y), SHADOW + (SHADOW_ALPHA,))
                elif outside <= 1 and (x + y) % 2 == 0:
                    picture.set_at((x, y), SHADOW + (SHADOW_ALPHA,))
        _ground[key] = picture
    return _ground[key]
