from __future__ import annotations

import json
from pathlib import Path

from campaign_assistant.approval import ApprovalHandler


def test_approval_handler_saves_and_loads_decisions(tmp_path: Path):
	handler = ApprovalHandler(
		workspace_root=tmp_path / "workspace",
		request_id="req-123",
	)

	handler.save_decision(
		proposal_id="fix-1",
		status="accepted",
		reviewer="human",
	)

	decisions = handler.load_decisions()

	assert "fix-1" in decisions
	assert decisions["fix-1"]["status"] == "accepted"
	assert decisions["fix-1"]["reviewer"] == "human"


def test_approval_handler_merge_statuses(tmp_path: Path):
	handler = ApprovalHandler(
		workspace_root=tmp_path / "workspace",
		request_id="req-123",
	)

	handler.save_decision(
		proposal_id="fix-1",
		status="rejected",
		reviewer="human",
	)

	proposals = [
		{
			"proposal_id": "fix-1",
			"category": "points",
			"status": "proposed",
		},
		{
			"proposal_id": "fix-2",
			"category": "gatekeeping",
			"status": "proposed",
		},
	]

	merged = handler.merge_statuses(proposals)

	assert merged[0]["status"] == "rejected"
	assert merged[0]["approval_meta"]["reviewer"] == "human"
	assert merged[1]["status"] == "proposed"


def test_approval_handler_persists_json_file(tmp_path: Path):
	handler = ApprovalHandler(
		workspace_root=tmp_path / "workspace",
		request_id="req-123",
	)

	handler.save_decision(
		proposal_id="fix-1",
		status="accepted",
		reviewer="human",
	)

	path = handler.approvals_path
	assert path.exists()

	data = json.loads(path.read_text(encoding="utf-8"))
	assert data["request_id"] == "req-123"
	assert data["decisions"]["fix-1"]["status"] == "accepted"

def test_approval_handler_bulk_save(tmp_path: Path):
	handler = ApprovalHandler(
		workspace_root=tmp_path / "workspace",
		request_id="req-123",
	)

	handler.save_decisions_bulk(
		[
			{
				"proposal_id": "fix-1",
				"status": "accepted",
				"reviewer": "human",
			},
			{
				"proposal_id": "fix-2",
				"status": "rejected",
				"reviewer": "human",
			},
		]
	)

	decisions = handler.load_decisions()

	assert decisions["fix-1"]["status"] == "accepted"
	assert decisions["fix-2"]["status"] == "rejected"

def test_approval_handler_bulk_save_overwrites_and_persists(tmp_path: Path):
	handler = ApprovalHandler(
		workspace_root=tmp_path / "workspace",
		request_id="req-123",
	)

	handler.save_decisions_bulk(
		[
			{"proposal_id": "fix-1", "status": "accepted", "reviewer": "human"},
			{"proposal_id": "fix-2", "status": "rejected", "reviewer": "human"},
		]
	)

	handler.save_decisions_bulk(
		[
			{"proposal_id": "fix-1", "status": "proposed", "reviewer": "human"},
		]
	)

	decisions = handler.load_decisions()

	assert decisions["fix-1"]["status"] == "proposed"
	assert decisions["fix-2"]["status"] == "rejected"
