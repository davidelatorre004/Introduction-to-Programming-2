"""The pixel art of Plot Twist: every sprite and tile, drawn as text.

Each picture is a list of rows, and each character of a row is one pixel: the
PALETTE says its color, and "." is transparent. To change a picture, change its
letters; every row of a picture must be as long as the others.

Names follow what main.py looks for:
- an item, puzzle or character by its id, or by id and status ("hold_puzzle_solved"),
  or else by kind and status ("switch_on"); the barrier as "barrier_0" and "barrier_1";
- doors as "door_open", "door_locked" and "door_sealed", drawn for the north wall
  (main.py turns them for the other walls);
- the player as "player_<down/up/right>_<0, 1 or 2>": 0 standing, 1 and 2 walking
  (left is right mirrored);
- the room tiles as "floor_<room>" and "wall_<room>", with "_0" and "_1" for the
  two frames of a moving tile (the sea around the deck).
A picture missing here is drawn as a colored rectangle by main.py.
"""

import pygame

PALETTE = {
    "k": (20, 16, 28),     # outline, black
    "w": (244, 240, 228),  # white
    "l": (176, 176, 190),  # light gray
    "d": (96, 96, 112),    # dark gray
    "r": (214, 64, 52),    # red
    "R": (130, 30, 34),    # dark red
    "o": (240, 140, 50),   # orange
    "y": (252, 214, 80),   # yellow
    "Y": (190, 140, 40),   # brass
    "b": (186, 128, 70),   # light wood
    "B": (140, 90, 50),    # wood
    "n": (88, 56, 34),     # dark wood
    "s": (40, 88, 168),    # sea
    "S": (24, 52, 112),    # deep sea
    "f": (150, 196, 236),  # foam
    "c": (112, 232, 255),  # magic
    "C": (56, 148, 200),   # dark magic
    "p": (186, 116, 255),  # purple
    "P": (112, 62, 176),   # dark purple
    "z": (250, 200, 160),  # skin
    "Z": (214, 150, 110),  # skin shadow
    "h": (96, 62, 40),     # hair
    "g": (96, 200, 120),   # green
    "G": (52, 128, 80),    # dark green
    "j": (60, 80, 150),    # trousers
    "t": (70, 128, 128),   # teal
    "T": (40, 82, 88),     # dark teal
    "m": (232, 226, 210),  # marble
    "M": (190, 184, 168),  # marble shadow
}

# The player's head and body are the same in the three frames of a direction:
# only the legs change.
PLAYER_DOWN = [
    "................",
    "......kkkk......",
    "....kkhhhhkk....",
    "...khhhhhhhhk...",
    "...khhhhhhhhk...",
    "...khzzzzzzhk...",
    "...kzkzzzzkzk...",
    "...kzzzzzzzzk...",
    "....kzzZZzzk....",
    "...kkggggggkk...",
    "..kzkggGGggkzk..",
    "..kzkggggggkzk..",
    "...kkjjjjjjkk...",
]
PLAYER_UP = [
    "................",
    "......kkkk......",
    "....kkhhhhkk....",
    "...khhhhhhhhk...",
    "...khhhhhhhhk...",
    "...khhhhhhhhk...",
    "...khhhhhhhhk...",
    "...kZhhhhhhZk...",
    "....kZzzzzZk....",
    "...kkggggggkk...",
    "..kzkggggggkzk..",
    "..kzkggGGggkzk..",
    "...kkjjjjjjkk...",
]
PLAYER_RIGHT = [
    "................",
    ".....kkkkk......",
    "....khhhhhkk....",
    "...khhhhhhhhk...",
    "...khhhhhzzzk...",
    "...khhhzzzzzk...",
    "...khhzzzzkzk...",
    "...kkhzzzzzzk...",
    "....kkzzzZzk....",
    "....kkggggkk....",
    "....kgggkzzk....",
    "....kggggGk.....",
    "....kjjjjjk.....",
]
LEGS_FRONT = [
    ["....kjjkkjjk....", "....kkk..kkk....", "................"],  # standing
    ["....kjjkkkkk....", "....kkk.........", "................"],  # left foot down
    ["....kkkkkjjk....", ".........kkk....", "................"],  # right foot down
]
LEGS_SIDE = [
    ["....kjjkjjk.....", "....kkk.kkk.....", "................"],  # standing
    ["...kjjk.kjjk....", "...kkk...kkk....", "................"],  # a long step
    ["....kjjkjjk.....", "....kkk.kkk.....", "................"],  # feet together again
]

SPRITES = {
    "player_down_0": PLAYER_DOWN + LEGS_FRONT[0],
    "player_down_1": PLAYER_DOWN + LEGS_FRONT[1],
    "player_down_2": PLAYER_DOWN + LEGS_FRONT[2],
    "player_up_0": PLAYER_UP + LEGS_FRONT[0],
    "player_up_1": PLAYER_UP + LEGS_FRONT[1],
    "player_up_2": PLAYER_UP + LEGS_FRONT[2],
    "player_right_0": PLAYER_RIGHT + LEGS_SIDE[0],
    "player_right_1": PLAYER_RIGHT + LEGS_SIDE[1],
    "player_right_2": PLAYER_RIGHT + LEGS_SIDE[2],
    "wand": [
        "................",
        "................",
        "................",
        "..........kyk...",
        ".........kywyk..",
        "..........kyk...",
        ".........kPk....",
        "........kPpk....",
        ".......kPpk.....",
        "......kPpk......",
        ".....kPpk.......",
        "....kPpk........",
        "...kPpk.........",
        "...kkk..........",
        "................",
        "................",
    ],
    "key": [
        "................",
        "................",
        "................",
        "................",
        "................",
        "..kkk...........",
        ".kyyyk..........",
        "kyk.kykkkkkkkk..",
        "kyk.kyyyyyyyyyk.",
        "kyk.kykkkkykyk..",
        ".kyyyk....kykk..",
        "..kkk......k....",
        "................",
        "................",
        "................",
        "................",
    ],
    # A generator of the cabin, with its lamp and its lever: off, then on.
    "switch_off": [
        "................",
        "...kkkkkkkkkk...",
        "...kllllllllk...",
        "...kllkkkkllk...",
        "...klkddddklk...",
        "...klkddddklk...",
        "...kllkkkkllkk..",
        "...kllllllllkdk.",
        "...kddddddddkdk.",
        "...kllllllllkdk.",
        "...kllllllllkrrk",
        "...kllllllllkrrk",
        "...kddddddddkkk.",
        "...kkkkkkkkkk...",
        "...kk......kk...",
        "................",
    ],
    "switch_on": [
        "............kk..",
        "...kkkkkkkkkkrrk",
        "...kllllllllkrrk",
        "...kllkkkkllkdk.",
        "...klkyyyyklkdk.",
        "...klkywyyklkdk.",
        "...kllkkkkllkk..",
        "...kllllllllk...",
        "...kddddddddk...",
        "...kllllllllk...",
        "...kllllllllk...",
        "...kllllllllk...",
        "...kddddddddk...",
        "...kkkkkkkkkk...",
        "...kk......kk...",
        "................",
    ],
    # The barrier's energy, drawn over each of its tiles: two pictures that flicker.
    "barrier_0": [
        "c.....c.....c...",
        ".C...c.C...c.C..",
        "..C.c...C.c...C.",
        "...c.....c.....c",
        "..c.C...c.C...c.",
        ".c...C.c...C.c..",
        "c.....c.....c...",
        ".C...c.C...c.C..",
        "..C.c...C.c...C.",
        "...c.....c.....c",
        "..c.C...c.C...c.",
        ".c...C.c...C.c..",
        "c.....c.....c...",
        ".C...c.C...c.C..",
        "..C.c...C.c...C.",
        "...c.....c.....c",
    ],
    "barrier_1": [
        "...c.....c.....c",
        "..c.C...c.C...c.",
        ".c...C.c...C.c..",
        "c.....c.....c...",
        ".C...c.C...c.C..",
        "..C.c...C.c...C.",
        "...c.....c.....c",
        "..c.C...c.C...c.",
        ".c...C.c...C.c..",
        "c.....c.....c...",
        ".C...c.C...c.C..",
        "..C.c...C.c...C.",
        "...c.....c.....c",
        "..c.C...c.C...c.",
        ".c...C.c...C.c..",
        "c.....c.....c...",
    ],
    # The stone altar: what lies on it is drawn a little higher, on its top.
    "altar": [
        "................",
        "................",
        "................",
        "................",
        "................",
        "..kkkkkkkkkkkk..",
        "..kmmmmmmmmmmk..",
        "..kMMMMMMMMMMk..",
        "...kkkkkkkkkk...",
        "....kmmmmmmk....",
        "....kmMmmMmk....",
        "....kmmmmmmk....",
        "....kMMMMMMk....",
        "...kkkkkkkkkk...",
        "...kMMMMMMMMk...",
        "...kkkkkkkkkk...",
    ],
    "hold_puzzle_unsolved": [
        "................",
        "....kkkkkkkk....",
        "...kBnBBBBnBk...",
        "..kbbbbbbbbbbk..",
        "..knnnnnnnnnnk..",
        "..kbbbbbbbbbbk..",
        "..kbcbbcbbcbbk..",
        "..kbbcbcbcbbbk..",
        "..kbcbbcbbcbbk..",
        "..kbbbbbbbbbbk..",
        "..knnnnnnnnnnk..",
        "..kbbbbbbbbbbk..",
        "...kBBBBBBBBk...",
        "....kkkkkkkk....",
        "................",
        "................",
    ],
    "hold_puzzle_solved": [
        "................",
        "....kkkkkkkk....",
        "...kBnBBBBnBk...",
        "..kbbbbbbbbbbk..",
        "..knnnnnnnnnnk..",
        "..kbbbbbbbbbbk..",
        "..kbbbbbbbbbbk..",
        "..kbwbwwbwbwbk..",
        "..kbbbbbbbbbbk..",
        "..kbbbbbbbbbbk..",
        "..knnnnnnnnnnk..",
        "..kbbbbbbbbbbk..",
        "...kBBBBBBBBk...",
        "....kkkkkkkk....",
        "................",
        "................",
    ],
    "crab": [
        "................",
        "................",
        ".kk..........kk.",
        "krrk........krrk",
        "krkrk......krkrk",
        ".krrk......krrk.",
        "..kk.kk..kk.kk..",
        "....kwk..kwk....",
        "....kkkkkkkk....",
        "..kkrrrrrrrrkk..",
        ".krrrrrrrrrrrrk.",
        ".krRrrrrrrrrRrk.",
        "..kkrRrrrrRrkk..",
        ".kr.kkkkkkkk.rk.",
        "kr..kr....rk..rk",
        "k...k......k...k",
    ],
    "angel": [
        "....kkyyyykk....",
        "......kkkk......",
        ".....kyyyyk.....",
        "....kyzzzzyk....",
        "....kzkzzkzk....",
        "....kzzzzzzk....",
        "lk...kzZZzk...kl",
        "llk.kwwwwwwk.kll",
        "lllkwwwwwwwwklll",
        "llkwwwlwwlwwwkll",
        ".lkwwwwwwwwwwkl.",
        "..kwwwwwwwwwwk..",
        "..kwwwlwwlwwwk..",
        "..kwwwwwwwwwwk..",
        "...kkkkkkkkkk...",
        "................",
    ],
    # The doors (as on the north wall), the ship and the room tiles. These were
    # composed by a small script, but they are plain pictures like the others.
    "door_open": [
        "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk",
        "knnnnnnnnnnnnnnnnnnnnnnnnnnnnnnk",
        "knBkkkkkkkkkkkkkkkkkkkkkkkkkkBnk",
        "knBkkkkkkkkkkkkkkkkkkkkkkkkkkBnk",
        "knBkkkkkkkkkkkkkkkkkkkkkkkkkkBnk",
        "knBkkkkkkkkkkkkkkkkkkkkkkkkkkBnk",
        "knBkkkkkkkkkkkkkkkkkkkkkkkkkkBnk",
        "knBkkkkkkkkkkkkkkkkkkkkkkkkkkBnk",
        "knBkkkkkkkkkkkkkkkkkkkkkkkkkkBnk",
        "knBkkkkkkkkkkkkkkkkkkkkkkkkkkBnk",
        "knBkkkkkkkkkkkkkkkkkkkkkkkkkkBnk",
        "knBkkkkkkkkkkkkkkkkkkkkkkkkkkBnk",
        "knBkkkkkkkkkkkkkkkkkkkkkkkkkkBnk",
        "knBkkkkkkkkkkkkkkkkkkkkkkkkkkBnk",
        "knBkkkkkkkkkkkkkkkkkkkkkkkkkkBnk",
        "knBddddddddddddddddddddddddddBnk",
    ],
    "door_locked": [
        "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk",
        "knnnnnnnnnnnnnnnnnnnnnnnnnnnnnnk",
        "knBbbbBbbbBbbbBkkBbbbBbbbBbbbBnk",
        "knBnnnnnnnnnnnnkknnnnnnnnnnnnBnk",
        "knBbbbBbbbBbbbBkkBbbbBbbbBbbbBnk",
        "knBbbbBbbbBbbbBkkBbbbBbbbBbbbBnk",
        "knBbbbBbbbBbbbBkkBbbbBbbbBbbbBnk",
        "knBbbbBbbbBbkkkkkkkkBbbbBbbbbBnk",
        "knBbbbBbbbBkYYYYYYYYkBbbbBbbbBnk",
        "knBbbbBbbbBkYYkkkkYYkBbbbBbbbBnk",
        "knBbbbBbbbBkYYYkkYYYkBbbbBbbbBnk",
        "knBbbbBbbbBbkkkkkkkkBbbbBbbbbBnk",
        "knBbbbBbbbBbbbBkkBbbbBbbbBbbbBnk",
        "knBnnnnnnnnnnnnkknnnnnnnnnnnnBnk",
        "knBbbbBbbbBbbbBkkBbbbBbbbBbbbBnk",
        "knBbbbBbbbBbbbBkkBbbbBbbbBbbbBnk",
    ],
    "door_sealed": [
        "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk",
        "knnnnnnnnnnnnnnnnnnnnnnnnnnnnnnk",
        "knBnRrBnnnBnnnBkkBnnnBnnnBrRnBnk",
        "knBnnRrnnnBnnnBkkBnnnBnnnrRnnBnk",
        "knBnnnBRrnBnnnBkkBnnnBnrRBnnnBnk",
        "knBnnnBnnRrnnnBkkBnnnrRnnBnnnBnk",
        "knBnnnBnnnBRrnBkkBnrRBnnnBnnnBnk",
        "knBnnnBnnnBnnRrkkrRnnBnnnBnnnBnk",
        "knBnnnBnnnBnnnBRRBnnnBnnnBnnnBnk",
        "knBnnnBnnnBnnnrRRrnnnBnnnBnnnBnk",
        "knBnnnBnnnBnrRBkkBRrnBnnnBnnnBnk",
        "knBnnnBnnnrRnnBkkBnnRrnnnBnnnBnk",
        "knBnnnBnrRBnnnBkkBnnnBRrnBnnnBnk",
        "knBnnnrRnnBnnnBkkBnnnBnnRrnnnBnk",
        "knBnrRBnnnBnnnBkkBnnnBnnnBRrnBnk",
        "knBRnnBnnnBnnnBkkBnnnBnnnBnnRBnk",
    ],
    "ship": [
        "...............k................",
        "..............kwk...............",
        ".............kwwwk..............",
        "............kwwwwwk.............",
        "...........kwwwwwwwk............",
        "..........kwwwlwwwwwk...........",
        ".........kwwwwlwwwwwwk..........",
        "...............n................",
        "...............n................",
        ".kkkkkkkkkkkkkkkkkkkkkkkkkkkkkk.",
        ".kbbbbbbbbbbbbbbbbbbbbbbbbbbbbk.",
        "..kBbbBbbBbbBbbBbbBbbBbbBbbBbk..",
        "...kbbbbbbbbbbbbbbbbbbbbbbbbk...",
        "....kkkkkkkkkkkkkkkkkkkkkkkk....",
        "................................",
        "................................",
    ],
    "floor_deck": [
        "bbbbbbbBbbbbbbbb",
        "bbbbbbbBbbbbbbbb",
        "bbbbbbbBbbbbbbbb",
        "BBBBBBBBBBBBBBBB",
        "bbbBbbbbbbbbbbbb",
        "bbbBbbbbbbbbbbbb",
        "bbbBbbbbbbbbbbbb",
        "BBBBBBBBBBBBBBBB",
        "bbbbbbbbbbbBbbbb",
        "bbbbbbbbbbbBbbbb",
        "bbbbbbbbbbbBbbbb",
        "BBBBBBBBBBBBBBBB",
        "Bbbbbbbbbbbbbbbb",
        "Bbbbbbbbbbbbbbbb",
        "Bbbbbbbbbbbbbbbb",
        "BBBBBBBBBBBBBBBB",
    ],
    "floor_cabin": [
        "BBBBnBBBBBBBBBBB",
        "BBBBnBBBBBBBBBBB",
        "BBBBnBBBBBBBBBBB",
        "nnnnnnnnnnnnnnnn",
        "BBBBBBBBBBBBnBBB",
        "BBBBBBBBBBBBnBBB",
        "BBBBBBBBBBBBnBBB",
        "nnnnnnnnnnnnnnnn",
        "BnBBBBBBBBBBBBBB",
        "BnBBBBBBBBBBBBBB",
        "BnBBBBBBBBBBBBBB",
        "nnnnnnnnnnnnnnnn",
        "BBBBBBBBnBBBBBBB",
        "BBBBBBBBnBBBBBBB",
        "BBBBBBBBnBBBBBBB",
        "nnnnnnnnnnnnnnnn",
    ],
    "floor_hold": [
        "lllllllklllllllk",
        "dddddddkdddddddk",
        "dddddddkdddddddk",
        "dddddddkdddddddk",
        "dddddddkdddddddk",
        "dddddddkdddddddk",
        "dddddddkdddddddk",
        "kkkkkkkkkkkkkkkk",
        "lllklllllllkllll",
        "dddkdddddddkdddd",
        "dddkdddddddkdddd",
        "dddkdddddddkdddd",
        "dddkdddddddkdddd",
        "dddkdddddddkdddd",
        "dddkdddddddkdddd",
        "kkkkkkkkkkkkkkkk",
    ],
    "wall_hold": [
        "BBBBBBBkBBBBBBBk",
        "nnnnnnnknnnnnnnk",
        "nnnnnnnknnnnnnnk",
        "kkkkkkkkkkkkkkkk",
        "BBBkBBBBBBBkBBBB",
        "nnnknnnnnnnknnnn",
        "nnnknnnnnnnknnnn",
        "kkkkkkkkkkkkkkkk",
        "BBBBBBBkBBBBBBBk",
        "nnnnnnnknnnnnnnk",
        "nnnnnnnknnnnnnnk",
        "kkkkkkkkkkkkkkkk",
        "BBBkBBBBBBBkBBBB",
        "nnnknnnnnnnknnnn",
        "nnnknnnnnnnknnnn",
        "kkkkkkkkkkkkkkkk",
    ],
    "wall_cabin": [
        "BBBBBBBBBBBBBBBB",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "kkkkkkkkkkkkkkkk",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "BBBBBBBBBBBBBBBB",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "kkkkkkkkkkkkkkkk",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "kkkkkkkkkkkkkkkk",
    ],
    "floor_crab_room": [
        "fttttttttttttttt",
        "ttttTtttttttfttt",
        "ttttttttTttttttt",
        "tttttttfttttTttt",
        "tttttttttttttttt",
        "ttfTtttttttttttt",
        "tttttttTttttttft",
        "TTTTTTTTTTTTTTTT",
        "tttttttttftttttT",
        "ttTttttttttttttt",
        "ttttftTttttttttt",
        "ttttttttttTttttt",
        "ttttttttttttttTt",
        "tTtttttttttftttt",
        "tttttTtttttttttt",
        "TTTTTTTTTTTTTTTT",
    ],
    "wall_crab_room": [
        "tttttttktttttttk",
        "TTTTTTTkTTTTTTTk",
        "TTTTTTTkTTTTTTTk",
        "kkkkkkkkkkkkkkkk",
        "tttktttttttktttt",
        "TTTkTTTTTTTkTTTT",
        "TTTkTTTTTTTkTTTT",
        "kkkkkkkkkkkkkkkk",
        "tttttttktttttttk",
        "TTTTTTTkTTTTTTTk",
        "TTTTTTTkTTTTTTTk",
        "kkkkkkkkkkkkkkkk",
        "tttktttttttktttt",
        "TTTkTTTTTTTkTTTT",
        "TTTkTTTTTTTkTTTT",
        "kkkkkkkkkkkkkkkk",
    ],
    "floor_angel_room": [
        "mmmmmmmmMMMMMMMM",
        "mmmmmmmmMMMMMMMM",
        "mmmmmmmmMMMMMMMM",
        "mmllmmmmMMMMMMMM",
        "mmmmmmmmMMMMMMMM",
        "mmmmmmmmMMMMMMMM",
        "mmmmmmmmMMMMMMMM",
        "mmmmmmmmMMMMMMMM",
        "MMMMMMMMmmmmmmmm",
        "MMMMMMMMmmmmmmmm",
        "MMMMMMMMmmmmmmmm",
        "MMMMMMMMmmmmmmmm",
        "MMMMMMMMmmmllmmm",
        "MMMMMMMMmmmmmmmm",
        "MMMMMMMMmmmmmmmm",
        "MMMMMMMMmmmmmmmm",
    ],
    "wall_angel_room": [
        "yyyyyyyyyyyyyyyy",
        "YYYYYYYYYYYYYYYY",
        "mmmmmmmlmmmmmmml",
        "MMMMMMMlMMMMMMMl",
        "MMMMMMMlMMMMMMMl",
        "llllllllllllllll",
        "mmmlmmmmmmmlmmmm",
        "MMMlMMMMMMMlMMMM",
        "MMMlMMMMMMMlMMMM",
        "llllllllllllllll",
        "mmmmmmmlmmmmmmml",
        "MMMMMMMlMMMMMMMl",
        "MMMMMMMlMMMMMMMl",
        "llllllllllllllll",
        "YYYYYYYYYYYYYYYY",
        "yyyyyyyyyyyyyyyy",
    ],
    "wall_deck_0": [
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssffffssssssssss",
        "sfSSSSfsssssssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssssssffffss",
        "sssssssssfSSSSfs",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
    ],
    "wall_deck_1": [
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ffssssssssssssff",
        "SSfssssssssssfSS",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssffffssssss",
        "sssssfSSSSfsssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
        "ssssssssssssssss",
    ],
}

# Pictures already turned into pygame Surfaces: (name, turns, flip) -> Surface.
_images = {}


def image(name, turns=0, flip=False):
    """The picture called `name` as a Surface, or None if there is no such picture.

    `turns` turns it a quarter turn counterclockwise each, `flip` mirrors it left
    to right. Each picture is drawn pixel by pixel only the first time.
    """
    if name not in SPRITES:
        return None
    key = (name, turns % 4, flip)
    if key not in _images:
        picture = build(SPRITES[name])
        if flip:
            picture = pygame.transform.flip(picture, True, False)
        if turns % 4:
            picture = pygame.transform.rotate(picture, 90 * (turns % 4))
        _images[key] = picture
    return _images[key]


def build(rows):
    """Draw a picture from its rows of letters, on a transparent Surface."""
    picture = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, letter in enumerate(row):
            if letter != ".":
                picture.set_at((x, y), PALETTE[letter])
    return picture
