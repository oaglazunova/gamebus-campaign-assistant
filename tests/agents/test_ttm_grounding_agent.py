from __future__ import annotations

from pathlib import Path

from campaign_assistant.agents.privacy_guardian import PrivacyGuardianAgent
from campaign_assistant.agents.ttm_grounding import TTMGroundingAgent
from campaign_assistant.orchestration.models import AgentContext


def _make_context(tmp_path: Path, *, uses_ttm: bool = True) -> AgentContext:
    campaign_file = tmp_path / "campaign.xlsx"
    campaign_file.write_text("dummy", encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    return AgentContext(
        request_id="req-ttm-001",
        file_path=campaign_file,
        selected_checks=["ttm"],
        export_excel=False,
        workspace_id="ws-ttm",
        workspace_root=workspace_root,
        snapshot_id="snap-001",
        analysis_profile={
            "intervention_model": {
                "uses_ttm": uses_ttm,
            },
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
                    "ttm_checks": uses_ttm,
                },
            },
            "result": {
                "summary": {
                    "failed_checks": ["ttm"],
                    "total_issues": 1,
                }
            },
        },
    )


def test_ttm_grounding_agent_uses_release2_name_and_shared_key(tmp_path: Path):
    ctx = _make_context(tmp_path, uses_ttm=True)

    PrivacyGuardianAgent().run(ctx)
    response = TTMGroundingAgent().run(ctx)

    assert response.success is True
    assert response.agent_name == "ttm_grounding_agent"
    assert "ttm_grounding" in ctx.shared
    assert ctx.shared["ttm_grounding"]["mode"] == "ttm"
    assert ctx.shared["ttm_grounding"]["uses_ttm"] is True

    # Temporary compatibility key for existing UI/helpers.
    assert ctx.shared["theory_grounding"] == ctx.shared["ttm_grounding"]


def test_ttm_grounding_agent_skips_non_ttm_campaigns(tmp_path: Path):
    ctx = _make_context(tmp_path, uses_ttm=False)

    PrivacyGuardianAgent().run(ctx)
    response = TTMGroundingAgent().run(ctx)

    assert response.success is True
    payload = ctx.shared["ttm_grounding"]
    assert payload["confidence"] == "not_applicable"
    assert payload["uses_ttm"] is False


def test_ttm_grounding_can_be_enabled_by_ttm_tagged_theory_source():
    agent = TTMGroundingAgent()

    assert agent._resolve_uses_ttm(
        capability_summary={"capabilities": {}},
        metadata_summary={
            "theory_sources": [
                {"path": "evidence/theory/ttm_structure.pdf", "tags": ["TTM"]},
            ],
        },
        analysis_profile={},
    ) is True
