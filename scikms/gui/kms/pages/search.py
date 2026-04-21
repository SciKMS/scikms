"""Search page — FTS5 dual-channel search with Fluent search box + template chips."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QHBoxLayout, QHeaderView, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel, CardWidget, CaptionLabel, ComboBox, FluentIcon, PrimaryPushButton,
    PushButton, SearchLineEdit, StrongBodyLabel, TableWidget,
    TransparentPushButton,
)

from scikms.gui.kms.shared import PageHeader
from scikms.i18n import t
from scikms.kms.config import SEARCH_TEMPLATES
from scikms.kms.db import get_paper_by_id, search_papers

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


class SearchPage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._results: list[dict] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(PageHeader(t("kms-search-title")))

        bar = QHBoxLayout()
        self._ed_query = SearchLineEdit(self)
        self._ed_query.setPlaceholderText(t("kms-search-prompt"))
        self._ed_query.searchSignal.connect(lambda _q: self._on_search())
        self._ed_query.returnPressed.connect(self._on_search)
        bar.addWidget(self._ed_query, 1)

        bar.addWidget(CaptionLabel(t("kms-search-scope") + ":"))
        self._cmb_scope = ComboBox(self)
        for label_key, data in [
            ("sidebar-filter-scope-all", "all"),
            ("sidebar-filter-scope-title-abstract", "title_abstract"),
            ("sidebar-filter-scope-notes", "notes"),
            ("sidebar-filter-scope-content", "fulltext"),
        ]:
            self._cmb_scope.addItem(t(label_key), userData=data)
        bar.addWidget(self._cmb_scope)

        btn = PrimaryPushButton(FluentIcon.SEARCH, t("kms-search-button"))
        btn.clicked.connect(self._on_search)
        bar.addWidget(btn)
        layout.addLayout(bar)

        tpl_card = CardWidget(self)
        tpl_card.setBorderRadius(8)
        tpl_lay = QVBoxLayout(tpl_card)
        tpl_lay.setContentsMargins(12, 10, 12, 10)
        tpl_lay.setSpacing(6)
        tpl_lay.addWidget(StrongBodyLabel(t("kms-search-templates")))
        chips = QHBoxLayout()
        chips.setSpacing(6)
        for label, q in SEARCH_TEMPLATES:
            b = TransparentPushButton(FluentIcon.TAG, label)
            b.clicked.connect(lambda _checked=False, query=q: self._run_query(query))
            chips.addWidget(b)
        chips.addStretch(1)
        tpl_lay.addLayout(chips)
        layout.addWidget(tpl_card)

        self._lbl_count = CaptionLabel("")
        layout.addWidget(self._lbl_count)
        self._lbl_breakdown = CaptionLabel("")
        layout.addWidget(self._lbl_breakdown)

        self._table = TableWidget(self)
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            t("kms-import-manual-title"), t("kms-import-manual-authors"),
            t("kms-import-manual-year"), "EBM", t("sidebar-filter-search-scope"),
            t("sidebar-filter-specialty"),
        ])
        self._table.verticalHeader().hide()
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.cellDoubleClicked.connect(self._on_open_paper)
        self._table.setBorderRadius(8)
        self._table.setBorderVisible(True)
        layout.addWidget(self._table, 1)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        if self._ed_query.text().strip():
            self._on_search()

    def _run_query(self, q: str) -> None:
        self._ed_query.setText(q)
        self._on_search()

    def _on_search(self) -> None:
        q = self._ed_query.text().strip()
        scope = self._cmb_scope.currentData() or "all"
        if not q:
            return
        self._results = search_papers(q, scope=scope)
        self._lbl_count.setText(t("kms-search-results-count", count=len(self._results)))
        self._render_breakdown()
        self._render_table()

    def _render_breakdown(self) -> None:
        if not self._results:
            self._lbl_breakdown.setText(t("kms-search-no-results"))
            return
        counts = {"I": 0, "II": 0, "III": 0, "IV": 0, "V": 0, "": 0}
        for p in self._results:
            counts[p.get("evidence_level") or ""] = counts.get(p.get("evidence_level") or "", 0) + 1
        parts = [t("kms-search-evidence-breakdown") + ":"]
        for level in ("I", "II", "III", "IV", "V"):
            parts.append(f"{level}={counts[level]}")
        if counts[""]:
            parts.append(f"?={counts['']}")
        self._lbl_breakdown.setText("  ·  ".join(parts))

    def _render_table(self) -> None:
        from PyQt6.QtWidgets import QTableWidgetItem
        self._table.setRowCount(len(self._results))
        for r, paper in enumerate(self._results):
            cells = [
                paper.get("title") or t("common-untitled"),
                paper.get("authors") or "",
                str(paper.get("year") or ""),
                paper.get("evidence_level") or "",
                paper.get("_match_scope") or "",
                paper.get("clinical_specialty") or "",
            ]
            for c, val in enumerate(cells):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, paper["id"])
                self._table.setItem(r, c, item)

    def _on_open_paper(self, row: int, _col: int) -> None:
        if row < 0:
            return
        item = self._table.item(row, 0)
        if not item:
            return
        pid = int(item.data(Qt.ItemDataRole.UserRole))
        paper = get_paper_by_id(pid)
        if paper:
            from scikms.gui.kms.dialogs.pdf_viewer import PdfViewerDialog
            PdfViewerDialog(paper, self).exec()
