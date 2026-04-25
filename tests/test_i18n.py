import pytest
from scikms import i18n


def test_t_returns_translation():
    result = i18n.t("kms-app-title", locale="en-US")
    assert isinstance(result, str)
    assert result != "kms-app-title"


def test_t_formats_translation_with_kwargs():
    result = i18n.t(
        "kms-library-page-info",
        locale="en-US",
        start=1,
        end=20,
        total=120,
    )
    assert "1" in result
    assert "20" in result
    assert "120" in result


def test_t_raises_for_plugin_domain():
    with pytest.raises(NotImplementedError):
        i18n.t("kms-app-title", domain="demo-plugin")


def test_register_plugin_i18n_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        i18n.register_plugin_i18n("demo-plugin", "/tmp/locales", ["demo.ftl"])


def test_human_readable_number_formats_values():
    assert i18n.human_readable_number(1500, locale="en-US") == "1.5K"
    assert i18n.human_readable_number(12000, locale="zh-CN") == "1.2万"
