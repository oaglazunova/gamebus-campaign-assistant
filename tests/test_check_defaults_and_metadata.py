from __future__ import annotations

from campaign_assistant.checker.check_metadata import (
    CHECK_EXPLANATIONS,
    CHECK_HINTS,
    PRIORITY_HINT,
    check_explanation,
    check_hint,
)
from campaign_assistant.checker.schema import (
    CHECK_PICKER_CHECKS,
    CONSISTENCY,
    DEFAULT_CHECKS,
    REACHABILITY,
    SECRETS,
    SPELLCHECKER,
    TARGETPOINTSREACHABLE,
    TTMSTRUCTURE,
    VISUALIZATIONINTERN,
    PROGRESSIONBRANCHCONSISTENCY,
    DUPLICATETASKNAMES,
    TEXTPOINTSCONSISTENCY,
)


def test_default_checks_include_actionable_checks_but_exclude_optional_checks() -> None:
    assert SPELLCHECKER in CHECK_PICKER_CHECKS
    assert TTMSTRUCTURE in CHECK_PICKER_CHECKS

    assert SPELLCHECKER not in DEFAULT_CHECKS
    assert TTMSTRUCTURE not in DEFAULT_CHECKS

    assert DEFAULT_CHECKS == [
        SECRETS,
        REACHABILITY,
        CONSISTENCY,
        VISUALIZATIONINTERN,
        PROGRESSIONBRANCHCONSISTENCY,
        TARGETPOINTSREACHABLE,
        TEXTPOINTSCONSISTENCY,
        DUPLICATETASKNAMES,
    ]


def test_short_hints_and_detailed_explanations_exist_for_picker_checks() -> None:
    for check_id in CHECK_PICKER_CHECKS:
        assert check_hint(check_id) == CHECK_HINTS[check_id]
        assert check_explanation(check_id) == CHECK_EXPLANATIONS[check_id]
        assert len(check_hint(check_id)) < len(check_explanation(check_id))


def test_spellchecker_hint_mentions_german_and_ttm_hint_mentions_hw8_specificity() -> None:
    assert "German" in check_hint(SPELLCHECKER)
    assert "HW8" in check_hint(TTMSTRUCTURE)


def test_priority_hint_matches_current_check_severities() -> None:
    assert "reachability = high" in PRIORITY_HINT
    assert "consistency = high" in PRIORITY_HINT
    assert "visualization internals = medium" in PRIORITY_HINT
    assert "success/fallback path consistency = medium" in PRIORITY_HINT
    assert "target points reachable = high" in PRIORITY_HINT
    assert "secrets = medium" in PRIORITY_HINT
    assert "spellchecker = low" in PRIORITY_HINT
    assert "TTM structure = medium" in PRIORITY_HINT
    assert "active_wave_boost = +50" in PRIORITY_HINT
