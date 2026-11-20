"""Tests for the crab that hunts the players: drawn pixel by pixel, in every pose."""

import pygame
import pytest

import crab

SHELL_TONES = {crab.OUTLINE, crab.SHADOW, crab.BASE, crab.LIGHT, crab.GLINT}
EYES = {crab.EYE, crab.PUPIL, crab.HUNT_EYE, crab.HUNT_PUPIL, crab.DAZED_EYE}


def pixels(picture):
    return {(x, y): tuple(picture.get_at((x, y)))[:3] for x in range(picture.get_width())
            for y in range(picture.get_height()) if picture.get_at((x, y)).a}


def test_the_crab_is_painted_in_five_tones_of_shell_and_its_eyes():
    picture = crab.picture(crab.pose())
    assert picture.get_size() == crab.SIZE
    used = set(pixels(picture).values())
    assert SHELL_TONES <= used  # outline, shadow, crimson, coral, glint
    assert used <= SHELL_TONES | EYES
    assert len(pixels(picture)) > 300  # a big crab, not a speck


def test_the_light_falls_on_the_top_and_the_shadow_underneath():
    painted = pixels(crab.picture(crab.pose()))
    cx, cy = crab.CENTER
    top = [painted[(x, y)] for (x, y) in painted if abs(x - cx) < 5 and cy - 4 <= y <= cy - 2]
    bottom = [painted[(x, y)] for (x, y) in painted if abs(x - cx) < 5 and cy + 3 <= y <= cy + 5]
    assert top.count(crab.LIGHT) > top.count(crab.SHADOW)
    assert bottom.count(crab.SHADOW) > bottom.count(crab.LIGHT)


def test_a_dark_outline_goes_all_around_it():
    painted = pixels(crab.picture(crab.pose()))
    for (x, y), color in painted.items():
        if any((x + dx, y + dy) not in painted for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            assert color == crab.OUTLINE, (x, y)


def test_spines_stand_out_of_the_shell_and_eyes_on_stalks_above_it():
    painted = pixels(crab.picture(crab.pose()))
    cx, cy = crab.CENTER
    rx, ry = crab.SHELL
    outside = [(x, y) for (x, y), color in painted.items() if color == crab.LIGHT
               and ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 > 1.3 and y < cy and abs(x - cx) < 13]
    assert len(outside) >= 4  # the pale tips of the spines, on both sides
    eyes = [(x, y) for (x, y), color in painted.items() if color == crab.EYE]
    assert eyes and all(y < cy - ry for _, y in eyes)  # up on their stalks


def test_the_legs_walk_in_two_groups_over_four_frames():
    frames = [pygame.image.tobytes(crab.picture(crab.pose(legs=frame)), "RGBA") for frame in range(4)]
    assert frames[1] == frames[3]  # all on the floor
    assert frames[0] != frames[1] and frames[2] != frames[1] and frames[0] != frames[2]  # one group, then the other
    assert crab.pose(legs=5)["legs"] == 1


def test_the_claws_shut_tip_to_tip_and_gape():
    def gap(opening):
        """The clear pixels between the two fingers of the right claw, a little below their tips."""
        painted = pixels(crab.picture(crab.pose(claws=opening)))
        palm_x = crab.CENTER[0] + crab.CLAW_AT[0]
        claw = [(x, y) for (x, y) in painted if abs(x - palm_x) <= 6]
        top = min(y for _, y in claw)
        widest = 0
        for row in range(top, top + 6):
            xs = sorted(x for x, y in claw if y == row)
            widest = max(widest, (xs[-1] - xs[0] + 1) - len(xs))
        return widest
    shut, half, wide = gap(0.0), gap(0.5), gap(1.0)
    assert shut == 0 < half < wide  # one point, tip to tip; then apart, wider and wider
    assert crab.pose(claws=0.6)["claws"] == 0.625 and crab.pose(claws=7)["claws"] == 1.0  # a few steps, kept in range
    assert pygame.image.tobytes(crab.picture(crab.pose(claws=0.5)), "RGBA") not in (
        pygame.image.tobytes(crab.picture(crab.pose(claws=0.0)), "RGBA"),
        pygame.image.tobytes(crab.picture(crab.pose(claws=1.0)), "RGBA"))
    assert half


def test_breathing_lifts_the_shell_but_not_the_feet():
    still = pixels(crab.picture(crab.pose(breath=0)))
    breathing = pixels(crab.picture(crab.pose(breath=1)))
    assert min(y for (x, y) in breathing) == min(y for (x, y) in still) - 1  # the shell and the eyes rise
    assert max(y for (x, y) in breathing) == max(y for (x, y) in still)      # the legs stay on the floor
    assert max(y for (x, y) in still) <= crab.FEET


def test_its_eyes_burn_when_it_hunts_and_droop_when_it_is_dazed():
    calm = set(pixels(crab.picture(crab.pose(eyes="calm"))).values())
    hunt = set(pixels(crab.picture(crab.pose(eyes="hunt"))).values())
    dazed = set(pixels(crab.picture(crab.pose(eyes="dazed"))).values())
    assert crab.EYE in calm and crab.HUNT_EYE not in calm
    assert crab.HUNT_EYE in hunt and crab.HUNT_PUPIL in hunt and crab.EYE not in hunt
    assert crab.DAZED_EYE in dazed and crab.PUPIL not in dazed
    for x, y in crab.eye_points(crab.pose(eyes="hunt")):
        assert pixels(crab.picture(crab.pose(eyes="hunt"))).get((x, y)) in (crab.HUNT_EYE, crab.HUNT_PUPIL)


def test_its_pupils_look_where_it_looks():
    def pupils(look):
        return sorted(point for point, color in pixels(crab.picture(crab.pose(look=look))).items() if color == crab.PUPIL)
    left, right = pupils((-1, 0)), pupils((1, 0))
    assert len(left) == len(right) == 2 and all(a[0] < b[0] for a, b in zip(left, right))


def test_each_pose_is_painted_once():
    first = crab.picture(crab.pose(legs=2, claws=0.75, eyes="hunt"))
    assert crab.picture(crab.pose(legs=2, claws=0.75, eyes="hunt")) is first
    assert crab.picture(crab.pose(legs=2, claws=0.75, eyes="calm")) is not first
