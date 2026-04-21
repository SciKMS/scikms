"""Atlas page — 2-pane browser.

Left pane lists papers with per-paper figure counts. The center is a flat
figure grid driven by the paper sidebar plus the top filter rail. Clicking
any thumbnail opens a full-size lightbox (``FigureLightboxDialog``) with
caption, source-paper action, and delete. No permanent detail pane —
the browsing surface is the whole grid.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QListView, QListWidget, QListWidgetItem, QSplitter,
    QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    CaptionLabel, CardWidget, ComboBox, FluentIcon, InfoBar, InfoBarPosition,
    PushButton, SearchLineEdit, StrongBodyLabel,
)

from scikms.gui.kms.dialogs.figure_lightbox import FigureLightboxDialog
from scikms.gui.kms.shared import PageHeader
from scikms.i18n import t
from scikms.kms import ATLAS_ROOT
from scikms.kms.atlas import atlas_delete_figure, atlas_load, atlas_search
from scikms.kms.config import FIGURE_TYPE_KEYWORDS, SUBJECT_DOMAIN_KEYWORDS
from scikms.kms.db import get_all_papers

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


_ALL = "(All)"
_PAPER_ALL_KEY = "__all__"
_ICON_W, _ICON_H = 180, 140
_CELL_W, _CELL_H = 200, 180

_FIG_NUM_RE = re.compile(r"^Fig p(\d+)-(\d+)$")


def _short_paper_label(paper: dict) -> str:
    year = paper.get("year") or "?"
    authors = (paper.get("authors") or "").split(";")[0].split(",")[0].strip()
    if not authors:
        authors = paper.get("original_filename") or "?"
    title = (paper.get("title") or "").strip()
    if len(title) > 60:
        title = title[:57] + "..."
    return f"[{year}] {authors} — {title}" if title else f"[{year}] {authors}"


def _fig_type_label(row) -> str:
    """Primary thumbnail label — figure type where known, ``Figure`` fallback.

    Auto-extract frequently classifies images as ``other``; showing that
    word on most cards adds noise, so collapse it to the neutral ``Figure``.
    """
    ftype = str(row.get("figure_type", "") or "").strip().lower()
    if not ftype or ftype == "other":
        return "Figure"
    return ftype.title()


def _page_hint(row) -> str:
    page = row.get("page_num")
    if page is None:
        return ""
    try:
        return f"p{int(page)}"
    except (ValueError, TypeError):
        return ""


def _fig_sort_key(fig_num) -> tuple[int, int]:
    m = _FIG_NUM_RE.match(str(fig_num or ""))
    return (int(m.group(1)), int(m.group(2))) if m else (10 ** 6, 10 ** 6)


def _make_figure_grid() -> QListWidget:
    grid = QListWidget()
    grid.setViewMode(QListView.ViewMode.IconMode)
    grid.setIconSize(QSize(_ICON_W, _ICON_H))
    grid.setGridSize(QSize(_CELL_W, _CELL_H))
    grid.setResizeMode(QListView.ResizeMode.Adjust)
    grid.setMovement(QListView.Movement.Static)
    grid.setSpacing(8)
    grid.setWordWrap(True)
    grid.setUniformItemSizes(True)
    grid.setFrameShape(QFrame.Shape.NoFrame)
    return grid


class AtlasPage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._df = None
        self._papers_by_id: dict[int, dict] = {}
        self._paper_filter: object = _PAPER_ALL_KEY
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(PageHeader(t("kms-atlas-title")))

        filter_card = CardWidget(self)
        filter_card.setBorderRadius(8)
        fc = QHBoxLayout(filter_card)
        fc.setContentsMargins(12, 8, 12, 8)
        fc.setSpacing(8)

        self._lbl_summary = StrongBodyLabel("")
        fc.addWidget(self._lbl_summary)
        fc.addSpacing(12)

        self._ed_q = SearchLineEdit(self)
        self._ed_q.setPlaceholderText(t("kms-atlas-search-prompt"))
        self._ed_q.textChanged.connect(self._refresh_grid)
        fc.addWidget(self._ed_q, 1)

        self._cmb_type = ComboBox(self)
        self._cmb_type.addItem(_ALL)
        self._cmb_type.addItems(list(FIGURE_TYPE_KEYWORDS.keys()) + ["other"])
        self._cmb_type.currentIndexChanged.connect(self._refresh_grid)
        fc.addWidget(CaptionLabel(t("kms-atlas-filter-type") + ":"))
        fc.addWidget(self._cmb_type)

        self._cmb_domain = ComboBox(self)
        self._cmb_domain.addItem(_ALL)
        self._cmb_domain.addItems(list(SUBJECT_DOMAIN_KEYWORDS.keys()) + ["general"])
        self._cmb_domain.currentIndexChanged.connect(self._refresh_grid)
        fc.addWidget(CaptionLabel(t("kms-atlas-filter-domain") + ":"))
        fc.addWidget(self._cmb_domain)

        fc.addSpacing(6)
        self._btn_reset = PushButton(FluentIcon.SYNC, t("kms-atlas-filter-reset"))
        self._btn_reset.clicked.connect(self._on_reset_filters)
        fc.addWidget(self._btn_reset)
        layout.addWidget(filter_card)

        split = QSplitter(Qt.Orientation.Horizontal, self)

        # --- left: paper list --------------------------------------------
        paper_pane = QWidget()
        pp = QVBoxLayout(paper_pane)
        pp.setContentsMargins(0, 0, 0, 0)
        pp.setSpacing(6)
        pp.addWidget(StrongBodyLabel(t("kms-atlas-filter-paper")))
        self._lst_papers = QListWidget()
        self._lst_papers.currentItemChanged.connect(self._on_paper_change)
        pp.addWidget(self._lst_papers, 1)
        split.addWidget(paper_pane)

        # --- center: figure grid -----------------------------------------
        grid_pane = QWidget()
        gp = QVBoxLayout(grid_pane)
        gp.setContentsMargins(0, 0, 0, 0)
        gp.setSpacing(4)
        self._lbl_grid_header = StrongBodyLabel(t("kms-atlas-paper-all"))
        self._lbl_grid_header.setWordWrap(True)
        gp.addWidget(self._lbl_grid_header)
        self._lbl_grid_sub = CaptionLabel("")
        gp.addWidget(self._lbl_grid_sub)

        self._grid = _make_figure_grid()
        # Single-click opens the lightbox. Arrow-key navigation still works
        # for selection without triggering a dialog on every key.
        self._grid.itemClicked.connect(self._on_item_clicked)
        gp.addWidget(self._grid, 1)

        split.addWidget(grid_pane)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 7)
        layout.addWidget(split, 1)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._df = atlas_load()
        if self._df is None:
            self._lbl_summary.setText("pandas not installed")
            self._lst_papers.clear()
            self._grid.clear()
            return

        if not self._df.empty:
            import pandas as pd
            if "kms_paper_id" in self._df.columns:
                self._df["kms_paper_id"] = pd.to_numeric(
                    self._df["kms_paper_id"], errors="coerce"
                )
            if "page_num" in self._df.columns:
                self._df["page_num"] = pd.to_numeric(
                    self._df["page_num"], errors="coerce"
                )

        self._papers_by_id = {int(p["id"]): p for p in get_all_papers()}
        self._refresh_paper_list()

        if self._df.empty:
            self._lbl_summary.setText(t("kms-atlas-empty"))
            self._lbl_grid_header.setText(t("kms-atlas-paper-all"))
            self._lbl_grid_sub.setText("")
            self._grid.clear()
            return

        self._refresh_grid()

    # ------------------------------------------------------------------
    def _refresh_paper_list(self) -> None:
        self._lst_papers.blockSignals(True)
        self._lst_papers.clear()

        counts: dict[int, int] = {}
        if self._df is not None and not self._df.empty \
                and "kms_paper_id" in self._df.columns:
            vc = self._df["kms_paper_id"].dropna().value_counts()
            for pid, n in vc.items():
                try:
                    counts[int(pid)] = int(n)
                except (ValueError, TypeError):
                    continue

        total = int(len(self._df)) if self._df is not None else 0
        all_item = QListWidgetItem(f"{t('kms-atlas-paper-all')}  ({total})")
        all_item.setData(Qt.ItemDataRole.UserRole, _PAPER_ALL_KEY)
        self._lst_papers.addItem(all_item)

        paper_ids = sorted(
            counts.keys(),
            key=lambda pid: (
                -(int(self._papers_by_id.get(pid, {}).get("year") or 0)),
                -pid,
            ),
        )
        for pid in paper_ids:
            paper = self._papers_by_id.get(pid)
            label = _short_paper_label(paper) if paper else f"Paper #{pid}"
            it = QListWidgetItem(f"{label}  ({counts[pid]})")
            it.setData(Qt.ItemDataRole.UserRole, pid)
            it.setToolTip(label)
            self._lst_papers.addItem(it)

        target_row = 0
        for i in range(self._lst_papers.count()):
            if self._lst_papers.item(i).data(Qt.ItemDataRole.UserRole) \
                    == self._paper_filter:
                target_row = i
                break
        else:
            self._paper_filter = _PAPER_ALL_KEY
        self._lst_papers.setCurrentRow(target_row)
        self._lst_papers.blockSignals(False)

    def _on_paper_change(self, current, _previous) -> None:
        if current is None:
            return
        self._paper_filter = current.data(Qt.ItemDataRole.UserRole)
        self._refresh_grid()

    def _on_reset_filters(self) -> None:
        for w in (self._ed_q, self._cmb_type, self._cmb_domain, self._lst_papers):
            w.blockSignals(True)
        self._ed_q.clear()
        self._cmb_type.setCurrentIndex(0)
        self._cmb_domain.setCurrentIndex(0)
        if self._lst_papers.count() > 0:
            self._lst_papers.setCurrentRow(0)
        self._paper_filter = _PAPER_ALL_KEY
        for w in (self._ed_q, self._cmb_type, self._cmb_domain, self._lst_papers):
            w.blockSignals(False)
        self._refresh_grid()

    # ------------------------------------------------------------------
    def _apply_common_filters(self, df):
        q = self._ed_q.text().strip()
        if q:
            df = atlas_search(q, df)
        if self._cmb_type.currentText() != _ALL:
            df = df[df["figure_type"] == self._cmb_type.currentText()]
        if self._cmb_domain.currentText() != _ALL:
            df = df[df["subject_domain"] == self._cmb_domain.currentText()]
        return df

    def _sort_by_paper_and_page(self, df):
        if df.empty:
            return df
        df = df.assign(_fig_order=df["fig_num"].map(_fig_sort_key))
        df = df.sort_values(
            by=["kms_paper_id", "page_num", "_fig_order"],
            kind="stable",
            na_position="last",
        ).drop(columns=["_fig_order"])
        return df

    def _current_df(self):
        if self._df is None or self._df.empty:
            return self._df
        df = self._df.copy()
        if self._paper_filter != _PAPER_ALL_KEY \
                and "kms_paper_id" in df.columns:
            df = df[df["kms_paper_id"] == self._paper_filter]
        df = self._apply_common_filters(df)
        return self._sort_by_paper_and_page(df)

    # ------------------------------------------------------------------
    def _refresh_grid(self) -> None:
        df = self._current_df()
        if df is None:
            return

        if self._paper_filter == _PAPER_ALL_KEY:
            self._lbl_grid_header.setText(t("kms-atlas-paper-all"))
        else:
            paper = self._papers_by_id.get(int(self._paper_filter))
            self._lbl_grid_header.setText(
                _short_paper_label(paper) if paper
                else f"Paper #{self._paper_filter}"
            )

        if df.empty:
            self._grid.clear()
            self._lbl_grid_sub.setText(t("kms-atlas-empty"))
            self._lbl_summary.setText(f"{t('kms-atlas-summary-figures')}: 0")
            return

        n_papers = df["kms_paper_id"].nunique() if "kms_paper_id" in df.columns else 0
        top_type_vc = df["figure_type"].value_counts()
        top_type = top_type_vc.index[0] if not top_type_vc.empty else "—"
        self._lbl_summary.setText(
            f"{t('kms-atlas-summary-figures')}: {len(df)}  ·  "
            f"{t('kms-atlas-summary-papers')}: {n_papers}  ·  "
            f"{t('kms-atlas-summary-top-type')}: {top_type}"
        )

        if "page_num" in df.columns and df["page_num"].notna().any():
            pmin = int(df["page_num"].min())
            pmax = int(df["page_num"].max())
            page_range = f"pp. {pmin}–{pmax}" if pmin != pmax else f"p. {pmin}"
        else:
            page_range = ""
        sub_parts = [f"{len(df)} {t('kms-atlas-summary-figures').lower()}"]
        if page_range:
            sub_parts.append(page_range)
        self._lbl_grid_sub.setText("  ·  ".join(sub_parts))

        show_book = self._paper_filter == _PAPER_ALL_KEY
        self._grid.blockSignals(True)
        self._grid.clear()
        for idx, row in df.iterrows():
            self._grid.addItem(self._make_fig_item(idx, row, show_book=show_book))
        self._grid.blockSignals(False)

    # ------------------------------------------------------------------
    def _make_fig_item(self, idx, row, show_book: bool) -> QListWidgetItem:
        thumb_rel = row.get("thumb_path", "") or row.get("image_path", "")
        full = ATLAS_ROOT / thumb_rel if thumb_rel else None

        # Line 1: figure type (or neutral "Figure"). Line 2: page + optional
        # book-name snippet when browsing across papers.
        type_line = _fig_type_label(row)
        page_line = _page_hint(row)
        if show_book:
            book = str(row.get("book_name", "") or "").strip()
            if book:
                book_short = book[:22] + ("…" if len(book) > 22 else "")
                second = f"{page_line} · {book_short}" if page_line else book_short
            else:
                second = page_line
        else:
            second = page_line
        label_txt = f"{type_line}\n{second}" if second else type_line

        item = QListWidgetItem(label_txt)
        if full and full.exists():
            pix = QPixmap(str(full))
            if not pix.isNull():
                item.setIcon(QIcon(pix.scaled(
                    _ICON_W, _ICON_H, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )))
        item.setData(Qt.ItemDataRole.UserRole, idx)
        item.setToolTip(
            f"{row.get('fig_num', '')} · page {row.get('page_num', '?')}\n"
            f"{(row.get('caption') or row.get('context') or '')[:240]}"
        )
        return item

    # ------------------------------------------------------------------
    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        if item is None or self._df is None:
            return
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx not in self._df.index:
            return
        row = self._df.loc[idx]
        try:
            pid = int(row.get("kms_paper_id"))
        except (ValueError, TypeError):
            pid = None
        paper = self._papers_by_id.get(pid) if pid is not None else None
        dlg = FigureLightboxDialog(idx, row, paper, ATLAS_ROOT, parent=self)
        dlg.delete_requested.connect(self._on_delete_figure)
        dlg.exec()

    def _on_delete_figure(self, idx) -> None:
        atlas_delete_figure(idx)
        self.refresh()
        InfoBar.success(
            title=t("common-success"), content="",
            parent=self, position=InfoBarPosition.TOP_RIGHT, duration=2000,
        )
