"""scikms.kms.db — SQLite + FTS5 data layer.

Schema, CRUD, dual-channel full-text search (content + notes), config
persistence. Derived verbatim from SciKMS v3.1 y-khoa/modules/db.py; the only
substantive change is removing the Streamlit ``@st.cache_data`` decorators
(scikms uses signal-based invalidation) and taking paths from
:mod:`scikms.kms` rather than hardcoded CWD.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import contextmanager

from scikms import kms as _kms
from scikms.kms.config import DEFAULT_TAG_DICT


@contextmanager
def db_conn():
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


def init_db() -> None:
    with db_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS papers (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                md5               TEXT UNIQUE,
                original_filename TEXT,
                renamed_filename  TEXT,
                title             TEXT,
                authors           TEXT,
                year              INTEGER,
                journal           TEXT,
                doi               TEXT,
                abstract          TEXT,
                keywords          TEXT,
                full_text         TEXT,
                tags              TEXT,
                notes             TEXT    DEFAULT '',
                highlights        TEXT    DEFAULT '[]',
                status            TEXT    DEFAULT 'unread',
                starred           INTEGER DEFAULT 0,
                pages             INTEGER DEFAULT 0,
                added_at          TEXT,
                file_path         TEXT,
                project           TEXT    DEFAULT '',
                reading_position  INTEGER DEFAULT 0,
                evidence_level    TEXT    DEFAULT '',
                study_design      TEXT    DEFAULT '',
                clinical_specialty TEXT   DEFAULT '',
                pico_json         TEXT    DEFAULT '{}',
                risk_of_bias_json TEXT    DEFAULT '{}',
                impact_factor     REAL    DEFAULT 0,
                citation_count    INTEGER DEFAULT 0
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
                id UNINDEXED, title, authors, abstract, keywords, full_text,
                content='papers', content_rowid='id'
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS papers_notes_fts USING fts5(
                id UNINDEXED, notes,
                content='papers', content_rowid='id'
            );

            CREATE TRIGGER IF NOT EXISTS papers_ai AFTER INSERT ON papers BEGIN
                INSERT INTO papers_fts(rowid,id,title,authors,abstract,keywords,full_text)
                VALUES (new.id,new.id,new.title,new.authors,new.abstract,new.keywords,new.full_text);
                INSERT INTO papers_notes_fts(rowid,id,notes)
                VALUES (new.id,new.id,new.notes);
            END;
            CREATE TRIGGER IF NOT EXISTS papers_ad AFTER DELETE ON papers BEGIN
                INSERT INTO papers_fts(papers_fts,rowid,id,title,authors,abstract,keywords,full_text)
                VALUES ('delete',old.id,old.id,old.title,old.authors,old.abstract,old.keywords,old.full_text);
                INSERT INTO papers_notes_fts(papers_notes_fts,rowid,id,notes)
                VALUES ('delete',old.id,old.id,old.notes);
            END;
            CREATE TRIGGER IF NOT EXISTS papers_au AFTER UPDATE ON papers BEGIN
                INSERT INTO papers_fts(papers_fts,rowid,id,title,authors,abstract,keywords,full_text)
                VALUES ('delete',old.id,old.id,old.title,old.authors,old.abstract,old.keywords,old.full_text);
                INSERT INTO papers_fts(rowid,id,title,authors,abstract,keywords,full_text)
                VALUES (new.id,new.id,new.title,new.authors,new.abstract,new.keywords,new.full_text);
                INSERT INTO papers_notes_fts(papers_notes_fts,rowid,id,notes)
                VALUES ('delete',old.id,old.id,old.notes);
                INSERT INTO papers_notes_fts(rowid,id,notes)
                VALUES (new.id,new.id,new.notes);
            END;
        """)
        _migrate(conn, [
            ("evidence_level",     "TEXT DEFAULT ''"),
            ("study_design",       "TEXT DEFAULT ''"),
            ("clinical_specialty", "TEXT DEFAULT ''"),
            ("pico_json",          "TEXT DEFAULT '{}'"),
            ("risk_of_bias_json",  "TEXT DEFAULT '{}'"),
            ("impact_factor",      "REAL DEFAULT 0"),
            ("citation_count",     "INTEGER DEFAULT 0"),
            ("reading_position",   "INTEGER DEFAULT 0"),
            ("project",            "TEXT DEFAULT ''"),
        ])


def _migrate(conn: sqlite3.Connection, columns: list[tuple[str, str]]) -> None:
    for col_name, col_def in columns:
        try:
            conn.execute(f"ALTER TABLE papers ADD COLUMN {col_name} {col_def}")
        except sqlite3.OperationalError:
            pass


_COLS = """
    p.id, p.md5, p.original_filename, p.renamed_filename,
    p.title, p.authors, p.year, p.journal, p.doi,
    p.abstract, p.keywords, p.tags, p.notes, p.highlights,
    p.status, p.starred, p.pages, p.added_at, p.file_path,
    p.project, p.reading_position,
    p.evidence_level, p.study_design, p.clinical_specialty,
    p.pico_json, p.risk_of_bias_json, p.impact_factor, p.citation_count
"""

_ORDER_MAP = {
    "Recently added":  "added_at DESC",
    "Year (newest)":   "year DESC, added_at DESC",
    "Year (oldest)":   "year ASC, added_at DESC",
    "Title A→Z":       "title ASC",
    "Authors A→Z":     "authors ASC",
    "Evidence Level":  "evidence_level ASC, added_at DESC",
    "Most pages":      "pages DESC, added_at DESC",
    "Impact Factor":   "impact_factor DESC, added_at DESC",
}


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
    sql_order = _ORDER_MAP.get(order, "added_at DESC")
    with db_conn() as conn:
        rows = conn.execute(f"SELECT {_COLS} FROM papers p ORDER BY {sql_order}").fetchall()
        return [dict(r) for r in rows]


def get_paper_by_id(paper_id: int) -> dict | None:
    with db_conn() as conn:
        row = conn.execute(
            f"SELECT {_COLS}, p.full_text FROM papers p WHERE p.id=?", (paper_id,)
        ).fetchone()
        return dict(row) if row else None


def search_papers(query: str, scope: str = "all") -> list[dict]:
    """Multi-scope FTS5 search.

    scope: "all" | "title_abstract" | "notes" | "fulltext".
    Each returned dict has ``_match_scope`` in {"content","notes","content+notes"}.
    """
    if not query.strip():
        return get_all_papers()

    q = query.strip()
    like = f"%{q}%"
    fts_q = " OR ".join(
        f'"{t}"' if " " in t else f"{t}*" for t in q.split()[:8]
    )

    results: dict[int, dict] = {}

    with db_conn() as conn:
        if scope in ("all", "title_abstract", "fulltext"):
            try:
                fts_rows = conn.execute(
                    f"SELECT {_COLS}, fts.rank FROM papers p "
                    "JOIN papers_fts fts ON p.id = fts.rowid "
                    "WHERE papers_fts MATCH ? ORDER BY fts.rank",
                    (fts_q,),
                ).fetchall()
                for r in fts_rows:
                    d = dict(r)
                    d.setdefault("_match_scope", "content")
                    results[d["id"]] = d
            except sqlite3.OperationalError:
                pass

        if scope in ("all", "notes"):
            try:
                notes_rows = conn.execute(
                    f"SELECT {_COLS} FROM papers p "
                    "JOIN papers_notes_fts nfts ON p.id = nfts.rowid "
                    "WHERE papers_notes_fts MATCH ?",
                    (fts_q,),
                ).fetchall()
                for r in notes_rows:
                    d = dict(r)
                    pid = d["id"]
                    if pid not in results:
                        d["_match_scope"] = "notes"
                        results[pid] = d
                    else:
                        results[pid]["_match_scope"] = "content+notes"
            except sqlite3.OperationalError:
                pass

        if scope in ("all", "notes"):
            like_rows = conn.execute(
                f"SELECT {_COLS} FROM papers p "
                "WHERE (notes LIKE ? OR highlights LIKE ?) "
                "ORDER BY added_at DESC",
                (like, like),
            ).fetchall()
            for r in like_rows:
                d = dict(r)
                if d["id"] not in results:
                    d["_match_scope"] = "notes"
                    results[d["id"]] = d

        if not results:
            like_rows = conn.execute(
                f"SELECT {_COLS} FROM papers p "
                "WHERE title LIKE ? OR authors LIKE ? "
                "   OR abstract LIKE ? OR keywords LIKE ? "
                "   OR notes LIKE ? OR highlights LIKE ? "
                "ORDER BY added_at DESC",
                (like, like, like, like, like, like),
            ).fetchall()
            for r in like_rows:
                d = dict(r)
                d.setdefault("_match_scope", "content")
                results[d["id"]] = d

    return list(results.values())


def insert_paper(paper: dict) -> int:
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


def delete_paper(paper_id: int) -> None:
    paper = get_paper_by_id(paper_id)
    if paper:
        fp = paper.get("file_path", "")
        if fp and os.path.exists(fp):
            try:
                os.remove(fp)
            except OSError:
                pass
    with db_conn() as conn:
        conn.execute("DELETE FROM papers WHERE id=?", (paper_id,))


def check_duplicate(md5: str, doi: str, title: str) -> dict | None:
    with db_conn() as conn:
        if md5:
            row = conn.execute("SELECT id,title,doi FROM papers WHERE md5=?", (md5,)).fetchone()
            if row:
                return dict(row)
        if doi:
            row = conn.execute("SELECT id,title,doi FROM papers WHERE doi=?", (doi,)).fetchone()
            if row:
                return dict(row)
        if title and len(title) > 15:
            t_words = set(re.sub(r'[^\w\s]', '', title.lower()).split())
            rows = conn.execute("SELECT id,title,doi FROM papers").fetchall()
            for r in rows:
                r_words = set(re.sub(r'[^\w\s]', '', (r["title"] or "").lower()).split())
                if len(t_words) > 3 and len(r_words) > 3:
                    common = len(t_words & r_words)
                    if common / max(len(t_words), len(r_words)) > 0.85:
                        return dict(r)
    return None


def get_db_stats() -> dict:
    with db_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        read_cnt = conn.execute("SELECT COUNT(*) FROM papers WHERE status='read'").fetchone()[0]
        rdng_cnt = conn.execute("SELECT COUNT(*) FROM papers WHERE status='reading'").fetchone()[0]
        star_cnt = conn.execute("SELECT COUNT(*) FROM papers WHERE starred=1").fetchone()[0]
        page_tot = conn.execute("SELECT COALESCE(SUM(pages),0) FROM papers").fetchone()[0]
        proj_cnt = conn.execute(
            "SELECT COUNT(DISTINCT project) FROM papers "
            "WHERE project IS NOT NULL AND project != ''"
        ).fetchone()[0]
        notes_cnt = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE notes IS NOT NULL AND notes != ''"
        ).fetchone()[0]

    db_sz = os.path.getsize(_kms.DB_PATH) / 1024 if os.path.exists(_kms.DB_PATH) else 0
    pdf_sz = sum(f.stat().st_size for f in _kms.STORAGE_DIR.glob("*.pdf") if f.is_file()) / (1024 * 1024)

    return {
        "total":     total,
        "read":      read_cnt,
        "reading":   rdng_cnt,
        "unread":    total - read_cnt - rdng_cnt,
        "starred":   star_cnt,
        "pages":     int(page_tot),
        "projects":  proj_cnt,
        "annotated": notes_cnt,
        "db_kb":     round(db_sz, 1),
        "pdf_mb":    round(pdf_sz, 2),
        "storage_path": str(_kms.STORAGE_DIR.resolve()),
    }


def _read_config() -> dict:
    if _kms.CONFIG_PATH.exists():
        try:
            return json.loads(_kms.CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_config(cfg: dict) -> None:
    _kms.CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_tag_dict() -> list[str]:
    return _read_config().get("custom_tag_dict") or DEFAULT_TAG_DICT


def save_tag_dict(terms: list[str]) -> None:
    cfg = _read_config()
    cfg["custom_tag_dict"] = terms
    _save_config(cfg)
