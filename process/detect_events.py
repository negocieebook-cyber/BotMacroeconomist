from __future__ import annotations

from typing import Dict, List

import pandas as pd



def detect_macro_events(df: pd.DataFrame) -> List[Dict[str, str]]:
    events = []
    for _, row in df.iterrows():
        direction = "up" if row["delta"] > 0 else "down" if row["delta"] < 0 else "flat"
        events.append(
            {
                "indicator": str(row["indicator"]),
                "country": str(row["country"]),
                "direction": direction,
                "summary": f"{row['indicator']} in {row['country']} moved {direction} from {row['previous']} to {row['value']}",
            }
        )
    return events
