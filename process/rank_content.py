from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict

import pandas as pd
import yaml


def _load_rules(base_dir: Path) -> Dict:
    with (base_dir / "config" / "content_ranking.yaml").open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _parse_dt(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc) - timedelta(days=3)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc) - timedelta(days=3)


def rank_content_24h(base_dir: Path, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    rules = _load_rules(base_dir)
    weights = rules.get("weights", {})
    now = datetime.now(timezone.utc)

    ranked = df.copy()
    ranked["published_dt"] = ranked["published_at"].fillna("").astype(str).apply(_parse_dt)
    ranked["hours_since"] = ranked["published_dt"].apply(lambda dt: max((now - dt).total_seconds() / 3600.0, 0.0))
    ranked["is_last_24h"] = ranked["hours_since"] <= 24
    ranked["recency_score"] = ranked["hours_since"].apply(lambda h: max(0.0, 1 - (h / 24 if h <= 24 else 1.2)))
    ranked["trust_score"] = ranked["trust_score"].fillna(0.6).astype(float).clip(0, 1)
    ranked["novelty_score"] = (ranked["title"].fillna("").astype(str).str.len() / 120).clip(0.2, 1.0)
    ranked["topic_priority"] = ranked["topic"].map(rules.get("topic_priority", {})).fillna(0.5)

    ranked["editorial_score"] = (
        ranked["recency_score"] * weights.get("recency", 0.35)
        + ranked["trust_score"] * weights.get("trust", 0.25)
        + ranked["novelty_score"] * weights.get("novelty", 0.15)
        + ranked["topic_priority"] * weights.get("topic_priority", 0.25)
    )

    ranked = ranked.sort_values(by=["is_last_24h", "editorial_score"], ascending=[False, False]).reset_index(drop=True)
    return ranked
