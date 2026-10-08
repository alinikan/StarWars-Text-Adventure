"""Original mission layouts, character sprites, and encounter briefings."""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Mission:
    key: str
    title: str
    location: str
    briefing: str
    objective: str
    rows: Tuple[str, ...]
    enemies: Tuple[tuple, ...]
    memory: Tuple[str, str]
    mood: str = "tension"
    waves: int = 1


def layout(walls=(), lava=(), objects=(), width=26, height=14):
    """Build a bounded tile map; coordinates are (x, y)."""
    grid = [["." for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            if x in (0, width - 1) or y in (0, height - 1):
                grid[y][x] = "#"
    for x, y, w, h in walls:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                grid[yy][xx] = "#"
    for x, y, w, h in lava:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                grid[yy][xx] = "~"
    for x, y, tile in objects:
        grid[y][x] = tile
    return tuple("".join(row) for row in grid)


MISSIONS = {
    "ashwalk": Mission(
        "ashwalk", "ASHES OF THE FOUNDRY", "MUSTAFAR / SERVICE GANTRY",
        "The refinery has locked its workers inside. Two coolant relays can open "
        "an evacuation corridor. Security droids still obey their last order: "
        "no witnesses. Somewhere in the ash, a child has left a recording.",
        "Activate both relays, then reach the evacuation lift.",
        layout(
            walls=((8, 1, 1, 7), (16, 6, 1, 7), (11, 4, 5, 1)),
            lava=((10, 9, 4, 3), (19, 2, 4, 3), (2, 10, 4, 2)),
            objects=((2, 2, "@"), (5, 3, "H"), (6, 8, "R"),
                     (12, 2, "!"), (20, 10, "R"), (23, 11, ">"))),
        (("droid", 6, 6), ("droid", 13, 7), ("drone", 21, 7),
         ("droid", 22, 11)),
        ("The People Below", "A small voice in a service recording: 'The Jedi "
         "will come. Mum says they always do.' The file is dated today."),
        mood="duel",
    ),
    "archive": Mission(
        "archive", "THE LAST SENATE SIGNAL", "CORUSCANT / SEALED ARCHIVE",
        "A Senate archivist has vanished. Her dead-man switch holds the names "
        "of the people the Empire will erase next. Padme must recover three "
        "cipher fragments, align the relay, and get the list off-world.",
        "Recover 3 fragments; slice the relay; reach the courier lift.",
        layout(
            walls=((7, 1, 1, 8), (15, 5, 1, 8), (10, 5, 5, 1),
                   (20, 1, 1, 5), (2, 7, 3, 1)),
            objects=((2, 2, "@"), (4, 4, "C"), (12, 2, "C"),
                     (21, 10, "C"), (21, 7, "R"), (23, 11, ">"),
                     (11, 10, "!"), (5, 10, "H"))),
        (("trooper", 5, 5), ("trooper", 12, 8), ("drone", 18, 8),
         ("trooper", 23, 5)),
        ("A Name, Not a Number", "The archivist copied a name into every "
         "checksum. Her own. The Empire can delete a file; it cannot make "
         "the people who read it forget her."),
    ),
    "gauntlet": Mission(
        "gauntlet", "TRIAL OF THE BROKEN ORDER", "HOLODECK / TRAINING CHAMBER",
        "The Temple's last training program is still running. It remembers "
        "the footsteps of everyone who never returned. Survive three waves "
        "and leave through the illuminated arch.",
        "Defeat 3 waves, then reach the exit arch.",
        layout(walls=((7, 4, 2, 2), (17, 4, 2, 2), (7, 9, 2, 2),
                      (17, 9, 2, 2)),
               objects=((12, 7, "@"), (3, 7, "H"), (22, 7, "H"),
                        (12, 2, "!"), (23, 11, ">"))),
        (("droid", 3, 3), ("droid", 22, 3)),
        ("The Empty Temple", "The training master congratulates you. Then "
         "asks why there are no other students. You let the recording finish."),
        mood="duel", waves=3,
    ),
    "duel": Mission(
        "duel", "BROTHERS IN THE FIRE", "MUSTAFAR / REACTOR PLATFORM",
        "Blue against blue. One brother stands across the platform. Watch "
        "his wind-up, move outside the marked strike, and choose your moment.",
        "Practice against your opponent. Campaign choices are unchanged.",
        layout(walls=((11, 2, 4, 2), (11, 10, 4, 2)),
               lava=((1, 1, 3, 12), (22, 1, 3, 12)),
               objects=((7, 7, "@"), (6, 3, "H"))),
        (("boss", 18, 7),),
        ("Blue Against Blue", "For a heartbeat, the sabers sound exactly "
         "as they did in the training room. Neither of you says it."),
        mood="duel",
    ),
}


TILE_SIZE = 6

# Six-by-six silhouettes have separate hair, face, clothing, and feet.
SPRITES = {
    "anakin": ("..hh..", ".hhhs.", "..ss..", ".bBBb.", "..bb..", ".k..k."),
    "obiwan": ("..hh..", ".hssh.", "..hh..", ".tBtt.", "..tt..", ".k..k."),
    "padme": (".hhhh.", ".hssh.", "..ss..", ".mwwm.", "..mm..", ".k..k."),
    "droid": ("..yy..", "..rk..", ".yggy.", ".gyyg.", "..gg..", ".g..g."),
    "trooper": ("..ww..", ".wkkw.", "..ww..", ".wkkw.", "..ww..", ".w..w."),
    "drone": ("......", ".g..g.", "ggrrgg", ".grrg.", "..gg..", "......"),
    "boss": ("..hh..", ".hhhs.", "..ss..", ".bBBb.", "..bb..", ".k..k."),
    "H": ("......", "..ee..", ".eeee.", "..ee..", "......", "......"),
    "C": (".gggg.", ".kcck.", ".kcwk.", ".kkkk.", "..gg..", ".gggg."),
    "R": (".yyyy.", ".ykky.", ".yccy.", ".ykky.", "..gg..", ".gggg."),
    "!": ("..m...", "..mm..", ".mwwm.", "..mm..", "...m..", "......"),
    ">": (".wwww.", ".wccw.", ".w..w.", ".w..w.", ".w..w.", ".wwww."),
}

PALETTE = {
    "h": (83, 50, 41), "s": (234, 184, 142), "b": (66, 61, 61),
    "B": (115, 87, 65), "t": (196, 186, 157), "m": (196, 91, 159), "w": (226, 237, 230),
    "k": (18, 25, 26), "g": (95, 122, 113), "y": (226, 185, 83),
    "r": (240, 78, 70), "c": (92, 242, 220),
    "e": (99, 232, 150),
}
