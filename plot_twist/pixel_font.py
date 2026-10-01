"""The pixel font of Plot Twist, drawn as text like the sprites.

Every character is a small picture 9 pixels tall, where "#" is a pixel and "."
is empty. Capitals and digits use the top 7 rows, small letters rows 2 to 6,
and g, j, p, q, y go down into the last two rows. Accents sit above the letters.

The characters are written in "sheets": the characters in a string, and below
them their pictures side by side, separated by spaces. A sheet of 7 rows gets
two empty rows added at the bottom.

PixelFont can be used like pygame.font.Font: render(), size() and get_linesize().
"""

import pygame

HEIGHT = 9      # rows of every character
SPACING = 1     # empty columns between two characters
LINE_GAP = 2    # empty rows between two lines of text

SHEETS = [
    ("ABCDEFGHIJKLM", """
.###. ####. .###. ####. ##### ##### .###. #...# ### ..### #...# #.... #...#
#...# #...# #...# #...# #.... #.... #...# #...# .#. ...#. #..#. #.... ##.##
#...# #...# #.... #...# #.... #.... #.... #...# .#. ...#. #.#.. #.... #.#.#
##### ####. #.... #...# ####. ####. #.### ##### .#. ...#. ##... #.... #...#
#...# #...# #.... #...# #.... #.... #...# #...# .#. ...#. #.#.. #.... #...#
#...# #...# #...# #...# #.... #.... #...# #...# .#. #..#. #..#. #.... #...#
#...# ####. .###. ####. ##### #.... .###. #...# ### .##.. #...# ##### #...#
"""),
    ("NOPQRSTUVWXYZ", """
#...# .###. ####. .###. ####. .###. ##### #...# #...# #...# #...# #...# #####
##..# #...# #...# #...# #...# #...# ..#.. #...# #...# #...# #...# #...# ....#
#.#.# #...# #...# #...# #...# #.... ..#.. #...# #...# #...# .#.#. .#.#. ...#.
#..## #...# ####. #...# ####. .###. ..#.. #...# #...# #.#.# ..#.. ..#.. ..#..
#...# #...# #.... #.#.# #.#.. ....# ..#.. #...# #...# #.#.# .#.#. ..#.. .#...
#...# #...# #.... #..#. #..#. #...# ..#.. #...# .#.#. ##.## #...# ..#.. #....
#...# .###. #.... .##.# #...# .###. ..#.. .###. ..#.. #...# #...# ..#.. #####
"""),
    ("abcdefghijklm", """
..... #.... .... ....# ..... ..## ..... #.... # ..# #... #. .....
..... #.... .... ....# ..... .#.. ..... #.... . ... #... #. .....
.###. ####. .### .#### .###. #### .#### ####. # ..# #..# #. ####.
....# #...# #... #...# #...# .#.. #...# #...# # ..# #.#. #. #.#.#
.#### #...# #... #...# ##### .#.. #...# #...# # ..# ##.. #. #.#.#
#...# #...# #... #...# #.... .#.. #...# #...# # ..# #.#. #. #.#.#
.#### ####. .### .#### .###. .#.. .#### #...# # ..# #..# .# #.#.#
..... ..... .... ..... ..... .... ....# ..... . ..# .... .. .....
..... ..... .... ..... ..... .... .###. ..... . ##. .... .. .....
"""),
    ("nopqrstuvwxyz", """
..... ..... ..... ..... .... .... .#.. ..... ..... ..... ..... ..... .....
..... ..... ..... ..... .... .... .#.. ..... ..... ..... ..... ..... .....
####. .###. ####. .#### #.## .### #### #...# #...# #...# #...# #...# #####
#...# #...# #...# #...# ##.. #... .#.. #...# #...# #...# .#.#. #...# ...#.
#...# #...# #...# #...# #... .##. .#.. #...# #...# #.#.# ..#.. #...# ..#..
#...# #...# #...# #...# #... ...# .#.. #...# .#.#. #.#.# .#.#. #...# .#...
#...# .###. ####. .#### #... ###. ..## .#### ..#.. .#.#. #...# .#### #####
..... ..... #.... ....# .... .... .... ..... ..... ..... ..... ....# .....
..... ..... #.... ....# .... .... .... ..... ..... ..... ..... .###. .....
"""),
    ("àèéìòùÀÈÉÌÒÙ", """
.#... .#... ...#. #.. .#... .#... .#... .#... ...#. #.. .#... .#...
..#.. ..#.. ..#.. .#. ..#.. ..#.. .###. ##### ##### ### .###. #...#
.###. .###. .###. ... .###. #...# #...# #.... #.... .#. #...# #...#
....# #...# #...# .#. #...# #...# ##### ####. ####. .#. #...# #...#
.#### ##### ##### .#. #...# #...# #...# #.... #.... .#. #...# #...#
#...# #.... #.... .#. #...# #...# #...# #.... #.... .#. #...# #...#
.#### .###. .###. .#. .###. .#### #...# ##### ##### ### .###. .###.
"""),
    ("0123456789", """
.###. .#. .###. ####. ...#. ##### .###. ##### .###. .###.
#...# ##. #...# ....# ..##. #.... #.... ....# #...# #...#
#..## .#. ....# ....# .#.#. ####. #.... ...#. #...# #...#
#.#.# .#. ...#. .###. #..#. ....# ####. ..#.. .###. .####
##..# .#. ..#.. ....# ##### ....# #...# ..#.. #...# ....#
#...# .#. .#... ....# ...#. #...# #...# ..#.. #...# ....#
.###. ### ##### ####. ...#. .###. .###. ..#.. .###. .###.
"""),
    (" .,:;!?'\"-()/", """
... . .. . .. # .###. # #.# ... .# #. ..#
... . .. . .. # #...# # #.# ... #. .# ..#
... . .. . .. # ...#. . ... ... #. .# .#.
... . .. # .# # ..#.. . ... ... #. .# .#.
... . .. . .. # ..#.. . ... ### #. .# .#.
... . .. . .. . ..... . ... ... #. .# #..
... # .# # .# # ..#.. . ... ... .# #. #..
... . #. . #. . ..... . ... ... .. .. ...
... . .. . .. . ..... . ... ... .. .. ...
"""),
    ("«»·<>+=%—…", """
.... .... . ... ... ... ... ##..# ...... .....
.... .... . ... ... ... ... ##.#. ...... .....
.... .... . ..# #.. ... ... ...#. ...... .....
.#.# #.#. . .#. .#. .#. ### ..#.. ...... .....
#.#. .#.# # #.. ..# ### ... .#... ###### .....
.#.# #.#. . .#. .#. .#. ### .#.## ...... .....
.... .... . ..# #.. ... ... #..## ...... #.#.#
"""),
]

# What is drawn for a character the font does not have: a small empty box.
MISSING = ["####", "#..#", "#..#", "#..#", "#..#", "#..#", "####", "....", "...."]


def read_sheets(sheets):
    """Turn the sheets into a dict: character -> list of HEIGHT rows of "#" and "."."""
    glyphs = {}
    for chars, block in sheets:
        rows = [row.split() for row in block.strip("\n").split("\n")]
        while len(rows) < HEIGHT:
            rows.append(["." * len(picture) for picture in rows[0]])
        for row in rows:
            if len(row) != len(chars):
                raise ValueError(f"the sheet {chars!r} has a row with {len(row)} characters instead of {len(chars)}")
        for index, char in enumerate(chars):
            glyphs[char] = [row[index] for row in rows]
    return glyphs


GLYPHS = read_sheets(SHEETS)


def glyph(char):
    """The picture of a character, or the empty box if the font does not have it."""
    return GLYPHS.get(char, MISSING)


class PixelFont:
    """The pixel font at a scale (1, 2, 3...), used like a pygame.font.Font.

    A class keeps together the scale and the texts already drawn, so that each
    text is drawn pixel by pixel only once.
    """

    def __init__(self, scale=1):
        self.scale = scale
        self.drawn = {}

    def get_linesize(self):
        """The distance between two lines of text, in pixels."""
        return (HEIGHT + LINE_GAP) * self.scale

    def size(self, text):
        """The (width, height) in pixels of a line of text."""
        width = 0
        for char in text:
            width += len(glyph(char)[0]) + SPACING
        if text:
            width -= SPACING
        return (width * self.scale, HEIGHT * self.scale)

    def render(self, text, antialias, color):
        """A transparent picture of the text in `color`. `antialias` is ignored: the pixels stay sharp."""
        key = (text, tuple(color))
        if key not in self.drawn:
            if len(self.drawn) > 500:
                self.drawn.clear()  # many different texts: start over rather than keep them all
            self.drawn[key] = self.draw(text, color)
        return self.drawn[key]

    def draw(self, text, color):
        width, height = self.size(text)
        picture = pygame.Surface((max(width, 1), height), pygame.SRCALPHA)
        scale = self.scale
        x = 0
        for char in text:
            rows = glyph(char)
            for y, row in enumerate(rows):
                for column, pixel in enumerate(row):
                    if pixel == "#":
                        picture.fill(color, (x + column * scale, y * scale, scale, scale))
            x += (len(rows[0]) + SPACING) * scale
        return picture
