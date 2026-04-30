from __future__ import annotations

import json
from pathlib import Path

from campaign_assistant.agents.privacy_guardian import PrivacyGuardianAgent
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
		request_id="req-override-001",
		file_path=campaign_file,
		selected_checks=["ttm"],
		export_excel=False,
		workspace_id="ws-override",
		workspace_root=workspace_root,
		snapshot_id="snap-override-001",
		analysis_profile={},
		point_rules={},
		task_roles=[],
		evidence_index={},
		shared={},
	)


def test_workspace_override_changes_agent_policy(tmp_path: Path):
	ctx = _make_context(tmp_path)

	policy_path = ctx.workspace_root / "metadata" / "privacy_policy.json"
	policy_path.write_text(
		json.dumps(
			{
				"agent_policies": {
					"content_fixer_agent": {
						"allowed_asset_ids": ["task_roles_csv"],
						"redactions": ["custom_workspace_rule"],
						"allow_raw_workbook": False,
					}
				}
			},
			indent=2,
		),
		encoding="utf-8",
	)

	state = PrivacyService().build_privacy_state(ctx)
	policy = state.agent_policies["content_fixer_agent"]

	assert policy.allowed_asset_ids == ["task_roles_csv"]
	assert "custom_workspace_rule" in policy.redactions
	assert "no_raw_campaign_workbook" in policy.redactions
	assert "metadata_summary_only" in policy.redactions
	assert policy.allow_raw_workbook is False
	assert policy.policy_source == "workspace_override"


def test_workspace_override_ignores_unknown_asset_ids(tmp_path: Path):
	ctx = _make_context(tmp_path)

	policy_path = ctx.workspace_root / "metadata" / "privacy_policy.json"
	policy_path.write_text(
		json.dumps(
			{
				"agent_policies": {
					"theory_grounding_agent": {
						"allowed_asset_ids": ["does_not_exist", "task_roles_csv"],
					}
				}
			},
			indent=2,
		),
		encoding="utf-8",
	)

	state = PrivacyService().build_privacy_state(ctx)
	policy = state.agent_policies["theory_grounding_agent"]

	assert policy.allowed_asset_ids == ["task_roles_csv"]
	assert policy.policy_source == "workspace_override"


def test_privacy_guardian_summary_reports_override_usage(tmp_path: Path):
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

	response = PrivacyGuardianAgent().run(ctx)

	assert response.success is True
	summary = ctx.shared["privacy_state"]["summary"]
	assert summary["has_workspace_overrides"] is True
	assert "content_fixer_agent" in summary["overridden_agents"]
	assert summary["policy_mode"] == "coarse_grained_phase_2_step_11"
	assert ctx.shared["privacy_report"]["policy_sources_by_agent"]["content_fixer_agent"] == "workspace_override"


def test_semantic_override_cannot_grant_raw_workbook_access(tmp_path: Path):
	ctx = _make_context(tmp_path)

	policy_path = ctx.workspace_root / "metadata" / "privacy_policy.json"
	policy_path.write_text(
		json.dumps(
			{
				"agent_policies": {
					"content_fixer_agent": {
						"allowed_asset_ids": ["campaign_workbook", "task_roles_csv"],
						"allow_raw_workbook": True,
					}
				}
			},
			indent=2,
		),
		encoding="utf-8",
	)

	state = PrivacyService().build_privacy_state(ctx)
	policy = state.agent_policies["content_fixer_agent"]

	assert policy.allow_raw_workbook is False
	assert "campaign_workbook" not in policy.allowed_asset_ids
	assert "task_roles_csv" in policy.allowed_asset_ids
	assert policy.policy_source == "workspace_override"


def test_override_allowed_paths_are_derived_from_valid_asset_ids(tmp_path: Path):
	ctx = _make_context(tmp_path)

	policy_path = ctx.workspace_root / "metadata" / "privacy_policy.json"
	policy_path.write_text(
		json.dumps(
			{
				"agent_policies": {
					"theory_grounding_agent": {
						"allowed_asset_ids": ["task_roles_csv"],
						"allowed_paths": ["C:/totally/not/allowed.txt"],
					}
				}
			},
			indent=2,
		),
		encoding="utf-8",
	)

	state = PrivacyService().build_privacy_state(ctx)
	policy = state.agent_policies["theory_grounding_agent"]

	assert policy.allowed_asset_ids == ["task_roles_csv"]
	assert len(policy.allowed_paths) == 1
	assert policy.allowed_paths[0].endswith("task_roles.csv")
	assert "not/allowed.txt" not in policy.allowed_paths[0].replace("\\", "/")



def test_workspace_override_reports_unknown_agent_warning(tmp_path: Path):
    ctx = _make_context(tmp_path)

    policy_path = ctx.workspace_root / "metadata" / "privacy_policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "agent_policies": {
                    "imaginary_agent": {
                        "allowed_asset_ids": ["task_roles_csv"],
                    }
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    response = PrivacyGuardianAgent().run(ctx)

    assert response.success is True
    report = ctx.shared["privacy_report"]
    assert report["override_warning_count"] >= 1
    assert any(
        warning["code"] == "unknown_agent_override"
        for warning in report["override_warnings"]
    )


def test_workspace_override_reports_semantic_escalation_warning(tmp_path: Path):
    ctx = _make_context(tmp_path)

    policy_path = ctx.workspace_root / "metadata" / "privacy_policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "agent_policies": {
                    "content_fixer_agent": {
                        "allowed_asset_ids": ["campaign_workbook", "task_roles_csv"],
                        "allow_raw_workbook": True,
                    }
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    response = PrivacyGuardianAgent().run(ctx)

    assert response.success is True
    report = ctx.shared["privacy_report"]

    codes = {warning["code"] for warning in report["override_warnings"]}
    assert "semantic_raw_workbook_escalation_blocked" in codes
    assert "semantic_workbook_asset_removed" in codes