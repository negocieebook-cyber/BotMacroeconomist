from __future__ import annotations

import pandas as pd


def score_x_posts(df: pd.DataFrame) -> pd.DataFrame:
    scored = df.copy()
    scored["engagement_score"] = (
        scored["likes"] * 1.0
        + scored["reposts"] * 2.0
        + scored["replies"] * 1.5
        + scored.get("bookmarks", 0) * 1.2
    ) / scored["impressions"].clip(lower=1)
    return scored.sort_values(by="engagement_score", ascending=False)


def score_newsletters(df: pd.DataFrame) -> pd.DataFrame:
    scored = df.copy()
    scored["newsletter_score"] = (
        scored["open_rate"] * 0.5 + scored["ctr"] * 0.4 + scored["replies"] * 0.1
    )
    return scored.sort_values(by="newsletter_score", ascending=False)
