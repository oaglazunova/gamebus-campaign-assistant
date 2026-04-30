from __future__ import annotations

from campaign_assistant.checker.catalog import (
    CHECK_GROUP_CONFIG,
    CHECK_GROUP_LEGACY,
    CHECK_GROUP_UNIVERSAL,
    default_selected_check_ids,
    resolve_check_availability,
)
from campaign_assistant.checker.schema import (
    CONSISTENCY,
    GATEKEEPINGSEMANTICS,
    REACHABILITY,
    SECRETS,
    SPELLCHECKER,
    TARGETPOINTSREACHABLE,
    TTMSTRUCTURE,
    VISUALIZATIONINTERN,
)


def test_catalog_groups_universal_checks_as_expected():
    items = resolve_check_availability({"capabilities": {}})
    by_id = {item.check_id: item for item in items}

    assert by_id[SECRETS].group == CHECK_GROUP_UNIVERSAL
    assert by_id[SPELLCHECKER].group == CHECK_GROUP_UNIVERSAL


def test_catalog_groups_configuration_checks_as_expected():
    items = resolve_check_availability({"capabilities": {}})
    by_id = {item.check_id: item for item in items}

    assert by_id[REACHABILITY].group == CHECK_GROUP_CONFIG
    assert by_id[CONSISTENCY].group == CHECK_GROUP_CONFIG
    assert by_id[VISUALIZATIONINTERN].group == CHECK_GROUP_CONFIG
    assert by_id[TARGETPOINTSREACHABLE].group == CHECK_GROUP_CONFIG
    assert by_id[GATEKEEPINGSEMANTICS].group == CHECK_GROUP_CONFIG


def test_catalog_hides_legacy_checks_by_default():
    items = resolve_check_availability(
        {"capabilities": {"uses_ttm": True}},
        enable_legacy=False,
    )
    by_id = {item.check_id: item for item in items}

    assert by_id[TTMSTRUCTURE].group == CHECK_GROUP_LEGACY
    assert by_id[TTMSTRUCTURE].visible is False
    assert by_id[TTMSTRUCTURE].enabled is False


def test_catalog_can_show_legacy_check_when_explicitly_enabled():
    items = resolve_check_availability(
        {"capabilities": {"uses_ttm": True}},
        enable_legacy=True,
    )
    by_id = {item.check_id: item for item in items}

    assert by_id[TTMSTRUCTURE].visible is True
    assert by_id[TTMSTRUCTURE].enabled is True


def test_configuration_checks_disable_when_progression_is_explicitly_false():
    items = resolve_check_availability(
        {"capabilities": {"uses_progression": False}},
        enable_legacy=False,
    )
    by_id = {item.check_id: item for item in items}

    assert by_id[REACHABILITY].enabled is False
    assert by_id[CONSISTENCY].enabled is False
    assert by_id[VISUALIZATIONINTERN].enabled is False
    assert by_id[TARGETPOINTSREACHABLE].enabled is False
    assert by_id[GATEKEEPINGSEMANTICS].enabled is False


def test_gatekeeping_semantics_is_visible_but_disabled_when_readiness_missing():
    items = resolve_check_availability(
        {"capabilities": {"uses_progression": True}},
        enable_legacy=False,
    )
    by_id = {item.check_id: item for item in items}

    assert by_id[GATEKEEPINGSEMANTICS].visible is True
    assert by_id[GATEKEEPINGSEMANTICS].enabled is False
    assert "workspace readiness" in by_id[GATEKEEPINGSEMANTICS].reason.lower()


def test_gatekeeping_semantics_exposes_task_role_action_when_not_ready():
    items = resolve_check_availability(
        {
            "capabilities": {"uses_progression": True},
            "workspace_readiness": {
                "gatekeeping_semantics_ready": False,
                "disabled_checks": {
                    GATEKEEPINGSEMANTICS: {
                        "reason": "Disabled until required task-role annotations are added in the workspace.",
                        "action": {
                            "action_id": "open_task_role_annotations",
                            "label": "Annotate task roles",
                            "focus": "task_roles",
                        },
                    }
                },
            },
        },
        enable_legacy=False,
    )
    by_id = {item.check_id: item for item in items}

    assert by_id[GATEKEEPINGSEMANTICS].visible is True
    assert by_id[GATEKEEPINGSEMANTICS].enabled is False
    assert by_id[GATEKEEPINGSEMANTICS].action is not None
    assert by_id[GATEKEEPINGSEMANTICS].action["focus"] == "task_roles"


def test_gatekeeping_semantics_enables_when_workspace_is_ready():
    items = resolve_check_availability(
        {
            "capabilities": {"uses_progression": True},
            "workspace_readiness": {
                "progression_applicable": True,
                "gatekeeping_semantics_ready": True,
            },
        },
        enable_legacy=False,
    )
    by_id = {item.check_id: item for item in items}

    assert by_id[GATEKEEPINGSEMANTICS].visible is True
    assert by_id[GATEKEEPINGSEMANTICS].enabled is True


def test_default_selected_checks_exclude_hidden_legacy_and_nondefault_semantics():
    selected = default_selected_check_ids(
        {
            "capabilities": {"uses_progression": True},
            "workspace_readiness": {"gatekeeping_semantics_ready": True},
        },
        enable_legacy=False,
    )

    assert SECRETS in selected
    assert SPELLCHECKER in selected
    assert REACHABILITY in selected
    assert CONSISTENCY in selected
    assert VISUALIZATIONINTERN in selected
    assert TARGETPOINTSREACHABLE in selected
    assert GATEKEEPINGSEMANTICS not in selected
    assert TTMSTRUCTURE not in selected