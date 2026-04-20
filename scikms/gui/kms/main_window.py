"""scikms.gui.kms.main_window — KMS main window."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QStatusBar, QMenuBar, QMessageBox,
)

from scikms.i18n import t
from scikms.kms.config import NAV_ITEMS

from .sidebar import Sidebar
from .pages.atlas import AtlasPage
from .pages.export import ExportPage
from .pages.import_page import ImportPage
from .pages.library import LibraryPage
from .pages.rename import RenamePage
from .pages.search import SearchPage
from .pages.settings import SettingsPage
from .pages.stats import StatsPage


class MainWindow(QMainWindow):
    """Top-level window. Hosts sidebar dock + stacked page area + status bar."""

    page_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(t("kms-app-title"))
        self.resize(1280, 820)

        self._pages: dict[str, object] = {
            "library":  LibraryPage(self),
            "import":   ImportPage(self),
            "search":   SearchPage(self),
            "atlas":    AtlasPage(self),
            "stats":    StatsPage(self),
            "rename":   RenamePage(self),
            "export":   ExportPage(self),
            "settings": SettingsPage(self),
        }

        self._stack = QStackedWidget(self)
        self._key_to_index: dict[str, int] = {}
        for key, page in self._pages.items():
            self._key_to_index[key] = self._stack.addWidget(page)
        self.setCentralWidget(self._stack)

        self._sidebar = Sidebar(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._sidebar)
        self._sidebar.nav_clicked.connect(self.show_page)
        self._sidebar.filters_changed.connect(self._on_filters_changed)

        self.setStatusBar(QStatusBar(self))
        self._build_menus()

        self.show_page("library")

    # ------------------------------------------------------------------
    def _build_menus(self) -> None:
        bar: QMenuBar = self.menuBar()
        file_menu = bar.addMenu("&File")
        exit_act = QAction(t("common-close"), self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        view_menu = bar.addMenu("&View")
        for item in NAV_ITEMS:
            act = QAction(t(item["label_key"]), self)
            act.triggered.connect(lambda _checked=False, k=item["key"]: self.show_page(k))
            view_menu.addAction(act)

        help_menu = bar.addMenu("&Help")
        about_act = QAction(t("kms-settings-about"), self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    def _show_about(self) -> None:
        QMessageBox.about(
            self, t("kms-settings-about"),
            f"{t('kms-app-title')}\n\n{t('kms-settings-version')}: 0.1.0\n\n"
            "PyQt6 port of SciKMS v3.1 (https://github.com/...)",
        )

    # ------------------------------------------------------------------
    def show_page(self, key: str) -> None:
        if key not in self._key_to_index:
            return
        self._stack.setCurrentIndex(self._key_to_index[key])
        page = self._pages.get(key)
        if hasattr(page, "refresh"):
            page.refresh()
        self.page_changed.emit(key)
        self._sidebar.set_active(key)
        self.statusBar().showMessage(t(f"nav-{key}"), 2000)

    def current_filters(self) -> dict:
        return self._sidebar.current_filters()

    def _on_filters_changed(self) -> None:
        page = self._stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()

    def refresh_sidebar_stats(self) -> None:
        self._sidebar.refresh_stats()
