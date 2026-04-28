from __future__ import annotations

from pathlib import Path

import pandas as pd


DEFAULT_ROWS = [
    {
        "theme": "inflacao",
        "chars": 180,
        "has_number_early": 1,
        "format_type": "single_post",
        "opening_style": "data_first",
        "hour_local": 9,
        "impressions": 1200,
        "likes": 45,
        "reposts": 10,
        "replies": 4,
        "bookmarks": 7,
    },
    {
        "theme": "juros",
        "chars": 220,
        "has_number_early": 1,
        "format_type": "single_post",
        "opening_style": "thesis_first",
        "hour_local": 11,
        "impressions": 980,
        "likes": 28,
        "reposts": 8,
        "replies": 2,
        "bookmarks": 4,
    },
    {
        "theme": "helio",
        "chars": 205,
        "has_number_early": 0,
        "format_type": "single_post",
        "opening_style": "context_first",
        "hour_local": 10,
        "impressions": 760,
        "likes": 21,
        "reposts": 6,
        "replies": 1,
        "bookmarks": 3,
    },
]


def load_or_create_x_metrics(base_dir: Path) -> pd.DataFrame:
    path = base_dir / "data" / "processed" / "x_metrics.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        df = pd.read_csv(path)
        for row in DEFAULT_ROWS:
            for key, value in row.items():
                if key not in df.columns:
                    df[key] = value
        return df
    df = pd.DataFrame(DEFAULT_ROWS)
    df.to_csv(path, index=False)
    return df

