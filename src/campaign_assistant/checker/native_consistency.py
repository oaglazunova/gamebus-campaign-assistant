from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import CONSISTENCY, Issue
from campaign_assistant.checker.table_utils import (
    _active_wave_ids,
    _challenge_index,
    _challenge_url,
    _clean_scalar,
    _get_table,
    _is_initial,
)


def load_consistency_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
    return {
        "visualizations": pd.read_excel(file_path, sheet_name="visualizations"),
        "challenges": pd.read_excel(file_path, sheet_name="challenges"),
        "waves": pd.read_excel(file_path, sheet_name="waves"),
    }


def _issue(
    *,
    visualization: Mapping[str, Any],
    challenge: Mapping[str, Any],
    active_wave_ids: set[Any],
    message: str,
) -> Issue:
    wave_id = _clean_scalar(visualization.get("wave"))
    return Issue(
        check=CONSISTENCY,
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


def run_native_consistency_tables(
    tables: Mapping[str, pd.DataFrame],
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    visualizations_df = _get_table(tables, "visualizations")
    challenges_df = _get_table(tables, "challenges")
    waves_df = tables.get("waves", pd.DataFrame())

    challenges = _challenge_index(challenges_df)
    active_wave_ids = _active_wave_ids(waves_df, now=now)

    issues: list[Issue] = []

    for _, vis_row in visualizations_df.iterrows():
        visualization = vis_row.to_dict()
        visualization_id = visualization["id"]
        visualization_challenges = [
            challenge
            for challenge in challenges.values()
            if challenge.get("visualizations") == visualization_id
        ]

        for challenge in visualization_challenges:
            challenge_id = challenge.get("id")

            if not _is_initial(challenge):
                continue

            failure_next = challenge.get("failure_next")
            if failure_next == challenge_id:
                continue

            issues.append(
                _issue(
                    visualization=visualization,
                    challenge=challenge,
                    active_wave_ids=active_wave_ids,
                    message=f"Initial challenge does not lead to itself on failure {failure_next}",
                )
            )

    issues.sort(key=lambda item: (item.active_wave, item.challenge_id), reverse=True)

    return {
        "status": "Failed" if issues else "Passed",
        "issues": issues,
        "notes": [],
    }


def run_native_consistency_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_consistency_tables(file_path)
    return run_native_consistency_tables(tables, now=now)
