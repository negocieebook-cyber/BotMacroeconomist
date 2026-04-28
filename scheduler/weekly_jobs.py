from __future__ import annotations

from pathlib import Path

from analytics.pattern_learning import generate_learning_report
from collect.macro_collect import collect_macro_data
from collect.manual_ingest import load_manual_items
from collect.news_sites_collect import collect_site_news
from collect.rss_collect import collect_rss_items
from collect.x_collect import collect_x_context
from content.newsletter_writer import generate_newsletter
from memory.condensation import condense_topic_memory
from memory.editorial_memory import save_editorial_learnings, save_factual_events
from memory.learnings import save_learnings
from memory.store import append_record
from process.build_briefs import build_weekly_brief
from process.clean_data import clean_macro_data, clean_news_df, clean_x_posts
from process.deduplicate import deduplicate_content
from process.extract_topics import extract_topics
from process.rank_content import rank_content_24h
from process.rank_topics import rank_macro_topics
from process.unify_inputs import unify_content_sources


def run_weekly_pipeline(base_dir: Path) -> None:
    macro_raw = collect_macro_data(base_dir)
    x_raw = collect_x_context(base_dir)
    rss_raw = collect_rss_items(base_dir)
    site_raw = collect_site_news(base_dir)
    manual_items = load_manual_items(base_dir)

    macro_clean = clean_macro_data(macro_raw)
    x_clean = clean_x_posts(x_raw)
    rss_clean = clean_news_df(rss_raw)
    site_clean = clean_news_df(site_raw)

    unified = unify_content_sources(x_clean, rss_clean, site_clean, manual_items)
    deduped = deduplicate_content(unified)
    enriched = extract_topics(base_dir, deduped)
    ranked_content = rank_content_24h(base_dir, enriched)
    ranked_macro = rank_macro_topics(base_dir, macro_clean, x_clean)

    brief = build_weekly_brief(base_dir, ranked_macro, ranked_content)
    newsletter = generate_newsletter(base_dir, brief)
    save_factual_events(base_dir, ranked_content)
    append_record(base_dir, "weekly_history.json", {"brief": brief, "newsletter": newsletter})
    print("Pipeline semanal expandido concluído.")


def run_learning_pipeline(base_dir: Path) -> None:
    learnings = generate_learning_report(base_dir)
    save_learnings(base_dir, learnings)
    save_editorial_learnings(base_dir, learnings)

    for topic in ["inflacao", "juros", "atividade", "emprego", "helio"]:
        condense_topic_memory(base_dir, topic, period_label="weekly")

    append_record(base_dir, "learning_history.json", {"learnings": learnings})
    print("Pipeline de aprendizado expandido concluído.")
