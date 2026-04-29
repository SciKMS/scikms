"""Stats service for DB and storage metrics."""

from __future__ import annotations

import os

from scikms import kms as _kms
from scikms.kms.repositories.stats import get_library_stats


def get_db_stats() -> dict:
    stats = get_library_stats()
    db_sz = os.path.getsize(_kms.DB_PATH) / 1024 if os.path.exists(_kms.DB_PATH) else 0
    pdf_sz = sum(
        f.stat().st_size for f in _kms.STORAGE_DIR.glob("*.pdf") if f.is_file()
    ) / (1024 * 1024)

    return {
        **stats,
        "db_kb": round(db_sz, 1),
        "pdf_mb": round(pdf_sz, 2),
        "storage_path": str(_kms.STORAGE_DIR.resolve()),
    }
