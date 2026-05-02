from campaign_assistant.ui.overview import build_analysis_overview_model


def test_overview_model_exposes_workflow_actions():
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

    labels = [x["label"] for x in model["top_actions"]]

    assert "Open Setup" in labels
    assert "Review Findings" in labels
    assert "Review Fixes" in labels
    assert "Ask Assistant" in labels