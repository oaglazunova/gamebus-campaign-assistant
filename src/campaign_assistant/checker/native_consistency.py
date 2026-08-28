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

from campaign_assistant.checker.schema import CONSISTENCY, Issue
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
    _normalise_id,
    _same_id,
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
    active_wave_ids: set[str],
    message: str,
) -> Issue:
    wave_id = _normalise_id(visualization.get("wave"))

    return Issue(
        check=CONSISTENCY,
        severity="high",
        active_wave=wave_id in active_wave_ids if wave_id is not None else False,
        visualization_id=_normalise_id(visualization.get("id")),
        visualization=str(_clean_scalar(visualization.get("description")) or ""),
        challenge_id=_normalise_id(challenge.get("id")),
        challenge=str(_clean_scalar(challenge.get("name")) or ""),
        wave_id=wave_id,
        title="Start level does not return to itself after failure",
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

        # Consistency currently checks initial/start-level failure behavior.
        # Cyclic/support and non-progression visualizations should not be
        # forced to follow level-progression rules.
        if flow_kind != VisualizationFlowKind.PROGRESSION:
            continue

        for challenge in visualization_challenges:
            if not _is_initial(challenge):
                continue

            challenge_id = _normalise_id(challenge.get("id"))
            failure_next = _normalise_id(challenge.get("failure_next"))

            if _same_id(failure_next, challenge_id):
                continue

            issues.append(
                _issue(
                    visualization=visualization,
                    challenge=challenge,
                    active_wave_ids=active_wave_ids,
                    title="Start level does not return to itself after failure",
                    message=(
                        "Initial challenge does not lead to itself on failure "
                        f"{failure_next}"
                    ),
                )
            )

    coverage_problem = _coverage_note(
        check_name="Consistency",
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


def run_native_consistency_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_consistency_tables(file_path)
    return run_native_consistency_tables(tables, now=now)