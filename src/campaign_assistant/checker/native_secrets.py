from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import Issue, SECRETS


GAMEBUS_STUDIO = "GameBus Studio"


def load_secrets_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
    return {
        "tasks": pd.read_excel(file_path, sheet_name="tasks"),
        "challenges": pd.read_excel(file_path, sheet_name="challenges"),
        "visualizations": pd.read_excel(file_path, sheet_name="visualizations"),
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


def _challenge_url(visualization: Mapping[str, Any], challenge: Mapping[str, Any]) -> str:
    return (
        f"https://campaigns.healthyw8.gamebus.eu/editor/for/"
        f"{visualization.get('campaign')}/{challenge.get('visualizations')}/challenges/{challenge.get('id')}"
    )


def _issue(
    *,
    challenge: Mapping[str, Any],
    visualization: Mapping[str, Any],
    active_wave_ids: set[Any],
    message: str,
) -> Issue:
    wave_id = _clean_scalar(visualization.get("wave"))
    return Issue(
        check=SECRETS,
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


def split_triple(triple: str) -> list[str]:
    parts = triple.split(",")
    if len(parts) > 3:
        parts = [parts[0], parts[1], ",".join(parts[2:])]
    return [str(part).strip() for part in parts]


def parse_conditions_into_triples(value: Any) -> list[list[str]]:
    if isinstance(value, float):
        return []
    if value is None:
        return []

    triples = re.findall(r"\[([^\]]+)\]", str(value))
    return [split_triple(triple) for triple in triples]


def condition_triples_find_secret(triples: list[list[str]]) -> str | None:
    for triple in triples:
        if len(triple) < 3:
            continue
        left = str(triple[0]).strip()
        op = str(triple[1]).strip()
        if left == "SECRET" and op == "EQUAL":
            return str(triple[2]).strip()
    return None


def _proposed_secret_from_task_name(task_name: Any) -> str:
    return (
        str(task_name)
        .replace(" ", "-")
        .replace("ü", "ue")
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ß", "sz")
        .replace(".", "-dot-")
        .replace(";", "-semicolon-")
        .replace(":", "-colon-")
    )


def run_native_secrets_tables(
    tables: Mapping[str, pd.DataFrame],
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tasks_df = tables["tasks"]
    challenges_df = tables["challenges"]
    visualizations_df = tables["visualizations"]
    waves_df = tables.get("waves", pd.DataFrame())

    challenges = _challenge_index(challenges_df)
    visualizations = _visualization_index(visualizations_df)
    active_wave_ids = _active_wave_ids(waves_df, now=now)

    issues: list[Issue] = []
    secretchecks: dict[str, list[dict[str, Any]]] = {}

    for row_idx, task_row in tasks_df.iterrows():
        task = task_row.to_dict()

        if task.get("dataproviders") != GAMEBUS_STUDIO:
            continue

        secret = condition_triples_find_secret(
            parse_conditions_into_triples(task.get("conditions"))
        )

        if secret is not None:
            secretchecks.setdefault(secret, []).append(task)
            continue

        challenge = challenges.get(task.get("challenge"))
        if challenge is None:
            continue

        visualization = visualizations.get(challenge.get("visualizations"))
        if visualization is None:
            continue

        news = _proposed_secret_from_task_name(task.get("name"))
        proposedsecret = f"[SECRET, EQUAL, {news}]"

        if isinstance(task.get("conditions"), str):
            proposedsecret = f"{proposedsecret}, {task['conditions']}"

        issues.append(
            _issue(
                challenge=challenge,
                visualization=visualization,
                active_wave_ids=active_wave_ids,
                message=(
                    f"Task '{task['name']}' has no secret. "
                    f"Proposing {proposedsecret} at column 'conditions' "
                    f"in row={row_idx} (name={task['name']})"
                ),
            )
        )

    for secret, tasks in secretchecks.items():
        if len(tasks) <= 1:
            continue

        first = tasks[0]
        first_name = first.get("name")
        all_same_name = all(task.get("name") == first_name for task in tasks[1:])

        if all_same_name:
            continue

        challenge_ids = [task.get("challenge") for task in tasks]
        challenge_refs = [
            f"{cid} ({challenges.get(cid, {}).get('name', '')})"
            for cid in challenge_ids
        ]

        challenge = challenges.get(first.get("challenge"))
        if challenge is None:
            continue

        visualization = visualizations.get(challenge.get("visualizations"))
        if visualization is None:
            continue

        issues.append(
            _issue(
                challenge=challenge,
                visualization=visualization,
                active_wave_ids=active_wave_ids,
                message=(
                    f"Task '{first_name}' has copies with the same secret '{secret}', "
                    f"but that have different names (see challenges {challenge_refs})"
                ),
            )
        )

    issues.sort(key=lambda item: (item.active_wave, item.challenge_id), reverse=True)

    return {
        "status": "Failed" if issues else "Passed",
        "issues": issues,
        "notes": [],
    }


def run_native_secrets_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_secrets_tables(file_path)
    return run_native_secrets_tables(tables, now=now)