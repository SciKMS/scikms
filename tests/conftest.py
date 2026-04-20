from unittest.mock import MagicMock
import pytest


@pytest.fixture
def app_mock():
    return MagicMock()
