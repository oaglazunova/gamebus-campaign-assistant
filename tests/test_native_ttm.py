from __future__ import annotations

import pandas as pd

from campaign_assistant.checker.native_ttm import run_native_ttm_tables
from campaign_assistant.checker.schema import TTMSTRUCTURE


def _base_tables(challenges: list[dict]) -> dict[str, pd.DataFrame]:
    return {
        "visualizations": pd.DataFrame(
            [
                {
                    "id": 10,
                    "description": "Nutrition",
                    "campaign": 456,
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


def _valid_terminal_chain() -> list[dict]:
    return [
        {
            "id": 1,
            "name": "Level 1",
            "visualizations": 10,
            "is_initial_level": 1,
            "success_next": 2,
            "failure_next": 1,
        },
        {
            "id": 2,
            "name": "Level 2",
            "visualizations": 10,
            "is_initial_level": 0,
            "success_next": 3,
            "failure_next": 2,
        },
        {
            "id": 3,
            "name": "Level 3",
            "visualizations": 10,
            "is_initial_level": 0,
            "success_next": 4,
            "failure_next": 3,
        },
        {
            "id": 4,
            "name": "Level 4",
            "visualizations": 10,
            "is_initial_level": 0,
            "success_next": 5,
            "failure_next": 4,
        },
        {
            "id": 5,
            "name": "Maintenance",
            "visualizations": 10,
            "is_initial_level": 0,
            "success_next": 5,
            "failure_next": 4,
        },
    ]


def test_ttm_valid_terminal_chain_passes() -> None:
    result = run_native_ttm_tables(
        _base_tables(_valid_terminal_chain()),
        now=pd.Timestamp("2026-06-01"),
    )

    assert result["status"] == "Passed"
    assert result["issues"] == []


def test_ttm_reports_wrong_failure_in_first_four_levels() -> None:
    challenges = _valid_terminal_chain()
    challenges[0] = {**challenges[0], "failure_next": 2}

    result = run_native_ttm_tables(
        _base_tables(challenges),
        now=pd.Timestamp("2026-06-01"),
    )

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1

    issue = result["issues"][0]
    assert issue.check == TTMSTRUCTURE
    assert issue.severity == "medium"
    assert issue.active_wave is True
    assert issue.challenge_id == "1"
    assert "failure transition should point to itself" in issue.message
    assert "1 (Level 1)" in issue.message
    assert "2 (Level 2)" in issue.message


def test_ttm_reports_missing_success_target_without_crashing() -> None:
    challenges = _valid_terminal_chain()
    challenges[2] = {**challenges[2], "success_next": 999}

    result = run_native_ttm_tables(
        _base_tables(challenges),
        now=pd.Timestamp("2026-06-01"),
    )

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert "success transition does not point to an existing challenge" in result["issues"][0].message


def test_ttm_reports_relapse_at_risk_level_that_does_not_return_to_current_level() -> None:
    challenges = _valid_terminal_chain()
    # Make level 5 non-terminal and add an at-risk level 6. The at-risk level
    # fails correctly to the previous level 4 but incorrectly succeeds to itself.
    challenges[4] = {**challenges[4], "success_next": 7, "failure_next": 6}
    challenges.extend(
        [
            {
                "id": 6,
                "name": "Maintenance at risk",
                "visualizations": 10,
                "is_initial_level": 0,
                "success_next": 6,
                "failure_next": 4,
            },
            {
                "id": 7,
                "name": "Grandmaster",
                "visualizations": 10,
                "is_initial_level": 0,
                "success_next": 7,
                "failure_next": 5,
            },
        ]
    )

    result = run_native_ttm_tables(
        _base_tables(challenges),
        now=pd.Timestamp("2026-06-01"),
    )

    assert result["status"] == "Failed"
    messages = "\n".join(issue.message for issue in result["issues"])
    assert "at-risk level" in messages
    assert "should succeed back" in messages
