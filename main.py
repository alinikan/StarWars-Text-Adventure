"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     STAR WARS: DUEL OF FATES                               ║
║              A Text-Based Adventure Game · Mustafar Arc                     ║
║                                                                            ║
║  An immersive, choice-driven narrative game set during the climactic duel   ║
║  between Anakin Skywalker and Obi-Wan Kenobi on Mustafar. Every decision   ║
║  shapes your morality, affects combat outcomes, and determines which of    ║
║  multiple endings you unlock.                                              ║
║                                                                            ║
║  Features:                                                                 ║
║    • Morality system that tracks light/dark alignment                      ║
║    • Turn-based combat with Force powers and stamina management            ║
║    • Three playable routes: Anakin, Obi-Wan, and Padmé                    ║
║    • Inventory system with collectible items                               ║
║    • Relationship, clarity, codex, and secret-discovery systems            ║
║    • Codex and memory shard menus available during play                    ║
║    • Dynamic narrative that reacts to your choices                         ║
║    • Multiple endings (including secret paths)                             ║
║    • Atmospheric typing effects, animated set pieces, and pixel portraits  ║
║    • Dynamic music moods and synthesized terminal SFX                      ║
║    • Autosave and manual save/load support                                 ║
║                                                                            ║
║  Requirements: Python 3.8+, colorama, pygame                               ║
║  Install:  pip install colorama pygame                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import random
import textwrap
import math
import struct
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable
from enum import Enum

# Third-party imports for terminal colors and audio
from colorama import Fore, Back, Style, init
import pygame

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

init(autoreset=True)  # Auto-reset colorama styles after each print

# Terminal width used for centering and horizontal rules
TERMINAL_WIDTH = 70

# Typing speed: seconds per character for the typewriter effect
TYPE_SPEED = 0.02
TYPE_SPEED_FAST = 0.008
ANIMATION_DELAY = 0.08

# Set DUEL_OF_FATES_FAST=1 to skip typewriter/animation delays during testing.
FAST_MODE = os.environ.get("DUEL_OF_FATES_FAST", "").lower() in {"1", "true", "yes", "on"}

# Save file location
SAVE_FILE = "duel_of_fates_save.json"


def sleep_scaled(seconds: float):
    """Sleep unless fast mode is enabled."""
    if not FAST_MODE:
        time.sleep(seconds)

# ──────────────────────────────────────────────────────────────────────────────
# AUDIO ENGINE
# Handles background music and sound effects using pygame.mixer.
# Gracefully degrades if audio files are missing — the game still runs.
# ──────────────────────────────────────────────────────────────────────────────


class AudioEngine:
    """Manages optional background music, mood changes, and synthesized SFX."""

    def __init__(self):
        self.enabled = False
        self.current_music = None
        self.current_mood = None
        self.mood_volume = {
            "title": 0.35,
            "tension": 0.42,
            "dark": 0.48,
            "duel": 0.58,
            "hope": 0.38,
            "tragedy": 0.30,
            "silence": 0.0,
        }
        try:
            pygame.mixer.pre_init(44100, -16, 1, 512)
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            pass  # Audio unavailable — continue silently

    def play_music(self, filename: str, loops: int = -1, volume: float = 0.5):
        """
        Play background music on loop.

        Args:
            filename: Path to the audio file (mp3/ogg).
            loops: -1 for infinite loop, 0 for play once.
            volume: Float between 0.0 and 1.0.
        """
        if not self.enabled:
            return
        try:
            if self.current_music == filename and pygame.mixer.music.get_busy():
                pygame.mixer.music.set_volume(volume)
                return
            pygame.mixer.music.load(filename)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops)
            self.current_music = filename
        except pygame.error:
            pass

    def set_mood(self, mood: str):
        """Switch music intensity for the current scene."""
        if not self.enabled:
            return
        if mood == self.current_mood:
            return
        self.current_mood = mood
        if mood == "silence":
            self.stop_music()
            return
        volume = self.mood_volume.get(mood, 0.4)
        if os.path.exists("song.mp3"):
            self.play_music("song.mp3", volume=volume)
        elif pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(volume)

    def play_sfx(self, filename: str, volume: float = 0.7):
        """Play a one-shot sound effect."""
        if not self.enabled:
            return
        try:
            sfx = pygame.mixer.Sound(filename)
            sfx.set_volume(volume)
            sfx.play()
        except pygame.error:
            pass

    def play_tone(self, frequency: int, duration: float = 0.08, volume: float = 0.18):
        """Play a tiny synthesized tone without requiring sound-effect files."""
        if not self.enabled or FAST_MODE:
            return
        try:
            sample_rate = 44100
            sample_count = int(sample_rate * duration)
            amplitude = int(32767 * max(0.0, min(volume, 1.0)))
            raw = bytearray()
            for i in range(sample_count):
                envelope = 1.0 - (i / max(1, sample_count))
                sample = int(amplitude * envelope * math.sin(2 * math.pi * frequency * i / sample_rate))
                raw.extend(struct.pack("<h", sample))
            pygame.mixer.Sound(buffer=bytes(raw)).play()
        except (pygame.error, ValueError):
            pass

    def play_sfx_cue(self, cue: str):
        """Play a named synthesized UI/story cue."""
        cues = {
            "select": [(660, 0.035, 0.08)],
            "save": [(523, 0.05, 0.10), (784, 0.06, 0.10)],
            "secret": [(392, 0.07, 0.12), (587, 0.07, 0.12), (880, 0.12, 0.14)],
            "memory": [(330, 0.08, 0.10), (494, 0.10, 0.10)],
            "light": [(587, 0.07, 0.11), (880, 0.09, 0.12)],
            "dark": [(220, 0.10, 0.14), (165, 0.12, 0.14)],
            "damage": [(120, 0.08, 0.20)],
            "heal": [(440, 0.06, 0.10), (660, 0.08, 0.10)],
            "clash": [(260, 0.05, 0.16), (740, 0.05, 0.12)],
            "broadcast": [(440, 0.04, 0.08), (554, 0.04, 0.08), (659, 0.08, 0.10)],
        }
        for frequency, duration, volume in cues.get(cue, []):
            self.play_tone(frequency, duration, volume)
            sleep_scaled(duration * 0.35)

    def stop_music(self):
        """Fade out and stop background music."""
        if self.enabled:
            pygame.mixer.music.fadeout(2000)
            self.current_music = None


audio = AudioEngine()


ACTIVE_ENGINE = None


class LoadRequested(Exception):
    """Raised when the player requests an immediate manual load."""


class QuitRequested(Exception):
    """Raised when the player chooses to leave the game from a prompt."""


# ──────────────────────────────────────────────────────────────────────────────
# TERMINAL UI UTILITIES
# These functions create the atmospheric presentation layer — typing effects,
# styled boxes, centered text, color-coded dialogue, etc.
# ──────────────────────────────────────────────────────────────────────────────


def clear_screen():
    """Clear the terminal screen (cross-platform)."""
    os.system("cls" if os.name == "nt" else "clear")


def type_text(text: str, speed: float = TYPE_SPEED, color: str = ""):
    """
    Print text character-by-character for a typewriter effect.
    Wraps long lines to fit the terminal width.

    Args:
        text: The string to display.
        speed: Delay in seconds between each character.
        color: A colorama color/style prefix (e.g. Fore.RED).
    """
    wrapped = textwrap.fill(text, width=TERMINAL_WIDTH - 4)
    for char in wrapped:
        sys.stdout.write(f"{color}{char}")
        sys.stdout.flush()
        if char in ".!?":
            sleep_scaled(speed * 8)  # Pause longer at sentence boundaries
        elif char == ",":
            sleep_scaled(speed * 4)
        elif char == "\n":
            sleep_scaled(speed * 2)
        else:
            sleep_scaled(speed)
    print(Style.RESET_ALL)


def type_dialogue(speaker: str, text: str, color: str = Fore.WHITE):
    """
    Display a line of dialogue with the speaker's name highlighted.

    Args:
        speaker: Character name (displayed in bold).
        text: The dialogue line.
        color: Color for the speaker's name.
    """
    print()
    sys.stdout.write(f"  {color}{Style.BRIGHT}{speaker}:{Style.RESET_ALL} ")
    sys.stdout.flush()
    # Wrap the dialogue portion, indenting continuation lines
    indent = " " * (len(speaker) + 4)
    wrapped = textwrap.fill(f'"{text}"', width=TERMINAL_WIDTH - 6,
                            subsequent_indent=indent)
    # Skip the first character since fill re-includes the quote
    for char in wrapped:
        sys.stdout.write(f"{Fore.WHITE}{char}")
        sys.stdout.flush()
        sleep_scaled(TYPE_SPEED_FAST)
    print(Style.RESET_ALL)


def horizontal_rule(char: str = "═", color: str = Fore.YELLOW):
    """Print a colored horizontal line spanning the terminal width."""
    print(f"{color}{char * TERMINAL_WIDTH}{Style.RESET_ALL}")


def centered(text: str, color: str = Fore.WHITE):
    """Print text centered within the terminal width."""
    print(f"{color}{text:^{TERMINAL_WIDTH}}{Style.RESET_ALL}")


def header_box(title: str, subtitle: str = "", color: str = Fore.YELLOW):
    """
    Draw a decorative box around a title, used for scene headers
    and chapter transitions.
    """
    print()
    print(f"{color}╔{'═' * (TERMINAL_WIDTH - 2)}╗")
    print(f"║{title:^{TERMINAL_WIDTH - 2}}║")
    if subtitle:
        print(f"║{subtitle:^{TERMINAL_WIDTH - 2}}║")
    print(f"╚{'═' * (TERMINAL_WIDTH - 2)}╝{Style.RESET_ALL}")
    print()


def status_bar(player: "PlayerState"):
    """
    Render a compact HUD showing the player's current stats.
    Displayed before every choice to keep the player informed.
    """
    # Build the health bar: ██░░░░░░░░ style
    hp_filled = int((player.health / player.max_health) * 10)
    hp_bar = f"{'█' * hp_filled}{'░' * (10 - hp_filled)}"
    hp_color = Fore.GREEN if player.health > 60 else Fore.YELLOW if player.health > 30 else Fore.RED

    # Build the Force bar
    fp_filled = int((player.force_power / player.max_force) * 10)
    fp_bar = f"{'█' * fp_filled}{'░' * (10 - fp_filled)}"

    # Morality indicator: light side vs dark side
    if player.morality >= 3:
        moral_label = f"{Fore.CYAN}✦ Light Side"
    elif player.morality <= -3:
        moral_label = f"{Fore.RED}✦ Dark Side"
    else:
        moral_label = f"{Fore.YELLOW}✦ Conflicted"

    print(f"\n{Fore.WHITE}{Style.DIM}┌{'─' * (TERMINAL_WIDTH - 2)}┐")
    print(f"│ {hp_color}HP [{hp_bar}] {player.health}/{player.max_health}"
          f"  {Fore.BLUE}FP [{fp_bar}] {player.force_power}/{player.max_force}"
          f"  {moral_label}{Style.RESET_ALL}{Style.DIM}")
    print(f"│ {Fore.GREEN}STA {player.stamina:>3}/100"
          f"  {Fore.MAGENTA}Clarity {getattr(player, 'clarity', 0):>2}"
          f"  {Fore.YELLOW}Secrets {getattr(player, 'secrets_found', 0):>2}"
          f"  {Fore.BLUE}Mem {len(getattr(player, 'memory_shards', [])):>2}"
          f"{Style.RESET_ALL}{Style.DIM}")
    if player.inventory:
        items = ", ".join(player.inventory)
        print(f"{Style.DIM}│ {Fore.MAGENTA}Inventory: {items}{Style.RESET_ALL}{Style.DIM}")
    print(f"└{'─' * (TERMINAL_WIDTH - 2)}┘{Style.RESET_ALL}")


def show_choices(choices: list[str]) -> int:
    """
    Display numbered choices and return the player's valid selection.

    In addition to numeric choices, the player can enter:
      S = manual save
      L = manual load
      C = codex/status menu
      M = memory shards
      Q = save-and-quit / quit without saving
      H = show help

    Args:
        choices: List of choice description strings.

    Returns:
        The 1-based index of the selected choice.
    """
    print()
    for i, choice in enumerate(choices, 1):
        print(f"  {Fore.YELLOW}{Style.BRIGHT}[{i}]{Style.RESET_ALL} {choice}")
    print(f"\n  {Fore.WHITE}{Style.DIM}Commands: [S]ave  [L]oad  [C]odex  [M]emories  [Q]uit{Style.RESET_ALL}\n")

    while True:
        raw = input(f"  {Fore.YELLOW}▸ {Style.RESET_ALL}").strip()
        lowered = raw.lower()

        if lowered in {"s", "save"}:
            if ACTIVE_ENGINE is None:
                print(f"  {Fore.RED}No active game to save.{Style.RESET_ALL}")
                continue
            save_game(ACTIVE_ENGINE.player)
            audio.play_sfx_cue("save")
            continue

        if lowered in {"l", "load"}:
            saved = load_game()
            if saved is None:
                print(f"  {Fore.RED}No save file found.{Style.RESET_ALL}")
                continue
            if ACTIVE_ENGINE is not None and not getattr(ACTIVE_ENGINE, f"scene_{saved.current_scene}", None):
                print(f"  {Fore.RED}Save file is outdated or corrupted. Clearing it now.{Style.RESET_ALL}")
                delete_save()
                continue
            if ACTIVE_ENGINE is not None:
                ACTIVE_ENGINE.player = saved
            print(f"\n  {Fore.GREEN}✓ Save loaded. Resuming {saved.name or 'your adventure'} at '{saved.current_scene}'.{Style.RESET_ALL}")
            pause()
            raise LoadRequested()

        if lowered in {"h", "help", "?"}:
            print(f"  {Fore.WHITE}{Style.DIM}Type a choice number, or use S to save, L to load, C for codex, M for memories, or Q to quit.{Style.RESET_ALL}")
            continue

        if lowered in {"c", "codex", "journal", "status"}:
            if ACTIVE_ENGINE is None:
                print(f"  {Fore.RED}No active codex yet.{Style.RESET_ALL}")
                continue
            show_codex_menu(ACTIVE_ENGINE.player)
            continue

        if lowered in {"m", "memory", "memories", "shards"}:
            if ACTIVE_ENGINE is None:
                print(f"  {Fore.RED}No memory shards yet.{Style.RESET_ALL}")
                continue
            show_memory_shards(ACTIVE_ENGINE.player)
            continue

        if lowered in {"q", "quit", "exit"}:
            if ACTIVE_ENGINE is None:
                raise QuitRequested()
            while True:
                confirm = input(
                    f"  {Fore.YELLOW}Save before quitting? [Y]es / [N]o / [C]ancel ▸ {Style.RESET_ALL}"
                ).strip().lower()
                if confirm in {"y", "yes", ""}:
                    save_game(ACTIVE_ENGINE.player)
                    raise QuitRequested()
                if confirm in {"n", "no"}:
                    raise QuitRequested()
                if confirm in {"c", "cancel"}:
                    break
                print(f"  {Fore.RED}Please enter Y, N, or C.{Style.RESET_ALL}")
            continue

        try:
            selection = int(raw)
            if 1 <= selection <= len(choices):
                audio.play_sfx_cue("select")
                return selection
            print(f"  {Fore.RED}Choose a number between 1 and {len(choices)}.{Style.RESET_ALL}")
        except ValueError:
            print(f"  {Fore.RED}Enter a number or use S/L/Q.{Style.RESET_ALL}")


def pause(prompt: str = "Press Enter to continue..."):
    """Wait for the player to press Enter before proceeding."""
    input(f"\n  {Fore.WHITE}{Style.DIM}{prompt}{Style.RESET_ALL}")


def alignment_label(player) -> str:
    """Return a compact alignment label for menus and end screens."""
    if player.morality >= 5:
        return "Beacon of Light"
    if player.morality >= 2:
        return "Light Side"
    if player.morality >= -1:
        return "Conflicted"
    if player.morality >= -4:
        return "Dark Side"
    return "Consumed by Darkness"


def show_codex_menu(player):
    """Display discovered lore, route meters, and run status."""
    clear_screen()
    header_box("CODEX & STATUS", player.name or "Unknown Traveler", Fore.BLUE)
    status_bar(player)
    print()
    print(f"  {Fore.WHITE}{Style.DIM}{'Character:':<20}{Style.RESET_ALL}{Fore.YELLOW}{player.character.title() or 'Unchosen'}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}{Style.DIM}{'Alignment:':<20}{Style.RESET_ALL}{Fore.YELLOW}{alignment_label(player)}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}{Style.DIM}{'Padme Bond:':<20}{Style.RESET_ALL}{Fore.MAGENTA}{player.bond_padme}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}{Style.DIM}{'Brotherhood Bond:':<20}{Style.RESET_ALL}{Fore.CYAN}{player.bond_brotherhood}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}{Style.DIM}{'Clarity:':<20}{Style.RESET_ALL}{Fore.MAGENTA}{player.clarity}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}{Style.DIM}{'Secrets Found:':<20}{Style.RESET_ALL}{Fore.YELLOW}{player.secrets_found}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}{Style.DIM}{'Memory Shards:':<20}{Style.RESET_ALL}{Fore.BLUE}{len(getattr(player, 'memory_shards', []))}{Style.RESET_ALL}")

    print()
    horizontal_rule("─", Fore.BLUE + Style.DIM)
    centered("DISCOVERED CODEX", Fore.BLUE + Style.BRIGHT)
    horizontal_rule("─", Fore.BLUE + Style.DIM)
    if player.codex:
        for i, entry in enumerate(player.codex, 1):
            print(f"  {Fore.BLUE}{i:>2}.{Style.RESET_ALL} {entry}")
    else:
        print(f"  {Fore.WHITE}{Style.DIM}No codex entries discovered yet.{Style.RESET_ALL}")
    pause("Press Enter to return to the choice...")


def show_memory_shards(player):
    """Display unlocked memory fragments."""
    clear_screen()
    header_box("MEMORY SHARDS", "Fragments the Force has not let go", Fore.MAGENTA)
    shards = getattr(player, "memory_shards", [])
    if not shards:
        type_text("No memory shards have surfaced yet. Look for visions, confessions, "
                  "hidden recordings, and moments where mercy costs something.",
                  color=Fore.WHITE + Style.DIM,
                  speed=TYPE_SPEED_FAST)
        pause("Press Enter to return to the choice...")
        return

    for i, shard in enumerate(shards, 1):
        if isinstance(shard, dict):
            title = shard.get("title", f"Shard {i}")
            body = shard.get("body", "")
        else:
            title = f"Shard {i}"
            body = str(shard)
        print(f"\n  {Fore.MAGENTA}{Style.BRIGHT}{i}. {title}{Style.RESET_ALL}")
        print(textwrap.fill(body, width=TERMINAL_WIDTH - 6, initial_indent="  ", subsequent_indent="  "))
    audio.play_sfx_cue("memory")
    pause("Press Enter to return to the choice...")


def animate_frames(frames: list[str], color: str = Fore.WHITE,
                   cycles: int = 1, delay: float = ANIMATION_DELAY,
                   clear_between: bool = True):
    """Render simple terminal animation from ASCII frame strings."""
    if not frames:
        return
    if FAST_MODE or len(frames) == 1:
        print(f"{color}{frames[-1]}{Style.RESET_ALL}")
        return

    for _ in range(cycles):
        for frame in frames:
            if clear_between:
                clear_screen()
            print(f"{color}{frame}{Style.RESET_ALL}")
            sleep_scaled(delay)


def play_set_piece(name: str, cycles: int = 1, delay: float = 0.14):
    """Play a named terminal set piece with a matching audio cue."""
    frames, color, title = SET_PIECES.get(name, ([], Fore.WHITE, name.upper()))
    if not frames:
        return
    audio.play_sfx_cue("broadcast" if "signal" in name else "clash")
    cinematic_beat(title, "", color)
    animate_frames(frames, color, cycles=cycles, delay=delay, clear_between=False)


def cinematic_beat(title: str, art: str = "", color: str = Fore.YELLOW,
                   subtitle: str = ""):
    """Show a short cinematic title card with optional art."""
    clear_screen()
    if art:
        print(f"{color}{art}{Style.RESET_ALL}")
    header_box(title, subtitle, color)


def show_portrait(name: str, color: str = Fore.WHITE):
    """Display a small pixel-style character portrait if one exists."""
    portrait_art = CHARACTER_PORTRAITS.get(name.lower())
    if portrait_art:
        print(f"{color}{portrait_art}{Style.RESET_ALL}")


def show_secret(title: str, body: str):
    """Display a dramatic secret discovery card."""
    print()
    horizontal_rule("░", Fore.MAGENTA)
    centered(f"SECRET: {title}", Fore.MAGENTA + Style.BRIGHT)
    horizontal_rule("░", Fore.MAGENTA)
    type_text(body, color=Fore.WHITE + Style.DIM, speed=TYPE_SPEED_FAST)


# ──────────────────────────────────────────────────────────────────────────────
# ASCII ART
# Large-format text art for the title screen and key dramatic moments.
# ──────────────────────────────────────────────────────────────────────────────

TITLE_ART = r"""
        ____  __  _______ __       ____  ______   _________  ____________
       / __ \/ / / / ___// /      / __ \/ ____/  / ____/   |/_  __/ ____/
      / / / / / / / __/ / /      / / / / /_     / /_  / /| | / / / __/   
     / /_/ / /_/ / /___/ /___   / /_/ / __/    / __/ / ___ |/ / / /___   
    /_____/\____/_____/_____/   \____/_/      /_/   /_/  |_/_/ /_____/   
"""

MUSTAFAR_ART = r"""
               .        *          .     .          .
        .            .        .                    .
                ___________
            .  /           \  .        .
              / ~~ ≈≈≈ ~~   \           *
    .        / ≈≈≈≈≈≈≈≈≈≈≈≈≈ \    .
            /  🔥 MUSTAFAR 🔥  \
           / ≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈ \       .
    ~~~~~~/~~~~~~~~~~~~~~~~~~~~~~~~~\~~~~~~
    ≈≈≈≈≈≈≈≈≈≈≈≈  LAVA  ≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈
    ≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈
"""

LIGHTSABER_CLASH = r"""
                \         /
                 \   ⚡   /
                  \  |  /
                   \ | /
            ════════╳════════
                   / | \
                  /  |  \
                 /   ⚡   \
                /         \
"""

ENDING_ART_DARK = r"""
        ╔═══════════════════════════════════╗
        ║    THE DARK SIDE CONSUMES YOU     ║
        ║  You are now... DARTH VADER       ║
        ╚═══════════════════════════════════╝
"""

ENDING_ART_LIGHT = r"""
        ╔═══════════════════════════════════╗
        ║    THE LIGHT ENDURES              ║
        ║  The Force will be with you...    ║
        ║                        always.    ║
        ╚═══════════════════════════════════╝
"""

ENDING_ART_REDEMPTION = r"""
        ╔═══════════════════════════════════╗
        ║   ✦  A NEW PATH UNFOLDS  ✦       ║
        ║  Neither Jedi nor Sith —          ║
        ║  Something the galaxy has         ║
        ║  never seen before.               ║
        ╚═══════════════════════════════════╝
"""

HOLOCRON_ART = r"""
                 .-.
              .-'   '-.
           .-'  .- -.  '-.
          /   .'  _  '.   \
         ;   /   (_)   \   ;
         |  ;  .-'''-.  ;  |
         ;   \  '---'  /   ;
          \   '.     .'   /
           '-.  '---'  .-'
              '-.   .-'
                 '-'
"""

PALPATINE_HOLO_ART = r"""
             ______________________
            / .------------------. \
           / /  ////  ////  //// \ \
          | |     HOLO TRANSMIT    | |
          | |       _.-''''-._     | |
          | |     .'  .--.    '.   | |
          | |    /   (    )     \  | |
          | |    |    '--'      |  | |
           \ \    '._        _.'  / /
            \ '------------------' /
             '--------------------'
"""

DROID_ART = r"""
              .----.
             / .--. \
            | |K4S| |
            | '--' |
         ___|  __  |___
        / _ \_/  \_/_  \
       /_/ \___/\___/ \_\
           /_/    \_\
"""

JEDI_BEACON_ART = r"""
              \  |  /
            '.  \|/  .'
          ----  ( )  ----
            .'  /|\  '.
              /  |  \
           BEACON FREQUENCY
"""

MEMORY_SHARD_ART = r"""
             /\
            /  \
           / /\ \
          / /  \ \
         /_/____\_\
           \    /
            \  /
             \/
"""

CHARACTER_PORTRAITS = {
    "anakin": r"""
          .------.
         /  _  _  \
        |  (o)(o)  |
        |    __    |
        |  .'  '.  |
         \  `--'  /
          '------'
        ANAKIN SKYWALKER
    """,
    "obi-wan": r"""
          .------.
         /  -  -  \
        |  (o)(o)  |
        |    /\    |
        |  \____/  |
         \  ____  /
          '------'
         OBI-WAN KENOBI
    """,
    "padme": r"""
          .------.
         /  .--.  \
        |  (o  o)  |
        |    --    |
        |  .____.  |
         \        /
          '------'
             PADME
    """,
    "palpatine": r"""
          .------.
         /  .--.  \
        |  / .. \  |
        |  \_--_/  |
        |   /__\   |
         \  DARK  /
          '------'
          SIDIOUS
    """,
    "qui-gon": r"""
          .------.
         /  ~  ~  \
        |  (o)(o)  |
        |    __    |
        |  \____/  |
         \  FORCE /
          '------'
          QUI-GON
    """,
    "k-4s": DROID_ART,
}

MUSTAFAR_LAVA_FRAMES = [
    r"""
      ~~~~~~~~^^^^~~~~~~^^^^~~~~~~~~
    ~~  LAVA   ~~  ASH   ~~  LAVA  ~~
      ^^^^~~~~~~^^^^~~~~~~^^^^~~~~
    """,
    r"""
      ^^^^~~~~~~^^^^~~~~~~^^^^~~~~
    ~~  ASH    ~~  LAVA  ~~  ASH   ~~
      ~~~~~~~~^^^^~~~~~~^^^^~~~~~~~~
    """,
]

SABER_LOCK_FRAMES = [
    r"""
             blue hum          blue hum
                 \              /
                  \            /
                   \          /
                    \        /
                     \      /
                      \    /
                       \  /
                        \/
    """,
    r"""
             blue hum  >>>><<<<  blue hum
                 \        XX        /
                  \      XXXX      /
                   \      XX      /
                    \            /
                     \          /
                      \        /
    """,
    LIGHTSABER_CLASH,
]

FORCE_VISION_FRAMES = [
    r"""
              . . . . .
           .             .
         .    A MASK       .
         .   NOT YET       .
           .             .
              . . . . .
    """,
    r"""
              . . . . .
           .             .
         .   A CHILD       .
         .   HIDDEN        .
           .             .
              . . . . .
    """,
    r"""
              . . . . .
           .             .
         .   A MASTER      .
         .   AFRAID        .
           .             .
              . . . . .
    """,
]

SENATE_SIGNAL_FRAMES = [
    r"""
       [ CORUSCANT EMERGENCY CHANNEL ]
       . . . . . . . . . . . . . . .
       SIGNAL: searching
       STATUS: unstable
    """,
    r"""
       [ CORUSCANT EMERGENCY CHANNEL ]
       >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
       SIGNAL: locked
       STATUS: intercepted
    """,
    r"""
       [ CORUSCANT EMERGENCY CHANNEL ]
       >>>>>>>>> FREE SENATE <<<<<<<<
       SIGNAL: live
       STATUS: dangerous
    """,
]

MEDICAL_SCAN_FRAMES = [
    r"""
       LIFE SIGN SCAN
       Padme:  ||||||||....
       Twins:  ||||||||||||
       Risk:   rising
    """,
    r"""
       LIFE SIGN SCAN
       Padme:  ||||||||||..
       Twins:  ||||||||||||
       Risk:   contained
    """,
]

LAVA_CHASE_FRAMES = [
    r"""
       CATWALK A-17      >>> unstable
       ==============================
              \   lava surge   /
               \______________/
    """,
    r"""
       CATWALK A-17      >>> failing
       ==========  ==========  ======
             \  LAVA SURGE  /
              \____________/
    """,
    r"""
       CATWALK A-17      >>> jump
       =====      =====      =====
            \   FIRE BELOW   /
             \______________/
    """,
]

MASK_FORGE_FRAMES = [
    r"""
          [ IMPERIAL SURGICAL BAY ]
              mask shell: open
              breath: none
    """,
    r"""
          [ IMPERIAL SURGICAL BAY ]
              mask shell: closing
              breath: machine
    """,
    r"""
          [ IMPERIAL SURGICAL BAY ]
              mask shell: sealed
              breath: empire
    """,
]

PADME_ESCAPE_FRAMES = [
    r"""
       NABOO YACHT // AFT RAMP
       engines: cold
       shields: cracked
       droids:  scrambling
    """,
    r"""
       NABOO YACHT // AFT RAMP
       engines: igniting
       shields: failing
       droids:  rerouting
    """,
    r"""
       NABOO YACHT // AFT RAMP
       engines: live
       shields: holding
       droids:  cheering politely
    """,
]

SET_PIECES = {
    "senate_signal": (SENATE_SIGNAL_FRAMES, Fore.BLUE, "SENATE SIGNAL"),
    "medical_scan": (MEDICAL_SCAN_FRAMES, Fore.GREEN, "MEDICAL SCAN"),
    "lava_chase": (LAVA_CHASE_FRAMES, Fore.RED, "LAVA CHASE"),
    "mask_forge": (MASK_FORGE_FRAMES, Fore.RED, "MASK FORGE"),
    "padme_escape": (PADME_ESCAPE_FRAMES, Fore.YELLOW, "PADME ESCAPE"),
    "saber_lock": (SABER_LOCK_FRAMES, Fore.YELLOW, "SABER LOCK"),
}

# ──────────────────────────────────────────────────────────────────────────────
# PLAYER STATE
# Tracks everything about the player: health, force power, morality,
# inventory, and the flags that record which narrative branches were taken.
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class PlayerState:
    """
    Mutable game state for the current playthrough.

    Attributes:
        name: The player's chosen name.
        character: 'anakin' or 'obiwan'.
        health / max_health: Current and maximum hit points.
        force_power / max_force: Current and maximum Force energy.
        morality: Ranges roughly from -10 (dark) to +10 (light).
                  Affects dialogue, available choices, and endings.
        stamina: Depletes during combat; determines fatigue penalties.
        inventory: List of item names the player is carrying.
        flags: Arbitrary key→value store for narrative state tracking
               (e.g., {"spared_clone": True, "found_holocron": True}).
        bond_padme / bond_brotherhood: Relationship meters that unlock
               altered dialogue and secret endings.
        clarity: How clearly the player sees Palpatine's manipulation.
        secrets_found / codex / memory_shards: Optional discovery progress
               for replay value and menu inspection.
        current_scene: ID of the scene the player is currently in.
        choices_made: Running count of total decisions (for stats screen).
    """
    name: str = ""
    character: str = ""
    health: int = 100
    max_health: int = 100
    force_power: int = 100
    max_force: int = 100
    morality: int = 0       # Negative = dark, positive = light
    stamina: int = 100
    inventory: list = field(default_factory=list)
    flags: dict = field(default_factory=dict)
    bond_padme: int = 0
    bond_brotherhood: int = 0
    clarity: int = 0
    secrets_found: int = 0
    codex: list = field(default_factory=list)
    memory_shards: list = field(default_factory=list)
    current_scene: str = "title"
    choices_made: int = 0

    def shift_morality(self, amount: int, reason: str = ""):
        """
        Adjust morality and notify the player with a subtle indicator.

        Args:
            amount: Positive pushes toward light, negative toward dark.
            reason: Optional flavor text explaining the shift.
        """
        self.morality += amount
        if amount > 0:
            indicator = f"{Fore.CYAN}  ✦ Light side shift"
            audio.play_sfx_cue("light")
        elif amount < 0:
            indicator = f"{Fore.RED}  ✦ Dark side shift"
            audio.play_sfx_cue("dark")
        else:
            indicator = f"{Fore.YELLOW}  ✦ The Force remains balanced"
        if reason:
            indicator += f" — {reason}"
        print(f"{indicator}{Style.RESET_ALL}")

    def add_item(self, item: str):
        """Add an item to inventory and notify the player."""
        if item not in self.inventory:
            self.inventory.append(item)
            audio.play_sfx_cue("save")
            print(f"\n  {Fore.GREEN}+ Acquired: {Style.BRIGHT}{item}{Style.RESET_ALL}")

    def remove_item(self, item: str):
        """Remove an item from inventory if present."""
        if item in self.inventory:
            self.inventory.remove(item)
            print(f"\n  {Fore.RED}- Lost: {Style.BRIGHT}{item}{Style.RESET_ALL}")

    def use_force(self, cost: int) -> bool:
        """
        Attempt to spend Force energy. Returns True if successful.

        Args:
            cost: Amount of Force power required.
        """
        if self.force_power >= cost:
            self.force_power -= cost
            return True
        print(f"  {Fore.RED}Not enough Force power! ({self.force_power}/{cost}){Style.RESET_ALL}")
        return False

    def heal(self, amount: int):
        """Restore health up to the maximum."""
        self.health = min(self.max_health, self.health + amount)
        audio.play_sfx_cue("heal")
        print(f"  {Fore.GREEN}+ Restored {amount} HP{Style.RESET_ALL}")

    def change_bond(self, bond_name: str, amount: int, reason: str = ""):
        """Adjust one of the relationship meters and show the change."""
        attr = f"bond_{bond_name}"
        if not hasattr(self, attr):
            return
        setattr(self, attr, getattr(self, attr) + amount)
        label = bond_name.replace("_", " ").title()
        color = Fore.CYAN if amount >= 0 else Fore.RED
        sign = "+" if amount >= 0 else ""
        suffix = f" — {reason}" if reason else ""
        print(f"{color}  {label} bond {sign}{amount}{suffix}{Style.RESET_ALL}")

    def add_clarity(self, amount: int, reason: str = ""):
        """Increase insight into the deeper plot."""
        self.clarity = max(0, self.clarity + amount)
        suffix = f" — {reason}" if reason else ""
        print(f"{Fore.MAGENTA}  ✦ Clarity +{amount}{suffix}{Style.RESET_ALL}")

    def add_codex(self, entry: str):
        """Record an optional lore/discovery entry."""
        if entry not in self.codex:
            self.codex.append(entry)
            print(f"{Fore.BLUE}  Codex updated: {entry}{Style.RESET_ALL}")

    def add_memory_shard(self, title: str, body: str):
        """Record a memory shard for the in-game memory menu."""
        if not any(isinstance(shard, dict) and shard.get("title") == title for shard in self.memory_shards):
            self.memory_shards.append({"title": title, "body": body})
            audio.play_sfx_cue("memory")
            print(f"{Fore.MAGENTA}  Memory shard unlocked: {title}{Style.RESET_ALL}")

    def discover_secret(self, title: str, body: str):
        """Track and reveal a secret only once per run."""
        key = f"secret_{title.lower().replace(' ', '_')}"
        if not self.flags.get(key):
            self.flags[key] = True
            self.secrets_found += 1
            audio.play_sfx_cue("secret")
            show_secret(title, body)

    def take_damage(self, amount: int, source: str = ""):
        """
        Apply damage to the player and display it.
        Returns True if the player is still alive.
        """
        self.health = max(0, self.health - amount)
        audio.play_sfx_cue("damage")
        label = f" from {source}" if source else ""
        print(f"  {Fore.RED}✖ Took {amount} damage{label} "
              f"[HP: {self.health}/{self.max_health}]{Style.RESET_ALL}")
        return self.health > 0


# ──────────────────────────────────────────────────────────────────────────────
# COMBAT SYSTEM
# A turn-based combat engine with attack, defend, and Force abilities.
# Outcomes affect narrative flow — defeating enemies vs. showing mercy
# triggers different story branches.
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class Enemy:
    """Represents a combat opponent."""
    name: str
    health: int
    max_health: int
    attack_power: int
    defense: int
    dialogue: list = field(default_factory=list)  # Lines spoken mid-fight


def run_combat(player: PlayerState, enemy: Enemy) -> str:
    """
    Execute a turn-based combat encounter.

    The player chooses actions each turn; the enemy responds with
    semi-random attacks and occasional dialogue. Combat ends when
    either side reaches 0 HP, or the player flees.

    Args:
        player: The current player state (modified in place).
        enemy: The enemy to fight.

    Returns:
        "victory", "defeat", or "fled".
    """
    header_box("⚔  COMBAT  ⚔", f"vs. {enemy.name}", Fore.RED)
    turn = 0
    defending = False
    enemy_stunned = False

    while player.health > 0 and enemy.health > 0:
        turn += 1

        # ── Enemy health bar ──
        ehp_filled = int((enemy.health / enemy.max_health) * 20)
        ehp_bar = f"{'█' * ehp_filled}{'░' * (20 - ehp_filled)}"
        print(f"\n  {Fore.RED}{enemy.name}: [{ehp_bar}] "
              f"{enemy.health}/{enemy.max_health}{Style.RESET_ALL}")
        status_bar(player)

        # ── Enemy mid-fight dialogue (every few turns) ──
        if enemy.dialogue and turn % 3 == 0:
            line = random.choice(enemy.dialogue)
            type_dialogue(enemy.name, line, Fore.RED)

        # ── Player turn ──
        action_map = [
            ("strike", "⚔ Strike"),
            ("defend", "🛡 Defend"),
            ("force_push", "✦ Force Push (20 FP)"),
            ("force_heal", "✦ Force Heal (30 FP)"),
            ("center", "◎ Center Yourself (+stamina/+FP)"),
        ]
        if "Bacta Patch" in player.inventory:
            action_map.append(("bacta", "✚ Use Bacta Patch"))
        if "Thermal Detonator" in player.inventory:
            action_map.append(("detonator", "💣 Throw Thermal Detonator"))
        if "Emergency Flare" in player.inventory:
            action_map.append(("flare", "☄ Fire Emergency Flare"))

        choice = show_choices([label for _, label in action_map])
        action = action_map[choice - 1][0]

        if action == "strike":
            stamina_factor = 1.0 if player.stamina >= 25 else 0.72
            base_dmg = int(random.randint(16, 28) * stamina_factor)
            base_dmg = max(4, base_dmg - max(0, enemy.defense // 3))
            player.stamina = max(0, player.stamina - 12)

            if defending:
                base_dmg = int(base_dmg * 0.6)  # Reduced damage while defensive
                defending = False

            crit_chance = 0.15 + min(0.10, player.clarity * 0.01)
            crit = random.random() < crit_chance
            if crit:
                base_dmg = int(base_dmg * 1.8)
                print(f"  {Fore.YELLOW}{Style.BRIGHT}★ CRITICAL HIT!{Style.RESET_ALL}")
            enemy.health = max(0, enemy.health - base_dmg)
            print(f"  {Fore.GREEN}You strike for {base_dmg} damage!{Style.RESET_ALL}")
            if player.stamina < 20:
                print(f"  {Fore.YELLOW}Your arms burn with fatigue. Center yourself soon.{Style.RESET_ALL}")

        elif action == "defend":
            defending = True
            player.stamina = min(100, player.stamina + 20)
            print(f"  {Fore.BLUE}You brace for the next attack. (+20 stamina){Style.RESET_ALL}")

        elif action == "force_push":
            if player.use_force(20):
                dmg = max(10, random.randint(28, 46) - enemy.defense // 4)
                enemy.health = max(0, enemy.health - dmg)
                player.stamina = max(0, player.stamina - 8)
                print(f"  {Fore.CYAN}The Force surges through you — {dmg} damage!{Style.RESET_ALL}")
                # Small chance to stun (enemy skips next attack)
                if random.random() < 0.35:
                    print(f"  {Fore.CYAN}{enemy.name} staggers, stunned!{Style.RESET_ALL}")
                    enemy_stunned = True

        elif action == "force_heal":
            if player.use_force(30):
                heal_amt = random.randint(20, 35)
                player.heal(heal_amt)
                player.stamina = min(100, player.stamina + 10)

        elif action == "center":
            player.stamina = min(100, player.stamina + 28)
            player.force_power = min(player.max_force, player.force_power + 12)
            if random.random() < 0.35:
                player.add_clarity(1, "you read the rhythm of the duel")
            print(f"  {Fore.MAGENTA}You breathe through the heat and reclaim your balance.{Style.RESET_ALL}")

        elif action == "bacta":
            player.remove_item("Bacta Patch")
            player.heal(random.randint(32, 48))
            player.stamina = min(100, player.stamina + 12)

        elif action == "detonator":
            player.remove_item("Thermal Detonator")
            dmg = random.randint(40, 60)
            enemy.health = max(0, enemy.health - dmg)
            print(f"  {Fore.YELLOW}{Style.BRIGHT}💥 BOOM! {dmg} damage!{Style.RESET_ALL}")
            enemy_stunned = True

        elif action == "flare":
            player.remove_item("Emergency Flare")
            print(f"  {Fore.YELLOW}{Style.BRIGHT}A white-hot flare splits the ash cloud!{Style.RESET_ALL}")
            enemy_stunned = True

        # ── Check if enemy is defeated ──
        if enemy.health <= 0:
            print(f"\n  {Fore.GREEN}{Style.BRIGHT}{enemy.name} has been defeated!{Style.RESET_ALL}")
            pause()
            return "victory"

        # ── Enemy turn ──
        sleep_scaled(0.5)
        if enemy_stunned:
            enemy_stunned = False
            print(f"  {Fore.CYAN}{enemy.name} loses the rhythm of the duel and cannot answer.{Style.RESET_ALL}")
            continue

        if defending:
            # Reduced incoming damage when defending
            raw_dmg = random.randint(enemy.attack_power - 5, enemy.attack_power + 3)
            actual_dmg = max(1, raw_dmg // 2)
            defending = False
            print(f"  {Fore.RED}{enemy.name} attacks! Your guard absorbs the blow — "
                  f"only {actual_dmg} damage.{Style.RESET_ALL}")
        else:
            actual_dmg = random.randint(enemy.attack_power - 5, enemy.attack_power + 5)
            print(f"  {Fore.RED}{enemy.name} attacks for {actual_dmg} damage!{Style.RESET_ALL}")

        if not player.take_damage(actual_dmg, enemy.name):
            print(f"\n  {Fore.RED}{Style.BRIGHT}You have fallen.{Style.RESET_ALL}")
            pause()
            return "defeat"

    return "defeat"


# ──────────────────────────────────────────────────────────────────────────────
# SAVE / LOAD SYSTEM
# Persists player state to a JSON file so the player can resume later.
# ──────────────────────────────────────────────────────────────────────────────


def save_game(player: PlayerState, silent: bool = False) -> bool:
    """Serialize the player state to a JSON file."""
    data = asdict(player)
    data["save_timestamp"] = datetime.now().isoformat()
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        if not silent:
            print(f"\n  {Fore.GREEN}✓ Game saved.{Style.RESET_ALL}")
        return True
    except IOError as e:
        if not silent:
            print(f"\n  {Fore.RED}Save failed: {e}{Style.RESET_ALL}")
        return False


def delete_save(silent: bool = False) -> bool:
    """Delete the active save file if one exists."""
    try:
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)
            if not silent:
                print(f"\n  {Fore.YELLOW}Save cleared.{Style.RESET_ALL}")
        return True
    except OSError as e:
        if not silent:
            print(f"\n  {Fore.RED}Could not clear save: {e}{Style.RESET_ALL}")
        return False


def load_game() -> Optional[PlayerState]:
    """Load a saved game, returning a PlayerState or None."""
    if not os.path.exists(SAVE_FILE):
        return None
    try:
        with open(SAVE_FILE) as f:
            data = json.load(f)
        data.pop("save_timestamp", None)
        return PlayerState(**data)
    except (IOError, json.JSONDecodeError, TypeError):
        return None


# ──────────────────────────────────────────────────────────────────────────────
# GAME ENGINE
# The central class that drives scene transitions, handles the game loop,
# and coordinates between the narrative scenes, combat, and player state.
# ──────────────────────────────────────────────────────────────────────────────


class GameEngine:
    """
    Core game loop and scene dispatcher.

    Scenes are registered as methods (scene_xxx). The engine calls the
    current scene method, which returns the name of the next scene.
    """

    def __init__(self):
        self.player = PlayerState()
        self.running = True

    def _sync_audio_for_scene(self, scene_name: str):
        """Pick a music mood from the scene name."""
        if scene_name == "title":
            audio.set_mood("title")
        elif "duel" in scene_name or "high_ground" in scene_name or "combat" in scene_name:
            audio.set_mood("duel")
        elif "ending_dark" in scene_name or "ending_fall" in scene_name or "defeat" in scene_name:
            audio.set_mood("tragedy")
        elif "redemption" in scene_name or "rebellion" in scene_name or "miracle" in scene_name or "broken_mask" in scene_name:
            audio.set_mood("hope")
        elif scene_name.startswith("padme"):
            audio.set_mood("hope" if "ending" in scene_name else "tension")
        elif scene_name.startswith("anakin"):
            audio.set_mood("dark")
        else:
            audio.set_mood("tension")

    # ── Main loop ──

    def run(self):
        """Start the game loop, dispatching to scene methods."""
        global ACTIVE_ENGINE
        ACTIVE_ENGINE = self
        audio.set_mood("title")

        while self.running:
            scene_method = getattr(self, f"scene_{self.player.current_scene}", None)
            if scene_method is None:
                print(f"{Fore.RED}ERROR: Unknown scene '{self.player.current_scene}'{Style.RESET_ALL}")
                self.running = False
                break
            self._sync_audio_for_scene(self.player.current_scene)
            try:
                next_scene = scene_method()
            except LoadRequested:
                continue
            except QuitRequested:
                self.running = False
                break

            if next_scene is None:
                self.running = False
            else:
                self.player.current_scene = next_scene
                self.player.choices_made += 1
                save_game(self.player, silent=True)  # Autosave after each successful scene transition

    # ══════════════════════════════════════════════════════════════════════
    #  TITLE & SETUP SCENES
    # ══════════════════════════════════════════════════════════════════════

    def scene_title(self):
        """Title screen with new game / load game options."""
        clear_screen()
        print(f"{Fore.RED}{Style.BRIGHT}{TITLE_ART}{Style.RESET_ALL}")
        centered("S T A R   W A R S", f"{Fore.YELLOW}{Style.BRIGHT}")
        centered("D U E L   O F   F A T E S", f"{Fore.RED}{Style.BRIGHT}")
        print()
        centered("Expanded Cinematic Terminal Edition", Fore.WHITE + Style.DIM)
        print()
        horizontal_rule("─", Fore.RED + Style.DIM)

        saved = load_game()
        if saved and not getattr(self, f"scene_{saved.current_scene}", None):
            saved = None
            delete_save(silent=True)

        options = ["New Game"]
        if saved:
            options.append(f"Continue as {saved.name} ({saved.character.title()})")
        options.append("Quit")

        choice = show_choices(options)

        if choice == 1:
            self.player = PlayerState(current_scene="intro")
            save_game(self.player, silent=True)
            return "intro"
        elif choice == 2 and saved:
            self.player = saved
            print(f"\n  {Fore.GREEN}Welcome back, {self.player.name}.{Style.RESET_ALL}")
            pause()
            return self.player.current_scene
        else:
            self.running = False
            return None

    def scene_intro(self):
        """Player enters their name and chooses a character."""
        clear_screen()
        header_box("CHAPTER I", "The Beginning of the End", Fore.YELLOW)

        type_text("A long time ago in a galaxy far, far away...", color=Fore.BLUE + Style.BRIGHT)
        sleep_scaled(1)
        print()
        type_text("The Republic has fallen. Chancellor Palpatine has declared himself "
                   "Emperor, and the Jedi Order lies in ruins. On the volcanic planet of "
                   "Mustafar, two brothers in all but blood are about to face each other "
                   "in a duel that will determine the fate of the galaxy.",
                   color=Fore.WHITE)
        print()
        horizontal_rule("─", Fore.RED + Style.DIM)

        self.player.name = ""
        while not self.player.name.strip():
            self.player.name = input(f"\n  {Fore.YELLOW}What is your name, warrior? ▸ {Style.RESET_ALL}").strip()

        print()
        type_text(f"Welcome, {self.player.name}. Choose your destiny.", color=Fore.YELLOW)
        print()
        type_text(
            "Tip: During choice prompts, type S to save, L to load, C for codex, M for memories, or Q to quit.",
            color=Fore.WHITE + Style.DIM,
            speed=TYPE_SPEED_FAST,
        )

        choice = show_choices([
            f"{Fore.RED}Anakin Skywalker{Style.RESET_ALL} — The Chosen One, consumed by rage",
            f"{Fore.CYAN}Obi-Wan Kenobi{Style.RESET_ALL} — The faithful Jedi, burdened by duty",
            f"{Fore.MAGENTA}Padmé Amidala{Style.RESET_ALL} — The senator who can turn love into rebellion",
        ])

        if choice == 1:
            self.player.character = "anakin"
            self.player.morality = -1  # Anakin starts slightly dark
            self.player.bond_padme = 2
            self.player.bond_brotherhood = -1
            self.player.add_item("Lightsaber (Blue)")
            self.player.flags["has_padme_necklace"] = True
            self.player.add_codex("The Chosen One: prophecy twisted by fear")
            show_portrait("anakin", Fore.RED)
            type_text("You feel the dark side swelling inside you. There is power here — "
                       "power the Jedi were too afraid to use.",
                       color=Fore.RED)
            return "anakin_arrival"
        elif choice == 2:
            self.player.character = "obiwan"
            self.player.morality = 2  # Obi-Wan starts light-aligned
            self.player.bond_padme = 1
            self.player.bond_brotherhood = 3
            self.player.add_item("Lightsaber (Blue)")
            self.player.add_item("Jedi Comlink")
            self.player.add_codex("The Negotiator: mercy under impossible pressure")
            show_portrait("obi-wan", Fore.CYAN)
            type_text("You feel the weight of what must be done. Anakin was your brother. "
                       "But the boy you trained is gone.",
                       color=Fore.CYAN)
            return "obiwan_arrival"
        else:
            self.player.character = "padme"
            self.player.morality = 3
            self.player.bond_padme = 4
            self.player.bond_brotherhood = 1
            self.player.clarity = 1
            self.player.add_item("Royal Holdout Blaster")
            self.player.add_item("Senate Cipher")
            self.player.add_item("Japor Snippet")
            self.player.add_codex("Padme Amidala: diplomacy under imperial collapse")
            self.player.add_memory_shard(
                "Queen at Fourteen",
                "A throne room on Naboo. A girl too young for war learning that courage can wear ceremonial paint."
            )
            show_portrait("padme", Fore.MAGENTA)
            type_text("You have survived invasions, assassins, votes, and war. Now the "
                       "Republic itself is dead, and the man you love is somewhere inside "
                       "the smoke.",
                       color=Fore.MAGENTA)
            return "padme_coruscant"

    # ══════════════════════════════════════════════════════════════════════
    #  PADME PATH
    # ══════════════════════════════════════════════════════════════════════

    def scene_padme_coruscant(self):
        """Padme begins with politics, proof, and love moving in opposite directions."""
        clear_screen()
        header_box("CORUSCANT — SENATE APARTMENT", "Padme's Path", Fore.MAGENTA)
        show_portrait("padme", Fore.MAGENTA)

        type_text("Obi-Wan has just left. His words remain in the room like smoke: "
                   "Anakin killed children. Anakin serves the Sith. Anakin is on Mustafar.",
                   color=Fore.WHITE)
        print()
        type_text("Your hand rests over your children. The Empire is hours old. If you "
                   "move like a grieving wife, Palpatine wins. If you move like a queen, "
                   "you might still save someone.",
                   color=Fore.MAGENTA)

        choice = show_choices([
            "Fly to Mustafar alone. Anakin will listen to you.",
            "Call Bail Organa and seed a resistance before you leave.",
            "Use the Senate Cipher to inspect Palpatine's emergency records.",
            "Ask Obi-Wan to come openly, not hidden."
        ])

        if choice == 1:
            self.player.change_bond("padme", 1, "love moves faster than caution")
            self.player.flags["padme_alone"] = True
            type_text("No escort. No witnesses. Only the ship, your children, and a hope "
                       "so bright it hurts to look at.",
                       color=Fore.MAGENTA)
            pause()
            return "padme_mustafar_landing"
        if choice == 2:
            self.player.add_item("Rebellion Beacon")
            self.player.flags["bail_network"] = True
            self.player.add_clarity(1, "survival needs witnesses")
            self.player.add_codex("Bail Organa: the first safe channel")
            type_dialogue("Bail Organa", "If this is treason, Senator, then let history "
                           "write down who made loyalty impossible.", Fore.BLUE)
            pause()
            return "padme_yacht_preparation"
        if choice == 3:
            return "padme_senate_records"

        self.player.change_bond("brotherhood", 2, "you refuse to stage a betrayal")
        self.player.flags["obiwan_openly_invited"] = True
        type_dialogue("Obi-Wan", "If he sees me beside you, he may think the worst.",
                       Fore.CYAN)
        type_dialogue("Padme", "Then we will not let the worst be the only story in the room.",
                       Fore.MAGENTA)
        pause()
        return "padme_yacht_preparation"

    def scene_padme_senate_records(self):
        """Padme uncovers evidence hidden inside the first hours of the Empire."""
        play_set_piece("senate_signal", cycles=1, delay=0.12)
        header_box("SENATE RECORDS", "The Empire leaves fingerprints", Fore.BLUE)

        type_text("The Senate Cipher opens doors Palpatine forgot you helped design. "
                   "Emergency orders, medical transfers, clone redeployments, and one "
                   "sealed note marked: MUSTAFAR CONTINGENCY.",
                   color=Fore.WHITE)
        type_dialogue("Sidious Recording", "If Skywalker breaks, Kenobi will make him useful.",
                       Fore.MAGENTA)

        choice = show_choices([
            "Download the Mustafar Contingency as evidence.",
            "Transmit the evidence to Bail immediately.",
            "Delete your access trail to protect Anakin from suspicion.",
            "Read deeper, even if the system notices you."
        ])

        if choice == 1:
            self.player.add_item("Sidious Dossier")
            self.player.add_clarity(3, "Mustafar is a designed wound")
            self.player.add_memory_shard(
                "The Hidden Hand",
                "A line of code, a timestamp, a voice. The tragedy has an author."
            )
        elif choice == 2:
            self.player.add_item("Sidious Dossier")
            self.player.add_item("Rebellion Beacon")
            self.player.flags["bail_network"] = True
            self.player.add_clarity(3, "truth now has a witness")
            self.player.discover_secret(
                "Bail Has Proof",
                "Before Padme leaves Coruscant, a copy of Sidious's plan reaches Alderaan."
            )
        elif choice == 3:
            self.player.change_bond("padme", 1, "you still protect his name")
            self.player.add_clarity(1, "fear edits the truth")
            type_text("The evidence vanishes from the console. The knowledge does not "
                       "vanish from you.",
                       color=Fore.YELLOW)
        else:
            self.player.add_item("Sidious Dossier")
            self.player.add_item("Clone Override Code")
            self.player.add_clarity(4, "you see the trap and the machinery behind it")
            self.player.take_damage(8, "security feedback")
            self.player.discover_secret(
                "Clone Override",
                "A forgotten Senate failsafe can delay one squad of troopers, once."
            )

        pause()
        return "padme_yacht_preparation"

    def scene_padme_yacht_preparation(self):
        """Padme prepares the Naboo yacht for a rescue that may become a rebellion."""
        clear_screen()
        header_box("NABOO YACHT", "Preparation is a kind of courage", Fore.MAGENTA)

        type_text("C-3PO worries in six million forms of panic. R2-D2 plugs into the "
                   "ship and immediately starts arguing with the navcomputer. The launch "
                   "window is closing.",
                   color=Fore.WHITE)

        choice = show_choices([
            "Load med-droids and a concealed life-sign scanner.",
            "Arm the yacht's public transmitter for a galaxy-wide broadcast.",
            "Bring no one else into this. Fewer people means fewer targets.",
            "Ask the droids to prepare an extraction route under fire."
        ])

        if choice == 1:
            self.player.add_item("Med-Droid Kit")
            self.player.flags["med_droids_loaded"] = True
            self.player.add_codex("Naboo Medical Kit: small tools against enormous history")
        elif choice == 2:
            self.player.add_item("Public Transmitter")
            self.player.flags["transmitter_armed"] = True
            self.player.add_clarity(1, "truth needs a signal")
        elif choice == 3:
            self.player.flags["padme_isolated"] = True
            self.player.change_bond("padme", 1, "you carry the danger yourself")
            type_text("You leave with fewer safeguards and fewer people to mourn you.",
                       color=Fore.WHITE + Style.DIM)
        else:
            self.player.add_item("Droid Escape Plan")
            self.player.flags["droid_escape_ready"] = True
            self.player.add_memory_shard(
                "R2's Promise",
                "A blue astromech chirps like he has already decided history will need you alive."
            )

        pause()
        return "padme_mustafar_landing"

    def scene_padme_mustafar_landing(self):
        """Padme lands on Mustafar and reaches Anakin before the duel fully ignites."""
        clear_screen()
        animate_frames(MUSTAFAR_LAVA_FRAMES, Fore.MAGENTA, cycles=1, delay=0.12)
        header_box("MUSTAFAR — LANDING PLATFORM", "Love enters the fire", Fore.MAGENTA)

        type_text("Heat slams into you as the ramp lowers. Anakin turns from the control "
                   "center doors. For half a second, he is only the boy from Tatooine, "
                   "the pilot from Naboo, the husband who smiled when he thought no one saw.",
                   color=Fore.WHITE)
        show_portrait("anakin", Fore.RED)
        type_dialogue("Anakin", "I saw your ship. I knew you would come.", Fore.RED)

        choices = [
            "Embrace him and ask him to leave with you now.",
            "Tell him you know what happened at the Temple.",
            "Press the Japor Snippet into his hand.",
            "Secretly arm the Rebellion Beacon."
        ]
        if "Sidious Dossier" in self.player.inventory:
            choices.insert(2, "Show him the Mustafar Contingency.")

        choice = show_choices(choices)
        showed_dossier_choice = "Sidious Dossier" in self.player.inventory and choice == 3

        if choice == 1:
            self.player.change_bond("padme", 2, "you reach for Anakin before Vader")
            self.player.flags["padme_embraced_anakin"] = True
            type_dialogue("Padme", "Come away with me. We can disappear before he closes "
                           "his hand around you.", Fore.MAGENTA)
        elif choice == 2:
            self.player.shift_morality(1, "truth spoken while afraid")
            self.player.add_clarity(1, "love without truth is another prison")
            self.player.flags["named_temple_truth"] = True
            type_dialogue("Padme", "Tell me it is a lie. Tell me Obi-Wan is wrong.",
                           Fore.MAGENTA)
            type_text("Anakin looks away. That is answer enough.",
                       color=Fore.WHITE + Style.DIM)
        elif showed_dossier_choice:
            self.player.add_clarity(2, "Anakin hears the trap named")
            self.player.change_bond("padme", 2, "you bring proof instead of accusation")
            self.player.flags["anakin_heard_dossier"] = True
            type_dialogue("Padme", "He wrote this before I arrived. Before Obi-Wan stepped "
                           "off the ship. He planned your pain.", Fore.MAGENTA)
        elif choice == 3 or (choice == 4 and "Sidious Dossier" in self.player.inventory):
            self.player.change_bond("padme", 2, "a small mercy survives the fire")
            self.player.add_memory_shard(
                "Japor Snippet",
                "A carved charm in a shaking hand. Proof that Anakin was once someone who gave gifts."
            )
            type_text("His fingers close around the old charm. The yellow in his eyes "
                       "flickers like a candle in wind.",
                       color=Fore.YELLOW)
        else:
            if "Rebellion Beacon" in self.player.inventory:
                self.player.flags["beacon_armed"] = True
                self.player.add_clarity(1, "witnesses are protection")
                type_text("The beacon warms beneath your sleeve. Bail will hear what happens next.",
                           color=Fore.BLUE)
            else:
                type_text("You reach for a beacon you never brought. The silence feels enormous.",
                           color=Fore.RED)

        pause()
        return "padme_truth_confrontation"

    def scene_padme_truth_confrontation(self):
        """Padme tries to keep the confrontation from becoming Sidious's script."""
        clear_screen()
        header_box("THE THREE OF YOU", "A trap needs everyone in position", Fore.MAGENTA)

        if self.player.flags.get("obiwan_openly_invited"):
            type_text("Obi-Wan steps down the ramp openly, hands visible, saber unlit.",
                       color=Fore.CYAN)
        else:
            type_text("Obi-Wan appears from the ship. Anakin's grief turns instantly into "
                       "the shape Palpatine wanted.",
                       color=Fore.WHITE)

        type_dialogue("Anakin", "You brought him here to kill me.", Fore.RED)
        type_dialogue("Padme", "No. I came here to stop anyone else from deciding who you are.",
                       Fore.MAGENTA)

        choices = [
            "Stand physically between Anakin and Obi-Wan.",
            "Order Obi-Wan to lower his saber and explain the Sith trap.",
            "Broadcast the confrontation through the yacht transmitter.",
            "Tell Anakin the children can still know his real name."
        ]
        choice = show_choices(choices)

        if choice == 1:
            self.player.change_bond("padme", 2, "you make yourself the shield")
            if self.player.bond_padme >= 7 or self.player.flags.get("anakin_heard_dossier"):
                self.player.flags["padme_choke_avoided"] = True
                type_text("Anakin's hand rises, trembles, and falls. The moment passes. "
                           "Not safely. But it passes.",
                           color=Fore.YELLOW)
            else:
                self.player.take_damage(28, "Anakin's panic")
                self.player.flags["padme_wounded"] = True
        elif choice == 2:
            self.player.change_bond("brotherhood", 2, "you force the brothers to hear each other")
            self.player.add_clarity(1, "the script weakens when named")
            self.player.flags["obiwan_ordered_to_explain"] = True
            type_dialogue("Obi-Wan", "Anakin, Palpatine needs you isolated. He needs you "
                           "to believe no one else can love you now.", Fore.CYAN)
        elif choice == 3:
            if "Public Transmitter" in self.player.inventory or self.player.flags.get("beacon_armed"):
                play_set_piece("senate_signal", cycles=1, delay=0.10)
                self.player.flags["public_broadcast_started"] = True
                self.player.add_clarity(2, "the trap now has an audience")
                self.player.discover_secret(
                    "Mustafar Live",
                    "The first public crack in the Empire is not a speech. It is a family breaking in real time."
                )
            else:
                type_text("The yacht has no live channel prepared. The truth stays trapped "
                           "on Mustafar with you.",
                           color=Fore.RED)
        else:
            self.player.change_bond("padme", 3, "you offer him a future he has not ruined yet")
            self.player.add_memory_shard(
                "Names for the Children",
                "Two names unspoken in the heat. Two futures waiting to learn whether their father was only a monster."
            )
            type_text("For the first time since you landed, Anakin looks frightened of "
                       "something other than loss.",
                       color=Fore.YELLOW)

        if self.player.health <= 0:
            return "padme_ending_tragedy"
        pause()
        return "padme_refinery_escape"

    def scene_padme_refinery_escape(self):
        """Padme survives the duel by turning the facility into leverage."""
        play_set_piece("padme_escape", cycles=1, delay=0.12)
        header_box("REFINERY ESCAPE", "No saber, no surrender", Fore.MAGENTA)

        type_text("The duel tears away from the landing platform into the refinery. You "
                   "cannot match a Jedi's speed, but you can read systems, people, and "
                   "catastrophe. The facility is dying. So is the story Palpatine wrote.",
                   color=Fore.WHITE)

        choices = [
            "Use the med-droids to stabilize yourself and the twins.",
            "Open blast doors to slow the duel before the high ground.",
            "Route the public broadcast through the Separatist emergency array.",
            "Trigger coolant floods to separate Anakin from Obi-Wan."
        ]
        choice = show_choices(choices)

        if choice == 1:
            play_set_piece("medical_scan", cycles=1, delay=0.12)
            if "Med-Droid Kit" in self.player.inventory:
                self.player.heal(35)
                self.player.flags["twins_stabilized"] = True
                self.player.add_codex("Medical Scan: hope with a heartbeat")
            else:
                self.player.take_damage(12, "untreated shock")
                type_text("You can slow your breathing, but you cannot invent medical tools.",
                           color=Fore.RED)
        elif choice == 2:
            self.player.change_bond("brotherhood", 2, "you buy Obi-Wan one honest breath")
            self.player.flags["duel_slowed"] = True
            type_text("Blast doors slam down one by one, forcing both men to stop, look, "
                       "and remember they are not alone.",
                       color=Fore.CYAN)
        elif choice == 3:
            play_set_piece("senate_signal", cycles=1, delay=0.10)
            if "Sidious Dossier" in self.player.inventory or self.player.flags.get("public_broadcast_started"):
                self.player.flags["proof_broadcast"] = True
                self.player.add_clarity(2, "truth outruns the Empire")
                self.player.add_memory_shard(
                    "The First Broadcast",
                    "A queen's voice crossing static while a new Empire tries to become inevitable."
                )
            else:
                self.player.flags["raw_broadcast"] = True
                type_text("You have no proof, only your voice. Sometimes that is enough "
                           "to start a question.",
                           color=Fore.YELLOW)
        else:
            self.player.shift_morality(1, "nonlethal force under pressure")
            self.player.flags["coolant_separation"] = True
            self.player.take_damage(10, "steam burst")
            type_text("White coolant floods the lower gantry. The duel breaks apart in "
                       "a roar of steam.",
                       color=Fore.WHITE)

        if self.player.health <= 0:
            return "padme_ending_tragedy"
        pause()
        return "padme_final_broadcast"

    def scene_padme_final_broadcast(self):
        """Padme decides what kind of future can survive Mustafar."""
        clear_screen()
        header_box("THE FUTURE CHOOSES A WITNESS", "Padme's final move", Fore.MAGENTA)

        type_text("The yacht shakes as Mustafar collapses behind you. Obi-Wan calls from "
                   "one channel. Bail from another. Anakin's breathing comes through a "
                   "third, ragged and human and terrifyingly close to silence.",
                   color=Fore.WHITE)

        choice = show_choices([
            "Expose Palpatine through Bail's network and ignite the first rebellion.",
            "Spend every resource saving Anakin alive and accountable.",
            "Disappear with the children; let the galaxy believe Padme died.",
            "Seize the Separatist emergency array and become the Empire's public enemy."
        ])

        if choice == 1:
            if self.player.flags.get("proof_broadcast") and self.player.flags.get("bail_network"):
                return "padme_ending_rebellion"
            type_text("The network is too thin or the proof too incomplete. The signal "
                       "sparks, but it does not yet catch.",
                       color=Fore.YELLOW)
            return "padme_ending_hidden_flame"
        if choice == 2:
            if (self.player.bond_padme >= 8 and self.player.clarity >= 5 and
                    (self.player.flags.get("coolant_separation") or self.player.flags.get("duel_slowed"))):
                return "padme_ending_living_anakin"
            type_text("You try to save the man beneath the monster, but Mustafar has taken "
                       "too much and left too little time.",
                       color=Fore.RED)
            return "padme_ending_hidden_flame"
        if choice == 3:
            return "padme_ending_hidden_flame"
        return "padme_ending_queen_of_ashes"

    def scene_padme_ending_rebellion(self):
        """Padme survives and turns proof into organized resistance."""
        clear_screen()
        print(f"{Fore.YELLOW}{ENDING_ART_REDEMPTION}{Style.RESET_ALL}")
        play_set_piece("senate_signal", cycles=1, delay=0.10)
        type_text("Bail's network catches your signal, then multiplies it. Senators who "
                   "were ready to kneel hear Sidious's own contingency. Clone captains "
                   "hear the word 'trap' and hesitate for the first time all day.",
                   color=Fore.WHITE)
        print()
        type_dialogue("Padme", "This is not the end of the Republic. This is the first "
                       "record of its murder.", Fore.MAGENTA)
        type_text("The Empire still rises. But now it rises in public, bleeding secrets.",
                   color=Fore.YELLOW + Style.BRIGHT)
        self._show_stats("PADME ENDING — THE REBELLION HAS A VOICE")
        return None

    def scene_padme_ending_living_anakin(self):
        """Best Padme ending: Anakin lives, exposed and unmasked."""
        clear_screen()
        print(f"{Fore.CYAN}{ENDING_ART_REDEMPTION}{Style.RESET_ALL}")
        play_set_piece("medical_scan", cycles=1, delay=0.12)
        type_text("The med-droids keep Anakin alive without sealing him inside the mask "
                   "Sidious prepared. Obi-Wan stands guard. Bail takes the proof. You sit "
                   "between all of them, exhausted, furious, alive.",
                   color=Fore.WHITE)
        print()
        type_dialogue("Anakin", "What am I now?", Fore.RED)
        type_dialogue("Padme", "Answerable.", Fore.MAGENTA)
        type_text("It is not forgiveness. It is not peace. It is something harder: a future "
                   "where the truth survives long enough to demand justice.",
                   color=Fore.YELLOW + Style.BRIGHT)
        self._show_stats("SECRET PADME ENDING — ANSWERABLE")
        return None

    def scene_padme_ending_hidden_flame(self):
        """Padme survives in hiding and becomes the rebellion's protected center."""
        clear_screen()
        print(f"{Fore.CYAN}{ENDING_ART_LIGHT}{Style.RESET_ALL}")
        type_text("The galaxy believes Padme Amidala died of grief. The galaxy is wrong.",
                   color=Fore.WHITE)
        print()
        type_text("On a moon with no monuments, you hold your children and build a rebellion "
                   "that begins as a lullaby, a cipher, and one unbroken witness.",
                   color=Fore.CYAN)
        self._show_stats("PADME ENDING — THE HIDDEN FLAME")
        return None

    def scene_padme_ending_queen_of_ashes(self):
        """Darker Padme ending: public resistance by ruthless political force."""
        clear_screen()
        print(f"{Fore.RED}{JEDI_BEACON_ART}{Style.RESET_ALL}")
        type_text("You take the Separatist emergency array and make yourself impossible "
                   "to quietly erase. Palpatine brands you traitor before you finish the "
                   "first sentence. You smile because he had to answer.",
                   color=Fore.YELLOW)
        print()
        type_text("The Rebellion that follows you is not gentle. It is brilliant, hunted, "
                   "and willing to burn imperial lies before they harden into law.",
                   color=Fore.RED + Style.BRIGHT)
        self._show_stats("PADME ENDING — QUEEN OF ASHES")
        return None

    def scene_padme_ending_tragedy(self):
        """Padme falls on Mustafar."""
        clear_screen()
        header_box("TRAGEDY", "The witness falls", Fore.RED)
        type_text("Mustafar takes your breath, then your voice. Somewhere beyond the smoke, "
                   "men with lightsabers decide the shape of history without the person "
                   "who saw most clearly what it cost.",
                   color=Fore.RED)
        self._show_stats("PADME ENDING — THE SILENCED WITNESS")
        return None

    # ══════════════════════════════════════════════════════════════════════
    #  ANAKIN PATH
    # ══════════════════════════════════════════════════════════════════════

    def scene_anakin_arrival(self):
        """Anakin arrives on Mustafar after executing the Separatist leaders."""
        clear_screen()
        animate_frames(MUSTAFAR_LAVA_FRAMES, Fore.RED, cycles=1, delay=0.12)
        print(f"{Fore.RED}{MUSTAFAR_ART}{Style.RESET_ALL}")
        header_box("MUSTAFAR — CONTROL CENTER", "Anakin's Path", Fore.RED)

        type_text("The heat is unbearable. Rivers of molten rock carve through the "
                   "landscape like open wounds. You stand in the control room of the "
                   "Separatist facility, the bodies of the leaders you just executed "
                   "still warm on the floor.",
                   color=Fore.WHITE)
        print()
        type_text("Your comlink crackles. Padmé's ship is landing on the platform outside.",
                   color=Fore.YELLOW)

        choice = show_choices([
            "Go to Padmé immediately",
            "Search the control room for useful items first",
            "Slice the damaged Separatist console",
            "Meditate on your new power"
        ])

        if choice == 1:
            return "anakin_padme"
        elif choice == 2:
            return "anakin_search"
        elif choice == 3:
            return "anakin_separatist_signal"
        else:
            self.player.shift_morality(-1, "You embrace the dark side's power")
            self.player.force_power = min(self.player.max_force, self.player.force_power + 20)
            type_text("You reach out with the Force. The dark side answers eagerly, "
                       "flooding you with raw strength. You feel invincible.",
                       color=Fore.RED)
            pause()
            return "anakin_force_vision"

    def scene_anakin_search(self):
        """Optional: loot the control room for an advantage."""
        clear_screen()
        header_box("CONTROL ROOM", "Exploring", Fore.RED)

        type_text("You rummage through the wreckage. Among the Separatist equipment, "
                   "you find a few useful items.",
                   color=Fore.WHITE)

        self.player.add_item("Thermal Detonator")
        self.player.add_item("Bacta Patch")
        type_text("A datapad on the desk contains a half-finished message from Nute Gunray "
                   "to an unknown recipient, pleading for help. You feel nothing.",
                   color=Fore.WHITE + Style.DIM)
        pause()
        return "anakin_separatist_vault"

    def scene_anakin_separatist_signal(self):
        """Anakin uncovers a hidden recording from Sidious."""
        cinematic_beat("ENCRYPTED SIGNAL", PALPATINE_HOLO_ART, Fore.MAGENTA,
                       "A message not meant for you")

        type_text("The console coughs up a corrupted holo. Static shivers into the shape "
                   "of a hooded figure. The timestamp is from one hour ago.",
                   color=Fore.WHITE)
        show_portrait("palpatine", Fore.MAGENTA)
        type_dialogue("Sidious", "If Lord Vader hesitates, the Kenobi wound will open him. "
                       "Let the wife see what fear has made of him.", Fore.MAGENTA)
        print()
        type_text("The words do not sound like trust. They sound like a trap built around "
                   "your heart.",
                   color=Fore.YELLOW)

        choice = show_choices([
            "Destroy the recording. No one manipulates you.",
            "Pocket the recording for leverage against Sidious.",
            "Transmit it to Padmé before she reaches the platform."
        ])

        if choice == 1:
            self.player.shift_morality(-1, "rage at being controlled")
            type_text("You crush the console until sparks rain over the dead room.",
                       color=Fore.RED)
        elif choice == 2:
            self.player.add_item("Sidious Recording")
            self.player.add_clarity(2, "the master has a leash")
            self.player.add_codex("Sidious Contingency: Mustafar was bait")
            self.player.discover_secret(
                "The Kenobi Wound",
                "Sidious expected Obi-Wan to become the blade that carved Vader into obedience."
            )
        else:
            self.player.flags["sent_recording_to_padme"] = True
            self.player.change_bond("padme", 2, "you let her see the truth")
            self.player.add_clarity(2, "Padmé receives the hidden message")
            self.player.discover_secret(
                "Padmé Knows",
                "Padmé lands with proof that Palpatine has been steering every heartbeat."
            )

        pause()
        return "anakin_padme"

    def scene_anakin_force_vision(self):
        """A Force vision shows Anakin futures he was never meant to see."""
        cinematic_beat("FORCE VISION", MEMORY_SHARD_ART, Fore.YELLOW,
                       "The future screams")
        animate_frames(FORCE_VISION_FRAMES, Fore.YELLOW, cycles=1, delay=0.25)

        type_text("The dark side opens like an eye. You see a black mask descending. "
                   "You hear a child crying somewhere you cannot reach. You see Obi-Wan "
                   "walking away with your lightsaber in his hand.",
                   color=Fore.WHITE)
        print()
        type_text("Then the vision fractures: Padmé alive. Obi-Wan beside you. Sidious "
                   "afraid. Futures fighting like sparks in a storm.",
                   color=Fore.YELLOW)

        choice = show_choices([
            "Embrace the mask. Fear will make the galaxy kneel.",
            "Reject the mask. No master chooses your fate.",
            "Reach for Padmé through the vision."
        ])

        if choice == 1:
            self.player.shift_morality(-2, "you welcome the nightmare")
            self.player.force_power = min(self.player.max_force, self.player.force_power + 25)
            self.player.flags["saw_vader_mask"] = True
        elif choice == 2:
            self.player.shift_morality(2, "defiance against destiny")
            self.player.add_clarity(3, "the future can be broken")
            self.player.flags["rejected_mask"] = True
        else:
            self.player.change_bond("padme", 2, "love cuts through the vision")
            self.player.add_clarity(1, "Padmé is not the enemy")
            self.player.flags["reached_for_padme"] = True

        self.player.add_codex("Vision Shards: futures are warnings, not verdicts")
        self.player.add_memory_shard(
            "The Mask Not Yet Made",
            "Black lenses, borrowed breath, and a future still soft enough to scar differently."
        )
        pause()
        return "anakin_padme"

    def scene_anakin_separatist_vault(self):
        """A small optional encounter that can change later endings."""
        cinematic_beat("SEPARATIST VAULT", DROID_ART, Fore.YELLOW,
                       "Something survived your fury")

        type_text("A maintenance hatch rattles behind the conference table. A scorched "
                   "tactical droid unfolds itself from a cabinet, one photoreceptor "
                   "flickering like a nervous star.",
                   color=Fore.WHITE)
        type_dialogue("K-4S", "Statement: I am not strategically relevant enough to execute.",
                       Fore.YELLOW)

        choice = show_choices([
            "Spare K-4S and demand useful intelligence",
            "Reprogram the droid as a weapon",
            "Destroy it. No witnesses."
        ])

        if choice == 1:
            self.player.shift_morality(1, "mercy for the powerless")
            self.player.flags["kas_spared"] = True
            self.player.add_item("Droid Transponder")
            self.player.add_clarity(1, "K-4S maps the Separatist tunnels")
            self.player.discover_secret(
                "K-4S Survives",
                "A terrified machine now knows a hidden route beneath the lava refinery."
            )
        elif choice == 2:
            self.player.shift_morality(-1, "useful things should obey")
            self.player.flags["kas_reprogrammed"] = True
            self.player.add_item("Sabotage Spike")
            type_text("The droid's voice becomes flat. Obedient. Efficient.",
                       color=Fore.RED)
        else:
            self.player.shift_morality(-2, "no witnesses")
            type_text("One slash. The droid's photoreceptor goes dark.",
                       color=Fore.RED)

        pause()
        return "anakin_padme"

    def scene_anakin_padme(self):
        """The confrontation with Padmé before Obi-Wan reveals himself."""
        clear_screen()
        header_box("LANDING PLATFORM", "Padmé", Fore.RED)
        show_portrait("padme", Fore.MAGENTA)

        type_text("Padmé rushes toward you, her face a mask of fear and hope. She reaches "
                   "for your hands.",
                   color=Fore.WHITE)
        type_dialogue("Padmé", "Anakin, I was so worried about you. Obi-Wan told me "
                       "terrible things.", Fore.MAGENTA)

        if self.player.flags.get("sent_recording_to_padme"):
            type_dialogue("Padmé", "And then your message came through. Anakin... he is "
                           "using you. He planned this.", Fore.MAGENTA)
            self.player.add_clarity(1, "Padmé names the manipulation out loud")

        choice = show_choices([
            "Reassure her: 'I am more powerful than the Chancellor. I can overthrow him.'",
            "Demand to know what Obi-Wan told her",
            "Hold her gently and say nothing",
            "Show her your fear: 'I saw a future where I lose everything.'"
        ])

        if choice == 1:
            self.player.shift_morality(-1, "Hunger for power")
            self.player.change_bond("padme", -1, "love becomes possession")
            type_dialogue("Padmé", "I don't want to hear any more about Obi-Wan. "
                           "Anakin, all I want is your love.", Fore.MAGENTA)
            type_dialogue(self.player.name, "Love won't save you, Padmé. "
                           "Only my new powers can do that.", Fore.RED)
        elif choice == 2:
            type_dialogue(self.player.name, "What lies has he been feeding you?", Fore.RED)
            type_dialogue("Padmé", "He said... you turned to the dark side. "
                           "That you killed younglings.", Fore.MAGENTA)
            self.player.shift_morality(-1, "Deflecting guilt")
            self.player.change_bond("padme", -1, "you make her defend the truth")
        elif choice == 3:
            self.player.shift_morality(1, "A moment of tenderness")
            self.player.change_bond("padme", 1, "you remember how to be gentle")
            type_text("For a brief moment, the rage quiets. You hold her, and you "
                       "almost remember who you used to be.",
                       color=Fore.WHITE)
            if "Bacta Patch" in self.player.inventory:
                self.player.heal(10)
        else:
            self.player.shift_morality(2, "honesty instead of control")
            self.player.change_bond("padme", 2, "you tell her the truth")
            self.player.add_clarity(1, "fear is not prophecy")
            type_dialogue(self.player.name, "I saw myself in a mask. I saw you gone. "
                           "I don't know how to stop it.", Fore.YELLOW)
            type_dialogue("Padmé", "Then stop trying to rule the future. Choose me now.",
                           Fore.MAGENTA)

        pause()
        return "anakin_obiwan_appears"

    def scene_anakin_obiwan_appears(self):
        """Obi-Wan steps off Padmé's ship. The betrayal."""
        clear_screen()
        header_box("THE BETRAYAL", "Obi-Wan Appears", Fore.RED)

        type_text("Then you see him. Obi-Wan Kenobi steps off the ramp of Padmé's ship, "
                   "his robes billowing in the volcanic wind.",
                   color=Fore.WHITE)
        show_portrait("obi-wan", Fore.CYAN)

        if self.player.clarity >= 3:
            type_text("The old rage rises, but now it has competition: suspicion. "
                       "Sidious wanted this exact wound.",
                       color=Fore.YELLOW)
        else:
            type_text("Something inside you snaps. She brought him here. She betrayed you.",
                       color=Fore.RED)

        type_dialogue("Padmé", "No! Anakin, I—", Fore.MAGENTA)

        choice = show_choices([
            "Force choke Padmé in a rage",
            "Control your anger — confront Obi-Wan directly",
            "Demand an explanation from both of them"
        ])

        if choice == 1:
            self.player.shift_morality(-3, "You choke the one you love")
            self.player.change_bond("padme", -4, "you become the thing she feared")
            self.player.change_bond("brotherhood", -2, "Obi-Wan sees the line crossed")
            type_text("Your hand rises. The dark side coils around Padmé's throat like a "
                       "serpent. She gasps, clawing at nothing, then collapses.",
                       color=Fore.RED)
            type_dialogue("Obi-Wan", "Let her go, Anakin!", Fore.CYAN)
            self.player.flags["choked_padme"] = True
        elif choice == 2:
            self.player.shift_morality(1, "You resist the urge to harm Padmé")
            self.player.change_bond("padme", 1, "you choose restraint")
            type_text("Your fists clench, but you push Padmé behind you and focus your "
                       "rage on the real target.",
                       color=Fore.YELLOW)
            type_dialogue(self.player.name, "You turned her against me!", Fore.RED)
            type_dialogue("Obi-Wan", "You have done that yourself.", Fore.CYAN)
            self.player.flags["choked_padme"] = False
        else:
            self.player.shift_morality(0)
            self.player.add_clarity(1, "you ask before striking")
            type_dialogue(self.player.name, "Explain. Now.", Fore.RED)
            type_dialogue("Obi-Wan", "Anakin, Chancellor Palpatine is evil.", Fore.CYAN)
            type_dialogue(self.player.name, "From my point of view, the Jedi are evil!", Fore.RED)
            self.player.flags["choked_padme"] = False

        pause()
        return "anakin_sidious_revelation"

    def scene_anakin_sidious_revelation(self):
        """Sidious presses the wound he engineered."""
        clear_screen()
        if self.player.clarity >= 2 or "Sidious Recording" in self.player.inventory:
            header_box("THE HAND BEHIND THE FIRE", "The trap reveals its shape", Fore.MAGENTA)
            print(f"{Fore.MAGENTA}{PALPATINE_HOLO_ART}{Style.RESET_ALL}")
            type_text("Padmé's ship projector flickers alive without permission. The same "
                       "hooded face floats in the ash between you and Obi-Wan.",
                       color=Fore.WHITE)
            type_dialogue("Sidious", "Good. Let pain complete what instruction could not.",
                           Fore.MAGENTA)
            type_dialogue("Obi-Wan", "Anakin, listen to him. He is not saving you. "
                           "He is spending you.", Fore.CYAN)
        else:
            header_box("A VOICE IN THE ASH", "Sidious listens", Fore.MAGENTA)
            type_text("Your comlink hisses. For a moment, all three of you hear only "
                       "breathing. Then Palpatine's voice slides through the static.",
                       color=Fore.WHITE)
            type_dialogue("Sidious", "Do not hesitate, Lord Vader. Attachments have made "
                           "you weak before.", Fore.MAGENTA)

        choice = show_choices([
            "Submit to Sidious. Pain is proof of strength.",
            "Defy Sidious. No one owns your future.",
            "Turn to Obi-Wan: 'Did you know he planned this?'"
        ])

        if choice == 1:
            self.player.shift_morality(-2, "obedience dressed as power")
            self.player.force_power = min(self.player.max_force, self.player.force_power + 25)
            self.player.flags["obeyed_sidious"] = True
            type_text("The order becomes a chain, and for one terrible second, the chain "
                       "feels like certainty.",
                       color=Fore.RED)
        elif choice == 2:
            self.player.shift_morality(2, "you refuse the leash")
            self.player.add_clarity(2, "Sidious can be beaten")
            self.player.flags["defied_sidious"] = True
            type_dialogue(self.player.name, "You promised me the power to save her. "
                           "You only taught me how to lose myself.", Fore.YELLOW)
        else:
            self.player.change_bond("brotherhood", 2, "you ask Obi-Wan for truth")
            self.player.add_clarity(2, "the wound becomes visible")
            self.player.flags["asked_obiwan_about_sidious"] = True
            type_dialogue("Obi-Wan", "No. But I should have seen it sooner. I should have "
                           "seen you sooner.", Fore.CYAN)

        pause()
        return "anakin_confrontation"

    def scene_anakin_confrontation(self):
        """The verbal confrontation before combat begins."""
        clear_screen()
        header_box("CONFRONTATION", "Words Before Blades", Fore.RED)

        type_dialogue("Obi-Wan", "You have allowed this Dark Lord to twist your mind "
                       "until now you have become the very thing you swore to destroy.",
                       Fore.CYAN)

        choice = show_choices([
            "'Don't lecture me, Obi-Wan. I have brought peace to my new Empire.'",
            "'You're right... but it's too late for me now.'",
            "Say nothing. Ignite your lightsaber.",
            "'If Sidious made this wound, help me cut him out.'"
        ])

        if choice == 1:
            self.player.shift_morality(-1, "Arrogance")
            self.player.change_bond("brotherhood", -1, "you crown yourself above him")
            type_dialogue("Obi-Wan", "Your new Empire?", Fore.CYAN)
            type_dialogue(self.player.name, "If you're not with me, then you're my enemy.", Fore.RED)
            type_dialogue("Obi-Wan", "Only a Sith deals in absolutes. I will do what I must.", Fore.CYAN)
        elif choice == 2:
            self.player.shift_morality(3, "A crack in the darkness")
            self.player.change_bond("brotherhood", 2, "you let him see the wound")
            self.player.flags["showed_doubt"] = True
            type_text("Obi-Wan's eyes widen. For a heartbeat, hope flickers across his face.",
                       color=Fore.CYAN)
            type_dialogue("Obi-Wan", "It's never too late, Anakin. Come back. Please.", Fore.CYAN)
            # This opens the secret redemption path later
            return "anakin_redemption_choice"
        elif choice == 3:
            self.player.shift_morality(-2, "Cold silence before violence")
            type_text("The hum of your lightsaber fills the silence.",
                       color=Fore.RED)
        else:
            if self.player.clarity >= 4 or self.player.flags.get("defied_sidious"):
                self.player.shift_morality(3, "you choose the enemy behind the enemy")
                self.player.change_bond("brotherhood", 3, "you ask for help instead of victory")
                self.player.flags["anti_sidious_pact"] = True
                type_dialogue("Obi-Wan", "Then lower your blade, and we face him together.",
                               Fore.CYAN)
                return "anakin_redemption_choice"
            self.player.shift_morality(-1, "truth without trust curdles")
            type_text("You reach for an alliance, but suspicion twists the words into "
                       "another accusation. Obi-Wan's hand tightens around his saber.",
                       color=Fore.YELLOW)

        pause()
        return "anakin_duel"

    def scene_anakin_redemption_choice(self):
        """
        SECRET PATH: Anakin can choose redemption before the duel.
        Only accessible if the player showed doubt during the confrontation.
        """
        clear_screen()
        header_box("✦ THE CROSSROADS ✦", "A Path Few Have Walked", Fore.YELLOW)

        type_text("Something stirs deep within you — beneath the rage, beneath the "
                   "dark side's grip. A voice. Qui-Gon's voice, maybe. Or your mother's.",
                   color=Fore.YELLOW)
        print()
        type_text("'You were supposed to bring balance...'", color=Fore.CYAN + Style.DIM)

        choice = show_choices([
            "Reach for the light. Drop your weapon.",
            "It's a trick. The dark side is testing you. Fight!",
            "Walk away. Leave Mustafar. Leave everything.",
            "Turn the trap back on Sidious with Obi-Wan and Padmé."
        ])

        if choice == 1:
            self.player.shift_morality(5, "You choose the light")
            return "anakin_ending_redemption"
        elif choice == 2:
            self.player.shift_morality(-3, "You reject redemption")
            type_text("The moment passes. The darkness floods back, colder and stronger "
                       "than before. There is no turning back now.",
                       color=Fore.RED)
            pause()
            return "anakin_duel"
        else:
            if choice == 3:
                self.player.shift_morality(2, "You choose exile over destruction")
                return "anakin_ending_exile"
            if self.player.flags.get("anti_sidious_pact") and self.player.bond_padme >= 3:
                self.player.shift_morality(4, "love and truth become rebellion")
                return "anakin_ending_rebellion_of_two"
            type_text("You can see the shape of a better future, but there is not enough "
                       "trust left in the room to reach it.",
                       color=Fore.YELLOW)
            self.player.shift_morality(1, "almost a miracle")
            return "anakin_duel"

    def scene_anakin_duel(self):
        """The lightsaber duel with Obi-Wan — full combat encounter."""
        clear_screen()
        animate_frames(SABER_LOCK_FRAMES, Fore.YELLOW, cycles=1, delay=0.15)
        print(f"{Fore.YELLOW}{LIGHTSABER_CLASH}{Style.RESET_ALL}")
        header_box("⚔  THE DUEL  ⚔", "Anakin vs. Obi-Wan", Fore.RED)

        type_text("Lightsabers ignite. Blue against blue. Master against apprentice. "
                   "The battle that will scar the galaxy begins.",
                   color=Fore.YELLOW)

        obi_wan = Enemy(
            name="Obi-Wan Kenobi",
            health=120,
            max_health=120,
            attack_power=18,
            defense=12,
            dialogue=[
                "I have failed you, Anakin. I have failed you.",
                "I was never able to teach you to think.",
                "Don't make me destroy you.",
                "You were the Chosen One!",
            ]
        )

        # Morality affects combat — darker Anakin hits harder but takes more
        if self.player.morality < -3:
            type_text("The dark side fuels your strikes with terrifying power.",
                       color=Fore.RED + Style.DIM)
            self.player.force_power = min(self.player.max_force, self.player.force_power + 30)
        elif self.player.morality > 0:
            type_text("Your conflicted heart makes your strikes hesitant.",
                       color=Fore.YELLOW + Style.DIM)
            obi_wan.attack_power -= 3  # Obi-Wan holds back too
        if self.player.flags.get("anti_sidious_pact"):
            type_text("Neither of you truly wants this duel anymore, but trust is still "
                       "bleeding out between every exchange.",
                       color=Fore.YELLOW + Style.DIM)
            obi_wan.attack_power -= 2
        if "Sabotage Spike" in self.player.inventory:
            type_text("Your reprogrammed droid spike overloads a refinery panel behind "
                       "Obi-Wan, forcing him to split his focus.",
                       color=Fore.RED + Style.DIM)
            obi_wan.defense = max(0, obi_wan.defense - 4)

        result = run_combat(self.player, obi_wan)

        if result == "victory":
            return "anakin_mining_platform_collapse"
        else:
            return "anakin_ending_fall"

    def scene_anakin_mining_platform_collapse(self):
        """A cinematic aftermath beat before Anakin decides Obi-Wan's fate."""
        play_set_piece("lava_chase", cycles=1, delay=0.12)
        header_box("THE FACILITY BREAKS", "Victory is not the same as control", Fore.RED)

        type_text("Obi-Wan falls hard against a control rail. The refinery answers with "
                   "a scream of tortured metal. Lava pumps rupture. Catwalks twist. "
                   "Padmé's ship rocks on its landing struts.",
                   color=Fore.WHITE)

        choice = show_choices([
            "Drive Obi-Wan toward the lava while the platform collapses",
            "Use the Force to steady Padmé's ship",
            "Call K-4S through the tunnels and take a hidden route",
            "Let the whole place burn. You need no one."
        ])

        if choice == 1:
            self.player.shift_morality(-2, "victory becomes cruelty")
            self.player.change_bond("brotherhood", -2, "you use disaster as a weapon")
            type_text("You press forward, and the collapsing world becomes another blade.",
                       color=Fore.RED)
        elif choice == 2:
            self.player.shift_morality(2, "Padmé before pride")
            self.player.change_bond("padme", 2, "you save her before claiming victory")
            if self.player.use_force(20):
                type_text("The ship steadies. Through the viewport, Padmé sees you choose "
                           "something other than rage.",
                           color=Fore.YELLOW)
            else:
                type_text("You reach for the ship, but the duel has hollowed you out. "
                           "The landing struts buckle hard.",
                           color=Fore.RED)
                self.player.take_damage(12, "refinery shockwave")
        elif choice == 3 and self.player.flags.get("kas_spared"):
            self.player.shift_morality(1, "mercy returns as strategy")
            self.player.add_clarity(1, "small mercies have long shadows")
            type_dialogue("K-4S", "Statement: I remain strategically relevant.",
                           Fore.YELLOW)
            self.player.flags["hidden_tunnel_open"] = True
        elif choice == 3:
            type_text("No answer comes. The little droid you needed is scrap now.",
                       color=Fore.RED)
            self.player.take_damage(15, "collapsing refinery")
        else:
            self.player.shift_morality(-1, "isolation feels like strength")
            type_text("The refinery burns around you. You stand in the middle of it, "
                       "daring the galaxy to matter.",
                       color=Fore.RED)

        pause()
        return "anakin_high_ground_victory"

    def scene_anakin_high_ground_victory(self):
        """Anakin wins the duel — what does he do with victory?"""
        clear_screen()
        header_box("VICTORY", "Obi-Wan Falls", Fore.RED)

        type_text("Obi-Wan stumbles, his lightsaber clattering to the ground. He kneels "
                   "at the edge of the lava river, breathing hard, beaten.",
                   color=Fore.WHITE)
        print()
        type_dialogue("Obi-Wan", "Then you truly are lost.", Fore.CYAN)

        choices = [
            "Strike him down. Complete your victory.",
            "Spare him. 'You're not worth killing, old man.'",
            "Offer your hand. 'Come with me. We can overthrow the Emperor together.'"
        ]
        if self.player.clarity >= 5 or "Sidious Recording" in self.player.inventory:
            choices.append("Broadcast Sidious's betrayal and make Mustafar the first rebellion.")

        choice = show_choices(choices)

        if choice == 1:
            self.player.shift_morality(-4, "You kill your master")
            return "anakin_ending_dark"
        elif choice == 2:
            self.player.shift_morality(2, "Mercy")
            return "anakin_ending_hollow"
        elif choice == 3:
            self.player.shift_morality(1, "An unexpected offer")
            self.player.flags["offered_alliance"] = True
            return "anakin_ending_alliance"
        else:
            self.player.shift_morality(4, "you name the real enemy")
            self.player.flags["broadcast_sidious"] = True
            return "anakin_ending_rebellion_of_two"

    # ── Anakin Endings ──

    def scene_anakin_ending_dark(self):
        """Ending: Anakin fully embraces the dark side."""
        clear_screen()
        print(f"{Fore.RED}{ENDING_ART_DARK}{Style.RESET_ALL}")
        play_set_piece("mask_forge", cycles=1, delay=0.16)
        type_text("You stand alone on Mustafar, surrounded by fire and death. "
                   "Obi-Wan is gone. Padmé is gone. The boy from Tatooine is gone.",
                   color=Fore.RED)
        print()
        type_text("When Palpatine's shuttle arrives, you kneel without hesitation. "
                   "The mask descends. The respirator hisses to life.",
                   color=Fore.RED)
        print()
        type_text("You are Darth Vader now. And the galaxy will tremble.",
                   color=Fore.RED + Style.BRIGHT)
        self._show_stats("THE DARK LORD RISES")
        return None

    def scene_anakin_ending_fall(self):
        """Ending: Anakin loses the duel (canonical outcome)."""
        clear_screen()
        header_box("DEFEAT", "The High Ground", Fore.RED)

        type_text("Obi-Wan leaps to the bank above you, lava roaring below.",
                   color=Fore.WHITE)
        type_dialogue("Obi-Wan", "It's over, Anakin! I have the high ground.", Fore.CYAN)
        print()

        choice = show_choices([
            "'You underestimate my power!'  — Leap at him",
            "Yield. Let it end."
        ])

        if choice == 1:
            self.player.shift_morality(-1, "Pride")
            type_text("You leap. His blade flashes. You feel your legs leave you, then "
                       "the burning. Always the burning.",
                       color=Fore.RED)
            play_set_piece("mask_forge", cycles=1, delay=0.16)
            print()
            type_dialogue("Obi-Wan", "You were the Chosen One! It was said that you would "
                           "destroy the Sith, not join them!", Fore.CYAN)
            type_dialogue(self.player.name, "I HATE YOU!", Fore.RED)
            type_dialogue("Obi-Wan", "You were my brother, Anakin. I loved you.", Fore.CYAN)
        else:
            self.player.shift_morality(2, "Surrender")
            type_text("You deactivate your lightsaber. The fight drains out of you.",
                       color=Fore.YELLOW)
            type_dialogue("Obi-Wan", "...Anakin?", Fore.CYAN)
            return "anakin_ending_redemption"

        print(f"\n{Fore.RED}{ENDING_ART_DARK}{Style.RESET_ALL}")
        self._show_stats("CHOSEN ONE — FALLEN")
        return None

    def scene_anakin_ending_redemption(self):
        """Ending: Anakin turns back to the light."""
        clear_screen()
        print(f"{Fore.CYAN}{ENDING_ART_REDEMPTION}{Style.RESET_ALL}")
        type_text("The darkness recedes — not easily, not painlessly, but it recedes. "
                   "You drop to your knees. For the first time since Palpatine's office, "
                   "you weep.",
                   color=Fore.CYAN)
        print()
        type_dialogue("Obi-Wan", "...Anakin?", Fore.CYAN)
        type_dialogue(self.player.name, "I'm sorry. I'm so sorry.", Fore.YELLOW)
        print()
        type_text("The road back will be long. The things you've done cannot be undone. "
                   "But for the first time, there is hope.",
                   color=Fore.YELLOW + Style.BRIGHT)
        self._show_stats("REDEMPTION — THE CHOSEN ONE RETURNS")
        return None

    def scene_anakin_ending_exile(self):
        """Ending: Anakin walks away from everything."""
        clear_screen()
        print(f"{Fore.YELLOW}{ENDING_ART_REDEMPTION}{Style.RESET_ALL}")
        type_text("You leave. Not toward the light, not deeper into darkness. You "
                   "simply leave. Your lightsaber stays on the landing platform.",
                   color=Fore.YELLOW)
        print()
        type_text("Somewhere in the Outer Rim, a man with no name begins a quiet life. "
                   "The Empire searches for him. The Rebellion never finds him. "
                   "The Force, for once, leaves him in peace.",
                   color=Fore.WHITE + Style.DIM)
        self._show_stats("EXILE — NEITHER JEDI NOR SITH")
        return None

    def scene_anakin_ending_hollow(self):
        """Ending: Anakin spares Obi-Wan but remains dark."""
        clear_screen()
        header_box("HOLLOW VICTORY", "", Fore.RED)
        type_text("You let Obi-Wan go. Not out of mercy — you simply don't care enough "
                   "to finish it. He limps onto a shuttle and vanishes into hyperspace.",
                   color=Fore.RED)
        print()
        type_text("You have won everything and feel nothing. The Empire is yours to shape. "
                   "Palpatine smiles when you return. You do not smile back.",
                   color=Fore.RED + Style.DIM)
        self._show_stats("THE EMPTY THRONE")
        return None

    def scene_anakin_ending_alliance(self):
        """Ending: Anakin offers Obi-Wan an alliance against the Emperor."""
        clear_screen()
        print(f"{Fore.YELLOW}{ENDING_ART_REDEMPTION}{Style.RESET_ALL}")
        type_text("Obi-Wan stares at your outstretched hand for a long time.",
                   color=Fore.WHITE)
        type_dialogue("Obi-Wan", "You would betray Palpatine?", Fore.CYAN)
        type_dialogue(self.player.name, "He's using me. I see that now. But I'm not "
                       "going back to the Jedi. Help me build something new.", Fore.YELLOW)
        print()
        type_text("It's uneasy. It may not last. But two of the most powerful Force users "
                   "alive walk off Mustafar together, and the Emperor feels a tremor in "
                   "the Force he cannot explain.",
                   color=Fore.YELLOW + Style.BRIGHT)
        self._show_stats("THE GREY PATH — A NEW ORDER")
        return None

    def scene_anakin_ending_rebellion_of_two(self):
        """Secret ending: Anakin turns against Sidious before Vader is sealed."""
        clear_screen()
        print(f"{Fore.YELLOW}{ENDING_ART_REDEMPTION}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{PALPATINE_HOLO_ART}{Style.RESET_ALL}")

        type_text("The recording goes out on every Separatist emergency channel K-4S can "
                   "still touch. It jumps to Padmé's ship. Then to Bail Organa. Then to "
                   "anyone in the new Empire still brave enough to listen.",
                   color=Fore.YELLOW)
        print()
        type_dialogue("Sidious", "Vader. End this.", Fore.MAGENTA)
        type_dialogue(self.player.name, "My name is Anakin Skywalker.", Fore.YELLOW)
        type_dialogue("Obi-Wan", "Then we move. Together.", Fore.CYAN)
        print()
        type_text("You do not become a saint. Obi-Wan does not forget. Padmé does not "
                   "pretend the blood is gone. But the first secret of the Empire has "
                   "been dragged into firelight, and Sidious feels his perfect future "
                   "split down the middle.",
                   color=Fore.WHITE)
        self._show_stats("SECRET ENDING — THE FIRST REBELLION")
        return None

    # ══════════════════════════════════════════════════════════════════════
    #  OBI-WAN PATH
    # ══════════════════════════════════════════════════════════════════════

    def scene_obiwan_arrival(self):
        """Obi-Wan arrives on Mustafar, hidden aboard Padmé's ship."""
        clear_screen()
        animate_frames(MUSTAFAR_LAVA_FRAMES, Fore.CYAN, cycles=1, delay=0.12)
        print(f"{Fore.CYAN}{MUSTAFAR_ART}{Style.RESET_ALL}")
        header_box("MUSTAFAR — PADMÉ'S SHIP", "Obi-Wan's Path", Fore.CYAN)

        type_text("You feel Anakin's presence through the Force — a roiling storm of "
                   "rage and grief. The boy you raised is drowning in darkness.",
                   color=Fore.WHITE)
        print()
        type_text("Padmé's ship descends through clouds of ash. You hide in the cargo "
                   "hold, listening as she goes to confront her husband.",
                   color=Fore.WHITE)

        choice = show_choices([
            "Wait and listen — let Padmé try to reach him first",
            "Step out immediately to confront Anakin",
            "Search the ship for anything useful before going out"
        ])

        if choice == 1:
            self.player.shift_morality(1, "Patience and hope")
            self.player.change_bond("brotherhood", 1, "you give love one last chance")
            type_text("Through the hull, you hear their voices. Padmé pleading. Anakin's "
                       "voice, cold and unrecognizable. Then a choking sound. A body falling.",
                       color=Fore.WHITE + Style.DIM)
            type_text("You burst out of the ship. Padmé lies unconscious on the platform.",
                       color=Fore.RED)
            self.player.flags["padme_choked"] = True
        elif choice == 2:
            self.player.change_bond("brotherhood", -1, "Anakin sees ambush before mercy")
            type_text("You stride down the ramp. Anakin sees you before you can speak.",
                       color=Fore.WHITE)
            type_dialogue("Anakin", "YOU! You turned her against me!", Fore.RED)
            self.player.flags["padme_choked"] = False
        else:
            self.player.add_item("Bacta Patch")
            self.player.add_item("Emergency Flare")
            self.player.add_clarity(1, "you prepare before the wound opens")
            type_text("You find a bacta patch and an emergency flare in the cargo hold. "
                       "Then you hear Padmé scream.",
                       color=Fore.YELLOW)
            self.player.flags["padme_choked"] = True

        pause()
        return "obiwan_force_echo"

    def scene_obiwan_force_echo(self):
        """Obi-Wan senses the larger trap around the duel."""
        cinematic_beat("A QUIET VOICE", HOLOCRON_ART, Fore.CYAN,
                       "The Force has not abandoned you")
        show_portrait("qui-gon", Fore.CYAN)

        type_text("For one impossible heartbeat, the roar of Mustafar falls away. "
                   "You smell rain on Naboo, engine oil on Tatooine, and the library "
                   "dust of the Temple before it burned.",
                   color=Fore.WHITE)
        type_dialogue("Qui-Gon", "The Sith do not merely kill people, Obi-Wan. They arrange "
                       "people so they kill themselves.", Fore.CYAN)
        print()
        type_text("The words settle like a hand on your shoulder. This duel is real, but "
                   "it is also staged: Palpatine's theatre, written in grief.",
                   color=Fore.YELLOW)

        choice = show_choices([
            "Listen for Anakin beneath Vader",
            "Stabilize Padmé first; no victory matters if she dies",
            "Send a coded warning to Bail Organa",
            "Seal your heart. Duty must be clean."
        ])

        if choice == 1:
            self.player.shift_morality(2, "compassion sharpened into focus")
            self.player.change_bond("brotherhood", 2, "you listen for your brother")
            self.player.add_clarity(2, "the duel is a trap")
            self.player.flags["heard_quigon"] = True
        elif choice == 2:
            self.player.change_bond("padme", 2, "you protect the innocent first")
            self.player.add_item("Medpac Beacon")
            self.player.flags["padme_stabilized"] = True
            type_text("You prime the medbay beacon. Padmé's pulse steadies just enough.",
                       color=Fore.CYAN)
        elif choice == 3:
            self.player.add_clarity(2, "the rebellion gets its first warning")
            self.player.flags["bail_warned"] = True
            self.player.discover_secret(
                "Bail Warned",
                "A coded packet leaves Mustafar before the Empire can lock the channels."
            )
        else:
            self.player.shift_morality(-1, "duty without tenderness")
            self.player.change_bond("brotherhood", -2, "you bury the brother to fight the Sith")
            type_text("You close the door inside yourself. It helps. That frightens you.",
                       color=Fore.WHITE + Style.DIM)

        pause()
        return "obiwan_confrontation"

    def scene_obiwan_confrontation(self):
        """Obi-Wan confronts Anakin with words before blades."""
        clear_screen()
        header_box("CONFRONTATION", "Master and Apprentice", Fore.CYAN)

        type_dialogue(self.player.name, "Let her go, Anakin.", Fore.CYAN)
        type_dialogue("Anakin", "What have you and she been up to?", Fore.RED)

        choice = show_choices([
            "'Your anger and lust for power have already done that.'",
            "'I have failed you, Anakin. I have failed you.'",
            "'There is still good in you. I can feel it.'",
            "'This duel is exactly what Sidious wants.'"
        ])

        if choice == 1:
            self.player.change_bond("brotherhood", -1, "truth lands as judgment")
            type_dialogue("Anakin", "Don't lecture me, Obi-Wan. I see through the lies "
                           "of the Jedi.", Fore.RED)
        elif choice == 2:
            self.player.shift_morality(1, "Humility before pride")
            self.player.change_bond("brotherhood", 1, "you own your failure")
            type_dialogue("Anakin", "I should have known the Jedi were plotting to take over.",
                           Fore.RED)
            type_dialogue(self.player.name, "Anakin, Chancellor Palpatine is evil!", Fore.CYAN)
            type_dialogue("Anakin", "From my point of view, the Jedi are evil!", Fore.RED)
        elif choice == 3:
            self.player.shift_morality(2, "Faith in your brother")
            self.player.change_bond("brotherhood", 2, "you call him by name inside the dark")
            self.player.flags["appealed_to_good"] = True
            type_text("Anakin hesitates. Just for a moment, something flickers in his "
                       "yellow eyes. Then it's gone.",
                       color=Fore.YELLOW)
            type_dialogue("Anakin", "You don't know the power of the dark side. "
                           "I must obey my master.", Fore.RED)
        else:
            if self.player.clarity >= 2:
                self.player.shift_morality(2, "you name the trap")
                self.player.change_bond("brotherhood", 2, "you fight Sidious's script")
                self.player.flags["exposed_sidious_trap"] = True
                self.player.flags["appealed_to_good"] = True
                type_dialogue(self.player.name, "He chose this place, this timing, this wound. "
                               "He is making us finish his work.", Fore.CYAN)
                type_dialogue("Anakin", "Liar.", Fore.RED)
                type_text("But he says it too quickly. The word lands wrong.",
                           color=Fore.YELLOW)
            else:
                self.player.shift_morality(0)
                type_text("You sense the shape of a deeper trap, but you cannot prove it. "
                           "Anakin hears only another Jedi accusation.",
                           color=Fore.WHITE + Style.DIM)

        type_dialogue("Anakin", "If you're not with me, then you're my enemy.", Fore.RED)
        type_dialogue(self.player.name, "Only a Sith deals in absolutes. "
                       "I will do what I must.", Fore.CYAN)

        pause()
        return "obiwan_duel"

    def scene_obiwan_duel(self):
        """The lightsaber duel — Obi-Wan vs. Anakin."""
        clear_screen()
        animate_frames(SABER_LOCK_FRAMES, Fore.YELLOW, cycles=1, delay=0.15)
        print(f"{Fore.YELLOW}{LIGHTSABER_CLASH}{Style.RESET_ALL}")
        header_box("⚔  THE DUEL  ⚔", "Obi-Wan vs. Anakin", Fore.CYAN)

        type_text("You ignite your lightsaber. Anakin does the same. "
                   "The heat of Mustafar is nothing compared to the fire between you.",
                   color=Fore.YELLOW)

        anakin = Enemy(
            name="Anakin Skywalker",
            health=130,
            max_health=130,
            attack_power=22,
            defense=10,
            dialogue=[
                "Don't make me destroy you, Master!",
                "You hesitate... the flaw of compassion.",
                "I have brought peace and security to my new Empire!",
                "You underestimate my power!",
            ]
        )

        # If Obi-Wan appealed to Anakin's good side, Anakin fights less fiercely
        if self.player.flags.get("appealed_to_good"):
            anakin.attack_power -= 4
            type_text("Your earlier words echo in Anakin's mind. His strikes are "
                       "powerful but conflicted.",
                       color=Fore.YELLOW + Style.DIM)
        if self.player.flags.get("exposed_sidious_trap"):
            anakin.attack_power -= 3
            anakin.defense = max(0, anakin.defense - 2)
            type_text("The idea of Sidious's trap gnaws at him. Every third strike is "
                       "rage. Every fourth is doubt.",
                       color=Fore.MAGENTA + Style.DIM)
        if self.player.flags.get("padme_stabilized"):
            self.player.force_power = min(self.player.max_force, self.player.force_power + 15)
            type_text("Knowing Padmé is breathing steadies your connection to the Force.",
                       color=Fore.CYAN + Style.DIM)

        result = run_combat(self.player, anakin)

        if result == "victory":
            return "obiwan_crumbling_facility"
        else:
            return "obiwan_ending_defeat"

    def scene_obiwan_crumbling_facility(self):
        """Obi-Wan must choose what to save as the facility collapses."""
        play_set_piece("lava_chase", cycles=1, delay=0.12)
        header_box("REFINERY COLLAPSE", "The duel spills into disaster", Fore.CYAN)

        type_text("Your final exchange shatters the control gantry. Magma pressure alarms "
                   "howl across the facility. Below, Padmé's ship trembles. Above, Anakin "
                   "scrambles toward the open lava bank.",
                   color=Fore.WHITE)

        choice = show_choices([
            "Pursue Anakin immediately",
            "Use the Emergency Flare to guide rescuers to Padmé",
            "Send Bail Organa the proof before the channel dies",
            "Slow down and speak Anakin's name through the Force"
        ])

        if choice == 1:
            self.player.shift_morality(0)
            type_text("You pursue. Duty first. The galaxy may survive you being cold.",
                       color=Fore.CYAN)
        elif choice == 2 and "Emergency Flare" in self.player.inventory:
            self.player.remove_item("Emergency Flare")
            self.player.change_bond("padme", 2, "you make sure she is found")
            self.player.flags["padme_rescue_marked"] = True
            type_text("The flare cuts upward through ash: a white star over the landing pad.",
                       color=Fore.YELLOW)
        elif choice == 2:
            type_text("You reach for a flare you never took. The ash swallows the platform.",
                       color=Fore.RED)
            self.player.take_damage(10, "falling debris")
        elif choice == 3:
            self.player.add_clarity(1, "truth escapes Mustafar")
            self.player.flags["bail_warned"] = True
            self.player.discover_secret(
                "The First Packet",
                "Before the duel ends, Bail Organa receives enough truth to begin resisting."
            )
        else:
            self.player.shift_morality(2, "you refuse to fight a mask alone")
            self.player.change_bond("brotherhood", 2, "you call for Anakin, not Vader")
            self.player.flags["force_called_anakin"] = True
            type_text("Across the lava, Anakin flinches as if someone touched a bruise.",
                       color=Fore.YELLOW)

        pause()
        return "obiwan_high_ground"

    def scene_obiwan_high_ground(self):
        """Obi-Wan reaches the high ground — the iconic moment."""
        clear_screen()
        header_box("THE HIGH GROUND", "The Final Moment", Fore.CYAN)

        type_text("You leap to the embankment above. Anakin stands below, lava churning "
                   "behind him, rage burning in his eyes.",
                   color=Fore.WHITE)
        print()
        type_dialogue(self.player.name, "It's over, Anakin! I have the high ground.", Fore.CYAN)
        type_dialogue("Anakin", "You underestimate my power!", Fore.RED)

        choices = [
            "'Don't try it.'",
            "Throw your lightsaber aside and plead with him one last time",
            "Use the Force to push him back from the edge, saving him from himself"
        ]
        if self.player.flags.get("exposed_sidious_trap") or self.player.flags.get("bail_warned"):
            choices.append("Show him Sidious's trap and refuse the script")

        choice = show_choices(choices)

        if choice == 1:
            type_text("He leaps. Your blade moves on instinct, severing his legs and arm. "
                       "He tumbles down the slope, rolling to a stop at the lava's edge. "
                       "His robes catch fire.",
                       color=Fore.RED)
            return "obiwan_ending_canon"
        elif choice == 2:
            self.player.shift_morality(3, "You risk everything for peace")
            if self.player.flags.get("appealed_to_good"):
                return "obiwan_ending_miracle"
            else:
                type_text("You throw your lightsaber aside. Anakin stares at you, "
                           "uncomprehending. Then he attacks.",
                           color=Fore.RED)
                self.player.take_damage(40, "Anakin's fury")
                if self.player.health > 0:
                    type_text("You barely survive. But you could not reach him. "
                               "The boy is truly gone.",
                               color=Fore.WHITE + Style.DIM)
                    return "obiwan_ending_canon"
                else:
                    return "obiwan_ending_defeat"
        elif choice == 3:
            self.player.shift_morality(2, "Compassion over victory")
            if self.player.use_force(40):
                type_text("You reach out with the Force — not to attack, but to pull "
                           "Anakin back from the edge. He flies backward, slamming into "
                           "the wall, dazed but alive. Whole.",
                           color=Fore.CYAN)
                return "obiwan_ending_mercy"
            else:
                type_text("You don't have enough strength left. Anakin leaps.",
                           color=Fore.RED)
                return "obiwan_ending_canon"
        else:
            if (self.player.bond_brotherhood >= 7 and
                    (self.player.flags.get("force_called_anakin") or self.player.flags.get("heard_quigon"))):
                self.player.shift_morality(4, "you break the Sith script")
                return "obiwan_ending_broken_mask"
            type_text("You show him every piece of the trap, but the wound is still too "
                       "fresh. He leaps with tears in his eyes.",
                       color=Fore.YELLOW)
            return "obiwan_ending_canon"

    # ── Obi-Wan Endings ──

    def scene_obiwan_ending_canon(self):
        """The canonical ending — Obi-Wan leaves Anakin burning."""
        clear_screen()
        print(f"{Fore.CYAN}{ENDING_ART_LIGHT}{Style.RESET_ALL}")

        type_dialogue(self.player.name, "You were the Chosen One! It was said that you "
                       "would destroy the Sith, not join them. You were to bring balance "
                       "to the Force, not leave it in darkness.", Fore.CYAN)
        print()
        type_dialogue("Anakin", "I HATE YOU!", Fore.RED)
        print()
        type_dialogue(self.player.name, "You were my brother, Anakin. I loved you.",
                       Fore.CYAN)
        print()
        type_text("You pick up Anakin's lightsaber and walk away. The heat at your "
                   "back is nothing compared to the cold in your chest.",
                   color=Fore.WHITE + Style.DIM)
        self._show_stats("THE FAITHFUL JEDI — DUTY FULFILLED")
        return None

    def scene_obiwan_ending_defeat(self):
        """Obi-Wan falls in combat."""
        clear_screen()
        header_box("FALLEN", "The Jedi Falls", Fore.RED)
        type_text("You fall. Anakin stands over you, his lightsaber humming. "
                   "The last thing you see is the yellow of his eyes — not Anakin's eyes. "
                   "A stranger's.",
                   color=Fore.RED)
        print()
        type_text("Without Obi-Wan, there is no one to watch over Luke on Tatooine. "
                   "The galaxy's last hope dies before it's born.",
                   color=Fore.RED + Style.DIM)
        self._show_stats("THE JEDI FALLS — DARKNESS REIGNS")
        return None

    def scene_obiwan_ending_miracle(self):
        """Secret ending: Obi-Wan's faith actually reaches Anakin."""
        clear_screen()
        print(f"{Fore.YELLOW}{ENDING_ART_REDEMPTION}{Style.RESET_ALL}")

        type_text("Your lightsaber clatters to the ground. You stand unarmed before "
                   "the most dangerous man in the galaxy, arms open.",
                   color=Fore.CYAN)
        print()
        type_dialogue(self.player.name, "Then strike me down. But know that I forgive "
                       "you. And I will always love you, brother.", Fore.CYAN)
        print()
        type_text("Anakin's lightsaber shakes. His breathing is ragged. The yellow in "
                   "his eyes flickers — brown, yellow, brown.",
                   color=Fore.YELLOW)
        print()
        type_text("The lightsaber deactivates. Anakin collapses, and he weeps like the "
                   "nine-year-old boy who left his mother on Tatooine.",
                   color=Fore.WHITE)
        print()
        type_text("It will take years. The damage cannot be undone in a day, or a year, "
                   "or perhaps ever. But on this day, on this river of fire, a brother "
                   "reached through the dark and pulled another one back.",
                   color=Fore.YELLOW + Style.BRIGHT)
        self._show_stats("✦ THE MIRACLE — BROTHERS REUNITED ✦")
        return None

    def scene_obiwan_ending_mercy(self):
        """Ending: Obi-Wan saves Anakin from himself physically."""
        clear_screen()
        print(f"{Fore.CYAN}{ENDING_ART_LIGHT}{Style.RESET_ALL}")

        type_text("Anakin lies against the wall, dazed. You restrain him with Force "
                   "bindings and call for Senator Organa's ship.",
                   color=Fore.CYAN)
        print()
        type_text("They put him in a cell on Alderaan. Some days he rages. Some days "
                   "he weeps. Some days he is the boy you remember. You visit him every "
                   "week, without fail, for nineteen years.",
                   color=Fore.WHITE)
        print()
        type_text("The road is long, but you walk it together.",
                   color=Fore.CYAN + Style.BRIGHT)
        self._show_stats("THE LONG ROAD — MERCY ENDURES")
        return None

    def scene_obiwan_ending_broken_mask(self):
        """Secret Obi-Wan ending: the staged tragedy fails."""
        clear_screen()
        print(f"{Fore.YELLOW}{ENDING_ART_REDEMPTION}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{JEDI_BEACON_ART}{Style.RESET_ALL}")

        type_text("You do not throw away your lightsaber. You do not raise it either. "
                   "You hold Sidious's lie between you and Anakin like a mirror.",
                   color=Fore.CYAN)
        print()
        type_dialogue(self.player.name, "He wanted me to make you into a wound he could "
                       "wear as armor. I will not.", Fore.CYAN)
        type_dialogue("Anakin", "I killed them.", Fore.RED)
        type_dialogue(self.player.name, "Yes. And if there is any justice left in the "
                       "galaxy, you will spend the rest of your life answering for it. "
                       "But not as his slave.", Fore.CYAN)
        print()
        type_text("The saber falls from Anakin's hand before he does. On Alderaan, Bail "
                   "Organa receives your warning. In the Senate, Padmé wakes to a war "
                   "that has not yet learned its own name.",
                   color=Fore.WHITE)
        self._show_stats("SECRET ENDING — THE BROKEN MASK")
        return None

    # ══════════════════════════════════════════════════════════════════════
    #  UTILITY METHODS
    # ══════════════════════════════════════════════════════════════════════

    def _show_stats(self, title: str):
        """Display the end-of-game statistics screen."""
        print()
        horizontal_rule("═", Fore.YELLOW)
        centered(title, Fore.YELLOW + Style.BRIGHT)
        horizontal_rule("═", Fore.YELLOW)
        print()

        # Morality summary
        if self.player.morality >= 5:
            alignment = "Beacon of Light"
        elif self.player.morality >= 2:
            alignment = "Light Side"
        elif self.player.morality >= -1:
            alignment = "Conflicted"
        elif self.player.morality >= -4:
            alignment = "Dark Side"
        else:
            alignment = "Consumed by Darkness"

        stats = [
            ("Player", self.player.name),
            ("Character", self.player.character.title()),
            ("Alignment", alignment),
            ("Morality Score", str(self.player.morality)),
            ("Clarity", str(self.player.clarity)),
            ("Padme Bond", str(self.player.bond_padme)),
            ("Brotherhood Bond", str(self.player.bond_brotherhood)),
            ("Health Remaining", f"{self.player.health}/{self.player.max_health}"),
            ("Choices Made", str(self.player.choices_made)),
            ("Items Found", str(len(self.player.inventory))),
            ("Secrets Found", str(self.player.secrets_found)),
            ("Memory Shards", str(len(self.player.memory_shards))),
        ]

        for label, value in stats:
            print(f"  {Fore.WHITE}{Style.DIM}{label + ':':<22}{Style.RESET_ALL}"
                  f"{Fore.YELLOW}{value}{Style.RESET_ALL}")

        if self.player.codex:
            print()
            print(f"  {Fore.BLUE}{Style.BRIGHT}Codex:{Style.RESET_ALL}")
            for entry in self.player.codex[-5:]:
                print(f"  {Fore.WHITE}{Style.DIM}- {entry}{Style.RESET_ALL}")

        print()
        horizontal_rule("─", Fore.WHITE + Style.DIM)
        centered("Thank you for playing DUEL OF FATES", Fore.WHITE + Style.DIM)
        centered("May the Force be with you.", Fore.YELLOW)
        horizontal_rule("─", Fore.WHITE + Style.DIM)

        delete_save(silent=True)  # Completed runs should not resume from an old autosave

        # Offer to play again

        print()
        choice = show_choices(["Play Again", "Quit"])
        if choice == 1:
            self.player = PlayerState(current_scene="title")
            self.running = True
        else:
            self.running = False


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        engine = GameEngine()
        engine.run()
    except KeyboardInterrupt:
        if 'engine' in locals() and getattr(engine, 'player', None):
            save_game(engine.player, silent=True)
        print(f"\n\n  {Fore.YELLOW}Progress saved. The Force will be with you... always.{Style.RESET_ALL}\n")
        sys.exit(0)
    finally:
        audio.stop_music()
