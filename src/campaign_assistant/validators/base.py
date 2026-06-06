from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class ValidationContext:
    file_path: Path
    selected_checks: list[str]
    export_excel: bool = True


@dataclass
class ValidationResult:
    validator_name: str
    success: bool
    payload: dict[str, Any]
    warnings: list[str] | None = None


class BaseValidator(Protocol):
    name: str

    def is_applicable(self, context: ValidationContext) -> tuple[bool, str]:
        ...

    def run(self, context: ValidationContext) -> ValidationResult:
        ...