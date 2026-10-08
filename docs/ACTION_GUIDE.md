# Optional Terminal Missions

The campaign is choice-driven, including both central lightsaber duels. Two investigation scenes offer optional real-time terminal missions. Continuing the narrative is always the first option. Settings can disable these offers entirely.

Standalone practice is available through `--arcade` and `--mission`; it does not alter story health, choices, inventory, morality, or relationships.

## Characters

| Character | Primary attack | Power | Approach |
| --- | --- | --- | --- |
| Anakin | Forward lightsaber sweep | Short-range Force pulse | Close distance, strike, then dodge out of the warning area. |
| Obi-Wan | Forward lightsaber sweep | Short-range Force pulse | Manage guard stamina and punish enemy recovery. |
| Padme | Ranged blaster bolt | Wider ion pulse | Keep firing lanes open and disable approaching security. |

Sweeps hit within two tiles in the facing direction. Walls stop saber reach and blaster bolts. Force and ion pulses require energy and line of sight, interrupt attack wind-ups, briefly stun enemies, and clear hostile projectiles.

Movement and stamina define the fight. Attacking costs stamina. A dodge moves up to two tiles and grants brief immunity. Guard reduces a hit while sufficient stamina remains. Stamina and power regenerate; health requires a finite bacta charge or a between-wave recovery.

## Threats & Objects

| Appearance / ASCII tile | Meaning |
| --- | --- |
| Metal bulkhead / `#` | Solid wall |
| Molten channel / `~` | Walkable lava hazard; avoid prolonged exposure |
| Small person / `@` | Current player |
| Droid or trooper / `d` | Hostile unit |
| Saber opponent / `B` | Boss |
| Cyan console / `C` | Cipher fragment; collected by walking over it |
| Gold console / `R` | Relay; activate with `E` on or immediately ahead of it |
| Green relay / `r` | Activated relay |
| Pink fragment / `!` | Memory shard; collected by walking over it |
| Green charge / `H` | Bacta supply |
| White arch / `>` | Exit; use `E` after completing the objective |
| Gold warning corners | Enemy strike area; the HUD also shows `! INCOMING` |
| `+` in ASCII mode | Enemy strike warning on a floor tile |
| `=` / `*` in ASCII mode | Friendly / hostile projectile |

Enemies pursue through A* paths around walls. Droids wind up close-range strikes; troopers and drones warn before firing. Bosses accelerate their wind-up below half health. A warning provides a chance to move, guard, dodge, or interrupt.

## Objectives

`Tab` opens a full mission holo-map. `M` opens the recovered mission memory and recent transmissions. Both views pause combat and return to the same position.

**Ashes of the Foundry:** activate both coolant relays and use the lift. Defeating every enemy is optional. The memory in the upper service lane records a worker's child waiting for help.

**The Last Senate Signal:** collect all three cipher fragments, activate the relay, align the three octal rings with the visible checksum, and use the courier lift. Four failed transmissions cause security feedback; the relay remains available for another attempt. Disconnecting preserves collected fragments.

**Trial of the Broken Order:** defeat three waves, then leave through the arch. Later waves add more enemies and a ranged threat. Clearing a wave restores up to 15 health. The trial's memory is hidden near the north end of the chamber.

**Brothers in the Fire (standalone practice only):** defeat the opposing Jedi. The encounter finishes immediately when the opponent falls. It is not used by the campaign.

## Campaign Consequences

| Entry point | Field mission | Successful reward |
| --- | --- | --- |
| Anakin: search the control room | Foundry | +1 clarity, one Bacta Patch, +1 brotherhood, codex discovery, recovered mission memory |
| Padme: investigate Senate records | Archive | +1 clarity, one Bacta Patch, Rebellion Beacon, Bail network flag, codex discovery, recovered mission memory |

Rewards apply once per mission per story run. Failed or abandoned missions award nothing and leave campaign health, energy, stamina, and inventory unchanged. Declining an offer continues the original scene without repeating the invitation during that run.

Campaign duels always use the numbered turn-based combat menu, including when loading a save from an earlier build that selected action combat. Mission stats never replace campaign stats.

## Records & Scoring

Only victories update arcade records. Each mission/character pair tracks best score, clear count, and whether its memory has been recovered.

Score is calculated from a completion bonus, disabled enemies, cipher fragments, activated relays, a recovered memory, remaining health, and elapsed simulation time. Pauses, cipher menus, and terminal resizing do not advance simulation time. Records are local and do not affect ending conditions.

## Accessibility

Story difficulty is the campaign mission default and reduces incoming damage; Standard uses baseline damage and Veteran increases it. ASCII mode replaces pixel tiles with familiar symbols. Reduced motion freezes decorative lava animation and removes impact flashes while retaining essential movement and warnings. Music and sound effects can be switched off independently.

Pixel missions require a terminal at least 64 columns by 26 rows. Six-by-six sprites remain readable as the camera follows the player. A gold marker identifies the protagonist; the HUD gives a contextual relay/lift prompt or direction toward the next objective. Falling below the minimum size pauses combat until the terminal is enlarged.
