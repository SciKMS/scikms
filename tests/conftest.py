import pytest


# Add one fixture to avoid duplication in isolation-DB test
@pytest.fixture
def kms_db(tmp_path):
    from scikms import kms
    from scikms.kms.db import init_db

    kms.set_data_root(tmp_path)
    init_db()
    return tmp_path
