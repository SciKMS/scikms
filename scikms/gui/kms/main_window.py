"""scikms.gui.kms.main_window — KMS main window using FluentWindow.

The Fluent navigation bar is on the left (NavigationInterface). Each page is
a sub-interface, registered via :meth:`addSubInterface`. There is no separate
sidebar widget anymore — per-page filters live inside each page.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from qfluentwidgets import (
    FluentIcon, FluentWindow, NavigationItemPosition, setTheme, Theme,
)

from scikms.i18n import t

from .pages.atlas import AtlasPage
from .pages.export import ExportPage
from .pages.import_page import ImportPage
from .pages.library import LibraryPage
from .pages.rename import RenamePage
from .pages.search import SearchPage
from .pages.settings import SettingsPage
from .pages.stats import StatsPage


# (page_key, icon_attr_name, label_key) — icon names mapped to FluentIcon enum.
_PAGES: list[tuple[str, str, str]] = [
    ("library",  "LIBRARY",  "nav-library"),
    ("import",   "DOWNLOAD", "nav-import"),
    ("search",   "SEARCH",   "nav-search"),
    ("atlas",    "PHOTO",    "nav-atlas"),
    ("stats",    "PIE_SINGLE", "nav-stats"),
    ("rename",   "EDIT",     "nav-rename"),
    ("export",   "SHARE",    "nav-export"),
    ("settings", "SETTING",  "nav-settings"),
]


class MainWindow(FluentWindow):
    """Top-level Fluent window. Hosts navigation + stacked content."""

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

        # Each page widget needs an objectName for FluentWindow's stack routing.
        for key, page in self._pages.items():
            page.setObjectName(f"kms-page-{key}")

        # Navigation: 7 main items at top, settings at bottom.
        for key, icon_name, label_key in _PAGES:
            position = (
                NavigationItemPosition.BOTTOM if key == "settings"
                else NavigationItemPosition.TOP
            )
            icon = getattr(FluentIcon, icon_name, FluentIcon.HOME)
            self.addSubInterface(self._pages[key], icon, t(label_key), position)

        self.stackedWidget.currentChanged.connect(self._on_page_changed)
        self.show_page("library")

    # ------------------------------------------------------------------
    def show_page(self, key: str) -> None:
        page = self._pages.get(key)
        if not page:
            return
        self.switchTo(page)

    def _on_page_changed(self, _idx: int) -> None:
        page = self.stackedWidget.currentWidget()
        for key, p in self._pages.items():
            if p is page:
                if hasattr(page, "refresh"):
                    page.refresh()
                self.page_changed.emit(key)
                return

    # Backwards-compat shims so existing pages don't break.
    def current_filters(self) -> dict:
        """Legacy filter accessor. Filters now live per-page."""
        return {
            "status": "all", "starred": False, "project": "",
            "evidence": "", "design": "", "specialty": "", "scope": "all",
        }

    def refresh_sidebar_stats(self) -> None:
        """No-op kept for legacy callers; stats live in StatsPage now."""
