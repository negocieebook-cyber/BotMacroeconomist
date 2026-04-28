from __future__ import annotations

import json
from pathlib import Path

from collect.macro_collect import collect_macro_data
from collect.manual_ingest import load_manual_items
from collect.news_sites_collect import collect_site_news
from collect.rss_collect import collect_rss_items
from collect.topic_collect import collect_topic_context
from collect.x_collect import collect_x_context
from content.x_writer import generate_topic_x_posts, generate_x_posts
from memory.editorial_memory import save_factual_events
from memory.store import append_record
from process.build_briefs import build_daily_brief, build_topic_brief
from process.clean_data import clean_macro_data, clean_news_df, clean_x_posts
from process.deduplicate import deduplicate_content
from process.extract_topics import extract_topics
from process.rank_content import rank_content_24h
from process.rank_topics import rank_macro_topics
from process.unify_inputs import unify_content_sources
from scheduler.content_scheduler import generate_tomorrow_x_drafts


def _collect_daily_artifacts(base_dir: Path) -> tuple:
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
    return ranked_macro, ranked_content


def run_content_generation_pipeline(base_dir: Path, send_telegram: bool = False) -> dict:
    ranked_macro, ranked_content = _collect_daily_artifacts(base_dir)
    brief = build_daily_brief(base_dir, ranked_macro, ranked_content)
    drafts = generate_x_posts(base_dir, brief)
    tomorrow = generate_tomorrow_x_drafts(base_dir, brief, send_telegram=send_telegram)

    save_factual_events(base_dir, ranked_content)
    payload = {"brief": brief, "drafts": drafts, "tomorrow": tomorrow}
    append_record(base_dir, "daily_history.json", payload)

    summary_path = base_dir / "data" / "published" / "content_generation_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def run_daily_pipeline(base_dir: Path) -> dict:
    payload = run_content_generation_pipeline(base_dir, send_telegram=False)
    print("Pipeline diário expandido concluído.")
    return payload


def run_topic_pipeline(base_dir: Path, topic_name: str) -> None:
    topic_sources = collect_topic_context(base_dir, topic_name)
    rss_clean = clean_news_df(topic_sources["rss"])
    sites_clean = clean_news_df(topic_sources["sites"])
    x_clean = clean_x_posts(topic_sources["x"])

    unified = unify_content_sources(x_clean, rss_clean, sites_clean, [])
    deduped = deduplicate_content(unified)
    enriched = extract_topics(base_dir, deduped)
    ranked_content = rank_content_24h(base_dir, enriched)

    brief = build_topic_brief(base_dir, topic_name, ranked_content)
    drafts = generate_topic_x_posts(base_dir, brief)
    save_factual_events(base_dir, ranked_content)
    append_record(base_dir, f"topic_history_{topic_name}.json", {"brief": brief, "drafts": drafts})
    print(f"Pipeline do tema '{topic_name}' concluído.")
