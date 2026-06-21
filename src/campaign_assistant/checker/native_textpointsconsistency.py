from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import Issue, TEXTPOINTSCONSISTENCY
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

_POINT_TEXT_PATTERN = re.compile(
    r"(?<![\w.,])(?P<number>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>points?|punkte|punkt|punten|punt|pontos?|ponto)\b",
    flags=re.IGNORECASE,
)


def load_textpointsconsistency_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
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

    try:
        return float(value)
    except Exception:
        return None


def _point_numbers(text: str) -> list[float]:
    numbers: list[float] = []

    for match in _POINT_TEXT_PATTERN.finditer(text or ""):
        raw = match.group("number").replace(",", ".")
        try:
            numbers.append(float(raw))
        except Exception:
            continue

    return numbers


def _first_visualization_for_challenge(
    challenge: Mapping[str, Any],
    visualizations: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for visualization_id in _challenge_visualizations(challenge):
        visualization = visualizations.get(visualization_id)
        if visualization is not None:
            return visualization

    return None


def run_native_textpointsconsistency_tables(
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

    issues: list[Issue] = []

    for _, row in tasks_df.iterrows():
        task = row.to_dict()
        configured_points = _as_float(task.get("points"))

        if configured_points is None:
            continue

        text = "\n".join(
            str(_clean_scalar(task.get(field)) or "")
            for field in ("name", "description")
        )

        text_points = _point_numbers(text)
        mismatching_values = [value for value in text_points if value != configured_points]

        if not mismatching_values:
            continue

        challenge = challenges.get(_normalise_id(task.get("challenge")) or "")
        if challenge is None:
            continue

        visualization = _first_visualization_for_challenge(challenge, visualizations)
        if visualization is None:
            continue

        wave_id = _normalise_id(visualization.get("wave"))
        task_name = str(_clean_scalar(task.get("name")) or "unnamed task")
        rendered_text_points = ", ".join(
            str(int(value)) if value.is_integer() else str(value)
            for value in sorted(set(mismatching_values))
        )
        rendered_configured = (
            str(int(configured_points))
            if configured_points.is_integer()
            else str(configured_points)
        )

        issues.append(
            Issue(
                check=TEXTPOINTSCONSISTENCY,
                severity="medium",
                active_wave=wave_id in active_wave_ids if wave_id is not None else False,
                visualization_id=_normalise_id(visualization.get("id")),
                visualization=str(_clean_scalar(visualization.get("description")) or ""),
                challenge_id=_normalise_id(challenge.get("id")),
                challenge=str(_clean_scalar(challenge.get("name")) or ""),
                wave_id=wave_id,
                message=(
                    f"Task '{task_name}' mentions {rendered_text_points} point(s) in participant-facing text, "
                    f"but the exported task points value is {rendered_configured}. "
                    "Verify whether the text or the points setting is wrong."
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


def run_native_textpointsconsistency_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_textpointsconsistency_tables(file_path)
    return run_native_textpointsconsistency_tables(tables, now=now)