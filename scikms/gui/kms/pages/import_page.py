"""Import page — 4 tabs: PDF upload, DOI lookup, PubMed search, manual entry."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from scikms.i18n import t
from scikms.kms.clinical import auto_tag, build_renamed_filename, classify_all, parse_pico_from_abstract
from scikms.kms.db import db_conn
from scikms.kms.importers import fetch_pubmed, import_by_doi, process_pdf_bytes

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


class _PdfImportWorker(QThread):
    progress = pyqtSignal(int, int, str)  # current, total, filename
    finished_one = pyqtSignal(dict)

    def __init__(self, paths: list[str], extract_images: bool) -> None:
        super().__init__()
        self._paths = paths
        self._extract = extract_images

    def run(self) -> None:
        for i, path_str in enumerate(self._paths, 1):
            path = Path(path_str)
            self.progress.emit(i, len(self._paths), path.name)
            try:
                data = path.read_bytes()
                res = process_pdf_bytes(data, path.name, extract_images=self._extract)
            except Exception as e:
                res = {"error": str(e), "_filename": path.name}
            res.setdefault("_filename", path.name)
            self.finished_one.emit(res)


class ImportPage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._build()
        self._worker: _PdfImportWorker | None = None

    # ------------------------------------------------------------------
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h2>{t('kms-import-title')}</h2>"))
        layout.addWidget(QLabel(t("kms-import-pdf-help")))

        self._tabs = QTabWidget(self)
        self._tabs.addTab(self._build_pdf_tab(), t("kms-import-tab-pdf"))
        self._tabs.addTab(self._build_doi_tab(), t("kms-import-tab-doi"))
        self._tabs.addTab(self._build_pubmed_tab(), t("kms-import-tab-pubmed"))
        self._tabs.addTab(self._build_manual_tab(), t("kms-import-tab-manual"))
        layout.addWidget(self._tabs, 1)

    # ----- PDF tab -----------------------------------------------------
    def _build_pdf_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        row = QHBoxLayout()
        self._btn_pick = QPushButton(t("kms-import-pdf-pick"))
        self._btn_pick.clicked.connect(self._on_pick_pdfs)
        row.addWidget(self._btn_pick)
        self._chk_extract = QCheckBox(t("kms-import-pdf-extract-images"))
        self._chk_extract.setChecked(True)
        row.addWidget(self._chk_extract)
        row.addStretch(1)
        lay.addLayout(row)

        self._lst_files = QListWidget()
        lay.addWidget(self._lst_files, 1)

        self._btn_process = QPushButton(t("kms-import-pdf-process", count=0))
        self._btn_process.clicked.connect(self._on_process_pdfs)
        self._btn_process.setEnabled(False)
        lay.addWidget(self._btn_process)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        lay.addWidget(self._progress)

        self._lbl_pdf_status = QLabel("")
        lay.addWidget(self._lbl_pdf_status)

        return w

    def _on_pick_pdfs(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, t("kms-import-pdf-pick"), "", "PDF (*.pdf)")
        if not paths:
            return
        self._lst_files.clear()
        self._lst_files.addItems(paths)
        self._btn_process.setText(t("kms-import-pdf-process", count=len(paths)))
        self._btn_process.setEnabled(True)

    def _on_process_pdfs(self) -> None:
        paths = [self._lst_files.item(i).text() for i in range(self._lst_files.count())]
        if not paths or self._worker:
            return
        self._success = 0
        self._failed = 0
        self._progress.setVisible(True)
        self._progress.setRange(0, len(paths))
        self._progress.setValue(0)
        self._btn_process.setEnabled(False)
        self._lbl_pdf_status.setText("")

        self._worker = _PdfImportWorker(paths, self._chk_extract.isChecked())
        self._worker.progress.connect(self._on_pdf_progress)
        self._worker.finished_one.connect(self._on_pdf_one)
        self._worker.finished.connect(self._on_pdf_done)
        self._worker.start()

    def _on_pdf_progress(self, cur: int, total: int, filename: str) -> None:
        self._progress.setValue(cur)
        self._lbl_pdf_status.setText(f"[{cur}/{total}] {filename}")

    def _on_pdf_one(self, res: dict) -> None:
        if "error" in res:
            self._failed += 1
        else:
            self._success += 1

    def _on_pdf_done(self) -> None:
        self._worker = None
        self._progress.setVisible(False)
        self._btn_process.setEnabled(True)
        msg = (
            t("kms-import-pdf-success", count=self._success)
            + " " + t("kms-import-pdf-failed", count=self._failed)
        )
        self._lbl_pdf_status.setText(msg)
        self._main.refresh_sidebar_stats()

    # ----- DOI tab -----------------------------------------------------
    def _build_doi_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel(t("kms-import-doi-prompt")))
        self._txt_dois = QPlainTextEdit()
        self._txt_dois.setPlaceholderText("10.1056/NEJMoa2034577\n10.1016/j.lancet.2020.11.001")
        lay.addWidget(self._txt_dois, 1)
        self._chk_oa = QCheckBox(t("kms-import-doi-download-pdf"))
        lay.addWidget(self._chk_oa)
        btn = QPushButton(t("kms-import-doi-fetch"))
        btn.clicked.connect(self._on_fetch_doi)
        lay.addWidget(btn)
        self._lbl_doi_status = QLabel("")
        lay.addWidget(self._lbl_doi_status)
        return w

    def _on_fetch_doi(self) -> None:
        text = self._txt_dois.toPlainText().strip()
        if not text:
            return
        ok, fail = 0, 0
        for line in text.splitlines():
            doi = line.strip()
            if not doi:
                continue
            res = import_by_doi(doi, auto_download_pdf=self._chk_oa.isChecked())
            if "error" in res:
                fail += 1
            else:
                ok += 1
        self._lbl_doi_status.setText(
            t("kms-import-pdf-success", count=ok) + " " + t("kms-import-pdf-failed", count=fail)
        )
        self._main.refresh_sidebar_stats()

    # ----- PubMed tab -------------------------------------------------
    def _build_pubmed_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel(t("kms-import-pubmed-prompt")))
        self._ed_pubmed = QLineEdit()
        self._ed_pubmed.setPlaceholderText("e.g., metformin diabetes RCT 2024")
        lay.addWidget(self._ed_pubmed)
        btn = QPushButton(t("kms-import-pubmed-search"))
        btn.clicked.connect(self._on_pubmed)
        lay.addWidget(btn)
        self._lbl_pubmed_status = QLabel("")
        lay.addWidget(self._lbl_pubmed_status)
        lay.addStretch(1)
        return w

    def _on_pubmed(self) -> None:
        q = self._ed_pubmed.text().strip()
        if not q:
            return
        meta = fetch_pubmed(q)
        if not meta or not meta.get("title"):
            self._lbl_pubmed_status.setText(t("error-pubmed-not-found"))
            return
        if meta.get("doi"):
            res = import_by_doi(meta["doi"])
            if "error" in res:
                self._lbl_pubmed_status.setText(res["error"])
            else:
                self._lbl_pubmed_status.setText(t("kms-import-pdf-success", count=1))
                self._main.refresh_sidebar_stats()
        else:
            self._lbl_pubmed_status.setText(meta.get("title", "")[:120])

    # ----- Manual tab -------------------------------------------------
    def _build_manual_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._ed_title = QLineEdit()
        self._ed_authors = QLineEdit()
        self._ed_journal = QLineEdit()
        self._sp_year = QSpinBox()
        self._sp_year.setRange(1800, 2200)
        self._sp_year.setValue(datetime.now().year)
        self._ed_doi = QLineEdit()
        self._txt_abstract = QPlainTextEdit()
        form.addRow(t("kms-import-manual-title") + ":", self._ed_title)
        form.addRow(t("kms-import-manual-authors") + ":", self._ed_authors)
        form.addRow(t("kms-import-manual-journal") + ":", self._ed_journal)
        form.addRow(t("kms-import-manual-year") + ":", self._sp_year)
        form.addRow(t("kms-import-manual-doi") + ":", self._ed_doi)
        form.addRow(t("kms-import-manual-abstract") + ":", self._txt_abstract)
        btn = QPushButton(t("kms-import-manual-save"))
        btn.clicked.connect(self._on_manual_save)
        form.addRow("", btn)
        self._lbl_manual_status = QLabel("")
        form.addRow("", self._lbl_manual_status)
        return w

    def _on_manual_save(self) -> None:
        title = self._ed_title.text().strip()
        if not title:
            QMessageBox.warning(self, t("common-warning"), t("kms-import-manual-title"))
            return
        abstract = self._txt_abstract.toPlainText().strip()
        combined = f"{title} {abstract}"
        ev, sd, sp = classify_all(combined)
        pico = parse_pico_from_abstract(abstract)
        tags = auto_tag(abstract, "", abstract)
        import hashlib
        md5 = hashlib.md5(f"{title}{self._ed_doi.text()}".encode()).hexdigest()
        paper = {
            "md5":               md5,
            "original_filename": "(manual)",
            "title":             title,
            "authors":           self._ed_authors.text().strip(),
            "year":              self._sp_year.value(),
            "journal":           self._ed_journal.text().strip(),
            "doi":               self._ed_doi.text().strip(),
            "abstract":          abstract,
            "keywords":          "",
            "full_text":         abstract,
            "tags":              json.dumps(tags),
            "status":            "unread",
            "starred":           0,
            "pages":             0,
            "added_at":          datetime.now().strftime("%Y-%m-%d"),
            "file_path":         "",
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
                conn.execute(
                    "INSERT INTO papers ({c}) VALUES ({p})".format(
                        c=", ".join(paper.keys()),
                        p=", ".join(f":{k}" for k in paper),
                    ),
                    paper,
                )
            except Exception as e:
                self._lbl_manual_status.setText(str(e))
                return
        self._lbl_manual_status.setText(t("common-success"))
        self._ed_title.clear()
        self._ed_authors.clear()
        self._ed_journal.clear()
        self._ed_doi.clear()
        self._txt_abstract.clear()
        self._main.refresh_sidebar_stats()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        pass
