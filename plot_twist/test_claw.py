"""Tests for the giant claw: where its joints are at each moment of the attack, and how it is painted."""

import math

import pygame
import pytest

import claw

SIZE = (256, 224)
REACH, ATTACK, IMPACT, RETREAT = 10, 15, 27, 12
TONES = {claw.OUTLINE, claw.SHADOW, claw.BASE, claw.LIGHT, claw.PLATE, claw.TOOTH}


def pose(age):
    return claw.pose(age, SIZE, REACH, ATTACK, IMPACT, RETREAT)


def gap(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def angle(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])


def turn(first, second):
    """The angle between two directions, in degrees, from 0 to 180."""
    return abs(math.degrees(math.atan2(math.sin(first - second), math.cos(first - second))))


def painted(age):
    pygame.display.set_mode((1, 1))
    return claw.layer(SIZE, pose(age))


def pixels(picture):
    return [(x, y, tuple(picture.get_at((x, y)))) for x in range(SIZE[0]) for y in range(SIZE[1])]


# --- The pose ---------------------------------------------------------------------------------


def test_the_claw_comes_in_from_outside_and_closes_on_the_middle_of_the_screen():
    screen = pygame.Rect(0, 0, *SIZE)
    middle = (SIZE[0] / 2, SIZE[1] / 2)
    assert not screen.collidepoint(pose(0)["tip"])
    assert all(color[3] == 0 for x, y, color in pixels(painted(0)))  # nothing of it in sight before it strikes
    gaps = [gap(pose(age)["tip"], middle) for age in range(ATTACK)]
    assert gaps == sorted(gaps, reverse=True) and gaps[0] > 150  # closer and closer
    assert gap(pose(REACH)["tip"], middle) < 0.01 and pose(REACH)["opening"] == claw.JAW_OPEN  # there, still open
    openings = [pose(age)["opening"] for age in range(REACH, ATTACK)]
    assert openings == sorted(openings, reverse=True) and openings[-1] == 0.0  # the jaws shut
    assert gap(pose(ATTACK - 1)["tip"], middle) < 0.01


def test_the_limb_has_three_segments_that_keep_their_length_and_stand_at_an_angle():
    for age in range(0, IMPACT + RETREAT + 2):
        limb = pose(age)
        assert gap(limb["shoulder"], limb["elbow"]) == pytest.approx(claw.UPPER_ARM, abs=0.01), age
        assert gap(limb["elbow"], limb["wrist"]) == pytest.approx(claw.FOREARM, abs=0.01), age
        assert gap(limb["wrist"], limb["hinge"]) == pytest.approx(claw.HAND, abs=0.01), age
    limb = pose(ATTACK - 1)
    upper = angle(limb["shoulder"], limb["elbow"])
    fore = angle(limb["elbow"], limb["wrist"])
    hand = angle(limb["wrist"], limb["hinge"])
    assert turn(upper, fore) > 15 and turn(fore, hand) > 8 and turn(upper, hand) > 15  # none in line with another
    screen = pygame.Rect(0, 0, *SIZE)
    for name in ("elbow", "wrist", "hinge", "tip"):
        assert screen.collidepoint(limb[name]), name  # all three segments are on screen at the hit
    assert not screen.collidepoint(limb["shoulder"])  # the limb comes from beyond the corner
    assert limb["shoulder"][0] > SIZE[0] and limb["shoulder"][1] < 0


def test_the_joints_flex_during_the_lunge_and_as_the_jaws_shut():
    def elbow_bend(age):
        limb = pose(age)
        return turn(angle(limb["shoulder"], limb["elbow"]), angle(limb["elbow"], limb["wrist"]))

    def wrist_bend(age):
        limb = pose(age)
        return turn(angle(limb["elbow"], limb["wrist"]), limb["heading"])
    assert elbow_bend(4) > elbow_bend(REACH) + 20   # folded at first, the arm stretches out as it strikes
    assert abs(elbow_bend(REACH) - elbow_bend(ATTACK - 1)) > 3   # and gives a little as the jaws shut
    assert abs(wrist_bend(REACH) - wrist_bend(ATTACK - 1)) > 2   # the wrist gives too
    assert turn(pose(REACH)["heading"], pose(ATTACK - 1)["heading"]) > 12  # as the hand snaps forward on the grip
    headings = [pose(age)["heading"] for age in range(ATTACK)]
    assert headings[0] == pytest.approx(claw.AIM + claw.WRIST_COCKED) and headings[-1] == pytest.approx(claw.AIM + claw.WRIST_STRUCK)


def test_at_the_hit_the_arm_kicks_back_along_its_axis_then_shivers_and_holds():
    rest = pose(ATTACK - 1)["tip"]
    back = (-math.cos(claw.AIM), -math.sin(claw.AIM))  # away from the screen, along the hand
    moves = []
    for age in range(ATTACK, IMPACT):
        tip = pose(age)["tip"]
        along = (tip[0] - rest[0]) * back[0] + (tip[1] - rest[1]) * back[1]
        across = (tip[0] - rest[0]) * back[1] - (tip[1] - rest[1]) * back[0]
        assert abs(across) < 0.01, age  # only along the arm
        moves.append(round(along))
    assert moves[0] in (2, 3) and moves[1] in (2, 3)             # the kick: two or three pixels back
    assert set(moves[3:7]) <= {-1, 0, 1} and len(set(moves[3:7])) >= 2  # then a shiver of a pixel
    assert moves[len(claw.RECOIL):] == [0] * (IMPACT - ATTACK - len(claw.RECOIL))  # and it holds still
    assert pose(ATTACK + 1)["opening"] == 0.0


def test_after_the_screen_breaks_the_claw_pulls_back_out():
    gaps = [gap(pose(age)["tip"], pose(ATTACK - 1)["tip"]) for age in range(IMPACT, IMPACT + RETREAT + 1)]
    assert gaps == sorted(gaps)
    assert pose(IMPACT + RETREAT)["tip"] == pytest.approx(pose(0)["tip"])
    assert not pygame.Rect(0, 0, *SIZE).collidepoint(pose(IMPACT + RETREAT + 5)["tip"])


def test_the_shadow_is_far_while_the_claw_is_high_and_touches_it_at_the_hit():
    heights = [pose(age)["shadow"] for age in range(ATTACK)]
    assert heights[0] == 1.0 and heights == sorted(heights, reverse=True) and len(set(heights)) == ATTACK
    assert heights[-1] == 0.0  # the frame before the snap: nothing between the claw and the screen
    assert all(pose(age)["shadow"] == 0.0 for age in range(ATTACK, IMPACT + RETREAT))


def test_the_two_jaws_meet_at_their_tips_when_shut_and_gape_when_open():
    for heading in (0.0, claw.AIM, 2.0):
        hinge = (100.0, 100.0)
        shut = [claw.jaw_line(hinge, heading, side, 0.0) for side in (1, -1)]
        assert gap(shut[0][-1], shut[1][-1]) < 5  # tip to tip
        reach = claw.jaw_reach()
        meet = (hinge[0] + reach * math.cos(heading), hinge[1] + reach * math.sin(heading))
        assert gap(shut[0][-1], meet) < 3 and gap(shut[1][-1], meet) < 3
        wide = [claw.jaw_line(hinge, heading, side, claw.JAW_OPEN) for side in (1, -1)]
        assert gap(wide[0][-1], wide[1][-1]) > 40
        middle = len(shut[0]) // 2
        assert gap(shut[0][middle], shut[1][middle]) > gap(shut[0][-1], shut[1][-1]) + 10  # curved: a grip, not a beak
        assert len(shut[0]) == claw.JAW_STEPS + 1 == len(claw.JAW_WIDTHS)


def test_the_elbow_is_where_the_two_bones_meet_on_the_outside_of_the_arm():
    shoulder = (272.0, -42.0)
    for wrist in ((190.0, 62.0), (230.0, 20.0), (265.0, -30.0)):
        elbow = claw.elbow_between(shoulder, wrist)
        assert gap(shoulder, elbow) == pytest.approx(claw.UPPER_ARM, abs=0.01)
        if gap(shoulder, wrist) > abs(claw.UPPER_ARM - claw.FOREARM):
            assert gap(elbow, wrist) == pytest.approx(claw.FOREARM, abs=0.01)
        straight = (wrist[0] - shoulder[0], wrist[1] - shoulder[1])
        side = straight[0] * (elbow[1] - shoulder[1]) - straight[1] * (elbow[0] - shoulder[0])
        assert side < 0  # always the same side: the elbow never flips over
    assert claw.elbow_between(shoulder, (1000.0, 1000.0))  # out of reach: no error, the arm is straight


# --- The painting -----------------------------------------------------------------------------


def test_the_limb_is_painted_in_its_four_tones_with_hard_pixels():
    for age in (6, REACH, ATTACK - 1, ATTACK + 1):
        picture = painted(age)
        assert picture.get_size() == SIZE  # the small screen: nothing enlarged
        seen = {}
        for x, y, (r, g, b, a) in pixels(picture):
            assert a in (0, 255), (age, x, y)  # no soft edges
            if a:
                assert (r, g, b) in TONES, (age, x, y, (r, g, b))  # no colour in between: nothing blurred
                seen[(r, g, b)] = seen.get((r, g, b), 0) + 1
        for tone in (claw.OUTLINE, claw.SHADOW, claw.BASE, claw.LIGHT):
            assert seen.get(tone, 0) > 150, (age, tone)
        assert seen[claw.BASE] > seen[claw.LIGHT] and seen[claw.BASE] > seen[claw.OUTLINE]  # red, mostly
        assert seen.get(claw.PLATE, 0) > 100  # the dark plates of the joints


def test_the_light_comes_from_the_top_left():
    picture = painted(ATTACK - 1)
    lit = [(x, y) for x, y, color in pixels(picture) if color[:3] == claw.LIGHT and color[3]]
    dark = [(x, y) for x, y, color in pixels(picture) if color[:3] == claw.SHADOW and color[3]]
    def middle(points):
        return sum(x + y for x, y in points) / len(points)
    assert middle(lit) < middle(dark) - 6  # the pale edge is up and to the left of the shadow


def test_the_shell_is_not_flat_dither_and_grains():
    picture = painted(ATTACK - 1)
    area = picture.get_rect()

    def color(x, y):
        return tuple(picture.get_at((x, y)))[:3] if area.collidepoint(x, y) and picture.get_at((x, y))[3] else None
    lone = 0
    for x, y, (r, g, b, a) in pixels(picture):
        if a and (r, g, b) in (claw.SHADOW, claw.OUTLINE):
            around = [color(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            lone += all(other == claw.BASE for other in around)  # a dark pixel alone in the red
    assert lone >= 25


def test_spikes_stand_on_the_outer_edge_of_the_forearm_and_teeth_inside_the_grip(monkeypatch):
    thorns = []
    real = claw.thorn

    def spy(surface, base, direction, wide, tall, color):
        thorns.append((base, direction, tall, color))
        real(surface, base, direction, wide, tall, color)
    monkeypatch.setattr(claw, "thorn", spy)
    limb = pose(REACH)
    pygame.display.set_mode((1, 1))
    picture = claw.layer(SIZE, limb)
    spikes = [one for one in thorns if one[3] != claw.TOOTH]
    teeth = [one for one in thorns if one[3] == claw.TOOTH]
    assert len(spikes) == claw.SPIKES >= 4 and len(teeth) == 2 * claw.TEETH
    assert len({one[2] for one in spikes}) >= 2  # a saw: not all the same height
    elbow, wrist = limb["elbow"], limb["wrist"]
    bend = (elbow[0] - (limb["shoulder"][0] + wrist[0]) / 2, elbow[1] - (limb["shoulder"][1] + wrist[1]) / 2)
    for base, direction, tall, color in spikes:
        assert direction[0] * bend[0] + direction[1] * bend[1] > 0  # on the outside of the elbow's bend
        assert min(gap(base, elbow), gap(base, wrist)) < claw.FOREARM  # along the forearm
    axis = (math.cos(limb["heading"]), math.sin(limb["heading"]))
    for base, direction, tall, color in teeth:
        off = (base[0] - limb["hinge"][0]) * -axis[1] + (base[1] - limb["hinge"][1]) * axis[0]
        towards = direction[0] * -axis[1] + direction[1] * axis[0]
        assert off * towards < 0  # each tooth points across the grip, at the other jaw
    assert any(tuple(picture.get_at((x, y)))[:3] == claw.TOOTH for x in range(SIZE[0]) for y in range(SIZE[1]))


def test_the_joints_are_dark_plates_one_over_the_other():
    picture = painted(ATTACK - 1)
    limb = pose(ATTACK - 1)
    for name, radius in (("elbow", claw.ELBOW), ("wrist", claw.WRIST), ("hinge", claw.HINGE)):
        x, y = round(limb[name][0]), round(limb[name][1])
        near = {tuple(picture.get_at((x + dx, y + dy)))[:3] for dx in range(-radius, radius + 1)
                for dy in range(-radius, radius + 1) if 0 <= x + dx < SIZE[0] and 0 <= y + dy < SIZE[1]}
        assert {claw.PLATE, claw.OUTLINE, claw.SHADOW} <= near, name  # the plate, its outline, the plate over it


def test_the_shadow_has_the_shape_of_the_limb_in_see_through_black():
    picture = painted(8)
    shadow = claw.shadow_of(picture)
    assert shadow.get_size() == SIZE
    for x in range(0, SIZE[0], 3):
        for y in range(0, SIZE[1], 3):
            r, g, b, a = shadow.get_at((x, y))
            assert (a > 0) == (picture.get_at((x, y))[3] > 0), (x, y)
            if a:
                assert (r, g, b) == (0, 0, 0) and 60 < a < 200  # dark, but the game shows through


def test_the_limb_can_be_painted_pushed_aside_and_off_the_screen():
    pygame.display.set_mode((1, 1))
    still = claw.layer(SIZE, pose(ATTACK - 1))
    pushed = claw.layer(SIZE, pose(ATTACK - 1), offset=(4, -3))
    x, y = round(pose(ATTACK - 1)["wrist"][0]), round(pose(ATTACK - 1)["wrist"][1])
    assert pushed.get_at((x + 4, y - 3)) == still.get_at((x, y))
    for age in range(0, IMPACT + RETREAT + 3):
        claw.layer(SIZE, pose(age))  # every frame of the sequence, even with the limb outside
