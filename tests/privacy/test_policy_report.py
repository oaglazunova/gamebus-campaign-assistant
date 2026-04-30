from __future__ import annotations

import json
from pathlib import Path

from campaign_assistant.orchestration.models import AgentContext
from campaign_assistant.privacy.service import PrivacyService


def _make_context(tmp_path: Path) -> AgentContext:
    campaign_file = tmp_path / "campaign.xlsx"
    campaign_file.write_bytes(b"dummy")

    workspace_root = tmp_path / "workspace"
    metadata_dir = workspace_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    (metadata_dir / "campaign_profile.json").write_text("{}", encoding="utf-8")
    (metadata_dir / "task_roles.csv").write_text("task_id,task_name,role,notes\n", encoding="utf-8")
    (metadata_dir / "theory_registry.json").write_text("{}", encoding="utf-8")

    return AgentContext(
        request_id="req-policy-report-001",
        file_path=campaign_file,
        selected_checks=["ttm"],
        export_excel=False,
        workspace_id="ws-policy-report",
        workspace_root=workspace_root,
        snapshot_id="snap-policy-report-001",
        analysis_profile={},
        point_rules={},
        task_roles=[],
        evidence_index={},
        shared={},
    )


def test_build_privacy_report_from_baseline_state(tmp_path: Path):
    ctx = _make_context(tmp_path)

    service = PrivacyService()
    state = service.build_privacy_state(ctx).to_dict()
    report = service.build_privacy_report(state)

    assert report["policy_mode"] == "coarse_grained_phase_2_step_11"
    assert report["has_workspace_overrides"] is False
    assert "theory_grounding_agent" in report["policy_sources_by_agent"]
    assert report["policy_sources_by_agent"]["theory_grounding_agent"] == "baseline"
    assert "theory_grounding_agent" in report["semantic_agents_requiring_views"]
    assert "content_fixer_agent" in report["semantic_agents_requiring_views"]
    assert report["override_warning_count"] == 0
    assert report["override_warnings"] == []


def test_build_privacy_report_reflects_workspace_override(tmp_path: Path):
    ctx = _make_context(tmp_path)

    policy_path = ctx.workspace_root / "metadata" / "privacy_policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "agent_policies": {
                    "content_fixer_agent": {
                        "allowed_asset_ids": ["task_roles_csv"],
                    }
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    service = PrivacyService()
    state = service.build_privacy_state(ctx).to_dict()
    report = service.build_privacy_report(state)

    assert report["has_workspace_overrides"] is True
    assert "content_fixer_agent" in report["overridden_agents"]
    assert report["policy_sources_by_agent"]["content_fixer_agent"] == "workspace_override"
    assert report["policy_mode"] == "coarse_grained_phase_2_step_11"