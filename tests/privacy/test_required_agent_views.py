from __future__ import annotations

from pathlib import Path

import pytest

from campaign_assistant.agents.content_fixer import ContentFixerAgent
from campaign_assistant.agents.privacy_guardian import PrivacyGuardianAgent
from campaign_assistant.agents.theory_grounding import TheoryGroundingAgent
from campaign_assistant.orchestration.models import AgentContext


class DummyMetadataBundle:
    def __init__(self):
        self.task_roles = []
        self.theory_sources = []


def _make_context(tmp_path: Path) -> AgentContext:
    campaign_file = tmp_path / "campaign.xlsx"
    campaign_file.write_bytes(b"dummy")

    workspace_root = tmp_path / "workspace"
    metadata_dir = workspace_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "campaign_profile.json").write_text("{}", encoding="utf-8")

    ctx = AgentContext(
        request_id="req-required-views-001",
        file_path=campaign_file,
        selected_checks=["ttm"],
        export_excel=False,
        workspace_id="ws-required-views",
        workspace_root=workspace_root,
        snapshot_id="snap-required-views-001",
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
        "active_modules": {"point_gatekeeping_checks": True, "ttm_checks": True},
    }
    ctx.shared["metadata_bundle"] = DummyMetadataBundle()
    ctx.shared["result"] = {
        "summary": {"failed_checks": ["ttm"], "total_issues": 1},
        "issues_by_check": {"ttm": [{"message": "Wrong TTM successor."}]},
        "prioritized_issues": [{"check": "ttm", "severity": "high", "active_wave": True}],
        "point_gatekeeping": {"findings": []},
    }
    ctx.shared["theory_grounding"] = {
        "uses_ttm": True,
        "failed_checks_seen": ["ttm"],
    }
    return ctx


def test_theory_grounding_requires_privacy_initialization(tmp_path: Path):
    ctx = _make_context(tmp_path)

    with pytest.raises(RuntimeError, match="requires privacy initialization"):
        TheoryGroundingAgent().run(ctx)


def test_content_fixer_requires_privacy_initialization(tmp_path: Path):
    ctx = _make_context(tmp_path)

    with pytest.raises(RuntimeError, match="requires privacy initialization"):
        ContentFixerAgent().run(ctx)


def test_semantic_agents_work_after_privacy_initialization(tmp_path: Path):
    ctx = _make_context(tmp_path)

    PrivacyGuardianAgent().run(ctx)

    tg = TheoryGroundingAgent().run(ctx)
    cf = ContentFixerAgent().run(ctx)

    assert tg.success is True
    assert cf.success is True