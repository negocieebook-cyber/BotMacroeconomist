from __future__ import annotations

from typing import Any, Dict, Iterable, List

import pandas as pd


def _normalize_manual_item(item: Dict[str, Any]) -> Dict[str, Any]:
    text = item.get("text") or item.get("fact") or ""
    title = text[:120] if text else item.get("url", "manual input")
    return {
        "source_type": "manual",
        "source_name": item.get("source", "manual"),
        "url": item.get("url", ""),
        "title": title,
        "summary": text,
        "published_at": item.get("created_at"),
        "topic_hint": item.get("topic", ""),
        "trust_score": 0.9,
        "source_mode": "manual",
    }


def unify_content_sources(
    x_df: pd.DataFrame,
    rss_df: pd.DataFrame,
    sites_df: pd.DataFrame,
    manual_items: List[Dict[str, Any]],
) -> pd.DataFrame:
    parts: List[pd.DataFrame] = []

    if not x_df.empty:
        x_norm = x_df.copy()
        x_norm["source_type"] = "x"
        x_norm["source_name"] = x_norm["handle"]
        x_norm["title"] = x_norm["text"].str.slice(0, 120)
        x_norm["summary"] = x_norm["text"]
        x_norm["trust_score"] = x_norm.get("engagement_hint", 0.7)
        x_norm["published_at"] = x_norm.get("published_at")
        if "source_mode" not in x_norm.columns:
            x_norm["source_mode"] = "live"
        parts.append(x_norm[["source_type", "source_name", "url", "title", "summary", "published_at", "topic_hint", "trust_score", "source_mode"]])

    for df in [rss_df, sites_df]:
        if not df.empty:
            normalized = df.copy()
            if "source_mode" not in normalized.columns:
                normalized["source_mode"] = "live"
            parts.append(normalized[["source_type", "source_name", "url", "title", "summary", "published_at", "topic_hint", "trust_score", "source_mode"]].copy())

    if manual_items:
        manual_df = pd.DataFrame([_normalize_manual_item(item) for item in manual_items])
        parts.append(manual_df)

    if not parts:
        return pd.DataFrame(columns=["source_type", "source_name", "url", "title", "summary", "published_at", "topic_hint", "trust_score", "source_mode"])

    return pd.concat(parts, ignore_index=True)
