from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

"""
Represents the real record in DB
"""
@dataclass(slots=True)
class Paper:
    id: int
    md5: str = ""
    original_filename: str = ""
    renamed_filename: str = ""
    title: str = ""
    authors: str = ""
    year: int | None = None
    journal: str = ""
    doi: str = ""
    abstract: str = ""
    keywords: str = ""
    full_text: str = ""
    tags: str = ""
    # This notes can accept several notes from different places from the file
    notes: str = ""
    highlights: list[str] = field(default_factory=list)
    status: str = "unread"
    starred: int = 0
    pages: int = 0
    added_at: str = ""
    file_path: str = ""
    project: str = ""
    reading_position: int = 0
    evidence_level: str = ""
    study_design: str = ""
    clinical_specialty: str = ""
    pico: dict[str, Any] = field(default_factory=dict)
    risk_of_bias: dict[str, Any] = field(default_factory=dict)
    impact_factor: float = 0.0
    citation_count: int = 0

    # Note here: since the pyright does not accept int() or float() for the Any datatype
    # We need manually write the staticmethod to convert to int and float which
    # adds all of the error handling
    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Paper:

        return cls(
            id=cls._load_from_int(row["id"]),
            md5=row.get("md5") or "",
            original_filename=row.get("original_filename") or "",
            renamed_filename=row.get("renamed_filename") or "",
            title=row.get("title") or "",
            authors=row.get("authors") or "",
            year=cls._load_from_optional_int(row.get("year")),
            journal=row.get("journal") or "",
            doi=row.get("doi") or "",
            abstract=row.get("abstract") or "",
            keywords=row.get("keywords") or "",
            full_text=row.get("full_text") or "",
            tags=row.get("tags") or "",
            notes=row.get("notes") or "",
            highlights=cls._load_from_list(row.get("highlights")),
            status=row.get("status") or "unread",
            starred=cls._load_from_int(row.get("starred")),
            pages=cls._load_from_int(row.get("pages")),
            added_at=row.get("added_at") or "",
            file_path=row.get("file_path") or "",
            project=row.get("project") or "",
            reading_position=cls._load_from_int(row.get("reading_position")),
            evidence_level=row.get("evidence_level") or "",
            study_design=row.get("study_design") or "",
            clinical_specialty=row.get("clinical_specialty") or "",
            pico=cls._load_from_dict(row.get("pico_json")),
            risk_of_bias=cls._load_from_dict(row.get("risk_of_bias_json")),
            impact_factor=cls._load_from_float(row.get("impact_factor")),
            citation_count=cls._load_from_int(row.get("citation_count")),
        )
   
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self) 
        data["highlights"] = json.dumps(data["highlights"])
        data["pico_json"] = json.dumps(data.pop("pico"))
        data["risk_of_bias_json"] = json.dumps(data.pop("risk_of_bias"))

        return data

    # We use the staticmethod since it doesn't depend on any instance
    # of the class
    # It is just parsing to the correct value though :)))
    @staticmethod
    def _load_from_dict(value: Any) -> dict[str, Any]:
        if not value:
            return {}

        if isinstance(value, dict):
            return value

        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return {}

        if isinstance(parsed, dict):
            return parsed

        return {}

    @staticmethod
    def _load_from_list(value: Any) -> list[str]:
        if not value:
            return []

        if isinstance(value, list):
            return [str(val) for val in value]

        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return []

        if isinstance(parsed, list):
            return [str(val) for val in parsed]
        return []

    @staticmethod
    def _load_from_int(value: Any, default: int = 0) -> int:
        if value is None or value == "":
            return default

        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _load_from_optional_int(value: Any) -> int | None:
        if value is None or value == "":
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _load_from_float(value: Any, default: float = 0.0) -> float:
        if value is None or value == "":
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default



@dataclass(slots=True)
class PaperDuplicateRef:
    id: int 
    title: str = ""
    doi: str = ""

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> PaperDuplicateRef:
        return cls(
            id = Paper._load_from_int(row['id']),
            title = row.get("title") or "",
            doi = row.get("doi") or "",
        
        )


"""
Returns the search result in the services/ section
"""
@dataclass(slots = True)
class PaperSearchResult:
    paper: Paper 
    match_scope: str
    
    def add_scope(self, scope: str) -> None:
        """
        Adding the match_scope when searching (matched from content and notes)
        """
        if self.match_scope == scope:
            return 
        if self.match_scope == "default":
            self.match_scope = scope 
            return 

        # Get all the set of scope
        current_scope = set(self.match_scope.split('+'))
        current_scope.add(scope)
        # Since set is unordered, we need to reorder again
        self.match_scope = "+".join(sorted(current_scope))

