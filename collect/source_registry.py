from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Source:
    name: str
    category: str
    trust_score: float


DEFAULT_SOURCES: List[Source] = [
    Source(name="FRED", category="macro_data", trust_score=1.0),
    Source(name="IMF", category="macro_data", trust_score=1.0),
    Source(name="WorldBank", category="macro_data", trust_score=0.95),
    Source(name="OECD", category="macro_data", trust_score=0.95),
    Source(name="BIS", category="macro_data", trust_score=0.95),
    Source(name="FED", category="official_x", trust_score=1.0),
    Source(name="ECB", category="official_x", trust_score=1.0),
    Source(name="ReutersBiz", category="news_x", trust_score=0.9),
    Source(name="FT", category="news_x", trust_score=0.9),
    Source(name="MacroAnalystA", category="specialist_x", trust_score=0.8),
]


def source_lookup() -> Dict[str, Source]:
    return {source.name: source for source in DEFAULT_SOURCES}
