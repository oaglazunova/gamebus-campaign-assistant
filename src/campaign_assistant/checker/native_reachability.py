from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import Issue, REACHABILITY
from campaign_assistant.checker.table_utils import (
    _active_wave_ids,
    _challenge_index,
    _challenge_url,
    _clean_scalar,
    _get_table,
    _is_initial,
    _is_terminal,
)

REACHABILITY_INITIAL_ERROR = "Initial Challenge without terminal challenge"
REACHABILITY_TERMINAL_ERROR = "Terminal Challenge not reachable from any initial challenge"

WorkbookTables = Mapping[str, pd.DataFrame]


def load_reachability_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
    return {
        "visualizations": pd.read_excel(file_path, sheet_name="visualizations"),
        "challenges": pd.read_excel(file_path, sheet_name="challenges"),
        "waves": pd.read_excel(file_path, sheet_name="waves"),
    }


def _success_next(
    challenge: Mapping[str, Any],
    challenges: Mapping[Any, dict[str, Any]],
) -> dict[str, Any] | None:
    return challenges.get(challenge.get("success_next"))


def _reachable(
    from_challenge: Mapping[str, Any],
    to_challenge: Mapping[str, Any],
    challenges: Mapping[Any, dict[str, Any]],
    visited_ids: set[Any] | None = None,
) -> bool:
    visited_ids = set() if visited_ids is None else set(visited_ids)

    if from_challenge.get("id") == to_challenge.get("id"):
        return True

    from_id = from_challenge.get("id")
    if from_id in visited_ids:
        return False
    visited_ids.add(from_id)

    if _is_terminal(from_challenge):
        return False

    next_challenge = _success_next(from_challenge, challenges)
    if next_challenge is None:
        return False

    return _reachable(next_challenge, to_challenge, challenges, visited_ids)


def _issue_from_native(
    *,
    visualization: Mapping[str, Any],
    challenge: Mapping[str, Any],
    active_wave_ids: set[Any],
    message: str,
) -> Issue:
    wave_id = _clean_scalar(visualization.get("wave"))
    return Issue(
        check=REACHABILITY,
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


def run_native_reachability_tables(
    tables: WorkbookTables,
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

        initials = [challenge for challenge in visualization_challenges if _is_initial(challenge)]
        terminals = [challenge for challenge in visualization_challenges if _is_terminal(challenge)]

        for initial in initials:
            reaches_any_terminal = any(
                _reachable(initial, terminal, challenges)
                for terminal in terminals
            )
            if not reaches_any_terminal:
                issues.append(
                    _issue_from_native(
                        visualization=visualization,
                        challenge=initial,
                        active_wave_ids=active_wave_ids,
                        message=REACHABILITY_INITIAL_ERROR,
                    )
                )

        for terminal in terminals:
            reached_from_any_initial = any(
                _reachable(initial, terminal, challenges)
                for initial in initials
            )
            if not reached_from_any_initial:
                issues.append(
                    _issue_from_native(
                        visualization=visualization,
                        challenge=terminal,
                        active_wave_ids=active_wave_ids,
                        message=REACHABILITY_TERMINAL_ERROR,
                    )
                )

    issues.sort(key=lambda item: (item.active_wave, item.challenge_id), reverse=True)

    return {
        "status": "Failed" if issues else "Passed",
        "issues": issues,
        "notes": [],
    }


def run_native_reachability_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_reachability_tables(file_path)
    return run_native_reachability_tables(tables, now=now)
