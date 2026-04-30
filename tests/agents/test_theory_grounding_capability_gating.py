from __future__ import annotations

from pathlib import Path

from campaign_assistant.agents.theory_grounding import TheoryGroundingAgent
from campaign_assistant.orchestration.models import AgentContext
from campaign_assistant.agents.privacy_guardian import PrivacyGuardianAgent


def _make_context(tmp_path: Path, *, uses_ttm: bool, ttm_checks: bool) -> AgentContext:
    campaign_file = tmp_path / "campaign.xlsx"
    campaign_file.write_text("dummy", encoding="utf-8")

    return AgentContext(
        request_id="req-theory-001",
        file_path=campaign_file,
        selected_checks=["ttm"],
        export_excel=False,
        workspace_id="ws-theory",
        workspace_root=tmp_path / "workspace",
        snapshot_id="snap-001",
        analysis_profile={},
        point_rules={},
        task_roles=[],
        evidence_index={},
        shared={
            "capability_summary": {
                "capabilities": {
                    "uses_ttm": uses_ttm,
                },
                "active_modules": {
                    "ttm_checks": ttm_checks,
                },
            },
            "result": {
                "summary": {
                    "failed_checks": ["ttm"],
                }
            },
        },
    )


def test_theory_grounding_skips_when_ttm_not_enabled(tmp_path: Path):
    ctx = _make_context(tmp_path, uses_ttm=False, ttm_checks=False)

    PrivacyGuardianAgent().run(ctx)

    agent = TheoryGroundingAgent()
    response = agent.run(ctx)

    assert response.success is True
    payload = ctx.shared["theory_grounding"]
    assert payload["confidence"] == "not_applicable"
    assert payload["uses_ttm"] is False


def test_theory_grounding_runs_when_ttm_enabled(tmp_path: Path):
    ctx = _make_context(tmp_path, uses_ttm=True, ttm_checks=True)

    PrivacyGuardianAgent().run(ctx)

    agent = TheoryGroundingAgent()
    response = agent.run(ctx)

    assert response.success is True
    payload = ctx.shared["theory_grounding"]
    assert payload["confidence"] == "medium"
    assert payload["uses_ttm"] is True