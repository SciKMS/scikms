"""Library page — Frontiers-style card grid with inline filter rail.

Layout:
  Row 1 — count ("N bài báo") on the left, search + sort on the right.
  Row 2 — inline filter combos (status / starred / project / EBM / design /
          specialty) and page-size selector.
  Body  — scrollable 3-column grid of PaperCard widgets. Cards stretch with
          the viewport so the grid stays responsive under window resize /
          display zoom.
  Footer — pagination nav.

Click a card to open the PDF, right-click for contextual actions (star, edit
notes, delete). A small star button in the card's top-right toggles starred
without opening the paper.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QGridLayout, QHBoxLayout, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    BodyLabel, CaptionLabel, CardWidget, CheckBox, ComboBox, FluentIcon,
    InfoBar, InfoBarPosition, MessageBox, RoundMenu, SearchLineEdit, SpinBox,
    StrongBodyLabel, TransparentPushButton, TransparentToolButton,
)

from scikms.gui.kms.shared import PageHeader
from scikms.i18n import t
from scikms.kms.config import (
    CLINICAL_SPECIALTIES, SORT_OPTIONS, STUDY_DESIGN_KEYWORDS,
)
from scikms.kms.db import (
    delete_paper, get_all_papers, get_all_projects, get_paper_by_id,
    get_papers_count, update_paper,
)

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


_ALL = "(All)"
_GRID_COLS = 3
_CARD_MIN_W = 240
_TITLE_MAX_CHARS = 120
_ABSTRACT_MAX_CHARS = 200

_STATUS_STYLE = {
    "unread":  ("#d1d5db", "#4b5563"),   # grey
    "reading": ("#fed7aa", "#c2410c"),   # amber
    "read":    ("#bbf7d0", "#166534"),   # green
}


# ---------------------------------------------------------------------------
# PaperCard — one paper rendered as a Frontiers-style card.
# ---------------------------------------------------------------------------
def _chip(text: str, fg: str = "#4338CA", bg: str = "rgba(67,56,202,0.12)") -> CaptionLabel:
    lbl = CaptionLabel(text)
    lbl.setStyleSheet(
        f"padding: 2px 8px; border-radius: 10px; "
        f"background: {bg}; color: {fg};"
    )
    return lbl


def _status_chip(status: str) -> CaptionLabel:
    bg, fg = _STATUS_STYLE.get(status, _STATUS_STYLE["unread"])
    label_key = f"kms-library-paper-status-{status}" if status in {
        "unread", "reading", "read"} else "kms-library-paper-status-unread"
    return _chip(t(label_key), fg=fg, bg=bg)


class PaperCard(CardWidget):
    open_requested = pyqtSignal(int)
    star_toggled = pyqtSignal(int)
    menu_requested = pyqtSignal(int, QPoint)

    def __init__(self, paper: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._paper_id: int = int(paper["id"])
        self.setBorderRadius(10)
        self.setMinimumWidth(_CARD_MIN_W)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        # --- Title row with star + menu buttons in the corner -----------
        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        raw_title = paper.get("title") or t("common-untitled")
        title_text = raw_title if len(raw_title) <= _TITLE_MAX_CHARS \
            else raw_title[: _TITLE_MAX_CHARS - 1].rstrip() + "…"
        title = StrongBodyLabel(title_text)
        title.setWordWrap(True)
        # Reserve 2 lines so short and long titles share the same baseline
        # and rows stay aligned regardless of title length.
        title.setMinimumHeight(44)
        title.setMaximumHeight(48)
        title.setToolTip(raw_title)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        top_row.addWidget(title, 1)

        starred_now = bool(paper.get("starred"))
        self._btn_star = TransparentPushButton("★" if starred_now else "☆")
        self._btn_star.setStyleSheet(
            "font-size: 16px; padding: 0 6px;"
            + (" color: #f59e0b;" if starred_now else "")
        )
        self._btn_star.setToolTip(t(
            "kms-library-paper-unstar" if starred_now else "kms-library-paper-star"
        ))
        self._btn_star.clicked.connect(
            lambda: self.star_toggled.emit(self._paper_id)
        )
        top_row.addWidget(self._btn_star, 0, Qt.AlignmentFlag.AlignTop)

        self._btn_menu = TransparentToolButton(FluentIcon.MORE)
        self._btn_menu.clicked.connect(self._emit_menu)
        top_row.addWidget(self._btn_menu, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(top_row)

        # --- Chip row: EBM + study design -------------------------------
        chips = QHBoxLayout()
        chips.setSpacing(4)
        ev = paper.get("evidence_level")
        if ev:
            chips.addWidget(_chip(f"EBM {ev}"))
        sd = paper.get("study_design")
        if sd:
            chips.addWidget(_chip(sd, fg="#0f766e", bg="rgba(20,184,166,0.14)"))
        chips.addStretch(1)
        if chips.count() > 1:  # has at least one chip + the stretch
            lay.addLayout(chips)

        # --- Authors (muted) --------------------------------------------
        authors = (paper.get("authors") or "").strip()
        if authors:
            # Authors: split on ";" then join with middle-dot for Frontiers feel.
            parts = [a.strip() for a in authors.split(";") if a.strip()]
            shown = " · ".join(parts[:3])
            if len(parts) > 3:
                shown += f"  (+{len(parts) - 3})"
            lbl = CaptionLabel(shown)
            lbl.setWordWrap(True)
            lay.addWidget(lbl)

        # --- Abstract snippet -------------------------------------------
        abstract = (paper.get("abstract") or "").strip()
        if abstract:
            shown = (abstract[: _ABSTRACT_MAX_CHARS - 1].rstrip() + "…") \
                if len(abstract) > _ABSTRACT_MAX_CHARS else abstract
            snip = CaptionLabel(shown)
            snip.setWordWrap(True)
            snip.setStyleSheet("opacity: 0.72;")
            # ~3 lines so all cards share a consistent body block and the row
            # heights in the grid stay even across short/long abstracts.
            snip.setMinimumHeight(54)
            snip.setMaximumHeight(58)
            snip.setToolTip(abstract[:600])
            snip.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            lay.addWidget(snip)

        # --- Meta row: year · journal | specialty -----------------------
        year = paper.get("year") or "?"
        journal = (paper.get("journal") or "").strip()
        specialty = (paper.get("clinical_specialty") or "").strip()
        meta_parts = [str(year)]
        if journal:
            meta_parts.append(journal)
        meta = " · ".join(meta_parts)
        if specialty:
            meta += f"  |  {specialty}"
        lay.addWidget(CaptionLabel(meta))

        # --- Bottom stats row -------------------------------------------
        stats = QHBoxLayout()
        stats.setSpacing(6)
        stats.addWidget(_status_chip(paper.get("status") or "unread"))
        pages = paper.get("pages") or 0
        if pages:
            stats.addWidget(CaptionLabel(f"📄 {pages}"))
        notes = (paper.get("notes") or "").strip()
        if notes:
            stats.addWidget(CaptionLabel("📝"))
        stats.addStretch(1)
        lay.addLayout(stats)

    # -- Event handling --------------------------------------------------
    def _emit_menu(self) -> None:
        self.menu_requested.emit(
            self._paper_id,
            self._btn_menu.mapToGlobal(self._btn_menu.rect().bottomLeft()),
        )

    def mouseReleaseEvent(self, e) -> None:
        super().mouseReleaseEvent(e)
        if e.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit(self._paper_id)

    def contextMenuEvent(self, e) -> None:
        self.menu_requested.emit(self._paper_id, e.globalPos())


# ---------------------------------------------------------------------------
# LibraryPage
# ---------------------------------------------------------------------------
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
        layout.setSpacing(10)

        layout.addWidget(PageHeader(t("kms-library-title")))
        layout.addWidget(self._build_filter_card())

        # Scroll area hosting a fixed-width 3-column grid. Columns share equal
        # stretch so cards grow/shrink proportionally with the viewport — this
        # is what keeps the layout responsive under window resize / OS zoom.
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(14)
        self._grid.setVerticalSpacing(14)
        for c in range(_GRID_COLS):
            self._grid.setColumnStretch(c, 1)
        self._scroll.setWidget(self._grid_host)
        layout.addWidget(self._scroll, 1)

        # Empty-state label sits inside the scroll area when no cards exist.
        self._lbl_empty = BodyLabel("", self)
        self._lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_empty.setStyleSheet("opacity: 0.6; padding: 48px;")
        self._lbl_empty.hide()
        layout.addWidget(self._lbl_empty)

        # Pagination footer
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

    def _build_filter_card(self) -> CardWidget:
        card = CardWidget(self)
        card.setBorderRadius(8)
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(10)

        # Row 1 — count + search + sort
        top = QHBoxLayout()
        top.setSpacing(10)
        self._lbl_count = StrongBodyLabel("")
        top.addWidget(self._lbl_count)
        top.addSpacing(12)
        self._ed_filter = SearchLineEdit(self)
        self._ed_filter.setPlaceholderText(t("common-search"))
        self._ed_filter.textChanged.connect(self._apply_and_render)
        top.addWidget(self._ed_filter, 1)

        top.addWidget(CaptionLabel(t("kms-library-sort") + ":"))
        self._cmb_sort = ComboBox(self)
        self._cmb_sort.addItems(SORT_OPTIONS)
        self._cmb_sort.currentIndexChanged.connect(self.refresh)
        top.addWidget(self._cmb_sort)
        v.addLayout(top)

        # Row 2 — all inline filters
        bot = QHBoxLayout()
        bot.setSpacing(8)

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
        bot.addWidget(CaptionLabel(t("kms-library-page-size") + ":"))
        self._spn_size = SpinBox(self)
        self._spn_size.setRange(6, 200)
        self._spn_size.setValue(self._page_size)
        self._spn_size.valueChanged.connect(self._on_page_size)
        bot.addWidget(self._spn_size)
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
        self._lbl_count.setText(t("kms-library-count", count=len(rows)))
        self._page = max(0, min(self._page, max(0, (len(rows) - 1) // self._page_size)))
        self._render_page()

    def _render_page(self) -> None:
        self._clear_grid()
        total = len(self._filtered)

        if total == 0:
            self._lbl_empty.setText(
                t("kms-library-empty") if not get_papers_count()
                else t("kms-library-no-match")
            )
            self._lbl_empty.show()
            self._scroll.hide()
            self._lbl_info.setText("")
            self._btn_prev.setEnabled(False)
            self._btn_next.setEnabled(False)
            return

        self._lbl_empty.hide()
        self._scroll.show()

        start = self._page * self._page_size
        end = min(start + self._page_size, total)
        for i, paper in enumerate(self._filtered[start:end]):
            card = PaperCard(paper, self._grid_host)
            card.open_requested.connect(self._open_paper)
            card.star_toggled.connect(self._on_star_toggled)
            card.menu_requested.connect(self._on_card_menu)
            row, col = divmod(i, _GRID_COLS)
            self._grid.addWidget(card, row, col)

        self._lbl_info.setText(
            t("kms-library-page-info", start=start + 1, end=end, total=total)
        )
        self._btn_prev.setEnabled(self._page > 0)
        self._btn_next.setEnabled(end < total)

    def _clear_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

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

    # -- Card actions ---------------------------------------------------
    def _open_paper(self, pid: int) -> None:
        paper = get_paper_by_id(pid)
        if not paper:
            return
        from scikms.gui.kms.dialogs.pdf_viewer import PdfViewerDialog
        PdfViewerDialog(paper, self).exec()

    def _on_star_toggled(self, pid: int) -> None:
        paper = get_paper_by_id(pid)
        if not paper:
            return
        update_paper(pid, {"starred": 0 if paper.get("starred") else 1})
        self.refresh()

    def _on_edit_notes(self, pid: int) -> None:
        from scikms.gui.kms.dialogs.note_editor import NoteEditorDialog
        if NoteEditorDialog(pid, self).exec():
            self.refresh()

    def _on_delete_paper(self, pid: int) -> None:
        box = MessageBox(t("common-confirm"), t("confirm-delete-paper"), self)
        if box.exec():
            delete_paper(pid)
            self.refresh()
            InfoBar.success(
                title=t("common-success"), content="",
                parent=self, position=InfoBarPosition.TOP_RIGHT, duration=2000,
            )

    def _on_card_menu(self, pid: int, global_pos: QPoint) -> None:
        menu = RoundMenu(parent=self)
        act_open = QAction(t("kms-library-paper-open"))
        act_open.triggered.connect(lambda _=False, p=pid: self._open_paper(p))
        menu.addAction(act_open)
        act_star = QAction(t("kms-library-paper-star"))
        act_star.triggered.connect(lambda _=False, p=pid: self._on_star_toggled(p))
        menu.addAction(act_star)
        act_notes = QAction(t("kms-library-paper-edit-notes"))
        act_notes.triggered.connect(lambda _=False, p=pid: self._on_edit_notes(p))
        menu.addAction(act_notes)
        menu.addSeparator()
        act_delete = QAction(t("kms-library-paper-delete"))
        act_delete.triggered.connect(lambda _=False, p=pid: self._on_delete_paper(p))
        menu.addAction(act_delete)
        menu.exec(global_pos)
