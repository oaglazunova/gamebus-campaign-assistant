# This file contains checker logic adapted from GameBusChecker:
# https://github.com/SergeAutexier/GameBusChecker
#
# Original work:
#   Author: Serge Autexier
#   Copyright: DFKI GmbH 2026
#   License: Apache License 2.0
#
# Modifications:
#   Refactored and extended for GameBus Campaign Assistant by Olga Glazunova, 2026.
#   Changes include native checker integration, issue normalization, defensive handling
#   of campaign-export edge cases, assistant-facing messages, and additional guidance.
#
# Unless otherwise stated, original code in this repository is licensed under MIT.
# The adapted GameBusChecker-derived portions remain subject to Apache License 2.0.


from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import Issue, TARGETPOINTSREACHABLE
from campaign_assistant.checker.table_utils import (
    _active_wave_ids,
    _challenge_index,
    _challenge_url,
    _challenge_visualizations,
    _clean_scalar,
    _coverage_note,
    _get_table,
    _normalise_id,
    _visualization_index,
)


def load_targetpoints_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
    return {
        "tasks": pd.read_excel(file_path, sheet_name="tasks"),
        "challenges": pd.read_excel(file_path, sheet_name="challenges"),
        "visualizations": pd.read_excel(file_path, sheet_name="visualizations"),
        "waves": pd.read_excel(file_path, sheet_name="waves"),
    }


def _as_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if value is None:
        return None

    try:
        return float(value)
    except Exception:
        return None


def _tasks_by_challenge(tasks_df: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}

    for _, row in tasks_df.iterrows():
        record = row.to_dict()
        challenge_id = _normalise_id(record.get("challenge"))

        if challenge_id is not None:
            result.setdefault(challenge_id, []).append(record)

    return result


def _first_existing_visualization(
    challenge: Mapping[str, Any],
    visualizations: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for visualization_id in _challenge_visualizations(challenge):
        visualization = visualizations.get(visualization_id)

        if visualization is not None:
            return visualization

    return None


def _issue(
    *,
    challenge: Mapping[str, Any],
    visualization: Mapping[str, Any],
    active_wave_ids: set[str],
    title: str,
    message: str,
) -> Issue:
    wave_id = _normalise_id(visualization.get("wave"))

    return Issue(
        check=TARGETPOINTSREACHABLE,
        severity="high",
        active_wave=wave_id in active_wave_ids if wave_id is not None else False,
        visualization_id=_normalise_id(visualization.get("id")),
        visualization=str(_clean_scalar(visualization.get("description")) or ""),
        challenge_id=_normalise_id(challenge.get("id")),
        challenge=str(_clean_scalar(challenge.get("name")) or ""),
        wave_id=wave_id,
        title=title,
        message=message,
        url=_challenge_url(visualization, challenge),
    )


def compute_task_maximum_achievable_points(
    task: Mapping[str, Any],
    days_for_level: float,
) -> float | None:
    points = _as_float(task.get("points"))
    reward_count = _as_float(task.get("max_times_fired"))
    time_window = _as_float(task.get("min_days_between_fire"))

    # Safer than legacy:
    # if any required value is missing or non-positive, we treat it as non-computable.
    if (
        points is None
        or reward_count is None
        or time_window is None
        or time_window <= 0
        or days_for_level < 0
    ):
        return None

    p = math.floor(days_for_level / time_window)
    max_number_of_times_for_task = p * reward_count + min(
        days_for_level - (p * time_window),
        reward_count,
    )

    return max_number_of_times_for_task * points


def compute_challenge_reachable_points(
    challenge: Mapping[str, Any],
    challenge_tasks: list[dict[str, Any]],
) -> float | None:
    duration_minutes = _as_float(challenge.get("evaluate_fail_every_x_minutes"))

    if duration_minutes is None:
        return None

    days_for_level = duration_minutes / (24 * 60)
    total = 0.0

    for task in challenge_tasks:
        points = compute_task_maximum_achievable_points(task, days_for_level)

        if points is None:
            return None

        total += points

    return total


def run_native_targetpointsreachable_tables(
    tables: Mapping[str, pd.DataFrame],
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tasks_df = _get_table(tables, "tasks")
    challenges_df = _get_table(tables, "challenges")
    visualizations_df = _get_table(tables, "visualizations")
    waves_df = tables.get("waves", pd.DataFrame())

    challenges = _challenge_index(challenges_df)
    visualizations = _visualization_index(visualizations_df)
    tasks_by_challenge = _tasks_by_challenge(tasks_df)
    active_wave_ids = _active_wave_ids(waves_df, now=now)

    issues: list[Issue] = []
    notes: list[str] = []
    memberships_evaluated = 0

    for challenge_id, challenge in challenges.items():
        visualization_ids = _challenge_visualizations(challenge)
        memberships_evaluated += len(visualization_ids)

        visualization = _first_existing_visualization(challenge, visualizations)

        if visualization is None:
            continue

        challenge_target_points = _as_float(challenge.get("target"))
        challenge_tasks_reachable_points = compute_challenge_reachable_points(
            challenge,
            tasks_by_challenge.get(challenge_id, []),
        )

        if challenge_target_points is None:
            issues.append(
                _issue(
                    challenge=challenge,
                    visualization=visualization,
                    active_wave_ids=active_wave_ids,
                    title="Target points are missing",
                    message="Challenge no target points defined (None).",
                )
            )
            continue

        if challenge_tasks_reachable_points is None:
            issues.append(
                _issue(
                    challenge=challenge,
                    visualization=visualization,
                    active_wave_ids=active_wave_ids,
                    title="Reachable points cannot be calculated",
                    message=(
                        "Challenge reachable points cannot be computed because required values are "
                        "missing or invalid. Check the challenge evaluation interval and the task "
                        "point/reward/reset-window values."
                    ),
                )
            )
            continue

        if challenge_tasks_reachable_points < challenge_target_points:
            issues.append(
                _issue(
                    challenge=challenge,
                    visualization=visualization,
                    active_wave_ids=active_wave_ids,
                    title="Target points cannot be reached",
                    message=(
                        f"Challenge target points ({challenge_target_points}) cannot be reached "
                        f"with tasks (max reachable is {challenge_tasks_reachable_points})"
                    ),
                )
            )

    coverage_problem = _coverage_note(
        check_name="Target points reachable",
        memberships=memberships_evaluated,
        challenge_count=len(challenges_df),
        visualization_count=len(visualizations_df),
    )

    if coverage_problem:
        notes.append(coverage_problem)

    issues.sort(key=lambda item: (item.active_wave, item.challenge_id), reverse=True)

    return {
        "status": "Error" if coverage_problem else "Failed" if issues else "Passed",
        "issues": issues,
        "notes": notes,
    }


def run_native_targetpointsreachable_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_targetpoints_tables(file_path)
    return run_native_targetpointsreachable_tables(tables, now=now)