"""Tests for scikms.kms.services.search.search_papers.

Each test gets its own data root via tmp_path + ``set_data_root``.
"""

from __future__ import annotations

import uuid

import pytest

from scikms.kms.repositories.models import PaperSearchResult

_counter = 0


def _next_id() -> int:
    global _counter
    _counter += 1
    return _counter


def _sample_paper(
    *,
    md5: str | None = None,
    title: str = "Heart Disease Meta-Analysis",
    abstract: str = "A systematic review of cardiovascular outcomes",
    notes: str = "",
    highlights: str = "[]",
    keywords: str = "cardiology, meta-analysis",
    full_text: str = "Full text content about heart disease",
    **overrides,
) -> dict:
    global _counter
    row = {
        "id": _next_id(),
        "md5": md5 if md5 else f"{uuid.uuid4().hex[:12]}_{_counter}",
        "original_filename": "x.pdf",
        "renamed_filename": "x.pdf",
        "title": title,
        "authors": "Smith, John",
        "year": 2024,
        "journal": "NEJM",
        "doi": "10.1/x",
        "abstract": abstract,
        "keywords": keywords,
        "full_text": full_text,
        "tags": "[]",
        "notes": notes,
        "highlights": highlights,
        "status": "unread",
        "starred": 0,
        "pages": 10,
        "added_at": "2024-01-01",
        "file_path": "",
        "project": "",
        "reading_position": 0,
        "evidence_level": "I",
        "study_design": "Meta-analysis",
        "clinical_specialty": "Cardiology",
        "pico_json": "{}",
        "risk_of_bias_json": "{}",
        "impact_factor": 0.0,
        "citation_count": 0,
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# Empty query
# ---------------------------------------------------------------------------

def test_empty_query_returns_all_papers_default_scope(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    pid1 = insert_paper(_sample_paper(title="Paper Alpha"))
    pid2 = insert_paper(_sample_paper(title="Paper Beta"))
    results = search_papers("")

    assert len(results) == 2
    assert all(isinstance(r, PaperSearchResult) for r in results)
    assert all(r.match_scope == "default" for r in results)
    assert {r.paper.id for r in results} == {pid1, pid2}


def test_whitespace_query_returns_all_papers_default_scope(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    insert_paper(_sample_paper(title="Paper Alpha"))
    results = search_papers("   ")

    assert len(results) == 1
    assert results[0].match_scope == "default"


# ---------------------------------------------------------------------------
# Content scope matches (title_abstract / fulltext / all)
# ---------------------------------------------------------------------------

def test_title_match_returns_content_scope(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    pid = insert_paper(_sample_paper(title="Hypertension Guidelines"))
    results = search_papers("hypertension", scope="title_abstract")

    assert len(results) == 1
    assert results[0].paper.id == pid
    assert results[0].match_scope == "content"


def test_abstract_match_returns_content_scope(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    pid = insert_paper(_sample_paper(
        title="Generic Title",
        abstract="Atrial fibrillation increases stroke risk",
    ))
    results = search_papers("fibrillation", scope="fulltext")

    assert len(results) == 1
    assert results[0].paper.id == pid
    assert results[0].match_scope == "content"


def test_fulltext_match_returns_content_scope(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    pid = insert_paper(_sample_paper(
        title="Generic Title",
        full_text="BRCA1 mutation analysis in breast cancer",
    ))
    results = search_papers("BRCA1", scope="fulltext")

    assert len(results) == 1
    assert results[0].paper.id == pid
    assert results[0].match_scope == "content"


def test_keywords_match_returns_content_scope(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    pid = insert_paper(_sample_paper(
        title="Generic Title",
        keywords="immunotherapy, oncology",
    ))
    results = search_papers("immunotherapy", scope="title_abstract")

    assert len(results) == 1
    assert results[0].paper.id == pid
    assert results[0].match_scope == "content"


# ---------------------------------------------------------------------------
# Notes scope matches
# ---------------------------------------------------------------------------

def test_notes_match_returns_notes_scope(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    pid = insert_paper(_sample_paper(notes="Patient follow up at twelve months"))
    results = search_papers("follow", scope="notes")

    assert len(results) == 1
    assert results[0].paper.id == pid
    assert results[0].match_scope == "notes"


def test_highlights_match_via_notes_fallback(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    pid = insert_paper(_sample_paper(highlights='["Important LDL reduction"]'))
    results = search_papers("LDL", scope="notes")

    assert len(results) == 1
    assert results[0].paper.id == pid
    assert results[0].match_scope == "notes"


# ---------------------------------------------------------------------------
# Notes + content merge (content+notes scope)
# ---------------------------------------------------------------------------

def test_paper_matching_both_content_and_notes_gets_merged_scope(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    pid = insert_paper(_sample_paper(
        title="Dosing Guidelines",
        notes="Important note about dosing",
    ))
    results = search_papers("dosing", scope="all")

    matching = [r for r in results if r.paper.id == pid]
    assert len(matching) == 1
    assert matching[0].match_scope == "content+notes"


def test_paper_matching_content_and_highlights_gets_merged_scope(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    pid = insert_paper(_sample_paper(
        title="Regression Guidelines",
        highlights='["Regression result was clinically important"]',
    ))
    results = search_papers("regression", scope="all")

    assert len(results) == 1
    assert results[0].paper.id == pid
    assert results[0].match_scope == "content+notes"


def test_different_papers_returned_separately(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    pid_content = insert_paper(_sample_paper(
        title="Dosing Guidelines",
        notes="Something else",
    ))
    pid_notes = insert_paper(_sample_paper(
        title="Unrelated Title",
        notes="Important note about dosing",
    ))
    results = search_papers("dosing", scope="all")

    assert len(results) == 2
    ids = {r.paper.id for r in results}
    assert ids == {pid_content, pid_notes}


# ---------------------------------------------------------------------------
# Scope semantics — notes scope should NOT fall back to title/abstract
# ---------------------------------------------------------------------------

def test_notes_scope_does_not_return_title_only_match(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    insert_paper(_sample_paper(title="Caffeine Study"))
    results = search_papers("caffeine", scope="notes")

    assert len(results) == 0


def test_notes_scope_does_not_return_abstract_only_match(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    insert_paper(_sample_paper(abstract="Effects of caffeine on sleep"))
    results = search_papers("caffeine", scope="notes")

    assert len(results) == 0


# ---------------------------------------------------------------------------
# Fallback behavior
# ---------------------------------------------------------------------------

def test_content_scope_does_not_trigger_basic_like_fallback(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    insert_paper(_sample_paper(
        title="Some title",
        abstract="Some abstract",
        notes="",
    ))
    results = search_papers("nonexistenttermxyz", scope="title_abstract")

    assert len(results) == 0


def test_notes_scope_does_not_trigger_basic_like_fallback(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    insert_paper(_sample_paper(notes="Some notes"))
    results = search_papers("nonexistenttermxyz", scope="notes")

    assert len(results) == 0


def test_broad_fallback_only_for_all_scope(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    pid = insert_paper(_sample_paper(
        title="AlphaBetaCase Report",
        abstract="No tokenized fallback term here",
        notes="",
        full_text="",
    ))

    assert search_papers("betacase", scope="title_abstract") == []
    assert search_papers("betacase", scope="fulltext") == []
    assert search_papers("betacase", scope="notes") == []

    results = search_papers("betacase", scope="all")
    assert len(results) == 1
    assert results[0].paper.id == pid
    assert results[0].match_scope == "content"


# ---------------------------------------------------------------------------
# Empty database
# ---------------------------------------------------------------------------

def test_empty_database_returns_empty_list(kms_db):
    from scikms.kms.services.search import search_papers

    results = search_papers("anything")
    assert results == []


def test_empty_database_empty_query_returns_empty(kms_db):
    from scikms.kms.services.search import search_papers

    results = search_papers("")
    assert results == []


# ---------------------------------------------------------------------------
# Returns PaperSearchResult instances
# ---------------------------------------------------------------------------

def test_results_are_paper_search_result_instances(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    insert_paper(_sample_paper(title="Specific Title"))
    results = search_papers("specific", scope="all")

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, PaperSearchResult)
    assert result.paper.title == "Specific Title"
    assert result.match_scope in {"content", "notes", "content+notes"}


def test_no_duplicate_results_after_merge(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    pid = insert_paper(_sample_paper(
        title="Dosing Guidelines",
        notes="More about dosing",
    ))
    results = search_papers("dosing", scope="all")

    ids = [r.paper.id for r in results]
    assert ids.count(pid) == 1


# ---------------------------------------------------------------------------
# Multi-word query
# ---------------------------------------------------------------------------

def test_multi_word_query_fts_handling(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.services.search import search_papers

    pid = insert_paper(_sample_paper(
        title="Randomized Trial of Hypertension",
        abstract="A randomized controlled trial for hypertension",
    ))
    results = search_papers("randomized trial", scope="title_abstract")

    assert len(results) >= 1
    assert any(r.paper.id == pid for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
