"""Blessed input loop with safe screen restoration and pausable missions."""

import os
import sys
import textwrap
import time

os.environ.setdefault("BLESSED_QUERY_TIMEOUT_SECONDS", "0.2")
from blessed import Terminal

from .content import MISSIONS, SPRITES
from .model import World
from .profile import load_profile, record_result
from .render import Pixels, RenderOptions, ascii_world, puzzle_frame, render_frame


CONTROLS = [
    "WASD / arrows    Move and face a direction",
    "J               Saber sweep / Padme's blaster",
    "K               Brief guard; repeat to hold",
    "Space           Dodge two tiles in your facing direction",
    "F               Force pulse / Padme's ion pulse",
    "E               Activate a relay or leave through the lift",
    "H               Apply one bacta charge",
    "Tab / M         Holo-map / recovered mission memory",
    "P               Pause / resume",
    "Q / Escape      Leave mission; confirm with Y",
    "?               Controls and mission briefing",
    "",
    "Gold corners: incoming attack. Move, guard, or dodge.",
    "Cyan consoles: cipher. Gold console: relay. Pink star: memory.",
    "Green cross: bacta. White arch: exit. Orange tiles: lava.",
]


def input_command(key):
    names = {"KEY_UP": "up", "KEY_DOWN": "down", "KEY_LEFT": "left",
             "KEY_RIGHT": "right", "KEY_ESCAPE": "quit", "KEY_ENTER": "enter", "KEY_TAB": "map"}
    if key.name in names:
        return names[key.name]
    return {"w": "up", "s": "down", "a": "left", "d": "right",
            "j": "attack", "k": "guard", " ": "dodge", "f": "power",
            "e": "interact", "h": "heal", "p": "pause", "q": "quit",
            "?": "help", "m": "memory"}.get(str(key).lower(), "")


def _draw(term, rows):
    output = [term.home]
    for index, row in enumerate(rows[:max(1, term.height - 1)]):
        if os.environ.get("NO_COLOR"):
            row = term.strip_seqs(row)
        output.extend((term.move_yx(index, 0), term.clear_eol, " ",
                       term.truncate(row, max(1, term.width - 2)), term.normal))
    output.extend((term.move_yx(min(len(rows), term.height - 1), 0), term.clear_eos))
    sys.stdout.write("".join(output))
    sys.stdout.flush()


def _terminal():
    # Blessed applies NO_COLOR to cursor movement too. Fullscreen needs positioning.
    no_color = os.environ.pop("NO_COLOR", None)
    try:
        return Terminal(force_styling=True)
    finally:
        if no_color is not None:
            os.environ["NO_COLOR"] = no_color


def _available():
    return sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get("TERM") != "dumb"


def _notice():
    print("2D missions need an interactive terminal. Open Terminal, iTerm, or Windows Terminal.")
    print("The branching story and classic combat remain available.")


def _wait_ready(term, world, options):
    while True:
        width = max(20, min(78, term.width - 4))
        rows = [term.bold(term.cyan(world.mission.title)),
                term.dim(world.mission.location), ""]
        rows.extend(textwrap.wrap(world.mission.briefing, width))
        rows.append("")
        rows.extend(term.yellow(row) for row in textwrap.wrap(world.mission.objective, width))
        rows.extend(["", term.bold("FIELD CONTROLS"),
                     "WASD / arrows  Move     J  " + ("Blaster" if world.character == "padme" else "Lightsaber"),
                     "E  Use relay / lift    Space  Dodge    H  Heal",
                     "Tab  Full map          P  Pause        ?  All controls",
                     "", term.dim("Cyan terminal: cipher   Gold terminal: relay"),
                     term.dim("Pink crystal: memory    Green cross: bacta"),
                     term.dim("Gold strike corners: incoming attack. Move or guard."),
                     "", term.bold("ENTER deploy / Q return to story")])
        if len(rows) >= term.height:
            rows = rows[:term.height - 3] + ["", term.bold("ENTER deploy / Q return to story")]
        if term.width < 64 or term.height < 26:
            rows = render_frame(world, term, options)
        _draw(term, rows)
        key = input_command(term.inkey(timeout=0.1))
        if key == "quit":
            return False
        if key == "enter" and term.width >= 64 and term.height >= 26:
            return True


def _pause(term, world, controls=False):
    while True:
        rows = [term.bold(term.cyan("MISSION PAUSED")), "", world.mission.title,
                world.objective_text, ""]
        if controls:
            rows.extend(CONTROLS)
        rows.extend(["", term.bold("P / Enter resume    Q leave mission")])
        _draw(term, rows)
        command = input_command(term.inkey(timeout=0.1))
        if command in ("pause", "enter"):
            return False
        if command == "quit" and _confirm_leave(term):
            return True


def _confirm_leave(term):
    _draw(term, [term.bold("LEAVE THIS MISSION?"), "",
                 "Unfinished mission progress will be lost.",
                 "The story continues without a mission penalty.", "",
                 "Y leave / N, Q, Escape, or Enter resume"])
    while True:
        key = term.inkey(timeout=0.1)
        if str(key).lower() == "y":
            return True
        if str(key).lower() in ("n", "q") or input_command(key) in ("quit", "enter"):
            return False


def _journal(term, world, map_view=False):
    while True:
        if map_view:
            rows = [term.bold(term.cyan("HOLO-MAP / " + world.mission.title)),
                    world.objective_text, ""]
            rows.extend(ascii_world(world, world.width * 2 + 4, world.height + 11))
            rows.extend(["", "@ player  d hostile  C cipher  R relay  ! memory  > exit"])
        else:
            rows = [term.bold(term.magenta("MISSION MEMORY")), "", world.mission.title, ""]
            if world.memory_found:
                rows.append(term.magenta(world.mission.memory[0]))
                rows.extend(textwrap.wrap(world.mission.memory[1], max(20, min(72, term.width - 4))))
            else:
                rows.append("No memory recovered. Look for the pink fragment / ! tile.")
            rows.extend(["", term.dim("RECENT SIGNALS")])
            for message in world.messages:
                rows.extend(textwrap.wrap(message, max(20, min(72, term.width - 4))))
        rows.extend(["", "Enter / Tab / M / Q return to mission"])
        _draw(term, rows)
        if input_command(term.inkey(timeout=0.1)) in ("enter", "map", "memory", "quit"):
            return


def _results(term, world, saved):
    result = world.result()
    if result.outcome == "abandoned":
        return
    title = "MISSION COMPLETE" if result.outcome == "victory" else "SIGNAL LOST"
    rows = [term.bold(term.cyan(title)), "", world.mission.title, "",
            "SCORE {:05d}    HOSTILES {}    TIME {:.1f}s".format(result.score, result.kills, result.seconds),
            "HEALTH {}    CIPHERS {}    MEMORY {}".format(result.health, result.fragments,
                                                          "RECOVERED" if result.memory_found else "UNFOUND"), ""]
    if result.memory_found:
        rows.extend([term.magenta(world.mission.memory[0])])
        rows.extend(textwrap.wrap(world.mission.memory[1], max(20, min(72, term.width - 4))))
        rows.append("")
    if result.outcome == "victory" and not saved:
        rows.extend(["Local record could not be written. The mission result is still valid.", ""])
    rows.append("Enter / Q return")
    _draw(term, rows)
    while input_command(term.inkey(timeout=0.1)) not in ("enter", "quit"):
        pass


def _run(term, world, audio=None, options=None, record=True):
    options = options or RenderOptions()
    previous_mood = getattr(audio, "current_mood", None)
    if audio:
        audio.set_mood(world.mission.mood)
    try:
        if not _wait_ready(term, world, options):
            return world.result()
        previous = time.monotonic()
        while not world.outcome:
            started = time.monotonic()
            small = term.width < 64 or term.height < 26
            _draw(term, puzzle_frame(world, term) if world.puzzle and not small else render_frame(world, term, options))
            command = input_command(term.inkey(timeout=0.04))
            now = time.monotonic()
            if small:
                if command == "quit" and _confirm_leave(term):
                    world.outcome = "abandoned"
                previous = time.monotonic()
                continue
            if command in ("pause", "help"):
                if _pause(term, world, command == "help"):
                    world.outcome = "abandoned"
                previous = time.monotonic()
                continue
            if command in ("map", "memory"):
                _journal(term, world, command == "map")
                previous = time.monotonic()
                continue
            if command == "quit" and not world.puzzle:
                if _confirm_leave(term):
                    world.outcome = "abandoned"
                previous = time.monotonic()
                continue
            world.update(now - previous)
            world.command("attack" if world.puzzle and command == "enter" else command)
            previous = now
            if audio:
                for cue in dict.fromkeys(world.cues):
                    audio.play_sfx_cue(cue, instant=True)
            world.cues.clear()
            remaining = 0.04 - (time.monotonic() - started)
            if remaining > 0:
                time.sleep(remaining)
        saved = record_result(world.result(), world.character) if record else True
        _results(term, world, saved)
        return world.result()
    finally:
        if audio and previous_mood:
            audio.set_mood(previous_mood)


def play_mission(mission="ashwalk", character="anakin", audio=None, options=None, **kwargs):
    """Return a Result or None when interactive terminal access is unavailable."""
    if not _available():
        _notice()
        return None
    term = _terminal()
    options = options or RenderOptions()
    if os.environ.get("NO_COLOR"):
        options.ascii_mode = True
    world = World(mission, character, **kwargs)
    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        try:
            return _run(term, world, audio, options)
        except KeyboardInterrupt:
            world.outcome = "abandoned"
            return world.result()


def arcade_menu(character="anakin", audio=None, options=None, difficulty="standard"):
    """An independent arcade: records persist, story stats never change here."""
    if not _available():
        _notice()
        return
    term = _terminal()
    options = options or RenderOptions()
    if os.environ.get("NO_COLOR"):
        options.ascii_mode = True
    characters = ["anakin", "obiwan", "padme"]
    difficulties = ["story", "standard", "veteran"]
    if character not in characters:
        character = "anakin"
    keys = ["ashwalk", "archive", "gauntlet"]
    selected = 1 if character == "padme" else 0
    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        try:
            while True:
                mission = MISSIONS[keys[selected]]
                rows = [term.bold(term.cyan("DUEL OF FATES / HOLO-ARCADE")),
                        term.dim("FIELD MISSIONS + COMBAT TRIALS"), ""]
                if options.ascii_mode:
                    rows.extend(["   [A]       [O]       [P]", "  ANAKIN    OBI-WAN    PADME"])
                else:
                    portrait = Pixels(22, 6)
                    for i, char in enumerate(characters):
                        portrait.sprite(i * 8, 0, SPRITES[char])
                    rows.extend(portrait.terminal_lines())
                rows.extend(["", "PILOT {}    DIFFICULTY {}".format(character.upper(), difficulty.upper()),
                             "DISPLAY {}    MOTION {}".format("ASCII" if options.ascii_mode else "PIXEL",
                                                               "REDUCED" if options.reduced_motion else "FULL"), ""])
                profile = load_profile()
                for i, key in enumerate(keys):
                    prefix = "> " if i == selected else "  "
                    value = prefix + "{}  {}".format(i + 1, MISSIONS[key].title)
                    rows.append(term.bold(term.yellow(value)) if i == selected else value)
                rows.extend(["", term.dim(mission.location)])
                rows.extend(textwrap.wrap(mission.briefing, max(20, min(76, term.width - 4))))
                record = profile.get(mission.key + ":" + character, {})
                rows.extend(["", "PERSONAL BEST {}    CLEARS {}    MEMORY {}".format(
                    record.get("best", 0), record.get("wins", 0), "FOUND" if record.get("memory") else "UNFOUND"),
                    "", "Up/down select | Enter deploy | C pilot | N difficulty",
                    "V pixel/ASCII | R reduced motion | Q back"])
                _draw(term, rows)
                key = term.inkey(timeout=0.1)
                command = input_command(key)
                raw = str(key).lower()
                if command == "quit":
                    return
                if command in ("up", "down"):
                    selected = (selected + (1 if command == "down" else -1)) % len(keys)
                elif raw in ("1", "2", "3"):
                    selected = int(raw) - 1
                elif raw == "c":
                    character = characters[(characters.index(character) + 1) % len(characters)]
                elif raw == "n":
                    difficulty = difficulties[(difficulties.index(difficulty) + 1) % len(difficulties)]
                elif raw == "v":
                    options.ascii_mode = True if os.environ.get("NO_COLOR") else not options.ascii_mode
                elif raw == "r":
                    options.reduced_motion = not options.reduced_motion
                elif command == "enter":
                    _run(term, World(mission.key, character, difficulty), audio, options)
        except KeyboardInterrupt:
            return


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Duel of Fates pixel terminal missions")
    parser.add_argument("--mission", choices=tuple(MISSIONS))
    parser.add_argument("--character", choices=("anakin", "obiwan", "padme"), default="anakin")
    parser.add_argument("--difficulty", choices=("story", "standard", "veteran"), default="standard")
    parser.add_argument("--ascii", action="store_true")
    parser.add_argument("--reduced-motion", action="store_true")
    args = parser.parse_args()
    options = RenderOptions(args.ascii, args.reduced_motion)
    if args.mission:
        play_mission(args.mission, args.character, options=options, difficulty=args.difficulty)
    else:
        arcade_menu(args.character, options=options, difficulty=args.difficulty)
