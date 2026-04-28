from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BotEditorial/1.0)"
}


def load_site_sources(base_dir: Path) -> List[Dict[str, Any]]:
    config_path = base_dir / "config" / "news_sources.yaml"
    with config_path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    return config.get("site_sources", [])


def collect_site_news(base_dir: Path) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for source in load_site_sources(base_dir):
        listing_url = source.get("listing_url")
        article_selector = source.get("article_selector", "a")
        if not listing_url:
            continue

        try:
            response = requests.get(listing_url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            seen = set()
            for anchor in soup.select(article_selector)[:20]:
                href = anchor.get("href")
                title = anchor.get_text(" ", strip=True)
                if not href or not title or href in seen:
                    continue
                seen.add(href)
                rows.append(
                    {
                        "source_type": "site",
                        "source_name": source.get("name", "site"),
                        "url": href,
                        "title": title,
                        "summary": "",
                        "published_at": datetime.now(timezone.utc).isoformat(),
                        "topic_hint": source.get("topic_hint"),
                        "trust_score": source.get("trust_score", 0.75),
                        "source_mode": "live",
                    }
                )
        except Exception as exc:
            rows.append(
                {
                    "source_type": "site_error",
                    "source_name": source.get("name", "site"),
                    "url": listing_url,
                    "title": f"Falha de coleta: {exc}",
                    "summary": "",
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "topic_hint": source.get("topic_hint"),
                    "trust_score": 0.0,
                    "source_mode": "error",
                }
            )

    df = pd.DataFrame(rows)
    output = base_dir / "data" / "raw" / "site_news.csv"
    df.to_csv(output, index=False)
    return df
