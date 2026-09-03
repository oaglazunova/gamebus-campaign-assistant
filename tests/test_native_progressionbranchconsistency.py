from __future__ import annotations

import pandas as pd

from campaign_assistant.checker.native_progressionbranchconsistency import (
    run_native_progressionbranchconsistency_tables,
)
from campaign_assistant.checker.schema import (
    PROGRESSIONBRANCHCONSISTENCY,
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


def test_reports_lower_target_recovery_level_on_success_path() -> None:
    result = run_native_progressionbranchconsistency_tables(
        _tables(
            [
                {
                    "id": 1,
                    "name": "Proficient",
                    "visualizations": 10,
                    "is_initial_level": 1,
                    "target": 600,
                    "success_next": 2,
                    "failure_next": 1,
                },
                {
                    "id": 2,
                    "name": "Skilled at risk",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "target": 300,
                    "success_next": 3,
                    "failure_next": 1,
                },
                {
                    "id": 3,
                    "name": "Skilled",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "target": 600,
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

    assert issue.check == PROGRESSIONBRANCHCONSISTENCY
    assert issue.severity == "medium"
    assert issue.active_wave is True
    assert issue.challenge_id == "2"

    assert "normal success path" in issue.message
    assert "#1 Proficient" in issue.message
    assert "#3 Skilled" in issue.message


def test_correct_recovery_branch_is_not_reported() -> None:
    result = run_native_progressionbranchconsistency_tables(
        _tables(
            [
                {
                    "id": 1,
                    "name": "Proficient",
                    "visualizations": 10,
                    "is_initial_level": 1,
                    "target": 600,
                    "success_next": 3,
                    "failure_next": 1,
                },
                {
                    "id": 2,
                    "name": "Skilled at risk",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "target": 300,
                    "success_next": 3,
                    "failure_next": 1,
                },
                {
                    "id": 3,
                    "name": "Skilled",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "target": 600,
                    "success_next": 3,
                    "failure_next": 2,
                },
            ]
        ),
        now=pd.Timestamp("2026-09-03"),
    )

    assert result["status"] == "Passed"
    assert result["issues"] == []


def test_equal_target_reversible_chain_is_not_assumed_to_be_recovery() -> None:
    result = run_native_progressionbranchconsistency_tables(
        _tables(
            [
                {
                    "id": 1,
                    "name": "Level 1",
                    "visualizations": 10,
                    "is_initial_level": 1,
                    "target": 600,
                    "success_next": 2,
                    "failure_next": 1,
                },
                {
                    "id": 2,
                    "name": "Level 2",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "target": 600,
                    "success_next": 3,
                    "failure_next": 1,
                },
                {
                    "id": 3,
                    "name": "Level 3",
                    "visualizations": 10,
                    "is_initial_level": 0,
                    "target": 600,
                    "success_next": 3,
                    "failure_next": 2,
                },
            ]
        ),
        now=pd.Timestamp("2026-09-03"),
    )

    assert result["status"] == "Passed"
    assert result["issues"] == []