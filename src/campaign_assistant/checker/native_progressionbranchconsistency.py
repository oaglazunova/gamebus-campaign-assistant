from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import (
    Issue,
    PROGRESSIONBRANCHCONSISTENCY,
)
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
    _normalise_id,
    _same_id,
)


WorkbookTables = Mapping[str, pd.DataFrame]


def _numeric_target(value: Any) -> float | None:
    value = _clean_scalar(value)
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if pd.isna(number):
        return None

    return number


def _challenge_ref(challenge: Mapping[str, Any]) -> str:
    challenge_id = _normalise_id(challenge.get("id")) or "?"
    challenge_name = str(
        _clean_scalar(challenge.get("name")) or "unnamed"
    )

    return f"#{challenge_id} {challenge_name}"


def _format_target(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:g}"


def _issue(
    *,
    visualization: Mapping[str, Any],
    candidate: Mapping[str, Any],
    previous: Mapping[str, Any],
    next_level: Mapping[str, Any],
    candidate_target: float,
    previous_target: float,
    next_target: float,
    active_wave_ids: set[str],
) -> Issue:
    wave_id = _normalise_id(visualization.get("wave"))

    message = (
        f"{_challenge_ref(candidate)} looks like a lower-target "
        "recovery/fallback level: "
        f"its target is {_format_target(candidate_target)}, compared with "
        f"{_format_target(previous_target)} for "
        f"{_challenge_ref(previous)} and "
        f"{_format_target(next_target)} for "
        f"{_challenge_ref(next_level)}. "
        f"It succeeds to {_challenge_ref(next_level)}, fails back to "
        f"{_challenge_ref(previous)}, and "
        f"{_challenge_ref(next_level)} fails back to it. "
        f"However, successful completion of {_challenge_ref(previous)} "
        "also leads directly to this level, which places the fallback "
        "level on the normal success path. "
        "Check whether the previous level should instead succeed "
        "directly to the next normal level."
    )

    return Issue(
        check=PROGRESSIONBRANCHCONSISTENCY,
        severity="medium",
        active_wave=(
            wave_id in active_wave_ids
            if wave_id is not None
            else False
        ),
        visualization_id=_normalise_id(
            visualization.get("id")
        ),
        visualization=str(
            _clean_scalar(visualization.get("description")) or ""
        ),
        challenge_id=_normalise_id(candidate.get("id")),
        challenge=str(
            _clean_scalar(candidate.get("name")) or ""
        ),
        wave_id=wave_id,
        title=(
            "Possible recovery level is on the normal success path"
        ),
        message=message,
        url=_challenge_url(visualization, candidate),
    )


def run_native_progressionbranchconsistency_tables(
    tables: WorkbookTables,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    visualizations_df = _get_table(
        tables,
        "visualizations",
    )
    challenges_df = _get_table(
        tables,
        "challenges",
    )
    waves_df = tables.get(
        "waves",
        pd.DataFrame(),
    )

    challenges = _challenge_index(challenges_df)
    active_wave_ids = _active_wave_ids(
        waves_df,
        now=now,
    )

    issues: list[Issue] = []
    notes: list[str] = []
    memberships_evaluated = 0

    for _, vis_row in visualizations_df.iterrows():
        visualization = vis_row.to_dict()
        visualization_id = _normalise_id(
            visualization.get("id")
        )

        if visualization_id is None:
            continue

        visualization_challenges = (
            _challenges_for_visualization(
                challenges,
                visualization_id,
            )
        )
        memberships_evaluated += len(
            visualization_challenges
        )

        flow_kind = _classify_visualization_flow(
            visualization,
            visualization_challenges,
            challenges,
        )

        if flow_kind != VisualizationFlowKind.PROGRESSION:
            continue

        for candidate in visualization_challenges:
            candidate_id = _normalise_id(
                candidate.get("id")
            )
            previous_id = _normalise_id(
                candidate.get("failure_next")
            )
            next_id = _normalise_id(
                candidate.get("success_next")
            )

            if (
                candidate_id is None
                or previous_id is None
                or next_id is None
                or candidate_id in {
                    previous_id,
                    next_id,
                }
                or previous_id == next_id
            ):
                continue

            previous = challenges.get(previous_id)
            next_level = challenges.get(next_id)

            if previous is None or next_level is None:
                continue

            # Keep this check local to one progression
            # visualization. Cross-visualization transitions
            # are handled by the existing visualization check.
            if not (
                _challenge_belongs_to_visualization(
                    previous,
                    visualization_id,
                )
                and _challenge_belongs_to_visualization(
                    next_level,
                    visualization_id,
                )
            ):
                continue

            # Recovery/fallback topology:
            #
            # previous <-failure- candidate -success-> next
            #                         ^                 |
            #                         |------failure----|
            #
            # In other words, failure from the next level
            # returns to the candidate.
            if not _same_id(
                next_level.get("failure_next"),
                candidate_id,
            ):
                continue

            # Suspicious part:
            #
            # previous -success-> candidate
            #
            # This means that the same candidate used as a
            # fallback from the next level is also directly
            # on the normal success path.
            if not _same_id(
                previous.get("success_next"),
                candidate_id,
            ):
                continue

            candidate_target = _numeric_target(
                candidate.get("target")
            )
            previous_target = _numeric_target(
                previous.get("target")
            )
            next_target = _numeric_target(
                next_level.get("target")
            )

            # The lower target is a language-independent
            # signal that this is likely a recovery/fallback
            # level rather than an ordinary reversible
            # progression level.
            if None in {
                candidate_target,
                previous_target,
                next_target,
            }:
                continue

            assert candidate_target is not None
            assert previous_target is not None
            assert next_target is not None

            if not (
                candidate_target < previous_target
                and candidate_target < next_target
            ):
                continue

            issues.append(
                _issue(
                    visualization=visualization,
                    candidate=candidate,
                    previous=previous,
                    next_level=next_level,
                    candidate_target=candidate_target,
                    previous_target=previous_target,
                    next_target=next_target,
                    active_wave_ids=active_wave_ids,
                )
            )

    coverage_problem = _coverage_note(
        check_name="Progression branch consistency",
        memberships=memberships_evaluated,
        challenge_count=len(challenges_df),
        visualization_count=len(visualizations_df),
    )

    if coverage_problem:
        notes.append(coverage_problem)

    issues.sort(
        key=lambda item: (
            item.active_wave,
            item.challenge_id,
        ),
        reverse=True,
    )

    return {
        "status": (
            "Error"
            if coverage_problem
            else "Failed"
            if issues
            else "Passed"
        ),
        "issues": issues,
        "notes": notes,
    }


def load_progressionbranchconsistency_tables(
    file_path: str | Path,
) -> dict[str, pd.DataFrame]:
    return {
        "visualizations": pd.read_excel(
            file_path,
            sheet_name="visualizations",
        ),
        "challenges": pd.read_excel(
            file_path,
            sheet_name="challenges",
        ),
        "waves": pd.read_excel(
            file_path,
            sheet_name="waves",
        ),
    }


def run_native_progressionbranchconsistency_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_progressionbranchconsistency_tables(
        file_path
    )

    return run_native_progressionbranchconsistency_tables(
        tables,
        now=now,
    )