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

    return AgentContext(
        request_id="req-privacy-001",
        file_path=campaign_file,
        selected_checks=["ttm"],
        export_excel=False,
        workspace_id="ws-privacy",
        workspace_root=workspace_root,
        snapshot_id="snap-privacy-001",
        analysis_profile={},
        point_rules={},
        task_roles=[],
        evidence_index={},
        shared={},
    )


def test_privacy_service_builds_asset_inventory_and_policies(tmp_path: Path):
    ctx = _make_context(tmp_path)

    service = PrivacyService()
    state = service.build_privacy_state(ctx)

    assert state.request_id == "req-privacy-001"
    assert state.workspace_id == "ws-privacy"
    assert len(state.asset_inventory) >= 3
    assert "structural_change_agent" in state.agent_policies
    assert "content_fixer_agent" in state.agent_policies

    structural_policy = state.agent_policies["structural_change_agent"]
    fixer_policy = state.agent_policies["content_fixer_agent"]

    assert structural_policy.allow_raw_workbook is True
    assert fixer_policy.allow_raw_workbook is False
    assert "campaign_workbook" in [asset.asset_id for asset in state.asset_inventory]


def test_privacy_service_compatibility_policy_shape(tmp_path: Path):
    ctx = _make_context(tmp_path)

    service = PrivacyService()
    state = service.build_privacy_state(ctx)
    compat = service.to_compatibility_access_policy(state)

    assert "privacy_guardian" in compat
    assert "structural_change_agent" in compat
    assert "allowed_paths" in compat["structural_change_agent"]
    assert "redactions" in compat["content_fixer_agent"]