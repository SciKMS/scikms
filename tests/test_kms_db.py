"""Tests for scikms.kms.db schema, CRUD, FTS5 search.

Each test gets its own data root via tmp_path + ``set_data_root``.
"""

import uuid
from typing import Any

import pytest

from scikms.kms.db import db_conn
from scikms.kms.repositories.models import Paper, PaperDuplicateRef


def _sample_paper(
    md5: str | None = None, title="Title", abstract="A meta-analysis of heart disease"
) -> dict[str, Any]:
    return {
        "md5": md5 if md5 else uuid.uuid4().hex[:12],
        "original_filename": "x.pdf",
        "renamed_filename": "x.pdf",
        "title": title,
        "authors": "Smith, John",
        "year": 2024,
        "journal": "NEJM",
        "doi": "10.1/x",
        "abstract": abstract,
        "keywords": "",
        "full_text": abstract,
        "tags": "[]",
        "notes": "",
        "highlights": "[]",
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


# We are isolating the database creation from the autouse
def test_init_db_idempotent(tmp_path):
    from scikms import kms
    from scikms.kms.db import init_db

    kms.set_data_root(tmp_path)

    init_db()
    # We need this to test does it override or duplicate after
    # the initializing the database
    init_db()

    with db_conn() as conn:
        tables = conn.execute(
            "SELECT name from SQLITE_MASTER where type='table'"
        ).fetchall()

    names = {r["name"] for r in tables}
    assert "papers" in names
    assert "papers_fts" in names
    assert "papers_notes_fts" in names


# We inject the kms_db from the conftest.py to all the operations here
def test_insert_and_get_paper(kms_db):  # pytest will run the kms_db first
    from scikms.kms.db import get_paper_by_id, insert_paper

    pid = insert_paper(_sample_paper())
    paper = get_paper_by_id(pid)

    assert isinstance(paper, Paper)
    assert paper is not None
    assert paper.title == "Title"
    assert paper.status == "unread"


def test_get_all_papers_returns_paper_models(kms_db):
    from scikms.kms.db import get_all_papers, insert_paper

    insert_paper(_sample_paper(title="First"))
    insert_paper(_sample_paper(title="Second"))

    papers = get_all_papers()
    assert len(papers) == 2
    assert all(isinstance(p, Paper) for p in papers)
    assert {p.title for p in papers} == {"First", "Second"}


def test_update_and_delete_paper(kms_db):
    from scikms.kms.db import (delete_paper, get_paper_by_id, insert_paper,
                               update_paper)

    pid = insert_paper(_sample_paper())
    update_paper(pid, {"status": "read", "starred": 1})

    paper = get_paper_by_id(pid)
    assert paper is not None
    assert paper.status == "read"
    assert paper.starred == 1

    delete_paper(pid)
    assert get_paper_by_id(pid) is None

def test_check_duplicate_by_md5_returns_duplicate_ref(kms_db):
    from scikms.kms.db import check_duplicate, insert_paper

    insert_paper(_sample_paper(md5="dupkey"))
    dup = check_duplicate("dupkey", "", "")

    assert dup is not None
    assert isinstance(dup, PaperDuplicateRef)
    assert dup.title == "Title"
    assert dup.doi == "10.1/x"

def test_find_duplicate_by_md5_returns_duplicate_ref(kms_db):
    from scikms.kms.db import insert_paper
    from scikms.kms.repositories.papers import find_duplicate_by_md5

    insert_paper(_sample_paper(md5="dupkey"))
    dup = find_duplicate_by_md5("dupkey")

    assert dup is not None
    assert isinstance(dup, PaperDuplicateRef)
    assert dup.id >= 1
    assert dup.title == "Title"
    assert dup.doi == "10.1/x"


def test_insert_paper_accepts_paper_model(kms_db):
    from scikms.kms.db import get_paper_by_id, insert_paper
    from scikms.kms.repositories.models import Paper
    paper = Paper(
        id=0,
        md5="paper-model",
        original_filename="x.pdf",
        renamed_filename="x.pdf",
        title="Model Insert",
        authors="Smith, John",
        year=2024,
        journal="NEJM",
        doi="10.1/model",
        abstract="A meta-analysis of heart disease",
        keywords="",
        full_text="A meta-analysis of heart disease",
        tags="[]",
        notes="",
        status="unread",
        starred=0,
        pages=10,
        added_at="2024-01-01",
        file_path="",
        project="",
        reading_position=0,
        evidence_level="I",
        study_design="Meta-analysis",
        clinical_specialty="Cardiology",
        impact_factor=0.0,
        citation_count=0,
    )
    pid = insert_paper(paper)
    stored = get_paper_by_id(pid)
    assert stored is not None
    assert stored.title == "Model Insert"
    assert stored.doi == "10.1/model"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
