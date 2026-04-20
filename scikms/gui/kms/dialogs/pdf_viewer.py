"""PDF viewer dialog with side note editor.

Tries PyQt6.QtPdf for embedded rendering. Falls back to opening the system
viewer if QtPdf is unavailable (or the file is missing).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
    QSplitter, QVBoxLayout, QWidget,
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
        meta = QLabel(self._build_meta_html())
        meta.setTextFormat(Qt.TextFormat.RichText)
        meta.setWordWrap(True)
        layout.addWidget(meta)

        split = QSplitter(Qt.Orientation.Horizontal, self)
        split.addWidget(self._build_pdf_pane())
        split.addWidget(self._build_notes_pane())
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 1)
        layout.addWidget(split, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _build_meta_html(self) -> str:
        p = self._paper
        return (
            f"<b>{(p.get('title') or t('common-untitled'))[:200]}</b><br>"
            f"<i>{p.get('authors') or ''}</i> · {p.get('journal') or ''} "
            f"({p.get('year') or '?'})<br>"
            f"DOI: {p.get('doi') or '—'}  ·  "
            f"EBM: {p.get('evidence_level') or '—'}  ·  "
            f"{t('sidebar-filter-design')}: {p.get('study_design') or '—'}  ·  "
            f"{t('sidebar-filter-specialty')}: {p.get('clinical_specialty') or '—'}"
        )

    def _build_pdf_pane(self) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)

        fp = self._paper.get("file_path") or ""
        if not fp or not Path(fp).exists():
            lbl = QLabel(f"<i>{t('common-empty')}</i>  ({fp or '—'})")
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

        # Fallback: button to open in system viewer.
        info = QLabel(
            f"<i>QtPdf not available. PDF stored at:</i><br><tt>{fp}</tt>"
        )
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(info)
        from PyQt6.QtWidgets import QPushButton
        btn = QPushButton(t("kms-library-paper-open"))
        btn.clicked.connect(lambda: _open_external(fp))
        lay.addWidget(btn)
        return wrap

    def _build_notes_pane(self) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.addWidget(QLabel(f"<b>{t('kms-atlas-detail-notes')}</b>"))
        self._txt = QPlainTextEdit()
        self._txt.setPlainText(self._paper.get("notes") or "")
        lay.addWidget(self._txt, 1)
        from PyQt6.QtWidgets import QPushButton
        btn = QPushButton(t("common-save"))
        btn.clicked.connect(self._save_notes)
        lay.addWidget(btn)
        return wrap

    def _save_notes(self) -> None:
        update_paper(self._paper_id, {"notes": self._txt.toPlainText()})
        QMessageBox.information(self, t("common-success"), t("common-success"))


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
