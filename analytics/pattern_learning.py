from __future__ import annotations

from typing import Dict, List

from analytics.newsletter_metrics import load_or_create_newsletter_metrics
from analytics.performance_score import score_newsletters, score_x_posts
from analytics.x_metrics import load_or_create_x_metrics


def generate_learning_report(base_dir) -> List[Dict]:
    x_df = score_x_posts(load_or_create_x_metrics(base_dir))
    nl_df = score_newsletters(load_or_create_newsletter_metrics(base_dir))

    learnings: List[Dict] = []

    if not x_df.empty:
        best_x = x_df.iloc[0]
        learnings.append(
            {
                "type": "x_best_pattern",
                "topic": best_x["theme"],
                "message": (
                    f"Tema {best_x['theme']} performou melhor. "
                    f"Formato {best_x['format_type']} com abertura {best_x['opening_style']} "
                    f"e {best_x['chars']} chars merece prioridade."
                ),
                "preferences": {
                    "prefer_shorter_posts": int(best_x["chars"]) <= 220,
                    "prefer_numbers_early": int(best_x["has_number_early"]) == 1,
                    "best_hour_local": int(best_x["hour_local"]),
                },
            }
        )

    if not nl_df.empty:
        best_nl = nl_df.iloc[0]
        learnings.append(
            {
                "type": "newsletter_best_pattern",
                "topic": best_nl["theme"],
                "message": f"Tema {best_nl['theme']} teve melhor score de newsletter.",
                "preferences": {
                    "highlight_topic": best_nl["theme"],
                },
            }
        )

    return learnings
