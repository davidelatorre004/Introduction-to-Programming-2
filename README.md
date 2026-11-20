# Plot Twist

An 8-bit adventure game for one or two players, made in Python with pygame for the Introduction to Programming course (Nova SBE, 2026/27).

You wake up on the deck of a ship adrift in a storm, with a magic wand at your feet. You explore the ship, solve three puzzles to put a broken key back together, and decide who to give the wand to: there are three endings. Two players can play together on two computers on the same network, each with their own character and ability, chased by a crab that comes to life.

## Team

| Name | Student number |
|---|---|
| Davide La Torre | 80029 |
| Germano Di Felice | 81892 |
| Elisa Profeti | 78635 |
| Riccardo Miraglia | 79909 |

## Where to get it

Plot Twist is a desktop application: it runs on the player's own computer, in a window of its own. There is no web page to open: the game is downloaded from this repository.

- **Download (the `main` branch, as a ZIP):** https://github.com/davidelatorre004/Introduction-to-Programming-2/archive/refs/heads/main.zip
- **Repository:** https://github.com/davidelatorre004/Introduction-to-Programming-2

## Run it locally

You only need [uv](https://docs.astral.sh/uv/): it installs the right Python (3.12) and the pinned dependencies by itself.

1. Install uv, once:
   - Mac or Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

   Then close the terminal and open it again.
2. Get the code, with git or by extracting the ZIP above:
   ```
   git clone https://github.com/davidelatorre004/Introduction-to-Programming-2.git
   cd Introduction-to-Programming-2/plot_twist
   ```
3. Start the game, from the `plot_twist` folder:
   ```
   uv run python main.py
   ```

How to play, the controls, the game for two and the solution: [plot_twist/README.md](plot_twist/README.md).

## Run the tests

From the `plot_twist` folder:
```
uv run pytest
```
The tests need neither a screen nor a sound card: they run the game without a window.

## What is in the repository

Everything is in [plot_twist/](plot_twist/):

| Part | What it does |
|---|---|
| `story.py` | The game's data only: rooms, items, doors, puzzles, characters, texts |
| `engine.py` | The rules, as pure functions: they take a game state and return the new one and what happened |
| `main.py` | pygame: the window, the keys, the drawing, the sounds, the game for two |
| `save.py` | Saving and loading the game, as JSON |
| `net.py` | The connection between two computers in a game for two |
| `sprites.py`, `scenery.py`, `effects.py`, `crab.py`, `claw.py`, `weather.py` | The pictures and the visual effects, all made in code |
| `sounds.py` | The sounds, made in code like on an 8-bit console |
| `test_*.py` | The automatic tests |

What changed in each version: [plot_twist/CHANGELOG.md](plot_twist/CHANGELOG.md). The rules for every change: [plot_twist/CLAUDE.md](plot_twist/CLAUDE.md).
