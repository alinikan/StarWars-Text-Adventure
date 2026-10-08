"""True-color terminal half-block pixels, camera, HUD, and ASCII fallback."""

import math
from dataclasses import dataclass

from .content import PALETTE, SPRITES, TILE_SIZE


@dataclass
class RenderOptions:
    ascii_mode: bool = False
    reduced_motion: bool = False


class Pixels:
    def __init__(self, width, height, background=(12, 17, 18)):
        self.width, self.height = width, height
        self.rows = [[background] * width for _ in range(height)]

    def set(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.rows[y][x] = color

    def sprite(self, x, y, sprite, palette=PALETTE, flash=False):
        for yy, row in enumerate(sprite):
            for xx, value in enumerate(row):
                if value in palette:
                    self.set(x + xx, y + yy, (255, 248, 210) if flash else palette[value])

    def terminal_lines(self):
        lines = []
        for y in range(0, self.height, 2):
            line, previous = [], None
            for x in range(self.width):
                top, bottom = self.rows[y][x], self.rows[y + 1][x]
                colors = (top, bottom)
                if colors != previous:
                    line.append("\x1b[38;2;{};{};{}m\x1b[48;2;{};{};{}m".format(*top, *bottom))
                    previous = colors
                line.append("\u2580")
            lines.append("".join(line) + "\x1b[0m")
        return lines


def camera(world, columns, lines):
    tiles_x = max(1, min(world.width, (columns - 4) // TILE_SIZE))
    tiles_y = max(1, min(world.height, (lines - 11) // (TILE_SIZE // 2)))
    left = max(0, min(world.x - tiles_x // 2, world.width - tiles_x))
    top = max(0, min(world.y - tiles_y // 2, world.height - tiles_y))
    return left, top, tiles_x, tiles_y


def world_pixels(world, columns=110, lines=40, reduced_motion=False):
    left, top, width, height = camera(world, columns, lines)
    size = TILE_SIZE
    pixels = Pixels(width * size, height * size)
    phase = 0 if reduced_motion else int(world.now * 4)
    for y in range(height):
        for x in range(width):
            wx, wy = x + left, y + top
            tile = world.tile(wx, wy)
            for py in range(size):
                for px in range(size):
                    if tile == "#":
                        color = (37, 46, 46)
                        if py == 0:
                            color = (78, 88, 85)
                        elif px in (0, size - 1) or py == size - 1:
                            color = (23, 30, 31)
                        elif py == 2 and px == 2 and (wx + wy) % 3 == 0:
                            color = (150, 155, 142)
                        if world.mission.key == "archive" and px == 3 and py in (2, 3):
                            color = (88, 156, 144)
                    elif tile == "~":
                        bright = (wx * 7 + wy * 11 + px + py + phase) % 7
                        color = [(135, 29, 34), (189, 36, 35), (241, 78, 43),
                                 (255, 165, 60)][min(3, bright // 2)]
                    else:
                        color = (21, 27, 28)
                        if px == 0 or py == 0:
                            color = (30, 38, 37)
                        elif py == size - 1:
                            color = (16, 21, 23)
                    pixels.set(x * size + px, y * size + py, color)
            if tile in SPRITES:
                palette = {**PALETTE, "c": PALETTE["e"]} if tile == ">" and world.objective_ready else PALETTE
                pixels.sprite(x * size, y * size, SPRITES[tile], palette)
            elif tile == "r":
                pixels.sprite(x * size, y * size, SPRITES["R"], {**PALETTE, "y": PALETTE["e"]})
    for enemy in world.enemies:
        if enemy.strike_at:
            for wx, wy in enemy.danger:
                x, y = (wx - left) * size, (wy - top) * size
                for px, py in ((0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)):
                    pixels.set(x + px, y + py, (255, 209, 84))
        x, y = (enemy.x - left) * size, (enemy.y - top) * size
        sprite = SPRITES[enemy.kind]
        if enemy.kind == "boss" and world.character == "anakin":
            sprite = SPRITES["obiwan"]
        pixels.sprite(x, y, sprite, flash=enemy.flash_until > world.now and not reduced_motion)
        if enemy.kind == "boss":
            pixels.set(x + size, y + 2, (100, 213, 255))
            pixels.set(x + size, y + 3, (230, 251, 255))
        if enemy.stunned_until > world.now:
            pixels.set(x, y, (195, 125, 241))
    x, y = (world.x - left) * size, (world.y - top) * size
    sprite = list(SPRITES[world.character])
    if not reduced_motion and phase % 2 and world.next_move > world.now:
        sprite[-1] = "..k.k."
    pixels.sprite(x, y, sprite, flash=world.invulnerable_until > world.now and not reduced_motion)
    dx, dy = world.facing
    saber_color = (165, 239, 255) if world.character != "padme" else (240, 219, 139)
    pixels.set(x + 3 + dx * 3, y + 3 + dy * 3, saber_color)
    pixels.set(x + 3 + dx * 4, y + 3 + dy * 4, saber_color)
    pixels.set(x + 2, y - 1, (255, 217, 100))
    pixels.set(x + 3, y - 1, (255, 217, 100))
    if world.guard_until > world.now:
        for px, py in ((0, -1), (1, -1), (2, -1), (3, -1), (4, -1), (5, -1)):
            pixels.set(x + px, y + py, (124, 230, 179))
    for bolt in world.bolts:
        pixels.set(int((bolt.x - left) * size), int((bolt.y - top) * size),
                   (132, 255, 191) if bolt.friendly else (255, 98, 108))
    for effect in world.effects:
        ex, ey = (effect.x - left) * size, (effect.y - top) * size
        for px, py in ((1, 2), (4, 2), (2, 1), (2, 4)):
            pixels.set(ex + px, ey + py, PALETTE[effect.color])
    return pixels


def ascii_world(world, columns, lines):
    width = min(world.width, (columns - 4) // 2)
    height = min(world.height, lines - 11)
    left = max(0, min(world.x - width // 2, world.width - width))
    top = max(0, min(world.y - height // 2, world.height - height))
    grid = [[world.tile(x + left, y + top) for x in range(width)] for y in range(height)]
    for enemy in world.enemies:
        if enemy.strike_at:
            for x, y in enemy.danger:
                if left <= x < left + width and top <= y < top + height and grid[y - top][x - left] == ".":
                    grid[y - top][x - left] = "+"
    for bolt in world.bolts:
        x, y = int(bolt.x), int(bolt.y)
        if left <= x < left + width and top <= y < top + height:
            grid[y - top][x - left] = "=" if bolt.friendly else "*"
    for enemy in world.enemies:
        if left <= enemy.x < left + width and top <= enemy.y < top + height:
            grid[enemy.y - top][enemy.x - left] = "B" if enemy.kind == "boss" else "d"
    grid[world.y - top][world.x - left] = "@"
    return [" ".join(row) for row in grid]


def meter(value, maximum=100, width=8):
    filled = max(0, min(width, math.ceil(value / max(1, maximum) * width)))
    return "[" + "=" * filled + "." * (width - filled) + "]"


def render_frame(world, term, options=None):
    options = options or RenderOptions()
    width, height = term.width, term.height
    if width < 64 or height < 26:
        return [term.bold("TERMINAL TOO SMALL"), "",
                "Resize to at least 64 columns x 26 rows.",
                "The mission is paused. Q returns to the story.",
                "Current size: {} x {}".format(width, height)]
    danger = any(e.strike_at for e in world.enemies)
    rows = [term.bold(term.cyan("DUEL OF FATES")) + " / " + world.mission.title,
            term.dim(world.mission.location + " / " + world.character.upper() + " / " + world.difficulty.upper()),
            term.green("HP " + meter(world.health, world.max_health) + " {:3d}".format(world.health)) +
            "  " + term.cyan("ENERGY {:3d}".format(int(world.energy))) +
            "  STAMINA {:3d}  BACTA {}".format(int(world.stamina), world.medkits),
            term.yellow(world.objective_text) + (term.bold("  ! INCOMING") if danger else "")]
    if options.ascii_mode:
        board = ascii_world(world, width, height)
    else:
        board = world_pixels(world, width, height, options.reduced_motion).terminal_lines()
    board_width = term.length(board[0]) if board else 0
    border = "+" + "-" * board_width + "+"
    rows.append(term.dim(border))
    rows.extend(term.dim("|") + row + term.dim("|") for row in board)
    rows.append(term.dim(border))
    rows.append(term.white(world.navigation_hint))
    rows.append(term.dim("WASD move  J attack  K guard  Space dodge  F power"))
    rows.append(term.dim("E interact  H heal  Tab map  M memory"))
    rows.append(term.dim("P pause  ? controls  Q return to story"))
    return [term.truncate(row, width - 1) for row in rows[:height - 1]]


def puzzle_frame(world, term):
    puzzle = world.puzzle
    rows = [term.bold(term.cyan("SENATE CIPHER / RELAY ALIGNMENT")), "",
            "ARCHIVIST: 'They changed the locks. They forgot who wrote them.'", "",
            "TARGET CHECKSUM   [ {} ]   [ {} ]   [ {} ]".format(*puzzle.target), ""]
    rings = [[], [], [], []]
    for index, value in enumerate(puzzle.values):
        color = term.cyan if index == puzzle.selected else term.white
        for row, part in enumerate(("  /-----\\  ", " /   {}   \\ ".format(value),
                                    " \\       / ", "  \\-----/  ")):
            rings[row].append(color(part))
    rows.extend("   ".join(row) for row in rings)
    rows.extend(["", "ACTIVE RING {}    SECURITY ALERT {}/4".format(puzzle.selected + 1, puzzle.mistakes),
                 "Left/right select | Up/down rotate | J/Enter transmit | Q disconnect"])
    return [term.truncate(row, term.width - 1) for row in rows]
