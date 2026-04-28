from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List


SCHEMA = """
CREATE TABLE IF NOT EXISTS factual_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    source_name TEXT,
    title TEXT,
    summary TEXT,
    url TEXT,
    event_ts TEXT,
    trust_score REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS editorial_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    pattern_type TEXT,
    key TEXT,
    value TEXT,
    score REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS topic_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    snapshot TEXT,
    period_label TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def db_path(base_dir: Path) -> Path:
    path = base_dir / "data" / "processed" / "memory.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(base_dir: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(base_dir))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def insert_many(base_dir: Path, table: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    conn = get_connection(base_dir)
    keys = list(rows[0].keys())
    placeholders = ",".join("?" for _ in keys)
    sql = f"INSERT INTO {table} ({','.join(keys)}) VALUES ({placeholders})"
    conn.executemany(sql, [tuple(row[k] for k in keys) for row in rows])
    conn.commit()
    conn.close()


def fetch_rows(base_dir: Path, query: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
    conn = get_connection(base_dir)
    cur = conn.execute(query, tuple(params))
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows
