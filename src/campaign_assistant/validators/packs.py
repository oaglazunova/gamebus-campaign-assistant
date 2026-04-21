from __future__ import annotations

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


class HealthyW8LongTermTrialValidator(BaseValidator):
    name = "healthyw8_long_term_trial"

    def is_applicable(self, context: ValidationContext) -> tuple[bool, str]:
        capabilities = (context.capability_summary or {}).get("capabilities", {}) or {}
        metadata_bundle = context.metadata_bundle
        family = getattr(getattr(metadata_bundle, "campaign_family", None), "slug", None)
        selected = _selected_subset(context.selected_checks, [TTMSTRUCTURE])

        if not selected:
            return False, "No HealthyW8-specific checks were selected."

        if family == "healthyw8_long_term_trial":
            return True, "Campaign family explicitly matches HealthyW8 long-term trial."

        if capabilities.get("uses_ttm") is True:
            return True, "TTM capability is enabled, so the HealthyW8 TTM validator is applicable."

        return False, "HealthyW8-specific validator is not applicable."

    def run(self, context: ValidationContext) -> ValidationResult:
        payload = run_campaign_checks(
            file_path=context.file_path,
            checks=[TTMSTRUCTURE],
            export_excel=False,
        )
        return ValidationResult(validator_name=self.name, success=True, payload=payload)