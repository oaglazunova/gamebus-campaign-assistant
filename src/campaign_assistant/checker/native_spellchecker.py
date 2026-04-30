from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import language_tool_python
import pandas as pd
from language_tool_python.utils import TextStatus, classify_matches

from campaign_assistant.checker.schema import Issue, SPELLCHECKER


KNOWN_WORDS = [
    "Newbie",
    "Rookie",
    "Expert",
    "Master",
    "Grandmaster",
    "Skilled",
    "Proficient",
    "Mini-Walks",
    "Unterarmstützer",
    "Plank",
    "Wall-Sit",
    "Joggen",
    "MIND",
    "kalziumreiche",
    "Freundlichkeits-Tagebuch",
    "Mikrobiota",
    "Steppin",
    "Up",
    "Joggingintervalle",
    "Wandsitzer",
    "Wandsitz",
]


def load_spellchecker_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
    return {
        "tasks": pd.read_excel(file_path, sheet_name="tasks"),
        "challenges": pd.read_excel(file_path, sheet_name="challenges"),
        "visualizations": pd.read_excel(file_path, sheet_name="visualizations"),
        "waves": pd.read_excel(file_path, sheet_name="waves"),
    }


def build_spellchecker_tool():
    return language_tool_python.LanguageTool(
        language="de-DE",
        mother_tongue="de-DE",
        new_spellings=KNOWN_WORDS,
        remote_server="http://localhost:8081/",
    )


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
        check=SPELLCHECKER,
        severity="low",
        active_wave=wave_id in active_wave_ids if wave_id is not None else False,
        visualization_id=_clean_scalar(visualization.get("id")),
        visualization=str(_clean_scalar(visualization.get("description")) or ""),
        challenge_id=_clean_scalar(challenge.get("id")),
        challenge=str(_clean_scalar(challenge.get("name")) or ""),
        wave_id=wave_id,
        message=message,
        url=_challenge_url(visualization, challenge),
    )


def check_text(tool, text: Any, text_type: str) -> tuple[bool, str | None]:
    if isinstance(text, float):
        errormessage = f"{text_type} is empty."
    else:
        matches = tool.check(text)
        status = classify_matches(matches)
        errormessage = None

        if status == TextStatus.FAULTY:
            correction = tool.correct(text)
            errormessage = f"{text_type} is faulty '{text}'. Proposed correction is \n'{correction}'"
        elif status == TextStatus.GARBAGE:
            errormessage = f"{text_type} is garbage '{text}', no correction can be proposed"

    return (errormessage is not None), errormessage


def run_native_spellchecker_tables(
    tables: Mapping[str, pd.DataFrame],
    now: pd.Timestamp | None = None,
    tool=None,
) -> dict[str, Any]:
    tasks_df = tables["tasks"]
    challenges_df = tables["challenges"]
    visualizations_df = tables["visualizations"]
    waves_df = tables.get("waves", pd.DataFrame())

    tool = tool if tool is not None else build_spellchecker_tool()
    challenges = _challenge_index(challenges_df)
    visualizations = _visualization_index(visualizations_df)
    active_wave_ids = _active_wave_ids(waves_df, now=now)

    issues: list[Issue] = []

    for _, task_row in tasks_df.iterrows():
        task = task_row.to_dict()
        challenge = challenges.get(task.get("challenge"))
        if challenge is None:
            continue

        visualization = visualizations.get(challenge.get("visualizations"))
        if visualization is None:
            continue

        error, errormessage = check_text(tool, task.get("name"), "Name of task")
        if error and errormessage is not None:
            issues.append(
                _issue(
                    challenge=challenge,
                    visualization=visualization,
                    active_wave_ids=active_wave_ids,
                    message=errormessage,
                )
            )

    for _, challenge_row in challenges_df.iterrows():
        challenge = challenge_row.to_dict()
        visualization = visualizations.get(challenge.get("visualizations"))
        if visualization is None:
            continue

        error, errormessage = check_text(tool, challenge.get("name"), "Name of challenge")
        if error and errormessage is not None:
            issues.append(
                _issue(
                    challenge=challenge,
                    visualization=visualization,
                    active_wave_ids=active_wave_ids,
                    message=errormessage,
                )
            )

    issues.sort(key=lambda item: (item.active_wave, item.challenge_id), reverse=True)

    return {
        "status": "Failed" if issues else "Passed",
        "issues": issues,
        "notes": [],
    }


def run_native_spellchecker_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_spellchecker_tables(file_path)
    return run_native_spellchecker_tables(tables, now=now)