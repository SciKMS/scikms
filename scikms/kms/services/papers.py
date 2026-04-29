"""Paper services that combine repository operations with business behavior."""

from __future__ import annotations

import os
import re

from scikms.kms.repositories.papers import (
    delete_paper_row,
    find_duplicate_by_doi,
    find_duplicate_by_md5,
    get_duplicate_title_candidates,
    get_paper_by_id,
)


def delete_paper(paper_id: int) -> None:
    paper = get_paper_by_id(paper_id)
    if paper:
        fp = paper.get("file_path", "")
        if fp and os.path.exists(fp):
            try:
                os.remove(fp)
            except OSError:
                pass
    delete_paper_row(paper_id)


def check_duplicate(md5: str, doi: str, title: str) -> dict | None:
    if md5:
        row = find_duplicate_by_md5(md5)
        if row:
            return row
    if doi:
        row = find_duplicate_by_doi(doi)
        if row:
            return row
    if title and len(title) > 15:
        t_words = set(re.sub(r"[^\w\s]", "", title.lower()).split())
        for row in get_duplicate_title_candidates():
            r_words = set(
                re.sub(r"[^\w\s]", "", (row["title"] or "").lower()).split()
            )
            if len(t_words) > 3 and len(r_words) > 3:
                common = len(t_words & r_words)
                if common / max(len(t_words), len(r_words)) > 0.85:
                    return row
    return None
