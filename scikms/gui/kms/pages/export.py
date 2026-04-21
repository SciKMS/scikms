"""Export page — Fluent card rows: icon + description + button."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel, CaptionLabel, CardWidget, FluentIcon, IconWidget, InfoBar,
    InfoBarPosition, PrimaryPushButton, StrongBodyLabel,
)

from scikms.gui.kms.shared import PageHeader
from scikms.i18n import t
from scikms.kms.atlas import atlas_load
from scikms.kms.clinical import export_bib, export_ris
from scikms.kms.db import get_all_papers

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


class _ExportRow(CardWidget):
    def __init__(self, icon: FluentIcon, label: str, description: str, ext_filter: str,
                 slot, parent=None) -> None:
        super().__init__(parent)
        self.setBorderRadius(8)
        self.setFixedHeight(72)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(12)

        ic = IconWidget(icon, self)
        ic.setFixedSize(28, 28)
        lay.addWidget(ic)

        text_lay = QVBoxLayout()
        text_lay.setSpacing(2)
        text_lay.addWidget(StrongBodyLabel(label))
        text_lay.addWidget(CaptionLabel(description))
        lay.addLayout(text_lay, 1)

        btn = PrimaryPushButton(FluentIcon.SAVE, t("common-save"))
        btn.clicked.connect(lambda: self._run(slot, ext_filter))
        lay.addWidget(btn)
        self._slot = slot
        self._filter = ext_filter

    def _run(self, slot, ext_filter: str) -> None:
        papers = get_all_papers()
        path, _ = QFileDialog.getSaveFileName(self, t("common-save"), "", ext_filter)
        if not path:
            return
        try:
            slot(papers, Path(path))
            InfoBar.success(
                title=t("kms-export-saved", path=Path(path).name), content=str(path),
                parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000,
            )
        except Exception as e:
            InfoBar.error(
                title=t("common-error"), content=str(e),
                parent=self, position=InfoBarPosition.TOP_RIGHT, duration=4000,
            )


class ExportPage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        layout.addWidget(PageHeader(t("kms-export-title")))

        rows = [
            (FluentIcon.DOCUMENT, "kms-export-ris",       "Zotero / EndNote",
             "RIS (*.ris)", self._export_ris),
            (FluentIcon.DOCUMENT, "kms-export-bib",       "LaTeX",
             "BibTeX (*.bib)", self._export_bib),
            (FluentIcon.DOCUMENT, "kms-export-excel",     "xlsx spreadsheet",
             "Excel (*.xlsx)", self._export_excel),
            (FluentIcon.DOCUMENT, "kms-export-pico-csv",  "Population · Intervention · Comparison · Outcome",
             "CSV (*.csv)", self._export_pico),
            (FluentIcon.PHOTO,    "kms-export-atlas-csv", "Figure metadata",
             "CSV (*.csv)", self._export_atlas),
            (FluentIcon.ZIP_FOLDER, "kms-export-zip-bundle", "PDFs + metadata archive",
             "ZIP (*.zip)", self._export_zip),
        ]
        for icon, label_key, desc, ext, slot in rows:
            layout.addWidget(_ExportRow(icon, t(label_key), desc, ext, slot))
        layout.addStretch(1)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        pass

    def _export_ris(self, papers: list[dict], path: Path) -> None:
        if not papers:
            raise RuntimeError(t("kms-export-no-papers"))
        path.write_text(export_ris(papers), encoding="utf-8")

    def _export_bib(self, papers: list[dict], path: Path) -> None:
        if not papers:
            raise RuntimeError(t("kms-export-no-papers"))
        path.write_text(export_bib(papers), encoding="utf-8")

    def _export_excel(self, papers: list[dict], path: Path) -> None:
        if not papers:
            raise RuntimeError(t("kms-export-no-papers"))
        try:
            import openpyxl
        except ImportError as e:
            raise RuntimeError("openpyxl not installed") from e
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Papers"
        cols = [
            "id", "title", "authors", "year", "journal", "doi",
            "evidence_level", "study_design", "clinical_specialty",
            "status", "starred", "pages", "added_at", "tags", "notes",
        ]
        ws.append(cols)
        for p in papers:
            ws.append([p.get(c, "") for c in cols])
        wb.save(path)

    def _export_pico(self, papers: list[dict], path: Path) -> None:
        if not papers:
            raise RuntimeError(t("kms-export-no-papers"))
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "title", "P", "I", "C", "O"])
            for p in papers:
                try:
                    pico = json.loads(p.get("pico_json") or "{}")
                except Exception:
                    pico = {}
                w.writerow([
                    p.get("id"), p.get("title", ""),
                    pico.get("P", ""), pico.get("I", ""),
                    pico.get("C", ""), pico.get("O", ""),
                ])

    def _export_atlas(self, _papers: list[dict], path: Path) -> None:
        df = atlas_load()
        if df is None:
            raise RuntimeError("pandas not installed")
        df.to_csv(path, index=False)

    def _export_zip(self, papers: list[dict], path: Path) -> None:
        if not papers:
            raise RuntimeError(t("kms-export-no-papers"))
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            metadata_buf = io.StringIO()
            w = csv.writer(metadata_buf)
            w.writerow(["id", "title", "authors", "year", "doi", "file_path"])
            for p in papers:
                w.writerow([p.get("id"), p.get("title", ""), p.get("authors", ""),
                            p.get("year", ""), p.get("doi", ""), p.get("file_path", "")])
                fp = p.get("file_path") or ""
                if fp and Path(fp).exists():
                    zf.write(fp, arcname=f"pdfs/{Path(fp).name}")
            zf.writestr("metadata.csv", metadata_buf.getvalue())
