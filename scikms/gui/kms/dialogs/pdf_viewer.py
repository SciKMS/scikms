"""PDF viewer dialog with side notes panel. Fluent-styled chrome, QtPdf body."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QSplitter, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel, CaptionLabel, FluentIcon, InfoBar, InfoBarPosition,
    PlainTextEdit, PrimaryPushButton, PushButton, StrongBodyLabel,
    SubtitleLabel,
)

from scikms.i18n import t
from scikms.kms.db import update_paper


try:
    from PyQt6.QtPdf import QPdfDocument
    from PyQt6.QtPdfWidgets import QPdfView
    HAS_QPDF = True
except ImportError:
    HAS_QPDF = False


class PdfViewerDialog(QDialog):
    def __init__(self, paper: dict, parent=None) -> None:
        super().__init__(parent)
        self._paper = paper
        self._paper_id = paper["id"]
        self.setWindowTitle((paper.get("title") or t("common-untitled"))[:80])
        self.resize(1100, 760)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        layout.addWidget(SubtitleLabel((paper.get("title") or t("common-untitled"))[:140]))
        layout.addWidget(BodyLabel(
            f"<i>{paper.get('authors') or ''}</i> · {paper.get('journal') or ''} "
            f"({paper.get('year') or '?'})"
        ))
        layout.addWidget(CaptionLabel(
            f"DOI: {paper.get('doi') or '—'}  ·  "
            f"EBM: {paper.get('evidence_level') or '—'}  ·  "
            f"{paper.get('study_design') or '—'}  ·  "
            f"{paper.get('clinical_specialty') or '—'}"
        ))

        split = QSplitter(Qt.Orientation.Horizontal, self)
        split.addWidget(self._build_pdf_pane())
        split.addWidget(self._build_notes_pane())
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 1)
        layout.addWidget(split, 1)

        bar = QHBoxLayout()
        bar.addStretch(1)
        close_btn = PushButton(FluentIcon.CLOSE, t("common-close"))
        close_btn.clicked.connect(self.accept)
        bar.addWidget(close_btn)
        layout.addLayout(bar)

    def _build_pdf_pane(self) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)

        fp = self._paper.get("file_path") or ""
        if not fp or not Path(fp).exists():
            lbl = BodyLabel(f"<i>{t('common-empty')}</i>  ({fp or '—'})")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(lbl, 1)
            return wrap

        if HAS_QPDF:
            doc = QPdfDocument(self)
            doc.load(fp)
            view = QPdfView(self)
            view.setDocument(doc)
            view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            lay.addWidget(view, 1)
            return wrap

        info = BodyLabel(f"<i>QtPdf not available. File:</i><br><tt>{fp}</tt>")
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(info)
        btn = PrimaryPushButton(FluentIcon.VIEW, t("kms-library-paper-open"))
        btn.clicked.connect(lambda: _open_external(fp))
        lay.addWidget(btn)
        return wrap

    def _build_notes_pane(self) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setSpacing(6)
        lay.addWidget(StrongBodyLabel(t("kms-atlas-detail-notes")))
        self._txt = PlainTextEdit()
        self._txt.setPlainText(self._paper.get("notes") or "")
        lay.addWidget(self._txt, 1)
        btn = PrimaryPushButton(FluentIcon.SAVE, t("common-save"))
        btn.clicked.connect(self._save_notes)
        lay.addWidget(btn)
        return wrap

    def _save_notes(self) -> None:
        update_paper(self._paper_id, {"notes": self._txt.toPlainText()})
        InfoBar.success(
            title=t("common-success"), content="",
            parent=self, position=InfoBarPosition.TOP_RIGHT, duration=2000,
        )


def _open_external(path: str) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass
