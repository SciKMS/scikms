"""Rename page — bulk rename PDFs on disk to canonical pattern."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from scikms.i18n import t
from scikms.kms import STORAGE_DIR
from scikms.kms.clinical import build_renamed_filename
from scikms.kms.db import get_all_papers, update_paper

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


class RenamePage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._candidates: list[tuple[int, Path, str]] = []  # (paper_id, current_path, new_name)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h2>{t('kms-rename-title')}</h2>"))
        layout.addWidget(QLabel(t("kms-rename-pattern-info")))

        path_row = QHBoxLayout()
        self._lbl_path = QLabel(f"{t('kms-rename-storage-path')}: {STORAGE_DIR}")
        path_row.addWidget(self._lbl_path)
        btn_open = QPushButton(t("kms-rename-open-folder"))
        btn_open.clicked.connect(self._open_folder)
        path_row.addWidget(btn_open)
        path_row.addStretch(1)
        layout.addLayout(path_row)

        self._chk_skip = QCheckBox(t("kms-rename-skip-existing"))
        self._chk_skip.setChecked(True)
        self._chk_skip.toggled.connect(self.refresh)
        layout.addWidget(self._chk_skip)

        btn_preview = QPushButton(t("kms-rename-preview"))
        btn_preview.clicked.connect(self.refresh)
        layout.addWidget(btn_preview)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["ID", "Current", "New name"])
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table, 1)

        self._btn_execute = QPushButton(t("kms-rename-execute", count=0))
        self._btn_execute.clicked.connect(self._execute)
        layout.addWidget(self._btn_execute)

        self._lbl_status = QLabel("")
        layout.addWidget(self._lbl_status)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._candidates = []
        for p in get_all_papers():
            fp = p.get("file_path") or ""
            if not fp or not os.path.exists(fp):
                continue
            current = Path(fp)
            new_name = build_renamed_filename(p)
            if self._chk_skip.isChecked() and current.name == new_name:
                continue
            self._candidates.append((p["id"], current, new_name))
        self._render()

    def _render(self) -> None:
        if not self._candidates:
            self._table.setRowCount(0)
            self._lbl_status.setText(t("kms-rename-no-pdf"))
            self._btn_execute.setText(t("kms-rename-execute", count=0))
            self._btn_execute.setEnabled(False)
            return
        self._table.setRowCount(len(self._candidates))
        for r, (pid, cur, new) in enumerate(self._candidates):
            self._table.setItem(r, 0, QTableWidgetItem(str(pid)))
            self._table.setItem(r, 1, QTableWidgetItem(cur.name))
            self._table.setItem(r, 2, QTableWidgetItem(new))
        self._btn_execute.setText(t("kms-rename-execute", count=len(self._candidates)))
        self._btn_execute.setEnabled(True)
        self._lbl_status.setText("")

    def _execute(self) -> None:
        if not self._candidates:
            return
        renamed = 0
        for pid, cur, new in self._candidates:
            dest = cur.parent / new
            try:
                if dest.exists():
                    continue
                shutil.move(str(cur), str(dest))
                update_paper(pid, {"file_path": str(dest), "renamed_filename": new})
                renamed += 1
            except OSError:
                continue
        self._lbl_status.setText(t("status-renamed", count=renamed))
        self.refresh()

    def _open_folder(self) -> None:
        path = str(STORAGE_DIR.resolve())
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", path])
            elif sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass
