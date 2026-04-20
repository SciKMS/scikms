"""Lightbox image viewer."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QLabel, QScrollArea, QVBoxLayout


class ImageViewerDialog(QDialog):
    def __init__(self, image_path: str | Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(Path(image_path).name)
        self.resize(900, 700)

        layout = QVBoxLayout(self)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = QPixmap(str(image_path))
        if not pix.isNull():
            label.setPixmap(pix)
        scroll.setWidget(label)
        layout.addWidget(scroll, 1)
