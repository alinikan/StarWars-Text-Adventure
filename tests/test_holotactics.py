"""Gameplay contracts and save boundaries; run with unittest discovery."""

import ast
import io
import json
import os
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("DUEL_OF_FATES_FAST", "1")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from blessed import Terminal
from holotactics.content import MISSIONS, SPRITES, TILE_SIZE
from holotactics.model import Actor, Bolt, RingPuzzle, World
from holotactics.profile import load_profile, record_result
from holotactics.render import RenderOptions, camera, render_frame, world_pixels
import main


class SizedTerminal:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.terminal = Terminal(force_styling=True)

    def __getattr__(self, name):
        return getattr(self.terminal, name)


def advance(world, seconds):
    for _ in range(round(seconds * 20)):
        world.update(0.05)


class MapTests(unittest.TestCase):
    def test_every_object_and_enemy_is_reachable_without_lava(self):
        for key, mission in MISSIONS.items():
            with self.subTest(mission=key):
                world = World(key)
                seen = {(world.x, world.y)}
                queue = list(seen)
                for x, y in queue:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        point = (x + dx, y + dy)
                        if point not in seen and world.walkable(*point, enemy=True):
                            seen.add(point)
                            queue.append(point)
                for y, row in enumerate(mission.rows):
                    for x, tile in enumerate(row):
                        if tile in "HCR!>":
                            self.assertIn((x, y), seen)
                for _, x, y in mission.enemies:
                    self.assertIn((x, y), seen)

    def test_wall_blocks_player_but_changes_facing(self):
        world = World()
        world.x, world.y = 1, 1
        world.command("left")
        self.assertEqual((world.x, world.y), (1, 1))
        self.assertEqual(world.facing, (-1, 0))

    def test_a_star_moves_around_refinery_wall(self):
        world = World()
        enemy = Actor("droid", 12, 7)
        world.enemies = [enemy]
        visited = []
        for _ in range(60):
            world._step_toward(enemy)
            visited.append((enemy.x, enemy.y))
        self.assertLessEqual(abs(enemy.x - world.x) + abs(enemy.y - world.y), 1)
        self.assertTrue(all(world.walkable(x, y, enemy=True) for x, y in visited))
        self.assertTrue(any(y >= 8 for _, y in visited))


class CombatTests(unittest.TestCase):
    def setUp(self):
        self.world = World("duel")
        self.world.enemies = []
        self.world.x, self.world.y = 7, 7
        self.world.now = 2.0

    def test_saber_requires_range_facing_and_cooldown(self):
        world = self.world
        front = Actor("droid", 8, 7)
        behind = Actor("droid", 6, 7)
        distant = Actor("droid", 10, 7)
        world.enemies = [front, behind, distant]
        world.command("attack")
        self.assertEqual(front.health, 24)
        self.assertEqual(behind.health, 50)
        self.assertEqual(distant.health, 50)
        world.command("attack")
        self.assertEqual(front.health, 24)

    def test_saber_cannot_cut_through_wall(self):
        world = self.world
        world.grid[7][8] = "#"
        enemy = Actor("droid", 9, 7)
        world.enemies = [enemy]
        world.command("attack")
        self.assertEqual(enemy.health, 50)

    def test_padme_blaster_hits_at_range(self):
        world = self.world
        world.character = "padme"
        enemy = Actor("droid", 11, 7, next_move=99, next_attack=99)
        world.enemies = [enemy]
        world.command("attack")
        advance(world, 0.5)
        self.assertEqual(enemy.health, 27)
        self.assertFalse(world.bolts)

    def test_blaster_stops_at_walls(self):
        world = self.world
        world.character = "padme"
        world.grid[7][9] = "#"
        enemy = Actor("droid", 11, 7, next_move=99, next_attack=99)
        world.enemies = [enemy]
        world.command("attack")
        advance(world, 0.6)
        self.assertEqual(enemy.health, 50)

    def test_guard_consumes_stamina_and_reduces_damage(self):
        world = self.world
        world.command("guard")
        world.hurt(20, "test")
        self.assertEqual(world.health, 96)
        self.assertEqual(world.stamina, 88)

    def test_guard_without_stamina_cannot_block(self):
        world = self.world
        world.stamina = 0
        world.command("guard")
        world.hurt(20, "test")
        self.assertEqual(world.health, 80)

    def test_dodge_uses_energy_budget_and_grants_brief_immunity(self):
        world = self.world
        world.command("dodge")
        self.assertEqual((world.x, world.y), (9, 7))
        self.assertEqual(world.stamina, 82)
        world.hurt(40, "test")
        self.assertEqual(world.health, 100)
        world.command("dodge")
        self.assertEqual(world.x, 9)

    def test_enemy_telegraphs_before_applying_damage(self):
        world = self.world
        enemy = Actor("droid", 8, 7)
        world.enemies = [enemy]
        world.update(0.05)
        self.assertGreater(enemy.strike_at, world.now)
        self.assertIn((world.x, world.y), enemy.danger)
        self.assertEqual(world.health, 100)
        advance(world, 0.7)
        self.assertEqual(world.health, 86)

    def test_moving_out_of_telegraph_avoids_damage(self):
        world = self.world
        world.enemies = [Actor("droid", 8, 7)]
        world.update(0.05)
        world.command("left")
        advance(world, 0.7)
        self.assertEqual(world.health, 100)

    def test_force_cancels_windup_and_needs_energy(self):
        world = self.world
        enemy = Actor("droid", 8, 7, strike_at=2.5, danger=[(7, 7)])
        world.enemies = [enemy]
        world.command("power")
        self.assertEqual(world.energy, 72)
        self.assertEqual(enemy.strike_at, 0)
        self.assertGreater(enemy.stunned_until, world.now)
        world.energy = 0
        hp = enemy.health
        world.command("power")
        self.assertEqual(enemy.health, hp)

    def test_lava_deals_damage_but_is_not_an_instant_death(self):
        world = self.world
        world.x, world.y = 2, 7
        world.enemies = [Actor("boss", 18, 7, next_move=99, next_attack=99)]
        world.update(0.05)
        self.assertEqual(world.health, 84)

    def test_dead_enemy_cannot_strike(self):
        world = self.world
        world.enemies = [Actor("droid", 8, 7, health=0, strike_at=1, danger=[(7, 7)])]
        world.update(0.05)
        self.assertEqual(world.health, 100)
        self.assertEqual(world.kills, 1)
        self.assertEqual(world.outcome, "victory")

    def test_difficulty_changes_damage(self):
        health = []
        for mode in ("story", "standard", "veteran"):
            world = World(difficulty=mode)
            world.hurt(20, "test")
            health.append(world.health)
        self.assertEqual(health, [89, 80, 72])

    def test_campaign_enemy_defense_reduces_action_damage(self):
        world = World("duel", boss_defense=12)
        enemy = world.enemies[0]
        world.hit_enemy(enemy, 26)
        self.assertEqual(enemy.health, enemy.max_health - 20)


class ObjectiveTests(unittest.TestCase):
    def test_foundry_exit_requires_both_relays(self):
        world = World()
        world.x, world.y = world.find_tile(">")
        world.command("interact")
        self.assertIsNone(world.outcome)
        for _ in range(2):
            world.x, world.y = world.find_tile("R")
            world.command("interact")
        world.x, world.y = world.find_tile(">")
        world.command("interact")
        self.assertEqual(world.outcome, "victory")

    def test_archive_requires_all_fragments_then_solved_puzzle(self):
        world = World("archive", "padme")
        world.x, world.y = world.find_tile("R")
        world.command("interact")
        self.assertIsNone(world.puzzle)
        for _ in range(3):
            world.x, world.y = world.find_tile("C")
            world.pickup()
        world.x, world.y = world.find_tile("R")
        world.command("interact")
        self.assertIsNotNone(world.puzzle)
        time_before = world.now
        world.update(0.1)
        self.assertEqual(world.now, time_before)
        for index, target in enumerate(world.puzzle.target):
            world.puzzle.selected = index
            while world.puzzle.values[index] != target:
                world.command("up")
        world.command("attack")
        self.assertIsNone(world.puzzle)
        self.assertEqual(world.relays, 1)
        world.x, world.y = world.find_tile(">")
        world.command("interact")
        self.assertEqual(world.outcome, "victory")

    def test_disconnect_keeps_relay_available(self):
        world = World("archive", "padme")
        world.fragments = 3
        world.x, world.y = world.find_tile("R")
        world.command("interact")
        world.command("quit")
        self.assertIsNone(world.puzzle)
        self.assertEqual(world.relays, 0)
        self.assertEqual(world.tile(world.x, world.y), "R")

    def test_four_wrong_checksums_allow_retry_with_damage(self):
        world = World("archive", "padme")
        world.now = 2
        world.fragments = 3
        world.x, world.y = world.find_tile("R")
        world.command("interact")
        for _ in range(4):
            world.command("attack")
        self.assertIsNone(world.puzzle)
        self.assertEqual(world.health, 92)
        world.command("interact")
        self.assertIsNotNone(world.puzzle)

    def test_gauntlet_exit_waits_for_three_waves(self):
        world = World("gauntlet")
        for wave in (2, 3):
            for enemy in world.enemies:
                enemy.health = 0
            world.update(0.05)
            self.assertEqual(world.wave, wave)
            self.assertFalse(world.objective_ready)
        for enemy in world.enemies:
            enemy.health = 0
        world.update(0.05)
        self.assertTrue(world.objective_ready)
        world.x, world.y = world.find_tile(">")
        world.command("interact")
        self.assertEqual(world.outcome, "victory")

    def test_pickup_is_not_repeatable(self):
        world = World()
        world.x, world.y = world.find_tile("H")
        world.pickup()
        world.pickup()
        self.assertEqual(world.medkits, 2)
        world.health = 70
        world.command("heal")
        self.assertEqual(world.health, 100)
        self.assertEqual(world.medkits, 1)


class DisplayTests(unittest.TestCase):
    def test_sprite_dimensions_match_pixel_tiles(self):
        for name, sprite in SPRITES.items():
            self.assertEqual(len(sprite), TILE_SIZE, name)
            self.assertTrue(all(len(row) == TILE_SIZE for row in sprite), name)

    def test_context_hint_explains_relays_and_exit(self):
        world = World("archive", "padme")
        self.assertIn("CIPHER", world.navigation_hint)
        world.x, world.y = world.find_tile("R")
        self.assertIn("LOCKED", world.navigation_hint)
        world.fragments = 3
        self.assertIn("E / activate", world.navigation_hint)
        world.relays = 1
        world.x, world.y = world.find_tile(">")
        self.assertEqual(world.navigation_hint, "E / take the lift.")

    def test_pixel_and_ascii_frames_fit_supported_terminal_sizes(self):
        for width, height in ((64, 26), (80, 30), (110, 40), (160, 50)):
            for ascii_mode in (False, True):
                for key in MISSIONS:
                    with self.subTest(size=(width, height), ascii=ascii_mode, mission=key):
                        term = SizedTerminal(width, height)
                        world = World(key)
                        frame = render_frame(world, term, RenderOptions(ascii_mode))
                        self.assertLess(len(frame), height)
                        self.assertTrue(all(term.length(row) < width for row in frame))
                        self.assertIn("DUEL OF FATES", term.strip_seqs(frame[0]))

    def test_small_terminal_displays_resize_state(self):
        term = SizedTerminal(40, 15)
        self.assertIn("TOO SMALL", term.strip_seqs(render_frame(World(), term)[0]))

    def test_camera_always_contains_player(self):
        world = World()
        for width, height in ((64, 26), (110, 40)):
            for x, y in ((1, 1), (24, 12), (12, 7)):
                world.x, world.y = x, y
                left, top, w, h = camera(world, width, height)
                self.assertTrue(left <= x < left + w)
                self.assertTrue(top <= y < top + h)

    def test_pixels_are_nonblank_and_change_after_movement(self):
        world = World()
        before = world_pixels(world).rows
        world.command("right")
        after = world_pixels(world).rows
        self.assertNotEqual(before, after)
        self.assertGreater(len({pixel for row in after for pixel in row}), 15)


class PersistenceTests(unittest.TestCase):
    def test_field_rewards_are_applied_once_and_archive_establishes_bail_link(self):
        engine = main.GameEngine()
        engine.player.character = "padme"
        world = World("archive", "padme")
        world.outcome = "victory"
        world.memory_found = True
        with patch.object(main, "play_mission", return_value=world.result()) as mission, \
             patch.object(main, "show_choices", return_value=2), patch.object(main, "clear_screen"), \
             patch.object(main, "pause"), patch.object(main, "save_game"), \
             patch("sys.stdout", new_callable=io.StringIO):
            engine.offer_field_mission("archive")
            engine.offer_field_mission("archive")
        mission.assert_called_once()
        self.assertTrue(engine.player.flags["bail_network"])
        self.assertTrue(engine.player.flags["field_archive"])
        self.assertIn("Rebellion Beacon", engine.player.inventory)
        self.assertEqual(engine.player.clarity, 1)
        self.assertEqual(len(engine.player.memory_shards), 1)

    def test_abandoned_field_mission_cannot_award_a_collected_memory(self):
        engine = main.GameEngine()
        engine.player.character = "anakin"
        world = World()
        world.memory_found = True
        with patch.object(main, "play_mission", return_value=world.result()), \
             patch.object(main, "show_choices", return_value=2), patch.object(main, "clear_screen"), \
             patch("sys.stdout", new_callable=io.StringIO):
            engine.offer_field_mission("ashwalk")
        self.assertEqual(engine.player.health, 100)
        self.assertEqual(engine.player.clarity, 0)
        self.assertFalse(engine.player.memory_shards)
        self.assertFalse(engine.player.flags.get("field_ashwalk"))

    def test_failed_field_mission_returns_without_campaign_penalty(self):
        engine = main.GameEngine()
        engine.player.character = "anakin"
        world = World()
        world.outcome = "defeat"
        with patch.object(main, "play_mission", return_value=world.result()), \
             patch.object(main, "show_choices", return_value=2), patch.object(main, "clear_screen"), \
             patch.object(main, "pause"), patch("sys.stdout", new_callable=io.StringIO):
            engine.offer_field_mission("ashwalk")
        self.assertEqual(engine.player.health, 100)
        self.assertFalse(engine.player.flags.get("field_ashwalk"))

    def test_declining_mission_preserves_story_and_does_not_repeat_offer(self):
        engine = main.GameEngine()
        with patch.object(main, "show_choices", return_value=1) as choices, \
             patch.object(main, "play_mission") as mission, \
             patch("sys.stdout", new_callable=io.StringIO):
            engine.offer_field_mission("archive")
            engine.offer_field_mission("archive")
        choices.assert_called_once_with(["Continue the story.", "Play the optional 2D terminal mission."])
        mission.assert_not_called()
        self.assertEqual(engine.player.health, 100)
        self.assertFalse(engine.player.inventory)

    def test_disabled_optional_missions_do_not_interrupt_story(self):
        engine = main.GameEngine()
        engine.player.flags["skip_field_missions"] = True
        with patch.object(main, "show_choices") as choices, patch.object(main, "play_mission") as mission:
            engine.offer_field_mission("archive")
        choices.assert_not_called()
        mission.assert_not_called()

    def test_play_again_returns_to_title_and_preserves_display_settings(self):
        engine = main.GameEngine()
        engine.player.current_scene = "anakin_ending_dark"
        engine.player.flags["ascii_mode"] = True

        def ending():
            engine._show_stats("TEST ENDING")

        def title():
            engine.running = False

        with patch.object(engine, "scene_anakin_ending_dark", side_effect=ending), \
             patch.object(engine, "scene_title", side_effect=title) as title_scene, \
             patch.object(main, "show_choices", return_value=1), patch.object(main, "delete_save"), \
             patch("sys.stdout", new_callable=io.StringIO):
            engine.run()
        title_scene.assert_called_once()
        self.assertTrue(engine.player.flags["ascii_mode"])
        self.assertFalse(engine.restart_requested)

    def test_only_completed_missions_write_records_and_preserve_best(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            world = World()
            self.assertFalse(record_result(world.result(), "anakin", path))
            self.assertFalse(path.exists())
            world.outcome = "victory"
            world.memory_found = True
            self.assertTrue(record_result(world.result(), "anakin", path))
            first = load_profile(path)["ashwalk:anakin"]["best"]
            world.health = 1
            world.memory_found = False
            record_result(world.result(), "anakin", path)
            record = load_profile(path)["ashwalk:anakin"]
            self.assertEqual(record["best"], first)
            self.assertEqual(record["wins"], 2)
            self.assertTrue(record["memory"])

    def test_malformed_records_do_not_crash_game(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text("[]")
            self.assertEqual(load_profile(path), {})
            path.write_text('{"ashwalk:anakin": {"best": "oops", "wins": null}}')
            world = World()
            world.outcome = "victory"
            self.assertTrue(record_result(world.result(), "anakin", path))

    def test_old_story_saves_load_with_new_settings_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            path.write_text(json.dumps({"name": "Traveler", "character": "padme",
                                        "current_scene": "padme_senate_records"}))
            with patch.object(main, "SAVE_FILE", str(path)):
                player = main.load_game()
                self.assertEqual(player.name, "Traveler")
                self.assertEqual(player.flags.get("action_difficulty", "story"), "story")

    def test_title_menu_round_trip_does_not_overwrite_story_save(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            path.write_text('{"current_scene": "padme_senate_records"}')
            before = path.read_bytes()
            engine = main.GameEngine()
            with patch.object(main, "SAVE_FILE", str(path)), \
                 patch.object(engine, "scene_title", side_effect=["title", None]):
                engine.run()
            self.assertEqual(path.read_bytes(), before)

    def test_campaign_duels_are_choice_based_even_with_old_action_preference(self):
        for character, scene, destination in (
                ("anakin", "scene_anakin_duel", "anakin_mining_platform_collapse"),
                ("obiwan", "scene_obiwan_duel", "obiwan_crumbling_facility")):
            for outcome in ("victory", "defeat"):
                engine = main.GameEngine()
                engine.player = main.PlayerState(character=character, health=80, flags={"combat_style": "action"})
                with patch.object(main, "play_mission") as mission, patch.object(main, "clear_screen"), \
                     patch.object(main, "run_combat", return_value=outcome) as classic, \
                     patch("sys.stdout", new_callable=io.StringIO):
                    next_scene = getattr(engine, scene)()
                self.assertEqual(next_scene, destination if outcome == "victory" else
                                 "anakin_ending_fall" if character == "anakin" else "obiwan_ending_defeat")
                classic.assert_called_once()
                self.assertIs(classic.call_args.args[0], engine.player)
                mission.assert_not_called()

    def test_obiwan_first_scene_is_not_interrupted_by_a_minigame(self):
        engine = main.GameEngine()
        engine.player.character = "obiwan"
        with patch.object(engine, "offer_field_mission") as offer, patch.object(main, "clear_screen"), \
             patch.object(main, "show_choices", return_value=1), patch.object(main, "pause"), \
             patch("sys.stdout", new_callable=io.StringIO):
            engine.scene_obiwan_arrival()
        offer.assert_not_called()

    def test_overlays_restore_the_actual_choices(self):
        engine = main.GameEngine()
        with patch.object(main, "ACTIVE_ENGINE", engine), \
             patch.object(main, "clear_screen"), \
             patch("builtins.input", side_effect=["c", "", "m", "", "o", "5", "2"]), \
             patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(main.show_choices(["Save the archivist", "Reach the lift"]), 2)
        self.assertEqual(output.getvalue().count("Save the archivist"), 4)
        self.assertEqual(output.getvalue().count("Reach the lift"), 4)

    def test_title_has_stable_slots_and_no_story_or_arcade_commands(self):
        for saved in (None, main.PlayerState(name="Traveler", character="padme", current_scene="padme_senate_records")):
            engine = main.GameEngine()
            with patch.object(main, "load_game", return_value=saved), patch.object(main, "clear_screen"), \
                 patch("builtins.input", return_value="4"), patch("sys.stdout", new_callable=io.StringIO) as output:
                self.assertIsNone(engine.scene_title())
            text = Terminal(force_styling=True).strip_seqs(output.getvalue())
            for label in ("[1] New Story", "[2] Continue", "[3] Settings", "[4] Quit"):
                self.assertIn(label, text)
            for label in ("Holo-Arcade", "Codex", "Inventory", "Story duels"):
                self.assertNotIn(label, text)

    def test_title_settings_and_cancelled_new_game_preserve_saved_story(self):
        saved = main.PlayerState(name="Traveler", character="padme", current_scene="padme_senate_records")
        engine = main.GameEngine()
        with patch.object(main, "load_game", return_value=saved), patch.object(main, "clear_screen"), \
             patch.object(main, "show_terminal_settings") as settings, patch.object(main, "save_game") as save, \
             patch("builtins.input", side_effect=["3", "1", "n", "2"]), \
             patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(engine.scene_title(), "padme_senate_records")
        settings.assert_called_once()
        save.assert_not_called()
        self.assertIs(engine.player, saved)

    def test_invalid_save_is_not_deleted_by_opening_title(self):
        engine = main.GameEngine()
        with patch.object(main, "load_game", return_value=main.PlayerState(current_scene="obsolete")), \
             patch.object(main, "clear_screen"), patch.object(main, "delete_save") as delete, \
             patch("builtins.input", return_value="4"), patch("sys.stdout", new_callable=io.StringIO):
            engine.scene_title()
        delete.assert_not_called()

    def test_story_scene_graph_still_has_all_endings_and_valid_destinations(self):
        tree = ast.parse(Path(main.__file__).read_text())
        engine = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "GameEngine")
        scenes = {node.name[6:]: node for node in engine.body if isinstance(node, ast.FunctionDef) and node.name.startswith("scene_")}
        self.assertEqual(len(scenes), 45)
        self.assertEqual(sum("ending_" in key for key in scenes), 17)
        for scene in scenes.values():
            for node in ast.walk(scene):
                if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self.assertIn(node.value.value, scenes)


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.audio = main.AudioEngine()
        self.assertTrue(self.audio.enabled, "dummy mixer should be available")
        self.fast = patch.object(main, "FAST_MODE", False)
        self.fast.start()

    def tearDown(self):
        main.pygame.mixer.music.stop()
        self.fast.stop()

    def test_real_song_continues_across_title_and_story_moods_without_reload(self):
        with patch.object(main.pygame.mixer.music, "load", wraps=main.pygame.mixer.music.load) as load:
            for mood in ("title", "tension", "dark", "duel", "hope", "tragedy"):
                self.audio.set_mood(mood)
                self.assertEqual(self.audio.current_music, str(main.PROJECT_ROOT / "song.mp3"))
                self.assertTrue(main.pygame.mixer.music.get_busy())
            load.assert_called_once_with(str(main.PROJECT_ROOT / "song.mp3"))

    def test_invalid_custom_track_falls_back_to_song_not_synthesized_sound(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets" / "audio").mkdir(parents=True)
            (root / "assets" / "audio" / "dark.ogg").write_bytes(b"not audio")
            shutil.copyfile(main.PROJECT_ROOT / "song.mp3", root / "song.mp3")
            with patch.object(main, "PROJECT_ROOT", root), \
                 patch.object(main.pygame.mixer.music, "load", wraps=main.pygame.mixer.music.load) as load, \
                 patch.object(main.pygame.mixer, "Sound") as sound:
                self.audio.set_mood("dark")
            self.assertEqual(load.call_count, 2)
            self.assertEqual(self.audio.current_music, str(root / "song.mp3"))
            sound.assert_not_called()
            self.assertTrue(main.pygame.mixer.music.get_busy())

    def test_no_song_or_custom_track_is_silent(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(main, "PROJECT_ROOT", Path(directory)), \
             patch.object(main.pygame.mixer.music, "load") as load, \
             patch.object(main.pygame.mixer, "Sound") as sound:
            self.audio.set_mood("tension")
        load.assert_not_called()
        sound.assert_not_called()

    def test_unmuting_at_startup_does_not_start_music_before_title(self):
        with patch.object(self.audio, "play_music") as play:
            self.audio.set_muted(False)
            self.audio.set_music_muted(False)
        play.assert_not_called()

    def test_music_toggle_stops_and_resumes_real_track(self):
        self.audio.set_mood("title")
        self.audio.set_music_muted(True)
        self.assertFalse(main.pygame.mixer.music.get_busy())
        self.audio.set_mood("tension")
        self.audio.set_music_muted(False)
        self.assertTrue(main.pygame.mixer.music.get_busy())
        self.assertEqual(self.audio.current_music, str(main.PROJECT_ROOT / "song.mp3"))

    def test_music_and_sound_effects_can_be_disabled_independently(self):
        self.audio.set_music_muted(True)
        self.audio.play_tone(440, 0.004)
        self.assertIn((440, 0.004, 0.18), self.audio.tone_cache)
        self.audio.sfx_muted = True
        self.audio.play_tone(660, 0.004)
        self.assertNotIn((660, 0.004, 0.18), self.audio.tone_cache)
        self.audio.set_music_muted(False)
        self.audio.set_mood("title")
        self.assertTrue(main.pygame.mixer.music.get_busy())


if __name__ == "__main__":
    unittest.main()
