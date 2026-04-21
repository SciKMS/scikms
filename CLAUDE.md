# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SciKMS — a local-first, offline PyQt6 desktop app (macOS/Windows/Linux) for managing a personal collection of medical research papers. Core features: PDF/DOI/PubMed import, clinical classifiers (EBM level, study design, specialty, PICO), figure atlas extraction, SQLite+FTS5 dual-channel full-text search (content + notes), and export to Zotero/EndNote/LaTeX/Excel. UI is Fluent-styled (`pyqt6-fluent-widgets`) and bilingual (Vietnamese/English) via Fluent (Mozilla) .ftl files.

Python ≥ 3.10; `uv` is the package/tooling frontend for everything.

## Common commands

All commands assume `uv sync --dev` has been run. Never invoke the global `pytest`/`flake8`/etc. — always go through `uv run` so the project venv is used.

```bash
# Run the app
uv run scikms                               # or: uv run python -m scikms

# Tests (Qt widgets need an offscreen platform; Makefile sets it)
make pytest
QT_QPA_PLATFORM=offscreen uv run pytest -p no:faulthandler tests/test_kms_db.py
QT_QPA_PLATFORM=offscreen uv run pytest -p no:faulthandler tests/test_kms_db.py::test_name

# Lint / typecheck (note: pylint and mypy are narrowed — see Makefile PYLINT_PKGS / MYPY_PKGS)
make flake8
make pylint
make mypy
make lint                                   # flake8 + pylint
make test                                   # lint + pytest

# Autoformat
make yapf                                   # yapf, column_limit=89

# Bundle (PyInstaller; spec auto-detects platform)
make bundle-mac                             # → dist/SciKMS.app
make bundle-win                             # → dist\SciKMS\SciKMS.exe  (Windows host only)
make sign-mac                               # ad-hoc codesign so Gatekeeper stops nagging
make dmg                                    # requires `brew install create-dmg`
```

Line length is **89** (enforced by flake8 and yapf).

## Architecture

### Layering

UI is strictly separated from the domain. Anything importing PyQt6 lives under `scikms/gui/` or `scikms/app/`; everything in `scikms/kms/`, `scikms/server/`, `scikms/serializers/`, and `scikms/utils/` must stay UI-agnostic and safely importable in headless tests.

```
scikms/
  __main__.py       # entry point — reads QSettings, init_db(), shows MainWindow
  plugin.py         # Plugin / PluginsManager — discovers dirs + `scikms.plugins_v1` entry points
  config.py         # Config tree with deffield(); plugins attach subconfigs under it
  consts.py         # XDG paths on Linux; ~/.scikms elsewhere
  app/              # AppMode flags (server / gui / cli); there is no monolithic App class
  kms/              # Clinical domain: db.py, clinical.py, importers.py, atlas.py, config.py
  gui/              # PyQt6 UI
    kms/
      main_window.py   # FluentWindow; pages registered as sub-interfaces
      pages/           # library, import, search, atlas, stats, rename, export, settings
      dialogs/
    widgets/, components/, theme.py, hotkey.py
  i18n/             # Fluent (.ftl) localization; `t(msg_id, ...)` is the translation function
    assets/{en-US,vi-VN}/kms.ftl
  server/           # FuoServer + dslv1 parser + pubsub/rpc — DSL-driven RPC layer, not HTTP
  serializers/      # Plain-text formatter infrastructure
  utils/            # dispatch (Signal), aio, cache, reader, request, router, etc.
```

### Data layer (`scikms.kms`)

`scikms/kms/__init__.py` holds mutable module-level paths (`DATA_ROOT`, `DB_PATH`, `STORAGE_DIR`, `ATLAS_ROOT`, `CONFIG_PATH`). `set_data_root(path)` rebinds all of them and **must be called before `init_db()`**. Tests use `tmp_path` with this. User selection persists in `QSettings("scikms", "kms")` under `data_root` and is applied in `__main__.main()`.

`scikms.kms.db`:
- SQLite with `PRAGMA journal_mode=WAL`; connections via the `db_conn()` context manager (auto-commit on success, auto-rollback on exception).
- Two FTS5 virtual tables on the `papers` table: `papers_fts` (title/authors/abstract/keywords/full_text) and `papers_notes_fts` (notes) — dual-channel search is deliberate, don't collapse them.
- This module is a direct port of SciKMS v3.1 y-khoa's `modules/db.py`; the only substantive delta is removing Streamlit `@st.cache_data` decorators and reading paths from `scikms.kms` instead of hardcoding CWD. When porting more from y-khoa, preserve this pattern.

`scikms.kms.clinical` is pure functions (EBM/study-design/specialty classifiers, PICO parser, auto-tag). `scikms.kms.importers` takes raw `(bytes, filename)` tuples — never pass Streamlit `UploadedFile` objects — and cache invalidation is the caller's responsibility. `scikms.kms.atlas` extracts figures via PyMuPDF (`fitz`) and stores metadata as parquet/csv.

### i18n

Always route user-visible strings through `scikms.i18n.t("msg-id", var=value)`. Default locale comes from `SCIKMS_LOCALE` env var → `QSettings("scikms","kms").value("locale")` → OS locale → `en_US`. `__main__.main()` defaults to `vi-VN` if nothing is set. Add new keys to both `scikms/i18n/assets/en-US/kms.ftl` and `scikms/i18n/assets/vi-VN/kms.ftl`; missing keys fall back to `en-US` then `zh-CN`.

### Plugins

`plugins_mgr` scans `USER_PLUGINS_DIR` (under the XDG/`~/.scikms` data dir) and setuptools entry-point group `scikms.plugins_v1`. A plugin module must expose `__alias__`, `__desc__`, `__version__`, plus `enable(app)` / `disable(app)`; optionally `init_config(config)`. A plugin named `scikms_foo` also gets the shorter config alias `foo` so users write `app.foo.X = Y` instead of `app.scikms_foo.X = Y`.

### Bundling

`scikms.spec` is cross-platform — the same spec file is consumed by `pyinstaller` on macOS and Windows. Keep PyInstaller hidden-import / data-files entries in sync when adding packages that use `importlib.resources` or dynamic imports (notably: `fluent.runtime`, `qfluentwidgets` assets, `PyQt6.QtPdf*`, `darkdetect`). Don't add `PyQt6.QtWebEngine*` — it's in the `excludes` list for bundle size.

## Repo conventions

- `pylint` and `mypy` are intentionally narrowed (see `PYLINT_PKGS`, `MYPY_PKGS`, `MYPY_STRICT_PKGS` in the Makefile). Widen them as modules stabilize; don't expect a green run across the whole tree.
- `make test` is `lint + pytest`; run it before declaring work done.
- `pytest` options (`-q`, `--cov=scikms`, `asyncio_mode=auto`) are set in `pyproject.toml` — don't pass them manually.
- Main branch is protected by rulesets in `.github/rulesets/` (no force-push, no merge commits, squash/rebase only). Releases are manual via `workflow_dispatch` on `macos-release.yml` / `windows-release.yml`; there is no CI test workflow.
- Theme color `#4338CA` (indigo) and Fluent `Theme.AUTO` are the defaults; respect `QSettings("scikms","kms").value("theme")` when touching theming.
