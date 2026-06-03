from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.native_targetpointsreachable import (
    run_native_targetpointsreachable_check,
)
from campaign_assistant.checker.schema import (
    CONSISTENCY,
    REACHABILITY,
    SECRETS,
    SPELLCHECKER,
    TARGETPOINTSREACHABLE,
    VISUALIZATIONINTERN,
)
from campaign_assistant.checker.wrapper import run_campaign_checks
from campaign_assistant.validators.base import BaseValidator, ValidationContext, ValidationResult


UNIVERSAL_STRUCTURAL_CHECKS = [
    SECRETS,
    SPELLCHECKER,
]

EXPORT_STRUCTURAL_CHECKS = [
    REACHABILITY,
    CONSISTENCY,
    VISUALIZATIONINTERN,
]

ALL_EXPORT_BASED_STRUCTURAL_CHECKS = [
    *UNIVERSAL_STRUCTURAL_CHECKS,
    *EXPORT_STRUCTURAL_CHECKS,
]


def _selected_subset(selected_checks: list[str], allowed_checks: list[str]) -> list[str]:
    return [name for name in selected_checks if name in allowed_checks]


def _sort_prioritized_issues(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            3 if item.get("severity") == "high" else 2 if item.get("severity") == "medium" else 1,
            1 if item.get("active_wave") else 0,
        ),
        reverse=True,
    )


def _checker_payload_from_single_native_result(
    *,
    file_path: str | Path,
    check_name: str,
    native_result: dict[str, Any],
) -> dict[str, Any]:
    issue_dicts = [issue.to_dict() for issue in (native_result.get("issues") or [])]
    status = native_result.get("status", "Passed")

    return {
        "file_name": Path(file_path).name,
        "analyzed_at": pd.Timestamp.now().isoformat(),
        "checks_run": [check_name],
        "summary": {
            "total_issues": len(issue_dicts),
            "passed_checks": [check_name] if status == "Passed" else [],
            "failed_checks": [check_name] if status == "Failed" else [],
            "errored_checks": [check_name] if status == "Error" else [],
            "issue_count_by_check": {
                check_name: len(issue_dicts),
            },
        },
        "waves": [],
        "issues_by_check": {
            check_name: issue_dicts,
        },
        "prioritized_issues": _sort_prioritized_issues(issue_dicts),
        "notes": list(native_result.get("notes") or []),
        "excel_report_path": None,
    }


class ExportStructuralValidator(BaseValidator):
    """
    Runs reliable export-based structural checks.

    Paper-release scope:
    - no metadata;
    - no sidecars;
    - no capability gating;
    - no gatekeeping semantics;
    - no legacy TTM validator.
    """

    name = "export_structural"

    def is_applicable(self, context: ValidationContext) -> tuple[bool, str]:
        checks = _selected_subset(
            context.selected_checks,
            ALL_EXPORT_BASED_STRUCTURAL_CHECKS,
        )
        if not checks:
            return False, "No export-based structural checks were selected."
        return True, "Export-based structural validation is applicable."

    def run(self, context: ValidationContext) -> ValidationResult:
        checks = _selected_subset(
            context.selected_checks,
            ALL_EXPORT_BASED_STRUCTURAL_CHECKS,
        )
        payload = run_campaign_checks(
            file_path=context.file_path,
            checks=checks,
            export_excel=context.export_excel,
        )
        return ValidationResult(validator_name=self.name, success=True, payload=payload)


class TargetPointsReachableValidator(BaseValidator):
    name = TARGETPOINTSREACHABLE

    def is_applicable(self, context: ValidationContext) -> tuple[bool, str]:
        if TARGETPOINTSREACHABLE not in context.selected_checks:
            return False, "Target-points reachability was not selected."
        return True, "Target-points reachability is export-computable."

    def run(self, context: ValidationContext) -> ValidationResult:
        native_result = run_native_targetpointsreachable_check(context.file_path)
        payload = _checker_payload_from_single_native_result(
            file_path=context.file_path,
            check_name=TARGETPOINTSREACHABLE,
            native_result=native_result,
        )
        return ValidationResult(validator_name=self.name, success=True, payload=payload)


# Backward-compatible aliases for old imports/tests during cleanup.
UniversalStructuralValidator = ExportStructuralValidator
ConfigurationGatedStructuralValidator = ExportStructuralValidator