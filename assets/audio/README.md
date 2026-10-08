# Custom Audio

Duel of Fates plays the root-level `song.mp3` throughout the story. Only short sound effects are synthesized; background music is never replaced with a procedural hum.

Optional OGG tracks in this directory override individual moods:

| Filename | Mood |
| --- | --- |
| `title.ogg` | Title and setup |
| `tension.ogg` | Investigation and uncertain encounters |
| `dark.ogg` | Anakin's darker scenes |
| `duel.ogg` | Lightsaber duels and action missions |
| `hope.ogg` | Redemption and resistance |
| `tragedy.ogg` | Loss and darker endings |

Tracks loop through pygame's music channel. Missing or unreadable mood tracks fall back to `song.mp3`. When the same track serves consecutive scenes, it continues playing rather than restarting. If no usable music is available, the game continues silently.

Settings provides independent music and sound-effect switches. `--mute` disables both.

Only audio with suitable redistribution rights should be included in public repository contributions.
