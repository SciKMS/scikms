"""JSON config persistence repository."""

from __future__ import annotations

import json

from scikms import kms as _kms


def read_config() -> dict:
    if _kms.CONFIG_PATH.exists():
        try:
            return json.loads(_kms.CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(cfg: dict) -> None:
    _kms.CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_custom_tag_dict() -> list[str] | None:
    return read_config().get("custom_tag_dict")


def save_custom_tag_dict(terms: list[str]) -> None:
    cfg = read_config()
    cfg["custom_tag_dict"] = terms
    save_config(cfg)
