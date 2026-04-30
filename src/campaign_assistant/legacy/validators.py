from __future__ import annotations

from campaign_assistant.checker import run_campaign_checks
from campaign_assistant.checker.schema import TTMSTRUCTURE
from campaign_assistant.validators.base import BaseValidator, ValidationContext, ValidationResult


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


class LegacyTTMValidator(BaseValidator):
    """
    Legacy HealthyW8-specific TTM structure validator.

    This is intentionally kept outside the default validator registry.
    """
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