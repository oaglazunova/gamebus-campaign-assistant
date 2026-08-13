from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import DUPLICATETASKNAMES, Issue
from campaign_assistant.checker.table_utils import (
    _active_wave_ids,
    _challenge_index,
    _challenge_url,
    _challenge_visualizations,
    _clean_scalar,
    _get_table,
    _normalise_id,
    _visualization_index,
)


def load_duplicatetasknames_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
    return {
        "tasks": pd.read_excel(file_path, sheet_name="tasks"),
        "challenges": pd.read_excel(file_path, sheet_name="challenges"),
        "visualizations": pd.read_excel(file_path, sheet_name="visualizations"),
        "waves": pd.read_excel(file_path, sheet_name="waves"),
    }


def _normalized_name(value: Any) -> str:
    return " ".join(str(_clean_scalar(value) or "").strip().lower().split())


def _fingerprint(task: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        _clean_scalar(task.get("points")),
        _clean_scalar(task.get("conditions")),
        _clean_scalar(task.get("dataproviders")),
        _clean_scalar(task.get("max_times_fired")),
        _clean_scalar(task.get("min_days_between_fire")),
        _normalise_id(task.get("challenge")),
    )


def _first_visualization_for_challenge(
    challenge: Mapping[str, Any] | None,
    visualizations: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if challenge is None:
        return None

    for visualization_id in _challenge_visualizations(challenge):
        visualization = visualizations.get(visualization_id)
        if visualization is not None:
            return visualization

    return None


def run_native_duplicatetasknames_tables(
    tables: Mapping[str, pd.DataFrame],
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tasks_df = _get_table(tables, "tasks")
    challenges_df = _get_table(tables, "challenges")
    visualizations_df = _get_table(tables, "visualizations")
    waves_df = tables.get("waves", pd.DataFrame())

    challenges = _challenge_index(challenges_df)
    visualizations = _visualization_index(visualizations_df)
    active_wave_ids = _active_wave_ids(waves_df, now=now)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for _, row in tasks_df.iterrows():
        task = row.to_dict()
        name_key = _normalized_name(task.get("name"))

        if name_key:
            grouped[name_key].append(task)

    issues: list[Issue] = []

    for _, duplicate_tasks in grouped.items():
        if len(duplicate_tasks) <= 1:
            continue

        fingerprints = {_fingerprint(task) for task in duplicate_tasks}

        # Exact duplicates are not reported here. This check is intended to
        # highlight copied/similar task names that behave differently.
        if len(fingerprints) <= 1:
            continue

        first = duplicate_tasks[0]
        challenge = challenges.get(_normalise_id(first.get("challenge")) or "")
        visualization = _first_visualization_for_challenge(challenge, visualizations)

        if challenge is None or visualization is None:
            continue

        wave_id = _normalise_id(visualization.get("wave"))
        task_name = str(_clean_scalar(first.get("name")) or "unnamed task")

        refs: list[str] = []
        for task in duplicate_tasks:
            challenge_id = _normalise_id(task.get("challenge"))
            task_challenge = challenges.get(challenge_id or {})
            refs.append(
                f"{challenge_id} ({_clean_scalar(task_challenge.get('name')) or 'unnamed challenge'})"
            )

        issues.append(
            Issue(
                check=DUPLICATETASKNAMES,
                severity="medium",
                active_wave=wave_id in active_wave_ids if wave_id is not None else False,
                visualization_id=_normalise_id(visualization.get("id")),
                visualization=str(_clean_scalar(visualization.get("description")) or ""),
                challenge_id=_normalise_id(challenge.get("id")),
                challenge=str(_clean_scalar(challenge.get("name")) or ""),
                wave_id=wave_id,
                title="Duplicate task names have different settings",
                message=(
                    f"Task name '{task_name}' is reused for tasks with different settings. "
                    "This check only reports duplicate names when the duplicated tasks differ in meaningful fields "
                    "(points, conditions, provider, reward limits, reset window, or challenge). "
                    f"Review these challenge references: {refs}."
                ),
                url=_challenge_url(visualization, challenge),
            )
        )

    issues.sort(key=lambda item: (item.active_wave, item.challenge_id), reverse=True)

    return {
        "status": "Failed" if issues else "Passed",
        "issues": issues,
        "notes": [],
    }


def run_native_duplicatetasknames_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_duplicatetasknames_tables(file_path)
    return run_native_duplicatetasknames_tables(tables, now=now)