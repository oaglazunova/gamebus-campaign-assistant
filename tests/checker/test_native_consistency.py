from __future__ import annotations

import pandas as pd

from campaign_assistant.checker.native_consistency import run_native_consistency_tables


def _tables_for_consistency(
    *,
    rows: list[dict],
    wave_id: int = 10,
):
    visualizations = pd.DataFrame(
        [
            {
                "campaign": 1,
                "id": 100,
                "description": "Consistency Visualization",
                "wave": wave_id,
            }
        ]
    )

    challenges = pd.DataFrame(rows)

    waves = pd.DataFrame(
        [
            {
                "id": wave_id,
                "name": "Wave 1",
                "start": pd.Timestamp("2025-01-01"),
                "end": pd.Timestamp("2027-01-01"),
            }
        ]
    )

    return {
        "visualizations": visualizations,
        "challenges": challenges,
        "waves": waves,
    }


def test_native_consistency_passes_for_valid_initial_and_terminal_links():
    tables = _tables_for_consistency(
        rows=[
            {
                "campaign": 1,
                "id": 1,
                "labels": None,
                "type": "TASKS_COLLECTION",
                "name": "Initial",
                "visualizations": 100,
                "is_initial_level": 1,
                "success_next": 2,
                "failure_next": 1,
            },
            {
                "campaign": 1,
                "id": 2,
                "labels": None,
                "type": "TASKS_COLLECTION",
                "name": "Terminal",
                "visualizations": 100,
                "is_initial_level": 0,
                "success_next": 2,
                "failure_next": 1,
            },
        ]
    )

    result = run_native_consistency_tables(tables)

    assert result["status"] == "Passed"
    assert result["issues"] == []


def test_native_consistency_reports_initial_failure_not_self():
    tables = _tables_for_consistency(
        rows=[
            {
                "campaign": 1,
                "id": 1,
                "labels": None,
                "type": "TASKS_COLLECTION",
                "name": "Initial",
                "visualizations": 100,
                "is_initial_level": 1,
                "success_next": 2,
                "failure_next": 2,
            },
            {
                "campaign": 1,
                "id": 2,
                "labels": None,
                "type": "TASKS_COLLECTION",
                "name": "Terminal",
                "visualizations": 100,
                "is_initial_level": 0,
                "success_next": 2,
                "failure_next": 1,
            },
        ]
    )

    result = run_native_consistency_tables(tables)

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert result["issues"][0].challenge_id == 1
    assert result["issues"][0].message == "Initial challenge does not lead to itself on failure 2"
    assert result["issues"][0].active_wave is True


def test_native_consistency_ignores_non_terminal_success_links():
    tables = _tables_for_consistency(
        rows=[
            {
                "campaign": 1,
                "id": 1,
                "labels": None,
                "type": "TASKS_COLLECTION",
                "name": "Initial",
                "visualizations": 100,
                "is_initial_level": 1,
                "success_next": 2,
                "failure_next": 1,
            },
            {
                "campaign": 1,
                "id": 2,
                "labels": None,
                "type": "TASKS_COLLECTION",
                "name": "Middle",
                "visualizations": 100,
                "is_initial_level": 0,
                "success_next": 3,
                "failure_next": 1,
            },
            {
                "campaign": 1,
                "id": 3,
                "labels": None,
                "type": "TASKS_COLLECTION",
                "name": "Terminal",
                "visualizations": 100,
                "is_initial_level": 0,
                "success_next": 3,
                "failure_next": 2,
            },
        ]
    )

    result = run_native_consistency_tables(tables)

    assert result["status"] == "Passed"
    assert result["issues"] == []