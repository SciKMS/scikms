"""Tests for scikms.kms.db schema, CRUD, FTS5 search.

Each test gets its own data root via tmp_path + ``set_data_root``.
"""

import pytest
import uuid

from scikms.kms.db import db_conn


def _sample_paper(
    md5: str | None = None, title="Title", abstract="A meta-analysis of heart disease"
):
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
    from scikms.kms.db import insert_paper, get_paper_by_id, get_papers_count

    sample_paper = _sample_paper()
    pid = insert_paper(sample_paper)

    assert pid >= 1
    p = get_paper_by_id(pid)

    # The test fails if it returns to None
    assert p["title"] == "Title"
    assert get_papers_count() == 1


def test_search_papers_fts_match(kms_db):
    from scikms.kms.db import insert_paper, search_papers

    heart_study = _sample_paper(
        md5=None, title="Heart study", abstract="meta-analysis of heart"
    )
    lung_study = _sample_paper(
        md5=None, title="Lung study", abstract="cohort study lung cancer"
    )
    insert_paper(heart_study)
    insert_paper(lung_study)

    res = search_papers("heart")
    assert any("Heart" in r["title"] for r in res)


def test_search_papers_returns_all_on_empty_query(kms_db):
    from scikms.kms.db import insert_paper, search_papers

    insert_paper(_sample_paper())
    assert len(search_papers("")) == 1


def test_check_duplicate_by_md5(kms_db):
    from scikms.kms.db import insert_paper, check_duplicate

    insert_paper(_sample_paper(md5="dupkey"))
    dup = check_duplicate("dupkey", "", "")
    assert dup is not None
    assert dup["title"] == "Title"


def test_update_and_delete_paper(kms_db):
    from scikms.kms.db import insert_paper, update_paper, delete_paper, get_paper_by_id

    pid = insert_paper(_sample_paper())
    update_paper(pid, {"status": "read", "starred": 1})
    p = get_paper_by_id(pid)

    assert p["status"] == "read"
    assert p["starred"] == 1

    delete_paper(pid)
    assert get_paper_by_id(pid) is None


def test_get_db_stats_keys(kms_db):
    from scikms.kms.db import insert_paper, get_db_stats

    insert_paper(_sample_paper())
    stats = get_db_stats()
    for key in (
        "total",
        "read",
        "reading",
        "unread",
        "starred",
        "pages",
        "projects",
        "annotated",
        "db_kb",
        "pdf_mb",
        "storage_path",
    ):
        assert key in stats


def test_tag_dict_save_and_load(kms_db):
    from scikms.kms.db import save_tag_dict, get_tag_dict

    save_tag_dict(["tag1", "tag2"])
    tags = get_tag_dict()
    assert "tag1" in tags
