from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd

from collect.news_sites_collect import collect_site_news
from collect.rss_collect import collect_rss_items
from collect.x_collect import collect_x_context


def collect_topic_context(base_dir: Path, topic_name: str) -> Dict[str, pd.DataFrame]:
    rss_df = collect_rss_items(base_dir)
    site_df = collect_site_news(base_dir)
    x_df = collect_x_context(base_dir, topic_filter=topic_name)

    def _filter(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        text_cols = [col for col in ["title", "summary", "text", "topic_hint"] if col in df.columns]
        if not text_cols:
            return df.iloc[0:0]
        mask = False
        for col in text_cols:
            series = df[col].fillna("").astype(str).str.contains(topic_name, case=False, regex=False)
            mask = series if isinstance(mask, bool) else (mask | series)
        return df[mask].copy()

    return {
        "rss": _filter(rss_df),
        "sites": _filter(site_df),
        "x": _filter(x_df),
    }
