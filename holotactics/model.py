"""Deterministic action simulation, independent of the terminal and sound device."""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder

from .content import MISSIONS, Mission


@dataclass
class Actor:
    kind: str
    x: int
    y: int
    health: int = 50
    max_health: int = 50
    next_move: float = 0.0
    next_attack: float = 0.0
    stunned_until: float = 0.0
    strike_at: float = 0.0
    danger: List[tuple] = field(default_factory=list)
    flash_until: float = 0.0
    defense: int = 0


@dataclass
class Bolt:
    x: float
    y: float
    dx: float
    dy: float
    friendly: bool
    damage: int
    ttl: float = 2.0


@dataclass
class Effect:
    x: int
    y: int
    color: str
    until: float


@dataclass
class Result:
    outcome: str
    mission: str
    score: int
    health: int
    energy: int
    stamina: int
    kills: int
    fragments: int
    memory_found: bool
    seconds: float
    medkits: int


class RingPuzzle:
    """Three independent octal rings with a visible checksum and finite mistakes."""

    def __init__(self):
        self.values = [2, 5, 1]
        self.target = [6, 2, 4]
        self.selected = 0
        self.mistakes = 0
        self.solved = False

    def command(self, key):
        if key in ("left", "right"):
            self.selected = (self.selected + (1 if key == "right" else -1)) % 3
        elif key in ("up", "down"):
            delta = 1 if key == "up" else -1
            self.values[self.selected] = (self.values[self.selected] + delta) % 8
        elif key == "attack":
            self.solved = self.values == self.target
            if not self.solved:
                self.mistakes += 1
        return self.solved


class World:
    def __init__(self, mission="ashwalk", character="anakin", difficulty="standard",
                 health=100, energy=100, stamina=100, boss_health=None,
                 boss_damage=None, boss_defense=0, medkits=1):
        self.mission: Mission = MISSIONS[mission]
        self.character = character
        self.difficulty = difficulty
        self.damage_scale = {"story": 0.55, "standard": 1.0, "veteran": 1.4}[difficulty]
        self.grid = [list(row) for row in self.mission.rows]
        self.height = len(self.grid)
        self.width = len(self.grid[0])
        self.x, self.y = self.find_tile("@")
        self.grid[self.y][self.x] = "."
        self.health = max(0, health)
        self.energy = float(max(0, energy))
        self.stamina = float(max(0, stamina))
        self.max_health = max(100, health)
        self.facing = (1, 0)
        self.now = 0.0
        self.next_move = self.next_attack = self.next_dodge = 0.0
        self.guard_until = self.invulnerable_until = self.next_lava = 0.0
        self.medkits = medkits
        self.kills = self.fragments = self.relays = self.wave = 0
        self.memory_found = False
        self.initial_relays = sum(row.count("R") for row in self.grid)
        self.enemies: List[Actor] = []
        self.bolts: List[Bolt] = []
        self.effects: List[Effect] = []
        self.messages = [self.mission.objective]
        self.signal_until = 0.0
        self.cues: List[str] = []
        self.outcome: Optional[str] = None
        self.puzzle: Optional[RingPuzzle] = None
        self.puzzle_tile: Optional[tuple] = None
        self.boss_damage = boss_damage or 20
        self._path_grid = Grid(matrix=[
            [0 if tile in "#~" else 1 for tile in row] for row in self.grid
        ])
        self._finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        for kind, x, y in self.mission.enemies:
            hp = (boss_health or 125) if kind == "boss" else (34 if kind == "drone" else 48)
            self.enemies.append(Actor(kind, x, y, hp, hp, next_attack=1.2,
                                       defense=boss_defense if kind == "boss" else 0))
        self.wave = 1
        if self.health <= 0:
            self.outcome = "defeat"

    def find_tile(self, tile):
        return next((x, y) for y, row in enumerate(self.grid)
                    for x, value in enumerate(row) if value == tile)

    def tile(self, x, y):
        return self.grid[y][x] if 0 <= x < self.width and 0 <= y < self.height else "#"

    def walkable(self, x, y, enemy=False):
        return self.tile(x, y) not in ("#~" if enemy else "#")

    def occupied(self, x, y, except_actor=None):
        return any(e is not except_actor and e.health > 0 and (e.x, e.y) == (x, y)
                   for e in self.enemies)

    def say(self, text, cue=None):
        self.messages.append(text)
        self.messages = self.messages[-3:]
        self.signal_until = self.now + 2.2
        if cue:
            self.cues.append(cue)

    @property
    def objective_ready(self):
        if self.mission.key == "duel":
            return not self.enemies
        if self.mission.key == "gauntlet":
            return self.wave == self.mission.waves and not self.enemies
        return self.relays == self.initial_relays and (
            self.mission.key != "archive" or self.fragments == 3)

    @property
    def objective_text(self):
        if self.mission.key == "archive":
            return "CIPHERS {}/3  RELAY {}/1  {}".format(
                self.fragments, self.relays, "LIFT OPEN" if self.objective_ready else "LIFT LOCKED")
        if self.mission.key == "ashwalk":
            return "COOLANT {}/2  {}".format(
                self.relays, "LIFT OPEN" if self.objective_ready else "LIFT LOCKED")
        if self.mission.key == "gauntlet":
            return "WAVE {}/3  HOSTILES {}".format(self.wave, len(self.enemies))
        enemy = next(iter(self.enemies), None)
        return "OPPONENT {}/{}".format(enemy.health, enemy.max_health) if enemy else "DUEL WON"

    @property
    def navigation_hint(self):
        dx, dy = self.facing
        nearby = (self.tile(self.x, self.y), self.tile(self.x + dx, self.y + dy))
        if "R" in nearby:
            if self.mission.key == "archive" and self.fragments < 3:
                return "RELAY LOCKED / recover all three cyan cipher fragments."
            return "E / activate this relay" + (" and align the checksum." if self.mission.key == "archive" else ".")
        if ">" in nearby:
            return "E / take the lift." if self.objective_ready else "LIFT LOCKED / complete the objective first."
        if self.now < self.signal_until:
            return self.messages[-1]
        target = ">" if self.objective_ready else "C" if self.mission.key == "archive" and self.fragments < 3 else "R"
        candidates = [(abs(x - self.x) + abs(y - self.y), x, y)
                      for y, row in enumerate(self.grid) for x, tile in enumerate(row) if tile == target]
        if not candidates:
            return self.messages[-1]
        _, x, y = min(candidates)
        direction = []
        if x != self.x:
            direction.append("EAST" if x > self.x else "WEST")
        if y != self.y:
            direction.append("SOUTH" if y > self.y else "NORTH")
        name = {">": "LIFT", "C": "CIPHER", "R": "RELAY"}[target]
        return "NEXT {} / {} / Tab opens the full map".format(name, " + ".join(direction) or "HERE")

    def command(self, command):
        if self.outcome:
            return
        if self.puzzle:
            if command == "quit":
                self.puzzle = None
                self.say("Relay disconnected. The cipher is still recoverable.")
            elif self.puzzle.command(command):
                x, y = self.puzzle_tile
                self.grid[y][x] = "r"
                self.relays += 1
                self.puzzle = None
                self.say("Checksum accepted. A courier is waiting at the lift.", "broadcast")
            elif self.puzzle.mistakes >= 4:
                self.puzzle = None
                self.hurt(8, "Security feedback. Reconnect to try again.")
            return
        directions = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
        if command in directions:
            self.facing = directions[command]
            if self.now >= self.next_move:
                dx, dy = self.facing
                if self.walkable(self.x + dx, self.y + dy) and not self.occupied(self.x + dx, self.y + dy):
                    self.x += dx
                    self.y += dy
                    self.next_move = self.now + 0.10
                    self.pickup()
        elif command == "attack":
            self.attack()
        elif command == "guard" and self.stamina >= 5:
            self.guard_until = self.now + 0.8
        elif command == "dodge" and self.now >= self.next_dodge and self.stamina >= 18:
            self.stamina -= 18
            self.invulnerable_until = self.now + 0.4
            self.next_dodge = self.now + 0.7
            dx, dy = self.facing
            for _ in range(2):
                if self.walkable(self.x + dx, self.y + dy) and not self.occupied(self.x + dx, self.y + dy):
                    self.x += dx
                    self.y += dy
                    self.effects.append(Effect(self.x - dx, self.y - dy, "c", self.now + 0.25))
            self.pickup()
        elif command == "power":
            self.power()
        elif command == "heal":
            if self.medkits and self.health < self.max_health:
                self.health = min(self.max_health, self.health + 35)
                self.medkits -= 1
                self.say("Bacta applied. Breathe.", "heal")
        elif command == "interact":
            self.interact()

    def pickup(self):
        tile = self.tile(self.x, self.y)
        if tile == "H":
            self.medkits += 1
            self.say("Bacta charge recovered.", "heal")
        elif tile == "C":
            self.fragments += 1
            signals = ["FILE 1/3: The list names nurses, teachers, witnesses.",
                       "FILE 2/3: The arrest orders predate the Empire.",
                       "FILE 3/3: The archivist listed herself. Send every name."]
            self.say(signals[self.fragments - 1], "secret")
        elif tile == "!":
            self.memory_found = True
            self.say(self.mission.memory[0] + " / memory recovered.", "memory")
        else:
            return
        self.grid[self.y][self.x] = "."

    def interact(self):
        candidates = [(self.x, self.y), (self.x + self.facing[0], self.y + self.facing[1])]
        for x, y in candidates:
            tile = self.tile(x, y)
            if tile == "R":
                if self.mission.key == "archive":
                    if self.fragments < 3:
                        self.say("Relay encrypted. Recover all three cipher fragments first.")
                    else:
                        self.puzzle = RingPuzzle()
                        self.puzzle_tile = (x, y)
                else:
                    self.grid[y][x] = "r"
                    self.relays += 1
                    self.say("Coolant relay online ({}/2).".format(self.relays), "broadcast")
                return
            if tile == ">":
                if self.objective_ready:
                    self.outcome = "victory"
                    self.say("Mission complete. The signal survives.", "light")
                else:
                    self.say("Lift locked. " + self.mission.objective)
                return
        self.say("No active terminal in reach.")

    def attack(self):
        if self.now < self.next_attack or self.stamina < 8:
            return
        self.stamina -= 8
        self.guard_until = 0
        self.next_attack = self.now + (0.30 if self.character == "padme" else 0.36)
        dx, dy = self.facing
        if self.character == "padme":
            self.bolts.append(Bolt(self.x + 0.5, self.y + 0.5, dx, dy, True, 23))
            self.cues.append("blaster")
            return
        self.cues.append("clash")
        for x in range(self.x - 2, self.x + 3):
            for y in range(self.y - 2, self.y + 3):
                distance = abs(x - self.x) + abs(y - self.y)
                if 0 < distance <= 2 and (x - self.x) * dx + (y - self.y) * dy > 0:
                    if self.line_clear(self.x, self.y, x, y):
                        self.effects.append(Effect(x, y, "c", self.now + 0.15))
                        for enemy in self.enemies:
                            if (enemy.x, enemy.y) == (x, y):
                                self.hit_enemy(enemy, 26)

    def power(self):
        if self.energy < 28:
            self.say("Not enough energy. Give it a moment.")
            return
        self.energy -= 28
        radius = 5 if self.character == "padme" else 3
        for enemy in self.enemies:
            if abs(enemy.x - self.x) + abs(enemy.y - self.y) <= radius:
                if not self.line_clear(self.x, self.y, enemy.x, enemy.y):
                    continue
                self.hit_enemy(enemy, 18 if self.character == "padme" else 22)
                enemy.stunned_until = self.now + 1.5
                enemy.strike_at = 0
                enemy.danger = []
                dx = 0 if enemy.x == self.x else (1 if enemy.x > self.x else -1)
                dy = 0 if enemy.y == self.y else (1 if enemy.y > self.y else -1)
                if self.walkable(enemy.x + dx, enemy.y + dy, enemy=True) and not self.occupied(enemy.x + dx, enemy.y + dy):
                    enemy.x += dx
                    enemy.y += dy
        for y in range(self.y - radius, self.y + radius + 1):
            for x in range(self.x - radius, self.x + radius + 1):
                if abs(x - self.x) + abs(y - self.y) == radius:
                    self.effects.append(Effect(x, y, "m", self.now + 0.35))
        self.bolts = [b for b in self.bolts if b.friendly]
        self.say("Ion pulse: systems disabled." if self.character == "padme" else "Force pulse: space to breathe.", "power")

    def hit_enemy(self, enemy, damage):
        enemy.health -= max(1, damage - enemy.defense // 2)
        enemy.flash_until = self.now + 0.15

    def hurt(self, amount, message):
        if self.now < self.invulnerable_until:
            return
        if self.guard_until > self.now and self.stamina >= 12:
            self.stamina -= 12
            amount = max(1, amount // 5)
            self.cues.append("clash")
            self.say("Guard holds. Keep your footing.")
        else:
            self.say(message, "damage")
        self.health = max(0, self.health - max(1, round(amount * self.damage_scale)))
        self.invulnerable_until = self.now + 0.45
        if self.health <= 0:
            self.outcome = "defeat"

    def line_clear(self, x0, y0, x1, y1):
        steps = max(abs(x1 - x0), abs(y1 - y0))
        for step in range(1, steps + 1):
            x = round(x0 + (x1 - x0) * step / steps)
            y = round(y0 + (y1 - y0) * step / steps)
            if self.tile(x, y) == "#":
                return False
        return True

    def _step_toward(self, enemy):
        if not self.walkable(self.x, self.y, enemy=True):
            return
        self._path_grid.cleanup()
        path, _ = self._finder.find_path(
            self._path_grid.node(enemy.x, enemy.y),
            self._path_grid.node(self.x, self.y), self._path_grid)
        if len(path) > 1:
            x, y = path[1].x, path[1].y
            if not self.occupied(x, y, enemy) and (x, y) != (self.x, self.y):
                enemy.x, enemy.y = x, y

    def _enemy_turn(self, enemy):
        if enemy.stunned_until > self.now or enemy.health <= 0:
            return
        distance = abs(enemy.x - self.x) + abs(enemy.y - self.y)
        ranged = enemy.kind in ("trooper", "drone")
        if enemy.strike_at:
            if self.now >= enemy.strike_at:
                if ranged:
                    dx, dy = self.x - enemy.x, self.y - enemy.y
                    length = max(1, math.hypot(dx, dy))
                    self.bolts.append(Bolt(enemy.x + 0.5, enemy.y + 0.5,
                                           dx / length, dy / length, False, 12))
                elif (self.x, self.y) in enemy.danger:
                    self.hurt(self.boss_damage if enemy.kind == "boss" else 14,
                              "Saber impact." if enemy.kind == "boss" else "Security droid strike.")
                enemy.strike_at = 0
                enemy.danger = []
                enemy.next_attack = self.now + (0.65 if enemy.kind == "boss" else 1.1)
            return
        reach = 8 if ranged else (2 if enemy.kind == "boss" else 1)
        if distance <= reach and self.now >= enemy.next_attack and self.line_clear(enemy.x, enemy.y, self.x, self.y):
            enemy.strike_at = self.now + (0.8 if ranged else 0.65)
            if ranged:
                enemy.danger = [(self.x, self.y)]
            else:
                enemy.danger = [(x, y) for y in range(enemy.y - reach, enemy.y + reach + 1)
                                for x in range(enemy.x - reach, enemy.x + reach + 1)
                                if 0 < abs(x - enemy.x) + abs(y - enemy.y) <= reach]
            if enemy.kind == "boss" and enemy.health < enemy.max_health // 2:
                enemy.strike_at -= 0.12
            return
        if distance > (4 if ranged else 1) and self.now >= enemy.next_move:
            self._step_toward(enemy)
            enemy.next_move = self.now + (0.23 if enemy.kind == "boss" else 0.38)

    def _update_bolts(self, dt):
        remaining = []
        for bolt in self.bolts:
            bolt.ttl -= dt
            alive = bolt.ttl > 0
            substeps = max(1, math.ceil(dt * 8 / 0.25))
            for _ in range(substeps):
                bolt.x += bolt.dx * dt * 8 / substeps
                bolt.y += bolt.dy * dt * 8 / substeps
                if self.tile(int(bolt.x), int(bolt.y)) == "#":
                    alive = False
                    break
                if bolt.friendly:
                    enemy = next((e for e in self.enemies if e.health > 0 and
                                  math.hypot(e.x + 0.5 - bolt.x, e.y + 0.5 - bolt.y) < 0.65), None)
                    if enemy:
                        self.hit_enemy(enemy, bolt.damage)
                        alive = False
                        break
                elif math.hypot(self.x + 0.5 - bolt.x, self.y + 0.5 - bolt.y) < 0.65:
                    self.hurt(bolt.damage, "Blaster impact.")
                    alive = False
                    break
            if alive:
                remaining.append(bolt)
        self.bolts = remaining

    def update(self, dt):
        if self.outcome or self.puzzle:
            return
        dt = max(0, min(dt, 0.1))
        self.now += dt
        self.energy = min(100, self.energy + dt * 4)
        self.stamina = min(100, self.stamina + dt * (5 if self.guard_until > self.now else 17))
        if self.tile(self.x, self.y) == "~" and self.now >= self.next_lava:
            self.next_lava = self.now + 0.6
            self.hurt(16, "The lava burns. Move onto the gantry!")
        for enemy in self.enemies:
            self._enemy_turn(enemy)
            if self.outcome:
                break
        if not self.outcome:
            self._update_bolts(dt)
        dead = [e for e in self.enemies if e.health <= 0]
        self.kills += len(dead)
        for enemy in dead:
            self.effects.append(Effect(enemy.x, enemy.y, "y", self.now + 0.4))
            self.say("Hostile disabled.", "secret")
        self.enemies = [e for e in self.enemies if e.health > 0]
        self.effects = [e for e in self.effects if e.until > self.now]
        if not self.outcome and not self.enemies:
            if self.mission.key == "duel":
                self.outcome = "victory"
            elif self.wave < self.mission.waves:
                self.wave += 1
                spawn_points = [(3, 3), (22, 3), (3, 11), (22, 11)]
                for index, (x, y) in enumerate(spawn_points[:self.wave + 1]):
                    if (x, y) == (self.x, self.y):
                        y = 2 if y == 3 else 12
                    kind = "drone" if self.wave == 3 and index == 1 else "droid"
                    hp = 38 + self.wave * 5
                    self.enemies.append(Actor(kind, x, y, hp, hp, next_move=self.now + 1.0,
                                               next_attack=self.now + 1.2))
                self.health = min(self.max_health, self.health + 15)
                self.say("Wave {}. The Temple remembers.".format(self.wave), "broadcast")

    def result(self):
        won = self.outcome == "victory"
        score = max(0, (500 if won else 0) + self.kills * 100 + self.fragments * 150 +
                    self.relays * 200 + (250 if self.memory_found else 0) +
                    (self.health * 5 if won else 0) - int(self.now))
        return Result(self.outcome or "abandoned", self.mission.key, score,
                      self.health, int(self.energy), int(self.stamina), self.kills,
                      self.fragments, self.memory_found, round(self.now, 1), self.medkits)
