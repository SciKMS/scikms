"""scikms.kms.atlas — figure extraction and metadata store.

Data layer only. The Streamlit UI in y-khoa/modules/atlas.py has been dropped;
the PyQt6 atlas page in :mod:`scikms.gui.kms.pages.atlas` replaces it.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

from scikms import kms as _kms
from scikms.kms.config import (
    ATLAS_META_COLS, FIGURE_TYPE_KEYWORDS, SUBJECT_DOMAIN_KEYWORDS,
)


def _atlas_paths():
    return _kms.ATLAS_ROOT / "metadata.parquet", _kms.ATLAS_ROOT / "metadata.csv"


try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def _empty_df():
    if not HAS_PANDAS:
        return None
    return pd.DataFrame(columns=ATLAS_META_COLS)


def atlas_load():
    """Load figure-atlas metadata. Parquet preferred, CSV fallback, empty otherwise."""
    if not HAS_PANDAS:
        return None
    parquet, csv = _atlas_paths()
    try:
        if parquet.exists():
            return pd.read_parquet(parquet)
    except Exception:
        pass
    try:
        if csv.exists():
            return pd.read_csv(csv)
    except Exception:
        pass
    return _empty_df()


def atlas_save(df) -> None:
    if not HAS_PANDAS:
        return
    for col in ATLAS_META_COLS:
        if col not in df.columns:
            df[col] = ""
    parquet, csv = _atlas_paths()
    try:
        df.to_parquet(parquet, index=False)
    except Exception:
        pass
    try:
        df.to_csv(csv, index=False)
    except Exception:
        pass


def atlas_search(query: str, df=None):
    if not HAS_PANDAS:
        return None
    if df is None:
        df = atlas_load()
    if df is None or df.empty:
        return df
    bag = (
        df["caption"].fillna("") + " " +
        df["context"].fillna("") + " " +
        df["fig_num"].fillna("") + " " +
        df["notes"].fillna("")
    ).str.lower()
    return df[bag.str.contains(re.escape(query.lower()), na=False)]


def atlas_count() -> int:
    df = atlas_load()
    return 0 if df is None else len(df)


def atlas_delete_figure(idx) -> None:
    df = atlas_load()
    if df is None or idx not in df.index:
        return
    row = df.loc[idx]
    for path_col in ("image_path", "thumb_path"):
        rel = row.get(path_col, "")
        if rel:
            full = _kms.ATLAS_ROOT / rel
            if full.exists():
                try:
                    full.unlink()
                except OSError:
                    pass
    df = df.drop(index=idx).reset_index(drop=True)
    atlas_save(df)


def _classify_figure_type(context: str) -> str:
    if not context:
        return "other"
    t = context.lower()
    for ftype, kws in FIGURE_TYPE_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return ftype
    return "other"


def _classify_domain(context: str) -> str:
    if not context:
        return "general"
    t = context.lower()
    for domain, kws in SUBJECT_DOMAIN_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return domain
    return "general"


def atlas_extract_from_pdf(
    pdf_bytes: bytes,
    paper_id: int,
    book_name: str,
    source_document_path: str,
    min_px: int = 120,
) -> int:
    """Extract images from ``pdf_bytes`` into the atlas. Returns count saved."""
    try:
        import fitz  # PyMuPDF
        from PIL import Image
    except ImportError:
        return 0
    if not HAS_PANDAS:
        return 0

    saved = 0
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return 0

    df = atlas_load()
    if df is None:
        return 0

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        img_list = page.get_images(full=True)
        page_ctx = page.get_text("text")[:600]

        for img_index, img_info in enumerate(img_list):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
            except Exception:
                continue
            if not base_image or not base_image.get("image"):
                continue

            width = base_image.get("width", 0)
            height = base_image.get("height", 0)
            if width < min_px or height < min_px:
                continue

            img_bytes = base_image["image"]
            ext = base_image.get("ext", "png")
            md5 = hashlib.md5(img_bytes).hexdigest()

            if not df.empty and "bytes_md5" in df.columns and md5 in df["bytes_md5"].values:
                continue

            rel_dir = Path(f"paper_{paper_id}")
            (_kms.ATLAS_ROOT / rel_dir).mkdir(parents=True, exist_ok=True)
            fname = f"p{page_idx+1}_x{xref}.{ext}"
            full_rel = rel_dir / fname
            full_path = _kms.ATLAS_ROOT / full_rel
            full_path.write_bytes(img_bytes)

            thumb_rel = None
            try:
                from io import BytesIO
                pil_img = Image.open(BytesIO(img_bytes))
                pil_img.thumbnail((200, 200))
                thumb_fname = f"p{page_idx+1}_x{xref}_thumb.{ext}"
                thumb_rel = Path("_thumbs") / thumb_fname
                thumb_path = _kms.ATLAS_ROOT / thumb_rel
                pil_img.save(str(thumb_path))
            except Exception:
                thumb_rel = None

            fig_type = _classify_figure_type(page_ctx)
            domain = _classify_domain(page_ctx)

            new_row = {
                "kms_paper_id":         paper_id,
                "book_name":            book_name,
                "image_path":           str(full_rel),
                "thumb_path":           str(thumb_rel) if thumb_rel else "",
                "page_num":             page_idx + 1,
                "fig_num":              f"Fig p{page_idx+1}-{img_index+1}",
                "group_key":            "",
                "caption":              "",
                "context":              page_ctx,
                "figure_type":          fig_type,
                "subject_domain":       domain,
                "confidence":           "low",
                "source":               "auto-extract",
                "saved_at":             datetime.now().isoformat(),
                "bytes_md5":            md5,
                "relevance_score":      0,
                "notes":                "",
                "source_document_path": source_document_path,
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            saved += 1

    doc.close()
    if saved:
        atlas_save(df)
    return saved
