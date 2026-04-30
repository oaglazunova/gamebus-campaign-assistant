from __future__ import annotations

from campaign_assistant.privacy.presentation import build_privacy_diagnostics_model


def test_privacy_setup_panel_inputs_have_expected_shape():
    report = {
        "policy_mode": "coarse_grained_phase_2_step_11",
        "has_workspace_overrides": True,
        "overridden_agents": ["content_fixer_agent"],
        "override_warning_count": 1,
        "override_warnings": [
            {"code": "semantic_raw_workbook_escalation_blocked", "message": "Blocked escalation."}
        ],
        "raw_workbook_allowed_agents": ["structural_change_agent"],
        "sanitized_only_agents": ["content_fixer_agent", "theory_grounding_agent"],
        "semantic_agents_requiring_views": ["content_fixer_agent", "theory_grounding_agent"],
        "policy_sources_by_agent": {
            "content_fixer_agent": "workspace_override",
            "structural_change_agent": "baseline",
        },
    }

    model = build_privacy_diagnostics_model(report)

    assert model["has_any_diagnostics"] is True
    assert model["status"] == "warning"
    assert "content_fixer_agent" in model["overridden_agents"]
    assert "structural_change_agent" in model["raw_workbook_allowed_agents"]