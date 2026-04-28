"""
Bootstrap de conhecimento curado sem alterar o fluxo principal do agente.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from memory.chromadb_manager import ChromaDBManager


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _build_seed_documents(base_dir: Path) -> List[Dict[str, Any]]:
    knowledge_dir = base_dir / "knowledge"
    seed = _load_json(knowledge_dir / "seed_profiles.json")
    if not seed:
        return []

    timestamp = datetime.utcnow().isoformat()
    documents: List[Dict[str, Any]] = []

    newsletter = seed.get("newsletter_learning", {})
    for index, item in enumerate(newsletter.get("must_do", []), 1):
        documents.append(
            {
                "id": f"seed_newsletter_rule_{index}",
                "text": f"Regra editorial de newsletter: {item}",
                "metadata": {
                    "api": "USER_SEED",
                    "focus_area": "Editorial_Newsletter",
                    "timestamp": timestamp,
                    "type": "seed_learning",
                    "seed_category": "newsletter_rule",
                    "title": f"Newsletter rule {index}",
                },
            }
        )

    x_learning = seed.get("x_learning", {})
    for index, item in enumerate(x_learning.get("style_principles", []), 1):
        documents.append(
            {
                "id": f"seed_x_rule_{index}",
                "text": f"Principio editorial para X: {item}",
                "metadata": {
                    "api": "USER_SEED",
                    "focus_area": "Editorial_X",
                    "timestamp": timestamp,
                    "type": "seed_learning",
                    "seed_category": "x_rule",
                    "title": f"X rule {index}",
                },
            }
        )

    for index, account in enumerate(seed.get("x_accounts", []), 1):
        handle = account.get("handle", f"account_{index}")
        role = account.get("role", "referencia")
        url = account.get("url", "")
        documents.append(
            {
                "id": f"seed_x_account_{handle.lower()}",
                "text": f"Conta de referencia no X: @{handle}. Papel: {role}. URL: {url}",
                "metadata": {
                    "api": "USER_SEED",
                    "focus_area": "Editorial_X",
                    "timestamp": timestamp,
                    "type": "seed_reference",
                    "seed_category": "x_account",
                    "title": handle,
                    "role": role,
                    "url": url,
                },
            }
        )

    cards = [
        ("newsletter_card.md", "Editorial_Newsletter", "newsletter_card"),
        ("x_style_card.md", "Editorial_X", "x_style_card"),
    ]
    for file_name, focus_area, seed_category in cards:
        card_path = knowledge_dir / "cards" / file_name
        content = _load_text(card_path)
        if not content:
            continue
        documents.append(
            {
                "id": f"seed_card_{seed_category}",
                "text": content,
                "metadata": {
                    "api": "USER_SEED",
                    "focus_area": focus_area,
                    "timestamp": timestamp,
                    "type": "seed_card",
                    "seed_category": seed_category,
                    "title": file_name,
                },
            }
        )

    return documents


def bootstrap_user_learning(base_dir: Path) -> Dict[str, Any]:
    """
    Carrega sementes curatoriais em memoria sem substituir o que ja existe.
    Pode ser executado varias vezes sem duplicar registros.
    """

    documents = _build_seed_documents(base_dir)
    db = ChromaDBManager()

    inserted = 0
    for item in documents:
        db.collection.upsert(
            ids=[item["id"]],
            documents=[item["text"]],
            metadatas=[item["metadata"]],
        )
        inserted += 1

    seed = _load_json(base_dir / "knowledge" / "seed_profiles.json")
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "ok" if documents else "empty",
        "documents_upserted": inserted,
        "seed_accounts": len(seed.get("x_accounts", [])),
        "newsletter_principles": len(seed.get("newsletter_learning", {}).get("must_do", [])),
        "x_principles": len(seed.get("x_learning", {}).get("style_principles", [])),
    }

    output_path = base_dir / "data" / "bootstrap" / "learning_bootstrap_summary.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
