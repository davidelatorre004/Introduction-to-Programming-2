"""The giant claw that breaks the screen when the crab has caught both players.

A crab's limb in three segments (the upper arm from the corner of the screen,
the thick forearm, the massive hand) and the two jaws of the claw, joined by
dark plated joints. Nothing here is a picture: pose() works out where every
joint is at a moment of the attack, and draw() paints the limb from that, with
plain polygons on the pixel grid of the small screen. So it bends at its
joints without ever being turned or enlarged, and every pixel stays sharp.

The shell has four tones, for a round, armoured look: a dark outline, a deep
shadow on the side away from the light, the red of the crab, and a pale
highlight along the edge that faces the light, which comes from the top left.

This module knows nothing about the game: main.py tells it the time and the
size of the screen, and draws what it returns.
"""

import math

import pygame

# --- The shell: four tones, and what the details are made of ------------------------------

OUTLINE = (44, 10, 18)     # almost black, with a little red in it
SHADOW = (132, 30, 36)     # the side away from the light
BASE = (214, 64, 52)       # the red of the crab
LIGHT = (252, 156, 124)    # the edge that catches the light: salmon
PLATE = (88, 20, 28)       # the dark plates of the joints
TOOTH = (250, 228, 204)    # the small teeth inside the grip
LIGHT_FROM = (-0.7071, -0.7071)  # the way to the light: up and to the left
RED = {"outline": OUTLINE, "shadow": SHADOW, "base": BASE, "light": LIGHT, "plate": PLATE, "tooth": TOOTH}
# A common shore crab, for the easy crab on the choice of the difficulty: sandy orange, softer.
CORAL = {"outline": (62, 30, 22), "shadow": (172, 84, 50), "base": (230, 136, 80), "light": (255, 212, 160),
         "plate": (122, 60, 38), "tooth": (250, 238, 214)}

# --- The limb: lengths and widths, in pixels ------------------------------------------------

UPPER_ARM = 88       # from the shoulder, beyond the corner of the screen, to the elbow
FOREARM = 56         # from the elbow to the wrist: the thickest part
HAND = 28            # the base of the claw, from the wrist to the hinge of the jaws
JAW = 56             # each jaw, along its curve
JAW_STEPS = 8        # the pieces a jaw's curve is made of
JAW_SPREAD = 0.55    # radians a jaw leans outwards where it leaves the hand...
JAW_CURL = 1.25      # ...and how much it curls back in by its tip
JAW_GAP = 6          # how far from the middle of the hand each jaw starts

UPPER_WIDTHS = (10, 11, 12)        # half the width of each segment along its length
FOREARM_WIDTHS = (12, 16, 14)
HAND_WIDTHS = (15, 19, 18)
JAW_WIDTHS = (11, 11, 10, 9, 8, 6, 4, 2, 1)
ELBOW, WRIST, HINGE = 11, 13, 9    # how big the plates of each joint are
SHOULDER = (16, -42)               # where the shoulder is: right of the screen's right edge, above its top
FOLDED = (-30, -36)                # where the wrist is, from the shoulder, while the arm waits folded out of sight

SPIKES = 5           # the saw of chitin along the outer edge of the forearm
TEETH = 5            # the small teeth along the inside of each jaw

# --- The attack: how the limb moves ---------------------------------------------------------

AIM = math.atan2(0.62, -0.78)   # where the hand points when it strikes: down and to the left
WRIST_COCKED = 0.42             # radians the hand is bent back while the arm comes in...
WRIST_STRUCK = -0.06            # ...and how far it snaps forward as the jaws shut
JAW_OPEN = 0.62                 # radians each jaw is open while the claw comes in
RECOIL = (-3, -3, -2, 1, -1, 1, 0, -1, 0)  # pixels along the arm, frame by frame from the hit: a kick, then a shiver


def jaw_line(hinge, heading, side, opening, length=JAW, gap=JAW_GAP, spread=JAW_SPREAD, curl=JAW_CURL):
    """The middle line of one jaw: points from the hand to the tip.

    `side` is 1 for the jaw on the left of the way the hand points, -1 for the
    other. It leaves the hand leaning outwards and curls back in, so that the
    two tips meet when `opening` is 0. The giant claw has the jaws of the
    constants above; a smaller one gives its own `length`, `gap`, `spread` and `curl`.
    """
    nx, ny = -math.sin(heading), math.cos(heading)  # the left of the way the hand points
    x = hinge[0] - side * gap * nx
    y = hinge[1] - side * gap * ny
    points = [(x, y)]
    step = length / JAW_STEPS
    for index in range(JAW_STEPS):
        along = (index + 0.5) / JAW_STEPS
        turn = heading - side * (opening + spread - curl * along)
        x += step * math.cos(turn)
        y += step * math.sin(turn)
        points.append((x, y))
    return points


def jaw_reach():
    """How far in front of the hinge the tips of the shut jaws meet."""
    tip = jaw_line((0.0, 0.0), 0.0, 1, 0.0)[-1]
    return tip[0]


def elbow_between(shoulder, wrist):
    """Where the elbow is, for an arm of two bones from the shoulder to the wrist.

    The two bones have fixed lengths, so the elbow is where two circles cross:
    of the two places, the one on the outside of the screen (down and to the
    right of the arm). The closer the wrist is to the shoulder, the more the arm
    is bent; it straightens as the claw strikes.
    """
    dx, dy = wrist[0] - shoulder[0], wrist[1] - shoulder[1]
    real = math.hypot(dx, dy) or 1.0
    dx, dy = dx / real, dy / real
    apart = min(max(real, abs(UPPER_ARM - FOREARM) + 0.01), UPPER_ARM + FOREARM - 0.01)
    along = (UPPER_ARM ** 2 - FOREARM ** 2 + apart ** 2) / (2 * apart)
    off = math.sqrt(max(UPPER_ARM ** 2 - along ** 2, 0.0))
    return (shoulder[0] + dx * along + dy * off, shoulder[1] + dy * along - dx * off)


def ease(way):
    """From 0 to 1, fast in the middle and soft at both ends."""
    way = min(max(way, 0.0), 1.0)
    return way * way * (3 - 2 * way)


def pose(age, size, reach_frames, attack_frames, impact_frame, retreat_frames):
    """Where the whole limb is, `age` frames into the sequence, on a screen of this size.

    The claw comes in from the top right corner with its jaws open and its wrist
    cocked back (`reach_frames`), shuts on the middle of the screen as the wrist
    snaps forward (until `attack_frames`), kicks back and shivers at the hit,
    holds, and from `impact_frame` pulls back out in `retreat_frames`.

    Returns a dict: the joints "shoulder", "elbow", "wrist", "hinge" and the point
    "tip" the jaws close on, the "heading" of the hand, how far the jaws are open
    ("opening", in radians), and "shadow": how far the limb is above the screen
    (1 far away, 0 touching it).
    """
    width, height = size
    shoulder = (width + float(SHOULDER[0]), float(SHOULDER[1]))
    target = (width / 2.0, height / 2.0)
    grip = HAND + jaw_reach()  # from the wrist to where the tips meet
    # Before the attack the arm is folded beyond the corner, the whole claw out of sight: the wrist
    # up and to the right of the shoulder, far enough for the two bones to reach it.
    cocked = AIM + WRIST_COCKED  # the way the hand points then
    folded = (shoulder[0] + FOLDED[0] + grip * math.cos(cocked), shoulder[1] + FOLDED[1] + grip * math.sin(cocked))
    if age < impact_frame:
        way = ease(age / reach_frames)
        shutting = min(max((age - reach_frames) / max(attack_frames - 1 - reach_frames, 1), 0.0), 1.0)
        opening = JAW_OPEN * (1.0 - shutting)
        bend = WRIST_COCKED + (WRIST_STRUCK - WRIST_COCKED) * ease(0.35 * way + 0.65 * shutting)
        shadow = 1.0 - min(age / max(attack_frames - 1, 1), 1.0)
    else:
        way = 1.0 - ease((age - impact_frame) / retreat_frames)
        opening = 0.0
        bend = WRIST_STRUCK
        shadow = 0.0
    heading = AIM + bend
    since_hit = age - attack_frames
    kick = RECOIL[since_hit] if 0 <= since_hit < len(RECOIL) and age < impact_frame else 0
    tip = (folded[0] + (target[0] - folded[0]) * way + kick * math.cos(AIM),
           folded[1] + (target[1] - folded[1]) * way + kick * math.sin(AIM))
    hinge = (tip[0] - jaw_reach() * math.cos(heading), tip[1] - jaw_reach() * math.sin(heading))
    wrist = (hinge[0] - HAND * math.cos(heading), hinge[1] - HAND * math.sin(heading))
    return {"shoulder": shoulder, "elbow": elbow_between(shoulder, wrist), "wrist": wrist, "hinge": hinge,
            "tip": tip, "heading": heading, "opening": opening, "shadow": shadow}


# --- Drawing: ribbons of shell, joints, spikes and teeth -----------------------------------


def normals(points):
    """For each point of a line, the direction to its left: where the width of a ribbon goes."""
    result = []
    last = len(points) - 1
    for index in range(len(points)):
        ax, ay = points[max(index - 1, 0)]
        bx, by = points[min(index + 1, last)]
        length = math.hypot(bx - ax, by - ay) or 1.0
        result.append((-(by - ay) / length, (bx - ax) / length))
    return result


def lit_side(sides):
    """1 if the left of a ribbon faces the light, -1 if its right does."""
    facing = sum(nx * LIGHT_FROM[0] + ny * LIGHT_FROM[1] for nx, ny in sides)
    return 1 if facing > 0 else -1


def edge(points, widths, sides, share, extra=0.0):
    """The line that runs along a ribbon at `share` of its half width: 1 is its left edge, -1 its right."""
    return [(x + nx * (width + extra) * share, y + ny * (width + extra) * share)
            for (x, y), width, (nx, ny) in zip(points, widths, sides)]


def strip(surface, color, points, widths, sides, start, end, extra=0.0):
    """Fill a ribbon between two shares of its width."""
    outline = edge(points, widths, sides, start, extra) + edge(points, widths, sides, end, extra)[::-1]
    pygame.draw.polygon(surface, color, [(round(x), round(y)) for x, y in outline])


def along(points, widths, sides, step):
    """Walk along a ribbon every `step` pixels: yields ((x, y), (left x, left y), half width) there."""
    left = 0.0
    for index in range(len(points) - 1):
        (ax, ay), (bx, by) = points[index], points[index + 1]
        length = math.hypot(bx - ax, by - ay)
        while left < length:
            share = left / length
            nx = sides[index][0] + (sides[index + 1][0] - sides[index][0]) * share
            ny = sides[index][1] + (sides[index + 1][1] - sides[index][1]) * share
            width = widths[index] + (widths[index + 1] - widths[index]) * share
            yield (ax + (bx - ax) * share, ay + (by - ay) * share), (nx, ny), width
            left += step
        left -= length


def spread(widths, count):
    """The widths of a segment given for a few places, stretched over `count` points along it."""
    result = []
    for index in range(count):
        place = index * (len(widths) - 1) / max(count - 1, 1)
        low = min(int(place), len(widths) - 2)
        result.append(widths[low] + (widths[low + 1] - widths[low]) * (place - low))
    return result


GRAINS = (0.08, 0.34, -0.5, 0.2, -0.72, 0.0, 0.28, -0.42)  # where across the shell each grain is: 1 is the lit edge


def dot(surface, x, y, color):
    """One pixel, if it is on the picture."""
    x, y = round(x), round(y)
    if 0 <= x < surface.get_width() and 0 <= y < surface.get_height():
        surface.set_at((x, y), color)


def ribbon(surface, points, widths, tones=RED):
    """A piece of shell along a line of points, round like a tube: outline, red, shadow on the side
    away from the light, a pale edge on the side towards it, a dither where shadow and red meet,
    and a few grains so that the shell is not flat. `tones` are the four tones of the shell."""
    sides = normals(points)
    lit = lit_side(sides)
    strip(surface, tones["outline"], points, widths, sides, -1, 1, extra=1.5)
    strip(surface, tones["base"], points, widths, sides, -1, 1)
    strip(surface, tones["shadow"], points, widths, sides, -lit, -lit * 0.25)
    strip(surface, tones["light"], points, widths, sides, lit * 0.5, lit * 0.8)
    for index, ((x, y), (nx, ny), width) in enumerate(along(points, widths, sides, 2)):
        if index % 2 == 0:  # every other pixel just past the shadow: shadow and red mix
            dot(surface, x - lit * nx * width * 0.13, y - lit * ny * width * 0.13, tones["shadow"])
    for index, ((x, y), (nx, ny), width) in enumerate(along(points, widths, sides, 5)):
        if width < 5:
            continue  # too thin for grains: the tip of a jaw
        share = GRAINS[index % len(GRAINS)]
        dot(surface, x + lit * nx * width * share, y + lit * ny * width * share,
            tones["shadow"] if share > -0.25 else tones["outline"])


def joint(surface, center, radius, heading, tones=RED):
    """A joint of the limb: two dark plates, one over the other, with a hard outline and a glint."""
    x, y = round(center[0]), round(center[1])
    pygame.draw.circle(surface, tones["outline"], (x, y), radius + 1)
    pygame.draw.circle(surface, tones["plate"], (x, y), radius)
    over = (round(x + 3 * math.cos(heading)), round(y + 3 * math.sin(heading)))  # the plate of the next segment
    pygame.draw.circle(surface, tones["outline"], over, radius - 2)
    pygame.draw.circle(surface, tones["shadow"], over, radius - 3)
    glint = (over[0] - radius // 3, over[1] - radius // 3)
    if surface.get_rect().collidepoint(glint):
        pygame.draw.rect(surface, tones["light"], (glint[0], glint[1], 2, 1))
        surface.set_at((glint[0], glint[1] + 1), tones["base"])


def thorn(surface, base, direction, wide, tall, color, outline=OUTLINE):
    """A small triangle standing on an edge: a spike of chitin, or a tooth."""
    along = (-direction[1], direction[0])
    corners = [(base[0] - along[0] * wide, base[1] - along[1] * wide),
               (base[0] + direction[0] * tall, base[1] + direction[1] * tall),
               (base[0] + along[0] * wide, base[1] + along[1] * wide)]
    corners = [(round(x), round(y)) for x, y in corners]
    pygame.draw.polygon(surface, color, corners)
    pygame.draw.polygon(surface, outline, corners, 1)


def segment(start, end, widths, count=5):
    """The points and the widths of a straight segment of the limb."""
    points = [(start[0] + (end[0] - start[0]) * index / (count - 1), start[1] + (end[1] - start[1]) * index / (count - 1))
              for index in range(count)]
    return points, spread(widths, count)


def draw(surface, limb, offset=(0, 0)):
    """Paint the whole limb of a pose() on the surface, from the shoulder to the tips of the jaws."""
    def moved(point):
        return (point[0] + offset[0], point[1] + offset[1])
    shoulder, elbow, wrist, hinge = (moved(limb[name]) for name in ("shoulder", "elbow", "wrist", "hinge"))
    heading, opening = limb["heading"], limb["opening"]
    upper, upper_widths = segment(shoulder, elbow, UPPER_WIDTHS)
    fore, fore_widths = segment(elbow, wrist, FOREARM_WIDTHS)
    hand, hand_widths = segment(wrist, hinge, HAND_WIDTHS)
    ribbon(surface, upper, upper_widths)
    # The saw of chitin: spikes on the outer edge of the forearm, the side of the elbow's bend.
    sides = normals(fore)
    outer = -1 if lit_side(sides) == 1 else 1  # the bend is on the side away from the light
    rim = edge(fore, fore_widths, sides, outer)
    for index in range(SPIKES):
        share = (index + 0.8) / (SPIKES + 0.6)
        place = share * (len(rim) - 1)
        low = min(int(place), len(rim) - 2)
        base = (rim[low][0] + (rim[low + 1][0] - rim[low][0]) * (place - low),
                rim[low][1] + (rim[low + 1][1] - rim[low][1]) * (place - low))
        nx, ny = sides[low]
        thorn(surface, base, (nx * outer, ny * outer), 3, 6 if index % 2 == 0 else 4, SHADOW)
    ribbon(surface, fore, fore_widths)
    joint(surface, elbow, ELBOW, math.atan2(wrist[1] - elbow[1], wrist[0] - elbow[0]))
    # The jaws, each with its small teeth on the inside, under the hand that holds them.
    for side in (1, -1):
        line = jaw_line(hinge, heading, side, opening)
        widths = list(JAW_WIDTHS)
        sides = normals(line)
        inner = edge(line, widths, sides, side)  # the edge that faces the other jaw
        for index in range(TEETH):
            place = 2 + index
            nx, ny = sides[place]
            thorn(surface, inner[place], (nx * side, ny * side), 2, 4 if index % 2 == 0 else 3, TOOTH)
        ribbon(surface, line, widths)
    ribbon(surface, hand, hand_widths)
    joint(surface, wrist, WRIST, heading)
    joint(surface, hinge, HINGE, heading)


def layer(size, limb, offset=(0, 0)):
    """The limb alone on a clear picture of this size: to draw it, and to cast its shadow."""
    picture = pygame.Surface(size, pygame.SRCALPHA)
    draw(picture, limb, offset)
    return picture


def shadow_of(picture, darkness=120):
    """The dark shape a picture of the limb casts: the same outline, see-through black."""
    return pygame.mask.from_surface(picture).to_surface(setcolor=(0, 0, 0, darkness), unsetcolor=(0, 0, 0, 0))


# --- Portraits: a claw alone in a frame, for the choice of the difficulty -------------------
#
# The same shell as the giant claw, smaller and still: a forearm coming in from the bottom
# left, the hand, and the two jaws pointing up and to the right. The gentle one is a common
# crab's claw: sandy orange, thick and round, with blunt jaws, knobbly little teeth and pale
# speckles on the hand. The fierce one is the claw of the end of the game: red, with long
# hooked jaws full of sharp teeth and a saw of spikes along its arm and its hand.

PORTRAIT_AIM = -0.9      # radians: where the hand points, up and to the right
GENTLE = {"tones": CORAL, "fore": (6, 8, 8), "hand": (10, 16, 17, 13), "hand_length": 30,
          "jaw": 36, "jaw_widths": (8, 9, 8, 8, 7, 6, 5, 4, 3), "gap": 6, "spread": 0.3, "curl": 0.75,
          "spikes": 0, "teeth": 4, "tooth": (2, 2)}
FIERCE = {"tones": RED, "fore": (6, 8, 8), "hand": (9, 13, 13, 10), "hand_length": 26,
          "jaw": 46, "jaw_widths": (8, 8, 7, 6, 5, 4, 3, 2, 1), "gap": 5, "spread": 0.55, "curl": 1.35,
          "spikes": 6, "teeth": 6, "tooth": (2, 5)}
SPECKLES = ((0.25, 0.35), (0.5, -0.4), (0.7, 0.25), (0.45, 0.05), (0.85, -0.15), (0.15, -0.25))  # along, across


def seam(surface, point, heading, half_width, tones):
    """Where two pieces of shell meet: a dark line across, with a pale glint on the lit side."""
    nx, ny = -math.sin(heading), math.cos(heading)
    a = (round(point[0] - nx * half_width), round(point[1] - ny * half_width))
    b = (round(point[0] + nx * half_width), round(point[1] + ny * half_width))
    pygame.draw.line(surface, tones["outline"], a, b, 2)
    lit = a if nx * LIGHT_FROM[0] + ny * LIGHT_FROM[1] < 0 else b
    toward = (point[0] - lit[0], point[1] - lit[1])
    length = math.hypot(*toward) or 1.0
    glint = (round(lit[0] + toward[0] / length * 3 + math.cos(heading) * 2),
             round(lit[1] + toward[1] / length * 3 + math.sin(heading) * 2))
    dot(surface, glint[0], glint[1], tones["light"])


def portrait(size, fierce, opening=0.25):
    """A claw alone on a clear picture of this size: the fierce red one, or the gentle orange one."""
    look = FIERCE if fierce else GENTLE
    tones = look["tones"]
    width, height = size
    picture = pygame.Surface(size, pygame.SRCALPHA)
    heading = PORTRAIT_AIM
    cos, sin = math.cos(heading), math.sin(heading)
    reach = look["hand_length"] + look["jaw"] * 0.7  # from the wrist to about the tips
    wrist = (width * 0.5 - reach * cos * 0.5, height * 0.52 - reach * sin * 0.5)
    elbow = (wrist[0] - 40 * math.cos(heading + 0.3), wrist[1] - 40 * math.sin(heading + 0.3))
    hinge = (wrist[0] + look["hand_length"] * cos, wrist[1] + look["hand_length"] * sin)
    fore, fore_widths = segment(elbow, wrist, look["fore"])
    hand, hand_widths = segment(wrist, hinge, look["hand"], 7)
    outer = -1 if lit_side(normals(fore)) == 1 else 1  # the side away from the light: the back of the claw
    if look["spikes"]:  # the saw of chitin along the back of the arm and of the hand
        for line, widths in ((fore, fore_widths), (hand, hand_widths)):
            line_sides = normals(line)
            rim = edge(line, widths, line_sides, outer)
            for index in range(1, len(rim) - 1):
                nx, ny = line_sides[index]
                thorn(picture, rim[index], (nx * outer, ny * outer), 2, 6 if index % 2 else 4, tones["shadow"],
                      tones["outline"])
    ribbon(picture, fore, fore_widths, tones)
    knuckle = (round(hinge[0] + cos * 2), round(hinge[1] + sin * 2))  # under the roots of the two jaws: no hole
    pygame.draw.circle(picture, tones["outline"], knuckle, look["gap"] + 3)
    pygame.draw.circle(picture, tones["shadow"], knuckle, look["gap"] + 2)
    for side in (1, -1):
        line = jaw_line(hinge, heading, side, opening, look["jaw"], look["gap"], look["spread"], look["curl"])
        widths = list(look["jaw_widths"])
        jaw_sides = normals(line)
        inner = edge(line, widths, jaw_sides, side)
        wide, tall = look["tooth"]
        for index in range(look["teeth"]):
            place = 1 + index
            nx, ny = jaw_sides[place]
            if fierce:
                thorn(picture, inner[place], (nx * side, ny * side), wide, tall - index % 2, tones["tooth"],
                      tones["outline"])
            else:  # knobbly little teeth: round bumps
                x, y = inner[place][0] + nx * side * 1.5, inner[place][1] + ny * side * 1.5
                pygame.draw.circle(picture, tones["outline"], (round(x), round(y)), wide + 1)
                pygame.draw.circle(picture, tones["tooth"], (round(x), round(y)), wide)
        ribbon(picture, line, widths, tones)
        if not fierce:  # a blunt, rounded tip, darker like a real crab's
            tip = line[-1]
            pygame.draw.circle(picture, tones["outline"], (round(tip[0]), round(tip[1])), 4)
            pygame.draw.circle(picture, tones["plate"], (round(tip[0]), round(tip[1])), 3)
            dot(picture, tip[0] - 1, tip[1] - 1, tones["shadow"])
    ribbon(picture, hand, hand_widths, tones)
    if not fierce:  # pale speckles on the round palm
        hand_sides = normals(hand)
        for along_share, across in SPECKLES:
            place = along_share * (len(hand) - 1)
            low = min(int(place), len(hand) - 2)
            x = hand[low][0] + (hand[low + 1][0] - hand[low][0]) * (place - low)
            y = hand[low][1] + (hand[low + 1][1] - hand[low][1]) * (place - low)
            nx, ny = hand_sides[low]
            w = hand_widths[low]
            pygame.draw.rect(picture, tones["light"], (round(x + nx * w * across), round(y + ny * w * across), 2, 2))
    seam(picture, wrist, heading, look["fore"][-1] + 1, tones)
    return picture
