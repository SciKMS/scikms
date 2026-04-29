"""SQLite schema creation and migrations for KMS."""

from __future__ import annotations

import sqlite3

from .connection import db_conn


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
                INSERT INTO papers_fts(
                    rowid,id,title,authors,abstract,keywords,full_text
                )
                VALUES (
                    new.id,new.id,new.title,new.authors,new.abstract,
                    new.keywords,new.full_text
                );
                INSERT INTO papers_notes_fts(rowid,id,notes)
                VALUES (new.id,new.id,new.notes);
            END;
            CREATE TRIGGER IF NOT EXISTS papers_ad AFTER DELETE ON papers BEGIN
                INSERT INTO papers_fts(
                    papers_fts,rowid,id,title,authors,abstract,keywords,full_text
                )
                VALUES (
                    'delete',old.id,old.id,old.title,old.authors,
                    old.abstract,old.keywords,old.full_text
                );
                INSERT INTO papers_notes_fts(papers_notes_fts,rowid,id,notes)
                VALUES ('delete',old.id,old.id,old.notes);
            END;
            CREATE TRIGGER IF NOT EXISTS papers_au AFTER UPDATE ON papers BEGIN
                INSERT INTO papers_fts(
                    papers_fts,rowid,id,title,authors,abstract,keywords,full_text
                )
                VALUES (
                    'delete',old.id,old.id,old.title,old.authors,
                    old.abstract,old.keywords,old.full_text
                );
                INSERT INTO papers_fts(
                    rowid,id,title,authors,abstract,keywords,full_text
                )
                VALUES (
                    new.id,new.id,new.title,new.authors,new.abstract,
                    new.keywords,new.full_text
                );
                INSERT INTO papers_notes_fts(papers_notes_fts,rowid,id,notes)
                VALUES ('delete',old.id,old.id,old.notes);
                INSERT INTO papers_notes_fts(rowid,id,notes)
                VALUES (new.id,new.id,new.notes);
            END;
        """)
        _migrate(
            conn,
            [
                ("evidence_level", "TEXT DEFAULT ''"),
                ("study_design", "TEXT DEFAULT ''"),
                ("clinical_specialty", "TEXT DEFAULT ''"),
                ("pico_json", "TEXT DEFAULT '{}'"),
                ("risk_of_bias_json", "TEXT DEFAULT '{}'"),
                ("impact_factor", "REAL DEFAULT 0"),
                ("citation_count", "INTEGER DEFAULT 0"),
                ("reading_position", "INTEGER DEFAULT 0"),
                ("project", "TEXT DEFAULT ''"),
            ],
        )


def _migrate(conn: sqlite3.Connection, columns: list[tuple[str, str]]) -> None:
    for col_name, col_def in columns:
        try:
            conn.execute(f"ALTER TABLE papers ADD COLUMN {col_name} {col_def}")
        except sqlite3.OperationalError:
            pass
