from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import Issue, VISUALIZATIONINTERN


def load_visualizationintern_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
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


def _get_success(challenge: Mapping[str, Any], challenges: Mapping[Any, dict[str, Any]]) -> dict[str, Any] | None:
    return challenges.get(challenge.get("success_next"))


def _get_failure(challenge: Mapping[str, Any], challenges: Mapping[Any, dict[str, Any]]) -> dict[str, Any] | None:
    return challenges.get(challenge.get("failure_next"))


def _is_terminal(challenge: Mapping[str, Any], challenges: Mapping[Any, dict[str, Any]]) -> bool:
    next_challenge = _get_success(challenge, challenges)
    if next_challenge is None:
        return False
    return next_challenge.get("id") == challenge.get("id")


def _labels_equal(left: Any, right: Any) -> bool:
    left_missing = pd.isna(left)
    right_missing = pd.isna(right)
    if left_missing and right_missing:
        return True
    if left_missing or right_missing:
        return False
    return left == right


def _reachable_terminal_challenges(
    challenge: Mapping[str, Any],
    challenges: Mapping[Any, dict[str, Any]],
    visited_ids: set[Any] | None = None,
) -> list[dict[str, Any]]:
    visited_ids = set() if visited_ids is None else set(visited_ids)
    challenge_id = challenge.get("id")

    if challenge_id in visited_ids:
        return []

    visited_ids.add(challenge_id)

    if _is_terminal(challenge, challenges):
        return [dict(challenge)]

    result: list[dict[str, Any]] = []
    next_candidates = [
        _get_success(challenge, challenges),
        _get_failure(challenge, challenges),
    ]

    for next_challenge in next_candidates:
        if next_challenge is None:
            continue
        next_id = next_challenge.get("id")
        if next_id in visited_ids:
            continue
        result.extend(
            _reachable_terminal_challenges(
                next_challenge,
                challenges,
                visited_ids=visited_ids,
            )
        )

    return result


def _challenge_url(visualization: Mapping[str, Any], challenge: Mapping[str, Any]) -> str:
    return (
        f"https://campaigns.healthyw8.gamebus.eu/editor/for/"
        f"{visualization.get('campaign')}/{challenge.get('visualizations')}/challenges/{challenge.get('id')}"
    )


def _issue(
    *,
    visualization: Mapping[str, Any],
    reachable_challenge: Mapping[str, Any],
    active_wave_ids: set[Any],
    initial_challenge: Mapping[str, Any],
) -> Issue:
    wave_id = _clean_scalar(visualization.get("wave"))
    description = (
        "Reachable Challenge from some initial level is not in same visualization or not with same label:\n"
        f"Initial challenge visualization = '{initial_challenge.get('visualizations')}'; "
        f"reachable challenge visualization = '{reachable_challenge.get('visualizations')}'\n"
        f"Initial challenge labels = '{initial_challenge.get('labels')}'; "
        f"reachable challenge labels = '{reachable_challenge.get('labels')}'\n"
    )
    return Issue(
        check=VISUALIZATIONINTERN,
        severity="high",
        active_wave=wave_id in active_wave_ids if wave_id is not None else False,
        visualization_id=_clean_scalar(visualization.get("id")),
        visualization=str(_clean_scalar(visualization.get("description")) or ""),
        challenge_id=_clean_scalar(reachable_challenge.get("id")),
        challenge=str(_clean_scalar(reachable_challenge.get("name")) or ""),
        wave_id=wave_id,
        message=description,
        url=_challenge_url(visualization, reachable_challenge),
    )


def run_native_visualizationintern_tables(
    tables: Mapping[str, pd.DataFrame],
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    visualizations_df = tables["visualizations"]
    challenges_df = tables["challenges"]
    waves_df = tables.get("waves", pd.DataFrame())

    challenges = _challenge_index(challenges_df)
    active_wave_ids = _active_wave_ids(waves_df, now=now)

    issues: list[Issue] = []
    seen_pairs: set[tuple[Any, Any]] = set()

    for _, vis_row in visualizations_df.iterrows():
        vis = vis_row.to_dict()
        vis_id = vis["id"]

        vis_challenges = [
            c for c in challenges.values()
            if c.get("visualizations") == vis_id
        ]
        initial_challenges = [c for c in vis_challenges if _is_initial(c)]

        for initial in initial_challenges:
            reachable_terminals = _reachable_terminal_challenges(initial, challenges)

            for reachable in reachable_terminals:
                same_visualization = initial.get("visualizations") == reachable.get("visualizations")
                same_label = _labels_equal(initial.get("labels"), reachable.get("labels"))

                if same_visualization and same_label:
                    continue

                key = (initial.get("id"), reachable.get("id"))
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)

                issues.append(
                    _issue(
                        visualization=vis,
                        reachable_challenge=reachable,
                        active_wave_ids=active_wave_ids,
                        initial_challenge=initial,
                    )
                )

    issues.sort(key=lambda item: (item.active_wave, item.challenge_id), reverse=True)

    return {
        "status": "Failed" if issues else "Passed",
        "issues": issues,
        "notes": [],
    }


def run_native_visualizationintern_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_visualizationintern_tables(file_path)
    return run_native_visualizationintern_tables(tables, now=now)