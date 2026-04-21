from __future__ import annotations

import pandas as pd

from campaign_assistant.checker.native_targetpointsreachable import (
    compute_challenge_reachable_points,
    compute_task_maximum_achievable_points,
    run_native_targetpointsreachable_tables,
)


def _tables_for_targetpoints(
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


def test_compute_task_maximum_achievable_points():
    task = {
        "points": 10,
        "max_times_fired": 2,
        "min_days_between_fire": 1,
    }

    result = compute_task_maximum_achievable_points(task, days_for_level=3)

    assert result == 60


def test_compute_challenge_reachable_points_returns_none_when_duration_missing():
    challenge = {
        "id": 1,
        "evaluate_fail_every_x_minutes": None,
    }

    result = compute_challenge_reachable_points(challenge, [])

    assert result is None


def test_native_targetpoints_passes_when_target_is_reachable():
    tables = _tables_for_targetpoints(
        tasks=[
            {
                "challenge": 1,
                "points": 10,
                "max_times_fired": 2,
                "min_days_between_fire": 1,
            }
        ],
        challenges=[
            {
                "id": 1,
                "name": "Challenge 1",
                "visualizations": 100,
                "target": 50,
                "evaluate_fail_every_x_minutes": 3 * 24 * 60,
            }
        ],
    )

    result = run_native_targetpointsreachable_tables(tables)

    assert result["status"] == "Passed"
    assert result["issues"] == []


def test_native_targetpoints_reports_unreachable_target():
    tables = _tables_for_targetpoints(
        tasks=[
            {
                "challenge": 1,
                "points": 10,
                "max_times_fired": 2,
                "min_days_between_fire": 1,
            }
        ],
        challenges=[
            {
                "id": 1,
                "name": "Challenge 1",
                "visualizations": 100,
                "target": 100,
                "evaluate_fail_every_x_minutes": 3 * 24 * 60,
            }
        ],
    )

    result = run_native_targetpointsreachable_tables(tables)

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert "cannot be reached with tasks" in result["issues"][0].message
    assert result["issues"][0].active_wave is True


def test_native_targetpoints_reports_missing_target():
    tables = _tables_for_targetpoints(
        tasks=[
            {
                "challenge": 1,
                "points": 10,
                "max_times_fired": 2,
                "min_days_between_fire": 1,
            }
        ],
        challenges=[
            {
                "id": 1,
                "name": "Challenge 1",
                "visualizations": 100,
                "target": None,
                "evaluate_fail_every_x_minutes": 3 * 24 * 60,
            }
        ],
    )

    result = run_native_targetpointsreachable_tables(tables)

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert "no target points defined" in result["issues"][0].message


def test_native_targetpoints_reports_noncomputable_tasks():
    tables = _tables_for_targetpoints(
        tasks=[
            {
                "challenge": 1,
                "points": 10,
                "max_times_fired": 2,
                "min_days_between_fire": None,
            }
        ],
        challenges=[
            {
                "id": 1,
                "name": "Challenge 1",
                "visualizations": 100,
                "target": 20,
                "evaluate_fail_every_x_minutes": 3 * 24 * 60,
            }
        ],
    )

    result = run_native_targetpointsreachable_tables(tables)

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert "cannot be computed" in result["issues"][0].message