from campaign_assistant.ui.overview import build_analysis_overview_model


def test_overview_model_handles_empty_result():
    model = build_analysis_overview_model(None)

    assert model["has_result"] is False
    assert model["status"] == "empty"


def test_overview_model_marks_readiness_gap():
    model = build_analysis_overview_model(
        {
            "summary": {
                "total_issues": 4,
                "failed_checks": ["targetpointsreachable"],
                "errored_checks": [],
            },
            "fix_proposals": {
                "proposal_count": 2,
            },
            "assistant_meta": {
                "workspace_id": "ws-1",
                "snapshot_id": "snap-1",
                "workspace_readiness": {
                    "progression_applicable": True,
                    "gatekeeping_semantics_ready": False,
                },
            },
        }
    )

    assert model["has_result"] is True
    assert model["status"] == "issues_found"
    assert model["readiness_status"] == "needs_annotations"
    assert any(action["focus"] == "task_roles" for action in model["top_actions"])


def test_overview_model_marks_clean():
    model = build_analysis_overview_model(
        {
            "summary": {
                "total_issues": 0,
                "failed_checks": [],
                "errored_checks": [],
            },
            "fix_proposals": {
                "proposal_count": 0,
            },
            "assistant_meta": {
                "workspace_id": "ws-1",
                "snapshot_id": "snap-1",
                "workspace_readiness": {
                    "progression_applicable": False,
                    "gatekeeping_semantics_ready": False,
                },
            },
        }
    )

    assert model["has_result"] is True
    assert model["status"] == "clean"
    assert model["readiness_status"] == "not_applicable"