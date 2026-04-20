.PHONY: all pytest lint flake8 pylint mypy yapf clean clean_py clean_emacs

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
PYLINT_PKGS+=scikms/fuoexec/
PYLINT_PKGS+=scikms/server/

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
