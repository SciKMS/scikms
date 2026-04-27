from unittest.mock import MagicMock
import pytest
from PyQt6.QtCore import QSettings
from scikms.gui.kms.pages.settings import SettingsPage
from qfluentwidgets import OptionsSettingCard


@pytest.fixture
def fake_main():
    return MagicMock()


@pytest.fixture
def clean_settings():
    settings = QSettings("scikms", "kms")
    settings.clear()
    settings.sync()
    yield settings
    settings.clear()
    settings.sync()


def test_settings_page_saves_locale_code_on_language_change(
    qtbot, fake_main, clean_settings, monkeypatch
):
    page = SettingsPage(fake_main)
    qtbot.addWidget(page)
    prompt = MagicMock()
    monkeypatch.setattr(page, "_prompt_restart", prompt)

    class FakeItem:
        value = "en-US"

    page._on_lang_change(FakeItem())
    assert clean_settings.value("locale") == "en-US"
    prompt.assert_called_once()


def test_settings_page_prompts_restart_after_language_change(
    qtbot, fake_main, monkeypatch
):
    page = SettingsPage(fake_main)
    qtbot.addWidget(page)

    prompt = MagicMock()
    monkeypatch.setattr(page, "_prompt_restart", prompt)

    class FakeItem:
        value = "vi-VN"

    page._on_lang_change(FakeItem())
    prompt.assert_called_once()


def test_translation_in_english_by_env_translation(qtbot, fake_main, monkeypatch):
    monkeypatch.setenv("SCIKMS_LOCALE", "en-US")
    page = SettingsPage(fake_main)
    qtbot.addWidget(page)

    texts = []
    for widget in page.findChildren(object):
        if hasattr(widget, "text") and callable(widget.text):
            try:
                texts.append(widget.text())
            except TypeError:
                pass

    print(f"Logging: {texts}")
    assert "Settings" in texts


def test_translation_in_vietnamese_by_env_translation(qtbot, fake_main, monkeypatch):
    monkeypatch.setenv("SCIKMS_LOCALE", "vi-VN")
    page = SettingsPage(fake_main)
    qtbot.addWidget(page)

    texts = []
    for widget in page.findChildren(object):
        if hasattr(widget, "text") and callable(widget.text):
            try:
                texts.append(widget.text())
            except TypeError:
                pass

    print(f"Logging: {texts}")
    assert "Cài đặt" in texts


def test_language_card_button_properties_are_expected_locale_codes(
    qtbot, clean_settings
):
    page = SettingsPage(MagicMock())
    qtbot.addWidget(page)
    lang_card = next(
        card
        for card in page.findChildren(OptionsSettingCard)
        if card.configName == "languageCode"
    )
    assert list(lang_card.configItem.options) == ["vi-VN", "en-US"]
    buttons = lang_card.buttonGroup.buttons()
    assert len(buttons) == 2
    assert buttons[0].property("languageCode") == "vi-VN"
    assert buttons[1].property("languageCode") == "en-US"


def test_clicking_english_emits_en_us_locale(qtbot, clean_settings, monkeypatch):
    page = SettingsPage(MagicMock())
    qtbot.addWidget(page)
    seen = {}

    def capture(item):
        seen["value"] = item.value

    monkeypatch.setattr(page, "_prompt_restart", MagicMock())
    lang_card = next(
        card
        for card in page.findChildren(OptionsSettingCard)
        if card.configName == "languageCode"
    )
    lang_card.optionChanged.connect(capture)
    english_button = lang_card.buttonGroup.buttons()[1]
    english_button.click()
    assert seen["value"] == "en-US"
