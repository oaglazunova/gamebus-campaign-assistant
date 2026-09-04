from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import tempfile

import pandas as pd

from campaign_assistant.checker.native_consistency import run_native_consistency_tables
from campaign_assistant.checker.native_reachability import run_native_reachability_tables
from campaign_assistant.checker.native_secrets import run_native_secrets_tables
from campaign_assistant.checker.native_spellchecker import run_native_spellchecker_tables
from campaign_assistant.checker.native_targetpointsreachable import run_native_targetpointsreachable_tables
from campaign_assistant.checker.native_ttm import run_native_ttm_tables
from campaign_assistant.checker.native_visualizationintern import run_native_visualizationintern_tables
from campaign_assistant.checker.prioritization import issue_priority_score
from campaign_assistant.checker.schema import (
    CONSISTENCY,
    DEFAULT_CHECKS,
    Issue,
    REACHABILITY,
    SECRETS,
    SPELLCHECKER,
    TARGETPOINTSREACHABLE,
    TTMSTRUCTURE,
    VISUALIZATIONINTERN,
    PROGRESSIONBRANCHCONSISTENCY,
    DUPLICATETASKNAMES,
    TEXTPOINTSCONSISTENCY,
    CAMPAIGNMETADATA,
)
from campaign_assistant.checker.table_utils import (
    _active_wave_ids,
    _clean_scalar,
    _get_now_timestamp,
    _get_table,
    _normalise_id,
    load_workbook_tables,
)
from campaign_assistant.checker.native_duplicatetasknames import run_native_duplicatetasknames_tables
from campaign_assistant.checker.native_textpointsconsistency import run_native_textpointsconsistency_tables
from campaign_assistant.checker.native_progressionbranchconsistency import (
    run_native_progressionbranchconsistency_tables,
)
from campaign_assistant.checker.native_campaignmetadata import (
    run_native_campaignmetadata_tables,
)


NATIVE_CHECK_RUNNERS = {
    REACHABILITY: run_native_reachability_tables,
    CONSISTENCY: run_native_consistency_tables,
    VISUALIZATIONINTERN: run_native_visualizationintern_tables,
    PROGRESSIONBRANCHCONSISTENCY: (
        run_native_progressionbranchconsistency_tables
    ),
    SECRETS: run_native_secrets_tables,
    SPELLCHECKER: run_native_spellchecker_tables,
    TARGETPOINTSREACHABLE: run_native_targetpointsreachable_tables,
    TTMSTRUCTURE: run_native_ttm_tables,
    TEXTPOINTSCONSISTENCY: run_native_textpointsconsistency_tables,
    DUPLICATETASKNAMES: run_native_duplicatetasknames_tables,
    CAMPAIGNMETADATA: run_native_campaignmetadata_tables,
}


EXCEL_REPORT_COLUMNS = ["Kind", "Visualization", "Challenge", "Error", "URL"]


def export_issues_to_excel(issues: list[Issue], output_path: str | Path) -> str:
    """Export normalized issues to the traditional GameBus checker Excel format."""
    rows = [
        {
            "Kind": issue.check,
            "Visualization": issue.visualization,
            "Challenge": issue.challenge,
            "Error": issue.message,
            "URL": issue.url,
        }
        for issue in issues
    ]
    df = pd.DataFrame(rows, columns=EXCEL_REPORT_COLUMNS)

    output_path = str(output_path)
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Errors", index=False)
        worksheet = writer.sheets["Errors"]

        max_row, max_col = df.shape
        column_settings = [{"header": column} for column in df.columns]
        worksheet.add_table(0, 0, max_row, max_col - 1, {"columns": column_settings})
        worksheet.autofit()

    return output_path


def _build_waves_summary(tables: dict[str, pd.DataFrame], active_wave_ids: set[Any]) -> list[dict[str, Any]]:
    try:
        waves_df = _get_table(tables, "waves")
    except KeyError:
        return []

    if waves_df.empty:
        return []

    waves: list[dict[str, Any]] = []
    for _, row in waves_df.iterrows():
        wave_id = _normalise_id(row.get("id"))
        waves.append(
            {
                "id": wave_id,
                "name": _clean_scalar(row.get("name")),
                "start": _clean_scalar(row.get("start")),
                "end": _clean_scalar(row.get("end")),
                "active_now": wave_id in active_wave_ids,
            }
        )

    return waves


def _excel_report_path_for(file_path: str | Path) -> Path:
    output_dir = Path(tempfile.gettempdir()) / "gamebus_campaign_assistant"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"issues-{Path(file_path).stem}.xlsx"


def run_campaign_checks(
    file_path: str | Path,
    checks: list[str] | None = None,
    export_excel: bool = False,
) -> dict[str, Any]:
    """Run selected native checks on a GameBus campaign Excel export."""
    selected_checks = list(checks or DEFAULT_CHECKS)
    tables = load_workbook_tables(file_path)
    now = _get_now_timestamp()

    try:
        waves_df = _get_table(tables, "waves")
    except KeyError:
        waves_df = pd.DataFrame()
    active_wave_ids = _active_wave_ids(waves_df, now=now)

    check_status: dict[str, str] = {}
    notes: list[str] = []
    issues: list[Issue] = []

    for check_name in selected_checks:
        runner = NATIVE_CHECK_RUNNERS.get(check_name)
        if runner is None:
            check_status[check_name] = "Error"
            notes.append(f"Unknown check '{check_name}'")
            continue

        try:
            native_result = runner(tables, now=now)
        except Exception as exc:
            check_status[check_name] = "Error"
            notes.append(f"Check '{check_name}' crashed: {exc}")
            continue

        check_status[check_name] = str(native_result.get("status", "Error"))
        issues.extend(native_result.get("issues", []))
        notes.extend(native_result.get("notes", []))

    issues.sort(key=issue_priority_score, reverse=True)

    issues_by_check: dict[str, list[dict[str, Any]]] = {check: [] for check in selected_checks}
    for issue in issues:
        issues_by_check.setdefault(issue.check, []).append(issue.to_dict())

    passed_checks = [name for name, status in check_status.items() if status == "Passed"]
    failed_checks = [name for name, status in check_status.items() if status == "Failed"]
    errored_checks = [name for name, status in check_status.items() if status == "Error"]

    excel_report_path = None
    if export_excel:
        report_path = _excel_report_path_for(file_path)
        export_issues_to_excel(issues, report_path)
        excel_report_path = str(report_path)

    return {
        "file_name": Path(file_path).name,
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
        "checks_run": selected_checks,
        "summary": {
            "total_issues": len(issues),
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "errored_checks": errored_checks,
            "issue_count_by_check": {
                name: len(issues_by_check.get(name, [])) for name in selected_checks
            },
        },
        "waves": _build_waves_summary(tables, active_wave_ids),
        "issues_by_check": issues_by_check,
        "prioritized_issues": [issue.to_dict() for issue in issues[:25]],
        "notes": notes,
        "excel_report_path": excel_report_path,
    }
