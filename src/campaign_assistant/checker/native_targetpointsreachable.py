from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import Issue, TARGETPOINTSREACHABLE


def load_targetpoints_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
    return {
        "tasks": pd.read_excel(file_path, sheet_name="tasks"),
        "challenges": pd.read_excel(file_path, sheet_name="challenges"),
        "visualizations": pd.read_excel(file_path, sheet_name="visualizations"),
        "waves": pd.read_excel(file_path, sheet_name="waves"),
    }


def _get_now_timestamp() -> pd.Timestamp:
    return pd.Timestamp.now().tz_localize(None)


def _active_wave_ids(waves_df: pd.DataFrame, now: pd.Timestamp | None = None) -> set[Any]:
    if waves_df is None or waves_df.empty:
        return set()

    now = now if now is not None else _get_now_timestamp()
    active: set[Any] = set()

    for _, row in waves_df.iterrows():
        start = row.get("start")
        end = row.get("end")
        if pd.notna(start) and pd.notna(end) and start <= now <= end:
            active.add(row.get("id"))

    return active


def _clean_scalar(value: Any) -> Any:
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


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


def _challenge_index(challenges_df: pd.DataFrame) -> dict[Any, dict[str, Any]]:
    index: dict[Any, dict[str, Any]] = {}
    for _, row in challenges_df.iterrows():
        record = row.to_dict()
        index[record["id"]] = record
    return index


def _visualization_index(visualizations_df: pd.DataFrame) -> dict[Any, dict[str, Any]]:
    index: dict[Any, dict[str, Any]] = {}
    for _, row in visualizations_df.iterrows():
        record = row.to_dict()
        index[record["id"]] = record
    return index


def _tasks_by_challenge(tasks_df: pd.DataFrame) -> dict[Any, list[dict[str, Any]]]:
    result: dict[Any, list[dict[str, Any]]] = {}
    for _, row in tasks_df.iterrows():
        record = row.to_dict()
        challenge_id = record.get("challenge")
        result.setdefault(challenge_id, []).append(record)
    return result


def _challenge_url(visualization: Mapping[str, Any], challenge: Mapping[str, Any]) -> str:
    return (
        f"https://campaigns.healthyw8.gamebus.eu/editor/for/"
        f"{visualization.get('campaign')}/{challenge.get('visualizations')}/challenges/{challenge.get('id')}"
    )


def _issue(
    *,
    challenge: Mapping[str, Any],
    visualization: Mapping[str, Any],
    active_wave_ids: set[Any],
    message: str,
) -> Issue:
    wave_id = _clean_scalar(visualization.get("wave"))
    return Issue(
        check=TARGETPOINTSREACHABLE,
        severity="high",
        active_wave=wave_id in active_wave_ids if wave_id is not None else False,
        visualization_id=_clean_scalar(visualization.get("id")),
        visualization=str(_clean_scalar(visualization.get("description")) or ""),
        challenge_id=_clean_scalar(challenge.get("id")),
        challenge=str(_clean_scalar(challenge.get("name")) or ""),
        wave_id=wave_id,
        message=message,
        url=_challenge_url(visualization, challenge),
    )


def compute_task_maximum_achievable_points(task: Mapping[str, Any], days_for_level: float) -> float | None:
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
    max_points_for_task = max_number_of_times_for_task * points
    return max_points_for_task


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
    tasks_df = tables["tasks"]
    challenges_df = tables["challenges"]
    visualizations_df = tables["visualizations"]
    waves_df = tables.get("waves", pd.DataFrame())

    challenges = _challenge_index(challenges_df)
    visualizations = _visualization_index(visualizations_df)
    tasks_by_challenge = _tasks_by_challenge(tasks_df)
    active_wave_ids = _active_wave_ids(waves_df, now=now)

    issues: list[Issue] = []

    for challenge_id, challenge in challenges.items():
        visualization = visualizations.get(challenge.get("visualizations"))
        if visualization is None:
            continue

        challenge_target_points = _as_float(challenge.get("target"))
        challenge_tasks_reachable_points = compute_challenge_reachable_points(
            challenge,
            tasks_by_challenge.get(challenge_id, []),
        )

        if challenge_target_points is not None:
            if challenge_tasks_reachable_points is not None:
                if challenge_tasks_reachable_points < challenge_target_points:
                    issues.append(
                        _issue(
                            challenge=challenge,
                            visualization=visualization,
                            active_wave_ids=active_wave_ids,
                            message=(
                                f"Challenge target points ({challenge_target_points}) cannot be reached "
                                f"with tasks (max reachable is {challenge_tasks_reachable_points})"
                            ),
                        )
                    )
            else:
                issues.append(
                    _issue(
                        challenge=challenge,
                        visualization=visualization,
                        active_wave_ids=active_wave_ids,
                        message=(
                            f"Challenge reachable points ({challenge_tasks_reachable_points}) "
                            f"cannot be computed, missing values in tasks."
                        ),
                    )
                )
        else:
            issues.append(
                _issue(
                    challenge=challenge,
                    visualization=visualization,
                    active_wave_ids=active_wave_ids,
                    message=f"Challenge no target points defined ({challenge_target_points}).",
                )
            )

    issues.sort(key=lambda item: (item.active_wave, item.challenge_id), reverse=True)

    return {
        "status": "Failed" if issues else "Passed",
        "issues": issues,
        "notes": [],
    }


def run_native_targetpointsreachable_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_targetpoints_tables(file_path)
    return run_native_targetpointsreachable_tables(tables, now=now)