from __future__ import annotations

import re
from difflib import SequenceMatcher

import pandas as pd


def _normalize_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value.lower().strip())
    return re.sub(r"[^a-z0-9à-ÿ ]", "", value)


def deduplicate_content(df: pd.DataFrame, similarity_threshold: float = 0.92) -> pd.DataFrame:
    if df.empty:
        return df

    seen = []
    keep_rows = []

    for _, row in df.iterrows():
        title = _normalize_text(str(row.get("title", "")))
        url = str(row.get("url", "")).strip()
        key = url or title

        is_dup = False
        for old in seen:
            if key and old["key"] == key:
                is_dup = True
                break
            if title and old["title"] and SequenceMatcher(None, title, old["title"]).ratio() >= similarity_threshold:
                is_dup = True
                break

        if not is_dup:
            seen.append({"key": key, "title": title})
            keep_rows.append(row)

    return pd.DataFrame(keep_rows).reset_index(drop=True)
