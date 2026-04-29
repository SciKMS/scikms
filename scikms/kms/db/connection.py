"""SQLite connection helpers for the KMS data layer."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Generator

from scikms import kms as _kms


@contextmanager
def db_conn() -> Generator[sqlite3.Connection]:
    """Auto-commit, auto-close, WAL-mode connection context manager."""
    conn = sqlite3.connect(str(_kms.DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
