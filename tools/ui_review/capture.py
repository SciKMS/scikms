"""UI review screenshot harness — read-only, offscreen.

Instantiates each page widget directly (skipping ``FluentWindow`` which hangs
under the offscreen platform plugin), resizes it to several sizes, and saves
a PNG per (page, size) pair. This captures the page *content* without nav
chrome — good enough to audit hierarchy, typography, spacing, responsive
behaviour, and empty states.

A separate helper captures a single composed ``FluentWindow`` screenshot by
mocking the splash animation. TODO only if needed later; page-level captures
are sufficient for the design audit.

Run:
    QT_QPA_PLATFORM=offscreen uv run python tools/ui_review/capture.py \
        --out ~/.gstack/projects/SciKMS-scikms/designs/design-audit-<date>/screenshots
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path


def _seed_demo_data() -> None:
    """Populate the temp DB with a small sample so tables are not empty."""
    from scikms.kms.db import db_conn, init_db

    init_db()
    rows = [
        ("10.1001/sample.001", "RCT on statins vs placebo in NSTEMI",
         "Nguyen A; Tran B", 2023, "NEJM",
         "Randomized trial of high-dose statins.", "statins, NSTEMI", "I",
         "RCT", "Cardiology", 12, "read", 1,
         '["cardio","RCT","statin"]', "2024-06-01T10:00:00"),
        ("10.1001/sample.002", "Meta-analysis of beta-blockers in HFrEF",
         "Le C; Pham D", 2022, "Lancet",
         "Systematic review and meta-analysis.", "beta-blocker, HFrEF", "I",
         "Meta-analysis", "Cardiology", 18, "reading", 0,
         '["cardio","meta-analysis"]', "2024-07-02T09:00:00"),
        ("10.1001/sample.003", "Cohort study of SGLT2 inhibitors in T2DM",
         "Bui E", 2024, "JAMA",
         "Prospective cohort of 5000 patients.", "SGLT2, T2DM", "II",
         "Cohort", "Endocrinology", 14, "read", 1,
         '["endo","cohort"]', "2024-08-15T14:00:00"),
        ("10.1001/sample.004", "Case series of rare pediatric nephrotic syndrome",
         "Do F; Vu G", 2021, "Pediatrics",
         "Ten consecutive pediatric cases.", "nephrotic, pediatric", "IV",
         "Case series", "Pediatrics", 8, "unread", 0,
         '["peds","nephro"]', "2024-09-10T08:00:00"),
        ("10.1001/sample.005", "Narrative review of immunotherapy in melanoma",
         "Hoang H", 2020, "Nature Reviews",
         "Summary of current immunotherapy.", "immunotherapy, melanoma", "V",
         "Narrative review", "Oncology", 22, "read", 0,
         '["onco","review"]', "2024-10-03T11:00:00"),
        ("10.1001/sample.006", "RCT: GLP-1 agonists in obesity",
         "Pham I", 2024, "NEJM",
         "Phase III trial, 52-week follow-up.", "GLP-1, obesity", "I",
         "RCT", "Endocrinology", 16, "reading", 1,
         '["endo","RCT","GLP-1"]', "2024-11-20T13:00:00"),
        ("10.1001/sample.007", "Observational study on delirium in ICU",
         "Ngo J", 2023, "Crit Care Med",
         "500-patient observational.", "delirium, ICU", "III",
         "Observational", "Critical Care", 10, "read", 0,
         '["ICU","observational"]', "2025-01-11T15:00:00"),
    ]
    with db_conn() as conn:
        for r in rows:
            conn.execute(
                """INSERT OR IGNORE INTO papers
                (doi,title,authors,year,journal,abstract,keywords,
                 evidence_level,study_design,clinical_specialty,
                 pages,status,starred,tags,added_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", r,
            )


def _make_mock_window():
    """Stub for the ``main_window`` argument every page takes."""
    from PyQt6.QtCore import QObject, pyqtSignal

    class _Mock(QObject):
        page_changed = pyqtSignal(str)

        def current_filters(self):
            return {
                "status": "all", "starred": False, "project": "",
                "evidence": "", "design": "", "specialty": "", "scope": "all",
            }

        def refresh_sidebar_stats(self):
            pass

        def show_page(self, _key):
            pass

    return _Mock()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True,
                        help="Directory to write PNGs into.")
    parser.add_argument("--no-seed", action="store_true",
                        help="Skip demo-data seeding (capture empty states).")
    parser.add_argument("--sizes", nargs="+",
                        default=["800x720", "1280x820", "1920x1080"],
                        help="Window sizes as WxH.")
    parser.add_argument("--only", nargs="+", default=None,
                        help="Only capture these page keys.")
    args = parser.parse_args()

    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("SCIKMS_LOCALE", "vi-VN")

    tmp = tempfile.mkdtemp(prefix="scikms-uireview-")
    from scikms.kms import set_data_root
    set_data_root(Path(tmp))

    if not args.no_seed:
        _seed_demo_data()
    else:
        from scikms.kms.db import init_db
        init_db()

    print("Booting QApplication...", flush=True)
    from PyQt6.QtWidgets import QApplication
    from qfluentwidgets import Theme, setTheme, setThemeColor
    app = QApplication.instance() or QApplication(sys.argv)
    setTheme(Theme.LIGHT)
    setThemeColor("#4338CA")

    from scikms.gui.kms.pages.atlas import AtlasPage
    from scikms.gui.kms.pages.export import ExportPage
    from scikms.gui.kms.pages.import_page import ImportPage
    from scikms.gui.kms.pages.library import LibraryPage
    from scikms.gui.kms.pages.rename import RenamePage
    from scikms.gui.kms.pages.search import SearchPage
    from scikms.gui.kms.pages.settings import SettingsPage
    from scikms.gui.kms.pages.stats import StatsPage

    page_factories = {
        "library":  LibraryPage,
        "import":   ImportPage,
        "search":   SearchPage,
        "atlas":    AtlasPage,
        "stats":    StatsPage,
        "rename":   RenamePage,
        "export":   ExportPage,
        "settings": SettingsPage,
    }

    sizes = []
    for s in args.sizes:
        w, h = s.lower().split("x")
        sizes.append((int(w), int(h)))

    suffix = "-empty" if args.no_seed else ""
    only = set(args.only) if args.only else None

    for key, factory in page_factories.items():
        if only and key not in only:
            continue
        mock = _make_mock_window()
        print(f"[{key}] construct...", flush=True)
        page = factory(mock)
        page.setObjectName(f"kms-page-{key}")
        if hasattr(page, "refresh"):
            try:
                page.refresh()
            except Exception as e:
                print(f"  refresh error: {e}", flush=True)
        page.show()
        for _ in range(4):
            app.processEvents()
        for (w, h) in sizes:
            page.resize(w, h)
            for _ in range(6):
                app.processEvents()
            pix = page.grab()
            filename = f"{key}-{w}x{h}{suffix}.png"
            out_path = out_dir / filename
            pix.save(str(out_path), "PNG")
            print(f"  [{w:>4}x{h:<4}] {filename}  ({pix.width()}x{pix.height()})", flush=True)
        page.deleteLater()
        for _ in range(2):
            app.processEvents()

    print(f"Done. Files in {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
