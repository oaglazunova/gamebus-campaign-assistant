from __future__ import annotations

import pandas as pd

from campaign_assistant.checker.native_secrets import run_native_secrets_tables


def _tables_for_secrets(
    *,
    tasks: list[dict],
    challenges: list[dict],
    visualizations: list[dict] | None = None,
    waves: list[dict] | None = None,
):
    if visualizations is None:
        visualizations = [
            {"campaign": 1, "id": 100, "description": "V1", "wave": 10},
        ]

    if waves is None:
        waves = [
            {
                "id": 10,
                "name": "Wave 1",
                "start": pd.Timestamp("2025-01-01"),
                "end": pd.Timestamp("2027-01-01"),
            }
        ]

    return {
        "tasks": pd.DataFrame(tasks),
        "challenges": pd.DataFrame(challenges),
        "visualizations": pd.DataFrame(visualizations),
        "waves": pd.DataFrame(waves),
    }


def test_native_secrets_reports_missing_secret_for_gamebus_studio_task():
    tables = _tables_for_secrets(
        tasks=[
            {
                "name": "Drink Water",
                "challenge": 1,
                "dataproviders": "GameBus Studio",
                "conditions": None,
            }
        ],
        challenges=[
            {
                "id": 1,
                "name": "Challenge 1",
                "visualizations": 100,
            }
        ],
    )

    result = run_native_secrets_tables(tables)

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert "has no secret" in result["issues"][0].message
    assert "[SECRET, EQUAL, Drink-Water]" in result["issues"][0].message
    assert result["issues"][0].active_wave is True


def test_native_secrets_ignores_non_gamebus_studio_task_without_secret():
    tables = _tables_for_secrets(
        tasks=[
            {
                "name": "Drink Water",
                "challenge": 1,
                "dataproviders": "Another Provider",
                "conditions": None,
            }
        ],
        challenges=[
            {
                "id": 1,
                "name": "Challenge 1",
                "visualizations": 100,
            }
        ],
    )

    result = run_native_secrets_tables(tables)

    assert result["status"] == "Passed"
    assert result["issues"] == []


def test_native_secrets_allows_same_secret_when_names_match():
    tables = _tables_for_secrets(
        tasks=[
            {
                "name": "Drink Water",
                "challenge": 1,
                "dataproviders": "GameBus Studio",
                "conditions": "[SECRET, EQUAL, water-secret]",
            },
            {
                "name": "Drink Water",
                "challenge": 2,
                "dataproviders": "GameBus Studio",
                "conditions": "[SECRET, EQUAL, water-secret]",
            },
        ],
        challenges=[
            {"id": 1, "name": "Challenge 1", "visualizations": 100},
            {"id": 2, "name": "Challenge 2", "visualizations": 100},
        ],
    )

    result = run_native_secrets_tables(tables)

    assert result["status"] == "Passed"
    assert result["issues"] == []


def test_native_secrets_reports_same_secret_with_different_names():
    tables = _tables_for_secrets(
        tasks=[
            {
                "name": "Drink Water",
                "challenge": 1,
                "dataproviders": "GameBus Studio",
                "conditions": "[SECRET, EQUAL, shared-secret]",
            },
            {
                "name": "Walk",
                "challenge": 2,
                "dataproviders": "GameBus Studio",
                "conditions": "[SECRET, EQUAL, shared-secret]",
            },
        ],
        challenges=[
            {"id": 1, "name": "Challenge 1", "visualizations": 100},
            {"id": 2, "name": "Challenge 2", "visualizations": 100},
        ],
    )

    result = run_native_secrets_tables(tables)

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert "same secret 'shared-secret'" in result["issues"][0].message
    assert "different names" in result["issues"][0].message