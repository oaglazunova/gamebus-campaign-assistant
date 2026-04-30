from campaign_assistant.reasoning.workspace_readiness import WorkspaceReadinessService


class DummyPointGatekeepingService:
    def __init__(self, payload):
        self.payload = payload

    def analyze(self, *, campaign_file, point_rules, task_roles):
        return self.payload


def test_workspace_readiness_marks_progression_not_applicable():
    service = WorkspaceReadinessService()

    result = service.analyze(
        campaign_file="dummy.xlsx",
        capability_summary={"capabilities": {"uses_progression": False}},
        point_rules={},
        task_roles=[],
    )

    assert result["progression_applicable"] is False
    assert result["gatekeeping_semantics_ready"] is False


def test_workspace_readiness_disables_semantics_when_gatekeeping_annotations_missing():
    service = WorkspaceReadinessService()
    service.point_gatekeeping = DummyPointGatekeepingService(
        {
            "findings": [
                {
                    "challenge_name": "Challenge A",
                    "warnings": ["No explicit gatekeeping task is marked for this challenge."],
                }
            ]
        }
    )

    result = service.analyze(
        campaign_file="dummy.xlsx",
        capability_summary={"capabilities": {"uses_progression": True}},
        point_rules={},
        task_roles=[],
    )

    assert result["progression_applicable"] is True
    assert result["gatekeeping_semantics_ready"] is False
    assert result["gatekeeping_annotations_present"] is False
    assert result["disabled_checks"]["gatekeeping_semantics"]["action"]["focus"] == "task_roles"


def test_workspace_readiness_enables_semantics_when_required_annotations_are_present():
    service = WorkspaceReadinessService()
    service.point_gatekeeping = DummyPointGatekeepingService(
        {
            "findings": [
                {
                    "challenge_name": "Challenge A",
                    "warnings": ["Target points exceed the theoretical maximum."],
                }
            ]
        }
    )

    result = service.analyze(
        campaign_file="dummy.xlsx",
        capability_summary={"capabilities": {"uses_progression": True}},
        point_rules={},
        task_roles=[{"task_id": "1", "role": "gatekeeping"}],
    )

    assert result["progression_applicable"] is True
    assert result["gatekeeping_semantics_ready"] is True
    assert result["gatekeeping_annotations_present"] is True