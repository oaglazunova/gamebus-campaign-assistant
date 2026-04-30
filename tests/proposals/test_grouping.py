from __future__ import annotations

from campaign_assistant.proposals.grouping import build_proposal_groups


def test_build_proposal_groups_groups_by_issue_family():
    proposals = [
        {
            "proposal_id": "p1",
            "challenge_name": "Challenge A",
            "category": "gatekeeping",
            "action_type": "annotate_gatekeeper",
            "severity": "medium",
            "status": "proposed",
            "rationale": "Need explicit gatekeeper.",
            "notes": "Annotate in task_roles.csv",
        },
        {
            "proposal_id": "p2",
            "challenge_name": "Challenge B",
            "category": "gatekeeping",
            "action_type": "annotate_gatekeeper",
            "severity": "medium",
            "status": "proposed",
            "rationale": "Need explicit gatekeeper.",
            "notes": "Annotate in task_roles.csv",
        },
        {
            "proposal_id": "p3",
            "challenge_name": "Challenge C",
            "category": "points",
            "action_type": "lower_target_points",
            "severity": "high",
            "status": "accepted",
            "rationale": "Target exceeds theoretical maximum.",
            "notes": "Lower target.",
        },
    ]

    groups = build_proposal_groups(proposals)

    assert len(groups) == 2

    gatekeeping_group = next(g for g in groups if g["issue_family"] == "missing_explicit_gatekeeper")
    points_group = next(g for g in groups if g["issue_family"] == "unreachable_target_points")

    assert gatekeeping_group["member_count"] == 2
    assert gatekeeping_group["status"] == "proposed"
    assert set(gatekeeping_group["member_proposal_ids"]) == {"p1", "p2"}
    assert "across 2 challenges" in gatekeeping_group["summary"]

    assert points_group["member_count"] == 1
    assert points_group["status"] == "accepted"


def test_build_proposal_groups_marks_mixed_status():
    proposals = [
        {
            "proposal_id": "p1",
            "challenge_name": "Challenge A",
            "category": "points",
            "action_type": "lower_target_points",
            "severity": "high",
            "status": "accepted",
        },
        {
            "proposal_id": "p2",
            "challenge_name": "Challenge B",
            "category": "points",
            "action_type": "lower_target_points",
            "severity": "high",
            "status": "rejected",
        },
    ]

    groups = build_proposal_groups(proposals)
    assert len(groups) == 1
    assert groups[0]["status"] == "mixed"
    assert groups[0]["issue_family"] == "unreachable_target_points"