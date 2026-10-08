"""Drive a real PTY and export actual terminal frames for visual inspection.

Development dependencies only. Works on macOS/Linux.
"""

import argparse
import os
from pathlib import Path
import sys
import time

import pexpect
import pyte
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent


def font_path():
    candidates = ("/System/Library/Fonts/Menlo.ttc",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    return next((path for path in candidates if Path(path).exists()), None)


def color(value, default):
    named = {"black": "#0d1214", "red": "#f2737b", "green": "#8fdfa8",
             "brown": "#f0cf7a", "yellow": "#f0cf7a", "blue": "#7bbcec",
             "magenta": "#dc97d7", "cyan": "#8fded9", "white": "#d9e7e2",
             "brightblack": "#83938f", "brightwhite": "#f4faf7"}
    if value in named:
        return named[value]
    if len(value) == 6 and all(char in "0123456789abcdef" for char in value.lower()):
        return "#" + value
    return default


def screenshot(screen, path):
    font = ImageFont.truetype(font_path(), 15) if font_path() else ImageFont.load_default()
    cell_width, cell_height = 10, 20
    image = Image.new("RGB", (screen.columns * cell_width + 32, screen.lines * cell_height + 32), "#0d1214")
    draw = ImageDraw.Draw(image)
    for y in range(screen.lines):
        for x in range(screen.columns):
            char = screen.buffer[y][x]
            fg, bg = color(char.fg, "#d9e7e2"), color(char.bg, "#0d1214")
            if char.reverse:
                fg, bg = bg, fg
            xx, yy = 16 + x * cell_width, 16 + y * cell_height
            draw.rectangle((xx, yy, xx + cell_width - 1, yy + cell_height - 1), fill=bg)
            if char.data == "\u2580":
                draw.rectangle((xx, yy, xx + cell_width - 1, yy + cell_height // 2 - 1), fill=fg)
            else:
                draw.text((xx, yy), char.data, font=font, fill=fg)
    image.save(path)
    return image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "images")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TERM="xterm-256color", DUEL_OF_FATES_FAST="1", SDL_AUDIODRIVER="dummy")
    env.pop("NO_COLOR", None)
    snapshots = []
    for mission, character in (("ashwalk", "anakin"), ("archive", "padme"), ("gauntlet", "obiwan"), ("duel", "anakin")):
        child = pexpect.spawn(sys.executable,
                              ["main.py", "--mission", mission, "--character", character, "--mute"],
                              cwd=str(ROOT), env=env, encoding="utf-8", timeout=5, dimensions=(54, 160))
        screen = pyte.Screen(160, 54)
        stream = pyte.Stream(screen)

        def framebuffer():
            return tuple(tuple(screen.buffer[y][x] for x in range(screen.columns))
                         for y in range(screen.lines))

        def drain(seconds=0.15):
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                try:
                    data = child.read_nonblocking(65536, timeout=0.04)
                    stream.feed(data)
                except pexpect.TIMEOUT:
                    pass

        try:
            drain(0.4)
            assert any("ENTER deploy" in line for line in screen.display), mission + " briefing missing"
            child.send("\r")
            drain(0.3)
            assert any("DUEL OF FATES" in line for line in screen.display), mission + " HUD missing"
            initial = framebuffer()
            child.send("d")
            drain(0.15)
            assert framebuffer() != initial, mission + " movement did not redraw"
            child.send("\t")
            drain(0.15)
            assert any("HOLO-MAP" in line for line in screen.display)
            child.send("\t")
            drain(0.15)
            child.send("m")
            drain(0.15)
            assert any("MISSION MEMORY" in line for line in screen.display)
            child.send("m")
            drain(0.15)
            target = args.output / (mission + ".png")
            screenshot(screen, target)
            if mission in ("ashwalk", "archive"):
                snapshots.append(Image.open(target).copy())
            child.send("jfk")
            drain(0.2)
            child.send("p")
            drain(0.2)
            assert any("MISSION PAUSED" in line for line in screen.display)
            paused = framebuffer()
            drain(0.3)
            assert framebuffer() == paused, "paused mission kept rendering"
            child.send("p")
            drain(0.15)
            child.setwinsize(20, 50)
            screen.resize(20, 50)
            drain(0.2)
            assert any("TOO SMALL" in line for line in screen.display)
            child.setwinsize(40, 110)
            screen.resize(40, 110)
            drain(0.2)
            assert any("DUEL OF FATES" in line for line in screen.display)
            child.send("q")
            drain(0.2)
            assert any("LEAVE THIS MISSION" in line for line in screen.display)
            child.send("y")
            child.expect(pexpect.EOF)
            assert child.before is not None
        finally:
            child.close(force=True)
        print(mission + ": movement, attacks, map, memory, pause, resize, and exit passed")
    # Only campaign side missions appear in the public gallery.
    snapshots[0].save(args.output / "terminal-gallery.gif", save_all=True,
                      append_images=snapshots[1:], duration=1800, loop=0)
    print("Screenshots: " + str(args.output))


if __name__ == "__main__":
    main()
