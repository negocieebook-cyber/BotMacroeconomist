from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _inbox_path(base_dir: Path) -> Path:
    path = base_dir / "data" / "inbox" / "manual_inputs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ingest_manual_item(base_dir: Path, payload: Dict[str, Any]) -> None:
    clean_payload = {k: v for k, v in payload.items() if v not in (None, "", [])}
    clean_payload["created_at"] = datetime.now(timezone.utc).isoformat()
    with _inbox_path(base_dir).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(clean_payload, ensure_ascii=False) + "\n")


def load_manual_items(base_dir: Path) -> List[Dict[str, Any]]:
    path = _inbox_path(base_dir)
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows
