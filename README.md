# StarWars-Text-Adventure

> A cinematic, choice-driven **text adventure game** set during the Mustafar duel from **Star Wars: Episode III – Revenge of the Sith**.

**Duel of Fates** is a Python terminal game that reimagines the confrontation between **Anakin Skywalker** and **Obi-Wan Kenobi** as an interactive narrative. Instead of retelling the scene in a strictly linear way, the project lets the player shape the outcome through branching choices, morality shifts, turn-based combat, item usage, and multiple endings.

Whether you play as a fallen hero on the edge of total corruption or as a Jedi trying to save his brother, your decisions affect the story, the duel, and the final fate of Mustafar.

---

## Features

- **Two playable protagonists**: choose **Anakin Skywalker** or **Obi-Wan Kenobi**
- **Branching narrative paths** with route-specific scenes and alternate outcomes
- **Morality system** that tracks your movement toward the Light Side, Dark Side, or a conflicted middle ground
- **Turn-based combat** with attacks, defense, Force abilities, critical hits, and item-based actions
- **Inventory system** with route-specific collectibles and usable combat items
- **Multiple endings**, including canon-inspired and non-canon “what if?” outcomes
- **Atmospheric terminal UI** with typewriter text, colored dialogue, boxed scene headers, and ASCII art
- **Audio support** through `pygame`, with graceful fallback if audio is unavailable
- **Save/load groundwork** using JSON-based player state data

---

## Preview

### Play as Anakin
Walk the line between love, rage, ambition, and regret.

- search the Mustafar control room for useful items
- confront Padmé in different ways
- resist or embrace the dark side
- duel Obi-Wan with different emotional states affecting the outcome
- unlock redemption, exile, domination, or tragedy

### Play as Obi-Wan
Take the role of a Jedi trying to stop catastrophe without giving up hope.

- choose whether to intervene early or wait
- search Padmé’s ship for supplies
- appeal to Anakin’s remaining goodness
- fight through the duel from Obi-Wan’s perspective
- pursue duty, mercy, sacrifice, or a miracle outcome

---

## Screens and Systems Included

### Branching story structure
This is no longer a simple one-path text adventure. The current script contains:

- two distinct character routes
- route-specific dialogue and scene transitions
- optional exploration scenes
- hidden story branches
- multiple route-dependent endings

### Morality and alignment
The player has a morality score that shifts based on decisions.

- **positive morality** pushes the player toward the **Light Side**
- **negative morality** pushes the player toward the **Dark Side**
- values near the center reflect a more **conflicted** character state

Morality affects both presentation and gameplay. In some sections it changes the tone of scenes, opens alternate paths, or influences combat flavor and encounter balance.

### Turn-based combat
The duel sequences use a structured combat loop with player and enemy stats.

Combat actions currently include:

- **Strike**
- **Defend**
- **Force Push**
- **Force Heal**
- **Throw Thermal Detonator** *(when available)*

Combat also includes:

- randomized damage ranges
- critical hits
- Force power costs
- enemy dialogue during battle
- defensive damage reduction
- stun chances on Force-based actions

### Inventory and items
The player can collect and use items during the run.

Examples present in the code include:

- **Lightsaber (Blue)**
- **Jedi Comlink**
- **Thermal Detonator**
- **Bacta Patch**
- **Emergency Flare**

### Terminal presentation
The game is designed to feel dramatic in the command line.

It currently includes:

- typewriter-style text output
- colored scene text and dialogue using `colorama`
- centered titles and boxed chapter headers
- ASCII art for key moments and endings
- a compact player HUD during gameplay

### Audio engine
The project includes an `AudioEngine` powered by `pygame`.

Current behavior in the code:

- attempts to initialize `pygame.mixer`
- plays looping background music if a valid audio file is present
- supports one-shot sound effects in the engine
- fails gracefully if audio is not available

---

## Endings Currently in the Code

The project includes **10 ending scenes** across both routes.

### Anakin endings
1. **The Dark Lord Rises**
2. **Chosen One — Fallen**
3. **Redemption — The Chosen One Returns**
4. **Exile — Neither Jedi Nor Sith**
5. **The Empty Throne**
6. **The Grey Path — A New Order**

### Obi-Wan endings
1. **The Faithful Jedi — Duty Fulfilled**
2. **The Jedi Falls — Darkness Reigns**
3. **The Miracle — Brothers Reunited**
4. **The Long Road — Mercy Endures**

---

## Tech Stack

- **Python 3.8+**
- **colorama** for terminal colors and styled text
- **pygame** for audio playback
- **JSON** for save-state serialization

---

## Installation

Clone the repository and install the required dependencies:

```bash
git clone <your-repo-url>
cd StarWars-Text-Adventure
pip install colorama pygame
```

---

## Run the Game

```bash
python main.py
```

If your system uses `python3`, run:

```bash
python3 main.py
```

---

## Project Structure

```text
StarWars-Text-Adventure/
├── main.py
├── README.md
├── song.mp3                  # optional
└── duel_of_fates_save.json   # generated when applicable
```

### Notes
- `song.mp3` is optional
- if no audio file is present, the game should still run normally
- the save file is JSON-based and only appears when save data exists

---

## Gameplay Flow

### 1. Title screen
The title screen can:

- start a new game
- continue from a detected save file
- quit the game

### 2. Character setup
The player:

1. enters a name
2. selects **Anakin Skywalker** or **Obi-Wan Kenobi**

That choice determines:

- starting morality
- starting inventory
- scene progression
- route-specific choices and endings

### 3. Narrative choices
Throughout the game, the player selects numbered options in the terminal. Those choices shape:

- the immediate dialogue
- morality shifts
- route-specific scene branches
- combat context
- final ending outcomes

### 4. Combat encounters
Combat runs in rounds until one side is defeated. The player can:

- attack directly
- defend for reduced incoming damage
- spend Force points on abilities
- use certain items if available

### 5. End-of-run stats
At the end of a playthrough, the game displays a summary that includes:

- player name
- selected character
- alignment
- morality score
- remaining health
- number of choices made
- items found

---

## Core Code Components

### `AudioEngine`
Handles:

- background music
- sound effect playback
- graceful failure when audio is unavailable

### `PlayerState`
Tracks:

- player name
- selected character
- health and max health
- Force power and max Force power
- morality
- stamina
- inventory
- route flags
- current scene
- choices made

### `Enemy`
Defines combat opponents with:

- name
- health
- max health
- attack power
- defense
- optional combat dialogue

### `run_combat()`
Executes the turn-based duel system and returns a combat result such as:

- `victory`
- `defeat`
- `fled` *(documented in the function, though not currently exposed as a menu option)*

### `GameEngine`
Controls the full gameplay loop by:

- maintaining player state
- dispatching scenes
- updating the active route
- progressing the story until an ending is reached

---

## Save System Status

The code includes a JSON save/load system built around:

```text
duel_of_fates_save.json
```

What is currently true in the code:

- loading an existing save is implemented from the title screen
- a `save_game()` function exists
- manual save and autosave are **not yet fully wired into the active gameplay loop**

That means the project already has save-system groundwork, but loading is currently more complete than active in-game saving.

---

## Known Limitations

A few implementation details are worth noting:

- `save_game()` exists, but saving is not currently triggered during normal play
- the audio engine supports sound effects, but the game flow mainly uses background music
- combat documentation mentions a `fled` outcome, but there is no flee option in the current combat action menu
- some imports and types appear to be unused in the current script

These do not prevent the game from running, but they are good opportunities for polish and expansion.

---

## Roadmap Ideas

Good next upgrades for the project could include:

- wiring manual save and autosave into gameplay
- adding more Mustafar scenes before the duel
- expanding inventory usage outside combat
- introducing more enemies or encounters
- adding sound effects at major story beats
- including difficulty settings
- adding a real flee mechanic in combat
- splitting the project into multiple modules for maintainability
- adding screenshots or terminal GIFs to the README

---

## Why This Project Stands Out

This project blends several appealing ideas into one experience:

- **interactive fiction**
- **Star Wars alternate-history storytelling**
- **RPG-lite combat systems**
- **terminal UI design**
- **cinematic presentation in Python**

It feels like a mix between a command-line game, a branching fan-fiction experience, and a playable “what if?” version of one of the most iconic duels in Star Wars.

---

## Credits

Inspired by:

- **Star Wars: Episode III – Revenge of the Sith**
- the Mustafar duel between **Anakin Skywalker** and **Obi-Wan Kenobi**

Built with:

- **Python**
- **colorama**
- **pygame**

---

## License

Add your preferred license here if you plan to publish the project publicly.

Popular options include:

- MIT License
- Apache 2.0
- GPL-3.0

---

## Support the Project

If you expand this game, consider adding:

- screenshots or terminal captures
- a changelog
- a license file
- badges for Python version and dependencies
- a future releases section

If you’re putting this on GitHub, a polished next step would be adding a `LICENSE` file and a few screenshots near the top of the README.
