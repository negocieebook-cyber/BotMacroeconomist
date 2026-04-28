from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_or_create_newsletter_metrics(base_dir: Path) -> pd.DataFrame:
    path = base_dir / "data" / "processed" / "newsletter_metrics.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return pd.read_csv(path)

    df = pd.DataFrame(
        [
            {"theme": "inflacao", "open_rate": 0.41, "ctr": 0.12, "replies": 4, "unsubscribes": 0},
            {"theme": "juros", "open_rate": 0.38, "ctr": 0.09, "replies": 2, "unsubscribes": 1},
            {"theme": "helio", "open_rate": 0.36, "ctr": 0.11, "replies": 1, "unsubscribes": 0},
        ]
    )
    df.to_csv(path, index=False)
    return df
