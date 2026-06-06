from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from campaign_assistant.checker.campaign_snapshot import build_campaign_snapshot


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value or []) if isinstance(value, list) else []


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _issue_check(issue: dict[str, Any], fallback: str | None = None) -> str:
    return str(issue.get("check") or fallback or "unknown")


def _issue_severity(issue: dict[str, Any]) -> str:
    severity = str(
        issue.get("severity")
        or issue.get("priority")
        or issue.get("level")
        or "unknown"
    ).lower()

    if severity == "critical":
        return "high"

    if severity in {"high", "medium", "low"}:
        return severity

    return "unknown"


def _severity_rank(issue: dict[str, Any]) -> int:
    severity = _issue_severity(issue)
    if severity == "high":
        return 0
    if severity == "medium":
        return 1
    if severity == "low":
        return 2
    return 3


def _active_wave_rank(issue: dict[str, Any]) -> int:
    return 0 if bool(issue.get("active_wave")) else 1


def _issue_title(issue: dict[str, Any]) -> str:
    return str(
        issue.get("title")
        or issue.get("message")
        or issue.get("description")
        or issue.get("issue")
        or "Finding"
    )


def _normalize_issue(issue: dict[str, Any], fallback_check: str | None = None) -> dict[str, Any]:
    normalized = dict(issue)
    normalized["check"] = _issue_check(normalized, fallback=fallback_check)
    normalized["severity"] = _issue_severity(normalized)

    if "title" not in normalized:
        normalized["title"] = _issue_title(normalized)

    return normalized


def _collect_issues_by_check(result: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    raw_by_check = _as_dict(result.get("issues_by_check"))
    issues_by_check: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for check_id, raw_issues in raw_by_check.items():
        check_id = str(check_id)
        if not isinstance(raw_issues, list):
            continue

        for raw_issue in raw_issues:
            if isinstance(raw_issue, dict):
                issue = _normalize_issue(raw_issue, fallback_check=check_id)
                issues_by_check[issue["check"]].append(issue)

    if issues_by_check:
        return dict(issues_by_check)

    # Fallback: reconstruct from prioritized_issues if issues_by_check is missing.
    prioritized = _as_list(result.get("prioritized_issues"))
    for raw_issue in prioritized:
        if isinstance(raw_issue, dict):
            issue = _normalize_issue(raw_issue)
            issues_by_check[issue["check"]].append(issue)

    return dict(issues_by_check)


def _flatten_issues(issues_by_check: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []

    for check_id, issues in issues_by_check.items():
        for issue in issues:
            flattened.append(_normalize_issue(issue, fallback_check=check_id))

    return flattened


def _prioritize_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        issues,
        key=lambda issue: (
            _severity_rank(issue),
            _active_wave_rank(issue),
            str(issue.get("check") or ""),
            str(issue.get("visualization") or ""),
            str(issue.get("challenge") or ""),
            str(issue.get("title") or ""),
        ),
    )


def _issue_count_by_check(issues_by_check: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {check: len(issues) for check, issues in sorted(issues_by_check.items())}


def _severity_counts(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "high": 0,
        "medium": 0,
        "low": 0,
        "unknown": 0,
    }

    for issue in issues:
        severity = _issue_severity(issue)
        counts[severity] = counts.get(severity, 0) + 1

    return counts


def _infer_failed_checks(
    *,
    checks_run: list[str],
    issue_count_by_check: dict[str, int],
    existing_failed: list[str],
    existing_errored: list[str],
) -> list[str]:
    failed = set(existing_failed)

    for check in checks_run:
        if issue_count_by_check.get(check, 0) > 0:
            failed.add(check)

    for check in existing_errored:
        failed.discard(check)

    return sorted(failed)


def _infer_passed_checks(
    *,
    checks_run: list[str],
    failed_checks: list[str],
    errored_checks: list[str],
) -> list[str]:
    failed_or_errored = set(failed_checks) | set(errored_checks)
    return [check for check in checks_run if check not in failed_or_errored]


def _campaign_name_from_result(result: dict[str, Any]) -> str | None:
    for key in ["campaign_name", "campaign", "name"]:
        value = _string_or_none(result.get(key))
        if value:
            return value

    snapshot = _as_dict(result.get("campaign_snapshot"))
    for key in ["campaign_name", "name"]:
        value = _string_or_none(snapshot.get(key))
        if value:
            return value

    return None


def _basic_campaign_snapshot(
    result: dict[str, Any],
    *,
    source_file: str | Path | None,
    checks_run: list[str],
) -> dict[str, Any]:
    """
    Compact campaign context for UI and future LLM agents.
    """
    existing = _as_dict(result.get("campaign_snapshot"))
    if existing and existing.get("counts"):
        return existing

    if source_file is not None:
        snapshot = build_campaign_snapshot(
            source_file,
            checks_run=checks_run,
        )
        if snapshot:
            return snapshot

    return {
        "campaign_name": _campaign_name_from_result(result),
        "source_file": _string_or_none(result.get("source_file")),
        "file_name": _string_or_none(result.get("file_name")),
        "checks_run": list(checks_run or result.get("checks_run") or []),
        "waves": [],
        "visualizations": [],
        "challenges": [],
        "tasks": [],
        "transitions": [],
        "task_summary_by_challenge": {},
        "counts": {},
        "extraction_warnings": [],
    }


def normalize_analysis_result(
    result: dict[str, Any],
    *,
    source_file: str | Path | None = None,
    selected_checks: list[str] | None = None,
) -> dict[str, Any]:
    """
    Normalize checker output into one stable paper-release result structure.

    This function does not change validator logic. It only makes downstream
    UI/assistant code consume a predictable schema.
    """
    normalized = dict(result or {})

    source_file_str = str(source_file) if source_file is not None else _string_or_none(normalized.get("source_file"))
    file_name = (
        _string_or_none(normalized.get("file_name"))
        or (Path(source_file_str).name if source_file_str else None)
        or "campaign_export.xlsx"
    )

    checks_run = list(selected_checks or normalized.get("checks_run") or [])

    issues_by_check = _collect_issues_by_check(normalized)
    all_issues = _flatten_issues(issues_by_check)
    prioritized_issues = _prioritize_issues(all_issues)

    issue_count_by_check = _issue_count_by_check(issues_by_check)
    severity_counts = _severity_counts(all_issues)

    old_summary = _as_dict(normalized.get("summary"))
    errored_checks = sorted(str(item) for item in _as_list(old_summary.get("errored_checks")))
    old_failed_checks = [str(item) for item in _as_list(old_summary.get("failed_checks"))]

    failed_checks = _infer_failed_checks(
        checks_run=checks_run,
        issue_count_by_check=issue_count_by_check,
        existing_failed=old_failed_checks,
        existing_errored=errored_checks,
    )
    passed_checks = _infer_passed_checks(
        checks_run=checks_run,
        failed_checks=failed_checks,
        errored_checks=errored_checks,
    )

    normalized["campaign_name"] = _campaign_name_from_result(normalized)
    normalized["file_name"] = file_name
    normalized["source_file"] = source_file_str
    normalized["checks_run"] = checks_run
    normalized["issues_by_check"] = issues_by_check
    normalized["prioritized_issues"] = prioritized_issues
    normalized["campaign_snapshot"] = _basic_campaign_snapshot(
        normalized,
        source_file=source_file,
        checks_run=checks_run,
    )
    normalized["excel_report_path"] = normalized.get("excel_report_path")

    normalized["summary"] = {
        **old_summary,
        "total_issues": len(all_issues),
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "errored_checks": errored_checks,
        "issue_count_by_check": issue_count_by_check,
        "severity_counts": severity_counts,
    }

    assistant_meta = _as_dict(normalized.get("assistant_meta"))
    assistant_meta.setdefault("selected_checks", checks_run)
    normalized["assistant_meta"] = assistant_meta

    return normalized
