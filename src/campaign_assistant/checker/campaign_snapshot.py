from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


def _clean_value(value: Any) -> Any:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass

    if isinstance(value, str):
        text = value.strip()
        return text if text else None

    return value


def _clean_text(value: Any) -> str | None:
    value = _clean_value(value)
    if value is None:
        return None
    return str(value).strip() or None


def _clean_number(value: Any) -> int | float | str | None:
    value = _clean_value(value)
    if value is None:
        return None

    if isinstance(value, float) and value.is_integer():
        return int(value)

    return value


def _sheet_lookup(tables: dict[str, pd.DataFrame], wanted: str) -> pd.DataFrame | None:
    wanted_norm = wanted.lower().replace(" ", "").replace("_", "")

    for sheet_name, df in tables.items():
        sheet_norm = str(sheet_name).lower().replace(" ", "").replace("_", "")
        if sheet_norm == wanted_norm:
            return df

    return None


def _column_lookup(df: pd.DataFrame) -> dict[str, str]:
    lookup: dict[str, str] = {}

    for column in df.columns:
        key = str(column).strip().lower().replace(" ", "_")
        lookup[key] = column

    return lookup


def _get(row: pd.Series, columns: dict[str, str], *names: str) -> Any:
    for name in names:
        key = name.strip().lower().replace(" ", "_")
        if key in columns:
            return _clean_value(row.get(columns[key]))
    return None


def _get_text(row: pd.Series, columns: dict[str, str], *names: str) -> str | None:
    return _clean_text(_get(row, columns, *names))


def _get_number(row: pd.Series, columns: dict[str, str], *names: str) -> int | float | str | None:
    return _clean_number(_get(row, columns, *names))


def _records(df: pd.DataFrame | None, *, max_rows: int | None = None) -> list[pd.Series]:
    if df is None or df.empty:
        return []

    working = df.copy()
    working = working.dropna(how="all")

    if max_rows is not None:
        working = working.head(max_rows)

    return [row for _, row in working.iterrows()]


def _extract_campaign_name(campaigns: pd.DataFrame | None) -> str | None:
    rows = _records(campaigns, max_rows=1)
    if not rows:
        return None

    columns = _column_lookup(campaigns)
    row = rows[0]

    return (
        _get_text(row, columns, "name", "campaign_name", "label", "title")
        or _get_text(row, columns, "abbreviation", "id")
    )


def _extract_waves(waves: pd.DataFrame | None, *, max_items: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    if waves is None:
        return items

    columns = _column_lookup(waves)

    for row in _records(waves, max_rows=max_items):
        item = {
            "id": _get_number(row, columns, "id", "wave_id"),
            "name": _get_text(row, columns, "name", "label", "title"),
            "start": _get_text(row, columns, "start", "start_date", "date_start"),
            "end": _get_text(row, columns, "end", "end_date", "date_end"),
        }

        if any(value is not None for value in item.values()):
            items.append(item)

    return items


def _extract_visualizations(visualizations: pd.DataFrame | None, *, max_items: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    if visualizations is None:
        return items

    columns = _column_lookup(visualizations)

    for row in _records(visualizations, max_rows=max_items):
        item = {
            "id": _get_number(row, columns, "id", "visualization_id"),
            "name": _get_text(row, columns, "name", "label", "visualization", "title"),
            "wave_id": _get_number(row, columns, "wave", "wave_id"),
            "groups": _get_text(row, columns, "groups", "group", "group_id"),
            "menu_order": _get_number(row, columns, "menu_order", "menuorder"),
            "tabbar_order": _get_number(row, columns, "tabbar_order", "tabbarorder"),
            "show_in_menu": _get(row, columns, "show_in_menu", "showinmenu"),
            "show_in_tabbar": _get(row, columns, "show_in_tabbar", "showintabbar"),
        }

        if any(value is not None for value in item.values()):
            items.append(item)

    return items


def _extract_challenges(challenges: pd.DataFrame | None, *, max_items: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    if challenges is None:
        return items

    columns = _column_lookup(challenges)

    for row in _records(challenges, max_rows=max_items):
        item = {
            "id": _get_number(row, columns, "id", "challenge_id"),
            "name": _get_text(row, columns, "name", "label", "title"),
            "description": _get_text(row, columns, "description", "desc"),
            "visualization_id": _get_number(row, columns, "visualizations", "visualization", "visualization_id"),
            "target_points": _get_number(row, columns, "target", "target_points", "targetpoints"),
            "is_initial_level": _get(
                row,
                columns,
                "is_initial_level",
                "isinitiallevel",
            ),
            "success_next": _get_number(row, columns, "success_next", "successnext", "success"),
            "failure_next": _get_number(row, columns, "failure_next", "fail_next", "failure", "failure_next_id"),
            "start": _get_text(row, columns, "start", "start_date", "date_start"),
            "end": _get_text(row, columns, "end", "end_date", "date_end"),
            "url": _get_text(row, columns, "url", "edit_url"),
        }

        if any(value is not None for value in item.values()):
            items.append(item)

    return items


def _extract_tasks(tasks: pd.DataFrame | None, *, max_items: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    if tasks is None:
        return items

    columns = _column_lookup(tasks)

    for row in _records(tasks, max_rows=max_items):
        item = {
            "id": _get_number(row, columns, "id", "task_id"),
            "name": _get_text(row, columns, "name", "label", "title"),
            "description": _get_text(row, columns, "description", "desc"),
            "challenge_id": _get_number(row, columns, "challenge", "challenge_id"),
            "points": _get_number(row, columns, "points", "point"),
            "conditions": _get_text(row, columns, "conditions", "condition"),
            "activity_scheme_default": _get_text(
                row,
                columns,
                "activityscheme_default",
                "activity_scheme_default",
                "activityscheme",
            ),
            "activity_schemes_allowed": _get_text(
                row,
                columns,
                "activityschemes_allowed",
                "activity_schemes_allowed",
            ),
            "max_times_fired": _get_number(row, columns, "max_times_fired", "maxtimesfired"),
            "min_days_between_fire": _get_number(
                row,
                columns,
                "min_days_between_fire",
                "mindaysbetweenfire",
            ),
            "image_required": _get(row, columns, "image_required", "imagerequired"),
        }

        if any(value is not None for value in item.values()):
            items.append(item)

    return items


def _task_summary_by_challenge(tasks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for task in tasks:
        challenge_id = task.get("challenge_id")
        if challenge_id is None:
            continue
        grouped[str(challenge_id)].append(task)

    summary: dict[str, dict[str, Any]] = {}

    for challenge_id, challenge_tasks in grouped.items():
        points = [
            task.get("points")
            for task in challenge_tasks
            if isinstance(task.get("points"), (int, float))
        ]

        summary[challenge_id] = {
            "task_count": len(challenge_tasks),
            "total_points_if_all_tasks_completed_once": sum(points) if points else None,
            "task_names": [
                str(task.get("name"))
                for task in challenge_tasks
                if task.get("name") is not None
            ][:10],
        }

    return summary


def _transition_summary(challenges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    transitions: list[dict[str, Any]] = []

    for challenge in challenges:
        source = challenge.get("id")
        if source is None:
            continue

        success_next = challenge.get("success_next")
        failure_next = challenge.get("failure_next")

        if success_next is not None:
            transitions.append(
                {
                    "source_challenge_id": source,
                    "target_challenge_id": success_next,
                    "transition_type": "success",
                }
            )

        if failure_next is not None:
            transitions.append(
                {
                    "source_challenge_id": source,
                    "target_challenge_id": failure_next,
                    "transition_type": "failure",
                }
            )

    return transitions


def build_campaign_snapshot(
    file_path: str | Path,
    *,
    checks_run: list[str] | None = None,
    max_items: int = 80,
) -> dict[str, Any]:
    """
    Build a compact, export-derived campaign snapshot.

    This is designed for UI summaries and future LLM agent context. It should
    remain compact and should not expose the full workbook contents.
    """
    file_path = Path(file_path)

    snapshot: dict[str, Any] = {
        "source_file": str(file_path),
        "file_name": file_path.name,
        "checks_run": list(checks_run or []),
        "campaign_name": None,
        "waves": [],
        "visualizations": [],
        "challenges": [],
        "tasks": [],
        "transitions": [],
        "task_summary_by_challenge": {},
        "counts": {},
        "extraction_warnings": [],
    }

    try:
        tables = pd.read_excel(file_path, sheet_name=None)
    except Exception as exc:
        snapshot["extraction_warnings"].append(f"Could not read campaign workbook: {exc}")
        return snapshot

    campaigns = _sheet_lookup(tables, "campaigns")
    waves = _sheet_lookup(tables, "waves")
    visualizations = _sheet_lookup(tables, "visualizations")
    challenges = _sheet_lookup(tables, "challenges")
    tasks = _sheet_lookup(tables, "tasks")

    missing_sheets = [
        name
        for name, df in {
            "campaigns": campaigns,
            "waves": waves,
            "visualizations": visualizations,
            "challenges": challenges,
            "tasks": tasks,
        }.items()
        if df is None
    ]

    if missing_sheets:
        snapshot["extraction_warnings"].append(
            "Missing expected sheet(s): " + ", ".join(missing_sheets)
        )

    campaign_name = _extract_campaign_name(campaigns)
    waves_data = _extract_waves(waves, max_items=max_items)
    visualizations_data = _extract_visualizations(visualizations, max_items=max_items)
    challenges_data = _extract_challenges(challenges, max_items=max_items)
    tasks_data = _extract_tasks(tasks, max_items=max_items)

    snapshot["campaign_name"] = campaign_name
    snapshot["waves"] = waves_data
    snapshot["visualizations"] = visualizations_data
    snapshot["challenges"] = challenges_data
    snapshot["tasks"] = tasks_data
    snapshot["transitions"] = _transition_summary(challenges_data)
    snapshot["task_summary_by_challenge"] = _task_summary_by_challenge(tasks_data)
    snapshot["counts"] = {
        "waves": len(waves_data),
        "visualizations": len(visualizations_data),
        "challenges": len(challenges_data),
        "tasks": len(tasks_data),
        "transitions": len(snapshot["transitions"]),
    }

    return snapshot
