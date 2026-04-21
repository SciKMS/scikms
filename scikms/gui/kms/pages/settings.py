"""Settings page — Fluent SettingCardGroup groupings, theme switcher."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import QFileDialog, QVBoxLayout, QWidget, QScrollArea
from qfluentwidgets import (
    BodyLabel, CardWidget, FluentIcon, InfoBar, InfoBarPosition, MessageBox,
    OptionsConfigItem, OptionsSettingCard, OptionsValidator, PlainTextEdit,
    PrimaryPushButton, PushButton, PushSettingCard, QConfig, SettingCardGroup,
    StrongBodyLabel, Theme, setTheme,
)

from scikms import __version__
from scikms.gui.kms.shared import PageHeader
from scikms.i18n import t
from scikms.kms import ATLAS_ROOT, DATA_ROOT
from scikms.kms.atlas import atlas_count, atlas_load, atlas_save
from scikms.kms.config import DEFAULT_TAG_DICT
from scikms.kms.db import get_tag_dict, save_tag_dict

if TYPE_CHECKING:
    from scikms.gui.kms.main_window import MainWindow


class _TagDictCard(CardWidget):
    """Custom card: plain-text editor for the tag dictionary + save/reset buttons."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setBorderRadius(8)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        lay.addWidget(StrongBodyLabel(t("kms-settings-tag-dict")))
        lay.addWidget(BodyLabel(t("kms-settings-tag-dict-help")))
        self._txt = PlainTextEdit(self)
        self._txt.setPlainText("\n".join(get_tag_dict()))
        self._txt.setMinimumHeight(200)
        lay.addWidget(self._txt, 1)
        from PyQt6.QtWidgets import QHBoxLayout
        row = QHBoxLayout()
        btn_save = PrimaryPushButton(FluentIcon.SAVE, t("kms-settings-tag-save"))
        btn_save.clicked.connect(self._on_save)
        row.addWidget(btn_save)
        btn_reset = PushButton(FluentIcon.CANCEL, t("kms-settings-tag-reset"))
        btn_reset.clicked.connect(self._on_reset)
        row.addWidget(btn_reset)
        row.addStretch(1)
        lay.addLayout(row)

    def refresh(self) -> None:
        self._txt.setPlainText("\n".join(get_tag_dict()))

    def _on_save(self) -> None:
        terms = [ln.strip() for ln in self._txt.toPlainText().splitlines() if ln.strip()]
        save_tag_dict(terms)
        InfoBar.success(title=t("common-success"), content="",
                        parent=self, position=InfoBarPosition.TOP_RIGHT, duration=2000)

    def _on_reset(self) -> None:
        box = MessageBox(t("common-confirm"), t("confirm-clear-tag-dict"), self)
        if box.exec():
            save_tag_dict(list(DEFAULT_TAG_DICT))
            self._txt.setPlainText("\n".join(DEFAULT_TAG_DICT))


class SettingsPage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._qs = QSettings("scikms", "kms")
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        outer.addWidget(PageHeader(t("kms-settings-title")))

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        body = QWidget(scroll)
        body_lay = QVBoxLayout(body)
        body_lay.setSpacing(16)

        # Appearance group
        appearance = SettingCardGroup(t("kms-settings-title"), body)
        theme_card = OptionsSettingCard(
            configItem=OptionsConfigItem(
                "scikms", "theme", str(self._qs.value("theme", "auto") or "auto"),
                OptionsValidator(["auto", "light", "dark"]),
            ),
            icon=FluentIcon.BRUSH,
            title=t("kms-settings-theme"),
            content=t("kms-settings-language-restart"),
            texts=[t("kms-settings-theme-auto"),
                   t("kms-settings-theme-light"),
                   t("kms-settings-theme-dark")],
            parent=appearance,
        )
        theme_card.optionChanged.connect(self._on_theme_change)
        appearance.addSettingCard(theme_card)

        lang_card = OptionsSettingCard(
            configItem=OptionsConfigItem(
                "scikms", "locale", str(self._qs.value("locale", "vi-VN") or "vi-VN"),
                OptionsValidator(["vi-VN", "en-US"]),
            ),
            icon=FluentIcon.LANGUAGE,
            title=t("kms-settings-language"),
            content=t("kms-settings-language-restart"),
            texts=[t("kms-settings-language-vi"), t("kms-settings-language-en")],
            parent=appearance,
        )
        lang_card.optionChanged.connect(self._on_lang_change)
        appearance.addSettingCard(lang_card)
        body_lay.addWidget(appearance)

        # Data group
        data_group = SettingCardGroup(t("kms-settings-data-section"), body)
        self._data_card = PushSettingCard(
            text=t("kms-settings-data-change"),
            icon=FluentIcon.FOLDER,
            title=t("kms-settings-data-root"),
            content=str(DATA_ROOT),
            parent=data_group,
        )
        self._data_card.clicked.connect(self._on_change_data_root)
        data_group.addSettingCard(self._data_card)
        body_lay.addWidget(data_group)

        # Atlas group
        atlas_group = SettingCardGroup(t("kms-settings-atlas-section"), body)
        clear_atlas_card = PushSettingCard(
            text=t("kms-settings-atlas-clear"),
            icon=FluentIcon.DELETE,
            title=t("kms-settings-atlas-clear"),
            content=f"{atlas_count()} figures",
            parent=atlas_group,
        )
        clear_atlas_card.clicked.connect(self._on_clear_atlas)
        self._clear_atlas_card = clear_atlas_card
        atlas_group.addSettingCard(clear_atlas_card)
        body_lay.addWidget(atlas_group)

        # Tag dictionary
        self._tag_card = _TagDictCard(body)
        body_lay.addWidget(self._tag_card)

        # About
        about_card = CardWidget(body)
        about_card.setBorderRadius(8)
        about_lay = QVBoxLayout(about_card)
        about_lay.setContentsMargins(16, 14, 16, 14)
        about_lay.setSpacing(4)
        about_lay.addWidget(StrongBodyLabel(t("kms-settings-about")))
        about_lay.addWidget(BodyLabel(t("kms-app-title")))
        about_lay.addWidget(BodyLabel(f"{t('kms-settings-version')}: {__version__}"))
        body_lay.addWidget(about_card)

        body_lay.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._tag_card.refresh()
        self._data_card.setContent(str(DATA_ROOT))
        self._clear_atlas_card.setContent(f"{atlas_count()} figures")

    def _on_theme_change(self, item) -> None:
        val = item.value if hasattr(item, "value") else str(item)
        theme_map = {"auto": Theme.AUTO, "light": Theme.LIGHT, "dark": Theme.DARK}
        setTheme(theme_map.get(val, Theme.AUTO))
        self._qs.setValue("theme", val)

    def _on_lang_change(self, item) -> None:
        val = item.value if hasattr(item, "value") else str(item)
        self._qs.setValue("locale", val)
        InfoBar.info(
            title=t("kms-settings-language-restart"), content="",
            parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000,
        )

    def _on_clear_atlas(self) -> None:
        n = atlas_count()
        if n == 0:
            return
        box = MessageBox(t("common-confirm"), t("confirm-clear-atlas"), self)
        if box.exec():
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
            atlas_save(df.iloc[0:0])
            self.refresh()
            InfoBar.success(title=t("common-success"), content="",
                            parent=self, position=InfoBarPosition.TOP_RIGHT, duration=2000)

    def _on_change_data_root(self) -> None:
        new_path = QFileDialog.getExistingDirectory(self, t("kms-settings-data-change"), str(DATA_ROOT))
        if new_path:
            self._qs.setValue("data_root", new_path)
            InfoBar.info(
                title=t("kms-settings-language-restart"), content=new_path,
                parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000,
            )
