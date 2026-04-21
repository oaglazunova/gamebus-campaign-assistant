from __future__ import annotations

import pandas as pd

from campaign_assistant.checker.native_ttm import run_native_ttm_tables


def _tables_for_ttm(
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


def test_native_ttm_passes_for_linear_levels_with_final_self_success():
    tables = _tables_for_ttm(
        visualizations=[
            {"campaign": 1, "id": 100, "description": "TTM Levels", "wave": 10},
        ],
        challenges=[
            {"id": 1, "name": "L1", "visualizations": 100, "is_initial_level": 1, "success_next": 2, "failure_next": 1},
            {"id": 2, "name": "L2", "visualizations": 100, "is_initial_level": 0, "success_next": 3, "failure_next": 2},
            {"id": 3, "name": "L3", "visualizations": 100, "is_initial_level": 0, "success_next": 4, "failure_next": 3},
            {"id": 4, "name": "L4", "visualizations": 100, "is_initial_level": 0, "success_next": 5, "failure_next": 4},
            {"id": 5, "name": "Final", "visualizations": 100, "is_initial_level": 0, "success_next": 5, "failure_next": 4},
        ],
    )

    result = run_native_ttm_tables(tables, norelapselevels=4)

    assert result["status"] == "Passed"
    assert result["issues"] == []


def test_native_ttm_reports_normal_level_failure_not_self():
    tables = _tables_for_ttm(
        visualizations=[
            {"campaign": 1, "id": 100, "description": "TTM Levels", "wave": 10},
        ],
        challenges=[
            {"id": 1, "name": "L1", "visualizations": 100, "is_initial_level": 1, "success_next": 2, "failure_next": 99},
            {"id": 2, "name": "L2", "visualizations": 100, "is_initial_level": 0, "success_next": 3, "failure_next": 2},
            {"id": 3, "name": "L3", "visualizations": 100, "is_initial_level": 0, "success_next": 4, "failure_next": 3},
            {"id": 4, "name": "L4", "visualizations": 100, "is_initial_level": 0, "success_next": 5, "failure_next": 4},
            {"id": 5, "name": "Final", "visualizations": 100, "is_initial_level": 0, "success_next": 5, "failure_next": 4},
        ],
    )

    result = run_native_ttm_tables(tables, norelapselevels=4)

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert "should have failure success level to itself" in result["issues"][0].message


def test_native_ttm_reports_final_level_failure_not_previous():
    tables = _tables_for_ttm(
        visualizations=[
            {"campaign": 1, "id": 100, "description": "TTM Levels", "wave": 10},
        ],
        challenges=[
            {"id": 1, "name": "L1", "visualizations": 100, "is_initial_level": 1, "success_next": 2, "failure_next": 1},
            {"id": 2, "name": "L2", "visualizations": 100, "is_initial_level": 0, "success_next": 3, "failure_next": 2},
            {"id": 3, "name": "L3", "visualizations": 100, "is_initial_level": 0, "success_next": 4, "failure_next": 3},
            {"id": 4, "name": "L4", "visualizations": 100, "is_initial_level": 0, "success_next": 5, "failure_next": 4},
            {"id": 5, "name": "Final", "visualizations": 100, "is_initial_level": 0, "success_next": 5, "failure_next": 1},
        ],
    )

    result = run_native_ttm_tables(tables, norelapselevels=4)

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert "should have failure to previous level" in result["issues"][0].message


def test_native_ttm_reports_relapse_level_rules():
    tables = _tables_for_ttm(
        visualizations=[
            {"campaign": 1, "id": 100, "description": "TTM Levels", "wave": 10},
        ],
        challenges=[
            {"id": 1, "name": "L1", "visualizations": 100, "is_initial_level": 1, "success_next": 2, "failure_next": 1},
            {"id": 2, "name": "L2", "visualizations": 100, "is_initial_level": 0, "success_next": 3, "failure_next": 2},
            {"id": 3, "name": "L3", "visualizations": 100, "is_initial_level": 0, "success_next": 4, "failure_next": 3},
            {"id": 4, "name": "L4", "visualizations": 100, "is_initial_level": 0, "success_next": 5, "failure_next": 4},
            {"id": 5, "name": "Action", "visualizations": 100, "is_initial_level": 0, "success_next": 7, "failure_next": 6},
            {"id": 6, "name": "At risk", "visualizations": 100, "is_initial_level": 0, "success_next": 1, "failure_next": 1},
            {"id": 7, "name": "Next", "visualizations": 100, "is_initial_level": 0, "success_next": 7, "failure_next": 5},
        ],
    )

    result = run_native_ttm_tables(tables, norelapselevels=4)

    assert result["status"] == "Failed"
    assert len(result["issues"]) >= 1
    assert any("At risk level" in issue.message for issue in result["issues"])