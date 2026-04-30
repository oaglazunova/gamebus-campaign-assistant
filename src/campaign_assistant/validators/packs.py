from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.native_targetpointsreachable import (
    run_native_targetpointsreachable_check,
)
from campaign_assistant.checker.schema import (
    CAPABILITY_GATED_CHECKS,
    TARGETPOINTSREACHABLE,
    TTMSTRUCTURE,
    UNIVERSAL_CHECKS,
)
from campaign_assistant.checker.wrapper import run_campaign_checks
from campaign_assistant.reasoning import PointGatekeepingService
from campaign_assistant.validators.base import BaseValidator, ValidationContext, ValidationResult


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


def _validator_applicability(context: ValidationContext) -> dict[str, bool]:
    summary = context.capability_summary or {}
    return dict(summary.get("validator_applicability") or {})


def _theory_tags(context: ValidationContext) -> set[str]:
    metadata_bundle = context.metadata_bundle
    if metadata_bundle is None:
        return set()

    theory_sources = getattr(metadata_bundle, "theory_sources", []) or []
    tags: set[str] = set()

    for source in theory_sources:
        for tag in getattr(source, "tags", []) or []:
            normalized = str(tag).strip().lower()
            if normalized:
                tags.add(normalized)

    return tags


class UniversalStructuralValidator(BaseValidator):
    name = "universal_structural"

    def is_applicable(self, context: ValidationContext) -> tuple[bool, str]:
        checks = _selected_subset(context.selected_checks, UNIVERSAL_CHECKS)
        if not checks:
            return False, "No universal checks were selected."
        return True, "Universal structural validation is always applicable."

    def run(self, context: ValidationContext) -> ValidationResult:
        checks = _selected_subset(context.selected_checks, UNIVERSAL_CHECKS)
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

        applicability = _validator_applicability(context)
        if TARGETPOINTSREACHABLE in applicability:
            enabled = bool(applicability[TARGETPOINTSREACHABLE])
            return enabled, (
                "Applicability comes from validator_applicability."
                if enabled
                else "validator_applicability disabled target-points reachability."
            )

        capabilities = (context.capability_summary or {}).get("capabilities", {}) or {}
        if capabilities.get("uses_progression") is False:
            return False, "Campaign explicitly does not use progression."

        return True, "Target-points reachability is applicable."

    def run(self, context: ValidationContext) -> ValidationResult:
        native_result = run_native_targetpointsreachable_check(context.file_path)
        payload = _checker_payload_from_single_native_result(
            file_path=context.file_path,
            check_name=TARGETPOINTSREACHABLE,
            native_result=native_result,
        )
        return ValidationResult(validator_name=self.name, success=True, payload=payload)


class PointGatekeepingValidator(BaseValidator):
    name = "point_gatekeeping"

    def __init__(self) -> None:
        self.service = PointGatekeepingService()

    def is_applicable(self, context: ValidationContext) -> tuple[bool, str]:
        capabilities = (context.capability_summary or {}).get("capabilities", {}) or {}
        selected = _selected_subset(context.selected_checks, CAPABILITY_GATED_CHECKS)

        if not selected and TARGETPOINTSREACHABLE not in context.selected_checks:
            return False, "No progression-aware checks were selected."

        if capabilities.get("uses_progression") is False:
            return False, "Campaign explicitly does not use progression."

        return True, "Point/gatekeeping reasoning is applicable."

    def run(self, context: ValidationContext) -> ValidationResult:
        payload = self.service.analyze(
            campaign_file=context.file_path,
            point_rules=context.point_rules,
            task_roles=context.task_roles,
        )
        return ValidationResult(validator_name=self.name, success=True, payload=payload)


class TTMValidator(BaseValidator):
    name = TTMSTRUCTURE

    def is_applicable(self, context: ValidationContext) -> tuple[bool, str]:
        if TTMSTRUCTURE not in context.selected_checks:
            return False, "TTM structure was not selected."

        applicability = _validator_applicability(context)
        if TTMSTRUCTURE in applicability:
            enabled = bool(applicability[TTMSTRUCTURE])
            return enabled, (
                "Applicability comes from validator_applicability."
                if enabled
                else "validator_applicability disabled TTM."
            )

        capabilities = (context.capability_summary or {}).get("capabilities", {}) or {}
        if capabilities.get("uses_ttm") is True:
            return True, "TTM capability is enabled."

        theory_tags = _theory_tags(context)
        if "ttm" in theory_tags or "transtheoretical_model" in theory_tags:
            return True, "Theory sources indicate TTM usage."

        return False, "TTM is not applicable."

    def run(self, context: ValidationContext) -> ValidationResult:
        payload = run_campaign_checks(
            file_path=context.file_path,
            checks=[TTMSTRUCTURE],
            export_excel=False,
        )
        return ValidationResult(validator_name=self.name, success=True, payload=payload)