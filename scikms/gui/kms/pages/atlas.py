"""Atlas page — figure browser grouped by paper."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from scikms.i18n import t
from scikms.kms import ATLAS_ROOT
from scikms.kms.atlas import atlas_count, atlas_delete_figure, atlas_load, atlas_search
from scikms.kms.config import FIGURE_TYPE_KEYWORDS, SUBJECT_DOMAIN_KEYWORDS

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


_ALL = "(All)"


class AtlasPage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._df = None
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h2>{t('kms-atlas-title')}</h2>"))

        self._lbl_summary = QLabel("")
        layout.addWidget(self._lbl_summary)

        bar = QHBoxLayout()
        self._ed_q = QLineEdit()
        self._ed_q.setPlaceholderText(t("kms-atlas-search-prompt"))
        self._ed_q.textChanged.connect(self._refresh_grid)
        bar.addWidget(self._ed_q, 1)

        self._cmb_type = QComboBox()
        self._cmb_type.addItem(_ALL)
        self._cmb_type.addItems(list(FIGURE_TYPE_KEYWORDS.keys()) + ["other"])
        self._cmb_type.currentIndexChanged.connect(self._refresh_grid)
        bar.addWidget(QLabel(t("kms-atlas-filter-type") + ":"))
        bar.addWidget(self._cmb_type)

        self._cmb_domain = QComboBox()
        self._cmb_domain.addItem(_ALL)
        self._cmb_domain.addItems(list(SUBJECT_DOMAIN_KEYWORDS.keys()) + ["general"])
        self._cmb_domain.currentIndexChanged.connect(self._refresh_grid)
        bar.addWidget(QLabel(t("kms-atlas-filter-domain") + ":"))
        bar.addWidget(self._cmb_domain)

        self._cmb_conf = QComboBox()
        self._cmb_conf.addItems([_ALL, "high", "medium", "low"])
        self._cmb_conf.currentIndexChanged.connect(self._refresh_grid)
        bar.addWidget(QLabel(t("kms-atlas-filter-confidence") + ":"))
        bar.addWidget(self._cmb_conf)

        layout.addLayout(bar)

        split = QSplitter(Qt.Orientation.Horizontal, self)
        self._grid = QListWidget()
        self._grid.setViewMode(QListView.ViewMode.IconMode)
        self._grid.setIconSize(QSize(160, 120))
        self._grid.setResizeMode(QListView.ResizeMode.Adjust)
        self._grid.setSpacing(8)
        self._grid.itemSelectionChanged.connect(self._on_select)
        split.addWidget(self._grid)

        self._detail = QWidget()
        d_lay = QVBoxLayout(self._detail)
        self._lbl_caption = QLabel("")
        self._lbl_caption.setWordWrap(True)
        d_lay.addWidget(self._lbl_caption)
        self._lbl_full_image = QLabel("")
        self._lbl_full_image.setMinimumSize(300, 300)
        self._lbl_full_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d_lay.addWidget(self._lbl_full_image, 1)
        self._btn_delete = QPushButton(t("kms-atlas-delete-figure"))
        self._btn_delete.clicked.connect(self._on_delete)
        d_lay.addWidget(self._btn_delete)
        split.addWidget(self._detail)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        layout.addWidget(split, 1)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._df = atlas_load()
        if self._df is None:
            self._lbl_summary.setText("pandas not installed")
            return
        if self._df.empty:
            self._lbl_summary.setText(t("kms-atlas-empty"))
            self._grid.clear()
            return
        self._refresh_grid()

    def _refresh_grid(self) -> None:
        if self._df is None or self._df.empty:
            return
        df = self._df.copy()
        q = self._ed_q.text().strip()
        if q:
            df = atlas_search(q, df)
        if self._cmb_type.currentText() != _ALL:
            df = df[df["figure_type"] == self._cmb_type.currentText()]
        if self._cmb_domain.currentText() != _ALL:
            df = df[df["subject_domain"] == self._cmb_domain.currentText()]
        if self._cmb_conf.currentText() != _ALL:
            df = df[df["confidence"] == self._cmb_conf.currentText()]

        n_papers = df["book_name"].nunique() if not df.empty else 0
        n_high = int((df["confidence"] == "high").sum()) if not df.empty else 0
        top_type = df["figure_type"].value_counts().index[0] if not df.empty else "—"
        self._lbl_summary.setText(
            f"{t('kms-atlas-summary-figures')}: {len(df)}  ·  "
            f"{t('kms-atlas-summary-papers')}: {n_papers}  ·  "
            f"{t('kms-atlas-summary-high-conf')}: {n_high}  ·  "
            f"{t('kms-atlas-summary-top-type')}: {top_type}"
        )

        self._grid.clear()
        for idx, row in df.iterrows():
            thumb_rel = row.get("thumb_path", "") or row.get("image_path", "")
            full = ATLAS_ROOT / thumb_rel if thumb_rel else None
            label_txt = f"{row.get('fig_num','?')}\n{(row.get('book_name','') or '')[:30]}"
            item = QListWidgetItem(label_txt)
            if full and full.exists():
                pix = QPixmap(str(full))
                if not pix.isNull():
                    item.setIcon(QIcon(pix.scaled(
                        160, 120, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )))
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self._grid.addItem(item)

    def _on_select(self) -> None:
        items = self._grid.selectedItems()
        if not items or self._df is None:
            return
        idx = items[0].data(Qt.ItemDataRole.UserRole)
        if idx not in self._df.index:
            return
        row = self._df.loc[idx]
        cap = row.get("caption", "") or ""
        ctx = row.get("context", "") or ""
        self._lbl_caption.setText(
            f"<b>{row.get('fig_num','?')}</b>  "
            f"<span style='color:#666'>{row.get('book_name','')}</span><br>"
            f"<i>{cap[:200]}</i><br>"
            f"<small style='color:#888'>{ctx[:300]}</small>"
        )
        img = ATLAS_ROOT / (row.get("image_path") or "")
        if img.exists():
            pix = QPixmap(str(img))
            if not pix.isNull():
                self._lbl_full_image.setPixmap(pix.scaled(
                    640, 480, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
                return
        self._lbl_full_image.setText("(image not found)")

    def _on_delete(self) -> None:
        items = self._grid.selectedItems()
        if not items:
            return
        idx = items[0].data(Qt.ItemDataRole.UserRole)
        ans = QMessageBox.question(
            self, t("common-confirm"), t("confirm-delete-figure"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            atlas_delete_figure(idx)
            self.refresh()
            self._main.refresh_sidebar_stats()
