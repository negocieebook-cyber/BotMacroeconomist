"""
Leitura simples da biblioteca teorica macro.
"""

from pathlib import Path
from typing import Dict, List


LIBRARY_PATH = Path(__file__).resolve().parents[1] / "MACRO_LIBRARY.md"


def load_macro_library() -> str:
    return LIBRARY_PATH.read_text(encoding="utf-8")


def get_macro_learning_cards() -> List[Dict[str, str]]:
    """Converte a biblioteca teorica em cards tecnicos aprendiveis."""
    text = load_macro_library()
    lines = text.splitlines()
    cards: List[Dict[str, str]] = []

    current_domain = ""
    current_title = ""
    current_body: List[str] = []

    def flush_current() -> None:
        nonlocal current_title, current_body
        if not current_title:
            return

        body = "\n".join(line.strip() for line in current_body if line.strip()).strip()
        cards.append(
            {
                "domain": current_domain or "Macro",
                "title": current_title,
                "content": body,
            }
        )
        current_title = ""
        current_body = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## "):
            flush_current()
            current_domain = stripped[3:].strip()
            continue

        if stripped.startswith("### "):
            flush_current()
            current_title = stripped[4:].strip()
            continue

        if current_title:
            current_body.append(line)

    flush_current()
    return cards


def select_relevant_theory_sections(collected_blocks: Dict[str, Dict]) -> List[str]:
    text = load_macro_library()
    sections = []

    keyword_map = [
        ("inflacao_politica", "## Inflacao"),
        ("inflacao_politica", "## Politica Monetaria"),
        ("crescimento", "## Crescimento"),
        ("mercado_trabalho", "## Mercado de Trabalho"),
        ("trade_finance", "## Credito e Risco"),
        ("trade_finance", "## Setor Externo"),
    ]

    for block_name, heading in keyword_map:
        if block_name in collected_blocks:
            section = _extract_section(text, heading)
            if section and section not in sections:
                sections.append(section)

    return sections[:4]


def _extract_section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start == -1:
        return ""

    next_heading = text.find("\n## ", start + len(heading))
    if next_heading == -1:
        next_heading = len(text)

    return text[start:next_heading].strip()
