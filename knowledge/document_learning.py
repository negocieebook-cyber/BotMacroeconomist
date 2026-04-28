from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def load_seed_profiles(base_dir: Path) -> Dict:
    path = base_dir / "knowledge" / "seed_profiles.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_user_materials(base_dir: Path) -> Dict:
    path = base_dir / "knowledge" / "processed" / "user_materials.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_source_catalog(base_dir: Path) -> List[Dict]:
    seed = load_seed_profiles(base_dir)
    catalog: List[Dict] = []

    for account in seed.get("x_accounts", []):
        catalog.append({
            "type": "x_account",
            "name": account["handle"],
            "role": account["role"],
            "url": account["url"],
        })

    newsletter = seed.get("newsletter_learning", {})
    for file_name in newsletter.get("source_files", []):
        catalog.append({"type": "document", "name": file_name, "role": "newsletter_seed"})

    x_learning = seed.get("x_learning", {})
    for file_name in x_learning.get("source_files", []):
        catalog.append({"type": "document", "name": file_name, "role": "x_seed"})

    return catalog
