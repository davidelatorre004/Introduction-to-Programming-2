"""The crab that hunts the players, drawn pixel by pixel in any pose.

Seen from above and a little from the front, like everything in the game: a round
shell with a crown of spikes, two eyes on stalks, two claws on segmented arms in
front, and three legs on each side. Nothing here is a picture: picture() paints the
crab for a pose, at the size of the small screen, and keeps what it painted.

A pose says:
- "legs": which of the 4 frames of the walk (0 to 3). The legs move in two groups,
  like a crab's: on frames 0 and 2 one group is lifted and reaching while the other
  pushes, on frames 1 and 3 all of them touch the floor;
- "claws": how far the claws are open, from 0 (shut) to 1 (gaping wide);
- "breath": 1 when the shell is risen by a pixel (breathing in), else 0;
- "eyes": "calm", "hunt" (red, burning) or "dazed" (half shut);
- "look": the way it looks, (-1, 0, 1) on each axis: where its pupils are.

The shell has five tones: a very dark red, almost violet, outline; a deep shadow
underneath; the crimson of the shell; coral where the light falls, on the top; and
a pale glint. The light comes from the top left, as on everything else.
"""

import math

import pygame

OUTLINE = (52, 10, 34)     # very dark red, almost violet
SHADOW = (120, 22, 44)     # the side away from the light, underneath
BASE = (192, 38, 52)       # crimson
LIGHT = (242, 112, 92)     # coral, where the light falls
GLINT = (255, 210, 182)    # a pale glint
EYE = (248, 242, 226)      # the white of the eyes
PUPIL = (26, 10, 22)
HUNT_EYE = (255, 92, 40)   # burning eyes, when it hunts...
HUNT_PUPIL = (255, 236, 120)  # ...with a hot core
DAZED_EYE = (150, 120, 130)

SIZE = (40, 30)            # the picture
CENTER = (20, 17)          # the middle of the shell on it
FEET = 28                  # the row where the legs touch the floor: the bottom of the crab on the floor
SHELL = (8.5, 5.5)         # half its width and half its height
SPINES = (2.55, 2.8, 3.05)  # where the spines stand along the front of each side of the shell (radians, right side)
HORNS = (-1, 1)            # two small horns between the eyes
STALKS = (-3, 3)           # where the eye stalks rise, from the middle
STALK = 4                  # how tall they are
LEG_ROOTS = (0, 2, 4)      # where the legs leave the side of the shell, below its middle
LEG_KNEES = (12, 13, 12)   # how far out from the middle each knee is
LEG_TIPS = (16, 17, 15)    # and each tip
CLAW_ROOT = (6, 2)         # where an arm leaves the shell, from the middle (x on each side, y down)
CLAW_ELBOW = (11, 2)       # its elbow
CLAW_AT = (14, -4)         # the middle of the palm of its claw
PALM = 8                   # how round the palm is (its radius squared)
FINGER = 6                 # how long the fingers are
FINGER_SHUT = -0.26        # radians each finger leans in when the claw is shut: their tips meet...
FINGER_OPEN = 0.55         # ...and out when it gapes

_pictures = {}


def pose(legs=1, claws=0.0, breath=0, eyes="calm", look=(0, 1)):
    """A pose of the crab (see the top of this file), its values kept in their ranges."""
    return {"legs": legs % 4, "claws": round(min(max(claws, 0.0), 1.0) * 4) / 4, "breath": 1 if breath else 0,
            "eyes": eyes, "look": (max(-1, min(1, look[0])), max(-1, min(1, look[1])))}


def picture(crab_pose):
    """The crab in this pose, on a clear picture of SIZE, painted once and kept."""
    key = tuple(sorted(crab_pose.items()))
    if key not in _pictures:
        _pictures[key] = paint(crab_pose)
    return _pictures[key]


def paint(crab_pose):
    """Paint the crab: the legs behind, the shell and its spikes, the arms and claws, the eyes;
    then a dark outline around all of it."""
    pixels = {}
    rise = crab_pose["breath"]
    cx, cy = CENTER[0], CENTER[1] - rise
    draw_legs(pixels, crab_pose["legs"], cx, CENTER[1])  # the legs stay on the floor as the shell breathes
    draw_shell(pixels, cx, cy)
    for side in (-1, 1):
        draw_claw(pixels, side, crab_pose["claws"], cx, cy)
    draw_eyes(pixels, crab_pose["eyes"], crab_pose["look"], cx, cy)
    outline(pixels)
    surface = pygame.Surface(SIZE, pygame.SRCALPHA)
    for (x, y), color in pixels.items():
        if 0 <= x < SIZE[0] and 0 <= y < SIZE[1]:
            surface.set_at((x, y), color)
    return surface


def put(pixels, x, y, color, over=True):
    """One pixel; `over` False leaves what is already there."""
    point = (round(x), round(y))
    if over or point not in pixels:
        pixels[point] = color


def line(pixels, start, end, color, over=True):
    """A line one pixel thick, with no gaps."""
    (x0, y0), (x1, y1) = start, end
    steps = max(abs(round(x1) - round(x0)), abs(round(y1) - round(y0)), 1)
    for step in range(steps + 1):
        share = step / steps
        put(pixels, x0 + (x1 - x0) * share, y0 + (y1 - y0) * share, color, over)


def shade(nx, ny, extra=0.0):
    """The tone of a round piece of shell where its surface faces (nx, ny), the light from the top left."""
    light = -0.45 * nx - 0.85 * ny + extra
    if light > 0.55:
        return LIGHT
    if light > -0.25:
        return BASE
    return SHADOW


def draw_shell(pixels, cx, cy):
    """The round shell: coral on top, crimson, a dithered edge into the shadow underneath, a glint,
    a seam across its back; a row of spines along the front of each side, and two horns in front."""
    rx, ry = SHELL
    for y in range(math.floor(cy - ry), math.ceil(cy + ry) + 1):
        for x in range(math.floor(cx - rx), math.ceil(cx + rx) + 1):
            u, v = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            if u * u + v * v > 1:
                continue
            tone = shade(u, v, 0.35 * (1 - u * u - v * v))
            if tone == BASE and -0.45 * u - 0.85 * v < -0.1 and (x + y) % 2 == 0:
                tone = SHADOW  # half way into the shadow: a dither
            if v > 0.62:
                tone = SHADOW  # the rim underneath
            put(pixels, x, y, tone)
    for x in range(round(cx - rx * 0.55), round(cx + rx * 0.55) + 1):  # the seam between the front and the back
        put(pixels, x, round(cy + 0.5 + 0.12 * abs(x - cx)), SHADOW)
    put(pixels, cx - 4, cy - 3, GLINT)
    put(pixels, cx - 3, cy - 3, GLINT)
    put(pixels, cx - 4, cy - 2, LIGHT)
    for side in (-1, 1):
        for index, angle in enumerate(SPINES):  # the spines: short, sharp, pointing out from the rim
            nx, ny = math.cos(angle), -math.sin(angle)
            nx = -nx * side  # the right side mirrored from the left
            rim = (cx + nx * rx, cy + ny * ry)
            put(pixels, rim[0] + nx * 0.8, rim[1] + ny * 0.8, BASE)
            put(pixels, rim[0] + nx * 1.9, rim[1] + ny * 1.9, BASE)
            put(pixels, rim[0] + nx * 2.9, rim[1] + ny * 2.9, LIGHT)  # a pale, sharp tip
    for offset in HORNS:
        put(pixels, cx + offset, round(cy - ry) - 1, BASE)


def draw_legs(pixels, frame, cx, cy):
    """Three legs on each side, each in two segments: out and up to the knee, then down to the floor.
    On frames 0 and 2 one group (front and back on the left, the middle on the right; or the
    other) is lifted and reaching while the other pushes; on 1 and 3 all of them stand."""
    for side in (-1, 1):
        for index in range(3):
            group = (index + (0 if side < 0 else 1)) % 2
            lifted = (frame == 0 and group == 0) or (frame == 2 and group == 1)
            pushing = (frame == 0 and group == 1) or (frame == 2 and group == 0)
            root = (cx + side * 6, cy + LEG_ROOTS[index])
            knee = (cx + side * LEG_KNEES[index], cy + LEG_ROOTS[index] - 2 - (1 if lifted else 0))
            tip = (cx + side * (LEG_TIPS[index] + (1 if lifted else 0) - (1 if pushing else 0)),
                   FEET - 1 - (1 if lifted else 0) - (2 - index) // 2)
            color = SHADOW if index == 2 else BASE
            line(pixels, root, knee, color)
            line(pixels, (root[0], root[1] + 1), (knee[0], knee[1] + 1), SHADOW)  # thick near the body
            line(pixels, knee, tip, SHADOW)
            put(pixels, knee[0], knee[1], LIGHT if index == 0 else BASE)  # the joint catches the light


def draw_claw(pixels, side, opening, cx, cy):
    """One arm and its claw: the arm in two thick segments with dark bands where they join, from the
    front of the shell out and up to a round palm; two fingers, shut tip to tip or apart as far
    as `opening` says, the upper one lit."""
    root = (cx + side * CLAW_ROOT[0], cy + CLAW_ROOT[1])
    elbow = (cx + side * CLAW_ELBOW[0], cy + CLAW_ELBOW[1])
    palm = (cx + side * CLAW_AT[0], cy + CLAW_AT[1])
    for (a, b) in ((root, elbow), (elbow, palm)):
        line(pixels, a, b, BASE)
        line(pixels, (a[0], a[1] + 1), (b[0] + side, b[1] + 1), SHADOW)
    for band in (root, elbow, ((elbow[0] + palm[0]) / 2, (elbow[1] + palm[1]) / 2)):
        put(pixels, band[0], band[1], SHADOW)  # the bands of the segments
        put(pixels, band[0], band[1] + 1, OUTLINE)
    for dy in range(-3, 4):  # the palm: round, lit on its top
        for dx in range(-3, 4):
            if dx * dx + dy * dy <= PALM:
                put(pixels, palm[0] + dx, palm[1] + dy, shade(dx / 2.8, dy / 2.8, 0.3))
    put(pixels, palm[0] - 1, palm[1] - 2, GLINT)
    put(pixels, palm[0] + side * 2, palm[1] + 1, SHADOW)
    heading = math.atan2(-1.0, side * 0.25)  # the fingers point up, a little outward
    spread = FINGER_SHUT + (FINGER_OPEN - FINGER_SHUT) * opening
    across = (math.cos(heading + math.pi / 2), math.sin(heading + math.pi / 2))
    for finger in (1, -1):  # 1: the outer finger, -1: the inner one
        angle = heading + finger * side * spread  # on screen a growing angle turns clockwise: outward
        base = (palm[0] + across[0] * finger * side * 1.6, palm[1] - 2 + across[1] * finger * side * 1.6)
        tip = (base[0] + FINGER * math.cos(angle), base[1] + FINGER * math.sin(angle))
        middle = ((base[0] + tip[0]) / 2, (base[1] + tip[1]) / 2)
        line(pixels, base, tip, LIGHT if finger == 1 else BASE)
        line(pixels, (base[0] + side * 0.6, base[1] + 0.6), (middle[0] + side * 0.6, middle[1] + 0.6),
             BASE if finger == 1 else SHADOW)  # thick at the base, thin at the tip
        put(pixels, tip[0], tip[1], SHADOW)


def draw_eyes(pixels, mood, look, cx, cy):
    """Two eyes on stalks above the shell, each with its pupil where the crab looks and a glint;
    burning red when it hunts, half shut when it is dazed."""
    eye, pupil = {"calm": (EYE, PUPIL), "hunt": (HUNT_EYE, HUNT_PUPIL), "dazed": (DAZED_EYE, PUPIL)}[mood]
    for offset in STALKS:
        x = cx + offset
        top = round(cy - SHELL[1]) - STALK
        line(pixels, (x, top + 2), (x, round(cy - SHELL[1]) + 1), SHADOW)
        for dx in (0, 1):
            for dy in (0, 1):
                put(pixels, x - 1 + dx, top + dy, eye)
        if mood == "dazed":
            put(pixels, x - 1, top, OUTLINE)  # the lid, half down
            put(pixels, x, top, OUTLINE)
            continue
        put(pixels, x - 1 + (1 if look[0] > 0 else 0), top + (1 if look[1] > 0 else 0), pupil)
        if mood == "calm":
            put(pixels, x - 1 + (0 if look[0] > 0 else 1), top, GLINT)  # a glint in the eye


def outline(pixels):
    """A dark outline: every empty pixel next to the crab, left, right, above or below."""
    edge = set()
    for (x, y) in pixels:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y + dy) not in pixels:
                edge.add((x + dx, y + dy))
    for point in edge:
        pixels[point] = OUTLINE


def eye_points(crab_pose):
    """Where the eyes are on the picture: for a glow or a trail drawn on top."""
    cx, cy = CENTER[0], CENTER[1] - crab_pose["breath"]
    top = round(cy - SHELL[1]) - STALK
    return [(cx + offset, top + 1) for offset in STALKS]
