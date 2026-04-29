"""Shared SQL constants for KMS repositories."""

PAPER_SELECT_COLS = """
    p.id, p.md5, p.original_filename, p.renamed_filename,
    p.title, p.authors, p.year, p.journal, p.doi,
    p.abstract, p.keywords, p.tags, p.notes, p.highlights,
    p.status, p.starred, p.pages, p.added_at, p.file_path,
    p.project, p.reading_position,
    p.evidence_level, p.study_design, p.clinical_specialty,
    p.pico_json, p.risk_of_bias_json, p.impact_factor, p.citation_count
"""

PAPER_ORDER_MAP = {
    "Recently added": "added_at DESC",
    "Year (newest)": "year DESC, added_at DESC",
    "Year (oldest)": "year ASC, added_at DESC",
    "Title A→Z": "title ASC",
    "Authors A→Z": "authors ASC",
    "Evidence Level": "evidence_level ASC, added_at DESC",
    "Most pages": "pages DESC, added_at DESC",
    "Impact Factor": "impact_factor DESC, added_at DESC",
}
