from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import yaml


def _load_rules(base_dir: Path) -> Dict:
    path = base_dir / "config" / "x_post_rules.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _clean_text(value: str) -> str:
    text = " ".join(str(value or "").split())
    return text.strip()


def _short_text(value: str, max_chars: int = 90) -> str:
    text = _clean_text(value)
    if len(text) <= max_chars:
        return text
    shortened = text[:max_chars].rsplit(" ", 1)[0].strip()
    while shortened.split() and shortened.split()[-1].lower() in {"of", "to", "the", "in", "with", "and", "or", "for"}:
        shortened = " ".join(shortened.split()[:-1]).strip()
    return shortened or text[:max_chars].strip()


def _first_macro_line(brief: dict, index: int = 0, fallback: str = "The setup matters more than the headline.") -> str:
    macro_points = brief.get("macro_points", [])
    if len(macro_points) > index:
        return _clean_text(macro_points[index])
    return fallback


def _first_news_item(brief: dict) -> Dict:
    items = brief.get("news_points", [])
    return items[0] if items else {}


def _news_item(brief: dict, index: int = 0) -> Dict:
    items = brief.get("news_points", [])
    return items[index] if len(items) > index else {}


def _clip(post: str, max_chars: int) -> str:
    compact = "\n".join(line.rstrip() for line in str(post).strip().splitlines())
    return compact[: max_chars - 3].rstrip() + "..." if len(compact) > max_chars else compact


def _max_chars(base_dir: Path) -> int:
    return int(_load_rules(base_dir).get("format", {}).get("max_chars", 280))


def _compose_post(base_dir: Path, post_type: str, hook: str, lines: List[str], closing: str) -> Dict[str, str]:
    rules = _load_rules(base_dir)
    marker = rules.get("format", {}).get("list_marker", "-->")
    body = "\n".join(f"{marker} {line}" for line in lines if line)
    text = f"{hook}\n\n{body}\n\n{closing}".strip()
    return {"type": post_type, "text": _clip(text, _max_chars(base_dir))}


def _with_variants(post_type: str, original: str, structured: str, base_dir: Path) -> Dict[str, object]:
    original = _clip(original, _max_chars(base_dir))
    structured = _clip(structured, _max_chars(base_dir))
    return {
        "type": post_type,
        "text": structured,
        "variants": [
            {"style": "original", "text": original},
            {"style": "structured", "text": structured},
        ],
    }


def generate_valor_post(base_dir: Path, brief: dict) -> Dict[str, str]:
    news = _first_news_item(brief)
    topic = _clean_text(brief.get("top_theme", "macro"))
    original = _compose_post(
        base_dir,
        "valor",
        "A useful way to read tomorrow's macro setup",
        [
            _short_text(_first_macro_line(brief, 0), 64),
            _short_text(_first_macro_line(brief, 1, "The clean read is in the second-order effect."), 64),
        ],
        "Start with the mechanism. Then watch price.",
    )["text"]
    structured_lines = [
        f"How I would read {_short_text(topic, 32)} tomorrow:",
        "",
        _short_text(_first_macro_line(brief, 0, "Liquidity is becoming more important than the headline."), 48),
        "",
        _short_text(_first_macro_line(brief, 1, "Policy expectations are reacting faster to incoming data."), 48),
        "",
        _short_text(_first_macro_line(brief, 2, "Markets are rewarding the cleanest balance-sheet stories."), 48),
        "",
        "None of this is a trade by itself.",
        "",
        "But it gives you the map before the move.",
    ]
    return _with_variants("valor", original, "\n".join(structured_lines), base_dir)


def generate_crescimento_post(base_dir: Path, brief: dict) -> Dict[str, str]:
    topic = _clean_text(brief.get("top_theme", "macro"))
    news = _first_news_item(brief)
    original = _compose_post(
        base_dir,
        "crescimento",
        "The market is usually focused on the wrong question",
        [
            f"The broad story in {_short_text(topic, 36)} is not just the headline.",
            f"The latest move matters if it shifts expectations." if news else "The latest move matters if it shifts expectations.",
        ],
        "That is where macro becomes practical.",
    )["text"]
    points = [
        _short_text(_first_macro_line(brief, 0, "Macro is still being driven by policy expectations"), 48),
        _short_text(_first_macro_line(brief, 1, "Growth is holding up better than expected"), 48),
        _short_text(_first_macro_line(brief, 2, "Liquidity remains the repricing variable"), 48),
        _short_text(_news_item(brief, 0).get("title", "Markets are still separating signal from noise"), 48),
    ]
    body = "\n".join(f"+ {point}" for point in points[:3] if point)
    text = (
        "What the market may already be pricing:\n\n"
        f"{body}\n\n"
        "Which one is still underestimated?"
    )
    return _with_variants("crescimento", original, text, base_dir)


def generate_personalidade_post(base_dir: Path, brief: dict) -> Dict[str, str]:
    topic = _clean_text(brief.get("top_theme", "macro"))
    first_signal = _short_text(_first_macro_line(brief, 0, "The market is pricing a cleaner path than the data is giving it."), 38)
    original = _compose_post(
        base_dir,
        "personalidade",
        "One thing I try not to do when macro gets noisy",
        [
            "I try not to turn the first headline into a thesis.",
            _first_macro_line(brief, 0, "The setup matters more than the emotional first read."),
            "A slower read usually makes the risk clearer.",
        ],
        "Process matters most when conviction feels easy.",
    )["text"]
    text = (
        f"I try not to react too fast when {_short_text(topic, 26)} gets noisy.\n\n"
        "The first read is usually emotional.\n\n"
        f"So I start here: {first_signal}\n\n"
        "Then I ask what actually changed in the setup.\n\n"
        "That pause protects conviction."
    )
    return _with_variants("personalidade", original, text, base_dir)


def generate_prova_post(base_dir: Path, brief: dict) -> Dict[str, str]:
    news = _first_news_item(brief)
    topic = _clean_text(brief.get("top_theme", "macro"))
    original = _compose_post(
        base_dir,
        "prova",
        "Evidence beats opinion",
        [
            _short_text(_first_macro_line(brief, 0), 64),
            f"Confirmation: {_short_text(news.get('title', 'the latest data'), 64)}." if news else "Confirmation is showing up in the data.",
            "A thesis gets stronger when data and price confirm the same path.",
        ],
        "Conviction needs receipts.",
    )["text"]
    text = (
        f"A recurring mistake in {_short_text(topic, 48)}:\n\n"
        f"\"{_short_text(news.get('title', 'one macro headline explains the whole move'), 74)}.\"\n\n"
        "It is not that simple.\n\n"
        "The headline matters only if data confirms it.\n\n"
        "If positioning absorbs it, the read changes.\n\n"
        "Correlation is not a thesis."
    )
    return _with_variants("prova", original, text, base_dir)


POST_GENERATORS = {
    "valor": generate_valor_post,
    "crescimento": generate_crescimento_post,
    "personalidade": generate_personalidade_post,
    "prova": generate_prova_post,
}


def generate_post_by_type(base_dir: Path, brief: dict, post_type: str) -> Dict[str, str]:
    generator = POST_GENERATORS.get(post_type)
    if generator is None:
        raise ValueError(f"Unsupported post type: {post_type}")
    return generator(base_dir, brief)


def save_post_bundle(base_dir: Path, file_name: str, payload: Dict) -> Path:
    output = base_dir / "data" / "published" / file_name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
