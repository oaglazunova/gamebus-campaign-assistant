from __future__ import annotations

from pathlib import Path

from campaign_assistant.agents.theory_grounding import TheoryGroundingAgent
from campaign_assistant.orchestration.models import AgentContext
from campaign_assistant.agents.privacy_guardian import PrivacyGuardianAgent


def _make_context(tmp_path: Path) -> AgentContext:
    campaign_file = tmp_path / "campaign.xlsx"
    campaign_file.write_text("dummy", encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    return AgentContext(
        request_id="req-test-001",
        file_path=campaign_file,
        selected_checks=["ttm"],
        export_excel=False,
        workspace_id="ws-test",
        workspace_root=workspace_root,
        snapshot_id="snap-001",
        analysis_profile={
            "checking_scope": {"theory_checks": True},
            "intervention_model": {
                "uses_ttm": True,
                "uses_bct_mapping": True,
                "uses_comb_mapping": True,
                "uses_gatekeeping": True,
            },
            "ttm": {
                "structure_file": "evidence/theory/ttm_structure.pdf",
                "stages": [
                    "precontemplation",
                    "contemplation",
                    "preparation",
                    "action",
                    "maintenance",
                ],
            },
            "theory_grounding": {
                "mapped_interventions_file": "evidence/theory/intervention_mapping.xlsx",
            },
        },
        point_rules={},
        task_roles=[],
        evidence_index={},
        shared={},
    )


def test_theory_agent_warns_when_ttm_and_mapping_files_are_missing(tmp_path: Path):
    ctx = _make_context(tmp_path)
    ctx.shared["result"] = {
        "summary": {
            "failed_checks": [],
            "total_issues": 0,
        }
    }

    PrivacyGuardianAgent().run(ctx)

    agent = TheoryGroundingAgent()
    response = agent.run(ctx)

    assert response.success is True
    assert response.agent_name == "theory_grounding_agent"
    assert "Theory grounding" in response.summary
    assert len(response.warnings) >= 1

    payload = ctx.shared["theory_grounding"]
    assert payload["uses_ttm"] is True
    assert payload["ttm_structure_file_exists"] is False
    assert payload["mapping_summary"]["exists"] is False
    assert payload["confidence"] == "low"


def test_theory_agent_surfaces_ttm_failure_from_structural_checker(tmp_path: Path):
    ctx = _make_context(tmp_path)

    # Create fake evidence files so confidence is not low due only to missing resources
    ttm_file = ctx.workspace_root / "evidence/theory/ttm_structure.pdf"
    ttm_file.parent.mkdir(parents=True, exist_ok=True)
    ttm_file.write_bytes(b"%PDF-1.4 test")

    mapping_file = ctx.workspace_root / "evidence/theory/intervention_mapping.xlsx"
    mapping_file.write_bytes(b"not-a-real-xlsx-but-exists")

    ctx.shared["result"] = {
        "summary": {
            "failed_checks": ["ttm"],
            "total_issues": 3,
        }
    }

    PrivacyGuardianAgent().run(ctx)

    agent = TheoryGroundingAgent()
    response = agent.run(ctx)

    assert response.success is True
    payload = ctx.shared["theory_grounding"]

    assert "ttm" in payload["failed_checks_seen"]
    assert any("TTM-related failure" in note for note in payload["notes"])


def test_theory_agent_reports_task_role_counts(tmp_path: Path):
    ctx = _make_context(tmp_path)
    ctx.task_roles = [
        {"task_id": "1", "task_name": "A", "role": "gatekeeping", "notes": ""},
        {"task_id": "2", "task_name": "B", "role": "maintenance", "notes": ""},
        {"task_id": "3", "task_name": "C", "role": "maintenance", "notes": ""},
    ]
    ctx.shared["result"] = {
        "summary": {
            "failed_checks": [],
            "total_issues": 0,
        }
    }

    PrivacyGuardianAgent().run(ctx)

    agent = TheoryGroundingAgent()
    response = agent.run(ctx)

    payload = ctx.shared["theory_grounding"]
    assert payload["task_role_counts"]["gatekeeping"] == 1
    assert payload["task_role_counts"]["maintenance"] == 2