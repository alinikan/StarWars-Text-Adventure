"""Exercise the real story UI without reading or replacing the player's save."""

import argparse
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time

import pexpect
import pyte

from terminal_smoke import ROOT, screenshot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "images")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TERM="xterm-256color", DUEL_OF_FATES_FAST="1", SDL_AUDIODRIVER="dummy")
    env.pop("NO_COLOR", None)
    for route, character in (("1", "anakin"), ("2", "obiwan"), ("3", "padme")):
        with tempfile.TemporaryDirectory() as directory:
            save = str(Path(directory) / "save.json")
            harness = ("import main; main.SAVE_FILE = " + repr(save) + "; "
                       "game = main.GameEngine(); game.launch_overrides['muted'] = True; game.run()")
            child = pexpect.spawn(sys.executable, ["-c", harness], cwd=str(ROOT), env=env,
                                  encoding="utf-8", timeout=5, dimensions=(24, 80))
            screen = pyte.Screen(80, 24)
            stream = pyte.Stream(screen)

            def wait_for(text, timeout=5):
                if text in "\n".join(screen.display):
                    return
                end = time.monotonic() + timeout
                while time.monotonic() < end:
                    try:
                        stream.feed(child.read_nonblocking(65536, timeout=0.05))
                    except pexpect.TIMEOUT:
                        continue
                    if text in "\n".join(screen.display):
                        return
                raise AssertionError(text + " missing:\n" + "\n".join(screen.display))

            def choices():
                return tuple(line.strip() for line in screen.display if re.search(r"\[\d+\]", line))

            try:
                wait_for("Choose 1-4 >")
                assert choices() == ("[1] New Story", "[2] Continue  (no saved story)", "[3] Settings", "[4] Quit")
                assert "Codex" not in "\n".join(screen.display)
                if character == "anakin":
                    screenshot(screen, args.output / "start-menu.png")
                child.sendline("3")
                wait_for("[5] Back")
                child.sendline("5")
                wait_for("Choose 1-4 >")
                assert not Path(save).exists(), "settings wrote a story save"
                child.sendline("1")
                wait_for("Your name >")
                child.sendline("Traveler")
                wait_for("[3] Padm")
                assert len(choices()) == 3
                if character == "anakin":
                    screenshot(screen, args.output / "choose-story.png")
                child.sendline(route)
                entry = {"anakin": "Go to Padm", "obiwan": "Wait and listen", "padme": "Fly to Mustafar alone"}[character]
                wait_for(entry)
                wait_for("[Q] Quit")
                original = choices()
                assert len(original) in (3, 4), "story choices are missing"
                assert "OPTIONAL MISSION" not in "\n".join(screen.display)
                for key, title in (("c", "CODEX & STATUS"), ("m", "MEMORY SHARDS")):
                    child.sendline(key)
                    wait_for(title)
                    wait_for("return to the choice")
                    child.sendline("")
                    wait_for("CURRENT CHOICES")
                    wait_for("[Q] Quit")
                    assert choices() == original, "overlay lost or renumbered choices"
                screenshot(screen, args.output / (character + "-choices.png"))
                if character == "padme":
                    child.sendline("3")
                    wait_for("[2] Play the optional 2D terminal mission.")
                    child.setwinsize(30, 80)
                    screen.resize(30, 80)
                    child.sendline("2")
                    wait_for("ENTER deploy")
                    child.send("q")
                    wait_for("[4] Read deeper")
                    assert "Download the Mustafar Contingency" in "\n".join(screen.display)
                child.sendline("q")
                wait_for("Save before quitting?")
                child.sendline("n")
                child.expect(pexpect.EOF)
            finally:
                child.close(force=True)
            print(character + ": title, settings, route, Codex/Memory return, and quit passed")
    print("Padme: optional mission exit returned to the original investigation choices")
    with tempfile.TemporaryDirectory() as directory:
        isolated = Path(directory)
        shutil.copyfile(ROOT / "main.py", isolated / "main.py")
        save = isolated / "duel_of_fates_save.json"
        save.write_text('{"name": "Traveler", "character": "padme", "current_scene": "padme_senate_records"}')
        before = save.read_bytes()
        child = pexpect.spawn(sys.executable, [str(isolated / "main.py"), "--mute"],
                              cwd=str(ROOT), env=dict(env, PYTHONPATH=str(ROOT)),
                              encoding="utf-8", timeout=5, dimensions=(24, 80))
        try:
            child.expect("Choose 1-4 >")
            child.sendcontrol("c")
            child.expect(pexpect.EOF)
            assert save.read_bytes() == before, "title interruption overwrote the saved story"
        finally:
            child.close(force=True)
    print("Title: Ctrl+C preserved the existing story save")
    print("Screenshots: " + str(args.output))


if __name__ == "__main__":
    main()
