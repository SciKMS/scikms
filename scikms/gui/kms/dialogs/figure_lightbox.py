"""Figure lightbox dialog — full-size image with caption and source actions.

Replaces the atlas page's permanent right-side detail pane. Opens on demand
when a thumbnail is clicked, frees the atlas workspace for browsing, and
keeps destructive Delete visually separate from the primary Open action.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QScrollArea, QVBoxLayout
from qfluentwidgets import (
    BodyLabel, CaptionLabel, FluentIcon, MessageBox, PrimaryPushButton,
    PushButton, StrongBodyLabel, TransparentToolButton,
)

from scikms.i18n import t


class FigureLightboxDialog(QDialog):
    """Modal full-size figure viewer.

    Emits ``delete_requested(idx)`` when the user confirms deletion; the caller
    (AtlasPage) is responsible for mutating atlas state and refreshing. Opens
    the source PDF directly via ``PdfViewerDialog`` when requested.
    """

    delete_requested = pyqtSignal(object)

    def __init__(self, idx, row, paper, atlas_root: Path, parent=None) -> None:
        super().__init__(parent)
        self._idx = idx
        self._row = row
        self._paper = paper

        title = (paper.get("title") if paper else "") \
            or str(row.get("book_name", "") or "") \
            or str(row.get("fig_num", "") or "Figure")
        self.setWindowTitle(str(title)[:120])
        self.resize(980, 760)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # --- Header line: fig_num · page · type ----------------------------
        fig_num = str(row.get("fig_num", "") or "?")
        page = row.get("page_num")
        header_parts = [fig_num]
        if page is not None and str(page) and str(page) != "nan":
            try:
                header_parts.append(f"p{int(page)}")
            except (ValueError, TypeError):
                header_parts.append(f"p{page}")
        ftype = str(row.get("figure_type", "") or "").strip()
        if ftype and ftype.lower() != "other":
            header_parts.append(ftype.title())
        lay.addWidget(StrongBodyLabel("  ·  ".join(header_parts)))

        # --- Full image at native size inside a scroll area ----------------
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        img_label = BodyLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rel = str(row.get("image_path") or "")
        if rel:
            path = atlas_root / rel
            if path.exists():
                pix = QPixmap(str(path))
                if not pix.isNull():
                    img_label.setPixmap(pix)
        scroll.setWidget(img_label)
        lay.addWidget(scroll, 1)

        # --- Caption + context excerpt -------------------------------------
        cap = str(row.get("caption", "") or "").strip()
        ctx = str(row.get("context", "") or "").strip()
        if cap:
            lbl_cap = BodyLabel(cap)
            lbl_cap.setWordWrap(True)
            lay.addWidget(lbl_cap)
        if ctx:
            shown = ctx[:400] + ("…" if len(ctx) > 400 else "")
            lbl_ctx = CaptionLabel(shown)
            lbl_ctx.setWordWrap(True)
            lbl_ctx.setStyleSheet("opacity: 0.72;")
            lay.addWidget(lbl_ctx)

        # --- Action row -----------------------------------------------------
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        if self._paper is not None:
            self._btn_open = PrimaryPushButton(
                FluentIcon.VIEW, t("kms-atlas-open-paper")
            )
            self._btn_open.clicked.connect(self._on_open_paper)
            btn_row.addWidget(self._btn_open)

        btn_row.addStretch(1)

        btn_del = TransparentToolButton(FluentIcon.DELETE)
        btn_del.setToolTip(t("kms-atlas-delete-figure"))
        btn_del.setStyleSheet(
            "TransparentToolButton { color: #9ca3af; }"
            "TransparentToolButton:hover { color: #dc2626; "
            "background: rgba(220,38,38,0.08); }"
        )
        btn_del.clicked.connect(self._on_delete)
        btn_row.addWidget(btn_del)

        btn_close = PushButton(FluentIcon.CLOSE, t("common-close"))
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)

        lay.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _on_open_paper(self) -> None:
        if self._paper is None:
            return
        try:
            page = int(self._row.get("page_num") or 1)
        except (ValueError, TypeError):
            page = 1
        # QPdfPageNavigator is 0-indexed.
        initial = max(0, page - 1)
        from scikms.gui.kms.dialogs.pdf_viewer import PdfViewerDialog
        PdfViewerDialog(self._paper, parent=self, initial_page=initial).exec()

    def _on_delete(self) -> None:
        box = MessageBox(t("common-confirm"), t("confirm-delete-figure"), self)
        if box.exec():
            self.delete_requested.emit(self._idx)
            self.accept()
