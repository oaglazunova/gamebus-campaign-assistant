from __future__ import annotations

import pytest


@pytest.fixture
def minimal_analysis_result() -> dict:
    return {
        "file_name": "example_campaign.xlsx",
        "campaign_name": "Example campaign",
        "checks_run": [
            "secrets",
            "spellchecker",
            "reachability",
            "consistency",
            "visualizationintern",
            "targetpointsreachable",
        ],
        "summary": {
            "total_issues": 0,
            "failed_checks": [],
            "passed_checks": [
                "secrets",
                "spellchecker",
                "reachability",
                "consistency",
                "visualizationintern",
                "targetpointsreachable",
            ],
            "errored_checks": [],
            "issue_count_by_check": {},
            "severity_counts": {},
        },
        "issues_by_check": {},
        "prioritized_issues": [],
        "campaign_snapshot": {
            "file_name": "example_campaign.xlsx",
            "campaign_name": "Example campaign",
            "counts": {
                "waves": 1,
                "visualizations": 1,
                "challenges": 3,
                "tasks": 3,
                "transitions": 4,
            },
            "visualizations": [
                {"id": 10, "name": "Nutrition progression"},
            ],
            "challenges": [
                {
                    "id": 1,
                    "name": "Beginner",
                    "visualization_id": 10,
                    "is_initial_level": True,
                    "target_points": 50,
                },
                {
                    "id": 2,
                    "name": "Balanced eater",
                    "visualization_id": 10,
                    "is_initial_level": False,
                    "target_points": 70,
                },
                {
                    "id": 3,
                    "name": "Food master",
                    "visualization_id": 10,
                    "is_initial_level": False,
                    "target_points": 100,
                },
            ],
            "tasks": [
                {"id": 100, "name": "Task A", "challenge_id": 1},
                {"id": 101, "name": "Task B", "challenge_id": 2},
                {"id": 102, "name": "Task C", "challenge_id": 3},
            ],
            "transitions": [
                {
                    "source_challenge_id": 1,
                    "target_challenge_id": 2,
                    "transition_type": "success",
                },
                {
                    "source_challenge_id": 2,
                    "target_challenge_id": 3,
                    "transition_type": "success",
                },
                {
                    "source_challenge_id": 1,
                    "target_challenge_id": 1,
                    "transition_type": "failure",
                },
                {
                    "source_challenge_id": 2,
                    "target_challenge_id": 2,
                    "transition_type": "failure",
                },
            ],
            "extraction_warnings": [],
        },
    }
