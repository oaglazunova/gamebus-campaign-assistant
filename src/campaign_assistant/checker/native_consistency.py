from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import CONSISTENCY, Issue


def load_consistency_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
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


def _is_terminal(challenge: Mapping[str, Any], challenges: Mapping[Any, dict[str, Any]]) -> bool:
    success_next = challenge.get("success_next")
    next_challenge = challenges.get(success_next)
    if next_challenge is None:
        return False
    return next_challenge.get("id") == challenge.get("id")


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
    visualizations_df = tables["visualizations"]
    challenges_df = tables["challenges"]
    waves_df = tables.get("waves", pd.DataFrame())

    challenges = _challenge_index(challenges_df)
    active_wave_ids = _active_wave_ids(waves_df, now=now)

    issues: list[Issue] = []

    for _, vis_row in visualizations_df.iterrows():
        vis = vis_row.to_dict()
        vis_id = vis["id"]

        vis_challenges = [
            c for c in challenges.values()
            if c.get("visualizations") == vis_id
        ]

        for challenge in vis_challenges:
            cid = challenge.get("id")

            if _is_initial(challenge):
                failure_next = challenge.get("failure_next")
                if failure_next != cid:
                    issues.append(
                        _issue(
                            visualization=vis,
                            challenge=challenge,
                            active_wave_ids=active_wave_ids,
                            message=f"Initial challenge does not lead to itself on failure {failure_next}",
                        )
                    )

            if _is_terminal(challenge, challenges):
                success_next = challenge.get("success_next")
                if success_next != cid:
                    issues.append(
                        _issue(
                            visualization=vis,
                            challenge=challenge,
                            active_wave_ids=active_wave_ids,
                            message=f"Terminal challenge does not lead to itself on success {success_next}",
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