from __future__ import annotations

from pathlib import Path

from campaign_assistant.agents.privacy_guardian import PrivacyGuardianAgent
from campaign_assistant.orchestration.models import AgentContext


def _make_context(tmp_path: Path) -> AgentContext:
    campaign_file = tmp_path / "campaign.xlsx"
    campaign_file.write_bytes(b"dummy")

    workspace_root = tmp_path / "workspace"
    metadata_dir = workspace_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "campaign_profile.json").write_text("{}", encoding="utf-8")

    return AgentContext(
        request_id="req-privacy-agent-001",
        file_path=campaign_file,
        selected_checks=["ttm"],
        export_excel=False,
        workspace_id="ws-privacy-agent",
        workspace_root=workspace_root,
        snapshot_id="snap-privacy-agent-001",
        analysis_profile={},
        point_rules={},
        task_roles=[],
        evidence_index={},
        shared={},
    )


def test_privacy_guardian_stores_compatibility_policy_and_rich_state(tmp_path: Path):
    ctx = _make_context(tmp_path)

    agent = PrivacyGuardianAgent()
    response = agent.run(ctx)

    assert response.success is True
    assert response.agent_name == "privacy_guardian"
    assert "privacy" in ctx.shared
    assert "privacy_state" in ctx.shared
    assert "access_policy" in response.payload
    assert "privacy_summary" in response.payload

    privacy = ctx.shared["privacy"]
    privacy_state = ctx.shared["privacy_state"]

    assert "structural_change_agent" in privacy
    assert "agent_policies" in privacy_state
    assert privacy_state["summary"]["policy_mode"] == "coarse_grained_phase_2_step_1"