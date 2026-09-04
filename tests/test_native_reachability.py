from __future__ import annotations

import pandas as pd

from campaign_assistant.checker.native_reachability import (
    run_native_reachability_tables,
)


def _tables(
    challenges: list[dict],
) -> dict[str, pd.DataFrame]:
    return {
        "visualizations": pd.DataFrame(
            [
                {
                    "id": 10,
                    "description": "Progression levels",
                    "campaign": 557,
                    "wave": 1,
                }
            ]
        ),
        "waves": pd.DataFrame(
            [
                {
                    "id": 1,
                    "name": "Active wave",
                    "start": pd.Timestamp("2026-01-01"),
                    "end": pd.Timestamp("2026-12-31"),
                }
            ]
        ),
        "challenges": pd.DataFrame(challenges),
    }


def test_failure_branch_counts_as_structurally_reachable() -> None:
    result = run_native_reachability_tables(
        _tables(
            [
                {
                    "id": 1,
                    "name": "Newbie",
                    "visualizations": 10,
                    "is_initial_level": 1,
                    "success_next": 2,
                    "failure_next": 1,
                },
                {
                    "id": 2,
                    "name": "Skilled",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "success_next": 3,
                    "failure_next": 4,
                },
                {
                    "id": 3,
                    "name": "Master",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "success_next": 3,
                    "failure_next": 2,
                },
                {
                    "id": 4,
                    "name": "Skilled at risk",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "success_next": 2,
                    "failure_next": 1,
                },
            ]
        ),
        now=pd.Timestamp("2026-09-03"),
    )

    assert result["status"] == "Passed"
    assert result["issues"] == []


def test_reports_nonterminal_level_with_no_incoming_reachable_path() -> None:
    result = run_native_reachability_tables(
        _tables(
            [
                {
                    "id": 1,
                    "name": "Newbie",
                    "visualizations": 10,
                    "is_initial_level": 1,
                    "success_next": 2,
                    "failure_next": 1,
                },
                {
                    "id": 2,
                    "name": "Skilled",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "success_next": 3,
                    "failure_next": 1,
                },
                {
                    "id": 3,
                    "name": "Master",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "success_next": 3,
                    "failure_next": 2,
                },
                {
                    # This level points INTO the reachable structure,
                    # but no reachable level points TO it.
                    "id": 99,
                    "name": "Skilled at risk",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "success_next": 2,
                    "failure_next": 1,
                },
            ]
        ),
        now=pd.Timestamp("2026-09-03"),
    )

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1

    issue = result["issues"][0]

    assert issue.challenge_id == "99"
    assert issue.severity == "high"
    assert issue.title == (
        "Level cannot be reached from a configured start level"
    )
    assert (
        "Progression level not reachable from any initial challenge"
        in issue.message
    )


def test_failure_only_route_does_not_count_as_successful_completion() -> None:
    result = run_native_reachability_tables(
        _tables(
            [
                {
                    "id": 1,
                    "name": "Start",
                    "visualizations": 10,
                    "is_initial_level": 1,
                    "success_next": 2,
                    "failure_next": 1,
                },
                {
                    # Success path cycles between 1 and 2.
                    "id": 2,
                    "name": "Intermediate",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "success_next": 1,
                    "failure_next": 3,
                },
                {
                    # Structurally reachable through failure,
                    # but not through the normal success path.
                    "id": 3,
                    "name": "Terminal",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "success_next": 3,
                    "failure_next": 2,
                },
            ]
        ),
        now=pd.Timestamp("2026-09-03"),
    )

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1

    issue = result["issues"][0]

    assert issue.challenge_id == "1"
    assert issue.title == (
        "No terminal level is reachable through the success path"
    )
    assert "Initial Challenge without terminal challenge" in issue.message