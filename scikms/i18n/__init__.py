import logging
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .manager import i18nManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_MANAGER = i18nManager()


def t(
    msg_id: str,
    locale: str | None = None,
    domain: str | None = None,
    **kwargs: str | int | float | Decimal | date | datetime | object,
) -> str:
    """
    Translate a Fluent message id using the shared i18n manager.

    :param msg_id: Message ID inside fluent translation files.
    :param locale: Optional BCP-47 language code
    :param domain: Plugin id, e.g. "fuo-netease".
                   If None, will use core bundle.
                   If passed, raises NotImplementedError (plugin support not yet added).
    :param kwargs: Variables to interpolate into the message

    :return: Translated string

    Example:
        t("kms-app-title")
        t("kms-library-page-info", start=1, end=20, total=120)
    """
    if domain is not None:
        # TODO: add plugin-specific bundle loading once plugin i18n is needed.
        raise NotImplementedError("Plugin i18n is not implemented yet.")

    return _MANAGER.translate(msg_id, locale=locale, **kwargs)


def register_plugin_i18n(
    domain: str,
    locales_dir: str | Path,
    resource_ids: list[str],
) -> None:
    """
    Reserved for future plugin i18n support.

    :param domain: Plugin id, e.g. "fuo-netease"
    :param locales_dir: Parent path of the locale files
    :param resource_ids: Locale file names as list

    TODO: add plugin registration and per-plugin bundle resolution in i18nManager.
    """
    raise NotImplementedError("Plugin i18n is not implemented yet.")


def human_readable_number(n: int, locale: str | None = None) -> str:
    """
    Compact number formatter.

    :param n: the number
    :param locale: BCP-47 language code
    :return: Human-readable compact representation

    Examples:
        human_readable_number(1500000) -> "1.5M"
        human_readable_number(123456789) -> "123.4M"
        human_readable_number(15000) with zh locale -> "1.5万"
    """
    locale = locale or _MANAGER._get_default_locale()

    if locale.startswith("zh"):
        levels = [
            (100000000, "亿"),
            (10000, "万"),
        ]
    else:
        levels = [
            (1_000_000_000, "B"),
            (1_000_000, "M"),
            (1_000, "K"),
        ]

    for value, unit in levels:
        if n > value:
            first, second = n // value, (n % value) // (value // 10)
            return f"{first}.{second}{unit}"
    return str(n)


if __name__ == "__main__":
    print("Supported locales:", _MANAGER._supported_locales)
    print("Detected default locale:", _MANAGER._get_default_locale())
    print()

    tests = [
        ("kms-app-title", {}),
        ("nav-library", {}),
        ("nav-import", {}),
        ("common-save", {}),
        ("common-cancel", {}),
        ("kms-library-title", {}),
        ("kms-import-title", {}),
        ("kms-search-title", {}),
        ("kms-settings-title", {}),
        ("kms-library-page-info", {"start": 1, "end": 20, "total": 120}),
        ("kms-import-pdf-process", {"count": 3}),
        ("kms-export-saved", {"path": "/tmp/out.csv"}),
        ("missing-key-example", {}),
    ]

    for locale in _MANAGER._supported_locales:
        print(f"=== {locale} ===")
        for key, kwargs in tests:
            value = _MANAGER.translate(key, locale=locale, **kwargs)
            print(f"{key}: {value}")
        print()
