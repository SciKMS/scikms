"""Import page — Fluent Pivot tabs, InfoBar toasts, Fluent ProgressBar."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView, QFileDialog, QFormLayout, QHBoxLayout, QListWidget,
    QStackedWidget, QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    BodyLabel, CardWidget, CheckBox, FluentIcon, InfoBar, InfoBarPosition,
    LineEdit, Pivot, PlainTextEdit, PrimaryPushButton, ProgressBar, PushButton,
    SpinBox, StrongBodyLabel, SubtitleLabel, CaptionLabel,
)

from scikms.i18n import t
from scikms.kms.clinical import (
    auto_tag, build_renamed_filename, classify_all, parse_pico_from_abstract,
)
from scikms.kms.db import db_conn
from scikms.kms.importers import fetch_pubmed, import_by_doi, process_pdf_bytes

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


class _PdfImportWorker(QThread):
    progress = pyqtSignal(int, int, str)
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
                res = {"error": str(e)}
            self.finished_one.emit(res)


class ImportPage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._worker: _PdfImportWorker | None = None
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(SubtitleLabel(t("kms-import-title")))
        layout.addWidget(CaptionLabel(t("kms-import-pdf-help")))

        self._pivot = Pivot(self)
        self._stack = QStackedWidget(self)

        tabs = [
            ("pdf",    t("kms-import-tab-pdf"),    self._build_pdf_tab),
            ("doi",    t("kms-import-tab-doi"),    self._build_doi_tab),
            ("pubmed", t("kms-import-tab-pubmed"), self._build_pubmed_tab),
            ("manual", t("kms-import-tab-manual"), self._build_manual_tab),
        ]
        for key, label, builder in tabs:
            w = builder()
            w.setObjectName(f"import-{key}")
            self._stack.addWidget(w)
            self._pivot.addItem(routeKey=key, text=label, onClick=lambda _checked=False, k=key: self._switch(k))

        self._pivot.setCurrentItem(tabs[0][0])
        layout.addWidget(self._pivot)
        layout.addWidget(self._stack, 1)

    def _switch(self, key: str) -> None:
        for i in range(self._stack.count()):
            if self._stack.widget(i).objectName() == f"import-{key}":
                self._stack.setCurrentIndex(i)
                return

    # ----- PDF tab -----------------------------------------------------
    def _build_pdf_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        row = QHBoxLayout()
        self._btn_pick = PrimaryPushButton(FluentIcon.FOLDER_ADD, t("kms-import-pdf-pick"))
        self._btn_pick.clicked.connect(self._on_pick_pdfs)
        row.addWidget(self._btn_pick)
        self._btn_remove = PushButton(FluentIcon.REMOVE, t("kms-import-pdf-remove"))
        self._btn_remove.clicked.connect(self._on_remove_selected)
        self._btn_remove.setEnabled(False)
        row.addWidget(self._btn_remove)
        self._btn_clear = PushButton(FluentIcon.DELETE, t("kms-import-pdf-clear"))
        self._btn_clear.clicked.connect(self._on_clear_files)
        self._btn_clear.setEnabled(False)
        row.addWidget(self._btn_clear)
        self._chk_extract = CheckBox(t("kms-import-pdf-extract-images"))
        self._chk_extract.setChecked(True)
        row.addWidget(self._chk_extract)
        row.addStretch(1)
        lay.addLayout(row)

        self._lst_files = QListWidget()
        self._lst_files.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._lst_files.itemSelectionChanged.connect(self._sync_file_buttons)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self._lst_files,
                  activated=self._on_remove_selected)
        QShortcut(QKeySequence(Qt.Key.Key_Backspace), self._lst_files,
                  activated=self._on_remove_selected)
        lay.addWidget(self._lst_files, 1)

        self._btn_process = PrimaryPushButton(FluentIcon.PLAY, t("kms-import-pdf-process", count=0))
        self._btn_process.clicked.connect(self._on_process_pdfs)
        self._btn_process.setEnabled(False)
        lay.addWidget(self._btn_process)

        self._progress = ProgressBar(w)
        self._progress.setVisible(False)
        lay.addWidget(self._progress)

        self._lbl_pdf_status = CaptionLabel("")
        lay.addWidget(self._lbl_pdf_status)
        return w

    def _on_pick_pdfs(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, t("kms-import-pdf-pick"), "", "PDF (*.pdf)")
        if not paths:
            return
        existing = {self._lst_files.item(i).text()
                    for i in range(self._lst_files.count())}
        for p in paths:
            if p not in existing:
                self._lst_files.addItem(p)
        self._sync_file_buttons()

    def _on_remove_selected(self) -> None:
        for item in self._lst_files.selectedItems():
            self._lst_files.takeItem(self._lst_files.row(item))
        self._sync_file_buttons()

    def _on_clear_files(self) -> None:
        self._lst_files.clear()
        self._sync_file_buttons()

    def _sync_file_buttons(self) -> None:
        count = self._lst_files.count()
        self._btn_process.setText(t("kms-import-pdf-process", count=count))
        self._btn_process.setEnabled(count > 0 and self._worker is None)
        self._btn_clear.setEnabled(count > 0)
        self._btn_remove.setEnabled(bool(self._lst_files.selectedItems()))

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
        self._sync_file_buttons()
        InfoBar.success(
            title=t("kms-import-pdf-success", count=self._success),
            content=t("kms-import-pdf-failed", count=self._failed) if self._failed else "",
            parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000,
        )

    # ----- DOI tab -----------------------------------------------------
    def _build_doi_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.addWidget(BodyLabel(t("kms-import-doi-prompt")))
        self._txt_dois = PlainTextEdit(w)
        self._txt_dois.setPlaceholderText("10.1056/NEJMoa2034577\n10.1016/j.lancet.2020.11.001")
        lay.addWidget(self._txt_dois, 1)
        self._chk_oa = CheckBox(t("kms-import-doi-download-pdf"))
        lay.addWidget(self._chk_oa)
        btn = PrimaryPushButton(FluentIcon.CLOUD_DOWNLOAD, t("kms-import-doi-fetch"))
        btn.clicked.connect(self._on_fetch_doi)
        lay.addWidget(btn)
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
        (InfoBar.success if ok and not fail else InfoBar.warning)(
            title=t("kms-import-pdf-success", count=ok),
            content=t("kms-import-pdf-failed", count=fail) if fail else "",
            parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000,
        )

    # ----- PubMed tab -------------------------------------------------
    def _build_pubmed_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.addWidget(BodyLabel(t("kms-import-pubmed-prompt")))
        self._ed_pubmed = LineEdit(w)
        self._ed_pubmed.setPlaceholderText("e.g., metformin diabetes RCT 2024")
        lay.addWidget(self._ed_pubmed)
        btn = PrimaryPushButton(FluentIcon.SEARCH, t("kms-import-pubmed-search"))
        btn.clicked.connect(self._on_pubmed)
        lay.addWidget(btn)
        lay.addStretch(1)
        return w

    def _on_pubmed(self) -> None:
        q = self._ed_pubmed.text().strip()
        if not q:
            return
        meta = fetch_pubmed(q)
        if not meta or not meta.get("title"):
            InfoBar.error(title=t("error-pubmed-not-found"), content="",
                          parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000)
            return
        if meta.get("doi"):
            res = import_by_doi(meta["doi"])
            if "error" in res:
                InfoBar.error(title=res["error"], content="",
                              parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000)
            else:
                InfoBar.success(title=t("kms-import-pdf-success", count=1), content="",
                                parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000)
        else:
            InfoBar.info(title=meta.get("title", "")[:120], content="",
                         parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000)

    # ----- Manual tab -------------------------------------------------
    def _build_manual_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)
        self._ed_title = LineEdit(w)
        self._ed_authors = LineEdit(w)
        self._ed_journal = LineEdit(w)
        self._sp_year = SpinBox(w)
        self._sp_year.setRange(1800, 2200)
        self._sp_year.setValue(datetime.now().year)
        self._ed_doi = LineEdit(w)
        self._txt_abstract = PlainTextEdit(w)
        form.addRow(t("kms-import-manual-title") + ":", self._ed_title)
        form.addRow(t("kms-import-manual-authors") + ":", self._ed_authors)
        form.addRow(t("kms-import-manual-journal") + ":", self._ed_journal)
        form.addRow(t("kms-import-manual-year") + ":", self._sp_year)
        form.addRow(t("kms-import-manual-doi") + ":", self._ed_doi)
        form.addRow(t("kms-import-manual-abstract") + ":", self._txt_abstract)
        btn = PrimaryPushButton(FluentIcon.SAVE, t("kms-import-manual-save"))
        btn.clicked.connect(self._on_manual_save)
        form.addRow("", btn)
        return w

    def _on_manual_save(self) -> None:
        title = self._ed_title.text().strip()
        if not title:
            InfoBar.warning(title=t("kms-import-manual-title"), content="",
                            parent=self, position=InfoBarPosition.TOP_RIGHT, duration=2000)
            return
        abstract = self._txt_abstract.toPlainText().strip()
        combined = f"{title} {abstract}"
        ev, sd, sp = classify_all(combined)
        pico = parse_pico_from_abstract(abstract)
        tags = auto_tag(abstract, "", abstract)
        import hashlib
        md5 = hashlib.md5(f"{title}{self._ed_doi.text()}".encode()).hexdigest()
        paper = {
            "md5": md5, "original_filename": "(manual)", "title": title,
            "authors": self._ed_authors.text().strip(), "year": self._sp_year.value(),
            "journal": self._ed_journal.text().strip(), "doi": self._ed_doi.text().strip(),
            "abstract": abstract, "keywords": "", "full_text": abstract,
            "tags": json.dumps(tags), "status": "unread", "starred": 0, "pages": 0,
            "added_at": datetime.now().strftime("%Y-%m-%d"), "file_path": "",
            "notes": "", "highlights": "[]", "project": "", "reading_position": 0,
            "evidence_level": ev, "study_design": sd, "clinical_specialty": sp,
            "pico_json": json.dumps(pico), "risk_of_bias_json": "{}",
            "impact_factor": 0.0, "citation_count": 0,
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
                InfoBar.error(title=t("common-error"), content=str(e),
                              parent=self, position=InfoBarPosition.TOP_RIGHT, duration=4000)
                return
        InfoBar.success(title=t("common-success"), content=title[:80],
                        parent=self, position=InfoBarPosition.TOP_RIGHT, duration=2500)
        self._ed_title.clear()
        self._ed_authors.clear()
        self._ed_journal.clear()
        self._ed_doi.clear()
        self._txt_abstract.clear()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        pass
