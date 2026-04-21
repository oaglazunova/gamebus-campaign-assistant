from __future__ import annotations

import pandas as pd

from campaign_assistant.checker.native_reachability import (
    REACHABILITY_INITIAL_ERROR,
    REACHABILITY_TERMINAL_ERROR,
    run_native_reachability_tables,
)


def _tables_for_progression(*, success_map: dict[int, int], initial_ids: set[int], wave_id: int = 10):
    visualizations = pd.DataFrame(
        [
            {
                "campaign": 1,
                "id": 100,
                "description": "Test Visualization",
                "wave": wave_id,
            }
        ]
    )
    challenges = []
    for cid, succ in success_map.items():
        challenges.append(
            {
                "campaign": 1,
                "id": cid,
                "labels": None,
                "type": "TASKS_COLLECTION",
                "name": f"Challenge {cid}",
                "visualizations": 100,
                "is_initial_level": 1 if cid in initial_ids else 0,
                "success_next": succ,
                "failure_next": cid,
            }
        )
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
        "challenges": pd.DataFrame(challenges),
        "waves": waves,
    }


def test_native_reachability_passes_for_linear_chain():
    tables = _tables_for_progression(success_map={1: 2, 2: 3, 3: 3}, initial_ids={1})

    result = run_native_reachability_tables(tables)

    assert result["status"] == "Passed"
    assert result["issues"] == []


def test_native_reachability_reports_initial_without_terminal():
    tables = _tables_for_progression(success_map={1: 2, 2: 1}, initial_ids={1})

    result = run_native_reachability_tables(tables)

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert result["issues"][0].message == REACHABILITY_INITIAL_ERROR
    assert result["issues"][0].active_wave is True


def test_native_reachability_reports_terminal_not_reached_from_initial():
    tables = _tables_for_progression(success_map={1: 1, 2: 2}, initial_ids={1})

    result = run_native_reachability_tables(tables)

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert result["issues"][0].challenge_id == 2
    assert result["issues"][0].message == REACHABILITY_TERMINAL_ERROR