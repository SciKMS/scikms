"""scikms.kms.importers — PDF / DOI / PubMed import pipelines.

Port of y-khoa/modules/importers.py. Streamlit coupling removed; callers pass
raw ``(bytes, filename)`` tuples instead of ``UploadedFile`` objects, and
cache invalidation is the caller's responsibility.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

from scikms import kms as _kms
from scikms.kms.atlas import atlas_extract_from_pdf
from scikms.kms.clinical import (
    auto_tag, build_renamed_filename, classify_all, parse_pico_from_abstract,
)
from scikms.kms.db import db_conn, check_duplicate


try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from PIL import Image  # noqa: F401
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def extract_pdf_text_and_meta(pdf_bytes: bytes) -> dict:
    empty = {"full_text": "", "pages": 0, "title": "", "author": "",
             "abstract": "", "keywords": "", "first_page_text": ""}
    if not HAS_PYMUPDF:
        return empty
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        meta = doc.metadata or {}
        pages = len(doc)
        texts = []
        for i, page in enumerate(doc):
            texts.append(page.get_text("text"))
            if i >= 80:
                break
        doc.close()
        full_text = "\n".join(texts)
        first_page = texts[0] if texts else ""
        abstract_m = re.search(
            r"(?i)(?:abstract|summary)[:\s\n]{1,5}(.{100,2000}?)(?:\n\n|\Z|introduction|background|methods)",
            full_text[:5000], re.S,
        )
        abstract = abstract_m.group(1).strip() if abstract_m else ""
        kw_m = re.search(r"(?i)keywords?[:\s]{1,5}(.{10,300}?)(?:\n\n|\Z)", full_text[:3000])
        keywords = kw_m.group(1).strip()[:300] if kw_m else ""
        return {
            "full_text":       full_text[:80000],
            "pages":           pages,
            "title":           (meta.get("title") or "").strip(),
            "author":          (meta.get("author") or "").strip(),
            "abstract":        abstract,
            "keywords":        keywords,
            "first_page_text": first_page[:3000],
        }
    except Exception:
        return empty


def _heuristic_fallback(first_page: str) -> dict:
    lines = [ln.strip() for ln in first_page.splitlines() if ln.strip()][:30]
    title, authors = "", ""
    for line in lines[:6]:
        if len(line) > 20 and not re.match(r"^\d", line) and "@" not in line:
            title = line[:200]
            break
    for line in lines[:20]:
        if re.search(r'[A-Z][a-z]+,?\s+[A-Z]\.', line) and len(line) < 200:
            authors = line[:200]
            break
    return {"title": title, "authors": authors}


def _is_garbage_title(t: str) -> bool:
    if not t or len(t) < 5:
        return True
    tl = t.lower()
    return tl in {"untitled", "null", "none", "no title", "pdf", "document"} or bool(
        re.match(r'^[\d\W]+$', t)
    )


def _is_garbage_author(a: str) -> bool:
    return not a or len(a) < 3 or a.lower() in {"unknown", "author", "authors", "anonymous", "n/a"}


def _extract_doi(text: str) -> str | None:
    m = re.search(r'\b10\.\d{4,}/[^\s"\'<>]{3,}\b', text)
    return m.group(0).rstrip(".,;") if m else None


def fetch_crossref(doi: str) -> dict:
    if not HAS_REQUESTS:
        return {}
    try:
        r = requests.get(
            f"https://api.crossref.org/works/{doi}",
            timeout=8,
            headers={"User-Agent": "scikms/0.1 (mailto:user@example.com)"},
        )
        if r.status_code != 200:
            return {}
        msg = r.json()["message"]
        title = (msg.get("title") or [""])[0]
        authors = "; ".join(
            f"{a.get('family','')}, {a.get('given','')}" for a in msg.get("author", [])
        )
        year = (msg.get("published-print") or msg.get("published-online") or {}).get(
            "date-parts", [[None]]
        )[0][0]
        journal = (msg.get("container-title") or [""])[0]
        abstract = re.sub(r"<[^>]+>", "", msg.get("abstract") or "")
        keywords = ", ".join(kw.get("value", "") for kw in msg.get("subject", []) if kw.get("value"))
        return {"title": title, "authors": authors, "year": year, "journal": journal,
                "abstract": abstract, "keywords": keywords, "doi": doi}
    except Exception:
        return {}


def fetch_pubmed(query: str) -> dict:
    if not HAS_REQUESTS:
        return {}
    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    try:
        r1 = requests.get(
            f"{BASE}/esearch.fcgi",
            params={"db": "pubmed", "term": query, "retmax": 1, "retmode": "json"},
            timeout=8,
        )
        ids = r1.json()["esearchresult"].get("idlist", [])
        if not ids:
            return {}
        pmid = ids[0]
        r2 = requests.get(
            f"{BASE}/efetch.fcgi",
            params={"db": "pubmed", "id": pmid, "retmode": "xml", "rettype": "abstract"},
            timeout=10,
        )
        xml = r2.text

        def _xt(tag: str, t: str) -> str:
            m = re.search(fr"<{tag}[^>]*>(.*?)</{tag}>", t, re.S)
            return m.group(1).strip() if m else ""

        def _xts(tag: str, t: str) -> list[str]:
            return re.findall(fr"<{tag}[^>]*>(.*?)</{tag}>", t, re.S)

        title = re.sub(r"<[^>]+>", "", _xt("ArticleTitle", xml))
        authors = "; ".join(
            f"{re.sub(r'<[^>]+>','',_xt('LastName',a))}, {re.sub(r'<[^>]+>','',_xt('ForeName',a))}"
            for a in _xts("Author", xml)
        )
        abstract = re.sub(r'<[^>]+>', '', _xt("AbstractText", xml))
        year_m = re.search(r'<PubDate>.*?<Year>(\d{4})</Year>', xml, re.S)
        journal = re.sub(r'<[^>]+>', '', _xt("Title", xml))
        doi_m = re.search(r'<ArticleId IdType="doi"[^>]*>([^<]+)<', xml)
        doi = doi_m.group(1).strip() if doi_m else ""
        return {"title": title, "authors": authors, "abstract": abstract,
                "year": int(year_m.group(1)) if year_m else None,
                "journal": journal, "doi": doi}
    except Exception:
        return {}


def extract_meta_with_gemini(text: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or not HAS_REQUESTS:
        return {}
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        prompt = (
            "Extract bibliographic metadata from this academic paper text.\n"
            "Return ONLY valid JSON: {title, authors (semicolon-separated), year (int), "
            "journal, abstract, keywords}. Empty string if absent.\n"
            f"Text: {text[:2500]}"
        )
        r = requests.post(
            url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15,
        )
        if r.status_code == 200:
            content = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            m = re.search(r'\{.*\}', content, re.S)
            if m:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, dict):
                    return parsed
    except Exception:
        pass
    return {}


def find_open_access_pdf(doi: str) -> dict:
    if not HAS_REQUESTS or not doi:
        return {"found": False}
    try:
        r = requests.get(
            f"https://api.unpaywall.org/v2/{doi}?email=user@example.com", timeout=8,
        )
        if r.status_code == 200:
            oa_url = (r.json().get("best_oa_location") or {}).get("url_for_pdf")
            if oa_url:
                return {"found": True, "url": oa_url, "source": "Unpaywall"}
    except Exception:
        pass
    return {"found": False}


def download_and_save_pdf(pdf_url: str, doi: str = "", filename_hint: str = "") -> dict:
    if not HAS_REQUESTS:
        return {"success": False, "error": "requests not available"}
    try:
        r = requests.get(pdf_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"},
                         allow_redirects=True)
        if r.status_code != 200:
            return {"success": False, "error": f"HTTP {r.status_code}"}
        content = r.content
        if b"%PDF" not in content[:1024]:
            return {"success": False, "error": "Not a valid PDF"}
        md5 = hashlib.md5(content).hexdigest()
        safe = re.sub(r'[^\w\-]', '_', (filename_hint or doi or md5[:8]))[:40]
        dest = _kms.STORAGE_DIR / f"{md5[:8]}_{safe}.pdf"
        dest.write_bytes(content)
        pages, full_text = 0, ""
        if HAS_PYMUPDF:
            try:
                d = extract_pdf_text_and_meta(content)
                pages = d.get("pages", 0)
                full_text = d.get("full_text", "")[:50000]
            except Exception:
                pass
        return {"success": True, "file_path": str(dest), "pages": pages, "full_text": full_text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def process_pdf_bytes(file_bytes: bytes, filename: str, extract_images: bool = True) -> dict:
    """Ingest a PDF (raw bytes + original filename) and return the inserted paper dict.

    On duplicate, returns ``{"error": "...", "_is_dup": True, "_dup_id": N}``.
    Caller reads the file; this function has no UI dependencies.
    """
    md5 = hashlib.md5(file_bytes).hexdigest()

    dup = check_duplicate(md5, "", "")
    if dup:
        return {"error": f"File already in library (MD5: {md5[:8]}…)",
                "_is_dup": True, "_dup_id": dup.get("id")}

    pdf_data = extract_pdf_text_and_meta(file_bytes)
    full_text = pdf_data["full_text"]
    doi = _extract_doi(full_text) or _extract_doi(filename)

    meta: dict = {}
    if doi:
        meta = fetch_crossref(doi)

    raw_title = pdf_data.get("title", "")
    raw_author = pdf_data.get("author", "")
    if not meta.get("title") and not _is_garbage_title(raw_title):
        meta["title"] = raw_title
    if not meta.get("abstract") and pdf_data.get("abstract"):
        meta["abstract"] = pdf_data["abstract"]
    if not meta.get("authors") and not _is_garbage_author(raw_author):
        meta["authors"] = raw_author

    if not meta.get("title") or not meta.get("authors"):
        fb = _heuristic_fallback(pdf_data.get("first_page_text", ""))
        if not meta.get("title") and fb.get("title"):
            meta["title"] = fb["title"]
        if not meta.get("authors") and fb.get("authors"):
            meta["authors"] = fb["authors"]

    if HAS_REQUESTS and (not meta.get("title") or not meta.get("authors")):
        ai = extract_meta_with_gemini(pdf_data.get("first_page_text") or full_text[:3000])
        for k in ["title", "authors", "year", "journal", "abstract", "keywords"]:
            if not meta.get(k) and ai.get(k):
                meta[k] = ai[k]

    if not meta.get("title"):
        meta["title"] = Path(filename).stem.replace("_", " ").replace("-", " ").title()
    meta.setdefault("doi", doi or "")

    title_dup = check_duplicate("", meta.get("doi", ""), meta.get("title", ""))
    if title_dup:
        reason = "DOI" if title_dup.get("doi") == meta.get("doi") else "similar title"
        return {"error": f"Duplicate ({reason}): «{title_dup.get('title','')[:80]}»",
                "_is_dup": True, "_dup_id": title_dup.get("id")}

    tags = auto_tag(full_text[:5000], meta.get("keywords", ""), meta.get("abstract", ""))
    combined = f"{meta.get('title','')} {meta.get('abstract','')} {meta.get('keywords','')}"
    ev, sd, sp = classify_all(combined)
    pico = parse_pico_from_abstract(meta.get("abstract", ""))

    safe_name = re.sub(r'[^\w\-.]', '_', filename)
    dest = _kms.STORAGE_DIR / f"{md5[:8]}_{safe_name}"
    dest.write_bytes(file_bytes)

    paper = {
        "md5":               md5,
        "original_filename": filename,
        "title":             meta.get("title", ""),
        "authors":           meta.get("authors", ""),
        "year":              meta.get("year") or datetime.now().year,
        "journal":           meta.get("journal", ""),
        "doi":               meta.get("doi", ""),
        "abstract":          meta.get("abstract", ""),
        "keywords":          meta.get("keywords") or pdf_data.get("keywords", ""),
        "full_text":         full_text,
        "tags":              json.dumps(tags),
        "status":            "unread",
        "starred":           0,
        "pages":             pdf_data["pages"],
        "added_at":          datetime.now().strftime("%Y-%m-%d"),
        "file_path":         str(dest),
        "notes":             "",
        "highlights":        "[]",
        "project":           "",
        "reading_position":  0,
        "evidence_level":    ev,
        "study_design":      sd,
        "clinical_specialty": sp,
        "pico_json":         json.dumps(pico),
        "risk_of_bias_json": "{}",
        "impact_factor":     0.0,
        "citation_count":    0,
    }
    paper["renamed_filename"] = build_renamed_filename(paper)

    with db_conn() as conn:
        conn.execute("""
            INSERT INTO papers
            (md5,original_filename,renamed_filename,title,authors,year,journal,doi,
             abstract,keywords,full_text,tags,notes,highlights,status,starred,pages,
             added_at,file_path,project,reading_position,evidence_level,study_design,
             clinical_specialty,pico_json,risk_of_bias_json,impact_factor,citation_count)
            VALUES (:md5,:original_filename,:renamed_filename,:title,:authors,:year,:journal,:doi,
                    :abstract,:keywords,:full_text,:tags,:notes,:highlights,:status,:starred,:pages,
                    :added_at,:file_path,:project,:reading_position,:evidence_level,:study_design,
                    :clinical_specialty,:pico_json,:risk_of_bias_json,:impact_factor,:citation_count)
        """, paper)
        paper["id"] = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    if extract_images and HAS_PYMUPDF and HAS_PIL:
        try:
            n = atlas_extract_from_pdf(
                file_bytes, paper["id"],
                paper.get("title", "")[:50] or Path(filename).stem,
                str(dest),
            )
            if n > 0:
                paper["_atlas_images_extracted"] = n
        except Exception as e:
            paper["_atlas_error"] = str(e)

    return paper


def import_by_doi(doi: str, auto_download_pdf: bool = False) -> dict:
    doi = doi.strip().lstrip("https://doi.org/").lstrip("http://doi.org/")
    with db_conn() as conn:
        ex = conn.execute("SELECT id,title FROM papers WHERE doi=?", (doi,)).fetchone()
    if ex:
        return {"error": f"DOI already exists: «{ex['title']}»"}

    meta = fetch_crossref(doi)
    if not meta or not meta.get("title"):
        return {"error": f"No CrossRef metadata for DOI: {doi}"}

    file_path, pages, full_text = "", 0, f"{meta.get('title','')} {meta.get('abstract','')}"

    if auto_download_pdf:
        oa = find_open_access_pdf(doi)
        if oa["found"]:
            dl = download_and_save_pdf(
                oa["url"], doi=doi,
                filename_hint=re.sub(r'[^\w]', '_', meta.get("title", ""))[:30],
            )
            if dl["success"]:
                file_path = dl["file_path"]
                pages = dl.get("pages", 0)
                if dl.get("full_text"):
                    full_text = dl["full_text"]

    md5_src = (hashlib.md5(Path(file_path).read_bytes()).hexdigest()
               if file_path and os.path.exists(file_path)
               else hashlib.md5(doi.encode()).hexdigest())

    tags = auto_tag(full_text[:5000], meta.get("keywords", ""), meta.get("abstract", ""))
    combined = f"{meta.get('title','')} {meta.get('abstract','')}"
    ev, sd, sp = classify_all(combined)
    pico = parse_pico_from_abstract(meta.get("abstract", ""))

    paper = {
        "md5":               md5_src,
        "original_filename": f"(DOI: {doi})",
        "title":             meta.get("title", ""),
        "authors":           meta.get("authors", ""),
        "year":              meta.get("year") or datetime.now().year,
        "journal":           meta.get("journal", ""),
        "doi":               doi,
        "abstract":          meta.get("abstract", ""),
        "keywords":          meta.get("keywords", ""),
        "full_text":         full_text,
        "tags":              json.dumps(tags),
        "status":            "unread",
        "starred":           0,
        "pages":             pages,
        "added_at":          datetime.now().strftime("%Y-%m-%d"),
        "file_path":         file_path,
        "notes":             "",
        "highlights":        "[]",
        "project":           "",
        "reading_position":  0,
        "evidence_level":    ev,
        "study_design":      sd,
        "clinical_specialty": sp,
        "pico_json":         json.dumps(pico),
        "risk_of_bias_json": "{}",
        "impact_factor":     0.0,
        "citation_count":    0,
    }
    paper["renamed_filename"] = build_renamed_filename(paper)

    with db_conn() as conn:
        try:
            conn.execute("""
                INSERT INTO papers
                (md5,original_filename,renamed_filename,title,authors,year,journal,doi,
                 abstract,keywords,full_text,tags,notes,highlights,status,starred,pages,
                 added_at,file_path,project,reading_position,evidence_level,study_design,
                 clinical_specialty,pico_json,risk_of_bias_json,impact_factor,citation_count)
                VALUES (:md5,:original_filename,:renamed_filename,:title,:authors,:year,:journal,:doi,
                        :abstract,:keywords,:full_text,:tags,:notes,:highlights,:status,:starred,:pages,
                        :added_at,:file_path,:project,:reading_position,:evidence_level,:study_design,
                        :clinical_specialty,:pico_json,:risk_of_bias_json,:impact_factor,:citation_count)
            """, paper)
            paper["id"] = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        except Exception as e:
            return {"error": str(e)}

    return paper
