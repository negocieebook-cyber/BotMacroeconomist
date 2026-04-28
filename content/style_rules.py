from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml


def load_style_rules(base_dir: Path) -> Dict:
    with (base_dir / "config" / "x_post_rules.yaml").open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}
