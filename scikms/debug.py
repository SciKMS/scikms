from contextlib import contextmanager
from unittest.mock import MagicMock

from scikms.app import create_config


@contextmanager
def mock_app():
    app = MagicMock()
    app.config = create_config()
    yield app
