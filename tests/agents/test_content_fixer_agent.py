from __future__ import annotations

import json
from pathlib import Path

from campaign_assistant.agents.content_fixer import ContentFixerAgent
from campaign_assistant.orchestration.models import AgentContext


def _make_context(tmp_path: Path) -> AgentContext:
	campaign_file = tmp_path / "campaign.xlsx"
	campaign_file.write_text("dummy", encoding="utf-8")

	workspace_root = tmp_path / "workspace"
	workspace_root.mkdir(parents=True, exist_ok=True)

	return AgentContext(
		request_id="req-fix-001",
		file_path=campaign_file,
		selected_checks=["ttm"],
		export_excel=False,
		workspace_id="ws-fix",
		workspace_root=workspace_root,
		snapshot_id="snap-001",
		analysis_profile={
			"checking_scope": {
				"content_fix_suggestions": True,
			}
		},
		point_rules={},
		task_roles=[],
		evidence_index={},
		shared={},
	)


def test_content_fixer_generates_proposals_from_point_gatekeeping_findings(tmp_path: Path):
	ctx = _make_context(tmp_path)
	ctx.shared["result"] = {
		"point_gatekeeping": {
			"findings": [
				{
					"challenge_name": "Skilled At Risk",
					"target_points": 20,
					"theoretical_max_points": 18,
					"explicit_gatekeepers": [],
					"explicit_maintenance": [],
					"inferred_gatekeepers": ["Reflection task"],
					"warnings": [
						"Target points exceed the theoretical maximum.",
						"No explicit gatekeeping task is marked for this challenge.",
					],
					"suggestions": [],
				}
			]
		}
	}
	ctx.shared["theory_grounding"] = {
		"uses_ttm": True,
		"failed_checks_seen": [],
	}

	agent = ContentFixerAgent()
	response = agent.run(ctx)

	assert response.success is True
	payload = ctx.shared["fix_proposals"]
	assert payload["proposal_count"] >= 2
	assert any(p["action_type"] == "lower_target_points" for p in payload["proposals"])
	assert any(p["action_type"] == "annotate_gatekeeper" for p in payload["proposals"])


def test_content_fixer_adds_manual_ttm_review_when_ttm_failed(tmp_path: Path):
	ctx = _make_context(tmp_path)
	ctx.shared["result"] = {
		"point_gatekeeping": {
			"findings": []
		}
	}
	ctx.shared["theory_grounding"] = {
		"uses_ttm": True,
		"failed_checks_seen": ["ttm"],
	}

	agent = ContentFixerAgent()
	response = agent.run(ctx)

	payload = ctx.shared["fix_proposals"]
	assert any(p["action_type"] == "manual_ttm_review" for p in payload["proposals"])


def test_content_fixer_persists_proposals_to_workspace(tmp_path: Path):
	ctx = _make_context(tmp_path)
	ctx.shared["result"] = {
		"point_gatekeeping": {
			"findings": [
				{
					"challenge_name": "Challenge A",
					"target_points": None,
					"theoretical_max_points": 10,
					"explicit_gatekeepers": [],
					"explicit_maintenance": [],
					"inferred_gatekeepers": [],
					"warnings": [
						"Challenge has no target points defined."
					],
					"suggestions": [],
				}
			]
		}
	}
	ctx.shared["theory_grounding"] = {
		"uses_ttm": False,
		"failed_checks_seen": [],
	}

	agent = ContentFixerAgent()
	response = agent.run(ctx)

	payload = ctx.shared["fix_proposals"]
	path = payload["proposals_path"]
	assert path is not None

	saved = Path(path)
	assert saved.exists()

	data = json.loads(saved.read_text(encoding="utf-8"))
	assert data["proposal_count"] >= 1


def test_content_fixer_uses_configurable_role_annotation_target(tmp_path: Path):
	ctx = _make_context(tmp_path)
	ctx.analysis_profile["execution_preferences"] = {
		"role_annotation_target": "task_roles_csv"
	}
	ctx.shared["result"] = {
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
						"No explicit gatekeeping task is marked for this challenge.",
					],
					"suggestions": [],
				}
			]
		}
	}
	ctx.shared["theory_grounding"] = {
		"uses_ttm": False,
		"failed_checks_seen": [],
	}

	agent = ContentFixerAgent()
	agent.run(ctx)

	proposals = ctx.shared["fix_proposals"]["proposals"]
	gatekeeper_proposal = next(
		p for p in proposals if p["action_type"] == "annotate_gatekeeper"
	)

	assert "task_roles.csv" in gatekeeper_proposal["notes"]

def test_content_fixer_uses_gamebus_role_annotation_target_when_configured(tmp_path: Path):
    ctx = _make_context(tmp_path)
    ctx.analysis_profile["execution_preferences"] = {
        "role_annotation_target": "gamebus"
    }
    ctx.shared["result"] = {
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
                        "No explicit gatekeeping task is marked for this challenge.",
                    ],
                    "suggestions": [],
                }
            ]
        }
    }
    ctx.shared["theory_grounding"] = {
        "uses_ttm": False,
        "failed_checks_seen": [],
    }

    agent = ContentFixerAgent()
    agent.run(ctx)

    proposals = ctx.shared["fix_proposals"]["proposals"]
    gatekeeper_proposal = next(
        p for p in proposals if p["action_type"] == "annotate_gatekeeper"
    )

    assert "GameBus" in gatekeeper_proposal["notes"]
