# Plot Twist: what changed in each version

Newest first. Each version has its own page in [`versions/`](versions/), with how to play it.

## [v20](versions/v20.md) - Clues on the left, and a chime for a new one (2026-11-03)

In the latest commit of the branch [`claude/funny-ramanujan-ffrx60`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/claude/funny-ramanujan-ffrx60/plot_twist).

- The inventory screen (I) has two columns: the clues found on the left (or "No clues yet."), the items carried on the right. Same box, same font, same clues in the same order.
- The list of items can be longer than the box: up and down scroll it one item at a time, small arrows show there is more above or below, and it always opens at the top.
- When a clue is found, the thing that gave it (the barrel of the hold) glows softly, with four short rays turning around it and twinkles for about a second, and a new light chime plays (`clue` in `sounds.py`). The effect can be switched off with `FX["clues"]` in `effects.py`.
- Nothing changed in what is found, or when.

## [v19](versions/v19.md) - Visual effects (2026-11-03)

In commit [`937d09f`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/937d09f5e395ce5d3cb09a3844ddd682f0c7a36f/plot_twist).

- A new module, `effects.py`: particles, banded 8-bit glows, pixel-by-pixel dissolves, floor ripples and the portal warp. Each effect can be switched off in its `FX` table, and its timing and size are constants at the top of the file. The rules of the game did not change.
- Generators: a lamp that is on glows and pulses, and sparks jump from its lever. Lit cables pulse, with a spot of current running along them. When seven generators are on, the last one trembles and blushes red.
- Barriers: spots of energy run around their edges and they flash now and then; when one opens it dissolves pixel by pixel in one second, crackling with sparks.
- Cauldron: the liquid changes colour with the recipe (seaweed, brown, bright gold, then clear and glowing), bubbles rise in the same colour, and the blue fire lights the floor around it.
- Portals: light turns slowly around the ring, the floor sways around it, and going through one ends in a purple warp instead of a dark fade.
- Tiles of the hold: a lit tile glows and sends out a wave; a mistake throws red sparks and the red blinking lasts a second.
- Anvil: the two halves fly together above it, meet in a burst of sparks and a white flash, and the fused key builds up pixel by pixel.
- Wand: a spark climbs up the arm when it is picked up, and its icon in the bar glows.
- Mood: dust floats in the rooms indoors, lanterns swing and flicker, the crystals of the mine pulse purple. The bad ending flashes white, then red.
- Map: every visited room has a soft halo, the current one pulses, and once the doctor is at peace a small anvil marks the galley, if the player has been there.

## [v18](versions/v18.md) - E only for what matters (2026-11-03)

In commit [`055d470`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/055d470813e653602a8356e53663c1016a130fb2/plot_twist).

- E acts only on things that matter to the story: items, generators, doors, characters, puzzles, the cauldron, the anvil, portals.
- Near furniture, or far from everything, E does nothing and the top bar shows no hint. E also reaches past a barrel to what matters behind it.
- The three notes stay readable: the doctor's notes, the recipe in the galley and the captain's log.
- This file and the `versions` folder: what changed in every version.

## [v17](versions/v17.md) - More decor, no hints on the map (2026-11-03)

In commit [`716d757`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/716d757c82f9b9c9e258ca639d4791d5d4110d71/plot_twist).

- 53 new pieces of decor in every room: barrels, crates, lanterns, chairs, the captain's desk and log, crystals, puddles, an anchor and a fishing net.
- The map no longer blinks on the rooms where the anvil or the tinctures wait: they are found by exploring.

## [v16](versions/v16.md) - Choose your character (2026-11-03)

In commit [`3131e3b`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/3131e3bfb002ace15dbdcc56432f98661f86d7fa/plot_twist).

- After New game, a screen shows two characters side by side: left and right to choose, E to start, Esc to go back.
- They look the same, except for the shirt: green or red. The choice is saved, and Resume keeps it.

## [v15](versions/v15.md) - A calm sea on the title screen (2026-11-03)

In commit [`5740e55`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/5740e5512c0c60a8befe40022b23b54cbcb34233/plot_twist).

- The main menu has the calm blue sea of before again; the deck keeps the storm.

## [v14](versions/v14.md) - Scattered tinctures, a bigger cabin, the heart and a storm (2026-11-03)

In commit [`651350f`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/651350f546bda36c11e383110b5daa1b7456c540/plot_twist).

- The tinctures are items now. The green one is in the infirmary; picking it up makes the other three appear in the galley, the helm and the corridor. A wrong order empties the cauldron but keeps the bottles.
- The cabin is half as wide and half as long again (24 x 18 tiles), with eight generators in a ring. Two levers still solve it: A, then C.
- The corridor to the portal is two tiles lower.
- A crystal heart lies in the mine, and a one-way portal at its far end leads to the helm; the ring in the helm does nothing.
- The sea is darker and stormy; the good ending keeps the calm sea.

## [v13](versions/v13.md) - The whole code in one file, updated (2026-11-03)

In commit [`59ea0d6`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/59ea0d6391cfc3ae0118e44c4be7bfdb3ef24f77/plot_twist).

- `progetto_completo.txt` brought up to date with the code.

## [v12](versions/v12.md) - The doctor, the corridor, the portal and the map (2026-11-03)

In commit [`74650a2`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/74650a243a3e1df9082f3d08208c79f496e91ab9/plot_twist).

- The infirmary has the doctor's ghost and a cauldron: four tinctures poured in the right order make a remedy. Once the doctor drinks it, the anvil appears in the galley.
- New rooms: an empty room east of the cabin, a long corridor under the infirmary, its end with a portal, and a mine beyond it.
- The deck, the corridor and the mine are bigger than the screen: the view follows the player.
- A small map in the corner shows the rooms visited so far.

## [v11](versions/v11.md) - Phase 1: three new rooms and decor (2026-11-03)

In commit [`2db3acf`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/2db3acf40302f825c564f62e094d165cc74e7611/plot_twist).

- New rooms: the infirmary (west of the hold), the galley (west of the cabin) and the helm.
- A new kind of object, decor: furniture that only adds atmosphere. Some of it blocks the way, some lies flat on the floor.

## [v10](versions/v10.md) - The whole code in one file (2026-10-19)

In commit [`4d20a02`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/4d20a02a0fb16074a65ba4a99201873d24d0d3f7/plot_twist).

- `progetto_completo.txt`: every .py file of the game, one after the other, each under its name.

## [v09](versions/v09.md) - English (2026-10-06)

In commit [`060027a`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/060027a17a8ce871e638360c7ac20b41edc4a7ca/plot_twist).

- Every text of the game is now in English. Rules, saves and tests did not change.

## [v08](versions/v08.md) - The anvil, both doors, bigger characters (2026-10-06)

In commit [`8052186`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/805218685db39a851eb993d1d8674e0e216ef0e8/plot_twist).

- An anvil fuses the two halves into the fused key; the halves are gone for good.
- The fused key opens both final doors, and opening one no longer seals the other.
- The crab now covers 2 x 2 tiles and the angel 1 x 2.

## [v07](versions/v07.md) - The tiles of the hold and a key in two halves (2026-10-06)

In commit [`65ba649`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/65ba6499b490925fb9d7ce04a717069880913dc4/plot_twist).

- The cabin gives only the first half of the key; a gate bars the hold until the player carries it.
- Five numbered tiles in the hold, walked on in three phases (1-5, then 5-3-1, then 1-5-2-4-3). A wrong tile, or walking out of the grating, starts the phase over with a BZZZ.
- `sounds.py`: sound effects made in code (blip, ding, fanfare, buzz).

## [v06](versions/v06.md) - The generators of the cabin (2026-10-06)

In commit [`67bc2f5`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/67bc2f53342d26cbe49a9533c817b601eddc30cd/plot_twist).

- Four generators A-D: each one flips itself and the two wired to it. All four on dissolves the barrier around the altar and frees the key.
- The generators go back to their start every time the player walks in, until the puzzle is solved.
- Cables light up between generators that are both on.
- Also in this version: a play guide in Italian (`README.md`).

## [v05](versions/v05.md) - 8-bit graphics (2026-10-01)

In commit [`f272761`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/f2727619065f764ce000c62943a4997686a6b7c1/plot_twist).

- `sprites.py` draws every picture as text, one letter per pixel: the player walking in four directions, items, doors, characters, the ship and the room tiles.
- `pixel_font.py`: an original pixel font.
- Rooms fade in after a door; both endings are animated (dawn and coast, or the explosion).

## [v04](versions/v04.md) - The E key, the inventory and the endings (2026-10-01)

In commit [`6655a92`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/6655a921f3868ce6cc815c8e455fcdd12f06fad8/plot_twist).

- The top bar shows what E would do near the closest thing; several actions open a small menu.
- Actions that cannot be undone ask for confirmation first.
- I opens the inventory, with the clues found.
- Both endings can be reached on screen, and every accepted action is saved.

## [v03](versions/v03.md) - A window, menus and walking (2026-10-01)

In commit [`e2576bc`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/e2576bc5394e97bb8ba1113787ac324269eb7ffa/plot_twist).

- `main.py` opens the window: a 256 x 224 screen scaled three times.
- Main menu (Resume only with a valid save; a new game asks before replacing one), pause menu and ending screen.
- The player walks with the arrows or WASD and goes through a door by walking into it; a closed door says why, once per push.
- Rooms and things are coloured rectangles for now.

## [v02](versions/v02.md) - Saving and loading (2026-10-01)

In commit [`d36c765`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/d36c765d0998e310372b6b7de94e8a3824abab05/plot_twist).

- `save.py` writes the game as versioned JSON, through a temporary file, so a save is never left half-written.
- A missing, broken or outdated save file is treated as no save at all.
- The tests never touch the real save file (`conftest.py`).

## [v01](versions/v01.md) - The rules, without a window (2026-10-01)

In commit [`225b24f`](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/225b24f3336e072e4e639f79591d8f1e603a0d76/plot_twist).

- The story as data in `story.py`: five rooms, two items, eight doors, two placeholder puzzles, two endings and every text.
- The rules in `engine.py`: pure functions on a four-key game state (room, inventory, flags, ending), each returning the new state and an outcome.
- `test_engine.py` covers the acceptance scenarios A1-A6, the required capabilities PT01-PT05 and the business rules R1-R4.
- Nothing to see yet: the game is played by the tests only.
