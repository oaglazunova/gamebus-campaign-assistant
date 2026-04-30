from __future__ import annotations

from pathlib import Path

from campaign_assistant.orchestration.models import AgentContext
from campaign_assistant.privacy.service import PrivacyService


def _make_context(tmp_path: Path) -> AgentContext:
	campaign_file = tmp_path / "campaign.xlsx"
	campaign_file.write_bytes(b"dummy")

	workspace_root = tmp_path / "workspace"
	metadata_dir = workspace_root / "metadata"
	theory_dir = workspace_root / "evidence" / "theory"
	metadata_dir.mkdir(parents=True, exist_ok=True)
	theory_dir.mkdir(parents=True, exist_ok=True)

	(metadata_dir / "campaign_profile.json").write_text("{}", encoding="utf-8")
	(metadata_dir / "task_roles.csv").write_text("task_id,task_name,role,notes\n", encoding="utf-8")
	(theory_dir / "ttm_structure.pdf").write_bytes(b"%PDF-1.4")

	ctx = AgentContext(
		request_id="req-agent-view-001",
		file_path=campaign_file,
		selected_checks=["ttm"],
		export_excel=False,
		workspace_id="ws-agent-view",
		workspace_root=workspace_root,
		snapshot_id="snap-agent-view-001",
		analysis_profile={"checking_scope": {"content_fix_suggestions": True}},
		point_rules={},
		task_roles=[],
		evidence_index={},
		shared={},
	)

	ctx.shared["capability_summary"] = {
		"capabilities": {"uses_ttm": True, "uses_progression": True},
		"validator_applicability": {"ttm": True, "targetpointsreachable": True},
		"theory_applicability": {"ttm_grounding": True},
	}
	ctx.shared["metadata_bundle"] = None
	ctx.shared["result"] = {
		"summary": {"failed_checks": ["ttm"], "total_issues": 1},
		"issues_by_check": {"ttm": [{"message": "Wrong TTM successor."}]},
		"prioritized_issues": [{"check": "ttm", "severity": "high", "active_wave": True}],
		"point_gatekeeping": {"findings": []},
		"assistant_meta": {"should_not_leak": True},
	}
	ctx.shared["theory_grounding"] = {"uses_ttm": True, "failed_checks_seen": ["ttm"]}
	return ctx


def test_build_agent_view_appends_audit_event(tmp_path: Path):
	ctx = _make_context(tmp_path)
	service = PrivacyService()

	state = service.build_privacy_state(ctx).to_dict()
	ctx.shared["privacy_state"] = state

	before = len(ctx.shared["privacy_state"]["audit_log"])
	view = service.build_agent_view("theory_grounding_agent", ctx)
	after = len(ctx.shared["privacy_state"]["audit_log"])

	assert view["agent_name"] == "theory_grounding_agent"
	assert view["policy"]["policy_source"] in {"baseline", "workspace_override"}
	assert "agent_run_id" in view
	assert "agent_view_id" in view
	assert "used_asset_ids" in view
	assert "asset_access_event_ids" in view
	assert view["used_asset_ids"]
	assert view["asset_access_event_ids"]

	assert "result" in view
	assert "assistant_meta" not in view["result"]
	assert "metadata_summary" in view
	assert "metadata_bundle" not in view

	assert after > before

	audit_log = ctx.shared["privacy_state"]["audit_log"]
	assert any(event["event"] == "agent_view_built" for event in audit_log)
	assert any(event["event"] == "asset_access_recorded" for event in audit_log)

	view_event = next(event for event in reversed(audit_log) if event["event"] == "agent_view_built")
	assert view_event["event_id"]
	assert view_event["parent_event_id"]
	assert view_event["agent_run_id"] == view["agent_run_id"]
	assert view_event["agent_view_id"] == view["agent_view_id"]
	assert view_event["metadata_mode"] == "summary_only"
	assert view_event["policy_source"] in {"baseline", "workspace_override"}


def test_record_agent_outcome_links_to_view_event(tmp_path: Path):
	ctx = _make_context(tmp_path)
	service = PrivacyService()

	state = service.build_privacy_state(ctx).to_dict()
	ctx.shared["privacy_state"] = state

	view = service.build_agent_view("theory_grounding_agent", ctx)
	run_id = view["agent_run_id"]

	before = len(ctx.shared["privacy_state"]["audit_log"])
	service.record_agent_outcome(
		agent_name="theory_grounding_agent",
		context=ctx,
		agent_run_id=run_id,
		success=True,
		payload={"uses_ttm": True},
		warnings=[],
		notes=["ok"],
	)
	after = len(ctx.shared["privacy_state"]["audit_log"])

	assert after == before + 1
	event = ctx.shared["privacy_state"]["audit_log"][-1]
	assert event["event"] == "agent_completed"
	assert event["event_id"]
	assert event["parent_event_id"]
	assert event["agent_run_id"] == run_id
	assert event["payload_keys"] == ["uses_ttm"]
	assert event["note_count"] == 1


def test_record_agent_outcome_links_to_view_event(tmp_path: Path):
	ctx = _make_context(tmp_path)
	service = PrivacyService()

	state = service.build_privacy_state(ctx).to_dict()
	ctx.shared["privacy_state"] = state

	view = service.build_agent_view("theory_grounding_agent", ctx)
	run_id = view["agent_run_id"]

	before = len(ctx.shared["privacy_state"]["audit_log"])
	service.record_agent_outcome(
		agent_name="theory_grounding_agent",
		context=ctx,
		agent_run_id=run_id,
		success=True,
		payload={"uses_ttm": True},
		warnings=[],
		notes=["ok"],
	)
	after = len(ctx.shared["privacy_state"]["audit_log"])

	assert after == before + 1
	event = ctx.shared["privacy_state"]["audit_log"][-1]
	assert event["event"] == "agent_completed"
	assert event["event_id"]
	assert event["parent_event_id"]
	assert event["agent_run_id"] == run_id
	assert event["payload_keys"] == ["uses_ttm"]
	assert event["note_count"] == 1