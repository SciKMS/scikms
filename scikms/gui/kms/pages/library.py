"""Library page — paginated paper list, inline filter strip, Fluent actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QSizePolicy,
    QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    CardWidget, CheckBox, ComboBox, FluentIcon, InfoBar, InfoBarPosition,
    MessageBox, PrimaryPushButton, PushButton, RoundMenu, SearchLineEdit,
    SpinBox, SubtitleLabel, TableWidget, TransparentPushButton,
    TransparentToolButton, CaptionLabel,
)

from scikms.i18n import t
from scikms.kms.config import (
    CLINICAL_SPECIALTIES, EBM_LEVELS, SORT_OPTIONS, STUDY_DESIGN_KEYWORDS,
)
from scikms.kms.db import (
    delete_paper, get_all_papers, get_all_projects, get_paper_by_id,
    get_papers_count, update_paper,
)

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


_ALL = "(All)"


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
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(SubtitleLabel(t("kms-library-title")))

        layout.addWidget(self._build_filter_card())

        self._table = TableWidget(self)
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "★", t("kms-import-manual-title"), t("kms-import-manual-authors"),
            t("kms-import-manual-year"), "EBM", t("sidebar-filter-status"),
            t("sidebar-filter-specialty"),
        ])
        self._table.verticalHeader().hide()
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.cellDoubleClicked.connect(self._on_open_paper)
        self._table.setBorderRadius(8)
        self._table.setBorderVisible(True)
        layout.addWidget(self._table, 1)

        nav = QHBoxLayout()
        self._lbl_info = CaptionLabel("")
        nav.addWidget(self._lbl_info)
        nav.addStretch(1)
        self._btn_prev = TransparentPushButton(FluentIcon.PAGE_LEFT, t("common-prev"))
        self._btn_prev.clicked.connect(self._on_prev)
        nav.addWidget(self._btn_prev)
        self._btn_next = TransparentPushButton(FluentIcon.PAGE_RIGHT, t("common-next"))
        self._btn_next.clicked.connect(self._on_next)
        self._btn_next.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        nav.addWidget(self._btn_next)
        layout.addLayout(nav)

        actions = QHBoxLayout()
        self._btn_open = PrimaryPushButton(FluentIcon.VIEW, t("kms-library-paper-open"))
        self._btn_open.clicked.connect(self._open_selected)
        actions.addWidget(self._btn_open)
        self._btn_star = PushButton(FluentIcon.HEART, t("kms-library-paper-star"))
        self._btn_star.clicked.connect(self._on_toggle_star)
        actions.addWidget(self._btn_star)
        self._btn_notes = PushButton(FluentIcon.EDIT, t("kms-library-paper-edit-notes"))
        self._btn_notes.clicked.connect(self._on_edit_notes)
        actions.addWidget(self._btn_notes)
        self._btn_delete = PushButton(FluentIcon.DELETE, t("kms-library-paper-delete"))
        self._btn_delete.clicked.connect(self._on_delete_paper)
        actions.addWidget(self._btn_delete)
        actions.addStretch(1)
        layout.addLayout(actions)

    def _build_filter_card(self) -> CardWidget:
        card = CardWidget(self)
        card.setBorderRadius(8)
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(8)

        # Top row: search + sort + page-size
        top = QHBoxLayout()
        self._ed_filter = SearchLineEdit(self)
        self._ed_filter.setPlaceholderText(t("common-search"))
        self._ed_filter.textChanged.connect(self._apply_and_render)
        top.addWidget(self._ed_filter, 1)

        top.addWidget(CaptionLabel(t("kms-library-sort") + ":"))
        self._cmb_sort = ComboBox(self)
        self._cmb_sort.addItems(SORT_OPTIONS)
        self._cmb_sort.currentIndexChanged.connect(self.refresh)
        top.addWidget(self._cmb_sort)

        top.addWidget(CaptionLabel(t("kms-library-page-size") + ":"))
        self._spn_size = SpinBox(self)
        self._spn_size.setRange(5, 200)
        self._spn_size.setValue(15)
        self._spn_size.valueChanged.connect(self._on_page_size)
        top.addWidget(self._spn_size)
        v.addLayout(top)

        # Bottom row: filter combos
        bot = QHBoxLayout()

        self._cmb_status = ComboBox(self)
        self._cmb_status.addItems([
            t("sidebar-filter-status-all"),
            t("sidebar-filter-status-unread"),
            t("sidebar-filter-status-reading"),
            t("sidebar-filter-status-read"),
        ])
        self._cmb_status.currentIndexChanged.connect(self._apply_and_render)
        bot.addWidget(CaptionLabel(t("sidebar-filter-status") + ":"))
        bot.addWidget(self._cmb_status)

        self._chk_starred = CheckBox(t("sidebar-filter-starred"), self)
        self._chk_starred.toggled.connect(self._apply_and_render)
        bot.addWidget(self._chk_starred)

        self._cmb_project = ComboBox(self)
        self._cmb_project.addItem(_ALL)
        self._cmb_project.currentIndexChanged.connect(self._apply_and_render)
        bot.addWidget(CaptionLabel(t("sidebar-filter-project") + ":"))
        bot.addWidget(self._cmb_project)

        self._cmb_evidence = ComboBox(self)
        self._cmb_evidence.addItem(_ALL)
        for level in ("I", "II", "III", "IV", "V"):
            self._cmb_evidence.addItem(level)
        self._cmb_evidence.currentIndexChanged.connect(self._apply_and_render)
        bot.addWidget(CaptionLabel(t("sidebar-filter-evidence") + ":"))
        bot.addWidget(self._cmb_evidence)

        self._cmb_design = ComboBox(self)
        self._cmb_design.addItem(_ALL)
        for design in STUDY_DESIGN_KEYWORDS:
            self._cmb_design.addItem(design)
        self._cmb_design.currentIndexChanged.connect(self._apply_and_render)
        bot.addWidget(CaptionLabel(t("sidebar-filter-design") + ":"))
        bot.addWidget(self._cmb_design)

        self._cmb_specialty = ComboBox(self)
        self._cmb_specialty.addItem(_ALL)
        self._cmb_specialty.addItems(CLINICAL_SPECIALTIES)
        self._cmb_specialty.currentIndexChanged.connect(self._apply_and_render)
        bot.addWidget(CaptionLabel(t("sidebar-filter-specialty") + ":"))
        bot.addWidget(self._cmb_specialty)

        bot.addStretch(1)
        v.addLayout(bot)
        return card

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._all_papers = get_all_papers(self._cmb_sort.currentText())
        self._refresh_projects()
        self._apply_and_render()

    def _refresh_projects(self) -> None:
        cur = self._cmb_project.currentText()
        self._cmb_project.blockSignals(True)
        self._cmb_project.clear()
        self._cmb_project.addItem(_ALL)
        for p in get_all_projects():
            self._cmb_project.addItem(p)
        idx = self._cmb_project.findText(cur)
        if idx >= 0:
            self._cmb_project.setCurrentIndex(idx)
        self._cmb_project.blockSignals(False)

    def _apply_and_render(self) -> None:
        rows = list(self._all_papers)
        status = ["all", "unread", "reading", "read"][self._cmb_status.currentIndex()]
        if status != "all":
            rows = [r for r in rows if r.get("status") == status]
        if self._chk_starred.isChecked():
            rows = [r for r in rows if r.get("starred")]
        if self._cmb_project.currentText() != _ALL:
            rows = [r for r in rows if r.get("project") == self._cmb_project.currentText()]
        if self._cmb_evidence.currentText() != _ALL:
            rows = [r for r in rows if r.get("evidence_level") == self._cmb_evidence.currentText()]
        if self._cmb_design.currentText() != _ALL:
            rows = [r for r in rows if r.get("study_design") == self._cmb_design.currentText()]
        if self._cmb_specialty.currentText() != _ALL:
            rows = [r for r in rows if r.get("clinical_specialty") == self._cmb_specialty.currentText()]

        q = self._ed_filter.text().strip().lower()
        if q:
            rows = [
                r for r in rows
                if q in (r.get("title") or "").lower()
                or q in (r.get("authors") or "").lower()
                or q in (r.get("notes") or "").lower()
            ]

        self._filtered = rows
        self._page = max(0, min(self._page, max(0, (len(rows) - 1) // self._page_size)))
        self._render_page()

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
            self._btn_prev.setEnabled(False)
            self._btn_next.setEnabled(False)
            return

        self._table.setRowCount(len(slice_))
        from PyQt6.QtWidgets import QTableWidgetItem
        for r, paper in enumerate(slice_):
            star = "★" if paper.get("starred") else "☆"
            cells = [
                star,
                paper.get("title") or t("common-untitled"),
                paper.get("authors") or "",
                str(paper.get("year") or ""),
                paper.get("evidence_level") or "",
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

    def _open_selected(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        self._open_paper(pid)

    def _on_open_paper(self, row: int, _col: int) -> None:
        if row < 0:
            return
        item = self._table.item(row, 0)
        if not item:
            return
        self._open_paper(int(item.data(Qt.ItemDataRole.UserRole)))

    def _open_paper(self, pid: int) -> None:
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
        box = MessageBox(t("common-confirm"), t("confirm-delete-paper"), self)
        if box.exec():
            delete_paper(pid)
            self.refresh()
            InfoBar.success(
                title=t("common-success"), content="",
                parent=self, position=InfoBarPosition.TOP_RIGHT, duration=2000,
            )

    def _on_context_menu(self, pos) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        menu = RoundMenu(parent=self._table)
        act_open = QAction(t("kms-library-paper-open"))
        act_open.triggered.connect(self._open_selected)
        menu.addAction(act_open)
        act_star = QAction(t("kms-library-paper-star"))
        act_star.triggered.connect(self._on_toggle_star)
        menu.addAction(act_star)
        act_notes = QAction(t("kms-library-paper-edit-notes"))
        act_notes.triggered.connect(self._on_edit_notes)
        menu.addAction(act_notes)
        menu.addSeparator()
        act_delete = QAction(t("kms-library-paper-delete"))
        act_delete.triggered.connect(self._on_delete_paper)
        menu.addAction(act_delete)
        menu.exec(self._table.viewport().mapToGlobal(pos))
