from __future__ import annotations

from pathlib import Path

from campaign_assistant.agents.content_fixer import ContentFixerAgent
from campaign_assistant.agents.privacy_guardian import PrivacyGuardianAgent
from campaign_assistant.orchestration.models import AgentContext


class DummyMetadataBundle:
	def __init__(self):
		self.task_roles = []


def _make_context(tmp_path: Path) -> AgentContext:
	campaign_file = tmp_path / "campaign.xlsx"
	campaign_file.write_bytes(b"dummy")

	workspace_root = tmp_path / "workspace"
	metadata_dir = workspace_root / "metadata"
	metadata_dir.mkdir(parents=True, exist_ok=True)
	(metadata_dir / "campaign_profile.json").write_text("{}", encoding="utf-8")

	ctx = AgentContext(
		request_id="req-fixer-privacy-001",
		file_path=campaign_file,
		selected_checks=["ttm"],
		export_excel=False,
		workspace_id="ws-fixer-privacy",
		workspace_root=workspace_root,
		snapshot_id="snap-fixer-privacy-001",
		analysis_profile={"checking_scope": {"content_fix_suggestions": True}},
		point_rules={},
		task_roles=[],
		evidence_index={},
		shared={},
	)

	ctx.shared["capability_summary"] = {
		"capabilities": {"uses_ttm": True, "uses_progression": True},
		"active_modules": {"point_gatekeeping_checks": True, "ttm_checks": True},
		"validator_applicability": {"ttm": True, "targetpointsreachable": True},
		"theory_applicability": {"ttm_grounding": True},
	}
	ctx.shared["metadata_bundle"] = DummyMetadataBundle()
	ctx.shared["result"] = {
		"point_gatekeeping": {"findings": []},
		"summary": {"failed_checks": ["ttm"]},
		"assistant_meta": {"raw_debug_blob": "should_not_be_in_view"},
	}
	ctx.shared["theory_grounding"] = {
		"uses_ttm": True,
		"failed_checks_seen": ["ttm"],
	}
	return ctx


def test_content_fixer_builds_privacy_scoped_view(tmp_path: Path):
	ctx = _make_context(tmp_path)

	PrivacyGuardianAgent().run(ctx)
	response = ContentFixerAgent().run(ctx)

	assert response.success is True
	assert "content_fixer_agent" in ctx.shared.get("agent_views", {})

	view = ctx.shared["agent_views"]["content_fixer_agent"]
	assert "result" in view
	assert "assistant_meta" not in view["result"]
	assert "metadata_summary" in view
	assert "metadata_bundle" not in view
	assert "used_asset_ids" in view
	assert "asset_access_event_ids" in view

	audit_log = ctx.shared["privacy_state"]["audit_log"]
	assert any(event["event"] == "agent_view_built" for event in audit_log)
	assert any(event["event"] == "asset_access_recorded" for event in audit_log)
	assert any(event["event"] == "agent_completed" for event in audit_log)