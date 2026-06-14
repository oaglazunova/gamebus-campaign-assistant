from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import Issue, SECRETS
from campaign_assistant.checker.table_utils import (
    _active_wave_ids,
    _challenge_index,
    _challenge_url,
    _challenge_visualizations,
    _clean_scalar,
    _get_table,
    _normalise_id,
    _visualization_index,
)


GAMEBUS_STUDIO = "GameBus Studio"


def load_secrets_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
    return {
        "tasks": pd.read_excel(file_path, sheet_name="tasks"),
        "challenges": pd.read_excel(file_path, sheet_name="challenges"),
        "visualizations": pd.read_excel(file_path, sheet_name="visualizations"),
        "waves": pd.read_excel(file_path, sheet_name="waves"),
    }


def _first_existing_visualization(
    challenge: Mapping[str, Any],
    visualizations: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for visualization_id in _challenge_visualizations(challenge):
        visualization = visualizations.get(visualization_id)
        if visualization is not None:
            return visualization
    return None


def _issue(
    *,
    challenge: Mapping[str, Any],
    visualization: Mapping[str, Any],
    active_wave_ids: set[str],
    message: str,
) -> Issue:
    wave_id = _normalise_id(visualization.get("wave"))

    return Issue(
        check=SECRETS,
        severity="medium",
        active_wave=wave_id in active_wave_ids if wave_id is not None else False,
        visualization_id=_normalise_id(visualization.get("id")),
        visualization=str(_clean_scalar(visualization.get("description")) or ""),
        challenge_id=_normalise_id(challenge.get("id")),
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
    value = _clean_scalar(value)
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
        str(_clean_scalar(task_name) or "")
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
    tasks_df = _get_table(tables, "tasks")
    challenges_df = _get_table(tables, "challenges")
    visualizations_df = _get_table(tables, "visualizations")
    waves_df = tables.get("waves", pd.DataFrame())

    challenges = _challenge_index(challenges_df)
    visualizations = _visualization_index(visualizations_df)
    active_wave_ids = _active_wave_ids(waves_df, now=now)

    issues: list[Issue] = []
    secretchecks: dict[str, list[dict[str, Any]]] = {}

    for row_idx, task_row in tasks_df.iterrows():
        task = task_row.to_dict()

        if _clean_scalar(task.get("dataproviders")) != GAMEBUS_STUDIO:
            continue

        secret = condition_triples_find_secret(
            parse_conditions_into_triples(task.get("conditions"))
        )

        if secret is not None:
            secretchecks.setdefault(secret, []).append(task)
            continue

        challenge = challenges.get(_normalise_id(task.get("challenge")) or "")
        if challenge is None:
            continue

        visualization = _first_existing_visualization(challenge, visualizations)
        if visualization is None:
            continue

        task_name = _clean_scalar(task.get("name")) or ""
        news = _proposed_secret_from_task_name(task_name)
        proposedsecret = f"[SECRET, EQUAL, {news}]"

        conditions = _clean_scalar(task.get("conditions"))
        if isinstance(conditions, str) and conditions.strip():
            proposedsecret = f"{proposedsecret}, {conditions}"

        issues.append(
            _issue(
                challenge=challenge,
                visualization=visualization,
                active_wave_ids=active_wave_ids,
                message=(
                    f"Task '{task_name}' has no secret. "
                    f"Proposing {proposedsecret} at column 'conditions' "
                    f"in row={row_idx + 2} (name={task_name})"
                ),
            )
        )

    for secret, tasks in secretchecks.items():
        if len(tasks) <= 1:
            continue

        first = tasks[0]
        first_name = _clean_scalar(first.get("name"))

        all_same_name = all(
            _clean_scalar(task.get("name")) == first_name
            for task in tasks[1:]
        )

        if all_same_name:
            continue

        challenge_ids = [
            _normalise_id(task.get("challenge"))
            for task in tasks
        ]

        challenge_refs = [
            f"{cid} ({_clean_scalar(challenges.get(cid or '', {}).get('name')) or ''})"
            for cid in challenge_ids
        ]

        challenge = challenges.get(_normalise_id(first.get("challenge")) or "")
        if challenge is None:
            continue

        visualization = _first_existing_visualization(challenge, visualizations)
        if visualization is None:
            continue

        issues.append(
            _issue(
                challenge=challenge,
                visualization=visualization,
                active_wave_ids=active_wave_ids,
                message=(
                    f"Task '{first_name}' has copies with the same secret '{secret}', "
                    f"but they have different names (see challenges {challenge_refs})"
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