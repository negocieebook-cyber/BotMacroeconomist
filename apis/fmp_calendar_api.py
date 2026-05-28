"""
Cliente do calendario economico da Financial Modeling Prep.

Lê a chave de FMP_API_KEY no .env e nunca inclui a chave em mensagens,
metadados ou logs. A resposta e armazenada em cache local para economizar
requisicoes do plano gratuito.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from config import (
    ECONOMIC_CALENDAR_CACHE_MINUTES,
    ECONOMIC_CALENDAR_LOOKAHEAD_DAYS,
    FMP_API_KEY,
    FMP_ECONOMIC_CALENDAR_BASE,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)


class FmpEconomicCalendarClient:
    """Busca eventos macro programados e realizados via FMP."""

    def __init__(
        self,
        api_key: str = FMP_API_KEY,
        base_url: str = FMP_ECONOMIC_CALENDAR_BASE,
        cache_dir: str = "data/cache/economic_calendar",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_calendar(
        self,
        start_date: Optional[date | str] = None,
        end_date: Optional[date | str] = None,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """Retorna eventos entre start_date e end_date, inclusive."""
        if not self.is_configured:
            logger.info("FMP_API_KEY nao configurada; calendario economico desativado")
            return []

        start = self._coerce_date(start_date) or datetime.now(timezone.utc).date()
        end = self._coerce_date(end_date) or start
        cache_path = self._cache_path(start, end)

        if use_cache:
            cached = self._read_cache(cache_path)
            if cached is not None:
                return cached

        params = {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "apikey": self.api_key,
        }

        try:
            response = self.session.get(self.base_url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
            events = payload if isinstance(payload, list) else []
            normalized = [self._normalize_event(event) for event in events if isinstance(event, dict)]
            self._write_cache(cache_path, normalized)
            return normalized
        except requests.exceptions.RequestException as exc:
            logger.warning(f"Falha ao buscar calendario economico FMP: {exc.__class__.__name__}")
        except ValueError:
            logger.warning("Resposta invalida da FMP ao buscar calendario economico")

        cached = self._read_cache(cache_path, ignore_expiry=True)
        return cached or []

    def get_today_and_next_days(self, days_ahead: int = ECONOMIC_CALENDAR_LOOKAHEAD_DAYS) -> List[Dict[str, Any]]:
        today = datetime.now(timezone.utc).date()
        return self.get_calendar(today, today + timedelta(days=max(days_ahead, 0)))

    def format_for_context(self, events: Optional[List[Dict[str, Any]]] = None, limit: int = 12) -> str:
        """Formata eventos para prompt, briefing e memoria."""
        events = events if events is not None else self.get_today_and_next_days()
        if not events:
            return "Calendario economico FMP indisponivel ou sem eventos no intervalo."

        ranked = sorted(events, key=lambda item: (self._impact_rank(item.get("impact")), item.get("date") or ""))
        lines = ["Calendario economico FMP (horarios em UTC):"]

        for event in ranked[:limit]:
            when = event.get("date") or "-"
            country = event.get("country") or "-"
            currency = event.get("currency") or "-"
            name = event.get("event") or "Evento economico"
            impact = event.get("impact") or "-"
            previous = self._fmt_value(event.get("previous"))
            estimate = self._fmt_value(event.get("estimate"))
            actual = self._fmt_value(event.get("actual"))

            lines.append(
                f"- {when} | {country}/{currency} | {impact} | {name} | "
                f"anterior: {previous}; consenso: {estimate}; atual: {actual}"
            )

        return "\n".join(lines)

    def _read_cache(self, path: Path, ignore_expiry: bool = False) -> Optional[List[Dict[str, Any]]]:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            created_at = datetime.fromisoformat(payload.get("created_at", ""))
            age = datetime.now(timezone.utc) - created_at
            if not ignore_expiry and age.total_seconds() > ECONOMIC_CALENDAR_CACHE_MINUTES * 60:
                return None
            events = payload.get("events", [])
            return events if isinstance(events, list) else None
        except Exception:
            return None

    def _write_cache(self, path: Path, events: List[Dict[str, Any]]) -> None:
        payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "events": events,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _cache_path(self, start: date, end: date) -> Path:
        return self.cache_dir / f"fmp_calendar_{start.isoformat()}_{end.isoformat()}.json"

    @staticmethod
    def _coerce_date(value: Optional[date | str]) -> Optional[date]:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        return datetime.fromisoformat(str(value)).date()

    @staticmethod
    def _normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "date": event.get("date"),
            "country": event.get("country"),
            "event": event.get("event"),
            "currency": event.get("currency"),
            "previous": event.get("previous"),
            "estimate": event.get("estimate"),
            "actual": event.get("actual"),
            "change": event.get("change"),
            "impact": event.get("impact"),
            "changePercentage": event.get("changePercentage"),
        }

    @staticmethod
    def _impact_rank(impact: Any) -> int:
        value = str(impact or "").lower()
        if value == "high":
            return 0
        if value == "medium":
            return 1
        if value == "low":
            return 2
        return 3

    @staticmethod
    def _fmt_value(value: Any) -> str:
        if value is None or value == "":
            return "N/D"
        return str(value)
