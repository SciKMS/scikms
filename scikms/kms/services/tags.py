"""Tag dictionary service."""

from __future__ import annotations

from scikms.kms.config import DEFAULT_TAG_DICT
from scikms.kms.repositories.config import get_custom_tag_dict, save_custom_tag_dict


def get_tag_dict() -> list[str]:
    return get_custom_tag_dict() or DEFAULT_TAG_DICT


def save_tag_dict(terms: list[str]) -> None:
    save_custom_tag_dict(terms)
