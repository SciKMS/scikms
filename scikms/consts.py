"""Platform-specific filesystem paths.

Only two symbols leak outside this module today:
- ``DATA_DIR``: consumed by :mod:`scikms.kms` to place the SQLite DB, PDF
  storage and figure atlas under a stable per-user location.
- ``LOG_FILE``: consumed by :mod:`scikms` for file-mode logger config.

The rest (cache / state / themes / plugins / rc-file) came from FeelUOwn
upstream and have no runtime path into SciKMS today. They can be reintroduced
the first time a feature actually needs them.
"""

import os
import sys


USER_HOME = os.environ.get("SCIKMS_USER_HOME", os.path.expanduser("~"))


if sys.platform == "linux":
    _DATA_BASE = os.environ.get(
        "XDG_DATA_HOME", os.path.join(USER_HOME, ".local", "share")
    )
    _STATE_BASE = os.environ.get(
        "XDG_STATE_HOME", os.path.join(USER_HOME, ".local", "state")
    )
    DATA_DIR = os.path.join(_DATA_BASE, "scikms")
    LOG_FILE = os.path.join(_STATE_BASE, "scikms", "stdout.log")
else:
    _HOME_DIR = os.path.join(USER_HOME, ".scikms")
    DATA_DIR = os.path.join(_HOME_DIR, "data")
    LOG_FILE = os.path.join(_HOME_DIR, "stdout.log")
