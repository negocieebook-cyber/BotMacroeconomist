from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import yaml
from requests import exceptions as requests_exceptions

from config import (
    REQUEST_TIMEOUT,
    X_ALLOW_MOCK_FALLBACK,
    X_API_BASE,
    X_BEARER_TOKEN,
    X_COLLECTION_MODE,
    X_POST_FETCH_LIMIT,
    X_REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)

MOCK_X_POSTS: List[Dict[str, Any]] = [
    {
        "date": str(date.today()),
        "handle": "KobeissiLetter",
        "text": "Inflation progress remains uneven and services inflation is still elevated.",
        "topic_hint": "inflacao",
        "is_repost": False,
        "url": "https://x.example/fed-1",
        "engagement_hint": 0.7,
        "published_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
    },
    {
        "date": str(date.today()),
        "handle": "globalmarketss",
        "text": "US CPI surprised slightly to the upside, reinforcing higher-for-longer concerns.",
        "topic_hint": "juros",
        "is_repost": False,
        "url": "https://x.example/reuters-1",
        "engagement_hint": 0.8,
        "published_at": (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat(),
    },
    {
        "date": str(date.today()),
        "handle": "GabrielD_Ouro",
        "text": "Sticky core inflation may delay the timing of the first cut.",
        "topic_hint": "inflacao",
        "is_repost": False,
        "url": "https://x.example/macro-1",
        "engagement_hint": 0.6,
        "published_at": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
    },
    {
        "date": str(date.today()),
        "handle": "HeliumInsights",
        "text": "Helium markets remain tight in selected industrial applications after supply constraints.",
        "topic_hint": "helio",
        "is_repost": False,
        "url": "https://x.example/helium-1",
        "engagement_hint": 0.75,
        "published_at": (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat(),
    },
]


def _load_accounts(config_path: Path) -> Dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _build_allowed_handles(config: Dict[str, Any]) -> List[str]:
    handles: List[str] = []
    for group in ["official", "news", "macro_specialists"]:
        handles.extend(config.get(group, []) or [])
    blacklist = set(config.get("blacklist", []) or [])
    return [handle for handle in handles if handle not in blacklist]


def _infer_topic(text: str) -> str:
    lowered = (text or "").lower()
    if any(token in lowered for token in ["inflation", "cpi", "pce", "prices"]):
        return "inflacao"
    if any(token in lowered for token in ["rates", "yield", "fed", "cut", "hike", "juros"]):
        return "juros"
    if any(token in lowered for token in ["gdp", "growth", "activity", "payroll", "labor"]):
        return "atividade"
    if any(token in lowered for token in ["crypto", "bitcoin", "eth", "sol"]):
        return "cripto"
    if "helium" in lowered or "helio" in lowered:
        return "helio"
    return "macro"


def _fetch_x_posts_real(handles: List[str], topic_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    if X_COLLECTION_MODE in {"disabled", "off", "none"}:
        logger.info("Coleta do X desabilitada por configuracao; usando fontes RSS/site/manual.")
        return []

    if not X_BEARER_TOKEN:
        logger.info("X_BEARER_TOKEN ausente; coleta real do X indisponivel.")
        return []

    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
    rows: List[Dict[str, Any]] = []
    timeout = X_REQUEST_TIMEOUT or REQUEST_TIMEOUT
    max_per_handle = max(5, min(X_POST_FETCH_LIMIT, 10))

    for handle in handles:
        query_parts = [f"from:{handle}", "-is:retweet", "-is:reply"]
        if topic_filter:
            query_parts.append(f'"{topic_filter}"')
        query = " ".join(query_parts)
        params = {
            "query": query,
            "max_results": max_per_handle,
            "tweet.fields": "created_at,public_metrics,lang",
        }

        try:
            response = requests.get(
                f"{X_API_BASE}/tweets/search/recent",
                headers=headers,
                params=params,
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning(f"Falha ao consultar X para @{handle}: {exc}")
            continue

        for item in payload.get("data", []) or []:
            text = str(item.get("text", "")).strip()
            metrics = item.get("public_metrics", {}) or {}
            rows.append(
                {
                    "date": str(date.today()),
                    "handle": handle,
                    "text": text,
                    "topic_hint": _infer_topic(text),
                    "is_repost": False,
                    "url": f"https://x.com/{handle}/status/{item.get('id', '')}",
                    "engagement_hint": float(metrics.get("like_count", 0) + metrics.get("retweet_count", 0) * 2 + metrics.get("reply_count", 0)) / 100.0,
                    "published_at": item.get("created_at", datetime.now(timezone.utc).isoformat()),
                    "lang": item.get("lang", ""),
                    "like_count": metrics.get("like_count", 0),
                    "retweet_count": metrics.get("retweet_count", 0),
                    "reply_count": metrics.get("reply_count", 0),
                    "quote_count": metrics.get("quote_count", 0),
                    "bookmark_count": metrics.get("bookmark_count", 0),
                    "source_mode": "x_api",
                }
            )

    return rows


def diagnose_x_api(base_dir: Path, sample_handle: Optional[str] = None) -> Dict[str, Any]:
    config = _load_accounts(base_dir / "config" / "x_accounts.yaml")
    allowed = _build_allowed_handles(config)
    handle = sample_handle or (allowed[0] if allowed else "x")

    diagnosis: Dict[str, Any] = {
        "configured": bool(X_BEARER_TOKEN),
        "collection_mode": X_COLLECTION_MODE,
        "mock_fallback_enabled": X_ALLOW_MOCK_FALLBACK,
        "api_base": X_API_BASE,
        "handle_tested": handle,
        "status": "unknown",
        "http_status": None,
        "message": "",
        "details": {},
    }

    if X_COLLECTION_MODE in {"disabled", "off", "none"}:
        diagnosis["status"] = "disabled"
        diagnosis["message"] = "Coleta do X esta desabilitada. O pipeline usa RSS, sites e inputs manuais."
        return diagnosis

    if not X_BEARER_TOKEN:
        diagnosis["status"] = "missing_bearer"
        diagnosis["message"] = "X_BEARER_TOKEN nao configurado no .env. Sem problema: use RSS/sites/manual."
        return diagnosis

    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
    params = {
        "query": f"from:{handle} -is:retweet -is:reply",
        "max_results": 10,
        "tweet.fields": "created_at,public_metrics,lang",
    }

    try:
        response = requests.get(
            f"{X_API_BASE}/tweets/search/recent",
            headers=headers,
            params=params,
            timeout=X_REQUEST_TIMEOUT or REQUEST_TIMEOUT,
        )
        diagnosis["http_status"] = response.status_code

        if response.status_code == 200:
            payload = response.json()
            item_count = len(payload.get("data", []) or [])
            diagnosis["status"] = "ok"
            diagnosis["message"] = "Coleta do X funcionando."
            diagnosis["details"] = {
                "items_found": item_count,
                "meta": payload.get("meta", {}),
            }
            return diagnosis

        if response.status_code == 401:
            diagnosis["status"] = "invalid_token"
            diagnosis["message"] = "Bearer token invalido ou expirado."
        elif response.status_code == 403:
            diagnosis["status"] = "forbidden"
            diagnosis["message"] = "App sem permissao, plano ou acesso para esse endpoint."
        elif response.status_code == 429:
            diagnosis["status"] = "rate_limited"
            diagnosis["message"] = "Limite de taxa do X atingido."
        else:
            diagnosis["status"] = "http_error"
            diagnosis["message"] = f"X retornou HTTP {response.status_code}."

        try:
            diagnosis["details"] = response.json()
        except Exception:
            diagnosis["details"] = {"text": response.text[:500]}
        return diagnosis
    except requests_exceptions.ConnectionError as exc:
        diagnosis["status"] = "network_blocked"
        diagnosis["message"] = "Nao foi possivel conectar ao X API."
        diagnosis["details"] = {"error": str(exc)}
        return diagnosis
    except requests_exceptions.Timeout as exc:
        diagnosis["status"] = "timeout"
        diagnosis["message"] = "A consulta ao X expirou."
        diagnosis["details"] = {"error": str(exc)}
        return diagnosis
    except Exception as exc:
        diagnosis["status"] = "unexpected_error"
        diagnosis["message"] = "Erro inesperado ao consultar X."
        diagnosis["details"] = {"error": str(exc)}
        return diagnosis


def _filter_posts(posts: List[Dict[str, Any]], allowed: List[str], topic_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    filtered = [
        post for post in posts
        if post.get("handle") in allowed and not post.get("is_repost")
    ]

    if topic_filter:
        lowered = topic_filter.lower()
        filtered = [
            post for post in filtered
            if lowered in str(post.get("topic_hint", "")).lower()
            or lowered in str(post.get("text", "")).lower()
        ]

    return filtered


def collect_x_context(base_dir: Path, topic_filter: Optional[str] = None) -> pd.DataFrame:
    config = _load_accounts(base_dir / "config" / "x_accounts.yaml")
    allowed = _build_allowed_handles(config)

    real_posts = _fetch_x_posts_real(allowed, topic_filter=topic_filter)
    if real_posts:
        posts = real_posts
    elif X_ALLOW_MOCK_FALLBACK:
        posts = _filter_posts(MOCK_X_POSTS, allowed, topic_filter=topic_filter)
        for post in posts:
            post["source_mode"] = "mock"
    else:
        posts = []

    df = pd.DataFrame(posts)
    expected_columns = [
        "date",
        "handle",
        "text",
        "topic_hint",
        "is_repost",
        "url",
        "engagement_hint",
        "published_at",
        "source_mode",
    ]
    for column in expected_columns:
        if column not in df.columns:
            df[column] = ""

    output = base_dir / "data" / "raw" / "x_posts.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    return df
