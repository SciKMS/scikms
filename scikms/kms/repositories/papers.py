"""Paper table repository queries."""

from __future__ import annotations

from scikms.kms.db.connection import db_conn
from scikms.kms.db.constants import PAPER_ORDER_MAP, PAPER_SELECT_COLS
from typing import Any


def get_papers_count() -> int:
    with db_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]


def get_all_projects() -> list[str]:
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT project FROM papers "
            "WHERE project IS NOT NULL AND project != '' ORDER BY project"
        ).fetchall()
        return [r[0] for r in rows]


def get_all_papers(order: str = "Recently added") -> list[dict]:
    # Set the order to the newest
    sql_order = PAPER_ORDER_MAP.get(order, "added_at DESC")
    with db_conn() as conn:
        rows = conn.execute(
            f"SELECT {PAPER_SELECT_COLS} FROM papers p ORDER BY {sql_order}"
        ).fetchall()
        return [dict(r) for r in rows]


def get_paper_by_id(paper_id: int) -> dict | None:
    with db_conn() as conn:
        row = conn.execute(
            f"SELECT {PAPER_SELECT_COLS}, p.full_text FROM papers p WHERE p.id=?",
            (paper_id,),
        ).fetchone()
        return dict(row) if row else None


def insert_paper(paper: dict[Any, Any]) -> int:
    cols = list(paper.keys())
    placeholders = ", ".join(f":{c}" for c in cols)
    col_str = ", ".join(cols)
    with db_conn() as conn:
        conn.execute(f"INSERT INTO papers ({col_str}) VALUES ({placeholders})", paper)
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def update_paper(paper_id: int, fields: dict) -> None:
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [paper_id]
    with db_conn() as conn:
        conn.execute(f"UPDATE papers SET {set_clause} WHERE id=?", vals)


def delete_paper_row(paper_id: int) -> None:
    with db_conn() as conn:
        conn.execute("DELETE FROM papers WHERE id=?", (paper_id,))


def find_duplicate_by_md5(md5: str) -> dict | None:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id,title,doi FROM papers WHERE md5=?", (md5,)
        ).fetchone()
        return dict(row) if row else None


def find_duplicate_by_doi(doi: str) -> dict | None:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id,title,doi FROM papers WHERE doi=?", (doi,)
        ).fetchone()
        return dict(row) if row else None


def get_duplicate_title_candidates() -> list[dict]:
    with db_conn() as conn:
        rows = conn.execute("SELECT id,title,doi FROM papers").fetchall()
        return [dict(r) for r in rows]
