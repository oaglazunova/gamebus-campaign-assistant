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
REACHABILITY_LEVEL_ERROR = (
    "Progression level not reachable from any initial challenge"
)

WorkbookTables = Mapping[str, pd.DataFrame]


def load_reachability_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
    return {
        "visualizations": pd.read_excel(file_path, sheet_name="visualizations"),
        "challenges": pd.read_excel(file_path, sheet_name="challenges"),
        "waves": pd.read_excel(file_path, sheet_name="waves"),
    }


def _reachable_ids(
    start_challenges: list[Mapping[str, Any]],
    challenges: Mapping[str, dict[str, Any]],
    *,
    allowed_ids: set[str],
    transition_fields: tuple[str, ...],
) -> set[str]:
    """
    Return challenge ids reachable from the supplied start challenges.

    Only transitions whose targets belong to ``allowed_ids`` are followed.
    This keeps reachability local to the progression visualization currently
    being checked.

    ``transition_fields`` determines which transition types count:
    - ("success_next",) follows the normal success progression only.
    - ("success_next", "failure_next") follows the complete structural graph.
    """
    pending = [
        challenge_id
        for challenge in start_challenges
        if (
            challenge_id := _normalise_id(
                challenge.get("id")
            )
        ) is not None
        and challenge_id in allowed_ids
    ]

    reachable: set[str] = set()

    while pending:
        challenge_id = pending.pop()

        if challenge_id in reachable:
            continue

        challenge = challenges.get(challenge_id)
        if challenge is None:
            continue

        reachable.add(challenge_id)

        for field in transition_fields:
            target_id = _normalise_id(
                challenge.get(field)
            )

            if (
                target_id is not None
                and target_id in allowed_ids
                and target_id not in reachable
            ):
                pending.append(target_id)

    return reachable


def _issue_from_native(
    *,
    visualization: Mapping[str, Any],
    challenge: Mapping[str, Any],
    active_wave_ids: set[str],
    title: str,
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
        title=title,
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

        visualization_challenge_ids = {
            challenge_id
            for challenge in visualization_challenges
            if (
                   challenge_id := _normalise_id(
                       challenge.get("id")
                   )
               ) is not None
        }

        # ---------------------------------------------------------
        # 1. Structural reachability
        #
        # Every configured progression level should be reachable
        # from at least one configured start level through some
        # valid progression route. Both success and failure
        # transitions count here, because fallback / at-risk
        # branches are legitimate parts of the progression graph.
        # ---------------------------------------------------------
        structurally_reachable_ids = _reachable_ids(
            initials,
            challenges,
            allowed_ids=visualization_challenge_ids,
            transition_fields=(
                "success_next",
                "failure_next",
            ),
        )

        for challenge in visualization_challenges:
            challenge_id = _normalise_id(
                challenge.get("id")
            )

            if (
                    challenge_id is None
                    or challenge_id
                    in structurally_reachable_ids
            ):
                continue

            issues.append(
                _issue_from_native(
                    visualization=visualization,
                    challenge=challenge,
                    active_wave_ids=active_wave_ids,
                    title=(
                        "Level cannot be reached from a "
                        "configured start level"
                    ),
                    message=(
                        f"{REACHABILITY_LEVEL_ERROR}. "
                        "This level cannot be reached from any "
                        "configured start level by following "
                        "success or failure transitions within "
                        "this progression. Check whether an "
                        "earlier level should transition to it, "
                        "for example through a failure/recovery "
                        "path, or whether the level is obsolete."
                    ),
                )
            )

        # ---------------------------------------------------------
        # 2. Successful completion
        #
        # Structural reachability is not enough: each configured
        # start level must also have a normal success route to at
        # least one terminal level. Failure transitions deliberately
        # do not count for this part.
        # ---------------------------------------------------------
        terminal_ids = {
            terminal_id
            for terminal in terminals
            if (
                   terminal_id := _normalise_id(
                       terminal.get("id")
                   )
               ) is not None
        }

        for initial in initials:
            success_reachable_ids = _reachable_ids(
                [initial],
                challenges,
                allowed_ids=visualization_challenge_ids,
                transition_fields=("success_next",),
            )

            reaches_any_terminal = bool(
                terminal_ids
                & success_reachable_ids
            )

            if not reaches_any_terminal:
                issues.append(
                    _issue_from_native(
                        visualization=visualization,
                        challenge=initial,
                        active_wave_ids=active_wave_ids,
                        title=(
                            "No terminal level is reachable "
                            "through the success path"
                        ),
                        message=(
                            f"{REACHABILITY_INITIAL_ERROR}. "
                            "Following the normal success "
                            "transitions from this start level "
                            "does not reach any terminal level "
                            "in the same progression. Check the "
                            "success transitions and make sure "
                            "the normal completion path "
                            "eventually reaches an end level."
                        ),
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