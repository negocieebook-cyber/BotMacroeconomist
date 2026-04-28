from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from zoneinfo import ZoneInfo

import yaml

from content.style_optimizer import apply_editorial_preferences
from content.x_post_types import generate_post_by_type


def _load_schedule(base_dir: Path) -> dict:
    path = base_dir / "config" / "x_schedule.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _post_types_for_today(base_dir: Path) -> List[str]:
    schedule = _load_schedule(base_dir)
    timezone_name = schedule.get("timezone", "America/Sao_Paulo")
    weekday = datetime.now(ZoneInfo(timezone_name)).strftime("%A").lower()
    slots = schedule.get("week", {}).get(weekday, {}).get("slots", [])
    return [slot.get("type", "valor") for slot in slots] or ["valor", "crescimento", "prova", "personalidade"]


def generate_x_posts(base_dir: Path, brief: dict) -> List[Dict[str, str]]:
    types = _post_types_for_today(base_dir)
    drafts = [generate_post_by_type(base_dir, brief, post_type) for post_type in types]
    optimized = apply_editorial_preferences(
        base_dir,
        [draft["text"] for draft in drafts],
        brief.get("top_theme", "outros"),
    )
    variants = [
        {
            "type": draft["type"],
            "text": text,
            "variants": [
                (
                    {**variant, "text": text}
                    if variant.get("style") == "structured"
                    else variant
                )
                for variant in draft.get("variants", [])
            ],
        }
        for draft, text in zip(drafts, optimized)
    ]

    output = base_dir / "data" / "published" / "x_post_drafts.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(variants, ensure_ascii=False, indent=2), encoding="utf-8")
    return variants


def generate_topic_x_posts(base_dir: Path, brief: dict) -> List[str]:
    topic_name = brief.get("topic_name", "tema")
    items = brief.get("items", [])
    base = []
    for item in items[:3]:
        draft = (
            f"The cleanest angle in {topic_name} right now\n\n"
            f"--> {item.get('title')}\n"
            f"--> {str(item.get('summary', ''))[:120]}\n\n"
            "Good operators compress the narrative before they expand the view."
        )
        base.append(draft[:280])
    optimized = apply_editorial_preferences(base_dir, base, topic_name)
    output = base_dir / "data" / "published" / f"x_post_drafts_{topic_name}.json"
    output.write_text(json.dumps(optimized, ensure_ascii=False, indent=2), encoding="utf-8")
    return optimized
