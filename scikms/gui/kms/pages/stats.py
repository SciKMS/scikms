"""Stats page — EBM pyramid, study design, specialty, timeline, tags.

Uses Fluent CardWidget tiles for headline metrics and TableWidget for
distribution tables.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QGridLayout, QHBoxLayout, QHeaderView, QScrollArea,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    CardWidget, CaptionLabel, FluentIcon, IconWidget, StrongBodyLabel,
    SubtitleLabel, TableWidget,
)

from scikms.gui.kms.shared import BoundedRow, EmptyStatePanel, PageHeader
from scikms.i18n import t
from scikms.kms.atlas import atlas_count
from scikms.kms.db import get_all_papers, get_db_stats

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


class _MetricTile(CardWidget):
    """Small tile: icon + number + label."""

    def __init__(self, icon: FluentIcon, label: str, parent=None) -> None:
        super().__init__(parent)
        self.setBorderRadius(10)
        self.setFixedHeight(92)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed,
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(12)
        self._icon = IconWidget(icon, self)
        self._icon.setFixedSize(28, 28)
        lay.addWidget(self._icon)
        txt = QVBoxLayout()
        txt.setSpacing(2)
        self._value = SubtitleLabel("0", self)
        self._label = CaptionLabel(label, self)
        txt.addWidget(self._value)
        txt.addWidget(self._label)
        lay.addLayout(txt)
        lay.addStretch(1)

    def set_value(self, v: int | str) -> None:
        self._value.setText(str(v))


class StatsPage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        outer.addWidget(PageHeader(t("kms-stats-title")))

        # Metric tile grid (6 tiles). Capped at ~1160 px so tiles stay a
        # sensible ~180 px each at 1920 px instead of stretching into
        # banner-shaped cards with icon + number bunched on the left.
        metrics_holder = QWidget(self)
        grid = QGridLayout(metrics_holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        self._tile_papers = _MetricTile(FluentIcon.LIBRARY, t("sidebar-stats-papers"))
        self._tile_read = _MetricTile(FluentIcon.BOOK_SHELF, t("sidebar-stats-read"))
        self._tile_reading = _MetricTile(FluentIcon.PLAY, t("sidebar-stats-reading"))
        self._tile_starred = _MetricTile(FluentIcon.HEART, t("sidebar-stats-starred"))
        self._tile_pages = _MetricTile(FluentIcon.DOCUMENT, t("sidebar-stats-pages"))
        self._tile_figures = _MetricTile(FluentIcon.PHOTO, t("sidebar-stats-figures"))
        for col, tile in enumerate([
            self._tile_papers, self._tile_read, self._tile_reading,
            self._tile_starred, self._tile_pages, self._tile_figures,
        ]):
            grid.addWidget(tile, 0, col)
            grid.setColumnStretch(col, 1)
        outer.addWidget(BoundedRow(metrics_holder, max_width=1160))

        # Body stack: page 0 is the distribution-tables scroll view, page 1 is
        # a warm empty state for the zero-paper case. Tiles remain visible in
        # both modes so the user always sees the totals.
        self._body_stack = QStackedWidget(self)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget(scroll)
        body_layout = QVBoxLayout(body)
        body_layout.setSpacing(14)

        self._tbl_pyramid = self._make_table([t("ebm-pyramid-title"), "#"])
        body_layout.addWidget(self._wrap(t("kms-stats-evidence-pyramid"), self._tbl_pyramid))
        self._tbl_design = self._make_table([t("kms-stats-study-design"), "#"])
        body_layout.addWidget(self._wrap(t("kms-stats-study-design"), self._tbl_design))
        self._tbl_specialty = self._make_table([t("kms-stats-specialty"), "#"])
        body_layout.addWidget(self._wrap(t("kms-stats-specialty"), self._tbl_specialty))
        self._tbl_timeline = self._make_table([t("kms-import-manual-year"), "#"])
        body_layout.addWidget(self._wrap(t("kms-stats-timeline"), self._tbl_timeline))
        self._tbl_tags = self._make_table([t("kms-stats-top-tags"), "#"])
        body_layout.addWidget(self._wrap(t("kms-stats-top-tags"), self._tbl_tags))

        body_layout.addStretch(1)
        scroll.setWidget(body)
        self._body_stack.addWidget(scroll)

        self._empty = EmptyStatePanel(
            FluentIcon.LIBRARY,
            t("kms-stats-empty-title"),
            t("kms-stats-empty-message"),
            primary_text=t("kms-stats-empty-cta"),
            on_primary=lambda: self._main.show_page("import"),
        )
        self._body_stack.addWidget(self._empty)

        outer.addWidget(self._body_stack, 1)

    def _make_table(self, headers: list[str]) -> TableWidget:
        tbl = TableWidget()
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.verticalHeader().hide()
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # Tables size to their row count (set in _fill_table); the outer
        # scroll area handles overflow of the page as a whole, so internal
        # vertical scroll inside each table is not needed and would double up.
        tbl.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tbl.setBorderRadius(8)
        tbl.setBorderVisible(True)
        return tbl

    def _wrap(self, title: str, w: QWidget) -> CardWidget:
        box = CardWidget(self)
        box.setBorderRadius(8)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)
        lay.addWidget(StrongBodyLabel(title))
        lay.addWidget(w)
        return box

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        papers = get_all_papers()
        stats = get_db_stats()

        self._tile_papers.set_value(stats["total"])
        self._tile_read.set_value(stats["read"])
        self._tile_reading.set_value(stats["reading"])
        self._tile_starred.set_value(stats["starred"])
        self._tile_pages.set_value(stats["pages"])
        self._tile_figures.set_value(atlas_count())

        if not papers:
            # Swap in the warm empty-state panel instead of five empty tables.
            self._body_stack.setCurrentIndex(1)
            for tbl in (self._tbl_pyramid, self._tbl_design, self._tbl_specialty,
                        self._tbl_timeline, self._tbl_tags):
                tbl.setRowCount(0)
            return

        self._body_stack.setCurrentIndex(0)

        ebm_counts = Counter(p.get("evidence_level") or "—" for p in papers)
        order = ["I", "II", "III", "IV", "V", "—"]
        self._fill_table(self._tbl_pyramid, [(lv, ebm_counts.get(lv, 0)) for lv in order])

        design_counts = Counter(p.get("study_design") or "—" for p in papers).most_common(10)
        self._fill_table(self._tbl_design, design_counts)

        sp_counts = Counter(p.get("clinical_specialty") or "—" for p in papers).most_common(10)
        self._fill_table(self._tbl_specialty, sp_counts)

        year_counts = sorted(
            Counter(str(p.get("year") or "?") for p in papers).items(),
            key=lambda kv: kv[0], reverse=True,
        )[:15]
        self._fill_table(self._tbl_timeline, year_counts)

        tag_bag: list[str] = []
        for p in papers:
            try:
                tags = json.loads(p.get("tags") or "[]")
                tag_bag.extend(tags)
            except Exception:
                pass
        self._fill_table(self._tbl_tags, Counter(tag_bag).most_common(15))

    def _fill_table(self, tbl: TableWidget, rows: list[tuple]) -> None:
        from PyQt6.QtWidgets import QTableWidgetItem
        tbl.setRowCount(len(rows))
        for r, (key, val) in enumerate(rows):
            tbl.setItem(r, 0, QTableWidgetItem(str(key)))
            tbl.setItem(r, 1, QTableWidgetItem(str(val)))
        # Size the table to fit its rows — no internal scroll; the outer
        # page-level scroll area handles overall overflow.
        row_h = tbl.verticalHeader().defaultSectionSize() or 32
        header_h = tbl.horizontalHeader().sizeHint().height() or 32
        tbl.setFixedHeight(header_h + max(1, len(rows)) * row_h + 6)
