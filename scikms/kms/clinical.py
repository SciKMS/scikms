"""scikms.kms.clinical — clinical intelligence (EBM, PICO, citations, tags).

Pure functions. No UI, no persistence (except reading the user tag dict for
:func:`auto_tag`). Port of y-khoa/modules/models.py.
"""

from __future__ import annotations

import re
import unicodedata

from scikms.kms.config import (
    EVIDENCE_LEVEL_KEYWORDS,
    STUDY_DESIGN_KEYWORDS,
    SPECIALTY_KEYWORDS,
)
from scikms.kms.db import get_tag_dict


def detect_evidence_level(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    for level in ["I", "II", "III", "IV", "V"]:
        for kw in EVIDENCE_LEVEL_KEYWORDS.get(level, []):
            if kw in t:
                return level
    return ""


def detect_study_design(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    priority = [
        "Meta-analysis", "Systematic Review", "RCT", "Prospective Cohort",
        "Retrospective Cohort", "Case-Control", "Cross-sectional",
        "Case Series", "Case Report", "Review",
    ]
    for design in priority:
        for kw in STUDY_DESIGN_KEYWORDS.get(design, []):
            if kw in t:
                return design
    return ""


def detect_clinical_specialty(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    for specialty, kws in SPECIALTY_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return specialty
    return ""


def classify_all(text: str) -> tuple[str, str, str]:
    """Return ``(evidence_level, study_design, specialty)`` in one pass."""
    return (
        detect_evidence_level(text),
        detect_study_design(text),
        detect_clinical_specialty(text),
    )


def parse_pico_from_abstract(abstract: str) -> dict[str, str]:
    if not abstract:
        return {}
    pico: dict[str, str] = {}
    a = abstract.lower()

    patterns: dict[str, list[str]] = {
        "P": [
            r'(?:patients?|participants?|subjects?|adults?|children|population)\s+(?:with|who|aged?)[^.]{0,120}',
            r'(?:included|enrolled|recruited)\s+\d+[^.]{0,80}',
            r'(?:eligibility criteria|inclusion criteria)[^.]{0,120}',
        ],
        "I": [
            r'(?:intervention|treatment|therapy|drug|underwent|received|assigned to)[^.]{0,120}',
            r'(?:were randomized to|randomised to)[^.]{0,100}',
        ],
        "C": [
            r'(?:compared to|versus|vs\.?|control group|placebo|standard care)[^.]{0,100}',
        ],
        "O": [
            r'(?:primary outcome|secondary outcome|endpoint)[^.]{0,120}',
            r'(?:mortality|survival|reduction|improvement|incidence)\s+(?:was|were|rate|of)[^.]{0,100}',
        ],
    }

    for key, pats in patterns.items():
        for pat in pats:
            m = re.search(pat, a)
            if m:
                pico[key] = m.group(0).strip().capitalize()[:150]
                break

    return pico


ROB_DOMAINS: list[str] = [
    "Random sequence generation",
    "Allocation concealment",
    "Blinding of participants",
    "Blinding of outcome assessment",
    "Incomplete outcome data",
    "Selective reporting",
    "Other bias",
]
ROB_VALUES = ["Low", "High", "Unclear"]
ROB_ICONS = {"Low": "✅", "High": "❌", "Unclear": "⚠️"}


def generate_citation(paper: dict, fmt: str = "vancouver") -> str:
    raw = paper.get("authors") or ""
    alist = [a.strip() for a in raw.split(";") if a.strip()]
    title = paper.get("title") or ""
    journal = paper.get("journal") or ""
    year = paper.get("year") or ""
    doi = paper.get("doi") or ""
    doi_str = f" doi:{doi}" if doi else ""

    def _fv(a: str) -> str:
        parts = [x.strip() for x in a.split(",")]
        if len(parts) >= 2:
            return f"{parts[0]} {''.join(w[0].upper() for w in parts[1].split() if w)}"
        return a

    if fmt == "vancouver":
        auth = ", ".join(_fv(a) for a in alist[:6]) if alist else "Anonymous"
        if len(alist) > 6:
            auth += ", et al"
        return f"{auth}. {title}. {journal}. {year}.{doi_str}"

    if fmt == "apa":
        def _fa(a: str) -> str:
            parts = [x.strip() for x in a.split(",")]
            if len(parts) >= 2:
                return f"{parts[0]}, {'. '.join(w[0].upper() for w in parts[1].split() if w)}."
            return a
        auth = ", ".join(_fa(a) for a in alist[:7]) if alist else "Anonymous"
        doi_link = f" https://doi.org/{doi}" if doi else ""
        return f"{auth} ({year}). {title}. {journal}.{doi_link}"

    # chicago
    if not alist:
        auth = "Anonymous"
    elif len(alist) == 1:
        auth = alist[0]
    elif len(alist) > 3:
        auth = alist[0] + " et al."
    else:
        auth = ", ".join(alist[:-1]) + ", and " + alist[-1]
    return f'{auth}. "{title}." {journal} ({year}).{doi_str}'


def auto_tag(full_text: str, keywords: str, abstract: str) -> list[str]:
    combined = " ".join([(full_text or "")[:3000], keywords or "", abstract or ""]).lower()
    tag_dict = get_tag_dict()
    return list({t for t in tag_dict if t.lower() in combined})[:30]


def slugify(text: str, max_len: int = 60) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s\-]", "", text)
    return re.sub(r"[\s_]+", "_", text).strip("_")[:max_len]


def build_renamed_filename(paper: dict) -> str:
    year = paper.get("year") or "XXXX"
    raw_authors = paper.get("authors") or ""
    title = paper.get("title") or "Untitled"
    parts = [a.strip() for a in raw_authors.split(";") if a.strip()]
    if parts:
        last_names = [slugify(a.split(",")[0].strip(), 20) for a in parts[:2]]
        author_str = "_".join(last_names)
    else:
        author_str = "Unknown"
    title_words = re.sub(r'[^\w\s]', '', title).split()
    short_title = slugify("_".join(title_words[:6]), 50)
    return f"[{year}] {author_str} - {short_title}.pdf"


def export_ris(papers: list[dict]) -> str:
    lines: list[str] = []
    for p in papers:
        lines += [
            "TY  - JOUR",
            f"TI  - {p.get('title','')}",
            f"PY  - {p.get('year','')}",
            f"JO  - {p.get('journal','')}",
            f"DO  - {p.get('doi','')}",
            f"AB  - {p.get('abstract','')}",
        ]
        for a in (p.get("authors") or "").split(";"):
            if a.strip():
                lines.append(f"AU  - {a.strip()}")
        for kw in (p.get("keywords") or "").split(","):
            if kw.strip():
                lines.append(f"KW  - {kw.strip()}")
        lines.append("ER  -\n")
    return "\n".join(lines)


def export_bib(papers: list[dict]) -> str:
    entries: list[str] = []
    for p in papers:
        authors_raw = (p.get("authors") or "").replace("; ", " and ")
        year = p.get("year") or ""
        key = (
            (p.get("authors") or "unknown").split(";")[0].split(",")[0].strip().replace(" ", "")
            + str(year)
        )
        entries.append(
            f"@article{{{key},\n"
            f"  title   = {{{p.get('title','')}}},\n"
            f"  author  = {{{authors_raw}}},\n"
            f"  journal = {{{p.get('journal','')}}},\n"
            f"  year    = {{{year}}},\n"
            f"  doi     = {{{p.get('doi','')}}},\n"
            f"}}"
        )
    return "\n\n".join(entries)
