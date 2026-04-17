from __future__ import annotations

from pathlib import Path

from campaign_assistant.agents.content_fixer import ContentFixerAgent
from campaign_assistant.orchestration.models import AgentContext


def _make_context(tmp_path: Path, *, progression_enabled: bool, ttm_enabled: bool, uses_ttm: bool) -> AgentContext:
	campaign_file = tmp_path / "campaign.xlsx"
	campaign_file.write_text("dummy", encoding="utf-8")

	return AgentContext(
		request_id="req-fixer-001",
		file_path=campaign_file,
		selected_checks=["ttm"],
		export_excel=False,
		workspace_id="ws-fixer",
		workspace_root=tmp_path / "workspace",
		snapshot_id="snap-001",
		analysis_profile={
			"checking_scope": {
				"content_fix_suggestions": True,
			}
		},
		point_rules={},
		task_roles=[],
		evidence_index={},
		shared={
			"capability_summary": {
				"capabilities": {
					"uses_ttm": uses_ttm,
				},
				"active_modules": {
					"point_gatekeeping_checks": progression_enabled,
					"ttm_checks": ttm_enabled,
				},
			},
			"result": {
				"point_gatekeeping": {
					"findings": [
						{
							"challenge_name": "Challenge A",
							"target_points": 20,
							"theoretical_max_points": 18,
							"explicit_gatekeepers": [],
							"explicit_maintenance": [],
							"inferred_gatekeepers": ["Task X"],
							"warnings": [
								"Target points exceed the theoretical maximum.",
								"No explicit gatekeeping task is marked for this challenge.",
							],
							"suggestions": [],
						}
					]
				}
			},
			"theory_grounding": {
				"uses_ttm": uses_ttm,
				"failed_checks_seen": ["ttm"],
			},
		},
	)


def test_content_fixer_skips_progression_proposals_when_progression_not_enabled(tmp_path: Path):
	ctx = _make_context(tmp_path, progression_enabled=False, ttm_enabled=False, uses_ttm=False)

	agent = ContentFixerAgent()
	response = agent.run(ctx)

	payload = ctx.shared["fix_proposals"]
	assert payload["proposal_count"] == 0
	assert any("Progression/point-gatekeeping" in note for note in payload["notes"])


def test_content_fixer_only_emits_ttm_proposal_when_ttm_enabled(tmp_path: Path):
	ctx = _make_context(tmp_path, progression_enabled=False, ttm_enabled=True, uses_ttm=True)

	agent = ContentFixerAgent()
	response = agent.run(ctx)

	payload = ctx.shared["fix_proposals"]
	assert payload["proposal_count"] == 1
	assert payload["proposals"][0]["action_type"] == "manual_ttm_review"


def test_content_fixer_defers_strengthen_gatekeeping_until_roles_exist(tmp_path: Path):
    ctx = _make_context(tmp_path, progression_enabled=True, ttm_enabled=False, uses_ttm=False)

    ctx.shared["result"]["point_gatekeeping"]["findings"] = [
        {
            "challenge_name": "Challenge A",
            "target_points": 20,
            "theoretical_max_points": 18,
            "explicit_gatekeepers": [],
            "explicit_maintenance": [],
            "inferred_gatekeepers": ["Task X"],
            "warnings": [
                "Reachable even without completing the effective gatekeeping task.",
            ],
            "suggestions": [],
        }
    ]

    agent = ContentFixerAgent()
    agent.run(ctx)

    payload = ctx.shared["fix_proposals"]

    action_types = [p["action_type"] for p in payload["proposals"]]
    assert "strengthen_gatekeeping" not in action_types
    assert any("deferred stronger gatekeeping-point proposals" in note.lower() for note in payload["notes"])


def test_content_fixer_emits_strengthen_gatekeeping_when_roles_exist(tmp_path: Path):
    ctx = _make_context(tmp_path, progression_enabled=True, ttm_enabled=False, uses_ttm=False)

    ctx.task_roles = [
        {"task_id": "1", "task_name": "Walk 20 minutes", "role": "gatekeeping", "notes": ""},
    ]

    ctx.shared["result"]["point_gatekeeping"]["findings"] = [
        {
            "challenge_name": "Challenge A",
            "target_points": 20,
            "theoretical_max_points": 18,
            "explicit_gatekeepers": [],
            "explicit_maintenance": [],
            "inferred_gatekeepers": ["Task X"],
            "warnings": [
                "Reachable even without completing the effective gatekeeping task.",
            ],
            "suggestions": [],
        }
    ]

    agent = ContentFixerAgent()
    agent.run(ctx)

    payload = ctx.shared["fix_proposals"]

    action_types = [p["action_type"] for p in payload["proposals"]]
    assert "strengthen_gatekeeping" in action_types
