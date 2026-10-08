# Development & Sources

## Structure

`main.py` owns the 45-scene branching campaign, save data, relationship systems, codex, memories, and audio. `holotactics` adds a separate action simulation and terminal frontend:

| Module | Responsibility |
| --- | --- |
| `content.py` | Authored mission layouts, briefings, memories, sprites, and palette |
| `model.py` | Collision, attacks, projectiles, enemy decisions, objectives, waves, and relay puzzle |
| `render.py` | Half-block pixels, camera, HUD, monochrome tile view, and puzzle rendering |
| `terminal.py` | Blessed input, fullscreen restoration, pause, briefing, records menu, and CLI |
| `profile.py` | Atomic local arcade record writes |

The simulation has no terminal or audio calls. Its clock advances only through `World.update(dt)`. Input commands are separate from simulation updates, which makes combat behavior testable without a keyboard or sound device. Enemy navigation uses the third-party A* implementation rather than a custom pathfinder.

Maps and six-by-six sprites are original project assets. Every authored objective and spawn is reachable without crossing lava. Campaign duels stay in `run_combat`, the original turn-based system. Only Anakin's control-room search and Padme's Senate investigation call the optional mission frontend, after an explicit player selection. Field missions use independent encounter stats and apply explicit rewards after completion; failure cannot deplete campaign resources.

Fullscreen, cursor visibility, and keyboard modes use context managers. Pause, slicing, and undersized terminals freeze the simulation. `NO_COLOR` selects ASCII rendering; cursor positioning remains enabled. Terminal capability negotiation has a short default timeout to keep startup responsive.

## Verification

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
python3 tools/terminal_smoke.py
```

Regression tests cover objective reachability, pathfinding, range and facing, wall collisions, telegraphs, guard, dodge, pulses, ranged attacks, lava, waves, cipher checksums, display bounds, old saves, records, optional mission boundaries, title-menu stability, choice-based duels, continuous MP3 playback, audio fallback, and overlay restoration.

`terminal_smoke.py` launches actual game processes inside a pseudo-terminal on macOS/Linux. It sends movement and combat inputs, pauses, resizes below and above the supported minimum, and exits with confirmation. `story_smoke.py` checks the start menu and all three route entries using disposable save files, then opens and closes Codex and Memories to verify restored numbered choices. `pyte` interprets captured output; Pillow exports the actual terminal frames used in the README.

No save files, profiles, downloaded dependencies, or virtual environments belong in version control. `requirements.txt` describes runtime dependencies; `requirements-dev.txt` adds only local verification and screenshot tooling.

## Research & Credits

The expansion uses these primary technical references:

- [Blessed keyboard input](https://blessed.readthedocs.io/en/latest/keyboard.html): immediate key reads, key names, cbreak mode, and fullscreen context managers.
- [Blessed terminal API](https://blessed.readthedocs.io/en/latest/api/terminal.html): cursor positioning, styling, width measurement, and screen restoration.
- [python-pathfinding](https://github.com/brean/python-pathfinding): A* grids and cardinal enemy navigation.
- [pygame mixer documentation](https://www.pygame.org/docs/ref/mixer.html): sound buffers, reserved channels, loops, fades, and streamed custom music.
- [python-tcod documentation](https://python-tcod.readthedocs.io/en/latest/): reviewed as a roguelike toolkit. This implementation uses Blessed and pathfinding so encounters remain inside the actual terminal.

Design references include [Supergiant's Hades overview](https://www.supergiantgames.com/games/hades/) for combining repeatable action encounters with character-driven storytelling, and [Freehold's Caves of Qud roadmap](https://cavesofqud.com/roadmap/) for placing meaningful histories in relics and discoverable locations. Duel of Fates applies those broad ideas through its own missions, mechanics, layouts, text, and sprites. No code, art, dialogue, or music from those games is bundled.

Star Wars names and settings remain the property of their respective rights holders. This repository is an unofficial fan project.
