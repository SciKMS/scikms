"""Search service preserving current multi-scope search behavior."""

from __future__ import annotations

from scikms.kms.repositories.papers import get_all_papers
from scikms.kms.repositories.search import (
    search_basic_like,
    search_content_fts,
    search_notes_fts,
    search_notes_like,
)


def search_papers(query: str, scope: str = "all") -> list[dict]:
    """Multi-scope FTS5 search.

    scope: "all" | "title_abstract" | "notes" | "fulltext".
    Each returned dict has ``_match_scope`` in {"content","notes","content+notes"}.
    """
    if not query.strip():
        return get_all_papers()

    q = query.strip()
    like = f"%{q}%"
    fts_q = " OR ".join(f'"{t}"' if " " in t else f"{t}*" for t in q.split()[:8])

    results: dict[int, dict] = {}

    if scope in ("all", "title_abstract", "fulltext"):
        for row in search_content_fts(fts_q):
            row.setdefault("_match_scope", "content")
            results[row["id"]] = row

    if scope in ("all", "notes"):
        for row in search_notes_fts(fts_q):
            pid = row["id"]
            if pid not in results:
                row["_match_scope"] = "notes"
                results[pid] = row
            else:
                results[pid]["_match_scope"] = "content+notes"

    if scope in ("all", "notes"):
        for row in search_notes_like(like):
            if row["id"] not in results:
                row["_match_scope"] = "notes"
                results[row["id"]] = row

    if not results:
        for row in search_basic_like(like):
            row.setdefault("_match_scope", "content")
            results[row["id"]] = row

    return list(results.values())
