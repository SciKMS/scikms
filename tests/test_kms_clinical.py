"""Tests for scikms.kms.clinical pure functions."""

from scikms.kms.clinical import (
    build_renamed_filename, classify_all, detect_clinical_specialty,
    detect_evidence_level, detect_study_design, export_bib, export_ris,
    generate_citation, parse_pico_from_abstract, slugify,
)


def test_detect_evidence_level_meta_analysis():
    assert detect_evidence_level("This is a systematic review and meta-analysis of...") == "I"


def test_detect_evidence_level_rct():
    assert detect_evidence_level("A double-blind placebo-controlled randomized controlled trial") == "II"


def test_detect_evidence_level_empty():
    assert detect_evidence_level("") == ""
    assert detect_evidence_level("nothing here") == ""


def test_detect_study_design_priority_meta_over_rct():
    text = "We conducted a randomized controlled trial. Meta-analysis was performed."
    assert detect_study_design(text) == "Meta-analysis"


def test_detect_clinical_specialty():
    assert detect_clinical_specialty("Coronary heart disease patients with hypertension") == "Cardiology"
    assert detect_clinical_specialty("Treatment of carcinoma using chemotherapy") == "Oncology"


def test_classify_all_returns_triple():
    ev, sd, sp = classify_all("randomized controlled trial in heart failure patients")
    assert ev == "II"
    assert sd == "RCT"
    assert sp == "Cardiology"


def test_parse_pico_from_abstract():
    abstract = (
        "Patients with heart failure were randomized to drug X or placebo. "
        "Primary outcome was mortality at 12 months."
    )
    pico = parse_pico_from_abstract(abstract)
    assert "P" in pico
    assert "I" in pico or "C" in pico
    assert "O" in pico


def test_generate_citation_vancouver():
    paper = {"authors": "Smith, John; Doe, Jane", "title": "A study", "journal": "NEJM",
             "year": 2024, "doi": "10.1/abc"}
    cit = generate_citation(paper, "vancouver")
    assert "Smith J" in cit
    assert "A study" in cit
    assert "doi:10.1/abc" in cit


def test_generate_citation_apa():
    paper = {"authors": "Smith, John", "title": "Study", "journal": "Lancet", "year": 2024}
    assert "(2024)" in generate_citation(paper, "apa")


def test_export_ris_smoke():
    out = export_ris([{"title": "T", "authors": "A, B", "year": 2024, "journal": "J", "doi": "10.1"}])
    assert "TY  - JOUR" in out
    assert "TI  - T" in out


def test_export_bib_smoke():
    out = export_bib([{"title": "T", "authors": "Foo, Bar", "year": 2024, "journal": "J"}])
    assert "@article{" in out


def test_slugify_handles_diacritics():
    assert "_" in slugify("Hello World - Test")
    assert "Vit" in slugify("Việt") or "Vi" in slugify("Việt")


def test_build_renamed_filename_pattern():
    paper = {"year": 2024, "authors": "Smith, John; Doe, Jane", "title": "A new study"}
    fn = build_renamed_filename(paper)
    assert fn.startswith("[2024]")
    assert fn.endswith(".pdf")
