from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd
import yaml


def load_topic_rules(base_dir: Path) -> Dict:
    with (base_dir / "config" / "topic_rules.yaml").open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def extract_topics(base_dir: Path, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    rules = load_topic_rules(base_dir).get("topics", {})
    enriched = df.copy()

    def infer_topic(text: str, current_hint: str) -> str:
        raw = f"{current_hint} {text}".lower()
        for topic, topic_data in rules.items():
            keywords: List[str] = topic_data.get("keywords", [])
            if any(keyword.lower() in raw for keyword in keywords):
                return topic
        return current_hint or "outros"

    enriched["topic"] = (
        enriched.fillna("")
        .apply(lambda row: infer_topic(f"{row.get('title', '')} {row.get('summary', '')}", str(row.get("topic_hint", ""))), axis=1)
    )

    enriched["text_length"] = enriched["summary"].fillna("").astype(str).str.len()
    return enriched
