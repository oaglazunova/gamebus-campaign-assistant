from __future__ import annotations

from campaign_assistant.legacy import LegacyTTMValidator
from campaign_assistant.validators.base import BaseValidator, ValidationContext
from campaign_assistant.validators.packs import (
    PointGatekeepingValidator,
    TargetPointsReachableValidator,
    UniversalStructuralValidator,
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
    registry = ValidatorRegistry()
    registry.register(UniversalStructuralValidator())
    registry.register(TargetPointsReachableValidator())
    registry.register(PointGatekeepingValidator())

    if include_legacy:
        registry.register(LegacyTTMValidator())

    return registry


def build_legacy_validator_registry() -> ValidatorRegistry:
    registry = ValidatorRegistry()
    registry.register(LegacyTTMValidator())
    return registry