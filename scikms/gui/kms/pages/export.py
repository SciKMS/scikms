"""Export page — RIS, BibTeX, Excel, PICO CSV, Atlas CSV, ZIP."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QFileDialog, QGroupBox, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from scikms.i18n import t
from scikms.kms import ATLAS_ROOT
from scikms.kms.atlas import atlas_load
from scikms.kms.clinical import export_bib, export_ris
from scikms.kms.db import get_all_papers

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


class ExportPage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h2>{t('kms-export-title')}</h2>"))

        for label_key, slot, ext_filter in [
            ("kms-export-ris",       self._export_ris,   "RIS (*.ris)"),
            ("kms-export-bib",       self._export_bib,   "BibTeX (*.bib)"),
            ("kms-export-excel",     self._export_excel, "Excel (*.xlsx)"),
            ("kms-export-pico-csv",  self._export_pico,  "CSV (*.csv)"),
            ("kms-export-atlas-csv", self._export_atlas, "CSV (*.csv)"),
            ("kms-export-zip-bundle", self._export_zip,  "ZIP (*.zip)"),
        ]:
            btn = QPushButton(t(label_key))
            btn.clicked.connect(lambda _checked=False, fn=slot, fil=ext_filter: self._run_with_picker(fn, fil))
            layout.addWidget(btn)

        self._lbl_status = QLabel("")
        layout.addWidget(self._lbl_status)
        layout.addStretch(1)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        pass

    def _run_with_picker(self, fn, ext_filter: str) -> None:
        papers = get_all_papers()
        if not papers and "atlas" not in fn.__name__:
            self._lbl_status.setText(t("kms-export-no-papers"))
            return
        path, _ = QFileDialog.getSaveFileName(self, t("common-save"), "", ext_filter)
        if not path:
            return
        try:
            fn(papers, Path(path))
            self._lbl_status.setText(t("kms-export-saved", path=path))
        except Exception as e:
            self._lbl_status.setText(f"{t('common-error')}: {e}")

    def _export_ris(self, papers: list[dict], path: Path) -> None:
        path.write_text(export_ris(papers), encoding="utf-8")

    def _export_bib(self, papers: list[dict], path: Path) -> None:
        path.write_text(export_bib(papers), encoding="utf-8")

    def _export_excel(self, papers: list[dict], path: Path) -> None:
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

    def _export_atlas(self, papers: list[dict], path: Path) -> None:
        df = atlas_load()
        if df is None:
            raise RuntimeError("pandas not installed")
        df.to_csv(path, index=False)

    def _export_zip(self, papers: list[dict], path: Path) -> None:
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
