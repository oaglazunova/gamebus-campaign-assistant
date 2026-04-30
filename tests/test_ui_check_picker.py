from campaign_assistant.checker.catalog import resolve_check_availability
from campaign_assistant.checker.schema import GATEKEEPINGSEMANTICS


def test_grouped_picker_source_marks_gatekeeping_semantics_disabled_with_action():
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
        }
    )

    gatekeeping = next(item for item in items if item.check_id == GATEKEEPINGSEMANTICS)
    assert gatekeeping.visible is True
    assert gatekeeping.enabled is False
    assert gatekeeping.action is not None
    assert gatekeeping.action["label"] == "Annotate task roles"