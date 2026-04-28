from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from memory.sqlite_store import fetch_rows, insert_many


def save_factual_events(base_dir: Path, ranked_content_df) -> None:
    if ranked_content_df.empty:
        return
    rows = []
    for _, row in ranked_content_df.head(20).iterrows():
        rows.append(
            {
                "topic": row.get("topic"),
                "source_name": row.get("source_name"),
                "title": row.get("title"),
                "summary": row.get("summary"),
                "url": row.get("url"),
                "event_ts": row.get("published_at"),
                "trust_score": float(row.get("trust_score", 0.6)),
            }
        )
    insert_many(base_dir, "factual_events", rows)


def save_editorial_learnings(base_dir: Path, learnings: List[Dict]) -> None:
    rows = []
    for item in learnings:
        prefs = item.get("preferences", {})
        for key, value in prefs.items():
            rows.append(
                {
                    "topic": item.get("topic", "global"),
                    "pattern_type": item.get("type"),
                    "key": key,
                    "value": str(value),
                    "score": 1.0,
                }
            )
    insert_many(base_dir, "editorial_patterns", rows)


def get_editorial_preferences(base_dir: Path, topic: str) -> Dict[str, bool]:
    rows = fetch_rows(
        base_dir,
        """
        SELECT key, value
        FROM editorial_patterns
        WHERE topic IN (?, 'global')
        ORDER BY created_at DESC
        """,
        [topic],
    )
    prefs: Dict[str, bool] = {}
    for row in rows:
        value = row["value"]
        if value.lower() in {"true", "false"}:
            prefs[row["key"]] = value.lower() == "true"
        elif value.isdigit():
            prefs[row["key"]] = int(value) > 0
        else:
            prefs[row["key"]] = bool(value)
    return prefs
