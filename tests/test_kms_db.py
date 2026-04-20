"""Tests for scikms.kms.db schema, CRUD, FTS5 search.

Each test gets its own data root via tmp_path + ``set_data_root``.
"""

import pytest

from scikms import kms


@pytest.fixture(autouse=True)
def _isolated_data_root(tmp_path):
    kms.set_data_root(tmp_path)
    from scikms.kms.db import init_db
    init_db()
    yield


def _sample_paper(md5="abc", title="Title", abstract="A meta-analysis of heart disease"):
    return {
        "md5": md5,
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


def test_init_db_idempotent():
    from scikms.kms.db import init_db
    init_db()
    init_db()  # second call must not fail


def test_insert_and_get_paper():
    from scikms.kms.db import insert_paper, get_paper_by_id, get_papers_count
    pid = insert_paper(_sample_paper())
    assert pid >= 1
    p = get_paper_by_id(pid)
    assert p["title"] == "Title"
    assert get_papers_count() == 1


def test_search_papers_fts_match():
    from scikms.kms.db import insert_paper, search_papers
    insert_paper(_sample_paper(md5="m1", title="Heart study", abstract="meta-analysis of heart"))
    insert_paper(_sample_paper(md5="m2", title="Lung study", abstract="cohort study lung cancer"))
    res = search_papers("heart")
    assert any("Heart" in r["title"] for r in res)


def test_search_papers_returns_all_on_empty_query():
    from scikms.kms.db import insert_paper, search_papers
    insert_paper(_sample_paper())
    assert len(search_papers("")) == 1


def test_check_duplicate_by_md5():
    from scikms.kms.db import insert_paper, check_duplicate
    insert_paper(_sample_paper(md5="dupkey"))
    dup = check_duplicate("dupkey", "", "")
    assert dup is not None
    assert dup["title"] == "Title"


def test_update_and_delete_paper():
    from scikms.kms.db import insert_paper, update_paper, delete_paper, get_paper_by_id
    pid = insert_paper(_sample_paper())
    update_paper(pid, {"status": "read", "starred": 1})
    p = get_paper_by_id(pid)
    assert p["status"] == "read"
    assert p["starred"] == 1
    delete_paper(pid)
    assert get_paper_by_id(pid) is None


def test_get_db_stats_keys():
    from scikms.kms.db import insert_paper, get_db_stats
    insert_paper(_sample_paper())
    stats = get_db_stats()
    for key in ("total", "read", "reading", "unread", "starred", "pages",
                "projects", "annotated", "db_kb", "pdf_mb", "storage_path"):
        assert key in stats


def test_tag_dict_save_and_load():
    from scikms.kms.db import save_tag_dict, get_tag_dict
    save_tag_dict(["tag1", "tag2"])
    tags = get_tag_dict()
    assert "tag1" in tags
