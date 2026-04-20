"""Library page — paginated paper list with filters and bulk actions."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton, QSpinBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QComboBox,
)

from scikms.i18n import t
from scikms.kms.config import EBM_LEVELS, SORT_OPTIONS
from scikms.kms.db import (
    delete_paper, get_all_papers, get_paper_by_id, get_papers_count, update_paper,
)

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


_PAGE_SIZE_OPTIONS = [10, 15, 25, 50, 100]


class LibraryPage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._page = 0
        self._page_size = 15
        self._all_papers: list[dict] = []
        self._filtered: list[dict] = []
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel(f"<h2>{t('kms-library-title')}</h2>")
        title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel(t("kms-library-sort") + ":"))
        self._cmb_sort = QComboBox()
        self._cmb_sort.addItems(SORT_OPTIONS)
        self._cmb_sort.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self._cmb_sort)
        toolbar.addSpacing(20)
        toolbar.addWidget(QLabel(t("kms-library-page-size") + ":"))
        self._spn_size = QSpinBox()
        self._spn_size.setRange(5, 200)
        self._spn_size.setValue(15)
        self._spn_size.valueChanged.connect(self._on_page_size)
        toolbar.addWidget(self._spn_size)
        toolbar.addStretch(1)
        self._btn_refresh = QPushButton(t("common-refresh"))
        self._btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(self._btn_refresh)
        layout.addLayout(toolbar)

        self._table = QTableWidget(0, 7, self)
        self._table.setHorizontalHeaderLabels([
            "★", t("kms-import-manual-title"), t("kms-import-manual-authors"),
            t("kms-import-manual-year"), "EBM", t("sidebar-filter-status"),
            t("sidebar-filter-specialty"),
        ])
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.cellDoubleClicked.connect(self._on_open_paper)
        layout.addWidget(self._table, 1)

        nav = QHBoxLayout()
        self._lbl_info = QLabel("")
        nav.addWidget(self._lbl_info)
        nav.addStretch(1)
        self._btn_prev = QPushButton("◀ " + t("common-prev"))
        self._btn_prev.clicked.connect(self._on_prev)
        nav.addWidget(self._btn_prev)
        self._btn_next = QPushButton(t("common-next") + " ▶")
        self._btn_next.clicked.connect(self._on_next)
        nav.addWidget(self._btn_next)
        layout.addLayout(nav)

        actions = QHBoxLayout()
        self._btn_open = QPushButton(t("kms-library-paper-open"))
        self._btn_open.clicked.connect(lambda: self._on_open_paper(self._table.currentRow(), 0))
        actions.addWidget(self._btn_open)
        self._btn_star = QPushButton(t("kms-library-paper-star"))
        self._btn_star.clicked.connect(self._on_toggle_star)
        actions.addWidget(self._btn_star)
        self._btn_notes = QPushButton(t("kms-library-paper-edit-notes"))
        self._btn_notes.clicked.connect(self._on_edit_notes)
        actions.addWidget(self._btn_notes)
        self._btn_delete = QPushButton(t("kms-library-paper-delete"))
        self._btn_delete.clicked.connect(self._on_delete_paper)
        actions.addWidget(self._btn_delete)
        actions.addStretch(1)
        layout.addLayout(actions)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._all_papers = get_all_papers(self._cmb_sort.currentText())
        self._apply_filters()
        self._render_page()
        self._main.refresh_sidebar_stats()

    def _apply_filters(self) -> None:
        f = self._main.current_filters()
        rows = list(self._all_papers)
        if f["status"] != "all":
            rows = [r for r in rows if r.get("status") == f["status"]]
        if f["starred"]:
            rows = [r for r in rows if r.get("starred")]
        if f["project"]:
            rows = [r for r in rows if r.get("project") == f["project"]]
        if f["evidence"]:
            rows = [r for r in rows if r.get("evidence_level") == f["evidence"]]
        if f["design"]:
            rows = [r for r in rows if r.get("study_design") == f["design"]]
        if f["specialty"]:
            rows = [r for r in rows if r.get("clinical_specialty") == f["specialty"]]
        self._filtered = rows
        self._page = max(0, min(self._page, max(0, (len(rows) - 1) // self._page_size)))

    def _render_page(self) -> None:
        total = len(self._filtered)
        start = self._page * self._page_size
        end = min(start + self._page_size, total)
        slice_ = self._filtered[start:end]

        if total == 0:
            self._table.setRowCount(0)
            self._lbl_info.setText(
                t("kms-library-empty") if not get_papers_count() else t("kms-library-no-match")
            )
            return

        self._table.setRowCount(len(slice_))
        for r, paper in enumerate(slice_):
            star = "★" if paper.get("starred") else "☆"
            ev_label = ""
            ev = paper.get("evidence_level") or ""
            if ev:
                ev_label = ev
            cells = [
                star,
                paper.get("title") or t("common-untitled"),
                paper.get("authors") or "",
                str(paper.get("year") or ""),
                ev_label,
                paper.get("status") or "",
                paper.get("clinical_specialty") or "",
            ]
            for c, val in enumerate(cells):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, paper["id"])
                self._table.setItem(r, c, item)

        self._lbl_info.setText(
            t("kms-library-page-info", start=start + 1, end=end, total=total)
        )
        self._btn_prev.setEnabled(self._page > 0)
        self._btn_next.setEnabled(end < total)

    # ------------------------------------------------------------------
    def _on_prev(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._render_page()

    def _on_next(self) -> None:
        if (self._page + 1) * self._page_size < len(self._filtered):
            self._page += 1
            self._render_page()

    def _on_page_size(self, val: int) -> None:
        self._page_size = val
        self._page = 0
        self._render_page()

    def _selected_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        if not item:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def _on_open_paper(self, row: int, _col: int) -> None:
        if row < 0:
            return
        item = self._table.item(row, 0)
        if not item:
            return
        pid = int(item.data(Qt.ItemDataRole.UserRole))
        paper = get_paper_by_id(pid)
        if not paper:
            return
        from scikms.gui.kms.dialogs.pdf_viewer import PdfViewerDialog
        PdfViewerDialog(paper, self).exec()

    def _on_toggle_star(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        paper = get_paper_by_id(pid)
        if not paper:
            return
        update_paper(pid, {"starred": 0 if paper.get("starred") else 1})
        self.refresh()

    def _on_edit_notes(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        from scikms.gui.kms.dialogs.note_editor import NoteEditorDialog
        if NoteEditorDialog(pid, self).exec():
            self.refresh()

    def _on_delete_paper(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        ans = QMessageBox.question(
            self, t("common-confirm"), t("confirm-delete-paper"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            delete_paper(pid)
            self.refresh()
