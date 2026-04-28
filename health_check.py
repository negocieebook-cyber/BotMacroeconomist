from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


BASE_DIR = Path(__file__).resolve().parent

CORE_PACKAGES = [
    "requests",
    "dotenv",
    "yaml",
    "feedparser",
    "bs4",
]

FULL_PACKAGES = [
    "pandas",
    "numpy",
    "chromadb",
    "torch",
    "transformers",
    "huggingface_hub",
    "sentence_transformers",
    "statsmodels",
    "sqlalchemy",
    "openai",
]

OPTIONAL_PACKAGES = [
    "arch",
    "prophet",
    "plotly",
    "matplotlib",
    "yfinance",
]

REQUIRED_PATHS = [
    "main.py",
    "config.py",
    "requirements.txt",
    "config/news_sources.yaml",
    "config/x_schedule.yaml",
    "collect",
    "process",
    "content",
    "memory",
    "scheduler",
]


def _read_env_file() -> Dict[str, str]:
    env_path = BASE_DIR / ".env"
    values: Dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _env(name: str, default: str = "") -> str:
    return os.getenv(name) or _read_env_file().get(name, default)


def _package_status(names: Iterable[str]) -> List[Tuple[str, bool, str]]:
    rows = []
    for name in names:
        try:
            importlib.import_module(name)
            rows.append((name, True, ""))
        except Exception as exc:
            rows.append((name, False, str(exc)))
    return rows


def _path_status(paths: Iterable[str]) -> List[Tuple[str, bool]]:
    return [(path, (BASE_DIR / path).exists()) for path in paths]


def _print_section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def _print_status(rows: Iterable[Tuple[str, bool] | Tuple[str, bool, str]]) -> bool:
    all_ok = True
    for row in rows:
        label, ok = row[0], row[1]
        detail = row[2] if len(row) > 2 else ""
        marker = "OK" if ok else "FALTA"
        print(f"[{marker}] {label}")
        if detail and not ok:
            print(f"       {detail}")
        all_ok = all_ok and ok
    return all_ok


def _data_snapshot() -> None:
    data_dir = BASE_DIR / "data"
    if not data_dir.exists():
        print("[INFO] data/ ainda nao existe. Sera criado nos pipelines.")
        return

    interesting = [
        data_dir / "raw" / "rss_items.csv",
        data_dir / "raw" / "site_news.csv",
        data_dir / "raw" / "x_posts.csv",
        data_dir / "briefs" / "daily_brief.json",
        data_dir / "briefs" / "weekly_brief.json",
        data_dir / "published" / "x_post_drafts.json",
        data_dir / "published" / "newsletter_draft.md",
        data_dir / "chroma_db" / "chroma.sqlite3",
    ]
    for path in interesting:
        if path.exists():
            rel = path.relative_to(BASE_DIR)
            print(f"[OK] {rel} ({path.stat().st_size} bytes)")


def main() -> int:
    print("BotMacroeconomist health check")
    print(f"Projeto: {BASE_DIR}")

    _print_section("Estrutura")
    paths_ok = _print_status(_path_status(REQUIRED_PATHS))

    _print_section("Dependencias essenciais")
    core_ok = _print_status(_package_status(CORE_PACKAGES))

    _print_section("Dependencias do modo completo")
    full_rows = _package_status(FULL_PACKAGES)
    full_ok = _print_status(full_rows)

    _print_section("Dependencias opcionais")
    _print_status(_package_status(OPTIONAL_PACKAGES))

    _print_section("Configuracao operacional")
    x_mode = _env("X_COLLECTION_MODE", "disabled").lower()
    x_token = bool(_env("X_BEARER_TOKEN"))
    allow_x_mock = _env("X_ALLOW_MOCK_FALLBACK", "False").lower() == "true"
    telegram_ready = bool(_env("TELEGRAM_BOT_TOKEN"))
    fred_ready = bool(_env("FRED_API_KEY")) and _env("FRED_API_KEY") != "seu_fred_api_key_aqui"
    llm_ready = bool(_env("OPENAI_API_KEY")) or bool(_env("OPENROUTER_API_KEY"))

    print(f"X_COLLECTION_MODE={x_mode}")
    if x_mode in {"disabled", "off", "none"}:
        print("[OK] X desabilitado. Pipeline deve usar RSS, sites e inputs manuais.")
    elif x_token:
        print("[OK] X token configurado para coleta real.")
    elif allow_x_mock:
        print("[INFO] X sem token, mas fallback mock esta habilitado.")
    else:
        print("[AVISO] X habilitado sem token. Recomendado: X_COLLECTION_MODE=disabled.")

    print(f"[{'OK' if fred_ready else 'INFO'}] FRED_API_KEY {'configurada' if fred_ready else 'nao configurada ou placeholder'}")
    print(f"[{'OK' if llm_ready else 'INFO'}] LLM {'configurado' if llm_ready else 'opcional nao configurado'}")
    print(f"[{'OK' if telegram_ready else 'INFO'}] Telegram {'configurado' if telegram_ready else 'opcional nao configurado'}")

    _print_section("Artefatos existentes")
    _data_snapshot()

    print()
    if paths_ok and core_ok and full_ok:
        print("Resultado: projeto pronto para o modo completo.")
        return 0

    if paths_ok and core_ok:
        print("Resultado: estrutura e dependencias essenciais OK.")
        print("O pipeline leve/editorial pode rodar; memoria semantica/econometria ainda precisam do stack completo.")
        print("Para memoria: python -m pip install -r requirements-memory.txt")
        print("Para tudo: python -m pip install -r requirements.txt")
        return 1

    print("Resultado: ha problemas estruturais ou dependencias essenciais faltando.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
