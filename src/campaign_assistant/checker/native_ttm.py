from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import Issue, TTMSTRUCTURE


DEFAULT_NO_RELAPSE_LEVELS = 4


def load_ttm_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
    return {
        "visualizations": pd.read_excel(file_path, sheet_name="visualizations"),
        "challenges": pd.read_excel(file_path, sheet_name="challenges"),
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


def _challenge_index(challenges_df: pd.DataFrame) -> dict[Any, dict[str, Any]]:
    index: dict[Any, dict[str, Any]] = {}
    for _, row in challenges_df.iterrows():
        record = row.to_dict()
        index[record["id"]] = record
    return index


def _is_initial(challenge: Mapping[str, Any]) -> bool:
    return challenge.get("is_initial_level") == 1


def _challenge_ref(challenge: Mapping[str, Any] | None) -> str:
    if challenge is None:
        return "missing challenge"
    challenge_id = _clean_scalar(challenge.get("id"))
    challenge_name = _clean_scalar(challenge.get("name")) or "unnamed"
    return f"{challenge_id} ({challenge_name})"


def _same_challenge(left: Mapping[str, Any] | None, right: Mapping[str, Any] | None) -> bool:
    if left is None or right is None:
        return False
    return left.get("id") == right.get("id")


def _get_success(
    challenge: Mapping[str, Any] | None,
    challenges: Mapping[Any, dict[str, Any]],
) -> dict[str, Any] | None:
    if challenge is None:
        return None
    return challenges.get(challenge.get("success_next"))


def _get_failure(
    challenge: Mapping[str, Any] | None,
    challenges: Mapping[Any, dict[str, Any]],
) -> dict[str, Any] | None:
    if challenge is None:
        return None
    return challenges.get(challenge.get("failure_next"))


def _is_terminal(
    challenge: Mapping[str, Any],
    challenges: Mapping[Any, dict[str, Any]],
) -> bool:
    return _same_challenge(_get_success(challenge, challenges), challenge)


def _challenge_url(visualization: Mapping[str, Any], challenge: Mapping[str, Any]) -> str:
    return (
        f"https://campaigns.healthyw8.gamebus.eu/editor/for/"
        f"{visualization.get('campaign')}/{challenge.get('visualizations')}/challenges/{challenge.get('id')}"
    )


def _issue(
    *,
    visualization: Mapping[str, Any],
    challenge: Mapping[str, Any],
    active_wave_ids: set[Any],
    message: str,
) -> Issue:
    wave_id = _clean_scalar(visualization.get("wave"))
    return Issue(
        check=TTMSTRUCTURE,
        severity="medium",
        active_wave=wave_id in active_wave_ids if wave_id is not None else False,
        visualization_id=_clean_scalar(visualization.get("id")),
        visualization=str(_clean_scalar(visualization.get("description")) or ""),
        challenge_id=_clean_scalar(challenge.get("id")),
        challenge=str(_clean_scalar(challenge.get("name")) or ""),
        wave_id=wave_id,
        message=message,
        url=_challenge_url(visualization, challenge),
    )


def _add_issue(
    issues: list[Issue],
    *,
    visualization: Mapping[str, Any],
    challenge: Mapping[str, Any],
    active_wave_ids: set[Any],
    message: str,
) -> None:
    issues.append(
        _issue(
            visualization=visualization,
            challenge=challenge,
            active_wave_ids=active_wave_ids,
            message=message,
        )
    )


def _check_ttm_challenge(
    *,
    visualization: Mapping[str, Any],
    challenge: Mapping[str, Any],
    challenges: Mapping[Any, dict[str, Any]],
    active_wave_ids: set[Any],
    issues: list[Issue],
    no_relapse_levels: int,
    last_level: Mapping[str, Any] | None = None,
    visited_success_ids: set[Any] | None = None,
) -> None:
    """
    Check the HW8 long-term TTM-like progression structure.

    This ports the original GameBusChecker TTM check, but adds defensive handling
    for missing successor references and success-chain cycles.
    """
    visited_success_ids = set() if visited_success_ids is None else set(visited_success_ids)
    challenge_id = challenge.get("id")

    if challenge_id in visited_success_ids:
        _add_issue(
            issues,
            visualization=visualization,
            challenge=challenge,
            active_wave_ids=active_wave_ids,
            message=(
                f"TTM structure check stopped at challenge {_challenge_ref(challenge)} because "
                "the success progression contains a cycle."
            ),
        )
        return

    visited_success_ids.add(challenge_id)

    success_level = _get_success(challenge, challenges)
    failure_level = _get_failure(challenge, challenges)

    if no_relapse_levels > 0:
        if not _same_challenge(failure_level, challenge):
            _add_issue(
                issues,
                visualization=visualization,
                challenge=challenge,
                active_wave_ids=active_wave_ids,
                message=(
                    f"Challenge {_challenge_ref(challenge)} is in the first "
                    f"{DEFAULT_NO_RELAPSE_LEVELS} non-relapse TTM progression levels. "
                    f"Its failure transition should point to itself, but it points to "
                    f"{_challenge_ref(failure_level)}."
                ),
            )
            return

        if success_level is None:
            _add_issue(
                issues,
                visualization=visualization,
                challenge=challenge,
                active_wave_ids=active_wave_ids,
                message=(
                    f"Challenge {_challenge_ref(challenge)} is in the first "
                    f"{DEFAULT_NO_RELAPSE_LEVELS} non-relapse TTM progression levels, "
                    "but its success transition does not point to an existing challenge."
                ),
            )
            return

        if _same_challenge(success_level, challenge):
            return

        _check_ttm_challenge(
            visualization=visualization,
            challenge=success_level,
            challenges=challenges,
            active_wave_ids=active_wave_ids,
            issues=issues,
            no_relapse_levels=no_relapse_levels - 1,
            last_level=challenge,
            visited_success_ids=visited_success_ids,
        )
        return

    if last_level is None:
        _add_issue(
            issues,
            visualization=visualization,
            challenge=challenge,
            active_wave_ids=active_wave_ids,
            message=(
                f"Challenge {_challenge_ref(challenge)} is checked as a relapse-aware TTM level, "
                "but the previous level in the success hierarchy is unknown."
            ),
        )
        return

    if success_level is None:
        _add_issue(
            issues,
            visualization=visualization,
            challenge=challenge,
            active_wave_ids=active_wave_ids,
            message=(
                f"Challenge {_challenge_ref(challenge)} is checked as a relapse-aware TTM level, "
                "but its success transition does not point to an existing challenge."
            ),
        )
        return

    if _is_terminal(challenge, challenges):
        if not _same_challenge(failure_level, last_level):
            _add_issue(
                issues,
                visualization=visualization,
                challenge=challenge,
                active_wave_ids=active_wave_ids,
                message=(
                    f"Terminal TTM challenge {_challenge_ref(challenge)} should have failure transition "
                    f"to the previous level {_challenge_ref(last_level)}, but it points to "
                    f"{_challenge_ref(failure_level)}."
                ),
            )
        return

    at_risk_level = failure_level
    if at_risk_level is None:
        _add_issue(
            issues,
            visualization=visualization,
            challenge=challenge,
            active_wave_ids=active_wave_ids,
            message=(
                f"Relapse-aware TTM challenge {_challenge_ref(challenge)} should have a failure transition "
                "to an at-risk level, but the failure transition does not point to an existing challenge."
            ),
        )
        return

    at_risk_failure = _get_failure(at_risk_level, challenges)
    at_risk_success = _get_success(at_risk_level, challenges)

    if _same_challenge(at_risk_level, last_level):
        _add_issue(
            issues,
            visualization=visualization,
            challenge=challenge,
            active_wave_ids=active_wave_ids,
            message=(
                f"Challenge {_challenge_ref(challenge)} uses {_challenge_ref(at_risk_level)} as its at-risk level, "
                f"but that is also the previous level {_challenge_ref(last_level)} in the TTM hierarchy. "
                "The at-risk level should be a separate relapse-risk challenge."
            ),
        )

    if not _same_challenge(at_risk_failure, last_level):
        _add_issue(
            issues,
            visualization=visualization,
            challenge=challenge,
            active_wave_ids=active_wave_ids,
            message=(
                f"Challenge {_challenge_ref(challenge)} has at-risk level {_challenge_ref(at_risk_level)}. "
                f"That at-risk level should fail back to the previous level {_challenge_ref(last_level)}, "
                f"but it fails to {_challenge_ref(at_risk_failure)}."
            ),
        )

    if not _same_challenge(at_risk_success, challenge):
        _add_issue(
            issues,
            visualization=visualization,
            challenge=challenge,
            active_wave_ids=active_wave_ids,
            message=(
                f"Challenge {_challenge_ref(challenge)} has at-risk level {_challenge_ref(at_risk_level)}. "
                f"That at-risk level should succeed back to {_challenge_ref(challenge)}, "
                f"but it succeeds to {_challenge_ref(at_risk_success)}."
            ),
        )

    _check_ttm_challenge(
        visualization=visualization,
        challenge=success_level,
        challenges=challenges,
        active_wave_ids=active_wave_ids,
        issues=issues,
        no_relapse_levels=0,
        last_level=challenge,
        visited_success_ids=visited_success_ids,
    )


def run_native_ttm_tables(
    tables: Mapping[str, pd.DataFrame],
    now: pd.Timestamp | None = None,
    no_relapse_levels: int = DEFAULT_NO_RELAPSE_LEVELS,
) -> dict[str, Any]:
    if no_relapse_levels <= 0:
        raise ValueError("no_relapse_levels must be greater than 0")

    visualizations_df = tables["visualizations"]
    challenges_df = tables["challenges"]
    waves_df = tables.get("waves", pd.DataFrame())

    challenges = _challenge_index(challenges_df)
    active_wave_ids = _active_wave_ids(waves_df, now=now)

    issues: list[Issue] = []

    for _, vis_row in visualizations_df.iterrows():
        visualization = vis_row.to_dict()
        visualization_id = visualization.get("id")
        visualization_challenges = [
            challenge
            for challenge in challenges.values()
            if challenge.get("visualizations") == visualization_id
        ]
        initial_challenges = [challenge for challenge in visualization_challenges if _is_initial(challenge)]

        for initial_challenge in initial_challenges:
            _check_ttm_challenge(
                visualization=visualization,
                challenge=initial_challenge,
                challenges=challenges,
                active_wave_ids=active_wave_ids,
                issues=issues,
                no_relapse_levels=no_relapse_levels,
            )

    issues.sort(key=lambda item: (item.active_wave, item.challenge_id), reverse=True)

    return {
        "status": "Failed" if issues else "Passed",
        "issues": issues,
        "notes": [],
    }


def run_native_ttm_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
    no_relapse_levels: int = DEFAULT_NO_RELAPSE_LEVELS,
) -> dict[str, Any]:
    tables = load_ttm_tables(file_path)
    return run_native_ttm_tables(tables, now=now, no_relapse_levels=no_relapse_levels)