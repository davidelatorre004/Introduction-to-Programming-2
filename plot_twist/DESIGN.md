# Plot Twist — design document

> **Note:** this is the original design document, written before the code and kept up to date through milestone M6. The game has grown a lot since then (eight generators, more rooms, the infirmary and the remedy, the anvil in the empty room, two players on two computers, the crab, four characters with abilities, a third ending...). Where this document and the game differ, the game is right: what changed in each version is in [CHANGELOG.md](CHANGELOG.md).

A 2D top-down game in 8-bit style (like *The Binding of Isaac*, without fighting), written in Python with pygame, for the [Plot Twist](https://nova-sbe-introduction-to-programming.github.io/intro-to-programming-2026/weeks/week-05/01-plot-twist-brd.html) brief of week 5.

This document collects the decisions taken before writing code:
- the data of the story;
- the rules of the engine;
- saving;
- the interface;
- how each requirement of the brief is checked;
- the work plan.

## 1. The game

A ship is adrift on the ocean. The protagonist wakes up on the deck, with a magic wand lying on the floor nearby. In the two locked rooms of the ship a crab and an angel are waiting: who you give the wand to decides the ending.

| Scene | id | What is there |
|---|---|---|
| Deck (outdoors, start) | `deck` | The wand on the floor and the doors to all the other rooms |
| Captain's cabin | `cabin` | Four wired generators: turning them all on at the same time dissolves the barrier that guards the first half of the key |
| Hold | `hold` | Barred by a gate until you have the first half. Inside, five tiles to step on in three sequences: they dissolve the barrier around the anvil, with the second half on it. On the anvil the two halves are fused into the fused key. And a barrel that, with the wand, reveals that the crab tells the truth |
| Crab's room | `crab_room` | The crab, 2×2 tiles big: giving it the wand leads to the ending *Everyone saved* |
| Angel's room | `angel_room` | The angel, 2 tiles tall: giving it the wand leads to the ending *The ship explodes* |

Rules of the story:
- **Doors:** from the deck you walk freely into the cabin. The door of the hold has a gate, which opens by itself as soon as you have the first half of the key. The doors of the crab and of the angel need the fused key: the two halves, fused on the anvil of the hold. The fused key opens both.
- **Choice:** who to give the wand to. Both final doors can be opened, so you can meet both the crab and the angel before deciding.
- **Items:** they are never duplicated, and they are not used up by using them. The only transformation is at the anvil: the two halves of the key become the fused key.
- **Shortest path:** wand → generators in the cabin → first half of the key → tiles in the hold → second half → fusing at the anvil → a final door → giving the wand. The barrel of the hold is optional: it gives the clue for choosing the right door.
- **Puzzles:** two, both real (M5), described in §4: the wired switches in the cabin and the tiles in the hold. The barrel stays a simple reaction to the wand.

Controls:
- arrows or WASD to move;
- **E** to interact with what is near;
- **I** for the inventory;
- **Esc** for the menu.

What the brief asks for the first version, and where it is in the game:

| The brief asks | In the game |
|---|---|
| At least 5 scenes | 5 rooms |
| At least 2 collectible items | The wand and the two halves of the key, which become the fused key at the anvil |
| 2 reachable endings | *Everyone saved* and *The ship explodes* |
| An ending that depends on a choice or on an earlier item | Both depend on who gets the wand, and both need the fused key to get there |
| About 10 minutes of play | Two real puzzles. How long it really takes must be measured with people who do not know the solutions |
| Simple text and controls | Text boxes and 4 keys |
| No paid services or external integrations | pygame and a local JSON file |

## 2. Principles

1. **The state holds only what is saved:** room, inventory, flags, ending. Everything else is derived from these four fields: what lies on the floor, which doors are open or sealed, which puzzles are solved. So items cannot be duplicated, and saving writes the state as it is.
2. **The engine (`engine.py`) knows nothing about pixels, keys or files.** It receives actions such as "pick up X", "use X on Y", "go through door Z". `main.py` decides what is near the player; the engine decides whether the action is allowed and what changes. Every rule can be tested without opening a window.
3. **Actions do not change the state they receive:** they return a new state and an outcome. A refused action returns the state from before, untouched.
4. **Every outcome has a text:** the visible result if the action is accepted, the explanation if it is refused.
5. **The game is saved after every accepted action,** and only then.

## 3. Files

| File | Role | Imports |
|---|---|---|
| `story.py` | The data of the story: constants only | Nothing |
| `engine.py` | State and rules | `story` (and `copy`) |
| `save.py` | Writes and reads the JSON save file | `json`, `os` |
| `main.py` | pygame: window, input, drawing, scenes, movement triggers | `engine`, `save`, `sounds`, `sprites`, `story`, `pixel_font` |
| `sounds.py` | The sound effects, made of square waves generated in the code: no audio files | `pygame`, `array` |
| `test_engine.py` | Scenarios A1–A6 and the requirements of the brief | `engine`, `story`; from M2 also `save` |
| `test_save.py` | The behaviour of `save.py` | `save`, `engine` |
| `conftest.py` | Shared test setup: moves the save file to a temporary folder | `save` |
| `test_main.py` | Layout, walls and doors, movement, menus and saving as seen from the interface, without opening windows | `main`, `engine`, `save`, `story`, `pygame` |
| `sprites.py` | The sprites and tiles in pixel art, written as text (one letter per pixel) | `pygame` |
| `pixel_font.py` | The pixel font, written as text; it is used like a `pygame.font.Font` | `pygame` |
| `test_graphics.py` | Sprites, font and animations (M6) | `main`, `sprites`, `pixel_font`, `engine`, `story`, `pygame` |
| `test_sounds.py` | The waves of the effects, and the game staying silent without audio (M5) | `sounds`, `pygame` |

The `plot_twist/` folder sits next to `splitit/` and is organised the same way:
- a `pyproject.toml` for uv, with Python 3.12, pygame and pytest;
- a `.gitignore` that leaves out the save file.

## 4. `story.py`: the data

Conventions:
- **Constants only:** no functions, no imports.
- **Ids:** everything, rooms included, has a string id that is unique in the whole game, in English (such as `crab_door`). The texts on screen are in English too.
- **Flat dictionaries:** items, doors and characters are in `id → data` dictionaries with a `room` field, instead of being listed inside the rooms. So each piece of information is in one place only.
- **Texts:** they are all here, never in the engine. You can rewrite the dialogues without touching the rules or the tests.

| Constant | Content | Fields |
|---|---|---|
| `START_ROOM` | `"deck"` | — |
| `FLAGS` | Name of the flag → starting value | `generator_a: False`, `generator_b: True`, `generator_c: True`, `generator_d: False`, `cabin_solved: False`, `hold_phase: 1`, `hold_step: 0`, `hold_solved: False`, `crab_truthful: False`, `crab_door: None`, `angel_door: None` |
| `ROOMS` | The 5 rooms | `name`, `description`, `outdoor` (the deck is outdoors: needed for drawing) |
| `ITEMS` | `wand`, `key`, `second_key`, `fused_key` | `part_of` (the item it is fused into, or `None`), `name`, `description`, `room`, `appears_if` (the flag that makes it appear, or `None`), `free_if` (the flag that lets it be picked up, or `None`), `pickup_text` |
| `DOORS` | 8 doors, one for each direction | `room`, `to`, `requires` (a list of items, empty if the door has no lock), `choice_flag` (a flag or `None`), `opens_with` (an item or `None`), `locked_text`, `sealed_text`, `open_text` (only for doors with a lock), `barred_text` (only for barred doors) |
| `OBJECTS` | 4 generators, 5 tiles, 2 barriers, an altar, an anvil, a barrel and 2 characters | `kind`, `name`, `room`, `look_text`, `done_text` (required for puzzles), `reactions` (item used → reaction). The generators also have `flag`, `toggles`, `toggle_text` and `label`; the tiles `label`; the barriers `open_if`; the anvil `fuse_text`. The crab and the angel have `size` |
| `CIRCUITS` | `cabin_circuit` | `room`, `switches` (the generators), `solved_flag`, `solved_text` |
| `FLOOR_PUZZLES` | `hold_tiles` | `room`, `zone`, `phases` (each with `name` and `steps`), `phase_flag`, `step_flag`, `solved_flag` and the texts `lit_text`, `phase_text`, `wrong_text`, `left_text`, `solved_text` |
| `ENDINGS` | `saved`, `explosion` | `title`, `text` (lines of the ending screen), `good` |
| `CLUES` | Flag → text shown in the inventory | `crab_truthful` → "The crab always tells the truth." |
| `MESSAGES` | General texts | Opening scene, the question that confirms starting over, the explanations of refusals ("nothing happens", "it is not here", "the barrier keeps you from taking it", "this key is missing its other half", …), the text of an open door, the labels of the E actions |

The `kind`s of `OBJECTS`:
- `puzzle` and `character`: they react when you use an item on them (see "Reactions").
- `switch`: a generator of a circuit. Activating it flips the flags listed in `toggles`, its own included.
- `tile`: a numbered tile of a floor puzzle. It is not solid: you walk on it, and walking on it is how you play.
- `barrier`: it blocks the way while the flag `open_if` is false, then disappears.
- `altar`: it can only be looked at, and an item lies on it: the altar of the cabin.
- `anvil`: an item lies on the anvil too, and on top of that the parts of an item are fused on it (see "Fusing").

### Doors

| id | Connection | Opening |
|---|---|---|
| `deck_to_cabin` | Deck → cabin | Free |
| `deck_to_hold` | Deck → hold | Barred by a gate until the player has the first half of the key (`opens_with: key`). Then it is free: nothing needs to be used |
| `deck_to_crab`, `deck_to_angel` | Deck → final rooms | `requires: [fused_key]`, with a flag each (`crab_door`, `angel_door`): opening one does not seal the other. The separate halves do not turn |
| `cabin_to_deck`, `hold_to_deck`, `crab_to_deck`, `angel_to_deck` | Back to the deck | Free |

Each connection has two doors and each door is in one room only, so the engine never has to work out which side it is being crossed from.

### Collectible items

- `wand`: on the deck, always on the floor (`appears_if` and `free_if` are `None`).
- `key`, the "Central key": the first half of the key. In the cabin, on the altar. It can be seen from the start, but with `free_if: cabin_solved` it cannot be picked up while the barrier is there.
- `second_key`, the "Second key": the second half. In the hold, on the anvil, with `free_if: hold_solved`.
- `fused_key`, the "Fused key": it is nowhere (`room` and `pos` are `None`). It is made at the anvil from the two halves, which have `part_of: fused_key`.

### Fusing

One of the two halves is used on the anvil (E next to the anvil, then "Use: …").
- With both halves in the inventory, the halves disappear and the Fused key takes the place of the first one. The anvil's `fuse_text` appears.
- With one half only, it refuses with `missing_item`: the other one is missing.
- The fused halves never come back: they reappear neither on the altar nor on the anvil, and the door of the hold stays open, because the fused key counts as the first half.
- A half used on a final door does not turn: it refuses with `not_fused`, and the text says to fuse it at the anvil.
- The fused key is not used up: after opening one door, it opens the other one too.

### Reactions

A reaction sets a flag (`set_flag` with its name and `value` with its value) or ends the game (`ending` with the id of the ending). In both cases it has a `text`.

| Target | Item used | Effect |
|---|---|---|
| `hold_puzzle` | `wand` | `crab_truthful = True`: the clue appears in the inventory |
| `crab` | `wand` | Ending `saved` |
| `angel` | `wand` | Ending `explosion` |

The barrel of the hold is only a reaction to the wand. The two real puzzles do not use reactions instead: each has its own mechanism, the circuits and the floor puzzles. In every case the rest of the game only reads the final flag (`crab_truthful`, `cabin_solved`, `hold_solved`).

### The generator puzzle (M5)

In the cabin there are four generators at the corners of a square:
- A at the top left;
- B at the top right;
- C at the bottom left;
- D at the bottom right.

Each generator is a boolean flag: true is on, false is off. It is wired to the two generators next to it along the sides of the square, never to the one on the diagonal. Activating it flips it and its two neighbours:

| Activate | Flipped |
|---|---|
| A | A, B, C |
| B | B, A, D |
| C | C, A, D |
| D | D, B, C |

Rules:
- **Start:** A off, B on, C on, D off. The generators go back to this **every time the player walks into the cabin**, until the circuit is complete.
- **Win:** after each activation the circuit is checked. If the four generators are on at the same time:
  - `cabin_solved` becomes true;
  - the barrier disappears, and its collision with it;
  - "The electric flow is complete! The barrier has dissolved!" appears;
  - the Central key on the altar can be picked up.
- **After the win:** the generators stay on and cannot be activated any more.

Solution: the order does not matter, and activating the same generator twice undoes it. So solving means choosing which generators to activate once. From the starting configuration, A and D are enough. Each of the 16 possible configurations has a solution; the longest, from all off, needs all four to be activated.

### The tile puzzle (M5)

In the hold there are five tiles numbered from 1 to 5, in a row, one tile apart. Around them there is a zone of metal grating, one tile wider on each side: the lanes above and below the tiles let the player skip some of them, for example to go from 5 to 3 without stepping on 4. It is played by walking: the E key is not needed.

The puzzle is a state machine. Its state is two flags: the phase being played (`hold_phase`, from 1 to 3) and how many tiles of its sequence are already lit (`hold_step`).

| Phase | Name | Sequence |
|---|---|---|
| 1 | The Wave | 1 → 2 → 3 → 4 → 5 |
| 2 | The Return | 5 → 3 → 1 |
| 3 | The Short Circuit | 1 → 5 → 2 → 4 → 3 |

Rules:
- **Right step:** stepping on the next tile of the sequence lights it.
- **End of a phase:** the next phase starts from the tile the player is standing on, which stays lit. Phase 2 starts with tile 5 already lit, Phase 3 with tile 1, as the brief asks ("starting from tile 5").
- **Mistake:** stepping on any other tile, even one lit earlier in the same phase, or leaving the zone. The lights go out and **the current phase** starts over, from its first tile; the phases already passed stay passed. Leaving the hold counts as leaving the zone.
- **Not mistakes:** going back onto the tile lit last, and leaving the zone when no tile is lit.
- **Win:** the last tile of Phase 3 sets `hold_solved`. Then:
  - the barrier around the anvil disappears, and its collision with it;
  - "The hold's system unlocks! The barrier has dissolved!" appears;
  - the Second key on the anvil can be picked up.

  From then on the tiles all stay lit and do not react any more.

Clues: the names of the three phases are engraved on the anvil (they are read by examining the barrier), and each change of phase announces the name of the next one.

The shortest solution is 1 2 3 4 5, 3 1, 5 2 4 3: eleven steps. A test tries every tile at every moment and checks that there is no other solution of the same length.

### Derived rules

The engine works them out; they are never saved.

- **Item on the floor:** an item is on the floor if all three conditions are true:
  - it is in the current room;
  - `appears_if` is `None` or true;
  - it is not in the inventory.

  This is why an item with `appears_if` appears when its flag becomes true, and why every item disappears as soon as it is picked up.
- **Guarded item:** an item on the floor can be picked up only if `free_if` is `None` or true. Otherwise it can be seen and examined, but `pick_up` refuses it. This is the case of the key behind the barrier.
- **Barrier:** it is there while its `open_if` is false. Then it disappears from `things_here`, and so from the drawing and from the collisions.
- **State of a generator:** it is its flag. A circuit is complete when all its generators are on.
- **Barred door:** with `opens_with`, it is barred until the player has that item; then it counts like the others.
- **Lit tile:** it is among the first `hold_step` tiles of the sequence of the current phase. If the puzzle is solved, they are all lit.
- **State of a door:** without `requires` it is always open. With a `choice_flag`:
  - it is open if the flag holds the id of this door;
  - it is **sealed for good** if the flag holds the id of another one (this only happens to doors that share their flag: none do today);
  - it is locked if the flag is `None`.

  A "normal" locked door is a door whose `choice_flag` is not shared with any other.
- **Puzzle solved:** its flag already has the value of the reaction, so doing it again does nothing.
- **Game over:** `ending` is not `None`.

### Layout

It is added in M3, and the engine never reads it.
- `entry` for each room: where the player appears when a game is resumed.
- `side` for each door: N, S, E or W, in the middle of the wall.
- `pos` for items and characters.
- `size` for what covers more than one tile: each barrier covers 3×2, around the altar or the anvil; the crab 2×2; the angel 1×2. The sprites have the same size as the area.
- `zone` for each floor puzzle: the rectangle around the tiles. Leaving it starts the phase over.

An item can be on the tile of an altar: that is how the key lies on the altar.

Coordinates are in tiles, not in pixels. So moving something in the room does not break the tests, and changing the resolution does not touch the story.

## 5. The state

| Field | Type | At the start of a game |
|---|---|---|
| `room` | id of the current room | `"deck"` |
| `inventory` | List of ids in the order they were picked up, without duplicates | Empty |
| `flags` | A copy of `FLAGS` | All at their starting value |
| `ending` | id of the ending reached, or `None` | `None` |

It is exactly what the brief asks to remember: current scene, items collected, relevant decisions, ending reached.
- **Types:** only native JSON types, no sets or tuples.
- **Player position:** it is not saved. When a game is resumed, the player starts again from the entrance of the room.

## 6. `engine.py`: state and rules

### Outcome and errors

Every function that acts returns `(state, outcome)`. The outcome has three fields:
- `ok`: the action was accepted. `main.py` saves if and only if it is true.
- `event`: a code for the tests and for the interface.
- `text`: never empty. It is the visible result (PT02) or the explanation of the refusal (PT04).

There are two kinds of error:
- **The player cannot do it:** an outcome with `ok` false is returned.
- **The code passed an id that does not exist:** an exception is raised, because it is a bug.

### Session

- **`new_game()`:** creates the starting state, with `START_ROOM`, an empty inventory, a **copy** of `FLAGS` and no ending. It never returns the dictionaries of `story.py`: the first change would change them for all the following games and for all the tests.
- **`start_new_game(existing, confirmed)`:** the only way to start a game. `existing` is the current or saved progress.
  - If `existing` is not `None` and `confirmed` is false, it refuses with `needs_confirmation`. The text is the question to show, and `existing` stays untouched.
  - Otherwise it returns `new_game()`, with the opening scene as its text.
  - The main menu, "Restart" in the Esc menu and the ending screen all go through here, so the confirmation cannot be forgotten.
- **`menu_options(existing)`:** "New game" is always there; "Resume" only if `existing` is not `None`.
- **`restore_state(data)`:** checks a dictionary read from the save file and returns a clean state, or `None`. It checks that:
  - the 4 keys are there;
  - the room exists;
  - the items are known and without duplicates;
  - the flags are known and have valid values;
  - the ending exists;
  - every unsolved floor puzzle has fewer lit tiles than the sequence of its phase. A save with, for example, Phase 2 and four lit tiles is impossible, and is refused.

  It fills in missing flags with their starting value. So a save made before the generator or tile flags existed can still be resumed.

### Reading

These functions change nothing.
- **`is_over(state)`:** says whether an ending has been reached.
- **`has_item(state, item)`:** says whether an item is in the inventory.
- **`door_status(state, door)`:** returns `"open"`, `"barred"`, `"locked"` or `"sealed"`, following the derived rules.
- **`things_here(state)`:** returns everything that is in the room now, with id, kind and status:
  - visible items on the floor (`on_floor`, or `guarded` if they cannot be picked up yet);
  - doors;
  - puzzles (solved or not);
  - generators (`on` or `off`);
  - tiles (`lit` or `dark`);
  - the barriers, while they are there (`up`);
  - characters, altar and anvil.

  This is the only place where `main.py` learns what to draw and what is solid.
- **`actions_for(state, target)`:** returns the actions available by pressing E next to the target, each with a label:
  - "Pick up" for an item on the floor, or only "Examine" if it is guarded;
  - "Activate" for a generator, as the only action;
  - "Enter" for an open door;
  - "Examine" or "Talk";
  - "Use X" or "Give X" for **every** item in the inventory, not only the right one, otherwise the menu would give the solution away.

  It marks as `irreversible` the actions that trigger an ending, or that open a door which seals another one (none today: the final doors have a flag each). So only giving the wand asks for confirmation. After the ending it returns an empty list, and so it does for a floor puzzle: it is not a target of E.
- **`clues(state)`:** returns the texts of `CLUES` whose flags are true, to show in the inventory.

### Actions

Every action first checks that the game is not over.
- **`pick_up(state, item)`:** accepted if the item is on the floor in this room and is not guarded. It adds it at the end of the inventory. If it is guarded, it refuses with `guarded`.
- **`enter(state, door)`:** accepted if the door is in this room and is open. It changes `room`, and the text is the name of the new room. It turns off the tiles of the unsolved floor puzzles of the room it leaves: leaving the room is leaving the zone. It puts the generators of the incomplete circuits of the new room back in their starting configuration. If the door is barred, locked or sealed, it refuses with the door's text.
- **`activate(state, switch)`:** accepted if the generator is in the room and its circuit is not complete yet.
  - It flips every flag in `toggles`.
  - Then it checks the circuit. If all the generators are on it sets `solved_flag` and answers `circuit_complete` with `solved_text`; otherwise it answers `toggled` with the generator's `toggle_text`.
  - On a circuit that is already complete it refuses with `already_done`: the generators stay on.
  - An id that is not a generator raises an exception, like every wrong id.
- **`step_on(state, tile)`:** `main.py` calls it when the player arrives on a tile. It moves on the state machine described in §4:
  - `tile_lit` if the tile is the next one in the sequence;
  - `phase_complete` if it closes a phase, with the name of the next one in the text;
  - `tiles_complete` if it closes the last one, with `solved_text`;
  - `tiles_reset` if it is wrong: the phase starts over.

  It refuses with `already_lit` if it is the tile lit last, with `already_done` if the puzzle is already solved, with `not_here` if the tile is in another room.
- **`leave_zone(state, floor_puzzle)`:** `main.py` calls it when the player leaves the zone around the tiles. If at least one tile was lit, it answers `tiles_reset` and the phase starts over; otherwise it refuses with `nothing_happens`.
- **`use_item(state, item, target)`:** needs `item` to be in the inventory and `target` to be in the room.
  - On a locked door that needs that item: if the player has **all** the items of `requires`, it opens it by writing its own id in its `choice_flag` (`crab_door` or `angel_door`); otherwise it refuses with `missing_item`. A part of a required item (a half of the key) refuses with `not_fused`.
  - On the anvil: it fuses the parts, as in "Fusing".
  - On a puzzle or a character: it applies the reaction. If there is no reaction the text is "nothing happens"; if the reaction has already been applied it is "already done".
  - The item always stays in the inventory, even after "give".
- **`examine(state, target)`:** returns only a text. Depending on the target it is:
  - the description of the room, if the target is the current room;
  - the description of an item;
  - a character's line;
  - "it is locked", or what bars the door;
  - the `done_text` of a solved puzzle.
- **`perform(state, action)`:** receives an action as data and calls the right function, `step_on` and `leave_zone` included. The action has a verb, an item and a target, which is the same shape `actions_for` produces. `main.py` sends every action through here, and the tests write the scenarios as lists of actions.

### `event` codes

- **Accepted actions:** `started`, `picked_up`, `entered`, `door_opened`, `fused`, `flag_set`, `toggled`, `circuit_complete`, `tile_lit`, `phase_complete`, `tiles_complete`, `tiles_reset`, `ending`, `info`.
- **Refused actions:** `needs_confirmation`, `game_over`, `not_here`, `already_have`, `guarded`, `no_item`, `barred`, `locked`, `sealed`, `already_open`, `missing_item`, `not_fused`, `already_done`, `already_lit`, `nothing_happens`.

A mistake on the tiles (`tiles_reset`) is an accepted action: it changes the state, so it is saved.

Private helper functions:
- building an outcome or a refusal;
- checking whether something is in the current room;
- applying a reaction to a copy of the state;
- saying whether an item is guarded and whether something is still standing;
- finding the circuit of a generator, saying whether it is complete, putting the generators back in their starting configuration;
- finding the floor puzzle of a tile, saying whether a tile is lit, turning off the tiles of the room being left, checking that a save does not hold an impossible moment of the tiles.

## 7. `save.py`: saving

- **Functions:** `save_game(state, path)` and `load_game(path)`. The path is optional: without it `SAVE_PATH` is used, that is `savegame.json` next to the game. `SAVE_PATH` is read at every call, so `conftest.py` can move it to a temporary folder for each test and no test touches the real save file.
- **Format:** the file holds a `version` number plus the state.
- **Atomic writing:** first a temporary file, then the rename. The game is saved after every action, so a crash in the middle of writing must not corrupt the game.
- **Errors when reading:** a missing file, broken JSON or a different version give `None`, never an exception. `restore_state` validates the content.
- **Errors when writing:** they are not hidden, but raised. `main.py` (M3) shows a message if saving fails.
- **Repository:** the save file and its temporary copy are in the `.gitignore`.

## 8. `main.py`: the pygame interface

### Drawing

- **Resolution:** everything is drawn on a 256×224 Surface, which is then scaled ×3 (768×672) with `scale`, which is nearest-neighbour, never with `smoothscale`. The game runs at 60 fps.
- **Grid:** with 16 px tiles the grid is 16×14: 2 rows of HUD and a 16×12 room with its walls. The doors are in the middle of the walls, as in Isaac.
- **Texts:** with the pixel font of `pixel_font.py`, in three sizes: text, titles, big title.
- **Graphics:** 16×16 sprites and tiles from `sprites.py`.
  - The doors are drawn for the north wall and turned for the others.
  - The player looking left is the right-facing sprite, mirrored.
  - Whoever is lower on the screen covers what is behind.
  - If a sprite is missing, the coloured rectangle is drawn.
- **Animations:** they count frames in `app["frame"]`, not real time, so the tests can reproduce them. They are:
  - two alternating steps when the player walks;
  - two pictures of the sea;
  - the swaying ship;
  - the blinking arrow of the text box;
  - the room coming out of the dark after a door;
  - the crackling barriers;
  - the tiles blinking red after a mistake (`FLASH_FRAMES`), before going dark;
  - the dawn or the explosion in the endings.
- **Tiles:** the zone is a metal grating; on it, the tiles, grey when dark and yellow when lit, with the number written in the font. The door of the hold, while it is barred, has bars and a brass plate with a half-key-shaped slot. The two halves of the key in the inventory are the ring and the toothed part; the fused key is whole, with the mark of the weld. The crab is drawn 32×32 and the angel 16×32.
- **Generators:** each one has a lamp and a lever, and its letter above it. On and off can be told apart at a glance. A cable joins two wired generators, and lights up when both are on. The key on the altar is drawn a little higher, resting on top.

### Scenes

The sequence is menu → confirmation → game → ending. Pause, dialogue, action menu and inventory can open over the game.

### Flows

- **Start:** `load_game` and `restore_state` give the existing progress, or `None`. `menu_options` decides whether to show "Resume".
- **Resume:**
  - if the game is over, the ending screen opens, to see the outcome again (PT05);
  - otherwise the player appears at the `entry` of the saved room.
- **New game and Restart:** they call `start_new_game(existing)`. If the answer is `needs_confirmation` the Yes/No question appears. "Yes" calls the function again with the confirmation; "No" changes nothing.
- **Saving:** every action goes through `perform`. After every `ok` outcome, both of an action and of `start_new_game`, `save_game` is called.
- **Outcome texts:** they appear in a box that blocks movement until you close it. These are the exceptions, which appear for a few seconds without blocking:
  - `entered`: the name of the new room, as a title;
  - `toggled`: a generator's "Click!", so that combinations can be tried without closing a box every time;
  - the outcomes of the tiles (`tile_lit`, `phase_complete`, `tiles_reset`), because the player is walking.

  The win messages of the two puzzles (`circuit_complete`, `tiles_complete`) appear in the box instead.

### Movement and doors

- **Movement:** with the arrows or WASD. The player stops against walls, closed doors, puzzles, characters, generators, barriers, altar and anvil. Items on the floor and tiles can be walked over instead.
- **Doors:** walking into a door calls `enter` **once per contact**. If the door is open the room changes, otherwise the text of the refusal appears (A1, PT04).
- **Arrival:** coming in through a door, the player appears in front of the door that leads back.

### Movement triggers

The tiles are played with the feet, not with E. After every step, `update` calls `floor_triggers`:
- **Tile:** the player stands on the tile under the middle of their body. When that tile changes, and it is a tile, `step_on` is called. Standing still, or moving on the same tile, does not repeat it.
- **Zone:** when the middle of the body leaves the zone of a puzzle, `leave_zone` is called.
- **Memory:** `app` remembers the tile and the zones of the frame before (`on_tile`, `zones`). Appearing somewhere (at the start, when resuming, after a door) is not walking there: `settle_on_floor` updates the memory without triggering anything. The arrival points are outside the zones anyway, and a test checks it.
- **Outcomes:** `floor_action` shows them without stopping the player. Refusals are silent, because walking is not a request; the other outcomes play a sound, appear in the banner and are saved. The win opens the text box.
- **E and the tiles:** the tiles are not targets of E. Standing on a tile, E looks around.

### Sounds

`sounds.py` makes the effects with square waves, like an 8-bit console, without audio files. `EVENT_SOUNDS` says which one plays for each outcome of the tiles:

| Outcome | Effect |
|---|---|
| `tile_lit` | `blip`, a short note |
| `phase_complete` | `ding`, two rising notes: the confirmation sound |
| `tiles_complete` | `fanfare`, four notes |
| `tiles_reset` | `buzz`, the low "BZZZ" of the mistake |

`main()` prepares them at start-up with `sounds.load()`, in the mixer's format. If the computer has no audio, the mixer does not start and `play` does nothing: the game goes on the same.

### Interaction

- **HUD:** two lines.
  - First line: the name of the room and "I: inventory".
  - Second line: "E: <action>" and the icons of the items collected. The target is the nearest thing within `REACH` pixels; if nothing is within reach, the hint shows "Look around". In a top-down game this is how the available actions are shown (PT02). If there is more than one action, the hint shows the name of the thing.
  - The full list of controls is at the bottom of the title screen.
- **E:** calls `actions_for` on the nearest thing, tiles excluded. If there is only one action it does it at once; if there are more, it opens a mini-menu. `irreversible` actions ask for confirmation, with "No" highlighted. If there is nothing nearby, E describes the room. Only E makes the player act: Enter and Space are for closing texts and choosing in menus.
- **I:** shows the inventory, with descriptions and clues (`clues`).
- **Esc:** opens the pause menu, with Continue, Restart, Main menu and Quit. There is no "Save", because the game is already saved after every action.

### Ending

The screen says clearly which ending it is ("Ending 1 of 2 — Everyone saved"). It offers "New game", which goes through `start_new_game` and so asks for confirmation.

## 9. Requirements and checks

| Requirement | How the design meets it | Check | Milestone |
|---|---|---|---|
| **PT01** Start and resume | `menu_options`; `start_new_game` with confirmation; `restore_state` | `test_pt01_*`, A4, A6 | M1, M2, M3 |
| **PT02** Explore | `things_here` and `actions_for`; "E: <action>" in the HUD; E with no target describes the room; every accepted action has a text | `test_pt02_*` | M1, M4 |
| **PT03** Collect and use | Inventory with I; the two halves, fused at the anvil, become the key that opens both final doors; no duplicates | A2, A3, `test_pt03_*` | M1, M4, M5 |
| **PT04** Apply consequences | Who gets the wand decides the ending; fusing changes the inventory for good; every refusal has an explanation, the unfused half too; every mistake on the tiles can be seen, read and heard | A5, `test_pt04_*` | M1, M5 |
| **PT05** Finish and replay | `ENDINGS` with a title; after the ending every action is refused; ending screen with "New game" | A5, `test_pt05_*` | M1, M4 |
| **R1** Actions only with the right room and conditions | Every action checks room and conditions; a refusal returns the state untouched; the hold is barred until the player has the first half | `test_r1_*` | M1, M5 |
| **R2** Items only where expected, once, reusable | `room`, `appears_if` and `free_if`; `pick_up` refuses duplicates; items are not used up, and fused halves do not come back | `test_r2_*`, A2, A3 | M1, M5 |
| **R3** Scenes remember changes | Derived visibility; `done_text`; solved puzzles drawn as solved; the complete circuit and the solved tiles stay so | `test_r3_*`, A3 | M1, M4, M5 |
| **R4** A new game resets progress, not the story; every ending is reachable | `new_game` copies the data; `story.py` is never changed | `test_r4_*`, A5 | M1 |
| Remember scene, items, decisions and ending | The 4 fields of the state | A4 | M1, M2 |
| Save after every accepted action | `main.py` saves after every `ok` outcome | `test_persistence_*`, M4 checklist | M2, M4 |
| Accepted changes survive a restart; refused ones do not touch the data | Atomic writing; no saving on refusals | `test_persistence_*` | M2 |
| First version: 5 scenes, 2 items, 2 endings, about 10 minutes | See §1 | `test_story_*`, M4 checklist | M1, M5 |
| Tile puzzle: a state machine for 3 phases, a mistake that starts the phase over, BZZZ and lights out, a win that removes the barrier | See §4, §6 and §8 | `test_m5_*` in `test_engine.py`; triggers, sounds and blinking in `test_main.py`; `test_sounds.py` | M5 |

## 10. Acceptance scenarios

| Scenario | Steps | What is checked | Milestone |
|---|---|---|---|
| **A1** A locked route | New game, then `enter` on the crab's door and on the angel's | Refusal `locked` with an explanation; the player stays on the deck, the inventory does not change, the state is identical | M1 |
| **A2** An unlocked route | Wand, generators (A then D), first half, tiles of the hold, second half, fusing at the anvil, back to the deck, "use fused key" on the crab's door, `enter` | The player reaches the crab's room, with the fused key still in the inventory | M1, M5 |
| **A3** No duplicate collection | Pick up the wand, go into the cabin, come back and try again; then the same with the two halves | Refusal, and one copy of each item only. Going back into the cabin or the hold, the halves are no longer there, not even after fusing; activating a generator again or stepping on the tiles again gives `already_done` | M1, M5 |
| **A4** Resume correctly | Wand, fused key, opening the crab's door; then save and reopen with `load_game` and `restore_state` | Same room, inventory and flags. `door_status` and `actions_for` identical before and after: the same ways open, the angel's door still locked and still to be opened | M1 with a JSON round trip, M2 with the file |
| **A5** Two outcomes | Two new games, one for each ending | `saved` and `explosion` are reached. After the ending every action is refused and the state does not change, also after reloading | M1 |
| **A6** Restart safely | With saved progress, `start_new_game` first without confirmation, then with it | Without confirmation: identical state and untouched file. With confirmation: deck, empty inventory, starting flags, no ending, file overwritten | M1 and M2 |

Each scenario is shown twice: with the automatic test (from `test_a1_*` to `test_a6_*`) and with the manual checklist below, in the real game.

### Manual checklist

Start the game with `uv run python main.py` inside `plot_twist/`. To start from scratch, delete `savegame.json`.

| Scenario | What to do | What must happen |
|---|---|---|
| **A1** | New game. Walk into the door to the east (claw) and then into the one to the west (wing). | "It is locked" appears. You stay on the deck and the second line of the HUD shows no item icons. |
| **A2** | Pick up the wand (E). In the cabin: E next to generator A, then next to generator D. Pick up the key from the altar. Go into the hold and walk on tiles 1 2 3 4 5, then 3 1, then 5 2 4 3. Pick up the second key from the anvil, then E next to the anvil and "Use: Central key". On the deck: E on the claw door, then "Use: Fused key". Go in. | After generator D, "The electric flow is complete! The barrier has dissolved!" appears; after the last tile, "The hold's system unlocks! The barrier has dissolved!". At the anvil the fusing text appears. In the end you are in the crab's room, with the fused key still in the inventory (I). |
| **A3** | Go back into the cabin after taking the first half, then into the hold after taking the second. Try E next to the altar, a generator and the anvil; walk on the tiles again. | There is no other half on the altar or on the anvil. The generator answers "The circuit is complete: the generators stay on"; the tiles stay lit and make no sound. There is only one fused key in the inventory. |
| **A4** | Halfway through, after opening a final door, close the window. Open it again and choose "Resume". | You appear again at the entrance of the same room, with the same items. The open door is still open, and the other one can still be opened with the fused key. |
| **A5** | Play until you give the wand to the crab. Then, from a new game, to the angel. | First the text of the action, then the ending screen ("Ending 1 of 2 — Everyone saved" or "Ending 2 of 2 — The ship explodes"). Resuming the game takes you back to the ending screen, and you cannot play any more. |
| **A6** | Halfway through, Esc and then "Restart". Answer "No". Do it again and answer "Yes". | With "No" the game stays as it was. With "Yes" you are on the deck at the start, without items, with the opening scene. |
| **Two doors** | With the fused key, open the claw door, then the wing door, and go into both. | Neither asks for confirmation, both open and the fused key stays in the inventory. Giving the wand asks for confirmation instead. |
| **Gate** | New game. Walk into the door at the bottom, the one to the hold. Then take the first half of the key and try again. | First the text of the gate appears, with the half-key-shaped slot, and you stay on the deck. With the first half, the door has no bars any more and you go in. |
| **Half key** | With the two halves not fused yet, E on the claw door and "Use: Central key". Then, with one half only, try to use it on the anvil. | On the door it says the half must be fused at the anvil, and the door stays locked. On the anvil it says the other half is missing. |
| **Tiles** | With the sound on, in the hold: walk on 1 and 2, then on 4. Do 1 2 3 4 5 again. Leave the zone, come back in and walk on 5. Then 3 1, and 5 2 4 3. | Each right tile lights up with a "blip". Tile 4 goes "BZZZ": the tiles blink red and go dark. With 5 you hear the "ding" and "Phase 2: The Return" appears, with 5 staying lit. Leaving the zone you hear "BZZZ" again and 5 goes dark. At the end there is the fanfare, the win message appears, the barrier around the anvil disappears and the second key can be picked up. |
| **Generators** | New game, go into the cabin. Activate B. Leave and come back in. Try to reach the key. Then activate A and D. | With B, A and D turn on and B turns off: lamps and cables change at once, with a "Click!" that does not block. Coming back in, the generators are as at the start again (A and D off, B and C on). While the barrier is there the key cannot be reached. With A and D the barrier disappears. |

## 11. Other tests

- **Data integrity** (`test_story_*`):
  - ids are unique;
  - every reference to rooms, items and flags exists;
  - every door has its way back;
  - every door with `requires` has a `choice_flag`, and every door with `opens_with` has its `barred_text`;
  - every puzzle has a `done_text`;
  - every generator is in one circuit only, in its own room, and the flags it flips exist;
  - every tile is in one floor puzzle only, in its own room, and every phase starts from the tile the one before ends on;
  - no text is empty.
- **PT02 and PT04:** in every room and at various moments of the game, all the actions of `actions_for` are tried, plus some impossible ones. Accepted actions have a text, refused ones an explanation.
- **R1:** every refusal leaves room, inventory and flags identical.
- **R2:** no half of the key can be picked up while its barrier is there, nor from another room.
- **Generator puzzle (M5):**
  - the starting configuration;
  - each generator flips itself and its two neighbours, and activating it twice undoes it;
  - starting from each of the 16 configurations and activating each generator, the circuit is complete if and only if all four are on;
  - coming back into the cabin the generators go back to the start, but a complete circuit stays complete, also after saving;
  - the barrier keeps the key out of reach from every place the player can stand on (layout test).
- **Tile puzzle (M5):**
  - each phase, step by step, with the name of the next phase in the text;
  - a mistake in each of the three phases starts only that phase over;
  - going back onto the tile lit last, or leaving the zone with no lights on, changes nothing;
  - leaving the zone, or the hold, halfway through a phase starts it over;
  - trying every tile at every moment, the only shortest solution is the brief's, and from every moment the puzzle can still be won;
  - a save halfway through a phase is resumed identical, and one with an impossible moment is refused;
  - the zone holds only the tiles, and from each tile you can reach every other one without stepping on a third (layout test);
  - the triggers: each tile fires once per arrival, appearing is not walking, the tiles are not solid and are not targets of E;
  - each outcome has its sound and its text in the banner, the win opens the text box, each accepted outcome is saved;
  - after a mistake the tiles blink red, then go dark (checked on the pixels);
  - the square waves of the sounds, and the game silent but working without audio (`test_sounds.py`).
- **R4:**
  - the data of the story is identical after two complete games;
  - a `new_game()` made after a game is equal to the first one;
  - both endings are reached from `new_game()`, also without reading the barrel's clue.
- **Persistence (M2):**
  - after a refused action the file is identical byte for byte;
  - after every accepted action, reloading gives the same state;
  - with a missing or broken file, "Resume" does not appear.

Conventions:
- **Names:** the name of each test contains the id of the requirement (`test_a1_…`, `test_pt02_…`, `test_r1_…`), so the test file is also the proof of the requirements.
- **Helpers:** there are two.
  - The first plays a list of actions starting from `new_game()` and checks that each one is accepted, so each scenario is a script of a few lines.
  - The second does "`perform`, and if `ok` save", exactly like `main.py`.
- **What is checked:** `event` and state, **never the texts**.
- **Isolation:** the tests do not import pygame and do not touch the real save file.

## 12. Milestones

### M1 — The game without graphics

**Status: done.** 60 green tests. On top of that, 23 bugs put into the engine on purpose are all caught by the tests.

Files: `story.py`, `engine.py`, `test_engine.py`.

Order of work, writing the test before the function each time:
1. Data and integrity tests.
2. `new_game`, `start_new_game`, `menu_options`.
3. `pick_up`.
4. `door_status` and `enter`.
5. `use_item` on puzzles.
6. Choice doors.
7. Endings, and the lock after the ending.
8. `restore_state`.
9. `things_here`, `actions_for`, `perform`, `clues`.

*Done when*:
- `uv run pytest` is green;
- A1–A6 pass in the part that concerns the engine (A4 with a JSON round trip);
- `story.py` and `engine.py` do not import pygame;
- both endings are reached using only the engine.

To finish A4 and A6 completely already in M1, it is enough to write `save.py` early, which is small.

### M2 — Saving

**Status: done.** 83 green tests in all, A4 and A6 with the real file included. On top of that, 9 bugs put into `save.py` on purpose are all caught by the tests.

Files: `save.py`, `test_save.py`, `conftest.py`. On top of that, the file part of A4 and A6 and the persistence tests are completed.

*Done when*:
- you save halfway through a game, reload, and find room, inventory, flags and sealed door identical;
- a refused action does not touch the file.

### M3 — Window, menus and movement, with rectangles

**Status: done.** 109 green tests. On top of that, 15 bugs put into `main.py` on purpose are all caught by the tests.

Two things planned for M4 already arrived here:
- **Ending screen:** it is needed to resume a game that is already over.
- **"Restart" in the pause menu:** it uses the same confirmation as "New game".

- **Scenes and menus:** drawing at 256×224 ×3; the menu uses `menu_options` and `start_new_game`, confirmation included.
- **Rooms:** the layout goes into `story.py`; movement and collisions.
- **Doors:** `enter` once per contact. The player appears in front of the door back, or at `entry` when a game is resumed.

*Done when*:
- you walk around between deck, cabin and hold;
- trying to go through the crab's door, "it is locked" appears;
- you close the game and resume from the entrance of the right room.

### M4 — The complete game, still with rectangles

**Status: done in the code.** 119 green tests. Among the tests there are two complete games played only with the keys, one for each ending. On top of that, 13 bugs put into the new parts of `main.py` on purpose are all caught by the tests. The manual checklist (§10) is still to be done, on the real game with a window.

- "E: <action>" in the HUD; E with mini-menu and confirmations; dialogue box.
- Inventory with clues.
- After the ending the game moves to the ending screen, which already exists since M3.

*Done when* the manual checklist A1–A6 passes in the real game:
- a complete game for each ending;
- quitting and resuming halfway through;
- an attempt to open the sealed door;
- "Restart" first cancelled, then confirmed.

### M5 — Real puzzles

**Status: done in the code.** The two puzzles are real (§4): the wired switches in the cabin and the tiles in the hold. The key is split in two halves, one per puzzle, and the hold is barred until the player has the first.
- **Tests:** 216 green. Among them there is a complete game played only with the keys, tiles included, by walking on them.
- **Bugs put in on purpose:** all are caught: the 15 of the generators, the 40 of the tiles and sounds, and the 13 of the anvil, the fused key and the bigger characters. The ones of the earlier milestones are still caught too: 23 in the engine, 9 in saving, 15 of M3, 13 of M4 and 11 of M6.
- **In the real game:** a game recorded without a window, walking, up to the ending. The sounds played in the right order.
- **Still to do:** the manual checklist (§10) on the real game, and measuring whether people who do not know the solutions take about 10 minutes.

The plan:
- **Puzzles:** the placeholder reactions are replaced. If new mechanics are needed (sequences, codes), conditions are added to the format of the reaction, or a function to the engine, always writing the test first.
- **Tests:** the contract "solving a puzzle = setting a flag" stays the same. In the tests only the steps that solve the puzzles change.
- **Length:** more things to examine are added, up to about 10 minutes of play.

*Done when*: the tests are green with the real puzzles, and people who do not know the solution finish in about 10 minutes.

### M6 — 8-bit graphics

**Status: done.**
- **Tests:** 137 green. The test files of M1–M4 did not change; the new tests are in `test_graphics.py`.
- **Bugs put in on purpose:** the 11 in the graphics are all caught, and so are those of M3 (15) and M4 (13).
- **Speed:** about 1 ms per frame, measured without a screen, against the 16.7 ms that are enough for 60 fps.
- **Sounds:** there are none, they were optional.

The sprites and the font are original, drawn as text: they are changed by changing the letters in `sprites.py` and `pixel_font.py`.

- **16×16 sprites:** the player in 4 directions, with a walking animation; crab and angel; open, locked and sealed doors easy to tell apart.
- **Graphics and texts:** a tileset for each room and a pixel font.
- **Effects:** a transition between rooms, the explosion in the ending, optional sounds.
- **Missing sprites:** sprites are looked up by id, and if one is missing the coloured rectangle is drawn.

*Done when*: no rectangles are left, the game runs at 60 fps, and the tests, unchanged, are all green.

## 13. Assumptions

- **Hub:** the deck is the hub, and all four doors start from there.
- **Context menu:** E opens a context menu, instead of having the player choose an item in the inventory before pressing E. So there is no "item in hand" to manage, and only the engine knows what can be done.
- **Confirmations:** opening a final door and giving the wand ask for confirmation. An E pressed by mistake must not decide the game.
- **Resume:** on a game that is over, it shows the ending again.
- **New game:** it asks for confirmation every time a save exists, even of a game that is over (PT01 to the letter).
- **Clue:** it is optional. The barrel of the hold helps to choose the door, but is not needed to finish.
- **Generator puzzle:**
  - it replaces the placeholder drawer of the cabin, and the key has become the "Central key";
  - the wand is no longer needed for the key, but it is still needed for the hold and for the ending;
  - "starting configuration when entering the room" means that the generators go back to the start every time the player walks into the cabin from the deck. When a game is resumed instead, they are found as they were saved, because the saved state is resumed (A4);
  - with the circuit complete the generators stay on and cannot be activated any more;
  - the key can be seen on the altar from the start, behind the barrier: it can be examined, but not picked up.
- **The two halves of the key and the anvil:**
  - the halves are named as in the brief, "Central key" (cabin) and "Second key" (hold); fused, they become the "Fused key";
  - the anvil takes the place of the chest, behind the same barrier, with the second half on it. The key is fused by using one of the two halves on the anvil;
  - when fusing, the two halves disappear from the inventory: it is the only case in which an item changes. The fused key is not used up instead, and it opens both doors;
  - the final doors no longer seal each other, so opening them does not ask for confirmation: the choice that decides the ending is only who gets the wand. The engine can still seal doors that share a flag (there is a test), but none do;
  - a save from earlier versions, with the old `chosen_door` flag, can no longer be resumed: a new game must be started.
- **Crab and angel:** only their look changes. The crab covers 2×2 tiles, four times the area it had; the angel 1×2, twice. They do and say the same things.
- **The gate of the hold:** it is on the door of the deck that leads to the hold, so it bars the whole hold, barrel included. It opens by itself as soon as you have the first half of the key, without having to use it. The brief says both "until the first puzzle is solved" and "once the piece of the key is obtained": the second applies, which in practice is the same moment.
- **Tile puzzle:**
  - Phase 2 and Phase 3 start with their first tile already lit, the one the player is standing on;
  - stepping on a tile lit earlier in the same phase is a mistake too, but not on the one lit last: going back onto it is only a step back;
  - a wrong tile when none is lit still goes "BZZZ". Leaving the zone with no lights on does nothing instead, because it is only walking;
  - resuming a game saved halfway through a phase, the lights stay as they were: the saved state is resumed (A4);
  - the sounds are made in the code; besides the "BZZZ" and the confirmation sound of the brief, there is a "blip" at each right step and a fanfare at the win. Only this puzzle has sounds;
  - as a clue, the names of the phases from the brief are engraved on the anvil and announced at each change of phase.
- **Language:** from the version after M5 all the texts of the game are in English, in `story.py`. This document was first written in Italian and has been translated into English; the steps and requirements quote the texts of the game in English.
