from __future__ import annotations

import pandas as pd


def clean_macro_data(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    if cleaned.empty:
        return cleaned
    cleaned = cleaned.dropna(subset=["indicator", "value", "source"])
    cleaned["delta"] = cleaned["value"] - cleaned["previous"]
    cleaned["note"] = cleaned["note"].fillna("").astype(str).str.strip()
    return cleaned


def clean_x_posts(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    cleaned = df.copy()
    cleaned = cleaned.drop_duplicates(subset=["handle", "text"])
    cleaned["text"] = cleaned["text"].fillna("").astype(str).str.strip()
    cleaned = cleaned[cleaned["text"].str.len() > 20]
    return cleaned


def clean_news_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    cleaned = df.copy()
    for col in ["title", "summary", "url", "source_name", "topic_hint"]:
        if col not in cleaned.columns:
            cleaned[col] = ""
        cleaned[col] = cleaned[col].fillna("").astype(str).str.strip()
    cleaned = cleaned.drop_duplicates(subset=["url", "title"])
    cleaned = cleaned[cleaned["title"].str.len() > 8]
    return cleaned
