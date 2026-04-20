"""Entry point for ``python -m scikms`` and the ``scikms`` console script."""

from __future__ import annotations

import os
import sys


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

    from PyQt6.QtWidgets import QApplication
    from scikms.kms.db import init_db
    from scikms.gui.kms.main_window import MainWindow

    init_db()

    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
