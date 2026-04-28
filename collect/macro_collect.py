from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd


MOCK_MACRO_DATA: List[Dict[str, Any]] = [
    {
        "date": str(date.today()),
        "country": "US",
        "indicator": "CPI",
        "value": 3.4,
        "previous": 3.2,
        "source": "FRED",
        "note": "CPI annual rose above prior reading",
    },
    {
        "date": str(date.today()),
        "country": "US",
        "indicator": "Core CPI",
        "value": 3.7,
        "previous": 3.6,
        "source": "FRED",
        "note": "Core inflation remains sticky",
    },
    {
        "date": str(date.today()),
        "country": "BR",
        "indicator": "Selic",
        "value": 10.5,
        "previous": 10.75,
        "source": "BIS",
        "note": "Policy rate still restrictive despite cuts",
    },
]


def collect_macro_data(base_dir: Path) -> pd.DataFrame:
    df = pd.DataFrame(MOCK_MACRO_DATA)
    output = base_dir / "data" / "raw" / "macro_data.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    return df
