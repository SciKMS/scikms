"""Entry point for ``python -m scikms`` and the ``scikms`` console script."""

from __future__ import annotations

import os
import sys
import logging


def main() -> None:
    # Default to Vietnamese; user-configured locale lives in QSettings.
    if "SCIKMS_LOCALE" not in os.environ:
        try:
            from PyQt6.QtCore import QSettings

            saved = QSettings("scikms", "kms").value("locale", "vi-VN")
            os.environ["SCIKMS_LOCALE"] = str(saved or "vi-VN")
        except Exception:
            os.environ["SCIKMS_LOCALE"] = "vi-VN"

    # Apply user-chosen data root if set.
    try:
        from PyQt6.QtCore import QSettings
        from scikms.kms import set_data_root

        chosen = QSettings("scikms", "kms").value("data_root", "")
        if chosen:
            set_data_root(chosen)
    except Exception:
        pass

    # HiDPI rounding (must be set before QApplication) for crisp Fluent rendering.
    from PyQt6.QtCore import Qt

    try:
        from PyQt6.QtGui import QGuiApplication

        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    from PyQt6.QtWidgets import QApplication
    from qfluentwidgets import Theme, setTheme, setThemeColor

    from scikms.kms.db import init_db
    from scikms.gui.kms.main_window import MainWindow

    init_db()

    app = QApplication.instance() or QApplication(sys.argv)

    # Theme: read user choice (auto/light/dark), default AUTO. Indigo accent matches
    # the upstream y-khoa CSS palette.
    try:
        from PyQt6.QtCore import QSettings

        chosen_theme = (
            QSettings("scikms", "kms").value("theme", "auto") or "auto"
        ).lower()
    except Exception:
        chosen_theme = "auto"

    theme_map = {"auto": Theme.AUTO, "light": Theme.LIGHT, "dark": Theme.DARK}
    setTheme(theme_map.get(chosen_theme, Theme.AUTO))
    # setThemeColor("#4338CA")

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
