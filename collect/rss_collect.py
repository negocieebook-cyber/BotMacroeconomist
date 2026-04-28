from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import feedparser
import pandas as pd
import yaml


def load_rss_sources(base_dir: Path) -> List[Dict[str, Any]]:
    config_path = base_dir / "config" / "news_sources.yaml"
    with config_path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    return config.get("rss_sources", [])


def collect_rss_items(base_dir: Path) -> pd.DataFrame:
    items: List[Dict[str, Any]] = []
    for source in load_rss_sources(base_dir):
        url = source.get("url")
        if not url:
            continue
        parsed = feedparser.parse(url)
        for entry in parsed.entries[:20]:
            items.append(
                {
                    "source_type": "rss",
                    "source_name": source.get("name", "rss"),
                    "url": entry.get("link"),
                    "title": entry.get("title"),
                    "summary": entry.get("summary", ""),
                    "published_at": entry.get("published", datetime.now(timezone.utc).isoformat()),
                    "topic_hint": source.get("topic_hint"),
                    "trust_score": source.get("trust_score", 0.8),
                    "source_mode": "live",
                }
            )
    df = pd.DataFrame(items)
    output = base_dir / "data" / "raw" / "rss_items.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    return df
