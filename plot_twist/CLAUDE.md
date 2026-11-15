# Plot Twist: rules for every change

These rules apply to every future change to the game in this folder.

## Architecture

- `story.py` contains only data: rooms, items, doors, flags, texts.
- `engine.py` contains pure functions: they take a state and return `(new_state, outcome)`, without ever changing the state they received.
- `main.py` contains only pygame: input, movement, drawing, sounds.

## The game state

- `STATE_KEYS` does not change (`room`, `inventory`, `flags`, `ending`).
- New things in the story become new flags in `story.FLAGS`, validated by `engine._allowed_values` and by `engine.restore_state`.

## Texts and style

- The game's texts are in English.
- The documentation on GitHub (README, DESIGN, CHANGELOG, versions, this file) is in English too: the people who open it do not speak Italian.
- Comments and docstrings follow the style of the existing code.

## Compatibility

- In 1-player mode the game must behave exactly as before.

## Tests and way of working

- Every change has its own tests.
- After every step run `uv run pytest`. If something fails, stop and explain why before fixing it.
- At the end of every step, sum up briefly what changed and why.
