.PHONY: all pytest lint flake8 pylint mypy yapf clean clean_py clean_emacs \
        bundle bundle-mac bundle-win bundle-clean dmg sign-mac

all: pytest

# -- test --
pytest:
	QT_QPA_PLATFORM=offscreen uv run pytest -p no:faulthandler

# -- lint --
flake8:
	uv run flake8 scikms/ tests/

# Start narrow; widen PYLINT_PKGS as you stabilize more of the tree.
PYLINT_PKGS=
PYLINT_PKGS+=scikms/plugin.py
PYLINT_PKGS+=scikms/server/
PYLINT_PKGS+=scikms/kms/

pylint:
	uv run pylint ${PYLINT_PKGS}

MYPY_PKGS=
MYPY_PKGS+=scikms/app/
MYPY_STRICT_PKGS=
MYPY_STRICT_PKGS+=scikms/utils/reader.py
MYPY_STRICT_PKGS+=scikms/server/

mypy:
	uv run mypy ${MYPY_PKGS}
	uv run mypy --check-untyped-defs ${MYPY_STRICT_PKGS}

yapf:
	uv run yapf --in-place --recursive scikms/ tests/

# flake8 enforces coding style; pylint finds bugs; mypy improves readability.
lint: flake8 pylint

test: lint pytest

# -- housekeeping --
clean: clean_py clean_emacs

clean_py:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name ".mypy_cache" -type d -exec rm -rf {} +
	find . -name ".ruff_cache" -type d -exec rm -rf {} +

clean_emacs:
	find . -name "*~" -delete
	find . -name "#*#" -delete
	find . -name ".#*" -delete

# -- bundle (PyInstaller) --
# scikms.spec auto-detects platform; same command works on macOS and Windows.
# Requires `uv add --dev pyinstaller` first.

bundle:
	uv run --with pyinstaller pyinstaller --noconfirm scikms.spec

bundle-mac: bundle
	@echo "→ dist/SciKMS.app  (drag to /Applications)"
	@du -sh dist/SciKMS.app 2>/dev/null || true

bundle-win: bundle
	@echo "→ dist/SciKMS/SciKMS.exe  (folder mode; ship the whole folder)"

# Optional: ad-hoc codesign so macOS Gatekeeper stops nagging on personal builds.
sign-mac:
	codesign --force --deep --sign - dist/SciKMS.app

# Optional: build a .dmg installer (requires `brew install create-dmg`).
dmg: bundle-mac
	create-dmg --volname "SciKMS" --window-size 540 380 \
	  --icon "SciKMS.app" 140 190 --app-drop-link 400 190 \
	  dist/SciKMS-0.1.0.dmg dist/SciKMS.app

bundle-clean:
	rm -rf build dist *.spec.bak
