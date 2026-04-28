from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd
import yaml

from collect.source_registry import source_lookup


def _load_rules(base_dir: Path) -> Dict:
    with (base_dir / "config" / "scoring_rules.yaml").open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def rank_macro_topics(base_dir: Path, macro_df: pd.DataFrame, x_df: pd.DataFrame) -> pd.DataFrame:
    if macro_df.empty:
        return pd.DataFrame(columns=["topic", "indicator", "country", "score", "delta", "note"])

    weights = _load_rules(base_dir)["weights"]
    sources = source_lookup()

    x_counts = x_df["topic_hint"].value_counts().to_dict() if not x_df.empty and "topic_hint" in x_df.columns else {}
    rows = []
    for _, row in macro_df.iterrows():
        note = str(row.get("note", "")).lower()
        indicator = str(row["indicator"]).lower()

        if "inflation" in note or "cpi" in indicator:
            topic = "inflacao"
        elif "selic" in indicator or "rate" in indicator or "juros" in note:
            topic = "juros"
        else:
            topic = "atividade"

        source_quality = sources.get(str(row["source"]), None)
        source_quality_score = source_quality.trust_score if source_quality else 0.7
        macro_surprise = min(abs(float(row["delta"])) / max(abs(float(row["previous"])), 0.1), 1.0)
        x_recurrence = min(x_counts.get(topic, 0) / 3.0, 1.0)
        editorial_potential = 0.9 if abs(float(row["delta"])) > 0 else 0.5
        total_score = (
            macro_surprise * weights["macro_surprise"]
            + source_quality_score * weights["source_quality"]
            + x_recurrence * weights["x_recurrence"]
            + editorial_potential * weights["editorial_potential"]
        )
        rows.append(
            {
                "topic": topic,
                "indicator": row["indicator"],
                "country": row["country"],
                "score": round(total_score, 4),
                "delta": row["delta"],
                "note": row["note"],
            }
        )

    return pd.DataFrame(rows).sort_values(by="score", ascending=False).reset_index(drop=True)
