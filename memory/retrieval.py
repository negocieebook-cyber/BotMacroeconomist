from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from memory.sqlite_store import fetch_rows


def load_recent_facts(base_dir: Path, topic: str | None = None, limit: int = 10) -> List[Dict[str, Any]]:
    if topic:
        return fetch_rows(
            base_dir,
            """
            SELECT topic, source_name, title, summary, url, event_ts, trust_score
            FROM factual_events
            WHERE topic = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [topic, limit],
        )

    return fetch_rows(
        base_dir,
        """
        SELECT topic, source_name, title, summary, url, event_ts, trust_score
        FROM factual_events
        ORDER BY created_at DESC
        LIMIT ?
        """,
        [limit],
    )
