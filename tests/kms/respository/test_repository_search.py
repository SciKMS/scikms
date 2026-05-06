"""Tests for scikms.kms.repositories.search query functions.

Each test gets its own data root via tmp_path + ``set_data_root``.
"""

from __future__ import annotations

import uuid

import pytest

from scikms.kms.repositories.models import Paper
from scikms.kms.repositories.search import (search_basic_like,
                                            search_content_fts,
                                            search_notes_fts,
                                            search_notes_like)

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
# search_content_fts
# ---------------------------------------------------------------------------

def test_search_content_fts_returns_paper_models(kms_db):
    from scikms.kms.db import insert_paper

    pid = insert_paper(_sample_paper(title="Randomized Trial of Hypertension"))
    results = search_content_fts("hypertension")

    assert len(results) == 1
    assert isinstance(results[0], Paper)
    assert results[0].id == pid
    assert results[0].title == "Randomized Trial of Hypertension"


def test_search_content_fts_returns_empty_for_no_match(kms_db):
    from scikms.kms.db import insert_paper

    insert_paper(_sample_paper(title="Diabetes Study"))
    results = search_content_fts("nonexistentqueryxyz")

    assert results == []


def test_search_content_fts_searches_abstract(kms_db):
    from scikms.kms.db import insert_paper

    pid = insert_paper(_sample_paper(
        title="No Match Here",
        abstract="Atrial fibrillation increases stroke risk",
    ))
    results = search_content_fts("fibrillation")

    assert len(results) == 1
    assert results[0].id == pid


def test_search_content_fts_searches_keywords(kms_db):
    from scikms.kms.db import insert_paper

    pid = insert_paper(_sample_paper(
        title="Generic Title",
        keywords=" oncology, immunotherapy",
    ))
    results = search_content_fts("immunotherapy")

    assert len(results) == 1
    assert results[0].id == pid


def test_search_content_fts_searches_full_text(kms_db):
    from scikms.kms.db import insert_paper

    pid = insert_paper(_sample_paper(
        title="Generic Title",
        full_text="This article discusses BRCA1 mutations",
    ))
    results = search_content_fts("BRCA1")

    assert len(results) == 1
    assert results[0].id == pid


def test_search_content_fts_malformed_query_returns_empty(kms_db):
    from scikms.kms.db import insert_paper

    insert_paper(_sample_paper(title="Some Title"))
    results = search_content_fts('"unbalanced quote')

    assert results == []


def test_search_content_fts_empty_query_returns_empty(kms_db):
    from scikms.kms.db import insert_paper

    insert_paper(_sample_paper(title="Some Title"))
    results = search_content_fts("")

    assert results == []


# ---------------------------------------------------------------------------
# search_notes_fts
# ---------------------------------------------------------------------------

def test_search_notes_fts_returns_paper_models(kms_db):
    from scikms.kms.db import insert_paper

    pid = insert_paper(_sample_paper(notes="Patient follow up at twelve months"))
    results = search_notes_fts("follow")

    assert len(results) == 1
    assert isinstance(results[0], Paper)
    assert results[0].id == pid
    assert results[0].notes == "Patient follow up at twelve months"


def test_search_notes_fts_returns_empty_for_no_match(kms_db):
    from scikms.kms.db import insert_paper

    insert_paper(_sample_paper(notes="Some notes"))
    results = search_notes_fts("nonexistenttermxyz")

    assert results == []


def test_search_notes_fts_malformed_query_returns_empty(kms_db):
    from scikms.kms.db import insert_paper

    insert_paper(_sample_paper(notes="Some notes"))
    results = search_notes_fts('"unbalanced quote')

    assert results == []


# ---------------------------------------------------------------------------
# search_notes_like
# ---------------------------------------------------------------------------

def test_search_notes_like_returns_paper_models(kms_db):
    from scikms.kms.db import insert_paper

    pid = insert_paper(_sample_paper(notes="Long-term outcome analysis"))
    results = search_notes_like("%outcome%")

    assert len(results) == 1
    assert isinstance(results[0], Paper)
    assert results[0].id == pid


def test_search_notes_like_searches_notes_and_highlights(kms_db):
    from scikms.kms.db import insert_paper

    pid = insert_paper(_sample_paper(
        notes="Discussed limitation of sample size",
        highlights='["Key finding: dose dependent"]',
    ))
    results = search_notes_like("%sample%")
    assert len(results) == 1
    assert results[0].id == pid


def test_search_notes_like_returns_empty_for_no_match(kms_db):
    from scikms.kms.db import insert_paper

    insert_paper(_sample_paper(notes="Some notes"))
    results = search_notes_like("%nonexistentxyz%")

    assert results == []


# ---------------------------------------------------------------------------
# search_basic_like
# ---------------------------------------------------------------------------

def test_search_basic_like_searches_title(kms_db):
    from scikms.kms.db import insert_paper

    pid = insert_paper(_sample_paper(title="Parkinson Disease Review"))
    results = search_basic_like("%Parkinson%")

    assert len(results) == 1
    assert isinstance(results[0], Paper)
    assert results[0].id == pid


def test_search_basic_like_searches_abstract(kms_db):
    from scikms.kms.db import insert_paper

    pid = insert_paper(_sample_paper(abstract="Effects of caffeine on sleep"))
    results = search_basic_like("%caffeine%")

    assert len(results) == 1
    assert results[0].id == pid


def test_search_basic_like_searches_notes(kms_db):
    from scikms.kms.db import insert_paper

    pid = insert_paper(_sample_paper(notes="Discussed limitation of sample size"))
    results = search_basic_like("%sample size%")

    assert len(results) == 1
    assert results[0].id == pid


def test_search_basic_like_searches_highlights(kms_db):
    from scikms.kms.db import insert_paper

    pid = insert_paper(_sample_paper(highlights='["Important: dose-dependent effect"]'))
    results = search_basic_like("%dose-dependent%")

    assert len(results) == 1
    assert results[0].id == pid


def test_search_basic_like_returns_empty_for_no_match(kms_db):
    from scikms.kms.db import insert_paper

    insert_paper(_sample_paper(title="Some paper"))
    results = search_basic_like("%nonexistentxyz%")

    assert results == []


def test_search_basic_like_matches_multiple_fields(kms_db):
    from scikms.kms.db import insert_paper

    pid1 = insert_paper(_sample_paper(title="Caffeine Study"))
    pid2 = insert_paper(_sample_paper(abstract="Caffeine consumption in elderly"))
    results = search_basic_like("%Caffeine%")

    assert len(results) == 2
    assert {r.id for r in results} == {pid1, pid2}


# ---------------------------------------------------------------------------
# Mixed / edge cases
# ---------------------------------------------------------------------------

def test_search_content_fts_and_notes_are_independent(kms_db):
    from scikms.kms.db import insert_paper

    pid_note = insert_paper(_sample_paper(
        title="Unrelated Title",
        notes="Important note about dosing",
    ))
    pid_content = insert_paper(_sample_paper(
        title="Dosing Guidelines",
        abstract="Maximum recommended dosing",
    ))

    fts_results = search_content_fts("dosing")
    assert len(fts_results) == 1
    assert fts_results[0].id == pid_content

    notes_results = search_notes_fts("dosing")
    assert len(notes_results) == 1
    assert notes_results[0].id == pid_note


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
