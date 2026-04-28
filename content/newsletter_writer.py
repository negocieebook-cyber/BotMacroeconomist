from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import yaml

from content.newsletter_template import NEWSLETTER_TEMPLATE
from knowledge.document_learning import load_seed_profiles, load_user_materials


def _load_rules(base_dir: Path) -> Dict:
    path = base_dir / "config" / "newsletter_rules.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}


def _pick_central_idea(brief: dict) -> str:
    themes = brief.get("main_themes", [])
    if themes:
        return f"The real opportunity is hidden inside {themes[0]}, not in the surface narrative."
    summary = brief.get("macro_summary", [])
    if summary:
        return str(summary[0])
    return "The most valuable macro work turns complexity into a usable map."


def _pick_promise(central_idea: str) -> str:
    return f"A concise operating map for reading the setup behind: {central_idea}"


def _build_deliverable(brief: dict) -> str:
    macro_lines = brief.get("macro_summary", [])[:3]
    content_lines = brief.get("content_summary", [])[:3]

    framework = [
        "Deliverable: Operating map",
        "",
        "1. What matters now",
        f"- {macro_lines[0] if macro_lines else 'Identify the one signal that changes positioning.'}",
        "",
        "2. What the market may be missing",
        f"- {macro_lines[1] if len(macro_lines) > 1 else 'Separate the headline from the transmission mechanism.'}",
        "",
        "3. What to monitor next",
        f"- {content_lines[0] if content_lines else 'Track the next data point that can confirm or break the read.'}",
        "",
        "Key questions",
        f"- {content_lines[1] if len(content_lines) > 1 else 'Is the move broadening across related assets and indicators?'}",
        f"- {content_lines[2] if len(content_lines) > 2 else 'What would make this view obviously wrong?'}",
    ]
    return "\n".join(framework)


def _build_opening(central_idea: str, voice: List[str]) -> str:
    joined_voice = ", ".join(voice[:3]) if voice else "clear, elegant, practical"
    return (
        f"{central_idea}\n\n"
        f"This edition is built to feel {joined_voice}. "
        "The goal is not to comment on everything. "
        "It is to leave the reader with a cleaner mental model and a usable next step."
    )


def _build_closing(brief: dict) -> str:
    themes = brief.get("main_themes", [])[:2]
    if themes:
        return (
            f"The point is not just to understand {themes[0]}. "
            "It is to recognize the pattern early enough to act with more calm and more precision next time."
        )
    return "A premium macro letter should reduce confusion and increase agency. This one is designed to do both."


def _build_cta() -> str:
    return "CTA: Reply with the one theme you want turned into next week's operating map."


def _build_titles() -> List[str]:
    return [
        "The Quiet Signal Behind the Noise",
        "When the Setup Matters More Than the Headline",
        "What Actually Matters This Week",
        "A Better Way to Read This Move",
        "The Detail Most People Are Missing",
        "The Setup Hidden Inside the Narrative",
        "An Operator's Map for the Current Regime",
        "The Elegant Case for Reading Second-Order Effects First",
    ]


def generate_newsletter(base_dir: Path, brief: dict) -> str:
    rules = _load_rules(base_dir)
    seed = load_seed_profiles(base_dir)
    materials = load_user_materials(base_dir)
    voice = seed.get("newsletter_learning", {}).get("voice", rules.get("voice", {}).get("traits", []))

    central_idea = _pick_central_idea(brief)
    promise = _pick_promise(central_idea)
    opening = _build_opening(central_idea, voice)
    deliverable = _build_deliverable(brief)
    closing = _build_closing(brief)
    cta = _build_cta()
    titles = _build_titles()

    newsletter = NEWSLETTER_TEMPLATE.format(
        title=titles[0],
        subtitle=promise,
        opening=opening,
        deliverable=deliverable,
        closing=closing,
        cta=cta,
    )

    payload = {
        "central_idea": central_idea,
        "promise": promise,
        "newsletter": newsletter,
        "cta": cta,
        "alternative_titles": titles,
        "source_context": list(materials.keys())[:5],
    }

    output_txt = base_dir / "data" / "published" / "newsletter_draft.md"
    output_json = base_dir / "data" / "published" / "newsletter_meta.json"
    output_txt.parent.mkdir(parents=True, exist_ok=True)
    output_txt.write_text(newsletter, encoding="utf-8")
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return newsletter
