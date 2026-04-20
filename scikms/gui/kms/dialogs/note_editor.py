"""Note editor dialog for a paper's annotations."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QVBoxLayout,
)

from scikms.i18n import t
from scikms.kms.db import get_paper_by_id, update_paper


class NoteEditorDialog(QDialog):
    def __init__(self, paper_id: int, parent=None) -> None:
        super().__init__(parent)
        self._paper_id = paper_id
        self.setWindowTitle(t("kms-library-paper-edit-notes"))
        self.resize(640, 400)

        paper = get_paper_by_id(paper_id) or {}
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>{(paper.get('title') or t('common-untitled'))[:120]}</b>"))
        self._txt = QPlainTextEdit()
        self._txt.setPlainText(paper.get("notes") or "")
        layout.addWidget(self._txt, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save_and_accept(self) -> None:
        update_paper(self._paper_id, {"notes": self._txt.toPlainText()})
        self.accept()
