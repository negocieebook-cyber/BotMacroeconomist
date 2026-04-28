from __future__ import annotations

from collections import Counter
from pathlib import Path

from memory.sqlite_store import fetch_rows, insert_many


def condense_topic_memory(base_dir: Path, topic: str, period_label: str = "rolling") -> str:
    rows = fetch_rows(
        base_dir,
        """
        SELECT title, summary
        FROM factual_events
        WHERE topic = ?
        ORDER BY created_at DESC
        LIMIT 20
        """,
        [topic],
    )
    if not rows:
        snapshot = f"Sem memória factual consolidada para {topic}."
    else:
        titles = [row["title"] for row in rows if row.get("title")]
        top_titles = "; ".join(titles[:5])
        snapshot = f"Resumo condensado de {topic}: {top_titles}"

    insert_many(
        base_dir,
        "topic_snapshots",
        [{"topic": topic, "snapshot": snapshot, "period_label": period_label}],
    )
    return snapshot
