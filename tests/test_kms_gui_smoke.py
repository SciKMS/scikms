"""Smoke tests for the PyQt6 + qfluentwidgets KMS UI.

Notes:
- ``FluentWindow`` (the shell) requires a native QPA platform; offscreen
  segfaults during the underlying frameless-window initialization on macOS.
  We therefore test individual page widgets (which are plain ``QWidget``
  subclasses styled with Fluent components) instead of constructing the
  full ``MainWindow``. Native end-to-end smoke is intended for manual runs.
"""

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _isolated_data_root(tmp_path):
    from scikms import kms

    kms.set_data_root(tmp_path)
    from scikms.kms.db import init_db

    init_db()
    yield


@pytest.fixture
def fake_main():
    """A MagicMock standing in for MainWindow — pages only call shim methods."""
    mw = MagicMock()
    mw.current_filters.return_value = {
        "status": "all",
        "starred": False,
        "project": "",
        "evidence": "",
        "design": "",
        "specialty": "",
        "scope": "all",
    }
    return mw


@pytest.mark.parametrize(
    "page_module,class_name",
    [
        ("scikms.gui.kms.pages.library", "LibraryPage"),
        ("scikms.gui.kms.pages.import_page", "ImportPage"),
        ("scikms.gui.kms.pages.search", "SearchPage"),
        ("scikms.gui.kms.pages.atlas", "AtlasPage"),
        ("scikms.gui.kms.pages.stats", "StatsPage"),
        ("scikms.gui.kms.pages.rename", "RenamePage"),
        ("scikms.gui.kms.pages.export", "ExportPage"),
        ("scikms.gui.kms.pages.settings", "SettingsPage"),
    ],
)
def test_page_constructs(qtbot, fake_main, page_module, class_name):
    import importlib

    module = importlib.import_module(page_module)
    cls = getattr(module, class_name)
    page = cls(fake_main)
    qtbot.addWidget(page)
    # refresh() should be safe even on an empty database
    if hasattr(page, "refresh"):
        page.refresh()


def test_note_editor_dialog_constructs(qtbot):
    from PyQt6.QtWidgets import QWidget
    from scikms.kms.db import insert_paper

    pid = insert_paper(
        {
            "md5": "x",
            "original_filename": "f.pdf",
            "renamed_filename": "f.pdf",
            "title": "Sample",
            "authors": "A",
            "year": 2024,
            "journal": "J",
            "doi": "",
            "abstract": "",
            "keywords": "",
            "full_text": "",
            "tags": "[]",
            "notes": "",
            "highlights": "[]",
            "status": "unread",
            "starred": 0,
            "pages": 0,
            "added_at": "2024-01-01",
            "file_path": "",
            "project": "",
            "reading_position": 0,
            "evidence_level": "",
            "study_design": "",
            "clinical_specialty": "",
            "pico_json": "{}",
            "risk_of_bias_json": "{}",
            "impact_factor": 0.0,
            "citation_count": 0,
        }
    )
    # MessageBoxBase requires a non-None parent (it queries parent.width())
    parent = QWidget()
    qtbot.addWidget(parent)
    parent.resize(800, 600)
    from scikms.gui.kms.dialogs.note_editor import NoteEditorDialog

    dlg = NoteEditorDialog(pid, parent)
    qtbot.addWidget(dlg)


def test_image_viewer_dialog_constructs(qtbot, tmp_path):
    fake = tmp_path / "fake.png"
    fake.write_bytes(
        b""
    )  # not a real PNG; QPixmap.isNull() will be True, but ctor still runs
    from scikms.gui.kms.dialogs.image_viewer import ImageViewerDialog

    dlg = ImageViewerDialog(fake)
    qtbot.addWidget(dlg)


def test_theme_setters_callable():
    """Smoke: theme/accent helpers are importable and callable without QApplication."""
    from qfluentwidgets import Theme, setThemeColor

    # just verify the enum and helper exist
    assert Theme.AUTO is not None
    setThemeColor("#4338CA")
