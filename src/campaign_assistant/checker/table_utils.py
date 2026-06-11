from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd


WorkbookTables = Mapping[str, pd.DataFrame]


def _get_now_timestamp() -> pd.Timestamp:
    """Return a timezone-naive timestamp for comparing with Excel dates."""
    return pd.Timestamp.now().tz_localize(None)


def _normalise_table_name(name: Any) -> str:
    return str(name).strip().lower().replace(" ", "_")


def load_workbook_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
    """
    Load all sheets from a GameBus campaign export once.

    The native checkers expect lowercase sheet keys such as ``tasks`` and
    ``challenges``. Normalising names here keeps the wrapper independent from
    exact Excel sheet capitalisation while avoiding the old legacy checker
    dependency.
    """
    raw_tables = pd.read_excel(file_path, sheet_name=None)
    return {_normalise_table_name(name): df for name, df in raw_tables.items()}


def _get_table(tables: WorkbookTables, name: str) -> pd.DataFrame:
    key = _normalise_table_name(name)
    if key in tables:
        return tables[key]

    # Fallback for callers that pass a plain dict with original Excel names.
    for table_name, df in tables.items():
        if _normalise_table_name(table_name) == key:
            return df

    raise KeyError(f"Required sheet '{name}' is missing from the campaign export.")


def _coerce_timestamp(value: Any) -> pd.Timestamp | None:
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    try:
        return pd.Timestamp(value).tz_localize(None)
    except Exception:
        return None


def _active_wave_ids(waves_df: pd.DataFrame | None, now: pd.Timestamp | None = None) -> set[Any]:
    if waves_df is None or waves_df.empty:
        return set()

    now = now if now is not None else _get_now_timestamp()
    now = pd.Timestamp(now)
    if now.tzinfo is not None:
        now = now.tz_convert(None)
    active: set[Any] = set()

    for _, row in waves_df.iterrows():
        start = _coerce_timestamp(row.get("start"))
        end = _coerce_timestamp(row.get("end"))
        if start is not None and end is not None and start <= now <= end:
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
        "https://campaigns.healthyw8.gamebus.eu/editor/for/"
        f"{visualization.get('campaign')}/{challenge.get('visualizations')}/challenges/{challenge.get('id')}"
    )


def _is_initial(challenge: Mapping[str, Any]) -> bool:
    return challenge.get("is_initial_level") == 1


def _is_terminal(
    challenge: Mapping[str, Any],
    challenges: Mapping[Any, dict[str, Any]] | None = None,
) -> bool:
    """
    Return whether a challenge is terminal.

    A terminal challenge is represented by ``success_next`` pointing to itself.
    ``challenges`` is optional for compatibility with callers that already have
    the current challenge row and do not need to resolve the successor record.
    """
    challenge_id = challenge.get("id")
    success_next = challenge.get("success_next")

    if _clean_scalar(success_next) == _clean_scalar(challenge_id):
        return True

    if challenges is None:
        return False

    next_challenge = challenges.get(success_next)
    return next_challenge is not None and next_challenge.get("id") == challenge_id
