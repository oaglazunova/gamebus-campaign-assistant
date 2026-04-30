from __future__ import annotations

from campaign_assistant.proposals.context import (
    annotate_proposal_groups_with_context,
    matches_group_focus,
)


def test_annotate_proposal_groups_with_context_marks_gatekeeping_as_recommended_when_roles_missing():
    groups = [
        {
            "group_id": "g1",
            "issue_family": "missing_explicit_gatekeeper",
            "issue_label": "Missing explicit gatekeeper annotation",
            "summary": "Missing explicit gatekeeper annotation across 3 challenges (3 proposal(s))",
            "category": "gatekeeping",
            "severity": "medium",
            "status": "proposed",
            "member_count": 3,
            "member_proposal_ids": ["p1", "p2", "p3"],
            "challenge_names": ["A", "B", "C"],
            "rationales": [],
            "notes": [],
            "members": [],
        }
    ]

    capability_summary = {
        "capabilities": {
            "uses_progression": True,
            "uses_gatekeeping": None,
            "uses_maintenance_tasks": None,
            "uses_ttm": False,
        },
        "task_role_count": 0,
    }

    annotated = annotate_proposal_groups_with_context(groups, capability_summary)

    assert annotated[0]["priority"] == "recommended"
    assert "setup-needed" in annotated[0]["context_tags"]


def test_matches_group_focus_filters_expected_groups():
    group = {
        "issue_family": "ttm_manual_review",
        "context_tags": ["ttm"],
        "priority": "recommended",
    }

    assert matches_group_focus(group, "All") is True
    assert matches_group_focus(group, "Recommended now") is True
    assert matches_group_focus(group, "TTM review") is True
    assert matches_group_focus(group, "Point fixes") is False