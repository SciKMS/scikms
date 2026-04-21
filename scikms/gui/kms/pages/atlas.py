"""Atlas page — figures grouped by paper.

Left pane lists papers (with figure counts). When a specific paper is
selected the center shows a single flat grid of its figures; when
"All papers" is selected the center switches to a scrollable stack of
per-paper sections with headers, so groups are visually distinct.
The right pane is the detail view with an "Open paper at page" action
that jumps straight into the source PDF at the figure's page.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QListView, QListWidget, QListWidgetItem,
    QScrollArea, QSplitter, QStackedWidget, QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    BodyLabel, CardWidget, CaptionLabel, ComboBox, FluentIcon, InfoBar,
    InfoBarPosition, MessageBox, PushButton, SearchLineEdit, StrongBodyLabel,
    SubtitleLabel,
)

from scikms.gui.kms.dialogs.pdf_viewer import PdfViewerDialog
from scikms.i18n import t
from scikms.kms import ATLAS_ROOT
from scikms.kms.atlas import atlas_delete_figure, atlas_load, atlas_search
from scikms.kms.config import FIGURE_TYPE_KEYWORDS, SUBJECT_DOMAIN_KEYWORDS
from scikms.kms.db import get_all_papers

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


_ALL = "(All)"
_PAPER_ALL_KEY = "__all__"
_STACK_SINGLE = 0
_STACK_GROUPED = 1
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


def _short_fig_label(row) -> str:
    fig_num = str(row.get("fig_num", "") or "")
    m = _FIG_NUM_RE.match(fig_num)
    if m:
        return f"p{m.group(1)} · #{m.group(2)}"
    return fig_num or f"p{row.get('page_num', '?')}"


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
        # List of (paper_id, inner_grid) — only populated in grouped mode
        self._grouped_grids: list[tuple[int, QListWidget]] = []
        self._selected_idx = None  # dataframe index of the selected figure
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(SubtitleLabel(t("kms-atlas-title")))

        self._summary_card = CardWidget(self)
        self._summary_card.setBorderRadius(8)
        sc = QHBoxLayout(self._summary_card)
        sc.setContentsMargins(16, 12, 16, 12)
        self._lbl_summary = BodyLabel("")
        sc.addWidget(self._lbl_summary)
        sc.addStretch(1)
        layout.addWidget(self._summary_card)

        filter_card = CardWidget(self)
        filter_card.setBorderRadius(8)
        fc = QHBoxLayout(filter_card)
        fc.setContentsMargins(12, 8, 12, 8)
        fc.setSpacing(8)
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

        self._cmb_conf = ComboBox(self)
        self._cmb_conf.addItems([_ALL, "high", "medium", "low"])
        self._cmb_conf.currentIndexChanged.connect(self._refresh_grid)
        fc.addWidget(CaptionLabel(t("kms-atlas-filter-confidence") + ":"))
        fc.addWidget(self._cmb_conf)
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

        # --- center: figure grid stacked (single vs grouped) -------------
        grid_pane = QWidget()
        gp = QVBoxLayout(grid_pane)
        gp.setContentsMargins(0, 0, 0, 0)
        gp.setSpacing(4)
        self._lbl_grid_header = StrongBodyLabel(t("kms-atlas-paper-all"))
        self._lbl_grid_header.setWordWrap(True)
        gp.addWidget(self._lbl_grid_header)
        self._lbl_grid_sub = CaptionLabel("")
        gp.addWidget(self._lbl_grid_sub)

        self._stack = QStackedWidget()
        # Single-paper grid (flat)
        self._single_grid = _make_figure_grid()
        self._single_grid.itemSelectionChanged.connect(
            lambda: self._on_selection_from(self._single_grid)
        )
        self._stack.addWidget(self._single_grid)
        # Grouped grid — QScrollArea of sections
        self._grouped_scroll = QScrollArea()
        self._grouped_scroll.setWidgetResizable(True)
        self._grouped_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._grouped_host = QWidget()
        self._grouped_lay = QVBoxLayout(self._grouped_host)
        self._grouped_lay.setContentsMargins(0, 0, 0, 0)
        self._grouped_lay.setSpacing(14)
        self._grouped_lay.addStretch(1)
        self._grouped_scroll.setWidget(self._grouped_host)
        self._stack.addWidget(self._grouped_scroll)
        gp.addWidget(self._stack, 1)
        split.addWidget(grid_pane)

        # --- right: detail -----------------------------------------------
        detail_card = CardWidget(self)
        detail_card.setBorderRadius(8)
        d_lay = QVBoxLayout(detail_card)
        d_lay.setContentsMargins(16, 14, 16, 14)
        d_lay.setSpacing(8)
        self._lbl_caption = BodyLabel("")
        self._lbl_caption.setWordWrap(True)
        d_lay.addWidget(self._lbl_caption)
        self._lbl_full_image = BodyLabel("")
        self._lbl_full_image.setMinimumSize(300, 300)
        self._lbl_full_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d_lay.addWidget(self._lbl_full_image, 1)

        btn_row = QHBoxLayout()
        self._btn_open = PushButton(FluentIcon.VIEW, t("kms-atlas-open-paper"))
        self._btn_open.clicked.connect(self._on_open_paper)
        btn_row.addWidget(self._btn_open)
        self._btn_delete = PushButton(FluentIcon.DELETE, t("kms-atlas-delete-figure"))
        self._btn_delete.clicked.connect(self._on_delete)
        btn_row.addWidget(self._btn_delete)
        d_lay.addLayout(btn_row)
        split.addWidget(detail_card)

        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 5)
        split.setStretchFactor(2, 3)
        layout.addWidget(split, 1)

        self._clear_detail()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._df = atlas_load()
        if self._df is None:
            self._lbl_summary.setText("pandas not installed")
            self._lst_papers.clear()
            self._clear_all_grids()
            self._clear_detail()
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
            self._clear_all_grids()
            self._clear_detail()
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
        # Switching paper usually means the selected figure is out of scope.
        self._selected_idx = None
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
        if self._cmb_conf.currentText() != _ALL:
            df = df[df["confidence"] == self._cmb_conf.currentText()]
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
            self._clear_all_grids()
            self._lbl_grid_sub.setText(t("kms-atlas-empty"))
            self._lbl_summary.setText(f"{t('kms-atlas-summary-figures')}: 0")
            self._stack.setCurrentIndex(_STACK_SINGLE)
            # Keep any previously-selected figure detail visible iff still in df.
            if self._selected_idx is None or self._selected_idx not in df.index:
                self._clear_detail()
            return

        n_papers = df["kms_paper_id"].nunique() if "kms_paper_id" in df.columns else 0
        n_high = int((df["confidence"] == "high").sum())
        top_type_vc = df["figure_type"].value_counts()
        top_type = top_type_vc.index[0] if not top_type_vc.empty else "—"
        self._lbl_summary.setText(
            f"{t('kms-atlas-summary-figures')}: {len(df)}  ·  "
            f"{t('kms-atlas-summary-papers')}: {n_papers}  ·  "
            f"{t('kms-atlas-summary-high-conf')}: {n_high}  ·  "
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

        if self._paper_filter == _PAPER_ALL_KEY:
            self._populate_grouped(df)
            self._stack.setCurrentIndex(_STACK_GROUPED)
        else:
            self._populate_single(df)
            self._stack.setCurrentIndex(_STACK_SINGLE)

        # Drop selection if it fell out of the filtered df.
        if self._selected_idx is not None and self._selected_idx not in df.index:
            self._selected_idx = None
            self._clear_detail()

    # ------------------------------------------------------------------
    def _populate_single(self, df) -> None:
        self._clear_grouped()
        grid = self._single_grid
        grid.blockSignals(True)
        grid.clear()
        for idx, row in df.iterrows():
            grid.addItem(self._make_fig_item(idx, row, show_book=False))
        grid.blockSignals(False)

    def _populate_grouped(self, df) -> None:
        # Wipe the single grid so it does not hold phantom selection.
        self._single_grid.blockSignals(True)
        self._single_grid.clear()
        self._single_grid.blockSignals(False)
        # Rebuild sections.
        self._clear_grouped()

        paper_ids_in_order = []
        seen = set()
        for pid in df["kms_paper_id"]:
            try:
                p = int(pid)
            except (ValueError, TypeError):
                continue
            if p not in seen:
                seen.add(p)
                paper_ids_in_order.append(p)

        for pid in paper_ids_in_order:
            sub = df[df["kms_paper_id"] == pid]
            paper = self._papers_by_id.get(pid)
            header = _short_paper_label(paper) if paper else f"Paper #{pid}"

            if "page_num" in sub.columns and sub["page_num"].notna().any():
                pmin = int(sub["page_num"].min())
                pmax = int(sub["page_num"].max())
                range_txt = f"pp. {pmin}–{pmax}" if pmin != pmax else f"p. {pmin}"
            else:
                range_txt = ""
            sub_caption = f"{len(sub)} {t('kms-atlas-summary-figures').lower()}"
            if range_txt:
                sub_caption += f"  ·  {range_txt}"

            section = QWidget()
            s_lay = QVBoxLayout(section)
            s_lay.setContentsMargins(0, 0, 0, 0)
            s_lay.setSpacing(2)
            hdr = StrongBodyLabel(header)
            hdr.setWordWrap(True)
            s_lay.addWidget(hdr)
            s_lay.addWidget(CaptionLabel(sub_caption))

            inner = _make_figure_grid()
            # Assume ~2 columns in worst case so all items stay visible; the
            # outer QScrollArea handles overall vertical scrolling.
            rows = max(1, (len(sub) + 1) // 2)
            inner.setMinimumHeight(rows * _CELL_H + 24)
            inner.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            inner.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            for idx, row in sub.iterrows():
                inner.addItem(self._make_fig_item(idx, row, show_book=False))
            inner.itemSelectionChanged.connect(
                lambda g=inner: self._on_selection_from(g)
            )
            self._grouped_grids.append((pid, inner))
            s_lay.addWidget(inner)

            # Insert BEFORE the trailing stretch so sections stack top-down.
            self._grouped_lay.insertWidget(
                self._grouped_lay.count() - 1, section
            )

    def _make_fig_item(self, idx, row, show_book: bool) -> QListWidgetItem:
        thumb_rel = row.get("thumb_path", "") or row.get("image_path", "")
        full = ATLAS_ROOT / thumb_rel if thumb_rel else None
        if show_book:
            book = str(row.get("book_name", "") or "")[:28]
            label_txt = f"{_short_fig_label(row)}\n{book}"
        else:
            label_txt = _short_fig_label(row)
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

    def _clear_grouped(self) -> None:
        # Remove all child section widgets except the final stretch.
        while self._grouped_lay.count() > 1:
            item = self._grouped_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._grouped_grids.clear()

    def _clear_all_grids(self) -> None:
        self._single_grid.blockSignals(True)
        self._single_grid.clear()
        self._single_grid.blockSignals(False)
        self._clear_grouped()

    # ------------------------------------------------------------------
    def _on_selection_from(self, grid: QListWidget) -> None:
        items = grid.selectedItems()
        if not items:
            return
        idx = items[0].data(Qt.ItemDataRole.UserRole)
        # Clear selection in every OTHER grid so only one item is highlighted
        # globally.
        for g in [self._single_grid, *[ig for _, ig in self._grouped_grids]]:
            if g is grid:
                continue
            g.blockSignals(True)
            g.clearSelection()
            g.blockSignals(False)
        self._selected_idx = idx
        self._show_detail(idx)

    def _show_detail(self, idx) -> None:
        if self._df is None or idx not in self._df.index:
            self._clear_detail()
            return
        row = self._df.loc[idx]
        cap = row.get("caption", "") or ""
        ctx = row.get("context", "") or ""
        self._lbl_caption.setText(
            f"<b>{row.get('fig_num', '?')}</b>  "
            f"<span style='opacity:.6'>{row.get('book_name', '')}</span><br>"
            f"<i>{cap[:200]}</i><br>"
            f"<small style='opacity:.5'>{ctx[:300]}</small>"
        )
        img = ATLAS_ROOT / (row.get("image_path") or "")
        if img.exists():
            pix = QPixmap(str(img))
            if not pix.isNull():
                self._lbl_full_image.setPixmap(pix.scaled(
                    640, 480, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
            else:
                self._lbl_full_image.setText("(image not found)")
        else:
            self._lbl_full_image.setText("(image not found)")

        # Enable actions iff the source paper is known.
        try:
            pid = int(row.get("kms_paper_id"))
        except (ValueError, TypeError):
            pid = None
        self._btn_open.setEnabled(pid is not None and pid in self._papers_by_id)
        self._btn_delete.setEnabled(True)

    def _clear_detail(self) -> None:
        self._selected_idx = None
        self._lbl_caption.setText(
            f"<i style='opacity:.6'>{t('kms-atlas-detail-empty')}</i>"
        )
        self._lbl_full_image.clear()
        self._lbl_full_image.setText("")
        self._btn_open.setEnabled(False)
        self._btn_delete.setEnabled(False)

    # ------------------------------------------------------------------
    def _on_open_paper(self) -> None:
        if self._df is None or self._selected_idx is None:
            return
        if self._selected_idx not in self._df.index:
            return
        row = self._df.loc[self._selected_idx]
        try:
            pid = int(row.get("kms_paper_id"))
        except (ValueError, TypeError):
            return
        paper = self._papers_by_id.get(pid)
        if paper is None:
            return
        try:
            page = int(row.get("page_num") or 1)
        except (ValueError, TypeError):
            page = 1
        # QPdfPageNavigator uses 0-indexed pages.
        initial = max(0, page - 1)
        dlg = PdfViewerDialog(paper, parent=self, initial_page=initial)
        dlg.exec()

    def _on_delete(self) -> None:
        if self._selected_idx is None:
            return
        idx = self._selected_idx
        box = MessageBox(t("common-confirm"), t("confirm-delete-figure"), self)
        if box.exec():
            atlas_delete_figure(idx)
            self._selected_idx = None
            self.refresh()
            InfoBar.success(
                title=t("common-success"), content="",
                parent=self, position=InfoBarPosition.TOP_RIGHT, duration=2000,
            )
