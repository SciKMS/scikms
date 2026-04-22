"""scikms — clinical knowledge manager (PyQt6 desktop).

Top-level package. Import site effects are kept minimal so headless tests and
tooling can ``import scikms`` without spinning up any Qt or filesystem state.
"""

from importlib.metadata import version as _v, PackageNotFoundError as _E
try:
    __version__ = _v("scikms")
except _E:
    __version__ = "0.1.0"
