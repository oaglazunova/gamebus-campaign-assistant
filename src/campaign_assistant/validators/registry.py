from __future__ import annotations

from campaign_assistant.validators.base import BaseValidator, ValidationContext
from campaign_assistant.validators.packs import (
    HealthyW8LongTermTrialValidator,
    PointGatekeepingValidator,
    UniversalStructuralValidator,
)


class ValidatorRegistry:
    def __init__(self) -> None:
        self._validators: list[BaseValidator] = []

    def register(self, validator: BaseValidator) -> None:
        self._validators.append(validator)

    def resolve(self, context: ValidationContext) -> list[BaseValidator]:
        result: list[BaseValidator] = []
        for validator in self._validators:
            applicable, _reason = validator.is_applicable(context)
            if applicable:
                result.append(validator)
        return result


def build_default_validator_registry() -> ValidatorRegistry:
    registry = ValidatorRegistry()
    registry.register(UniversalStructuralValidator())
    registry.register(PointGatekeepingValidator())
    registry.register(HealthyW8LongTermTrialValidator())
    return registry