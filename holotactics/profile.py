"""Local arcade records, separate from the branching story's active save."""

import json
from pathlib import Path


PROFILE_PATH = Path(__file__).resolve().parent.parent / "duel_of_fates_profile.json"


def load_profile(path=PROFILE_PATH):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return {key: value for key, value in data.items() if isinstance(value, dict)}
    except (OSError, ValueError):
        return {}


def record_result(result, character, path=PROFILE_PATH):
    if result.outcome != "victory":
        return False
    profile = load_profile(path)
    key = result.mission + ":" + character
    previous = profile.get(key, {})
    try:
        best = max(int(previous.get("best", 0)), result.score)
        wins = int(previous.get("wins", 0)) + 1
    except (ValueError, TypeError):
        best, wins = result.score, 1
    profile[key] = {"best": best, "wins": wins,
                    "memory": bool(previous.get("memory")) or result.memory_found}
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    try:
        temporary.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        return True
    except OSError:
        return False
