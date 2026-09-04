from __future__ import annotations

import pandas as pd

from campaign_assistant.checker.native_secrets import (
    run_native_secrets_tables,
)


def _tables(
    conditions: str,
    *,
    task_name: str = "Example task",
) -> dict[str, pd.DataFrame]:
    return {
        "tasks": pd.DataFrame(
            [
                {
                    "id": 100,
                    "name": task_name,
                    "challenge": 1,
                    "dataproviders": "GameBus Studio",
                    "conditions": conditions,
                }
            ]
        ),
        "challenges": pd.DataFrame(
            [
                {
                    "id": 1,
                    "name": "Example level",
                    "visualizations": 10,
                }
            ]
        ),
        "visualizations": pd.DataFrame(
            [
                {
                    "id": 10,
                    "description": "Example progression",
                    "wave": 20,
                    "campaign": 557,
                }
            ]
        ),
        "waves": pd.DataFrame(
            [
                {
                    "id": 20,
                    "name": "Active wave",
                    "start": pd.Timestamp("2026-01-01"),
                    "end": pd.Timestamp("2026-12-31"),
                }
            ]
        ),
    }


def test_multiple_secret_conditions_are_reported() -> None:
    result = run_native_secrets_tables(
        _tables(
            "[SECRET, DIFFERENT, old-secret], "
            "[SECRET, EQUAL, intended-secret]"
        ),
        now=pd.Timestamp("2026-09-04"),
    )

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1

    issue = result["issues"][0]

    assert issue.title == "Task has multiple SECRET conditions"
    assert "2 SECRET conditions" in issue.message
    assert "[SECRET, DIFFERENT, old-secret]" in issue.message
    assert "[SECRET, EQUAL, intended-secret]" in issue.message


def test_two_secret_equal_conditions_are_reported() -> None:
    result = run_native_secrets_tables(
        _tables(
            "[SECRET, EQUAL, first-secret], "
            "[SECRET, EQUAL, second-secret]"
        ),
        now=pd.Timestamp("2026-09-04"),
    )

    assert result["status"] == "Failed"

    assert any(
        issue.title == "Task has multiple SECRET conditions"
        for issue in result["issues"]
    )


def test_one_secret_equal_condition_is_valid() -> None:
    result = run_native_secrets_tables(
        _tables(
            "[SECRET, EQUAL, intended-secret]"
        ),
        now=pd.Timestamp("2026-09-04"),
    )

    assert result["status"] == "Passed"
    assert result["issues"] == []


def test_non_secret_conditions_do_not_count_as_multiple_secrets() -> None:
    result = run_native_secrets_tables(
        _tables(
            "[SECRET, EQUAL, intended-secret], "
            "[ACTIVITY_TYPE, EQUAL, WALKING], "
            "[DISTANCE, GREATER, 1000]"
        ),
        now=pd.Timestamp("2026-09-04"),
    )

    assert result["status"] == "Passed"
    assert result["issues"] == []