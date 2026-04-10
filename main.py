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
║    • Inventory system with collectible items                               ║
║    • Dynamic narrative that reacts to your choices                         ║
║    • Multiple endings (including secret paths)                             ║
║    • Atmospheric typing effects and rich terminal UI                       ║
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

# Save file location
SAVE_FILE = "duel_of_fates_save.json"

# ──────────────────────────────────────────────────────────────────────────────
# AUDIO ENGINE
# Handles background music and sound effects using pygame.mixer.
# Gracefully degrades if audio files are missing — the game still runs.
# ──────────────────────────────────────────────────────────────────────────────


class AudioEngine:
    """Manages background music and one-shot sound effects."""

    def __init__(self):
        self.enabled = False
        try:
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
            pygame.mixer.music.load(filename)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops)
        except pygame.error:
            pass

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

    def stop_music(self):
        """Fade out and stop background music."""
        if self.enabled:
            pygame.mixer.music.fadeout(2000)


audio = AudioEngine()

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
            time.sleep(speed * 8)  # Pause longer at sentence boundaries
        elif char == ",":
            time.sleep(speed * 4)
        elif char == "\n":
            time.sleep(speed * 2)
        else:
            time.sleep(speed)
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
        time.sleep(TYPE_SPEED_FAST)
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
    if player.inventory:
        items = ", ".join(player.inventory)
        print(f"{Style.DIM}│ {Fore.MAGENTA}Inventory: {items}{Style.RESET_ALL}{Style.DIM}")
    print(f"└{'─' * (TERMINAL_WIDTH - 2)}┘{Style.RESET_ALL}")


def show_choices(choices: list[str]) -> int:
    """
    Display numbered choices and return the player's valid selection.

    Args:
        choices: List of choice description strings.

    Returns:
        The 1-based index of the selected choice.
    """
    print()
    for i, choice in enumerate(choices, 1):
        print(f"  {Fore.YELLOW}{Style.BRIGHT}[{i}]{Style.RESET_ALL} {choice}")
    print()

    while True:
        try:
            raw = input(f"  {Fore.YELLOW}▸ {Style.RESET_ALL}")
            selection = int(raw)
            if 1 <= selection <= len(choices):
                return selection
            print(f"  {Fore.RED}Choose a number between 1 and {len(choices)}.{Style.RESET_ALL}")
        except ValueError:
            print(f"  {Fore.RED}Enter a number.{Style.RESET_ALL}")


def pause(prompt: str = "Press Enter to continue..."):
    """Wait for the player to press Enter before proceeding."""
    input(f"\n  {Fore.WHITE}{Style.DIM}{prompt}{Style.RESET_ALL}")


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
        else:
            indicator = f"{Fore.RED}  ✦ Dark side shift"
        if reason:
            indicator += f" — {reason}"
        print(f"{indicator}{Style.RESET_ALL}")

    def add_item(self, item: str):
        """Add an item to inventory and notify the player."""
        if item not in self.inventory:
            self.inventory.append(item)
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
        print(f"  {Fore.GREEN}+ Restored {amount} HP{Style.RESET_ALL}")

    def take_damage(self, amount: int, source: str = ""):
        """
        Apply damage to the player and display it.
        Returns True if the player is still alive.
        """
        self.health = max(0, self.health - amount)
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
        actions = ["⚔ Strike", "🛡 Defend", "✦ Force Push (20 FP)", "✦ Force Heal (30 FP)"]
        if "Thermal Detonator" in player.inventory:
            actions.append("💣 Throw Thermal Detonator")

        choice = show_choices(actions)

        if choice == 1:  # Strike
            # Damage calculation with a small random spread
            base_dmg = random.randint(12, 22)
            if defending:
                base_dmg = int(base_dmg * 0.6)  # Reduced damage while defensive
                defending = False
            crit = random.random() < 0.15  # 15% crit chance
            if crit:
                base_dmg = int(base_dmg * 1.8)
                print(f"  {Fore.YELLOW}{Style.BRIGHT}★ CRITICAL HIT!{Style.RESET_ALL}")
            enemy.health = max(0, enemy.health - base_dmg)
            print(f"  {Fore.GREEN}You strike for {base_dmg} damage!{Style.RESET_ALL}")

        elif choice == 2:  # Defend
            defending = True
            player.stamina = min(100, player.stamina + 15)
            print(f"  {Fore.BLUE}You brace for the next attack. (+15 stamina){Style.RESET_ALL}")

        elif choice == 3:  # Force Push
            if player.use_force(20):
                dmg = random.randint(25, 40)
                enemy.health = max(0, enemy.health - dmg)
                print(f"  {Fore.CYAN}The Force surges through you — {dmg} damage!{Style.RESET_ALL}")
                # Small chance to stun (enemy skips next attack)
                if random.random() < 0.3:
                    print(f"  {Fore.CYAN}{enemy.name} staggers, stunned!{Style.RESET_ALL}")
                    continue  # Skip enemy turn

        elif choice == 4:  # Force Heal
            if player.use_force(30):
                heal_amt = random.randint(20, 35)
                player.heal(heal_amt)

        elif choice == 5:  # Thermal Detonator
            player.remove_item("Thermal Detonator")
            dmg = random.randint(40, 60)
            enemy.health = max(0, enemy.health - dmg)
            print(f"  {Fore.YELLOW}{Style.BRIGHT}💥 BOOM! {dmg} damage!{Style.RESET_ALL}")

        # ── Check if enemy is defeated ──
        if enemy.health <= 0:
            print(f"\n  {Fore.GREEN}{Style.BRIGHT}{enemy.name} has been defeated!{Style.RESET_ALL}")
            pause()
            return "victory"

        # ── Enemy turn ──
        time.sleep(0.5)
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


def save_game(player: PlayerState):
    """Serialize the player state to a JSON file."""
    data = asdict(player)
    data["save_timestamp"] = datetime.now().isoformat()
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\n  {Fore.GREEN}✓ Game saved.{Style.RESET_ALL}")
    except IOError as e:
        print(f"\n  {Fore.RED}Save failed: {e}{Style.RESET_ALL}")


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

    # ── Main loop ──

    def run(self):
        """Start the game loop, dispatching to scene methods."""
        audio.play_music("song.mp3", volume=0.4)

        while self.running:
            scene_method = getattr(self, f"scene_{self.player.current_scene}", None)
            if scene_method is None:
                print(f"{Fore.RED}ERROR: Unknown scene '{self.player.current_scene}'{Style.RESET_ALL}")
                self.running = False
                break
            next_scene = scene_method()
            if next_scene is None:
                self.running = False
            else:
                self.player.current_scene = next_scene
                self.player.choices_made += 1

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
        centered("A Text-Based Adventure", Fore.WHITE + Style.DIM)
        print()
        horizontal_rule("─", Fore.RED + Style.DIM)

        options = ["New Game"]
        saved = load_game()
        if saved:
            options.append(f"Continue as {saved.name} ({saved.character.title()})")
        options.append("Quit")

        choice = show_choices(options)

        if choice == 1:
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
        time.sleep(1)
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

        choice = show_choices([
            f"{Fore.RED}Anakin Skywalker{Style.RESET_ALL} — The Chosen One, consumed by rage",
            f"{Fore.CYAN}Obi-Wan Kenobi{Style.RESET_ALL} — The faithful Jedi, burdened by duty",
        ])

        if choice == 1:
            self.player.character = "anakin"
            self.player.morality = -1  # Anakin starts slightly dark
            self.player.add_item("Lightsaber (Blue)")
            self.player.flags["has_padme_necklace"] = True
            type_text("You feel the dark side swelling inside you. There is power here — "
                       "power the Jedi were too afraid to use.",
                       color=Fore.RED)
            return "anakin_arrival"
        else:
            self.player.character = "obiwan"
            self.player.morality = 2  # Obi-Wan starts light-aligned
            self.player.add_item("Lightsaber (Blue)")
            self.player.add_item("Jedi Comlink")
            type_text("You feel the weight of what must be done. Anakin was your brother. "
                       "But the boy you trained is gone.",
                       color=Fore.CYAN)
            return "obiwan_arrival"

    # ══════════════════════════════════════════════════════════════════════
    #  ANAKIN PATH
    # ══════════════════════════════════════════════════════════════════════

    def scene_anakin_arrival(self):
        """Anakin arrives on Mustafar after executing the Separatist leaders."""
        clear_screen()
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
            "Meditate on your new power"
        ])

        if choice == 1:
            return "anakin_padme"
        elif choice == 2:
            return "anakin_search"
        else:
            self.player.shift_morality(-1, "You embrace the dark side's power")
            self.player.force_power = min(self.player.max_force, self.player.force_power + 20)
            type_text("You reach out with the Force. The dark side answers eagerly, "
                       "flooding you with raw strength. You feel invincible.",
                       color=Fore.RED)
            pause()
            return "anakin_padme"

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
        return "anakin_padme"

    def scene_anakin_padme(self):
        """The confrontation with Padmé before Obi-Wan reveals himself."""
        clear_screen()
        header_box("LANDING PLATFORM", "Padmé", Fore.RED)

        type_text("Padmé rushes toward you, her face a mask of fear and hope. She reaches "
                   "for your hands.",
                   color=Fore.WHITE)
        type_dialogue("Padmé", "Anakin, I was so worried about you. Obi-Wan told me "
                       "terrible things.", Fore.MAGENTA)

        choice = show_choices([
            "Reassure her: 'I am more powerful than the Chancellor. I can overthrow him.'",
            "Demand to know what Obi-Wan told her",
            "Hold her gently and say nothing"
        ])

        if choice == 1:
            self.player.shift_morality(-1, "Hunger for power")
            type_dialogue("Padmé", "I don't want to hear any more about Obi-Wan. "
                           "Anakin, all I want is your love.", Fore.MAGENTA)
            type_dialogue(self.player.name, "Love won't save you, Padmé. "
                           "Only my new powers can do that.", Fore.RED)
        elif choice == 2:
            type_dialogue(self.player.name, "What lies has he been feeding you?", Fore.RED)
            type_dialogue("Padmé", "He said... you turned to the dark side. "
                           "That you killed younglings.", Fore.MAGENTA)
            self.player.shift_morality(-1, "Deflecting guilt")
        else:
            self.player.shift_morality(1, "A moment of tenderness")
            type_text("For a brief moment, the rage quiets. You hold her, and you "
                       "almost remember who you used to be.",
                       color=Fore.WHITE)
            if "Bacta Patch" in self.player.inventory:
                self.player.heal(10)

        pause()
        return "anakin_obiwan_appears"

    def scene_anakin_obiwan_appears(self):
        """Obi-Wan steps off Padmé's ship. The betrayal."""
        clear_screen()
        header_box("THE BETRAYAL", "Obi-Wan Appears", Fore.RED)

        type_text("Then you see him. Obi-Wan Kenobi steps off the ramp of Padmé's ship, "
                   "his robes billowing in the volcanic wind.",
                   color=Fore.WHITE)

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
            type_text("Your hand rises. The dark side coils around Padmé's throat like a "
                       "serpent. She gasps, clawing at nothing, then collapses.",
                       color=Fore.RED)
            type_dialogue("Obi-Wan", "Let her go, Anakin!", Fore.CYAN)
            self.player.flags["choked_padme"] = True
        elif choice == 2:
            self.player.shift_morality(1, "You resist the urge to harm Padmé")
            type_text("Your fists clench, but you push Padmé behind you and focus your "
                       "rage on the real target.",
                       color=Fore.YELLOW)
            type_dialogue(self.player.name, "You turned her against me!", Fore.RED)
            type_dialogue("Obi-Wan", "You have done that yourself.", Fore.CYAN)
            self.player.flags["choked_padme"] = False
        else:
            self.player.shift_morality(0)
            type_dialogue(self.player.name, "Explain. Now.", Fore.RED)
            type_dialogue("Obi-Wan", "Anakin, Chancellor Palpatine is evil.", Fore.CYAN)
            type_dialogue(self.player.name, "From my point of view, the Jedi are evil!", Fore.RED)
            self.player.flags["choked_padme"] = False

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
            "Say nothing. Ignite your lightsaber."
        ])

        if choice == 1:
            self.player.shift_morality(-1, "Arrogance")
            type_dialogue("Obi-Wan", "Your new Empire?", Fore.CYAN)
            type_dialogue(self.player.name, "If you're not with me, then you're my enemy.", Fore.RED)
            type_dialogue("Obi-Wan", "Only a Sith deals in absolutes. I will do what I must.", Fore.CYAN)
        elif choice == 2:
            self.player.shift_morality(3, "A crack in the darkness")
            self.player.flags["showed_doubt"] = True
            type_text("Obi-Wan's eyes widen. For a heartbeat, hope flickers across his face.",
                       color=Fore.CYAN)
            type_dialogue("Obi-Wan", "It's never too late, Anakin. Come back. Please.", Fore.CYAN)
            # This opens the secret redemption path later
            return "anakin_redemption_choice"
        else:
            self.player.shift_morality(-2, "Cold silence before violence")
            type_text("The hum of your lightsaber fills the silence.",
                       color=Fore.RED)

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
            "Walk away. Leave Mustafar. Leave everything."
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
            self.player.shift_morality(2, "You choose exile over destruction")
            return "anakin_ending_exile"

    def scene_anakin_duel(self):
        """The lightsaber duel with Obi-Wan — full combat encounter."""
        clear_screen()
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

        result = run_combat(self.player, obi_wan)

        if result == "victory":
            return "anakin_high_ground_victory"
        else:
            return "anakin_ending_fall"

    def scene_anakin_high_ground_victory(self):
        """Anakin wins the duel — what does he do with victory?"""
        clear_screen()
        header_box("VICTORY", "Obi-Wan Falls", Fore.RED)

        type_text("Obi-Wan stumbles, his lightsaber clattering to the ground. He kneels "
                   "at the edge of the lava river, breathing hard, beaten.",
                   color=Fore.WHITE)
        print()
        type_dialogue("Obi-Wan", "Then you truly are lost.", Fore.CYAN)

        choice = show_choices([
            "Strike him down. Complete your victory.",
            "Spare him. 'You're not worth killing, old man.'",
            "Offer your hand. 'Come with me. We can overthrow the Emperor together.'"
        ])

        if choice == 1:
            self.player.shift_morality(-4, "You kill your master")
            return "anakin_ending_dark"
        elif choice == 2:
            self.player.shift_morality(2, "Mercy")
            return "anakin_ending_hollow"
        else:
            self.player.shift_morality(1, "An unexpected offer")
            self.player.flags["offered_alliance"] = True
            return "anakin_ending_alliance"

    # ── Anakin Endings ──

    def scene_anakin_ending_dark(self):
        """Ending: Anakin fully embraces the dark side."""
        clear_screen()
        print(f"{Fore.RED}{ENDING_ART_DARK}{Style.RESET_ALL}")
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

    # ══════════════════════════════════════════════════════════════════════
    #  OBI-WAN PATH
    # ══════════════════════════════════════════════════════════════════════

    def scene_obiwan_arrival(self):
        """Obi-Wan arrives on Mustafar, hidden aboard Padmé's ship."""
        clear_screen()
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
            type_text("Through the hull, you hear their voices. Padmé pleading. Anakin's "
                       "voice, cold and unrecognizable. Then a choking sound. A body falling.",
                       color=Fore.WHITE + Style.DIM)
            type_text("You burst out of the ship. Padmé lies unconscious on the platform.",
                       color=Fore.RED)
            self.player.flags["padme_choked"] = True
        elif choice == 2:
            type_text("You stride down the ramp. Anakin sees you before you can speak.",
                       color=Fore.WHITE)
            type_dialogue("Anakin", "YOU! You turned her against me!", Fore.RED)
            self.player.flags["padme_choked"] = False
        else:
            self.player.add_item("Bacta Patch")
            self.player.add_item("Emergency Flare")
            type_text("You find a bacta patch and an emergency flare in the cargo hold. "
                       "Then you hear Padmé scream.",
                       color=Fore.YELLOW)
            self.player.flags["padme_choked"] = True

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
            "'There is still good in you. I can feel it.'"
        ])

        if choice == 1:
            type_dialogue("Anakin", "Don't lecture me, Obi-Wan. I see through the lies "
                           "of the Jedi.", Fore.RED)
        elif choice == 2:
            self.player.shift_morality(1, "Humility before pride")
            type_dialogue("Anakin", "I should have known the Jedi were plotting to take over.",
                           Fore.RED)
            type_dialogue(self.player.name, "Anakin, Chancellor Palpatine is evil!", Fore.CYAN)
            type_dialogue("Anakin", "From my point of view, the Jedi are evil!", Fore.RED)
        else:
            self.player.shift_morality(2, "Faith in your brother")
            self.player.flags["appealed_to_good"] = True
            type_text("Anakin hesitates. Just for a moment, something flickers in his "
                       "yellow eyes. Then it's gone.",
                       color=Fore.YELLOW)
            type_dialogue("Anakin", "You don't know the power of the dark side. "
                           "I must obey my master.", Fore.RED)

        type_dialogue("Anakin", "If you're not with me, then you're my enemy.", Fore.RED)
        type_dialogue(self.player.name, "Only a Sith deals in absolutes. "
                       "I will do what I must.", Fore.CYAN)

        pause()
        return "obiwan_duel"

    def scene_obiwan_duel(self):
        """The lightsaber duel — Obi-Wan vs. Anakin."""
        clear_screen()
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

        result = run_combat(self.player, anakin)

        if result == "victory":
            return "obiwan_high_ground"
        else:
            return "obiwan_ending_defeat"

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

        choice = show_choices([
            "'Don't try it.'",
            "Throw your lightsaber aside and plead with him one last time",
            "Use the Force to push him back from the edge, saving him from himself"
        ])

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
        else:
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
            ("Health Remaining", f"{self.player.health}/{self.player.max_health}"),
            ("Choices Made", str(self.player.choices_made)),
            ("Items Found", str(len(self.player.inventory))),
        ]

        for label, value in stats:
            print(f"  {Fore.WHITE}{Style.DIM}{label + ':':<22}{Style.RESET_ALL}"
                  f"{Fore.YELLOW}{value}{Style.RESET_ALL}")

        print()
        horizontal_rule("─", Fore.WHITE + Style.DIM)
        centered("Thank you for playing DUEL OF FATES", Fore.WHITE + Style.DIM)
        centered("May the Force be with you.", Fore.YELLOW)
        horizontal_rule("─", Fore.WHITE + Style.DIM)

        # Offer to play again
        print()
        choice = show_choices(["Play Again", "Quit"])
        if choice == 1:
            self.player = PlayerState()
            self.player.current_scene = "title"
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
        # Handle Ctrl+C gracefully
        print(f"\n\n  {Fore.YELLOW}The Force will be with you... always.{Style.RESET_ALL}\n")
        sys.exit(0)
    finally:
        audio.stop_music()
