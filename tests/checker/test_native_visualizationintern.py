from __future__ import annotations

import pandas as pd

from campaign_assistant.checker.native_visualizationintern import run_native_visualizationintern_tables


def _tables_for_visualizationintern(
    *,
    visualizations: list[dict],
    challenges: list[dict],
    waves: list[dict] | None = None,
):
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
        "visualizations": pd.DataFrame(visualizations),
        "challenges": pd.DataFrame(challenges),
        "waves": pd.DataFrame(waves),
    }


def test_native_visualizationintern_passes_when_reachable_terminals_stay_in_same_visualization_and_label():
    tables = _tables_for_visualizationintern(
        visualizations=[
            {"campaign": 1, "id": 100, "description": "V1", "wave": 10},
        ],
        challenges=[
            {
                "campaign": 1,
                "id": 1,
                "name": "Initial",
                "visualizations": 100,
                "labels": "A",
                "is_initial_level": 1,
                "success_next": 2,
                "failure_next": 1,
            },
            {
                "campaign": 1,
                "id": 2,
                "name": "Terminal",
                "visualizations": 100,
                "labels": "A",
                "is_initial_level": 0,
                "success_next": 2,
                "failure_next": 1,
            },
        ],
    )

    result = run_native_visualizationintern_tables(tables)

    assert result["status"] == "Passed"
    assert result["issues"] == []


def test_native_visualizationintern_reports_reachable_terminal_with_different_label():
    tables = _tables_for_visualizationintern(
        visualizations=[
            {"campaign": 1, "id": 100, "description": "V1", "wave": 10},
        ],
        challenges=[
            {
                "campaign": 1,
                "id": 1,
                "name": "Initial",
                "visualizations": 100,
                "labels": "A",
                "is_initial_level": 1,
                "success_next": 2,
                "failure_next": 1,
            },
            {
                "campaign": 1,
                "id": 2,
                "name": "Terminal",
                "visualizations": 100,
                "labels": "B",
                "is_initial_level": 0,
                "success_next": 2,
                "failure_next": 1,
            },
        ],
    )

    result = run_native_visualizationintern_tables(tables)

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert result["issues"][0].challenge_id == 2
    assert "reachable challenge labels = 'B'" in result["issues"][0].message
    assert result["issues"][0].active_wave is True


def test_native_visualizationintern_reports_reachable_terminal_with_different_visualization():
    tables = _tables_for_visualizationintern(
        visualizations=[
            {"campaign": 1, "id": 100, "description": "V1", "wave": 10},
            {"campaign": 1, "id": 200, "description": "V2", "wave": 10},
        ],
        challenges=[
            {
                "campaign": 1,
                "id": 1,
                "name": "Initial",
                "visualizations": 100,
                "labels": "A",
                "is_initial_level": 1,
                "success_next": 2,
                "failure_next": 1,
            },
            {
                "campaign": 1,
                "id": 2,
                "name": "Cross Terminal",
                "visualizations": 200,
                "labels": "A",
                "is_initial_level": 0,
                "success_next": 2,
                "failure_next": 1,
            },
        ],
    )

    result = run_native_visualizationintern_tables(tables)

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert result["issues"][0].challenge_id == 2
    assert "reachable challenge visualization = '200'" in result["issues"][0].message


def test_native_visualizationintern_treats_missing_labels_as_equal():
    tables = _tables_for_visualizationintern(
        visualizations=[
            {"campaign": 1, "id": 100, "description": "V1", "wave": 10},
        ],
        challenges=[
            {
                "campaign": 1,
                "id": 1,
                "name": "Initial",
                "visualizations": 100,
                "labels": None,
                "is_initial_level": 1,
                "success_next": 2,
                "failure_next": 1,
            },
            {
                "campaign": 1,
                "id": 2,
                "name": "Terminal",
                "visualizations": 100,
                "labels": None,
                "is_initial_level": 0,
                "success_next": 2,
                "failure_next": 1,
            },
        ],
    )

    result = run_native_visualizationintern_tables(tables)

    assert result["status"] == "Passed"
    assert result["issues"] == []