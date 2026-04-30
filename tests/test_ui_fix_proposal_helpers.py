from campaign_assistant.ui.chat import (
    _count_fix_proposals_by_status,
    _priority_group_count,
)


def test_count_fix_proposals_by_status_counts_known_statuses():
    proposals = [
        {"proposal_id": "p1", "status": "proposed"},
        {"proposal_id": "p2", "status": "accepted"},
        {"proposal_id": "p3", "status": "rejected"},
        {"proposal_id": "p4", "status": "proposed"},
    ]

    counts = _count_fix_proposals_by_status(proposals)

    assert counts["proposed"] == 2
    assert counts["accepted"] == 1
    assert counts["rejected"] == 1


def test_priority_group_count_counts_non_normal_groups():
    groups = [
        {"group_id": "g1", "priority": "normal"},
        {"group_id": "g2", "priority": "high"},
        {"group_id": "g3", "priority": "recommended_now"},
    ]

    assert _priority_group_count(groups) == 2