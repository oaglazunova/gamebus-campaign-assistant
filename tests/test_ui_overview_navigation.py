from campaign_assistant.ui.overview import build_analysis_overview_model


def test_overview_model_exposes_core_overview_fields():
    model = build_analysis_overview_model(
        {
            "summary": {
                "total_issues": 3,
                "failed_checks": ["reachability"],
                "errored_checks": [],
            },
            "fix_proposals": {
                "proposal_count": 2,
            },
            "assistant_meta": {
                "workspace_id": "ws-1",
                "snapshot_id": "snap-1",
                "selected_checks": ["reachability", "secrets"],
                "workspace_readiness": {
                    "progression_applicable": True,
                    "gatekeeping_semantics_ready": False,
                },
            },
        }
    )

    assert model["has_result"] is True
    assert model["status"] == "issues_found"
    assert model["workspace_id"] == "ws-1"
    assert model["snapshot_id"] == "snap-1"
    assert model["selected_checks"] == ["reachability", "secrets"]
    assert model["proposal_count"] == 2
    assert model["readiness_status"] == "needs_annotations"
    assert "top_actions" not in model