from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import Issue, VISUALIZATIONINTERN
from campaign_assistant.checker.table_utils import (
    VisualizationFlowKind,
    _active_wave_ids,
    _challenge_belongs_to_visualization,
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
    _reference_ids,
    _visualization_index,
)


def load_visualizationintern_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
    return {
        "visualizations": pd.read_excel(file_path, sheet_name="visualizations"),
        "challenges": pd.read_excel(file_path, sheet_name="challenges"),
        "waves": pd.read_excel(file_path, sheet_name="waves"),
    }


def _challenge_ref(challenge: Mapping[str, Any]) -> str:
    challenge_id = _normalise_id(challenge.get("id"))
    challenge_name = _clean_scalar(challenge.get("name")) or "unnamed"

    return f"{challenge_id} ({challenge_name})"


def _visualization_ref(
    visualization_ids: Any,
    visualizations: Mapping[str, dict[str, Any]],
) -> str:
    refs: list[str] = []

    for visualization_id in _reference_ids(visualization_ids):
        visualization = visualizations.get(visualization_id)

        if visualization is None:
            refs.append(str(visualization_id))
            continue

        description = _clean_scalar(visualization.get("description")) or "unnamed"
        refs.append(f"{visualization_id} ({description})")

    return ", ".join(refs) if refs else "missing visualization"


def _get_success(
    challenge: Mapping[str, Any],
    challenges: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    return challenges.get(_normalise_id(challenge.get("success_next")) or "")


def _get_failure(
    challenge: Mapping[str, Any],
    challenges: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    return challenges.get(_normalise_id(challenge.get("failure_next")) or "")


def _is_missing_label(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def _labels_equal(left: Any, right: Any) -> bool:
    left_missing = _is_missing_label(left)
    right_missing = _is_missing_label(right)

    if left_missing and right_missing:
        return True

    if left_missing or right_missing:
        return False

    return left == right


def _reachable_terminal_challenges(
    challenge: Mapping[str, Any],
    challenges: Mapping[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    terminals: dict[str, dict[str, Any]] = {}
    visited_ids: set[str] = set()

    start_id = _normalise_id(challenge.get("id"))
    if start_id is None:
        return []

    stack: list[dict[str, Any]] = [dict(challenge)]

    while stack:
        current = stack.pop()
        current_id = _normalise_id(current.get("id"))

        if current_id is None or current_id in visited_ids:
            continue

        visited_ids.add(current_id)

        if _is_terminal(current, challenges):
            terminals[current_id] = dict(current)
            continue

        for next_challenge in (
            _get_success(current, challenges),
            _get_failure(current, challenges),
        ):
            next_id = _normalise_id(next_challenge.get("id")) if next_challenge else None

            if next_challenge is not None and next_id not in visited_ids:
                stack.append(next_challenge)

    return list(terminals.values())


def _issue(
    *,
    visualization: Mapping[str, Any],
    reachable_challenge: Mapping[str, Any],
    active_wave_ids: set[str],
    initial_challenge: Mapping[str, Any],
    visualizations: Mapping[str, dict[str, Any]],
) -> Issue:
    wave_id = _normalise_id(visualization.get("wave"))

    description = (
        "Reachable challenge from an initial level is not in the same visualization "
        "or does not have the same label:\n"
        f"Initial challenge = {_challenge_ref(initial_challenge)}; "
        f"reachable challenge = {_challenge_ref(reachable_challenge)}\n"
        f"Initial challenge visualization(s) = "
        f"'{_visualization_ref(initial_challenge.get('visualizations'), visualizations)}'; "
        f"reachable challenge visualization(s) = "
        f"'{_visualization_ref(reachable_challenge.get('visualizations'), visualizations)}'\n"
        f"Initial challenge labels = '{initial_challenge.get('labels')}'; "
        f"reachable challenge labels = '{reachable_challenge.get('labels')}'\n"
    )

    return Issue(
        check=VISUALIZATIONINTERN,
        severity="medium",
        active_wave=wave_id in active_wave_ids if wave_id is not None else False,
        visualization_id=_normalise_id(visualization.get("id")),
        visualization=str(_clean_scalar(visualization.get("description")) or ""),
        challenge_id=_normalise_id(reachable_challenge.get("id")),
        challenge=str(_clean_scalar(reachable_challenge.get("name")) or ""),
        wave_id=wave_id,
        message=description,
        url=_challenge_url(visualization, reachable_challenge),
    )


def run_native_visualizationintern_tables(
    tables: Mapping[str, pd.DataFrame],
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    visualizations_df = _get_table(tables, "visualizations")
    challenges_df = _get_table(tables, "challenges")
    waves_df = tables.get("waves", pd.DataFrame())

    challenges = _challenge_index(challenges_df)
    visualizations = _visualization_index(visualizations_df)
    active_wave_ids = _active_wave_ids(waves_df, now=now)

    issues: list[Issue] = []
    notes: list[str] = []
    seen_pairs: set[tuple[str | None, str | None, str | None]] = set()
    memberships_evaluated = 0

    for _, vis_row in visualizations_df.iterrows():
        visualization = vis_row.to_dict()
        vis_id = _normalise_id(visualization.get("id"))

        if vis_id is None:
            continue

        vis_challenges = _challenges_for_visualization(challenges, vis_id)
        memberships_evaluated += len(vis_challenges)

        flow_kind = _classify_visualization_flow(
            visualization,
            vis_challenges,
            challenges,
        )

        # This check is meaningful for level-progressions. Cyclic/support
        # visualizations such as Tips/Info/Support should not be forced into
        # progression-terminal assumptions.
        if flow_kind != VisualizationFlowKind.PROGRESSION:
            continue

        initial_challenges = [
            challenge
            for challenge in vis_challenges
            if _is_initial(challenge)
        ]

        for initial in initial_challenges:
            reachable_terminals = _reachable_terminal_challenges(initial, challenges)

            for reachable in reachable_terminals:
                same_visualization = _challenge_belongs_to_visualization(
                    reachable,
                    vis_id,
                )
                same_label = _labels_equal(
                    initial.get("labels"),
                    reachable.get("labels"),
                )

                if same_visualization and same_label:
                    continue

                key = (
                    vis_id,
                    _normalise_id(initial.get("id")),
                    _normalise_id(reachable.get("id")),
                )

                if key in seen_pairs:
                    continue

                seen_pairs.add(key)

                issues.append(
                    _issue(
                        visualization=visualization,
                        reachable_challenge=reachable,
                        active_wave_ids=active_wave_ids,
                        initial_challenge=initial,
                        visualizations=visualizations,
                    )
                )

    coverage_problem = _coverage_note(
        check_name="Visualization internals",
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


def run_native_visualizationintern_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_visualizationintern_tables(file_path)
    return run_native_visualizationintern_tables(tables, now=now)