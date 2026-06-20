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

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import Issue, REACHABILITY
from campaign_assistant.checker.table_utils import (
    VisualizationFlowKind,
    _active_wave_ids,
    _challenge_index,
    _challenge_url,
    _challenges_for_visualization,
    _classify_visualization_flow,
    _clean_scalar,
    _coverage_note,
    _get_table,
    _is_initial,
    _is_terminal,
    _normalise_id,
    _same_id,
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
    challenges: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    return challenges.get(_normalise_id(challenge.get("success_next")) or "")


def _reachable(
    from_challenge: Mapping[str, Any],
    to_challenge: Mapping[str, Any],
    challenges: Mapping[str, dict[str, Any]],
    visited_ids: set[str] | None = None,
) -> bool:
    visited_ids = set() if visited_ids is None else set(visited_ids)

    if _same_id(from_challenge.get("id"), to_challenge.get("id")):
        return True

    from_id = _normalise_id(from_challenge.get("id"))
    if from_id is None:
        return False

    if from_id in visited_ids:
        return False
    visited_ids.add(from_id)

    if _is_terminal(from_challenge, challenges):
        return False

    next_challenge = _success_next(from_challenge, challenges)
    if next_challenge is None:
        return False

    return _reachable(next_challenge, to_challenge, challenges, visited_ids)


def _issue_from_native(
    *,
    visualization: Mapping[str, Any],
    challenge: Mapping[str, Any],
    active_wave_ids: set[str],
    message: str,
) -> Issue:
    wave_id = _normalise_id(visualization.get("wave"))

    return Issue(
        check=REACHABILITY,
        severity="high",
        active_wave=wave_id in active_wave_ids if wave_id is not None else False,
        visualization_id=_normalise_id(visualization.get("id")),
        visualization=str(_clean_scalar(visualization.get("description")) or ""),
        challenge_id=_normalise_id(challenge.get("id")),
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
    notes: list[str] = []
    memberships_evaluated = 0

    for _, vis_row in visualizations_df.iterrows():
        visualization = vis_row.to_dict()
        visualization_id = _normalise_id(visualization.get("id"))
        if visualization_id is None:
            continue

        visualization_challenges = _challenges_for_visualization(
            challenges,
            visualization_id,
        )
        memberships_evaluated += len(visualization_challenges)

        flow_kind = _classify_visualization_flow(
            visualization,
            visualization_challenges,
            challenges,
        )

        if flow_kind == VisualizationFlowKind.CYCLIC_SUPPORT:
            notes.append(
                "Reachability treated visualization "
                f"{visualization_id} "
                f"({_clean_scalar(visualization.get('description')) or 'unnamed'}) "
                "as cyclic/support content: no terminal challenge is expected."
            )
            continue

        if flow_kind == VisualizationFlowKind.NON_PROGRESSION:
            continue

        initials = [
            challenge
            for challenge in visualization_challenges
            if _is_initial(challenge)
        ]
        terminals = [
            challenge
            for challenge in visualization_challenges
            if _is_terminal(challenge, challenges)
        ]

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

    coverage_problem = _coverage_note(
        check_name="Reachability",
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


def run_native_reachability_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_reachability_tables(file_path)
    return run_native_reachability_tables(tables, now=now)