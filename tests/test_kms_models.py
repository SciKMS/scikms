import json

import pytest

from scikms.kms.repositories.models import Paper


def test_paper_default():
    paper = Paper(id=1)
    assert paper.highlights == []
    assert paper.pico == {}
    assert paper.risk_of_bias == {}
    assert paper.year is None
    assert paper.starred == 0


@pytest.fixture
def make_paper_row():
    def _make_paper_row(**overrides):
        row = {
            "id": 1,
            "md5": "abc123",
            "original_filename": "original.pdf",
            "renamed_filename": "renamed.pdf",
            "title": "Sample Paper",
            "authors": "Smith, John; Doe, Jane",
            "year": 2024,
            "journal": "NEJM",
            "doi": "10.1000/sample",
            "abstract": "A randomized controlled trial.",
            "keywords": "trial, cardiology",
            "full_text": "Full text content",
            "tags": '["trial", "cardiology"]',
            "notes": "Some notes",
            "highlights": '["highlight 1", "highlight 2"]',
            "status": "unread",
            "starred": 1,
            "pages": 12,
            "added_at": "2024-01-01",
            "file_path": "/tmp/sample.pdf",
            "project": "demo",
            "reading_position": 3,
            "evidence_level": "II",
            "study_design": "RCT",
            "clinical_specialty": "Cardiology",
            "pico_json": '{"P": "Adults", "I": "Drug A", "C": "Placebo", "O": "Mortality"}',
            "risk_of_bias_json": '{"selection": "low", "performance": "some concerns"}',
            "impact_factor": 8.5,
            "citation_count": 42,
        }
        row.update(overrides)
        return row

    return _make_paper_row


def test_from_row_invalid_highlights_json(make_paper_row):
    row = make_paper_row(highlights="not-json")
    paper = Paper.from_row(row)
    assert paper.highlights == []


def test_from_row_highlights(make_paper_row):
    row = make_paper_row(highlights='["a", "b"]')
    paper = Paper.from_row(row)
    assert paper.highlights == ["a", "b"]


def test_from_row_pico_json(make_paper_row):
    row = make_paper_row(pico_json='{"P": "Photograph", "I": "International"}')
    paper = Paper.from_row(row)
    assert paper.pico == {"P": "Photograph", "I": "International"}


def test_from_row_handles_missing_numeric_values(make_paper_row):
    row = make_paper_row(
        year=None,
        starred=None,
        pages=None,
        reading_position=None,
        impact_factor=None,
        citation_count=None,
    )
    paper = Paper.from_row(row)
    assert paper.year is None
    assert paper.starred == 0
    assert paper.pages == 0
    assert paper.reading_position == 0
    assert paper.impact_factor == 0.0
    assert paper.citation_count == 0

# Test on serialization
def test_to_db_dict_serializes_model_fields():
    paper = Paper(
        id=1,
        md5="abc123",
        original_filename="original.pdf",
        renamed_filename="renamed.pdf",
        title="Sample Paper",
        authors="Smith, John; Doe, Jane",
        year=2024,
        journal="NEJM",
        doi="10.1000/sample",
        abstract="A randomized controlled trial.",
        keywords="trial, cardiology",
        full_text="Full text content",
        tags='["trial", "cardiology"]',
        notes="Some notes",
        highlights=["highlight 1", "highlight 2"],
        status="unread",
        starred=1,
        pages=12,
        added_at="2024-01-01",
        file_path="/tmp/sample.pdf",
        project="demo",
        reading_position=3,
        evidence_level="II",
        study_design="RCT",
        clinical_specialty="Cardiology",
        pico={"P": "Adults", "I": "Drug A", "C": "Placebo", "O": "Mortality"},
        risk_of_bias={"selection": "low", "performance": "some concerns"},
        impact_factor=8.5,
        citation_count=42,
    )
    data = paper.to_dict()
    assert data["id"] == 1
    assert data["title"] == "Sample Paper"
    assert data["authors"] == "Smith, John; Doe, Jane"
    assert data["year"] == 2024
    assert data["pages"] == 12
    assert data["impact_factor"] == 8.5
    assert data["citation_count"] == 42
    # assert data["highlights"] == json.dumps(["highlight 1", "highlight 2"])
    assert data["highlights"] == '["highlight 1", "highlight 2"]'
    assert data["pico_json"] == '{"P": "Adults", "I": "Drug A", "C": "Placebo", "O": "Mortality"}'
    assert data["risk_of_bias_json"] == '{"selection": "low", "performance": "some concerns"}'
    assert "pico" not in data
    assert "risk_of_bias" not in data

def test_to_db_dict_serializes_empty_json_fields():
    paper = Paper(id=1)
    data = paper.to_dict()
    assert data["highlights"] == "[]"
    assert data["pico_json"] == "{}"
    assert data["risk_of_bias_json"] == "{}"

def test_to_db_dict_round_trip(make_paper_row):
    row = make_paper_row(
        highlights='["a", "b"]',
        pico_json='{"P": "Adults", "I": "Drug A"}',
        risk_of_bias_json='{"selection": "low"}',
    )
    paper = Paper.from_row(row)
    data = paper.to_dict()
    assert data["id"] == row["id"]
    assert data["title"] == row["title"]
    assert data["authors"] == row["authors"]
    assert data["year"] == row["year"]
    assert data["highlights"] == row["highlights"]
    assert data["pico_json"] == row["pico_json"]
    assert data["risk_of_bias_json"] == row["risk_of_bias_json"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
