"""scikms.gui.kms.sidebar — left dock with navigation + stats + filters."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDockWidget, QFormLayout, QFrame, QGridLayout,
    QGroupBox, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from scikms.i18n import t
from scikms.kms.config import (
    CLINICAL_SPECIALTIES, EBM_LEVELS, NAV_ITEMS, STUDY_DESIGN_KEYWORDS,
)
from scikms.kms.db import get_all_projects, get_db_stats


_ALL = "(All)"


class Sidebar(QDockWidget):
    nav_clicked = pyqtSignal(str)
    filters_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(t("sidebar-section-navigation"), parent)
        self.setMinimumWidth(260)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        body = QWidget(scroll)
        self._layout = QVBoxLayout(body)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(10)
        scroll.setWidget(body)
        self.setWidget(scroll)

        self._nav_buttons: dict[str, QPushButton] = {}
        self._build_nav()
        self._build_stats()
        self._build_filters()

        self._layout.addStretch(1)

    # ------------------------------------------------------------------
    def _build_nav(self) -> None:
        box = QGroupBox(t("sidebar-section-navigation"))
        lay = QVBoxLayout(box)
        lay.setSpacing(2)
        for item in NAV_ITEMS:
            btn = QPushButton(t(item["label_key"]))
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setStyleSheet("QPushButton { text-align: left; padding: 6px 10px; }")
            btn.clicked.connect(lambda _checked=False, k=item["key"]: self.nav_clicked.emit(k))
            lay.addWidget(btn)
            self._nav_buttons[item["key"]] = btn
        self._layout.addWidget(box)

    def _build_stats(self) -> None:
        box = QGroupBox(t("sidebar-section-stats"))
        grid = QGridLayout(box)
        grid.setSpacing(4)
        self._stat_papers = QLabel("0")
        self._stat_figures = QLabel("0")
        self._stat_pages = QLabel("0")
        self._stat_annotated = QLabel("0")
        for r, (lbl_key, val_widget) in enumerate([
            ("sidebar-stats-papers", self._stat_papers),
            ("sidebar-stats-figures", self._stat_figures),
            ("sidebar-stats-pages", self._stat_pages),
            ("sidebar-stats-annotated", self._stat_annotated),
        ]):
            grid.addWidget(QLabel(t(lbl_key) + ":"), r, 0)
            val_widget.setStyleSheet("font-weight: bold;")
            grid.addWidget(val_widget, r, 1)
        self._layout.addWidget(box)

    def _build_filters(self) -> None:
        box = QGroupBox(t("sidebar-section-filters"))
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self._cmb_status = QComboBox()
        self._cmb_status.addItems([
            t("sidebar-filter-status-all"),
            t("sidebar-filter-status-unread"),
            t("sidebar-filter-status-reading"),
            t("sidebar-filter-status-read"),
        ])
        self._cmb_status.currentIndexChanged.connect(self._emit)
        form.addRow(t("sidebar-filter-status"), self._cmb_status)

        self._chk_starred = QCheckBox(t("sidebar-filter-starred"))
        self._chk_starred.toggled.connect(self._emit)
        form.addRow("", self._chk_starred)

        self._cmb_project = QComboBox()
        self._cmb_project.addItem(_ALL)
        self._cmb_project.currentIndexChanged.connect(self._emit)
        form.addRow(t("sidebar-filter-project"), self._cmb_project)

        self._cmb_evidence = QComboBox()
        self._cmb_evidence.addItem(_ALL)
        for level in ("I", "II", "III", "IV", "V"):
            self._cmb_evidence.addItem(t(EBM_LEVELS[level]["label_key"]))
        self._cmb_evidence.currentIndexChanged.connect(self._emit)
        form.addRow(t("sidebar-filter-evidence"), self._cmb_evidence)

        self._cmb_design = QComboBox()
        self._cmb_design.addItem(_ALL)
        for design in STUDY_DESIGN_KEYWORDS:
            self._cmb_design.addItem(design)
        self._cmb_design.currentIndexChanged.connect(self._emit)
        form.addRow(t("sidebar-filter-design"), self._cmb_design)

        self._cmb_specialty = QComboBox()
        self._cmb_specialty.addItem(_ALL)
        self._cmb_specialty.addItems(CLINICAL_SPECIALTIES)
        self._cmb_specialty.currentIndexChanged.connect(self._emit)
        form.addRow(t("sidebar-filter-specialty"), self._cmb_specialty)

        self._cmb_scope = QComboBox()
        for key, label in [
            ("all", "sidebar-filter-scope-all"),
            ("title_abstract", "sidebar-filter-scope-title-abstract"),
            ("notes", "sidebar-filter-scope-notes"),
            ("fulltext", "sidebar-filter-scope-content"),
        ]:
            self._cmb_scope.addItem(t(label), userData=key)
        self._cmb_scope.currentIndexChanged.connect(self._emit)
        form.addRow(t("sidebar-filter-search-scope"), self._cmb_scope)

        self._layout.addWidget(box)

    # ------------------------------------------------------------------
    def _emit(self) -> None:
        self.filters_changed.emit()

    def set_active(self, key: str) -> None:
        for k, btn in self._nav_buttons.items():
            btn.setChecked(k == key)

    def refresh_stats(self) -> None:
        try:
            stats = get_db_stats()
        except Exception:
            return
        self._stat_papers.setText(str(stats.get("total", 0)))
        self._stat_pages.setText(str(stats.get("pages", 0)))
        self._stat_annotated.setText(str(stats.get("annotated", 0)))
        try:
            from scikms.kms.atlas import atlas_count
            self._stat_figures.setText(str(atlas_count()))
        except Exception:
            self._stat_figures.setText("?")
        # Refresh project list
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

    def current_filters(self) -> dict:
        ev_text = self._cmb_evidence.currentText()
        ev_level = ""
        for level in ("I", "II", "III", "IV", "V"):
            if t(EBM_LEVELS[level]["label_key"]) == ev_text:
                ev_level = level
                break
        return {
            "status":   ["all", "unread", "reading", "read"][self._cmb_status.currentIndex()],
            "starred":  self._chk_starred.isChecked(),
            "project":  self._cmb_project.currentText() if self._cmb_project.currentText() != _ALL else "",
            "evidence": ev_level,
            "design":   self._cmb_design.currentText() if self._cmb_design.currentText() != _ALL else "",
            "specialty": self._cmb_specialty.currentText() if self._cmb_specialty.currentText() != _ALL else "",
            "scope":    self._cmb_scope.currentData() or "all",
        }
