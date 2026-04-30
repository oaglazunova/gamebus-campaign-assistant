from __future__ import annotations

from pathlib import Path

from campaign_assistant.agents.privacy_guardian import PrivacyGuardianAgent
from campaign_assistant.agents.theory_grounding import TheoryGroundingAgent
from campaign_assistant.orchestration.models import AgentContext



class DummyMetadataBundle:
	def __init__(self):
		self.theory_sources = []


def _make_context(tmp_path: Path) -> AgentContext:
	campaign_file = tmp_path / "campaign.xlsx"
	campaign_file.write_bytes(b"dummy")

	workspace_root = tmp_path / "workspace"
	metadata_dir = workspace_root / "metadata"
	theory_dir = workspace_root / "evidence" / "theory"
	metadata_dir.mkdir(parents=True, exist_ok=True)
	theory_dir.mkdir(parents=True, exist_ok=True)

	(theory_dir / "ttm_structure.pdf").write_bytes(b"%PDF-1.4")

	ctx = AgentContext(
		request_id="req-theory-privacy-001",
		file_path=campaign_file,
		selected_checks=["ttm"],
		export_excel=False,
		workspace_id="ws-theory-privacy",
		workspace_root=workspace_root,
		snapshot_id="snap-theory-privacy-001",
		analysis_profile={},
		point_rules={},
		task_roles=[],
		evidence_index={},
		shared={},
	)

	ctx.shared["capability_summary"] = {
		"capabilities": {"uses_ttm": True},
		"validator_applicability": {"ttm": True},
		"theory_applicability": {"ttm_grounding": True},
	}
	ctx.shared["metadata_bundle"] = DummyMetadataBundle()
	ctx.shared["result"] = {
		"summary": {"failed_checks": ["ttm"], "total_issues": 1},
		"issues_by_check": {"ttm": [{"message": "Wrong TTM successor."}]},
		"assistant_meta": {"raw_debug_blob": "should_not_be_in_view"},
	}
	return ctx


def test_theory_grounding_builds_privacy_scoped_view(tmp_path: Path):
	ctx = _make_context(tmp_path)

	PrivacyGuardianAgent().run(ctx)

	PrivacyGuardianAgent().run(ctx)
	response = TheoryGroundingAgent().run(ctx)

	assert response.success is True
	assert "theory_grounding_agent" in ctx.shared.get("agent_views", {})

	view = ctx.shared["agent_views"]["theory_grounding_agent"]
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