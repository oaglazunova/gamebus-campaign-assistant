from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import Issue, TTMSTRUCTURE


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


def _visualization_index(visualizations_df: pd.DataFrame) -> dict[Any, dict[str, Any]]:
    index: dict[Any, dict[str, Any]] = {}
    for _, row in visualizations_df.iterrows():
        record = row.to_dict()
        index[record["id"]] = record
    return index


def _challenge_equal(c1: Mapping[str, Any] | None, c2: Mapping[str, Any] | None) -> bool:
    if c1 is None or c2 is None:
        return False
    return c1.get("id") == c2.get("id")


def _is_initial(challenge: Mapping[str, Any]) -> bool:
    return challenge.get("is_initial_level") == 1


def _success(challenge: Mapping[str, Any], challenges: Mapping[Any, dict[str, Any]]) -> dict[str, Any] | None:
    return challenges.get(challenge.get("success_next"))


def _failure(challenge: Mapping[str, Any], challenges: Mapping[Any, dict[str, Any]]) -> dict[str, Any] | None:
    return challenges.get(challenge.get("failure_next"))


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


def _visualization_initial_challenges(
    visualization: Mapping[str, Any],
    challenges: Mapping[Any, dict[str, Any]],
) -> list[dict[str, Any]]:
    vis_id = visualization.get("id")
    return [
        c for c in challenges.values()
        if c.get("visualizations") == vis_id and _is_initial(c)
    ]


def _check_challenge_ttm(
    *,
    visualization: Mapping[str, Any],
    challenge: Mapping[str, Any],
    challenges: Mapping[Any, dict[str, Any]],
    active_wave_ids: set[Any],
    issues: list[Issue],
    norelapselevels: int = 0,
    lastlevel: Mapping[str, Any] | None = None,
) -> None:
    nextlevel = _success(challenge, challenges)

    if norelapselevels > 0:
        # Normal level: failure must point to itself.
        if not _challenge_equal(_failure(challenge, challenges), challenge):
            issues.append(
                _issue(
                    visualization=visualization,
                    challenge=challenge,
                    active_wave_ids=active_wave_ids,
                    message=(
                        f"Challenge {challenge['id']} ({challenge['name']}) "
                        f"should have failure success level to itself."
                    ),
                )
            )
        elif not _challenge_equal(nextlevel, challenge):
            _check_challenge_ttm(
                visualization=visualization,
                challenge=nextlevel,
                challenges=challenges,
                active_wave_ids=active_wave_ids,
                issues=issues,
                norelapselevels=norelapselevels - 1,
                lastlevel=challenge,
            )
        else:
            return

    elif _challenge_equal(nextlevel, challenge):
        # Final level: failure must go to the previous level.
        if lastlevel is None:
            return

        if not _challenge_equal(_failure(challenge, challenges), lastlevel):
            issues.append(
                _issue(
                    visualization=visualization,
                    challenge=challenge,
                    active_wave_ids=active_wave_ids,
                    message=(
                        f"Challenge {challenge['id']} ({challenge['name']}) should have failure to previous level "
                        f"{lastlevel['id']} ({lastlevel['name']}) that led to {challenge['id']} ({challenge['name']}) "
                        f"as successor level."
                    ),
                )
            )
    else:
        # Relapse pattern.
        if lastlevel is None:
            return

        relapselevel = _failure(challenge, challenges)
        if relapselevel is None:
            issues.append(
                _issue(
                    visualization=visualization,
                    challenge=challenge,
                    active_wave_ids=active_wave_ids,
                    message=(
                        f"Challenge {challenge['id']} ({challenge['name']}): "
                        "its 'At risk level' is missing."
                    ),
                )
            )
            return

        relapselevelfailure = _failure(relapselevel, challenges)
        relapselevelsuccess = _success(relapselevel, challenges)

        if _challenge_equal(relapselevel, lastlevel):
            issues.append(
                _issue(
                    visualization=visualization,
                    challenge=challenge,
                    active_wave_ids=active_wave_ids,
                    message=(
                        f"Challenge {challenge['id']} ({challenge['name']}): its 'At risk level' "
                        f"{relapselevel['id']} ({relapselevel['name']}) should not be the previous level "
                        f"{lastlevel['id']} ({lastlevel['name']}) in TTM hierarchy. "
                        "Maybe the error is also from that successor challenge being wrong."
                    ),
                )
            )

        if not _challenge_equal(relapselevelfailure, lastlevel):
            issues.append(
                _issue(
                    visualization=visualization,
                    challenge=challenge,
                    active_wave_ids=active_wave_ids,
                    message=(
                        f"Challenge {challenge['id']} ({challenge['name']}): its 'At risk level' "
                        f"{relapselevel['id']} ({relapselevel['name']}) should have as failure challenge the previous "
                        f"level {lastlevel['id']} ({lastlevel['name']}) in the TTM hierarchy that led to "
                        f"{challenge['id']} ({challenge['name']})."
                    ),
                )
            )

        if not _challenge_equal(relapselevelsuccess, challenge):
            issues.append(
                _issue(
                    visualization=visualization,
                    challenge=challenge,
                    active_wave_ids=active_wave_ids,
                    message=(
                        f"Challenge {challenge['id']} ({challenge['name']}): its 'At risk level' "
                        f"{relapselevel['id']} ({relapselevel['name']}) should have as success challenge the challenge "
                        f"{challenge['id']} ({challenge['name']})  again."
                    ),
                )
            )

        if nextlevel is not None:
            _check_challenge_ttm(
                visualization=visualization,
                challenge=nextlevel,
                challenges=challenges,
                active_wave_ids=active_wave_ids,
                issues=issues,
                norelapselevels=0,
                lastlevel=challenge,
            )


def run_native_ttm_tables(
    tables: Mapping[str, pd.DataFrame],
    now: pd.Timestamp | None = None,
    norelapselevels: int = 4,
) -> dict[str, Any]:
    if norelapselevels <= 0:
        raise ValueError("norelapselevels must be > 0")

    visualizations_df = tables["visualizations"]
    challenges_df = tables["challenges"]
    waves_df = tables.get("waves", pd.DataFrame())

    visualizations = _visualization_index(visualizations_df)
    challenges = _challenge_index(challenges_df)
    active_wave_ids = _active_wave_ids(waves_df, now=now)

    issues: list[Issue] = []

    for visualization in visualizations.values():
        for challenge in _visualization_initial_challenges(visualization, challenges):
            _check_challenge_ttm(
                visualization=visualization,
                challenge=challenge,
                challenges=challenges,
                active_wave_ids=active_wave_ids,
                issues=issues,
                norelapselevels=norelapselevels,
                lastlevel=None,
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
    norelapselevels: int = 4,
) -> dict[str, Any]:
    tables = load_ttm_tables(file_path)
    return run_native_ttm_tables(tables, now=now, norelapselevels=norelapselevels)