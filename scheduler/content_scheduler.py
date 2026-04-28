from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from zoneinfo import ZoneInfo

import yaml

from content.x_post_types import generate_post_by_type


def load_x_schedule(base_dir: Path) -> Dict:
    path = base_dir / "config" / "x_schedule.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _timezone(schedule: Dict) -> ZoneInfo:
    return ZoneInfo(schedule.get("timezone", "America/Sao_Paulo"))


def get_day_schedule(base_dir: Path, target_date: datetime | None = None) -> Dict:
    schedule = load_x_schedule(base_dir)
    now = target_date or datetime.now(_timezone(schedule))
    weekday = now.strftime("%A").lower()
    return schedule.get("week", {}).get(weekday, {})


def format_week_schedule(base_dir: Path) -> str:
    schedule = load_x_schedule(base_dir)
    lines = ["X weekly schedule"]
    for day_name, day_config in schedule.get("week", {}).items():
        performance = day_config.get("performance", "-")
        lines.append(f"{day_name.title()} | performance: {performance}")
        for slot in day_config.get("slots", []):
            lines.append(
                f"- {slot.get('time_brt')} BRT | {slot.get('label', 'Post')} | {str(slot.get('type', '')).upper()}"
            )
    return "\n".join(lines)


def _tomorrow(base_dir: Path) -> datetime:
    schedule = load_x_schedule(base_dir)
    return datetime.now(_timezone(schedule)) + timedelta(days=1)


def _build_slot_drafts(base_dir: Path, brief: dict, target_date: datetime) -> List[Dict]:
    day_schedule = get_day_schedule(base_dir, target_date)
    slots = day_schedule.get("slots", [])
    drafts = []
    for slot in slots:
        post_type = slot.get("type", "valor")
        post = generate_post_by_type(base_dir, brief, post_type)
        drafts.append(
            {
                "time_brt": slot.get("time_brt"),
                "label": slot.get("label", "Post"),
                "type": post_type,
                "text": post["text"],
                "variants": post.get("variants", []),
            }
        )
    return drafts


def _format_draft_text(draft: Dict) -> List[str]:
    variants = draft.get("variants") or [{"style": "structured", "text": draft.get("text", "")}]
    lines: List[str] = []
    for variant in variants:
        lines.append(f"{str(variant.get('style', 'versao')).upper()}:")
        lines.append(str(variant.get("text", "")).strip())
    return lines


def format_x_drafts_message(target_date: datetime, drafts: List[Dict]) -> str:
    day_label = target_date.strftime("%A").upper()
    date_label = target_date.strftime("%d/%m")
    lines = [f"Posts de {day_label} {date_label}", "-" * 32]
    for draft in drafts:
        lines.append(f"{draft['time_brt']} - {draft['label']} [{draft['type'].upper()}]")
        lines.extend(_format_draft_text(draft))
        lines.append("-" * 32)
    return "\n".join(lines)


def latest_x_drafts_path(base_dir: Path) -> Path | None:
    published = base_dir / "data" / "published"
    dated = sorted(published.glob("x_drafts_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if dated:
        return dated[0]
    fallback = published / "x_post_drafts.json"
    return fallback if fallback.exists() else None


def read_latest_x_drafts(base_dir: Path) -> Dict | List | None:
    path = latest_x_drafts_path(base_dir)
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def format_latest_x_drafts(base_dir: Path) -> str:
    payload = read_latest_x_drafts(base_dir)
    if not payload:
        return "Nenhum draft de X encontrado. Rode `python main.py daily` primeiro."

    if isinstance(payload, dict):
        drafts = payload.get("drafts", [])
        date = payload.get("date", "-")
        lines = [f"Drafts para X ({date}):"]
    else:
        drafts = payload
        lines = ["Drafts atuais para X:"]

    for index, draft in enumerate(drafts, 1):
        if isinstance(draft, dict):
            header = f"{index}. [{draft.get('type', 'sem_tipo')}]"
            if draft.get("time_brt"):
                header += f" {draft.get('time_brt')}"
            lines.append(header)
            lines.extend(_format_draft_text(draft))
        else:
            lines.append(f"{index}. {draft}")
    return "\n".join(lines)


def generate_tomorrow_x_drafts(base_dir: Path, brief: dict, send_telegram: bool = True) -> Dict:
    target_date = _tomorrow(base_dir)
    drafts = _build_slot_drafts(base_dir, brief, target_date)
    payload = {
        "date": target_date.date().isoformat(),
        "weekday": target_date.strftime("%A").lower(),
        "drafts": drafts,
    }

    output = base_dir / "data" / "published" / f"x_drafts_{payload['date']}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if send_telegram:
        from utils.telegram_notifier import TelegramNotifier

        notifier = TelegramNotifier()
        notifier.send_long_message(format_x_drafts_message(target_date, drafts))

    return payload
