"""Stats repository queries."""

from __future__ import annotations

from scikms.kms.db.connection import db_conn


def get_library_stats() -> dict:
    with db_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        read_cnt = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE status='read'"
        ).fetchone()[0]
        rdng_cnt = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE status='reading'"
        ).fetchone()[0]
        star_cnt = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE starred=1"
        ).fetchone()[0]
        page_tot = conn.execute("SELECT COALESCE(SUM(pages),0) FROM papers").fetchone()[
            0
        ]
        proj_cnt = conn.execute(
            "SELECT COUNT(DISTINCT project) FROM papers "
            "WHERE project IS NOT NULL AND project != ''"
        ).fetchone()[0]
        notes_cnt = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE notes IS NOT NULL AND notes != ''"
        ).fetchone()[0]

    return {
        "total": total,
        "read": read_cnt,
        "reading": rdng_cnt,
        "unread": total - read_cnt - rdng_cnt,
        "starred": star_cnt,
        "pages": int(page_tot),
        "projects": proj_cnt,
        "annotated": notes_cnt,
    }
