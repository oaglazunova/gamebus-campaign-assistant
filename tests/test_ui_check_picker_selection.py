from campaign_assistant.checker.catalog import resolve_check_availability
from campaign_assistant.checker.schema import (
    GATEKEEPINGSEMANTICS,
    TARGETPOINTSREACHABLE,
)


def test_gatekeeping_semantics_is_visible_but_not_default_selected():
    items = resolve_check_availability(
        {
            "capabilities": {"uses_progression": True},
            "workspace_readiness": {
                "progression_applicable": True,
                "gatekeeping_semantics_ready": True,
            },
        }
    )

    by_id = {item.check_id: item for item in items}

    assert by_id[TARGETPOINTSREACHABLE].enabled is True
    assert by_id[TARGETPOINTSREACHABLE].selected_by_default is True

    assert by_id[GATEKEEPINGSEMANTICS].visible is True
    assert by_id[GATEKEEPINGSEMANTICS].enabled is True
    assert by_id[GATEKEEPINGSEMANTICS].selected_by_default is False