"""Shared widgets used by multiple KMS pages.

Keep widgets here small, dependency-free of pages, and Fluent-consistent.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, TitleLabel


class PageHeader(QWidget):
    """Standard page-level header used by every KMS page.

    Renders the page title with ``TitleLabel`` (h1 in the Fluent hierarchy)
    and an optional caption line below it. Use this instead of raw
    ``SubtitleLabel`` so the page title always outranks in-page card titles
    (``SubtitleLabel`` / ``StrongBodyLabel``).
    """

    def __init__(
        self,
        title: str,
        caption: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self._title = TitleLabel(title, self)
        lay.addWidget(self._title)
        self._caption: Optional[CaptionLabel] = None
        if caption:
            self._caption = CaptionLabel(caption, self)
            lay.addWidget(self._caption)

    def set_title(self, text: str) -> None:
        self._title.setText(text)

    def set_caption(self, text: str) -> None:
        if self._caption is None:
            self._caption = CaptionLabel(text, self)
            layout = self.layout()
            if layout is not None:
                layout.addWidget(self._caption)
        else:
            self._caption.setText(text)
        self._caption.setVisible(bool(text))
