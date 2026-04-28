from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def save_learnings(base_dir: Path, learnings: List[Dict]) -> None:
    path = base_dir / "data" / "processed" / "learnings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(learnings, ensure_ascii=False, indent=2), encoding="utf-8")
