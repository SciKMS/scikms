"""Lightbox image viewer — plain QDialog with Fluent-styled close button."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QScrollArea, QVBoxLayout
from qfluentwidgets import BodyLabel, FluentIcon, PushButton


class ImageViewerDialog(QDialog):
    def __init__(self, image_path: str | Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(Path(image_path).name)
        self.resize(900, 700)

        layout = QVBoxLayout(self)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        label = BodyLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = QPixmap(str(image_path))
        if not pix.isNull():
            label.setPixmap(pix)
        scroll.setWidget(label)
        layout.addWidget(scroll, 1)

        btn = PushButton(FluentIcon.CLOSE, "Close")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
