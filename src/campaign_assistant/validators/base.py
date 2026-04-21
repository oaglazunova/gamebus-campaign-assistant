from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ValidationContext:
    file_path: Path
    selected_checks: list[str]
    export_excel: bool
    analysis_profile: dict[str, Any] = field(default_factory=dict)
    point_rules: dict[str, Any] = field(default_factory=dict)
    task_roles: list[dict[str, Any]] = field(default_factory=list)
    metadata_bundle: Any = None
    capability_summary: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationResult:
    validator_name: str
    success: bool
    payload: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BaseValidator:
    name = "base_validator"

    def is_applicable(self, context: ValidationContext) -> tuple[bool, str]:
        return True, "applicable"

    def run(self, context: ValidationContext) -> ValidationResult:
        raise NotImplementedError