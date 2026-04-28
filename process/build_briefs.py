from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict, List

import pandas as pd


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_daily_brief(base_dir: Path, ranked_macro_df: pd.DataFrame, ranked_content_df: pd.DataFrame) -> Dict:
    top_macro = ranked_macro_df.iloc[0].to_dict() if not ranked_macro_df.empty else {}
    top_content = ranked_content_df.head(5).to_dict(orient="records") if not ranked_content_df.empty else []

    brief = {
        "date": str(date.today()),
        "top_theme": top_macro.get("topic", top_content[0]["topic"] if top_content else "outros"),
        "macro_points": [
            f"{top_macro.get('indicator', 'Indicador')} em {top_macro.get('country', 'N/A')} variou {top_macro.get('delta', 0)}",
            str(top_macro.get("note", "Sem nota macro relevante.")),
        ],
        "news_points": [
            {
                "title": item.get("title"),
                "summary": item.get("summary"),
                "source_name": item.get("source_name"),
                "topic": item.get("topic"),
                "score": item.get("editorial_score"),
                "source_mode": item.get("source_mode", "unknown"),
            }
            for item in top_content
        ],
        "source_mix": ranked_content_df["source_type"].value_counts().to_dict() if not ranked_content_df.empty else {},
        "source_modes": ranked_content_df["source_mode"].value_counts().to_dict() if not ranked_content_df.empty and "source_mode" in ranked_content_df.columns else {},
        "recommended_output": "x_post",
    }

    _write_json(base_dir / "data" / "briefs" / "daily_brief.json", brief)
    return brief


def build_weekly_brief(base_dir: Path, ranked_macro_df: pd.DataFrame, ranked_content_df: pd.DataFrame) -> Dict:
    macro_summary = ranked_macro_df.head(5).to_dict(orient="records") if not ranked_macro_df.empty else []
    themes = ranked_content_df["topic"].value_counts().head(5).index.tolist() if not ranked_content_df.empty else []
    top_items = ranked_content_df.head(8).to_dict(orient="records") if not ranked_content_df.empty else []

    brief = {
        "date": str(date.today()),
        "main_themes": themes,
        "macro_summary": [
            f"{row.get('indicator')} em {row.get('country')} score {row.get('score')}"
            for row in macro_summary
        ],
        "content_summary": [
            f"{row.get('source_name')}: {row.get('title')}" for row in top_items
        ],
        "recommended_output": "newsletter",
    }

    _write_json(base_dir / "data" / "briefs" / "weekly_brief.json", brief)
    return brief


def build_topic_brief(base_dir: Path, topic_name: str, ranked_content_df: pd.DataFrame) -> Dict:
    top_items = ranked_content_df.head(10).to_dict(orient="records") if not ranked_content_df.empty else []
    brief = {
        "date": str(date.today()),
        "topic_name": topic_name,
        "headline": f"Radar de {topic_name} nas últimas 24h",
        "items": [
            {
                "title": item.get("title"),
                "summary": item.get("summary"),
                "source_name": item.get("source_name"),
                "score": item.get("editorial_score"),
            }
            for item in top_items
        ],
        "recommended_output": ["x_post", "newsletter_snippet"],
    }
    _write_json(base_dir / "data" / "briefs" / f"topic_brief_{topic_name}.json", brief)
    return brief
