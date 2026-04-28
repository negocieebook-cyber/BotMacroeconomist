from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _read(path: str) -> str:
    return (BASE_DIR / path).read_text(encoding="utf-8")


def test_required_files() -> None:
    required = [
        "main.py",
        "health_check.py",
        "config.py",
        ".env.example",
        "requirements-core.txt",
        "requirements-memory.txt",
        "requirements-analytics.txt",
        "config/news_sources.yaml",
        "collect/x_collect.py",
        "process/unify_inputs.py",
        "process/build_briefs.py",
    ]
    missing = [path for path in required if not (BASE_DIR / path).exists()]
    assert not missing, f"Arquivos obrigatorios ausentes: {missing}"


def test_x_defaults_to_disabled() -> None:
    env_example = _read(".env.example")
    config_py = _read("config.py")
    assert "X_COLLECTION_MODE=disabled" in env_example
    assert 'os.getenv("X_COLLECTION_MODE", "disabled")' in config_py
    assert "X_ALLOW_MOCK_FALLBACK=False" in env_example


def test_no_placeholder_news_source() -> None:
    news_sources = _read("config/news_sources.yaml")
    assert "example.com" not in news_sources


def test_source_mode_is_propagated() -> None:
    assert '"source_mode"' in _read("collect/rss_collect.py")
    assert '"source_mode"' in _read("collect/news_sites_collect.py")
    assert '"source_mode"' in _read("process/unify_inputs.py")
    assert '"source_modes"' in _read("process/build_briefs.py")


def run_all() -> int:
    tests = [
        test_required_files,
        test_x_defaults_to_disabled,
        test_no_placeholder_news_source,
        test_source_mode_is_propagated,
    ]

    failures = []
    for test in tests:
        try:
            test()
            print(f"[OK] {test.__name__}")
        except AssertionError as exc:
            failures.append({"test": test.__name__, "error": str(exc)})
            print(f"[FALHOU] {test.__name__}: {exc}")

    if failures:
        print(json.dumps({"failures": failures}, ensure_ascii=False, indent=2))
        return 1

    print("Testes leves passaram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_all())
