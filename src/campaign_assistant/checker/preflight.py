from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.metadata import load_merged_metadata_bundle


_TARGETPOINTS_REQUIRED = {
    "tasks": {"challenge", "points", "max_times_fired", "min_days_between_fire"},
    "challenges": {"id", "visualizations", "target", "evaluate_fail_every_x_minutes"},
    "visualizations": {"id", "campaign", "description", "wave"},
    "waves": {"id", "start", "end"},
}


def _safe_read_sheet(file_path: str | Path, sheet_name: str) -> pd.DataFrame | None:
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception:
        return None


def _normalized_columns(df: pd.DataFrame | None) -> set[str]:
    if df is None:
        return set()
    return {str(column).strip().lower() for column in df.columns}


def _theory_tags(metadata_bundle) -> list[str]:
    return sorted(
        {
            str(tag).strip().lower()
            for item in getattr(metadata_bundle, "theory_sources", []) or []
            for tag in getattr(item, "tags", []) or []
            if str(tag).strip()
        }
    )


def _resolve_ttm_enabled(capabilities: dict[str, Any], theory_tags: list[str]) -> bool:
    if capabilities.get("uses_ttm") is True:
        return True
    return "ttm" in theory_tags or "transtheoretical_model" in theory_tags


def _coerce_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _missing_required_sheets_or_columns(
    file_path: str | Path,
) -> tuple[list[str], dict[str, list[str]], dict[str, pd.DataFrame]]:
    missing_sheets: list[str] = []
    missing_columns: dict[str, list[str]] = {}
    tables: dict[str, pd.DataFrame] = {}

    for sheet_name, required_columns in _TARGETPOINTS_REQUIRED.items():
        df = _safe_read_sheet(file_path, sheet_name)
        if df is None:
            missing_sheets.append(sheet_name)
            continue

        tables[sheet_name] = df
        present = _normalized_columns(df)
        missing = sorted(required_columns - present)
        if missing:
            missing_columns[sheet_name] = missing

    return missing_sheets, missing_columns, tables


def probe_targetpoints_applicability(file_path: str | Path) -> tuple[bool, str]:
    missing_sheets, missing_columns, tables = _missing_required_sheets_or_columns(file_path)

    if missing_sheets:
        joined = ", ".join(f"`{name}`" for name in missing_sheets)
        return False, f"Disabled because the workbook is missing required sheet(s): {joined}."

    if missing_columns:
        parts = [
            f"`{sheet}`: {', '.join(f'`{column}`' for column in columns)}"
            for sheet, columns in missing_columns.items()
        ]
        return (
            False,
            "Disabled because the workbook is missing required target-points columns: "
            + "; ".join(parts)
            + ".",
        )

    tasks_df = tables["tasks"].copy()
    challenges_df = tables["challenges"].copy()
    visualizations_df = tables["visualizations"].copy()
    waves_df = tables["waves"].copy()

    if challenges_df.empty:
        return False, "Disabled because the workbook has no challenge rows."
    if tasks_df.empty:
        return False, "Disabled because the workbook has no task rows."
    if visualizations_df.empty:
        return False, "Disabled because the workbook has no visualization rows."
    if waves_df.empty:
        return False, "Disabled because the workbook has no wave rows."

    if _coerce_numeric(challenges_df["target"]).notna().sum() == 0:
        return False, "Disabled because no challenge has a numeric `target` value."

    if _coerce_numeric(challenges_df["evaluate_fail_every_x_minutes"]).gt(0).sum() == 0:
        return False, (
            "Disabled because no challenge has a positive numeric "
            "`evaluate_fail_every_x_minutes` value."
        )

    task_value_checks = {
        "points": "positive numeric `points`",
        "max_times_fired": "positive numeric `max_times_fired`",
        "min_days_between_fire": "positive numeric `min_days_between_fire`",
    }
    for column, label in task_value_checks.items():
        if _coerce_numeric(tasks_df[column]).gt(0).sum() == 0:
            return False, f"Disabled because no task has {label}."

    challenge_ids = set(challenges_df["id"].dropna().tolist())
    visualization_ids = set(visualizations_df["id"].dropna().tolist())
    wave_ids = set(waves_df["id"].dropna().tolist())

    tasks_df = tasks_df[tasks_df["challenge"].isin(challenge_ids)].copy()
    challenges_df = challenges_df[challenges_df["visualizations"].isin(visualization_ids)].copy()
    visualizations_df = visualizations_df[visualizations_df["wave"].isin(wave_ids)].copy()

    visualization_ids = set(visualizations_df["id"].dropna().tolist())
    challenges_df = challenges_df[challenges_df["visualizations"].isin(visualization_ids)].copy()

    challenge_ids = set(challenges_df["id"].dropna().tolist())
    tasks_df = tasks_df[tasks_df["challenge"].isin(challenge_ids)].copy()

    if tasks_df.empty:
        return False, "Disabled because no tasks are linked to a known challenge."
    if challenges_df.empty:
        return False, "Disabled because no challenges are linked to a known visualization and wave."

    valid_tasks_df = tasks_df[
        _coerce_numeric(tasks_df["points"]).gt(0)
        & _coerce_numeric(tasks_df["max_times_fired"]).gt(0)
        & _coerce_numeric(tasks_df["min_days_between_fire"]).gt(0)
    ].copy()

    if valid_tasks_df.empty:
        return False, (
            "Disabled because no linked task has all required point-computation values "
            "(`points`, `max_times_fired`, `min_days_between_fire`)."
        )

    challenge_ids_with_valid_tasks = set(valid_tasks_df["challenge"].dropna().tolist())

    candidate_challenges_df = challenges_df[
        challenges_df["id"].isin(challenge_ids_with_valid_tasks)
        & _coerce_numeric(challenges_df["target"]).notna()
        & _coerce_numeric(challenges_df["evaluate_fail_every_x_minutes"]).gt(0)
    ].copy()

    if candidate_challenges_df.empty:
        return False, (
            "Disabled because no challenge is fully computable yet: a computable challenge needs "
            "a linked task with valid point settings, a numeric `target`, and a positive "
            "`evaluate_fail_every_x_minutes`."
        )

    challenge_count = len(candidate_challenges_df)
    task_count = len(valid_tasks_df[valid_tasks_df["challenge"].isin(candidate_challenges_df["id"])])

    return (
        True,
        "Enabled because the workbook contains at least "
        f"{challenge_count} computable challenge(s) linked to {task_count} valid task row(s).",
    )


def build_capability_summary_for_file(
    *,
    file_path: str | Path,
    workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    metadata_bundle = load_merged_metadata_bundle(
        file_path=file_path,
        workspace_root=workspace_root,
    )

    capabilities = metadata_bundle.capabilities.to_dict()
    theory_tags = _theory_tags(metadata_bundle)
    ttm_enabled = _resolve_ttm_enabled(capabilities, theory_tags)

    targetpoints_enabled, targetpoints_reason = probe_targetpoints_applicability(file_path)

    validator_applicability = {
        "universal_structural": True,
        "targetpointsreachable": targetpoints_enabled,
        "ttm": ttm_enabled,
    }

    theory_applicability = {
        "ttm_grounding": ttm_enabled,
    }

    uses_progression = capabilities.get("uses_progression")
    point_gatekeeping_module_enabled = uses_progression is not False

    active_modules = {
        "validator_applicability": validator_applicability,
        "theory_applicability": theory_applicability,
        "structural_checks": True,
        "point_gatekeeping_checks": point_gatekeeping_module_enabled,
        "ttm_checks": theory_applicability.get("ttm_grounding", False),
        "content_fix_suggestions": True,
    }

    active_validators = [
        name
        for name, enabled in validator_applicability.items()
        if enabled
    ]

    return {
        "capabilities": capabilities,
        "campaign_family": metadata_bundle.campaign_family.to_dict(),
        "theory_tags": theory_tags,
        "theory_source_count": len(metadata_bundle.theory_sources),
        "validator_applicability": validator_applicability,
        "validator_reasons": {
            "targetpointsreachable": targetpoints_reason,
        },
        "theory_applicability": theory_applicability,
        "active_modules": active_modules,
        "active_validators": active_validators,
        "task_role_count": len(metadata_bundle.task_roles),
        "sources": metadata_bundle.sources,
        "notes": metadata_bundle.notes,
        "missing": metadata_bundle.missing,
    }