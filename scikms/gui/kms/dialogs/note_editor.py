"""Note editor — Fluent MessageBox-style dialog for paper annotations."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout
from qfluentwidgets import (
    BodyLabel, MessageBoxBase, PlainTextEdit, StrongBodyLabel, SubtitleLabel,
)

from scikms.i18n import t
from scikms.kms.db import get_paper_by_id, update_paper


class NoteEditorDialog(MessageBoxBase):
    def __init__(self, paper_id: int, parent=None) -> None:
        super().__init__(parent)
        self._paper_id = paper_id
        paper = get_paper_by_id(paper_id) or {}

        self._title = SubtitleLabel(t("kms-library-paper-edit-notes"))
        self.viewLayout.addWidget(self._title)
        self.viewLayout.addWidget(
            BodyLabel((paper.get("title") or t("common-untitled"))[:140])
        )
        self._txt = PlainTextEdit()
        self._txt.setPlainText(paper.get("notes") or "")
        self._txt.setMinimumSize(640, 360)
        self.viewLayout.addWidget(self._txt)

        self.yesButton.setText(t("common-save"))
        self.cancelButton.setText(t("common-cancel"))
        self.widget.setMinimumWidth(700)

    def accept(self) -> None:
        update_paper(self._paper_id, {"notes": self._txt.toPlainText()})
        super().accept()
