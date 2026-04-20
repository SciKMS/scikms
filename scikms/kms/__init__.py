"""scikms KMS — clinical knowledge management domain.

Port of the SciKMS v3.1 (y-khoa) Streamlit app's domain layer: SQLite+FTS5
database, clinical classifiers (EBM/PICO/specialty), PDF/DOI/PubMed importers,
and figure atlas extraction. UI-agnostic — the PyQt6 pages in scikms.gui.kms
consume these services.
"""

from pathlib import Path

from scikms.consts import DATA_DIR


def _default_data_root() -> Path:
    root = Path(DATA_DIR) / "kms"
    root.mkdir(parents=True, exist_ok=True)
    return root


DATA_ROOT: Path = _default_data_root()
DB_PATH: Path = DATA_ROOT / "kms.db"
STORAGE_DIR: Path = DATA_ROOT / "storage"
ATLAS_ROOT: Path = DATA_ROOT / "atlas"
CONFIG_PATH: Path = DATA_ROOT / "kms_config.json"


def set_data_root(root: Path) -> None:
    """Rebind DATA_ROOT and all derived paths. Call before init_db().

    Used by tests (tmp_path) and by user preference ('Use this folder for data').
    """
    global DATA_ROOT, DB_PATH, STORAGE_DIR, ATLAS_ROOT, CONFIG_PATH
    DATA_ROOT = Path(root)
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    DB_PATH = DATA_ROOT / "kms.db"
    STORAGE_DIR = DATA_ROOT / "storage"
    ATLAS_ROOT = DATA_ROOT / "atlas"
    CONFIG_PATH = DATA_ROOT / "kms_config.json"
    STORAGE_DIR.mkdir(exist_ok=True)
    ATLAS_ROOT.mkdir(exist_ok=True)
    (ATLAS_ROOT / "_thumbs").mkdir(exist_ok=True)


# Ensure default dirs exist on import.
STORAGE_DIR.mkdir(exist_ok=True)
ATLAS_ROOT.mkdir(exist_ok=True)
(ATLAS_ROOT / "_thumbs").mkdir(exist_ok=True)
