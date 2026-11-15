"""The sound effects of Plot Twist, made from square waves and noise like on an 8-bit console.

There are no sound files: each effect is a list of notes, (frequency in Hz,
length in seconds), where a frequency of 0 is a pause and a negative frequency
is noise: the hiss of the console's noise channel, as rough as the number is
low (-60 rumbles, -8000 crackles). load() turns them into
pygame sounds once the mixer is running, in whatever rate and channels it opened
with. Without audio (no sound card, or the mixer could not start), play() does
nothing, and the game runs the same.
"""

import array

import pygame

VOLUME = 0.2  # of the loudest square wave: the effects are short and should not hurt
FADE = 0.005  # seconds at the end of each note that fade out, so notes do not click

EFFECTS = {
    "blip": [(1047, 0.04)],                                            # a tile lights up
    "ding": [(784, 0.07), (1175, 0.16)],                               # a phase is complete
    "fanfare": [(523, 0.08), (659, 0.08), (784, 0.08), (1047, 0.3)],   # the puzzle is solved
    "buzz": [(98, 0.12), (0, 0.04), (98, 0.3)],                        # BZZZ: a mistake, the lights go out
    "clue": [(988, 0.05), (1319, 0.05), (0, 0.02), (1976, 0.22)],      # a new clue: a light, rising chime
    "crab_wake": [(73, 0.1), (82, 0.1), (98, 0.1), (0, 0.03), (147, 0.35)],  # the statue cracks: the crab is awake
    "knocked": [(392, 0.06), (262, 0.06), (131, 0.25)],                # the crab knocks a player down
    "revived": [(523, 0.06), (784, 0.06), (1047, 0.15)],               # back on their feet
    "ability": [(659, 0.04), (988, 0.04), (1319, 0.04), (1976, 0.12)],  # a character's ability: a quick rising run
    "drop": [(330, 0.04), (196, 0.07)],                                # an item dropped on the floor
    "thunder": [(110, 0.03), (55, 0.1), (49, 0.12), (0, 0.04), (41, 0.18), (37, 0.3)],  # the bolt that opens the game
    "knocked_out": [(330, 0.15), (262, 0.15), (196, 0.15), (131, 0.4)],  # a player is out of the game
    # The crab statue shakes and crumbles: low, jagged noise over a deep square wave.
    "crumble": [(-90, 0.08), (55, 0.05), (-60, 0.12), (41, 0.06), (-45, 0.2), (-30, 0.25)],
    # The giant claw snaps shut: a dry crack.
    "snap": [(-4000, 0.015), (1800, 0.02), (-2500, 0.025), (90, 0.05)],
    # The screen breaks like glass: a high crackle with a few bright chips.
    "shatter": [(-9000, 0.05), (3520, 0.02), (-7000, 0.06), (4186, 0.02), (-8000, 0.08), (2637, 0.03),
                (-6000, 0.12), (-5000, 0.15)],
}

_loaded = {}  # effect name -> pygame Sound, once load() has run with audio


NOISE_SEED = 1  # where the register of the noise starts: the same noise every time


def noise_bit(register):
    """One step of the noise: a 15-bit shift register fed back on itself, like the noise channel
    of an 8-bit console. Returns the new register; its lowest bit is the next level (up or down)."""
    feedback = (register ^ (register >> 1)) & 1
    return (register >> 1) | (feedback << 14)


def samples(notes, rate, channels=1):
    """The notes as signed 16-bit samples, the same value repeated on every channel."""
    peak = int(32767 * VOLUME)
    fade = max(1, int(rate * FADE))
    data = array.array("h")
    register = NOISE_SEED
    for frequency, length in notes:
        count = int(rate * length)
        step = -1
        for index in range(count):
            value = 0
            if frequency > 0:
                # Half of each period up, half down: a square wave.
                up = (2 * index * frequency // rate) % 2 == 0
                value = peak if up else -peak
            elif frequency < 0:
                # Noise: a new random level -frequency times a second, held in between.
                now = index * -frequency // rate
                if now != step:
                    step = now
                    register = noise_bit(register)
                value = peak if register & 1 else -peak
            if frequency != 0:
                left = count - index
                if left < fade:
                    value = value * left // fade
            data.extend([value] * channels)
    return data


def load():
    """Make the sounds for the running mixer. Without audio, or with samples that are not 16-bit, there are none."""
    _loaded.clear()
    settings = pygame.mixer.get_init()
    if settings is None:
        return
    rate, size, channels = settings
    if size != -16:
        return
    for name, notes in EFFECTS.items():
        _loaded[name] = pygame.mixer.Sound(buffer=samples(notes, rate, channels).tobytes())


def play(name):
    """Play an effect. An unknown name, None or a game without audio make no sound."""
    sound = _loaded.get(name)
    if sound is not None:
        sound.play()
