from campaign_assistant.checker.schema import (
    CAPABILITY_GATED_CHECKS,
    CONSISTENCY,
    REACHABILITY,
    SECRETS,
    SPELLCHECKER,
    UNIVERSAL_CHECKS,
    VISUALIZATIONINTERN,
)
from campaign_assistant.validators import build_default_validator_registry


def test_release2_taxonomy_moves_only_secrets_and_spellchecker_to_universal():
    assert UNIVERSAL_CHECKS == [SECRETS, SPELLCHECKER]
    assert REACHABILITY not in UNIVERSAL_CHECKS
    assert CONSISTENCY not in UNIVERSAL_CHECKS
    assert VISUALIZATIONINTERN not in UNIVERSAL_CHECKS


def test_release2_taxonomy_marks_progression_checks_as_configuration_gated():
    assert REACHABILITY in CAPABILITY_GATED_CHECKS
    assert CONSISTENCY in CAPABILITY_GATED_CHECKS
    assert VISUALIZATIONINTERN in CAPABILITY_GATED_CHECKS


def test_default_registry_contains_configuration_gated_structural_validator():
    names = [validator.name for validator in build_default_validator_registry()._validators]
    assert "configuration_gated_structural" in names