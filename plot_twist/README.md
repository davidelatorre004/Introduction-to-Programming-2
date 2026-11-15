# Plot Twist — how to play

A short 8-bit game: you wake up on the deck of a ship adrift, with a magic wand lying on the floor nearby. You explore the ship, solve puzzles to put a broken key back together, and in the end you choose who to give the wand to. There are three endings.

The game has a few sound effects: keep the sound on.

What changed in each version: [CHANGELOG.md](CHANGELOG.md), with one page per version in the [versions](versions/) folder.

## 1. What you need

- **uv**, the tool that installs Python and pygame for you. If you have already used it, you are all set. Otherwise install it:
  - on Mac or Linux, in the terminal:
    ```
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
  - on Windows, in PowerShell:
    ```
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

  Then close the terminal and open it again.
- **Python** does not need to be installed by hand: if it is missing, uv downloads the right version (3.12) by itself.

## 2. Download the game

The game is in the `plot_twist` folder of the repository, on the `main` branch. The repository is private: GitHub will ask you to sign in with your account.

**With git.** In the terminal, from the folder where you want to put the game (the one the terminal opens in is fine too):
```
git clone https://github.com/davidelatorre004/Introduction-to-Programming-2.git
```
This creates the folder `Introduction-to-Programming-2`.

If you already have the repository on your computer, go into its folder and get the latest version:
```
git checkout main
git pull
```

**Without git:**
1. Open the [repository page on GitHub](https://github.com/davidelatorre004/Introduction-to-Programming-2).
2. Click the green **Code** button, then **Download ZIP**.
3. Extract the ZIP.

## 3. Start the game

In the terminal, go into the `plot_twist` folder (the one with `main.py`) and start the game. If you have just run `git clone`:
```
cd Introduction-to-Programming-2/plot_twist
uv run python main.py
```

On Windows there is a shortcut: open the `plot_twist` folder in File Explorer, type `powershell` in the address bar and press Enter. PowerShell opens already in that folder.

The first time, uv installs pygame: it takes a few seconds. Then the game window opens. If the keys do not respond, click once on the window.

## 4. Controls

| Key | What it does |
|---|---|
| Arrows or WASD | Move |
| E | Interact with what is next to you. In text boxes, go on |
| I | Open and close the inventory |
| Q | Drop the last item you got, where you stand. Anyone can pick it up again with E |
| Space | Use your character's ability (only in a game for two, once per game) |
| F11 | Full screen, and F11 again to go back to the window |
| Esc | The pause menu: Continue, Restart, Main menu, Quit |
| Up, Down and Enter (or E) | Choose in menus |

Some help:
- **What E does:** the bar at the top tells you, on its second line, for example "E: Pick up: Magic wand". E only acts on what matters to the story: next to furniture (barrels, crates, lanterns...) or far from everything it does nothing. Notes pinned to the walls can be read, though.
- **Several possible actions:** E opens a small menu, for example Examine, "Use: …", "Give: …".
- **Doors:** to go through, just walk into them. If a door is closed, the game tells you why.
- **Final choices:** the game asks you to confirm, with "No" already selected. To confirm, choose "Yes".

### Two players, on two computers

Two people can play together on two computers connected to the same network (the same Wi‑Fi). Each one has their own screen and moves on their own.

1. On the first computer: **New game**, then **Host game for 2**, then choose your character. The screen shows "Your address: …", for example `192.168.1.23`.
2. On the second computer: **Join game**, type that address (digits and dots only) and press Enter. Then choose your character.
3. The game starts on both screens.

Some help:
- Each player has their own inventory. To give an item to the other player, walk up to them and press E: "Give to partner: …".
- Esc opens the menu, but the game does not stop, because the other player keeps playing. Main menu or Quit end the game for both.
- The game is saved only on the computer that hosts it. To resume it, choose **Resume** on that computer; then the other player joins again with Join game.
- If the second computer cannot find the game, check that both computers are on the same network. Also check that the firewall of the first one lets the game in (port 50555).

**The characters.** At the start you choose one of four characters. Alone, only the look changes. In a game for two each player chooses their own on their own screen (the player who joins cannot take the host's), and each one has an ability:

| Character | Ability |
|---|---|
| Wizard | Space: the crab is stunned and stands still for 5 seconds, whatever room it is in |
| Nurse | Always on: she helps a player who is down get up in 1 second instead of 4 |
| Ghost | Space: for 5 seconds the crab cannot see you and goes for the other player. If the other player is down or out, the crab runs away from you |
| Flash | Space: a dash of 5 tiles in the direction you face. It stops against obstacles and goes through open doors and portals |

The Space ability works only once per game: the bottom left corner says so as long as it is available. If you use it while the crab is still a statue, it is wasted.

**The crab (two players only).** As soon as you solve the cabin, the whole ship shakes: the crab statue on the deck trembles, breaks into pieces, and the crab comes out to hunt you. The rubble stays there until the end.
- It chases the nearest player and is slower than you. If nobody is in its room, it follows you through the open doors.
- If it touches you, you go down and cannot move. Your partner has one minute to help you up: they must stand next to you and hold **E** for 4 seconds (the green bar shows how much is left).
- If nobody helps you up in time, you are out until the end of the game, and your items pass to your partner. While you are out you watch your partner play.
- If the crab catches both of you, even when one of you is already out, the game is lost: a giant claw snaps shut on the screen and breaks it to pieces, and then comes the third ending, "Caught by the crab".
- A strategy: one player keeps the crab busy while the other solves the puzzles.
- When you fuse the two halves of the key, the crab turns back to stone and vanishes in a cloud of dust.

## 5. The goal (no spoilers)

- From the deck you can reach four rooms:
  - at the top, the captain's cabin;
  - at the bottom, the hold, closed by a gate;
  - on the right and on the left, two locked doors.
- The key to the locked doors is broken in two halves: each puzzle hides one. The halves do not turn on their own: they must be fused on an anvil, which appears only after you have helped the doctor in the infirmary.
- The fused key opens both doors. Behind each one there is someone who wants your wand, and who you give it to decides the ending.
- **Hint for the cabin:** the eight generators are wired together in a ring, and switching one also switches the two next to it. You must turn them all on at the same time.
- **Hint for the infirmary:** the doctor's remedy is made with four bottles, in a precise order. The first one is in the infirmary; when you pick it up, the others appear around the ship: look for them. The doctor's notes give the order.
- **The mine:** the portal at the end of the corridor leads to a mine. At the far end of the mine a second portal takes you back to the ship, but it only works one way.
- **Hint for the hold:** the five numbered tiles are stepped on, in three trials one after the other. A wrong tile, or walking off the metal grating around them, starts the current trial over: "BZZZ!". The names of the trials are engraved on the barrier around the altar at the far end of the hold: examine it.

## 6. Saving

- **Automatic:** the game saves by itself after every action, so you can close the window whenever you want.
- **Resume:** from the main menu you go back to the entrance of the room you were in, with the same items and the same choices.
- **New game:** if there is already a saved game, it asks for confirmation before deleting it.
- **Starting from scratch:** you can also delete the file `plot_twist/savegame.json`.

## 7. If something goes wrong

| Problem | Solution |
|---|---|
| `uv: command not found`, or "uv is not recognized" | Install uv (step 1), then close the terminal and open it again |
| `'origin' does not appear to be a git repository`, or `pathspec ... did not match` | You are not in the repository's folder: download it with `git clone` (step 2), or go into its folder |
| `can't open file 'main.py'` | You are not in the right folder: go into `plot_twist` |
| You cannot find the `plot_twist` folder | You have an old copy: run `git checkout main` and then `git pull` |
| You cannot see the window | Look for it behind the other windows, or in the Dock on a Mac |

To run the automatic tests, inside `plot_twist`:
```
uv run pytest
```

## 8. The solution

<details>
<summary>Spoiler warning: click to see it</summary>

1. On the deck, pick up the magic wand: walk onto it and press E.
2. Go into the cabin, through the door at the top.
   - Each generator, when you switch it, flips itself and its two neighbours in the ring A, B, C, D, E, F, G, H.
   - Switch **A** and then **C**: all eight turn on and the barrier dissolves.
   - Take the key from the altar: it is the "Central key".

   If you leave before you finish, the generators go back to how they were at the start.
3. With the first half of the key, the gate of the hold opens by itself. Go in through the door at the bottom.
   - Optional: use the wand on the barrel. You discover a clue, which you can read again in the inventory.
   - Walk on the tiles, using the lanes of the grating to skip the ones you do not need:
     - **The Wave:** 1, 2, 3, 4, 5;
     - **The Return**, starting from the 5 you are standing on: 3, 1;
     - **The Short Circuit**, starting from the 1 you are standing on: 5, 2, 4, 3.
   - The barrier disappears: take the "Second key" from the altar.
4. From the hold go into the infirmary (door on the left) and pick up the green bottle. The other three appear:
   - the **blue** one in the corridor, through the bottom door of the infirmary;
   - the **red** one in the galley, to the left of the cabin;
   - the **gold** one at the helm, through the top door of the cabin.
5. Go back to the infirmary. Next to the cauldron press E and pour, in this order: **green, red, gold, blue**. If you get it wrong the cauldron empties, but you keep the bottles: start again from the green one.
6. Pick up the remedy from the cauldron and give it to the doctor ("Give: Remedy"). The anvil appears in the middle of the empty room to the right of the cabin, among red sparks: next to the anvil press E and choose "Use: Central key" (or the second one). The two halves become the "Fused key".
7. Go back to the deck. Next to the door on the right, the one with the claw, press E and choose "Use: Fused key". Go in.
8. Next to the crab press E, choose "Give: Magic wand" and then "Yes": **Ending 1 of 3 — Everyone saved**.

For the second ending also open the door on the left, the one with the wing (the fused key opens both), and give the wand to the angel: **Ending 2 of 3 — The ship explodes**.

The third ending, **Caught by the crab**, only exists in a game for two: it is what happens if the crab catches both players.

Optional: from the corridor, at its far end, step into the portal and you arrive in the mine. There is a crystal heart there. It is used the moment you pick it up, and then it is gone: in a game for two it instantly helps your partner up if they are down, or brings them back into the game if they were out (they appear next to you). If nobody needs it, or if you play alone, it is wasted: there is only one per game. The portal at the far end of the mine takes you straight to the helm; the one at the helm does not take you back.

</details>
