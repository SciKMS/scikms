"""Paper table repository queries."""

from __future__ import annotations

from typing import Any

from scikms.kms.db.connection import db_conn
from scikms.kms.db.constants import PAPER_ORDER_MAP, PAPER_SELECT_COLS

from .models import Paper, PaperDuplicateRef


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


def get_all_papers(order: str = "Recently added") -> list[Paper]:
    # Set the order to the newest
    sql_order = PAPER_ORDER_MAP.get(order, "added_at DESC")
    with db_conn() as conn:
        rows = conn.execute(
            f"SELECT {PAPER_SELECT_COLS} FROM papers p ORDER BY {sql_order}"
        ).fetchall()
        return [Paper.from_row(dict(row)) for row in rows]


def get_paper_by_id(paper_id: int) -> Paper | None:
    """Returns the Paper Object by querying the paper.id

    Args:
        paper_id: int: The paper id
    Returns:
        paper_object: Paper | None: The Paper dataclass defined by the 'papers'
                                   table in the schema
  
    """
    with db_conn() as conn:
        row = conn.execute(
            f"SELECT {PAPER_SELECT_COLS}, p.full_text FROM papers p WHERE p.id=?",
            (paper_id,),
        ).fetchone()
        return Paper.from_row(dict(row)) if row else None


# Add the API in the Paper model to transform to the dict object 
# To connect to the old code
def insert_paper(paper: Paper| dict[str, Any]) -> int:
    if isinstance(paper, Paper):
        paper = paper.to_dict()

    cols = list(paper.keys())
    placeholders = ", ".join(f":{c}" for c in cols)
    col_str = ", ".join(cols)
    
    insert_command = f"INSERT INTO papers ({col_str}) VALUES ({placeholders})"
    print(f"[INFO] Insert Queries: {insert_command}")

    with db_conn() as conn:
        conn.execute(insert_command, paper)
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def update_paper(paper_id: int, update_fields: dict[str, Any]) -> None:
    if not update_fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in update_fields)
    vals = list(update_fields.values()) + [paper_id]
    with db_conn() as conn:
        conn.execute(f"UPDATE papers SET {set_clause} WHERE id=?", vals)


def delete_paper_row(paper_id: int) -> None:
    with db_conn() as conn:
        conn.execute("DELETE FROM papers WHERE id=?", (paper_id,))


def find_duplicate_by_md5(md5: str) -> PaperDuplicateRef | None:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id,title,doi FROM papers WHERE md5=?", (md5,)
        ).fetchone()
        return PaperDuplicateRef.from_row(dict(row)) if row else None


def find_duplicate_by_doi(doi: str) -> PaperDuplicateRef | None:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id,title,doi FROM papers WHERE doi=?", (doi,)
        ).fetchone()
        return PaperDuplicateRef.from_row(dict(row)) if row else None


def get_duplicate_title_candidates() -> list[PaperDuplicateRef]:
    with db_conn() as conn:
        rows = conn.execute("SELECT id,title,doi FROM papers").fetchall()
        return [PaperDuplicateRef.from_row(dict(r)) for r in rows]
