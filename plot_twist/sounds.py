"""The sounds of Plot Twist, made in code like on an 8-bit console: no sound files.

The voices are those of the sound chip of an 8-bit console:

- "pulse12", "pulse25" and "square": a pulse wave that is up for 1/8, 1/4 or half of
  each period. The thinner the pulse, the thinner and more nasal the sound.
- "triangle": a triangle in 32 steps of 16 levels, round and deep, for the basses.
- "noise": the hiss of a 15-bit shift register fed back on itself (the noise channel),
  clocked `freq` times a second: low is a rumble, high a crackle. "metal" is the same
  register in its short mode, which repeats every 93 steps and rings like metal.

Each effect is a list of layers played together, each a voice with its own:

- envelope, ADSR: it rises in `attack` seconds, falls in `decay` to the `sustain` level,
  holds it until the layer's `length` is over, then dies in `release`. Like the chip's
  4-bit volume, the envelope moves in 16 steps;
- pitch: it starts at `freq` and glides to `to` (if given) in `sweep` seconds, or over the
  whole layer; `vibrato` (rate in Hz, depth in semitones) makes it waver;
- `tremolo` (rate, depth from 0 to 1): the volume beating, for a rumble that grinds;
- filters: a one-pole `lowpass` (which can glide to `lowpass_to`) muffles it, a
  `highpass` thins it: the noise of a footstep in a puddle is not the noise of glass.

The loops (LOOPS) are made the same way and fade into themselves at their seam, so they
can play forever: the sea on the deck, water dripping, the hum of a machine. They play on
channels of their own (loop, update_loops), whose volume moves a little every frame, so
that they fade in and out cleanly when the player changes room.

load() makes everything once the mixer is running, in its rate and channels. Without
audio (no sound card, or the mixer could not start) play() and loop() do nothing, and
the game runs the same. With a stereo mixer, play() can put a sound to the left or to
the right (`pan`), and quieter (`volume`): main.py does so with the crab, wherever it is.
"""

import array
import math

import pygame

MASTER = 0.3        # of the loudest possible sample: a few voices together never hurt
STEPS = 16          # the envelope moves in 16 levels, like the 4-bit volume of the chip
BLOCK = 32          # samples between two updates of the pitch and the envelope
RENDER_RATE = 22050  # the sounds are made at most at this rate, then held to the mixer's
NOISE_SEED = 1      # where the register of the noise starts: the same noise every time
LOOP_FADE = 0.25    # seconds at the end of a loop that fade into its start: no click at the seam
LOOP_FADE_FRAMES = 30  # frames a loop takes to fade in or out (half a second)
LOOP_CHANNELS = 6   # mixer channels kept for the loops: two for each loop slot, to cross-fade
LOOP_SLOTS = ("bed", "hum", "spare")  # what can loop at the same time

DUTIES = {"pulse12": 0.125, "pulse25": 0.25, "square": 0.5}
TRIANGLE = [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0,
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]  # 32 steps of 16 levels, like the chip


def noise_bit(register, short=False):
    """One step of the noise: a 15-bit shift register fed back on itself, like the noise channel
    of an 8-bit console. Returns the new register; its lowest bit is the next level (up or down).
    In the short mode the feedback comes from bit 6 instead of bit 1: a loop of 93 steps that rings."""
    feedback = (register ^ (register >> (6 if short else 1))) & 1
    return (register >> 1) | (feedback << 14)


def layer(wave, freq, length, start=0.0, volume=1.0, to=None, sweep=None, attack=0.002, decay=0.0,
          sustain=1.0, release=0.02, vibrato=None, tremolo=None, lowpass=None, lowpass_to=None, highpass=None):
    """One voice of an effect (see the top of this file). Times in seconds, frequencies in Hz."""
    return {"wave": wave, "freq": freq, "length": length, "start": start, "volume": volume, "to": to,
            "sweep": sweep, "attack": attack, "decay": decay, "sustain": sustain, "release": release,
            "vibrato": vibrato, "tremolo": tremolo, "lowpass": lowpass, "lowpass_to": lowpass_to,
            "highpass": highpass}


def hit(wave, freq, length, start=0.0, volume=1.0, **more):
    """A voice that strikes and dies away by itself: no sustain, its whole length a decay."""
    return layer(wave, freq, length, start, volume, attack=0.001, decay=length, sustain=0.0, release=0.005, **more)


def notes(wave, pitches, each, start=0.0, volume=1.0, **more):
    """A run of short struck notes, one after the other."""
    return [hit(wave, pitch, each * 1.6, start + index * each, volume, **more) for index, pitch in enumerate(pitches)]


def muffled(effect, cutoff):
    """The same effect heard through a wall: every voice muffled."""
    return [dict(voice, lowpass=min(voice["lowpass"] or cutoff, cutoff), lowpass_to=None) for voice in effect]


def scattered(wave, count, start, spread, low, high, length, volume, seed, **more):
    """`count` short struck voices at times and pitches that look random, but are always the same."""
    voices = []
    register = seed
    for _ in range(count):
        register = noise_bit(noise_bit(noise_bit(register)))
        when = start + spread * ((register % 97) / 97)
        register = noise_bit(noise_bit(register))
        pitch = low + (high - low) * ((register % 89) / 89)
        voices.append(hit(wave, pitch, length, when, volume, **more))
    return voices


EFFECTS = {
    # The puzzles
    "blip": [hit("pulse25", 1047, 0.07), hit("triangle", 523, 0.07, volume=0.6)],          # a tile lights up
    "ding": [hit("pulse25", 784, 0.08), hit("pulse25", 1175, 0.35, 0.07, vibrato=(7, 0.15)),
             hit("triangle", 392, 0.42, volume=0.7)],                                       # a phase is complete
    "fanfare": notes("square", [523, 659, 784], 0.08, volume=0.7)                           # the puzzle is solved
    + [layer("square", 1047, 0.3, 0.24, 0.7, decay=0.1, sustain=0.6, release=0.15, vibrato=(6, 0.2))]
    + notes("triangle", [262, 330, 392], 0.08) + [layer("triangle", 523, 0.3, 0.24, release=0.15)],
    "buzz": [layer("pulse12", 98, 0.12, release=0.01), layer("metal", 1800, 0.12, volume=0.35, lowpass=2500),
             layer("pulse12", 98, 0.3, 0.16, decay=0.3, sustain=0.2, release=0.05, to=82),
             layer("metal", 1800, 0.3, 0.16, volume=0.35, lowpass=2500, decay=0.3, sustain=0.1)],  # BZZZ: a mistake
    "clue": notes("pulse12", [988, 1319, 1976], 0.05) + notes("pulse12", [988, 1319, 1976], 0.05, 0.09, 0.3)
    + [hit("triangle", 1976, 0.25, 0.1, 0.5)],                                              # a new clue: a chime and its echo
    # The crab
    "crab_wake": [layer("triangle", 98, 0.6, to=55, decay=0.2, sustain=0.7, release=0.2),   # the statue cracks
                  layer("noise", 900, 0.5, volume=0.8, lowpass=400, decay=0.5, sustain=0.0, tremolo=(18, 0.6)),
                  hit("metal", 3000, 0.06, 0.0, 0.6, highpass=1500), hit("pulse12", 147, 0.35, 0.45, 0.6)],
    "knocked": [layer("pulse25", 392, 0.3, to=110, decay=0.3, sustain=0.0, release=0.02),  # the crab knocks a player down
                hit("noise", 1500, 0.08, 0.0, 0.8, lowpass=600), hit("triangle", 131, 0.3, 0.05, 0.9)],
    "revived": notes("pulse25", [523, 784], 0.06)                                           # back on their feet
    + [layer("pulse25", 1047, 0.15, 0.12, to=1319, decay=0.1, sustain=0.5, release=0.08)]
    + notes("triangle", [262, 392, 523], 0.06, volume=0.7),
    "knocked_out": [layer("pulse25", pitch, 0.18, 0.16 * index, decay=0.15, sustain=0.5, release=0.05,
                          vibrato=(5, 0.3) if index == 3 else None)
                    for index, pitch in enumerate((330, 262, 196, 131))]                     # a player is out of the game
    + [layer("triangle", 65, 0.6, 0.48, decay=0.5, sustain=0.3, release=0.2)],
    # Its claws on the floor: two dry clicks of chitin
    "claw_click": [hit("metal", 5000, 0.012, 0.0, 0.7, highpass=2500), hit("pulse12", 2200, 0.02, 0.0, 0.4, to=1400),
                   hit("metal", 4500, 0.012, 0.045, 0.6, highpass=2500), hit("pulse12", 1900, 0.02, 0.045, 0.35, to=1200)],
    # The crab charges: a hiss and a clatter
    "crab_charge": [layer("noise", 7000, 0.3, volume=0.6, highpass=2500, decay=0.3, sustain=0.0, tremolo=(30, 0.5)),
                    hit("pulse12", 330, 0.2, 0.0, 0.5, to=660)]
    + scattered("metal", 5, 0.02, 0.25, 4000, 6000, 0.012, 0.5, 31, highpass=2500),
    # The abilities
    "ability": [layer("pulse12", 659, 0.16, to=1976, decay=0.12, sustain=0.4, release=0.05),  # a quick rising run
                hit("triangle", 330, 0.18, volume=0.6, to=988)],
    "zap": [layer("pulse12", 1568, 0.3, to=2349, vibrato=(28, 2.0), decay=0.25, sustain=0.2, release=0.06),
            layer("metal", 6000, 0.25, volume=0.4, highpass=3000, decay=0.25, sustain=0.0),
            hit("triangle", 196, 0.15, volume=0.6)],                                         # the wizard's ray crackles
    "dash": [layer("noise", 9000, 0.22, volume=0.9, lowpass=600, lowpass_to=7000, attack=0.03, decay=0.15,
                   sustain=0.0, release=0.04),                                               # Flash's dash: a rush of air
             layer("pulse25", 300, 0.14, volume=0.35, to=1300, decay=0.12, sustain=0.0)],
    "drop": [hit("triangle", 330, 0.12, to=150), hit("noise", 3000, 0.03, 0.0, 0.5, lowpass=2000)],  # an item on the floor
    # The game
    "thunder": [hit("noise", 12000, 0.06, 0.0, 1.0, highpass=2000),                          # the bolt that opens the game
                layer("noise", 4000, 1.3, 0.03, 1.0, lowpass=3000, lowpass_to=250, attack=0.01, decay=1.2,
                      sustain=0.0, tremolo=(9, 0.4)),
                layer("triangle", 55, 1.2, 0.05, to=36, decay=1.1, sustain=0.0)],
    # The statue crumbles: a crack, a deep rumble that falls, grinding, and pebbles bouncing
    "crumble": [hit("metal", 2500, 0.05, 0.0, 0.8, highpass=1200),
                layer("triangle", 70, 0.9, to=40, decay=0.8, sustain=0.0, release=0.1),
                layer("noise", 1200, 0.9, volume=0.9, lowpass=500, lowpass_to=150, decay=0.85, sustain=0.0,
                      tremolo=(13, 0.5))]
    + scattered("noise", 9, 0.12, 0.7, 4000, 9000, 0.025, 0.45, 7, highpass=1800),
    # The crab turns to stone: a grinding that slows down
    "petrify": [layer("triangle", 70, 0.7, to=45, decay=0.6, sustain=0.2, release=0.1),
                layer("noise", 800, 0.7, volume=0.8, lowpass=300, tremolo=(16, 0.7), decay=0.7, sustain=0.1)],
    # The giant claw snaps shut: a dry crack, a ring of chitin, a thump
    "snap": [hit("noise", 15000, 0.015, 0.0, 1.0, highpass=3000), hit("pulse12", 1800, 0.04, 0.0, 0.6, to=600),
             hit("metal", 3500, 0.05, 0.01, 0.5, highpass=2000), hit("triangle", 90, 0.08, 0.0, 1.0, to=60)],
    # The screen breaks like glass: a sharp burst, a ringing hiss and shards tinkling as they fall
    "shatter": [hit("noise", 15000, 0.06, 0.0, 1.0, highpass=3500),
                layer("metal", 9000, 0.5, 0.01, 0.6, highpass=2500, decay=0.5, sustain=0.0),
                hit("triangle", 120, 0.06, 0.0, 0.7)]
    + scattered("pulse12", 12, 0.03, 0.6, 2600, 5200, 0.06, 0.45, 99),
    # Footsteps, on each floor, and in a puddle
    "step_wood": [hit("triangle", 180, 0.06, to=110), hit("noise", 2000, 0.025, 0.0, 0.5, lowpass=1500)],
    "step_stone": [hit("noise", 6000, 0.025, 0.0, 0.8, highpass=1500), hit("triangle", 260, 0.03, 0.0, 0.4, to=200)],
    "step_tiles": [hit("pulse12", 1400, 0.018, 0.0, 0.5), hit("noise", 9000, 0.015, 0.0, 0.6, highpass=3000)],
    "step_earth": [hit("noise", 1500, 0.05, 0.0, 0.8, lowpass=700), hit("triangle", 110, 0.03, 0.0, 0.5)],
    "step_puddle": [layer("noise", 9000, 0.13, volume=0.8, lowpass=3000, lowpass_to=700, decay=0.13, sustain=0.0),
                    hit("triangle", 600, 0.06, 0.02, 0.5, to=1300), hit("triangle", 800, 0.04, 0.08, 0.3, to=1500)],
    # A door that does not open: a dull thud on the wood, and the bars or the lock rattle
    "locked": [hit("triangle", 110, 0.14, to=65), hit("noise", 2000, 0.05, 0.0, 0.8, lowpass=900)]
    + [hit("metal", 4000, 0.02, when, 0.45, highpass=2000) for when in (0.07, 0.12, 0.16)],
}
EFFECTS["claw_click_far"] = muffled(EFFECTS["claw_click"], 900)  # in the next room, through the wall

LOOPS = {
    # The sea on the deck: deep surf that swells and falls twice in four seconds, and the hiss of foam
    "sea": (4.0, [layer("noise", 3000, 4.0, volume=0.9, lowpass=500, attack=0.0, release=0.0, tremolo=(0.5, 0.7)),
                  layer("noise", 12000, 4.0, volume=0.25, lowpass=4000, highpass=1500, attack=0.0, release=0.0,
                        tremolo=(0.5, 0.9))]),
    # Water dripping in the dark: drops and their echo, now and then, on a breath of cave air
    "drips": (3.2, [layer("noise", 2000, 3.2, volume=0.12, lowpass=300, attack=0.0, release=0.0)]
              + [hit("triangle", pitch, 0.05, when, 0.6, to=pitch * 1.7) for when, pitch in
                 ((0.35, 900), (1.3, 1100), (1.9, 820), (2.8, 1000))]
              + [hit("triangle", pitch, 0.05, when + 0.09, 0.2, to=pitch * 1.7) for when, pitch in
                 ((0.35, 900), (1.3, 1100), (1.9, 820), (2.8, 1000))]),
    # A machine hums: the mains, its overtones, and a faint crackle
    "hum": (1.0, [layer("triangle", 60, 1.0, attack=0.0, release=0.0, vibrato=(3, 0.05)),
                  layer("pulse12", 120, 1.0, volume=0.25, attack=0.0, release=0.0, lowpass=900),
                  layer("pulse25", 180, 1.0, volume=0.1, attack=0.0, release=0.0, lowpass=900, tremolo=(2, 0.5)),
                  layer("metal", 8000, 1.0, volume=0.06, attack=0.0, release=0.0, highpass=4000, tremolo=(7, 0.9))]),
}
LOOPS["sea_far"] = (LOOPS["sea"][0], muffled(LOOPS["sea"][1], 250))  # the sea from inside the ship

_loaded = {}    # effect or loop name -> pygame Sound, once load() has run with audio
_loops = {}     # slot -> list of the loops playing in it (see loop)
_free = []      # the reserved channels no loop is using


def envelope(voice, time):
    """The level of a voice `time` seconds after it starts (ADSR), in STEPS steps, from 0 to 1."""
    length = voice["length"]
    attack, decay, sustain, release = voice["attack"], voice["decay"], voice["sustain"], voice["release"]
    if time < attack:
        level = time / attack
    elif time < attack + decay:
        level = 1 - (1 - sustain) * (time - attack) / decay
    else:
        level = sustain
    if time >= length:
        held = envelope(voice, length - 1e-9) if length > 0 else 0.0
        level = held * (1 - (time - length) / release) if release > 0 and time < length + release else 0.0
    return math.ceil(max(level, 0.0) * STEPS - 1e-9) / STEPS


def pitch(voice, time):
    """The frequency of a voice at `time`: its glide toward `to`, and its vibrato."""
    frequency = voice["freq"]
    if voice["to"]:
        span = voice["sweep"] or voice["length"]
        share = min(time / span, 1.0) if span > 0 else 1.0
        frequency *= (voice["to"] / voice["freq"]) ** share  # a glide by equal steps of pitch
    if voice["vibrato"]:
        rate, depth = voice["vibrato"]
        frequency *= 2 ** (depth * math.sin(2 * math.pi * rate * time) / 12)
    return frequency


def one_pole(cutoff, rate):
    """How much a one-pole lowpass filter moves toward its input at each sample."""
    return 1 - math.exp(-2 * math.pi * min(cutoff, rate * 0.45) / rate)


def voice_samples(voice, rate):
    """One voice, alone, as floats from -1 to 1, from its start to the end of its release."""
    count = int((voice["length"] + voice["release"]) * rate)
    out = [0.0] * count
    wave = voice["wave"]
    noisy = wave in ("noise", "metal")
    short = wave == "metal"
    duty = DUTIES.get(wave, 0.5)
    phase = 0.0
    register = NOISE_SEED
    level_now = 1.0 if register & 1 else -1.0
    low = voice["lowpass"]
    high = voice["highpass"]
    low_y = high_y = high_x = 0.0
    high_a = math.exp(-2 * math.pi * high / rate) if high else 0.0
    tremolo = voice["tremolo"]
    volume = voice["volume"]
    for block in range(0, count, BLOCK):
        time = block / rate
        gain = envelope(voice, time) * volume
        if tremolo:
            gain *= 1 - tremolo[1] * (0.5 + 0.5 * math.cos(2 * math.pi * tremolo[0] * time))
        step = pitch(voice, time) / rate
        low_a = None
        if low:
            cutoff = low
            if voice["lowpass_to"]:
                cutoff = low * (voice["lowpass_to"] / low) ** min(time / voice["length"], 1.0)
            low_a = one_pole(cutoff, rate)
        for index in range(block, min(block + BLOCK, count)):
            phase += step
            if noisy:
                while phase >= 1.0:
                    phase -= 1.0
                    register = noise_bit(register, short)
                    level_now = 1.0 if register & 1 else -1.0
                value = level_now
            else:
                phase -= int(phase)
                if wave == "triangle":
                    value = TRIANGLE[int(phase * 32)] / 7.5 - 1.0
                else:
                    value = 1.0 if phase < duty else -1.0
            if low_a is not None:
                low_y += low_a * (value - low_y)
                value = low_y
            if high:
                high_y = high_a * (high_y + value - high_x)
                high_x = value
                value = high_y
            out[index] = value * gain
    return out


def render(voices, rate, length=None):
    """All the voices of an effect mixed, as floats; `length` in seconds, else until the last one ends."""
    if length is None:
        length = max(voice["start"] + voice["length"] + voice["release"] for voice in voices)
    mix = [0.0] * int(length * rate)
    for voice in voices:
        start = int(voice["start"] * rate)
        for index, value in enumerate(voice_samples(voice, rate), start):
            if index < len(mix):
                mix[index] += value
    return mix


def seamless(mix, rate):
    """A loop that fades into its own start: its last LOOP_FADE seconds mixed into its first, and cut."""
    overlap = int(LOOP_FADE * rate)
    body = mix[:len(mix) - overlap]
    tail = mix[len(mix) - overlap:]
    for index, value in enumerate(tail):
        share = index / overlap
        body[index] = body[index] * share + value * (1 - share)
    return body


def pcm(mix, channels=1, repeat=1):
    """Floats as signed 16-bit samples: loudness MASTER, gently saturated rather than clipped,
    each sample held `repeat` times (to fill a faster mixer) and repeated on every channel."""
    data = array.array("h")
    width = channels * repeat
    for value in mix:
        value = value / (1 + abs(value) * 0.25)  # many voices together bend, they do not crack
        data.extend([int(max(-1.0, min(1.0, value * MASTER)) * 32767)] * width)
    return data


def loop_samples(length, voices, rate):
    """A loop as floats: the voices that last the whole loop go on past its end for LOOP_FADE seconds
    (they are periodic: the same as its start), and that end fades into the start."""
    longer = [dict(voice, length=voice["length"] + LOOP_FADE) if voice["length"] >= length else voice
              for voice in voices]
    return seamless(render(longer, rate, length + LOOP_FADE), rate)


def effect_length(voices):
    """How long an effect lasts, in seconds."""
    return max(voice["start"] + voice["length"] + voice["release"] for voice in voices)


def load():
    """Make the sounds for the running mixer. Without audio, or with samples that are not 16-bit, there are none."""
    _loaded.clear()
    _loops.clear()
    _free.clear()
    settings = pygame.mixer.get_init()
    if settings is None:
        return
    rate, size, channels = settings
    if size != -16:
        return
    repeat = max(1, round(rate / RENDER_RATE))
    made = rate / repeat
    for name, voices in EFFECTS.items():
        _loaded[name] = pygame.mixer.Sound(buffer=pcm(render(voices, made), channels, repeat).tobytes())
    for name, (length, voices) in LOOPS.items():
        _loaded[name] = pygame.mixer.Sound(buffer=pcm(loop_samples(length, voices, made), channels, repeat).tobytes())
    if pygame.mixer.get_num_channels() < LOOP_CHANNELS + 8:
        pygame.mixer.set_num_channels(LOOP_CHANNELS + 8)
    pygame.mixer.set_reserved(LOOP_CHANNELS)  # play() never takes these: they are the loops'
    _free.extend(pygame.mixer.Channel(index) for index in range(LOOP_CHANNELS))


def sides(volume, pan):
    """The volume of the left and the right speaker for a sound `pan` from the middle (-1 all
    left, 1 all right): as loud in the middle as at either side (equal power)."""
    angle = (max(-1.0, min(1.0, pan)) + 1) * math.pi / 4
    volume = max(0.0, min(1.0, volume))
    return (min(1.0, math.sqrt(2) * math.cos(angle)) * volume, min(1.0, math.sqrt(2) * math.sin(angle)) * volume)


def play(name, volume=1.0, pan=0.0):
    """Play an effect, `volume` from 0 to 1 and `pan` from -1 (left) to 1 (right). An unknown name,
    None or a game without audio make no sound."""
    sound = _loaded.get(name)
    if sound is None or volume <= 0:
        return
    channel = pygame.mixer.find_channel(True)  # the oldest one if all are busy: never one of the loops
    if channel is None:
        return
    channel.play(sound)
    channel.set_volume(*sides(volume, pan))


def loop(slot, name, volume=1.0, pan=0.0):
    """What a loop slot should play now (or None: nothing), how loud and where. A new loop fades
    in on a channel of its own while the old one fades out; the same loop only changes volume and
    pan, smoothly. The fades happen in update_loops, once a frame."""
    playing = _loops.setdefault(slot, [])
    for sound in playing:
        sound["target"] = volume if sound["name"] == name else 0.0
        if sound["name"] == name:
            sound["pan"] = pan
    if name is None or any(sound["name"] == name for sound in playing):
        return
    entry = {"name": name, "gain": 0.0, "target": volume, "pan": pan, "channel": None}
    if name in _loaded and _free:
        entry["channel"] = _free.pop()
        entry["channel"].play(_loaded[name], loops=-1)
        entry["channel"].set_volume(0.0, 0.0)
    playing.append(entry)


def update_loops(frames=LOOP_FADE_FRAMES):
    """Once a frame: each loop moves its volume a step toward what loop() asked, over `frames`
    frames; a loop faded out stops and gives its channel back."""
    step = 1.0 / frames
    for slot, playing in _loops.items():
        for sound in list(playing):
            if sound["gain"] < sound["target"]:
                sound["gain"] = min(sound["target"], sound["gain"] + step)
            else:
                sound["gain"] = max(sound["target"], sound["gain"] - step)
            if sound["channel"] is not None:
                sound["channel"].set_volume(*sides(sound["gain"], sound["pan"]))
            if sound["gain"] <= 0 and sound["target"] <= 0:
                if sound["channel"] is not None:
                    sound["channel"].stop()
                    _free.append(sound["channel"])
                playing.remove(sound)


def loop_volume(slot, name):
    """How loud a loop plays in its slot right now (0 if it does not)."""
    return sum(sound["gain"] for sound in _loops.get(slot, []) if sound["name"] == name)
