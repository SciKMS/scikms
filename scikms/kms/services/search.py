"""Search service preserving current multi-scope search behavior."""

from __future__ import annotations

from typing import Literal

from scikms.kms.repositories.models import Paper, PaperSearchResult
from scikms.kms.repositories.papers import get_all_papers
from scikms.kms.repositories.search import (search_basic_like,
                                            search_content_fts,
                                            search_notes_fts,
                                            search_notes_like)

SearchScope = Literal["all", "title_abstract", "notes", "fulltext"]


def _merge_results(
    results: dict[int, PaperSearchResult],
    rows: list[Paper],
    match_scope: str,
) -> None:
    for paper in rows:
        if paper.id not in results:
            results[paper.id] = PaperSearchResult(paper=paper, match_scope=match_scope)
        else:
            results[paper.id].add_scope(match_scope)


def search_papers(query: str, scope: SearchScope = "all") -> list[PaperSearchResult]:
    """Multi-scope FTS5 search.

    scope: "all" | "title_abstract" | "notes" | "fulltext".
    Each returned result has ``match_scope`` in
    {"default", "content", "notes", "content+notes"}.
    """
    if not query.strip():
        all_papers = get_all_papers()
        return [PaperSearchResult(paper=paper, match_scope="default") for paper in all_papers]

    q = query.strip()
    like = f"%{q}%"
    fts_q = " OR ".join(f'"{t}"' if " " in t else f"{t}*" for t in q.split()[:8])

    results: dict[int, PaperSearchResult] = {}

    if scope in ("all", "title_abstract", "fulltext"):
        _merge_results(results, search_content_fts(fts_q), "content")

    if scope in ("all", "notes"):
        _merge_results(results, search_notes_fts(fts_q), "notes")
        _merge_results(results, search_notes_like(like), "notes")

    # Fallback — only for broad "all" scope when FTS returned nothing
    if not results and scope == "all":
        _merge_results(results, search_basic_like(like), "content")

    return list(results.values())
