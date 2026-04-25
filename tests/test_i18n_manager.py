from scikms.i18n import _MANAGER
from scikms.i18n.manager import i18nManager


class FakeMessage:
    def __init__(self, value):
        self.value = value


class FakeBundle:
    def __init__(self, messages):
        self.messages = messages

    def get_message(self, key):
        if key not in self.messages:
            return None

        return FakeMessage(self.messages[key])

    def format_pattern(self, value, kwargs):
        return value.format(**kwargs), []


def test_build_fallback_chain_puts_requested_locale_first():
    manager = i18nManager()
    assert manager._build_fallback_chain("vi-VN") == ["vi-VN", "en-US"]


def test_get_default_locale_uses_env_override(monkeypatch):
    manager = i18nManager()
    monkeypatch.setenv("SCIKMS_LOCALE", "vi_VN")
    assert manager._get_default_locale() == "vi-VN"


def test_translate_uses_fallback_bundle(monkeypatch):
    manager = i18nManager()

    vi_bundle = FakeBundle({})
    en_bundle = FakeBundle({"hello": "Hello {name}"})

    def get_fake_bundle(locale):
        if locale == "vi-VN":
            return vi_bundle
        elif locale == "en-US":
            return en_bundle
        else:
            return AssertionError(f"Unexpected localed: {locale}")

    monkeypatch.setattr(manager, "_get_bundle", get_fake_bundle)

    result = manager.translate("hello", locale="vi-VN", name="Alice")
    assert result == "Hello Alice"


def test_missing_key_return_key(monkeypatch):
    manager = i18nManager()

    empty_bundle = FakeBundle({})

    monkeypatch.setattr(manager, "_get_bundle", lambda locale: empty_bundle)
    result = manager.translate("missing_key", locale="vi-VN")

    assert result == "missing_key"
