# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for scikms — works on macOS (.app) and Windows (.exe).

Run from project root:
    uv run pyinstaller scikms.spec

Output:
    macOS:   dist/SciKMS.app
    Windows: dist/SciKMS/SciKMS.exe       (folder mode, faster startup)
             dist/SciKMS.exe              (if --onefile is enabled below)
"""
from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules


HERE = Path(SPECPATH).resolve()  # SPECPATH provided by PyInstaller
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

ICON = str(HERE / "scikms" / "assets" / ("icon.icns" if IS_MAC else "icon.ico"))

# --- Collect everything that needs runtime resources -----------------------
# qfluentwidgets ships icons / themes / QSS / fonts inside its package.
qfw_datas, qfw_binaries, qfw_hiddens = collect_all("qfluentwidgets")

# scikms.i18n.assets ships .ftl translations — include both vi-VN and en-US.
i18n_datas = collect_data_files("scikms.i18n", include_py_files=False)

# Qt Pdf modules (optional at runtime but we want them shipped).
qtpdf_hiddens = (
    collect_submodules("PyQt6.QtPdf")
    + collect_submodules("PyQt6.QtPdfWidgets")
)

# darkdetect — Fluent theme auto-follow.
dd_hiddens = collect_submodules("darkdetect")

# Data files + hidden imports merged.
datas = qfw_datas + i18n_datas
binaries = qfw_binaries
hiddenimports = qfw_hiddens + qtpdf_hiddens + dd_hiddens + [
    # fluent-runtime uses importlib.resources at runtime; force the package in.
    "fluent.runtime",
    "scikms.kms",
    "scikms.gui.kms",
]

# --- Analysis --------------------------------------------------------------
a = Analysis(
    [str(HERE / "scikms" / "__main__.py")],
    pathex=[str(HERE)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # trim the fat — tests/dev tools never run in the bundle
        "pytest", "pytest_asyncio", "pytest_qt", "pytest_mock", "pytest_cov",
        "flake8", "pylint", "mypy", "yapf",
        "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets",  # unused
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

# --- Platform-specific bundling -------------------------------------------
if IS_MAC:
    # Folder build first, then BUNDLE wraps it in SciKMS.app.
    exe = EXE(
        pyz, a.scripts,
        [],
        exclude_binaries=True,
        name="SciKMS",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        target_arch=None,  # "arm64" or "x86_64" or None for current host
        icon=ICON,
    )
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=False, upx_exclude=[],
        name="SciKMS",
    )
    app = BUNDLE(
        coll,
        name="SciKMS.app",
        icon=ICON,
        bundle_identifier="com.scikms.app",
        info_plist={
            "CFBundleName": "SciKMS",
            "CFBundleDisplayName": "SciKMS",
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "NSHumanReadableCopyright": "GPL-3.0-or-later · scikms contributors",
        },
    )
else:
    # Windows (and Linux): folder-mode exe. Swap to onefile by moving args
    # from COLLECT into EXE (see PyInstaller docs) if you prefer a single .exe.
    exe = EXE(
        pyz, a.scripts,
        [],
        exclude_binaries=True,
        name="SciKMS",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        icon=ICON,
    )
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=False, upx_exclude=[],
        name="SciKMS",
    )
