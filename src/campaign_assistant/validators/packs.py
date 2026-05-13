from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.native_targetpointsreachable import (
    run_native_targetpointsreachable_check,
)
from campaign_assistant.checker.schema import (
    CONSISTENCY,
    GATEKEEPINGSEMANTICS,
    REACHABILITY,
    SECRETS,
    SPELLCHECKER,
    TARGETPOINTSREACHABLE,
    VISUALIZATIONINTERN,
)
from campaign_assistant.checker.wrapper import run_campaign_checks
from campaign_assistant.reasoning import PointGatekeepingService
from campaign_assistant.validators.base import BaseValidator, ValidationContext, ValidationResult


UNIVERSAL_STRUCTURAL_CHECKS = [
    SECRETS,
    SPELLCHECKER,
]

CONFIGURATION_GATED_STRUCTURAL_CHECKS = [
    REACHABILITY,
    CONSISTENCY,
    VISUALIZATIONINTERN,
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


def _validator_applicability(context: ValidationContext) -> dict[str, bool]:
    summary = context.capability_summary or {}
    return dict(summary.get("validator_applicability") or {})


def _validator_reasons(context: ValidationContext) -> dict[str, str]:
    summary = context.capability_summary or {}
    return dict(summary.get("validator_reasons") or {})


def _workspace_readiness(context: ValidationContext) -> dict[str, Any]:
    summary = context.capability_summary or {}
    return dict(summary.get("workspace_readiness") or {})


def _capabilities(context: ValidationContext) -> dict[str, Any]:
    summary = context.capability_summary or {}
    return dict(summary.get("capabilities") or {})


def _is_progression_enabled(context: ValidationContext) -> tuple[bool, str]:
    capabilities = _capabilities(context)
    if capabilities.get("uses_progression") is False:
        return False, "Campaign explicitly does not use progression."
    if capabilities.get("uses_progression") is True:
        return True, "Campaign explicitly uses progression."
    return True, "Progression relevance is not fully confirmed, so configuration-gated checks stay available."


def _resolve_enabled_configuration_checks(context: ValidationContext) -> tuple[list[str], list[str]]:
    selected = _selected_subset(context.selected_checks, CONFIGURATION_GATED_STRUCTURAL_CHECKS)
    if not selected:
        return [], []

    applicability = _validator_applicability(context)
    reasons = _validator_reasons(context)
    progression_enabled, progression_reason = _is_progression_enabled(context)

    enabled: list[str] = []
    disabled_reasons: list[str] = []

    for check_name in selected:
        if check_name in applicability:
            if bool(applicability[check_name]):
                enabled.append(check_name)
            else:
                disabled_reasons.append(
                    reasons.get(check_name) or f"{check_name} is disabled by validator_applicability."
                )
            continue

        if progression_enabled:
            enabled.append(check_name)
        else:
            disabled_reasons.append(progression_reason)

    return enabled, disabled_reasons


class UniversalStructuralValidator(BaseValidator):
    name = "universal_structural"

    def is_applicable(self, context: ValidationContext) -> tuple[bool, str]:
        checks = _selected_subset(context.selected_checks, UNIVERSAL_STRUCTURAL_CHECKS)
        if not checks:
            return False, "No universal checks were selected."
        return True, "Universal validation is always applicable."

    def run(self, context: ValidationContext) -> ValidationResult:
        checks = _selected_subset(context.selected_checks, UNIVERSAL_STRUCTURAL_CHECKS)
        payload = run_campaign_checks(
            file_path=context.file_path,
            checks=checks,
            export_excel=context.export_excel,
        )
        return ValidationResult(validator_name=self.name, success=True, payload=payload)


class ConfigurationGatedStructuralValidator(BaseValidator):
    name = "configuration_gated_structural"

    def is_applicable(self, context: ValidationContext) -> tuple[bool, str]:
        checks, disabled_reasons = _resolve_enabled_configuration_checks(context)
        if checks:
            return True, "Configuration-gated structural validation is applicable."

        if disabled_reasons:
            return False, disabled_reasons[0]

        return False, "No configuration-gated structural checks were selected."

    def run(self, context: ValidationContext) -> ValidationResult:
        checks, disabled_reasons = _resolve_enabled_configuration_checks(context)
        payload = run_campaign_checks(
            file_path=context.file_path,
            checks=checks,
            export_excel=context.export_excel,
        )
        return ValidationResult(
            validator_name=self.name,
            success=True,
            payload=payload,
            notes=disabled_reasons,
        )


class TargetPointsReachableValidator(BaseValidator):
    name = TARGETPOINTSREACHABLE

    def is_applicable(self, context: ValidationContext) -> tuple[bool, str]:
        if TARGETPOINTSREACHABLE not in context.selected_checks:
            return False, "Target-points reachability was not selected."

        applicability = _validator_applicability(context)
        reasons = _validator_reasons(context)
        if TARGETPOINTSREACHABLE in applicability:
            enabled = bool(applicability[TARGETPOINTSREACHABLE])
            return enabled, (
                reasons.get(TARGETPOINTSREACHABLE)
                or (
                    "Applicability comes from validator_applicability."
                    if enabled
                    else "validator_applicability disabled target-points reachability."
                )
            )

        progression_enabled, progression_reason = _is_progression_enabled(context)
        if not progression_enabled:
            return False, progression_reason

        return True, "Target-points reachability is applicable."

    def run(self, context: ValidationContext) -> ValidationResult:
        native_result = run_native_targetpointsreachable_check(context.file_path)
        payload = _checker_payload_from_single_native_result(
            file_path=context.file_path,
            check_name=TARGETPOINTSREACHABLE,
            native_result=native_result,
        )
        return ValidationResult(validator_name=self.name, success=True, payload=payload)


class GatekeepingSemanticsValidator(BaseValidator):
    name = GATEKEEPINGSEMANTICS

    def __init__(self) -> None:
        self.service = PointGatekeepingService()

    def is_applicable(self, context: ValidationContext) -> tuple[bool, str]:
        if GATEKEEPINGSEMANTICS not in context.selected_checks:
            return False, "Gatekeeping semantics was not selected."

        progression_enabled, progression_reason = _is_progression_enabled(context)
        if not progression_enabled:
            return False, progression_reason

        readiness = _workspace_readiness(context)
        if not readiness:
            return False, "Workspace readiness has not been computed yet."

        if not readiness.get("progression_applicable", False):
            return False, "Progression is not applicable."

        if not readiness.get("gatekeeping_semantics_ready", False):
            reasons = list(readiness.get("reasons", []) or [])
            return False, reasons[0] if reasons else "Gatekeeping semantics is disabled until required annotations are present."

        return True, "Workspace is ready for stronger gatekeeping semantics validation."

    def run(self, context: ValidationContext) -> ValidationResult:
        payload = self.service.analyze(
            campaign_file=context.file_path,
            point_rules=context.point_rules,
            task_roles=context.task_roles,
        )
        return ValidationResult(validator_name=self.name, success=True, payload=payload)


# Backward-compatible alias for any old imports/tests that still use the old class name.
PointGatekeepingValidator = GatekeepingSemanticsValidator

# Backward-compatible import alias.
# The legacy validator is no longer part of the default registry,
# but this alias avoids breaking any old imports.
from campaign_assistant.legacy.validators import LegacyTTMValidator as TTMValidator