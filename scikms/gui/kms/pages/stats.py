"""Stats page — EBM pyramid, study design, specialty, reading progress, timeline."""

from __future__ import annotations

import json
from collections import Counter
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QScrollArea, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, QGridLayout,
)

from scikms.i18n import t
from scikms.kms.atlas import atlas_count
from scikms.kms.db import get_all_papers, get_db_stats

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


class StatsPage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.addWidget(QLabel(f"<h2>{t('kms-stats-title')}</h2>"))

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        body = QWidget(scroll)
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setSpacing(12)

        self._lbl_metrics = QLabel("")
        self._body_layout.addWidget(self._lbl_metrics)

        self._tbl_pyramid = self._make_table([t("ebm-pyramid-title"), "#"])
        self._body_layout.addWidget(self._wrap("kms-stats-evidence-pyramid", self._tbl_pyramid))

        self._tbl_design = self._make_table([t("kms-stats-study-design"), "#"])
        self._body_layout.addWidget(self._wrap("kms-stats-study-design", self._tbl_design))

        self._tbl_specialty = self._make_table([t("kms-stats-specialty"), "#"])
        self._body_layout.addWidget(self._wrap("kms-stats-specialty", self._tbl_specialty))

        self._tbl_timeline = self._make_table([t("common-page"), "#"])
        self._body_layout.addWidget(self._wrap("kms-stats-timeline", self._tbl_timeline))

        self._tbl_tags = self._make_table([t("kms-stats-top-tags"), "#"])
        self._body_layout.addWidget(self._wrap("kms-stats-top-tags", self._tbl_tags))

        self._body_layout.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    def _make_table(self, headers: list[str]) -> QTableWidget:
        tbl = QTableWidget(0, len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setMaximumHeight(220)
        return tbl

    def _wrap(self, title_key: str, w: QWidget) -> QGroupBox:
        box = QGroupBox(t(title_key))
        lay = QVBoxLayout(box)
        lay.addWidget(w)
        return box

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        papers = get_all_papers()
        if not papers:
            self._lbl_metrics.setText(t("kms-stats-no-data"))
            for tbl in (self._tbl_pyramid, self._tbl_design, self._tbl_specialty,
                        self._tbl_timeline, self._tbl_tags):
                tbl.setRowCount(0)
            return

        stats = get_db_stats()
        self._lbl_metrics.setText(
            f"📚 {stats['total']}  ·  📖 {stats['read']}  ·  "
            f"⏳ {stats['reading']}  ·  ★ {stats['starred']}  ·  "
            f"📄 {stats['pages']}  ·  🖼 {atlas_count()}"
        )

        # EBM pyramid
        ebm_counts = Counter(p.get("evidence_level") or "—" for p in papers)
        order = ["I", "II", "III", "IV", "V", "—"]
        self._fill_table(self._tbl_pyramid, [(l, ebm_counts.get(l, 0)) for l in order])

        # Study design (top 10)
        design_counts = Counter(p.get("study_design") or "—" for p in papers).most_common(10)
        self._fill_table(self._tbl_design, design_counts)

        # Specialty (top 10)
        sp_counts = Counter(p.get("clinical_specialty") or "—" for p in papers).most_common(10)
        self._fill_table(self._tbl_specialty, sp_counts)

        # Timeline by year
        year_counts = sorted(
            Counter(str(p.get("year") or "?") for p in papers).items(),
            key=lambda kv: kv[0], reverse=True,
        )[:15]
        self._fill_table(self._tbl_timeline, year_counts)

        # Top tags
        tag_bag: list[str] = []
        for p in papers:
            try:
                tags = json.loads(p.get("tags") or "[]")
                tag_bag.extend(tags)
            except Exception:
                pass
        self._fill_table(self._tbl_tags, Counter(tag_bag).most_common(15))

    def _fill_table(self, tbl: QTableWidget, rows: list[tuple]) -> None:
        tbl.setRowCount(len(rows))
        for r, (key, val) in enumerate(rows):
            tbl.setItem(r, 0, QTableWidgetItem(str(key)))
            tbl.setItem(r, 1, QTableWidgetItem(str(val)))
