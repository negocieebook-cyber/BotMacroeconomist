from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def append_record(base_dir: Path, filename: str, payload: Dict[str, Any]) -> None:
    store_path = base_dir / "data" / "processed" / filename
    store_path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    if store_path.exists():
        records = json.loads(store_path.read_text(encoding="utf-8"))
    payload = {"timestamp": datetime.now(timezone.utc).isoformat(), **payload}
    records.append(payload)
    store_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
