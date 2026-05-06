"""Search repository queries for paper content and notes."""

from __future__ import annotations

import logging
import sqlite3

from scikms.kms.db.connection import db_conn
from scikms.kms.db.constants import PAPER_SELECT_COLS
from scikms.kms.repositories.models import Paper

logger = logging.getLogger(__name__)

def search_content_fts(fts_query: str) -> list[Paper]:
    with db_conn() as conn:
        try:
            rows = conn.execute(
                f"SELECT {PAPER_SELECT_COLS}, fts.rank FROM papers p "
                "JOIN papers_fts fts ON p.id = fts.rowid "
                "WHERE papers_fts MATCH ? ORDER BY fts.rank",
                (fts_query,),
            ).fetchall()
            return [Paper.from_row(dict(r)) for r in rows]
        except sqlite3.OperationalError:
            return []


def search_notes_fts(fts_query: str) -> list[Paper]:
    """Search notes using the notes FTS table."""
    with db_conn() as conn:
        try:
            rows = conn.execute(
                f"SELECT {PAPER_SELECT_COLS} FROM papers p "
                "JOIN papers_notes_fts nfts ON p.id = nfts.rowid "
                "WHERE papers_notes_fts MATCH ?",
                (fts_query,),
            ).fetchall()
            return [Paper.from_row(dict(r)) for r in rows]
        except sqlite3.OperationalError as exc:
            logger.warning("FTS notes search failed for query %r: %s", fts_query, exc)
            return []


def search_notes_like(like_query: str) -> list[Paper]:
    """Search notes and highlights using LIKE."""
    with db_conn() as conn:
        rows = conn.execute(
            f"SELECT {PAPER_SELECT_COLS} FROM papers p "
            "WHERE (notes LIKE ? OR highlights LIKE ?) "
            "ORDER BY added_at DESC",
            (like_query, like_query),
        ).fetchall()
        return [Paper.from_row(dict(r)) for r in rows]


def search_basic_like(like_query: str) -> list[Paper]:
    with db_conn() as conn:
        rows = conn.execute(
            f"SELECT {PAPER_SELECT_COLS} FROM papers p "
            "WHERE title LIKE ? OR authors LIKE ? "
            "   OR abstract LIKE ? OR keywords LIKE ? "
            "   OR notes LIKE ? OR highlights LIKE ? "
            "ORDER BY added_at DESC",
            (like_query, like_query, like_query, like_query, like_query, like_query),
        ).fetchall()
        return [Paper.from_row(dict(r)) for r in rows]
