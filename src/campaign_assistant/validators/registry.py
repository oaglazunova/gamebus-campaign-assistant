from __future__ import annotations

from campaign_assistant.validators.base import BaseValidator, ValidationContext
from campaign_assistant.validators.packs import (
    ExportStructuralValidator,
    TargetPointsReachableValidator,
)


class ValidatorRegistry:
    def __init__(self) -> None:
        self._validators: list[BaseValidator] = []

    def register(self, validator: BaseValidator) -> None:
        self._validators.append(validator)

    def resolve(self, context: ValidationContext) -> list[BaseValidator]:
        resolved: list[BaseValidator] = []
        for validator in self._validators:
            applicable, _reason = validator.is_applicable(context)
            if applicable:
                resolved.append(validator)
        return resolved


def build_default_validator_registry(*, include_legacy: bool = False) -> ValidatorRegistry:
    """
    Build the paper-release validator registry.

    The include_legacy argument is kept only for backward-compatible call sites.
    Legacy TTM validation is no longer registered.
    """
    registry = ValidatorRegistry()
    registry.register(ExportStructuralValidator())
    registry.register(TargetPointsReachableValidator())
    return registry


def build_legacy_validator_registry() -> ValidatorRegistry:
    """
    Legacy TTM validation has been removed from the paper-release scope.
    Return an empty registry for backward-compatible imports.
    """
    return ValidatorRegistry()