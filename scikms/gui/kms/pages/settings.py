"""Settings page — tag dictionary, atlas ops, language, data folder."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from scikms import __version__
from scikms.i18n import t
from scikms.kms import ATLAS_ROOT, DATA_ROOT, set_data_root
from scikms.kms.atlas import atlas_count, atlas_load, atlas_save
from scikms.kms.config import DEFAULT_TAG_DICT
from scikms.kms.db import get_tag_dict, save_tag_dict

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


class SettingsPage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h2>{t('kms-settings-title')}</h2>"))

        # Language
        lang_box = QGroupBox(t("kms-settings-language"))
        lang_lay = QVBoxLayout(lang_box)
        self._cmb_lang = QComboBox()
        self._cmb_lang.addItem(t("kms-settings-language-vi"), "vi-VN")
        self._cmb_lang.addItem(t("kms-settings-language-en"), "en-US")
        cur = QSettings("scikms", "kms").value("locale", "vi-VN")
        idx = self._cmb_lang.findData(cur)
        if idx >= 0:
            self._cmb_lang.setCurrentIndex(idx)
        self._cmb_lang.currentIndexChanged.connect(self._on_lang_change)
        lang_lay.addWidget(self._cmb_lang)
        lang_lay.addWidget(QLabel(f"<i>{t('kms-settings-language-restart')}</i>"))
        layout.addWidget(lang_box)

        # Tag dictionary
        tag_box = QGroupBox(t("kms-settings-tag-dict"))
        tag_lay = QVBoxLayout(tag_box)
        tag_lay.addWidget(QLabel(t("kms-settings-tag-dict-help")))
        self._txt_tags = QPlainTextEdit()
        self._txt_tags.setPlainText("\n".join(get_tag_dict()))
        tag_lay.addWidget(self._txt_tags, 1)
        row = QHBoxLayout()
        btn_save_tags = QPushButton(t("kms-settings-tag-save"))
        btn_save_tags.clicked.connect(self._on_save_tags)
        row.addWidget(btn_save_tags)
        btn_reset_tags = QPushButton(t("kms-settings-tag-reset"))
        btn_reset_tags.clicked.connect(self._on_reset_tags)
        row.addWidget(btn_reset_tags)
        row.addStretch(1)
        tag_lay.addLayout(row)
        layout.addWidget(tag_box, 1)

        # Atlas
        atlas_box = QGroupBox(t("kms-settings-atlas-section"))
        atlas_form = QFormLayout(atlas_box)
        self._sp_minpx = QSpinBox()
        self._sp_minpx.setRange(50, 1000)
        self._sp_minpx.setValue(120)
        atlas_form.addRow(t("kms-settings-atlas-min-px"), self._sp_minpx)
        btn_clear_atlas = QPushButton(t("kms-settings-atlas-clear"))
        btn_clear_atlas.clicked.connect(self._on_clear_atlas)
        atlas_form.addRow("", btn_clear_atlas)
        layout.addWidget(atlas_box)

        # Data folder
        data_box = QGroupBox(t("kms-settings-data-section"))
        data_lay = QVBoxLayout(data_box)
        self._lbl_data_root = QLabel(f"{t('kms-settings-data-root')}: {DATA_ROOT}")
        data_lay.addWidget(self._lbl_data_root)
        btn_change = QPushButton(t("kms-settings-data-change"))
        btn_change.clicked.connect(self._on_change_data_root)
        data_lay.addWidget(btn_change)
        layout.addWidget(data_box)

        # About
        about_box = QGroupBox(t("kms-settings-about"))
        about_lay = QVBoxLayout(about_box)
        about_lay.addWidget(QLabel(
            f"{t('kms-app-title')}\n{t('kms-settings-version')}: {__version__}"
        ))
        layout.addWidget(about_box)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._txt_tags.setPlainText("\n".join(get_tag_dict()))
        self._lbl_data_root.setText(f"{t('kms-settings-data-root')}: {DATA_ROOT}")

    def _on_lang_change(self, _idx: int) -> None:
        locale = self._cmb_lang.currentData()
        QSettings("scikms", "kms").setValue("locale", locale)

    def _on_save_tags(self) -> None:
        terms = [ln.strip() for ln in self._txt_tags.toPlainText().splitlines() if ln.strip()]
        save_tag_dict(terms)
        QMessageBox.information(self, t("common-success"), t("common-success"))

    def _on_reset_tags(self) -> None:
        ans = QMessageBox.question(
            self, t("common-confirm"), t("confirm-clear-tag-dict"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            save_tag_dict(list(DEFAULT_TAG_DICT))
            self._txt_tags.setPlainText("\n".join(DEFAULT_TAG_DICT))

    def _on_clear_atlas(self) -> None:
        n = atlas_count()
        if n == 0:
            return
        ans = QMessageBox.question(
            self, t("common-confirm"), t("confirm-clear-atlas"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            df = atlas_load()
            if df is None:
                return
            for _, row in df.iterrows():
                for col in ("image_path", "thumb_path"):
                    rel = row.get(col, "")
                    if rel:
                        full = ATLAS_ROOT / rel
                        if full.exists():
                            try:
                                full.unlink()
                            except OSError:
                                pass
            empty = df.iloc[0:0]
            atlas_save(empty)
            self._main.refresh_sidebar_stats()

    def _on_change_data_root(self) -> None:
        new_path = QFileDialog.getExistingDirectory(self, t("kms-settings-data-change"), str(DATA_ROOT))
        if new_path:
            QSettings("scikms", "kms").setValue("data_root", new_path)
            QMessageBox.information(
                self, t("common-success"), t("kms-settings-language-restart"),
            )
