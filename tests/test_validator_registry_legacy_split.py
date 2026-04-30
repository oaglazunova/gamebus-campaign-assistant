from campaign_assistant.checker.schema import ALL_CHECKS, DEFAULT_CHECKS, TTMSTRUCTURE
from campaign_assistant.validators import (
    build_default_validator_registry,
    build_legacy_validator_registry,
)


def _validator_names(registry) -> list[str]:
    return [validator.name for validator in registry._validators]


def test_default_checks_hide_legacy_ttm():
    assert TTMSTRUCTURE not in DEFAULT_CHECKS
    assert TTMSTRUCTURE in ALL_CHECKS


def test_default_registry_excludes_legacy_ttm():
    names = _validator_names(build_default_validator_registry())
    assert TTMSTRUCTURE not in names


def test_default_registry_can_include_legacy_when_explicitly_requested():
    names = _validator_names(build_default_validator_registry(include_legacy=True))
    assert TTMSTRUCTURE in names


def test_legacy_registry_contains_only_legacy_ttm():
    names = _validator_names(build_legacy_validator_registry())
    assert names == [TTMSTRUCTURE]