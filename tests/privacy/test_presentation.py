from __future__ import annotations

from campaign_assistant.privacy.presentation import build_privacy_diagnostics_model


def test_build_privacy_diagnostics_model_baseline():
    model = build_privacy_diagnostics_model(
        {
            "policy_mode": "coarse_grained_phase_2_step_11",
            "has_workspace_overrides": False,
            "overridden_agents": [],
            "override_warning_count": 0,
            "override_warnings": [],
            "raw_workbook_allowed_agents": ["structural_change_agent"],
            "sanitized_only_agents": ["theory_grounding_agent", "content_fixer_agent"],
            "semantic_agents_requiring_views": ["theory_grounding_agent", "content_fixer_agent"],
            "policy_sources_by_agent": {
                "structural_change_agent": "baseline",
                "theory_grounding_agent": "baseline",
            },
        }
    )

    assert model["status"] == "baseline"
    assert model["has_any_diagnostics"] is True
    assert model["override_warning_count"] == 0


def test_build_privacy_diagnostics_model_warning_status():
    model = build_privacy_diagnostics_model(
        {
            "policy_mode": "coarse_grained_phase_2_step_11",
            "has_workspace_overrides": True,
            "overridden_agents": ["content_fixer_agent"],
            "override_warning_count": 2,
            "override_warnings": [
                {"code": "semantic_raw_workbook_escalation_blocked", "message": "Blocked."},
                {"code": "semantic_workbook_asset_removed", "message": "Removed."},
            ],
            "raw_workbook_allowed_agents": ["structural_change_agent"],
            "sanitized_only_agents": ["content_fixer_agent"],
            "semantic_agents_requiring_views": ["content_fixer_agent"],
            "policy_sources_by_agent": {"content_fixer_agent": "workspace_override"},
        }
    )

    assert model["status"] == "warning"
    assert model["override_warning_count"] == 2
    assert model["overridden_agents"] == ["content_fixer_agent"]


def test_build_privacy_diagnostics_model_customized_status():
    model = build_privacy_diagnostics_model(
        {
            "policy_mode": "coarse_grained_phase_2_step_11",
            "has_workspace_overrides": True,
            "overridden_agents": ["content_fixer_agent"],
            "override_warning_count": 0,
            "override_warnings": [],
            "raw_workbook_allowed_agents": ["structural_change_agent"],
            "sanitized_only_agents": ["content_fixer_agent", "theory_grounding_agent"],
            "semantic_agents_requiring_views": ["content_fixer_agent", "theory_grounding_agent"],
            "policy_sources_by_agent": {
                "content_fixer_agent": "workspace_override",
                "structural_change_agent": "baseline",
            },
        }
    )

    assert model["status"] == "customized"
    assert model["has_workspace_overrides"] is True
    assert model["override_warning_count"] == 0