"""Compatibility facade for KMS database operations.

The implementation is split across DB infrastructure, repositories, and
services. Existing callers can continue importing from ``scikms.kms.db``.
"""

# from scikms.kms.db.connection import db_conn
# from scikms.kms.db.schema import init_db
from .connection import db_conn
from .schema import init_db

from scikms.kms.repositories.papers import (
    get_all_papers,
    get_all_projects,
    get_paper_by_id,
    get_papers_count,
    insert_paper,
    update_paper,
)
from scikms.kms.services.papers import check_duplicate, delete_paper
from scikms.kms.services.search import search_papers
from scikms.kms.services.stats import get_db_stats
from scikms.kms.services.tags import get_tag_dict, save_tag_dict

__all__ = [
    "check_duplicate",
    "db_conn",
    "delete_paper",
    "get_all_papers",
    "get_all_projects",
    "get_db_stats",
    "get_paper_by_id",
    "get_papers_count",
    "get_tag_dict",
    "init_db",
    "insert_paper",
    "save_tag_dict",
    "search_papers",
    "update_paper",
]
