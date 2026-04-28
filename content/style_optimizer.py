from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from memory.editorial_memory import get_editorial_preferences


def apply_editorial_preferences(base_dir: Path, drafts: List[str], topic: str) -> List[str]:
    preferences = get_editorial_preferences(base_dir, topic)
    optimized = []

    for draft in drafts:
        current = draft.strip()

        if preferences.get("prefer_shorter_posts") and len(current) > 220:
            current = current[:217].rstrip() + "..."

        if preferences.get("prefer_numbers_early") and not any(ch.isdigit() for ch in current[:40]):
            current = "Key number: " + current

        optimized.append(current)

    return optimized
