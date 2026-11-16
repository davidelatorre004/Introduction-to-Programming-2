"""Tests for the scenery: floors and walls with details, the depth of the walls, the shading of furniture."""

import pygame
import pytest

import scenery
import sprites
import story


@pytest.fixture(autouse=True)
def display():
    pygame.display.set_mode((1, 1))


def colors(surface, area=None):
    area = area or surface.get_rect()
    return [tuple(surface.get_at((x, y)))[:3] for x in range(area.left, area.right) for y in range(area.top, area.bottom)]


def tile(surface, col, row):
    return colors(surface, pygame.Rect(col * 16, row * 16, 16, 16))


def build(room, columns=10, rows=8, key=None):
    info = story.ROOMS[room]
    wall = sprites.image("wall_" + room) or sprites.image("wall_" + room + "_0")
    return scenery.background(key or ("test", room, columns, rows), columns, rows, sprites.image("floor_" + room), wall,
                              info["floor"], info["outdoor"], scenery.seed_of(room), info.get("damp", False))


# --- Numbers from coordinates ------------------------------------------------------------------


def test_the_hash_depends_only_on_the_coordinates_and_the_seed():
    values = [scenery.hash01(x, y, 3) for x in range(40) for y in range(40)]
    assert all(0 <= value < 1 for value in values)
    assert len(set(values)) > 1500  # spread out, not a few values
    assert 0.4 < sum(values) / len(values) < 0.6
    assert scenery.hash01(5, 9, 3) == scenery.hash01(5, 9, 3) != scenery.hash01(9, 5, 3)
    assert scenery.hash01(5, 9, 3) != scenery.hash01(5, 9, 4)
    assert scenery.seed_of("cabin") == scenery.seed_of("cabin") != scenery.seed_of("galley")


def test_value_noise_is_smooth():
    row = [scenery.value_noise(x, 10, 20, 7) for x in range(200)]
    assert all(0 <= value <= 1 for value in row)
    assert max(abs(one - two) for one, two in zip(row, row[1:])) < 0.12  # no jumps from a pixel to the next
    assert max(row) - min(row) > 0.4  # but it does change across the room


# --- Floors -----------------------------------------------------------------------------------


def test_every_room_has_a_floor_material():
    assert {info["floor"] for info in story.ROOMS.values()} <= {"wood", "stone", "tiles", "earth"}
    assert story.ROOMS["cabin"]["floor"] == "wood" and story.ROOMS["hold"]["floor"] == "stone"
    assert story.ROOMS["mine"]["floor"] == "earth" and story.ROOMS["infirmary"]["floor"] == "tiles"
    assert {room for room, info in story.ROOMS.items() if info.get("damp")} == {"hold", "corridor", "corridor_end", "mine"}


@pytest.mark.parametrize("room", ["cabin", "hold", "mine", "infirmary"])
def test_no_two_tiles_of_a_floor_are_the_same(room):
    picture = build(room)
    tiles = [tuple(tile(picture, col, row)) for col in range(1, 9) for row in range(1, 7)]
    assert len(set(tiles)) >= len(tiles) * (0.95 if room != "infirmary" else 0.2)  # polished floors: a few hairlines


def test_the_same_room_is_always_drawn_the_same():
    one = build("hold", key=("same", 1))
    two = build("hold", key=("same", 2))
    assert colors(one) == colors(two)
    assert build("hold", key=("same", 1)) is one  # and it is built only once


def test_wooden_planks_do_not_line_up_and_have_nails_and_grain():
    picture = build("cabin", columns=16, rows=8, key=("planks",))
    plank = scenery.colors_of(sprites.image("floor_cabin"))[0]
    seam = min(scenery.colors_of(sprites.image("floor_cabin"))[:3], key=scenery.brightness)
    ends = []
    for strip in range(4, 4 * 24, 4):
        y = 16 + strip
        if y + 3 > 16 * 7:
            break
        ends.append(tuple(x for x in range(17, 16 * 15 - 1) if tuple(picture.get_at((x, y)))[:3] == seam
                          and tuple(picture.get_at((x, y + 2)))[:3] == seam))
        assert tuple(picture.get_at((40, y - 1)))[:3] == seam  # the gap between two rows of planks
    assert len(set(ends)) == len(ends)  # no two rows of planks end in the same places
    gaps = [two - one for row in ends for one, two in zip(row, row[1:])]
    assert min(gaps) >= 18 and max(gaps) > 32  # planks of different lengths
    nails = sum(1 for color in colors(picture) if scenery.brightness(color) > scenery.brightness(plank) + 15)
    assert nails > 20
    shades = set(colors(picture, pygame.Rect(16, 16, 16 * 14, 16 * 6)))
    assert len(shades) >= 5  # plank, gap, grain, a lighter worn edge, nails


def test_stone_floors_have_cracks_and_damp_stains():
    dry = build("hold", key=("dry",))
    info = story.ROOMS["hold"]
    floor = sprites.image("floor_hold")
    plain = pygame.Surface((160, 128))
    for col in range(10):
        for row in range(8):
            plain.blit(floor, (col * 16, row * 16))
    inside = pygame.Rect(16, 16, 128, 96)
    changed = sum(1 for one, two in zip(colors(dry, inside), colors(plain, inside)) if one != two)
    assert changed > 1000  # slabs darker and lighter, cracks, damp
    assert info["damp"]
    bluer = sum(1 for one, two in zip(colors(dry, inside), colors(plain, inside))
                if one != two and one[2] - one[0] > two[2] - two[0])
    assert bluer > 100  # the damp is darker and bluer


def test_damp_comes_in_hard_bands_dithered_where_it_starts():
    surface = pygame.Surface((200, 120))
    surface.fill((120, 120, 120))
    scenery.damp(surface, surface.get_rect(), 5)
    seen = set(colors(surface))
    assert len(seen) == 2 and (120, 120, 120) in seen  # dry, or wet: one hard band of colour, no fade
    wet = (seen - {(120, 120, 120)}).pop()
    assert sum(wet) < 360 and wet[2] > wet[0]  # darker, and bluer
    dithered = solid = 0
    for x in range(0, 200, 2):
        for y in range(0, 120, 2):
            block = [tuple(surface.get_at((x + dx, y + dy)))[:3] for dx in (0, 1) for dy in (0, 1)]
            wet = sum(1 for color in block if color != (120, 120, 120))
            dithered += wet == 2
            solid += wet == 4
    assert dithered > 20 and solid > 5


# --- Walls ------------------------------------------------------------------------------------


def test_the_back_wall_has_a_light_top_a_face_and_a_dark_foot():
    picture = build("galley", key=("wall",))

    def row(y):  # how bright a row of the back wall is, on average
        return sum(scenery.brightness(picture.get_at((x, y))) for x in range(16, 16 * 9)) / (16 * 8)
    top, under_cap = row(0), row(scenery.CAP - 1)
    face = sum(row(y) for y in range(scenery.CAP, 13)) / (13 - scenery.CAP)
    foot = row(15)
    assert top > face > foot  # lit on top, darker down to the floor
    assert under_cap < face  # a dark line where the top meets the face
    assert row(1) > row(scenery.CAP + 1)


def test_the_walls_cast_a_short_shadow_on_the_floor():
    picture = build("galley", key=("shadow",))

    def row(y):
        return sum(scenery.brightness(picture.get_at((x, y))) for x in range(20, 140)) / 120

    def column(x):
        return sum(scenery.brightness(picture.get_at((x, y))) for y in range(20, 100)) / 80
    open_floor = sum(row(y) for y in range(28, 60)) / 32
    assert row(16) < open_floor * 0.75 and row(17) < open_floor * 0.75  # right under the back wall: solid shade
    assert row(16 + scenery.WALL_SHADOW[0] - 1) < open_floor  # dithered further out
    assert open_floor * 0.9 < row(16 + scenery.WALL_SHADOW[0] + 2)  # and then the floor as it is
    open_column = sum(column(x) for x in range(30, 60)) / 30
    assert column(16) < open_column * 0.8  # beside the left wall too


def test_the_side_walls_show_their_top_with_a_light_edge_on_the_room_side():
    picture = build("galley", key=("sides",))
    wall = sprites.image("wall_galley")
    assert scenery.brightness(picture.get_at((15, 40))) > scenery.brightness(picture.get_at((8, 40)))  # left wall
    assert scenery.brightness(picture.get_at((9 * 16, 40))) > scenery.brightness(picture.get_at((9 * 16 + 8, 40)))
    plain = scenery.brightness(wall.get_at((8, 8)))
    assert scenery.brightness(picture.get_at((8, 16 * 3 + 8))) > plain  # the top catches the light


def test_an_outdoor_room_keeps_its_sea_and_gets_no_walls():
    picture = build("deck", key=("deck",))
    sea = sprites.image("wall_deck_0")
    assert colors(picture, pygame.Rect(0, 0, 16, 16)) == colors(sea)


# --- Furniture --------------------------------------------------------------------------------


def test_furniture_has_no_plain_black_outline_but_a_dark_shade_of_its_colour():
    for name in ("decor_barrel", "decor_crate", "decor_bed", "decor_stove", "decor_table"):
        plain = sprites.image(name)
        shaded = scenery.shaded(name, plain)
        assert shaded.get_size() == plain.get_size()
        outline = [(x, y) for x in range(16) for y in range(16) if tuple(plain.get_at((x, y)))[:3] == scenery.OUTLINE
                   and plain.get_at((x, y))[3]]
        assert outline
        for x, y in outline:
            assert tuple(shaded.get_at((x, y)))[:3] != scenery.OUTLINE, (name, x, y)
            assert scenery.brightness(shaded.get_at((x, y))) < 90, (name, x, y)  # still dark: a clean edge
        alpha = [plain.get_at((x, y))[3] == shaded.get_at((x, y))[3] for x in range(16) for y in range(16)]
        assert all(alpha)  # the same shape


def test_shading_is_lighter_on_the_top_left_and_darker_on_the_bottom_right():
    plain = sprites.image("decor_crate")
    shaded = scenery.shaded("decor_crate", plain)
    lighter = darker = 0
    for x in range(16):
        for y in range(16):
            one, two = plain.get_at((x, y)), shaded.get_at((x, y))
            if not one[3] or tuple(one)[:3] == scenery.OUTLINE:
                continue
            if scenery.brightness(two) > scenery.brightness(one):
                lighter += 1
                assert x < 13 and y < 13
            elif scenery.brightness(two) < scenery.brightness(one):
                darker += 1
    assert lighter > 10 and darker > 10
    assert scenery.shaded("decor_crate", plain) is shaded  # made once


def test_the_hue_shifts_cool_in_the_shade_and_warm_in_the_light():
    red = (214, 64, 52)
    dark, light = scenery.darker(red, 0.4), scenery.lighter(red, 0.2)
    assert scenery.brightness(dark) < scenery.brightness(red) < scenery.brightness(light)
    assert dark[2] / max(dark[0], 1) > red[2] / red[0]  # bluer in the shade
    assert light[2] / light[0] < (red[2] + (255 - red[2]) * 0.2) / (red[0] + (255 - red[0]) * 0.2)  # warmer in the light


def test_the_ground_shadow_is_an_oval_solid_in_the_middle_and_dithered_around():
    shadow = scenery.ground_shadow(14, 5)
    assert shadow.get_size() == (14, 5)
    assert shadow.get_at((7, 2))[3] == scenery.SHADOW_ALPHA  # solid in the middle
    assert shadow.get_at((0, 0))[3] == 0 and shadow.get_at((13, 4))[3] == 0  # round: no corners
    edge = [shadow.get_at((x, 2))[3] for x in range(0, 3)]
    assert 0 in edge and scenery.SHADOW_ALPHA in edge  # dithered at its ends
    assert set(shadow.get_at((x, y))[3] for x in range(14) for y in range(5)) == {0, scenery.SHADOW_ALPHA}
    assert scenery.ground_shadow(14, 5) is shadow
