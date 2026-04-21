"""Shared widgets used by multiple KMS pages.

Keep widgets here small, dependency-free of pages, and Fluent-consistent.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel, CaptionLabel, FluentIconBase, IconWidget, PrimaryPushButton,
    StrongBodyLabel, TitleLabel,
)


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


class EmptyStatePanel(QWidget):
    """Generic empty-state panel: centred icon + title + message + CTA.

    Use inside cards, tables, or page bodies that may legitimately contain
    zero rows. Replaces the "active filters hovering over a blank canvas"
    anti-pattern: gives the user one clear explanation and one next action.
    """

    def __init__(
        self,
        icon: FluentIconBase,
        title: str,
        message: str = "",
        primary_text: Optional[str] = None,
        on_primary: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(0)
        outer.addStretch(1)

        ic = IconWidget(icon, self)
        ic.setFixedSize(48, 48)
        ic_row = QHBoxLayout()
        ic_row.addStretch(1)
        ic_row.addWidget(ic)
        ic_row.addStretch(1)
        outer.addLayout(ic_row)

        title_lbl = StrongBodyLabel(title, self)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addSpacing(12)
        outer.addWidget(title_lbl)

        if message:
            msg_lbl = BodyLabel(message, self)
            msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg_lbl.setWordWrap(True)
            msg_lbl.setMaximumWidth(440)
            msg_row = QHBoxLayout()
            msg_row.addStretch(1)
            msg_row.addWidget(msg_lbl)
            msg_row.addStretch(1)
            outer.addSpacing(4)
            outer.addLayout(msg_row)

        if primary_text and on_primary is not None:
            btn = PrimaryPushButton(primary_text, self)
            btn.clicked.connect(on_primary)
            btn_row = QHBoxLayout()
            btn_row.addStretch(1)
            btn_row.addWidget(btn)
            btn_row.addStretch(1)
            outer.addSpacing(16)
            outer.addLayout(btn_row)

        outer.addStretch(1)


class BoundedRow(QWidget):
    """Horizontally-centred wrapper that caps a child widget's width.

    Pages otherwise stretch every card and row to the full viewport on
    ultrawide screens, which produces banner-shaped cards (export rows),
    tables with meters of whitespace (search), and metric tiles that each
    span 300+ px (stats).

    Wrap the offending row with ``BoundedRow(child)`` to keep content a
    comfortable reading width. Default cap: 1280 px (matches the app's
    default window width, ``MainWindow(1280, 820)``).
    """

    DEFAULT_MAX_WIDTH = 1280

    def __init__(
        self,
        child: QWidget,
        max_width: int = DEFAULT_MAX_WIDTH,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        child.setParent(self)
        child.setMaximumWidth(max_width)
        current_v = child.sizePolicy().verticalPolicy()
        child.setSizePolicy(QSizePolicy.Policy.Expanding, current_v)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addStretch(1)
        lay.addWidget(child, 1)
        lay.addStretch(1)
        self._child = child

    @property
    def child(self) -> QWidget:
        return self._child
