from campaign_assistant.checker.schema import (
    ALL_CHECKS,
    CAPABILITY_GATED_CHECKS,
    DEFAULT_CHECKS,
    GATEKEEPINGSEMANTICS,
    TARGETPOINTSREACHABLE,
)


def test_gatekeeping_semantics_exists_but_is_not_in_flat_default_checks_yet():
    assert GATEKEEPINGSEMANTICS in ALL_CHECKS
    assert GATEKEEPINGSEMANTICS in CAPABILITY_GATED_CHECKS
    assert GATEKEEPINGSEMANTICS not in DEFAULT_CHECKS
    assert TARGETPOINTSREACHABLE in DEFAULT_CHECKS