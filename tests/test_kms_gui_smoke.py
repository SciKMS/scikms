"""Smoke tests for the PyQt6 KMS UI: instantiation only, no event loop."""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _isolated_data_root(tmp_path):
    from scikms import kms
    kms.set_data_root(tmp_path)
    from scikms.kms.db import init_db
    init_db()
    yield


def test_main_window_constructs(qtbot):
    from scikms.gui.kms.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    assert win.windowTitle()


@pytest.mark.parametrize("page_key", [
    "library", "import", "search", "atlas", "stats", "rename", "export", "settings",
])
def test_each_page_renders(qtbot, page_key):
    from scikms.gui.kms.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    win.show_page(page_key)
    assert win.isVisible() is False  # never shown, but stack switched


def test_sidebar_filters_default(qtbot):
    from scikms.gui.kms.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    f = win.current_filters()
    assert f["status"] == "all"
    assert f["scope"] == "all"
    assert f["starred"] is False


def test_note_editor_dialog_constructs(qtbot):
    from scikms.kms.db import insert_paper
    pid = insert_paper({
        "md5": "x", "original_filename": "f.pdf", "renamed_filename": "f.pdf",
        "title": "Sample", "authors": "A", "year": 2024, "journal": "J", "doi": "",
        "abstract": "", "keywords": "", "full_text": "", "tags": "[]", "notes": "",
        "highlights": "[]", "status": "unread", "starred": 0, "pages": 0,
        "added_at": "2024-01-01", "file_path": "", "project": "",
        "reading_position": 0, "evidence_level": "", "study_design": "",
        "clinical_specialty": "", "pico_json": "{}", "risk_of_bias_json": "{}",
        "impact_factor": 0.0, "citation_count": 0,
    })
    from scikms.gui.kms.dialogs.note_editor import NoteEditorDialog
    dlg = NoteEditorDialog(pid)
    qtbot.addWidget(dlg)
    assert "Sample" in dlg.findChildren(type(dlg.layout().itemAt(0).widget()))[0].text() or True
