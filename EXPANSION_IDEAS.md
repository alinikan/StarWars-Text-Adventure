# Duel of Fates Expansion Roadmap

This project is now structured around a stronger terminal-RPG identity: branching narrative, cinematic ASCII presentation, relationship meters, secrets, and combat choices that remember earlier scenes.

## Best Next Ideas

1. **Chapter Select / New Game Plus**
   - Unlock after any ending.
   - Let players replay from key branches with discovered secrets preserved.
   - Add "Force Echoes" that only appear on a second run.

2. **Playable Padme Route**
   - Political thriller route during the birth of the Empire.
   - Padme can expose Sidious, save Anakin, protect the twins, or become the first architect of rebellion.
   - Combat becomes debate, escape, persuasion, and risk management.

3. **Companion System**
   - K-4S can survive, evolve, lie, sacrifice itself, or become a recurring narrator.
   - R2-D2 and C-3PO can unlock stealth, repairs, or comic relief without breaking the tone.

4. **Expanded Combat Stances**
   - Anakin: Rage, Precision, Dominion.
   - Obi-Wan: Soresu, Negotiator, Last Stand.
   - Stances could alter stamina use, critical chance, defense, and available dialogue mid-fight.

5. **Secret Ending Web**
   - Track combinations of `clarity`, `bond_padme`, `bond_brotherhood`, and secrets found.
   - Add rare endings that require unusual moral combinations, such as "Light Anakin, low trust" or "Dark Obi-Wan, high duty."

6. **Animated Terminal Set Pieces**
   - Collapsing mining platform.
   - A full lava-surfing chase.
   - A Senate transmission scene where text corrupts as Sidious jams the signal.
   - A mask-forging sequence if Anakin falls.

7. **Codex and Memory Shards Menu**
   - Add an in-game `C` command at choice prompts.
   - Let players inspect discovered lore, secrets, and relationship meters.

8. **Dynamic Music/SFX**
   - Add optional `assets/audio/` with separate ambient, duel, tragedy, and secret-ending tracks.
   - Keep graceful fallback for terminals without audio.

9. **Save Slot Support**
   - Replace the single JSON save with `saves/slot_1.json`, `slot_2.json`, and `slot_3.json`.
   - Add ending history and unlocked secret flags.

10. **Original Side Stories**
   - Add named refugees, clones, and Separatist staff trapped on Mustafar.
   - Moral choices become less abstract when innocent people are physically present in the facility.

## Tone Targets

- Make every secret feel like the player found a crack in destiny.
- Let spectacle serve emotion: animations should land on a decision, reveal, or consequence.
- Keep morality complicated. Light choices can be naive; dark choices can be effective; the best endings should require truth and trust, not just "good" points.

## Implementation Notes

- Avoid adding mandatory external assets. Terminal art and optional audio keep the game easy to run.
- Keep new branches named as `scene_character_location_or_beat`.
- Whenever a scene adds a flag, make at least one later scene react to it.
- Preserve fast testing with `DUEL_OF_FATES_FAST=1`.
