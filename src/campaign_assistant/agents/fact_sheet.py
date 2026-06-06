from __future__ import annotations

from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value or []) if isinstance(value, list) else []


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _compact_issue(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "check": _text(issue.get("check")) or "unknown",
        "severity": _text(issue.get("severity")) or "unknown",
        "title": _text(
            issue.get("title")
            or issue.get("message")
            or issue.get("description")
            or issue.get("issue")
        )
        or "Finding",
        "message": _text(issue.get("message") or issue.get("description")),
        "visualization": _text(issue.get("visualization")),
        "visualization_id": issue.get("visualization_id"),
        "challenge": _text(issue.get("challenge")),
        "challenge_id": issue.get("challenge_id"),
        "wave_id": issue.get("wave_id"),
        "active_wave": bool(issue.get("active_wave")) if issue.get("active_wave") is not None else None,
    }


def build_fact_sheet(result: dict[str, Any]) -> dict[str, Any]:
    """
    Build authoritative facts for response guarding.

    Fact categories are intentionally separated:
    - checker_facts: deterministic checker output;
    - export_facts: descriptive workbook-derived structure;
    - approved_design_facts: optional future human-approved design context.
    """
    summary = _as_dict(result.get("summary"))
    snapshot = _as_dict(result.get("campaign_snapshot"))
    counts = _as_dict(snapshot.get("counts"))

    prioritized_issues = [
        item for item in _as_list(result.get("prioritized_issues"))
        if isinstance(item, dict)
    ]

    known_findings = [_compact_issue(issue) for issue in prioritized_issues]

    challenges = [
        item for item in _as_list(snapshot.get("challenges"))
        if isinstance(item, dict)
    ]
    tasks = [
        item for item in _as_list(snapshot.get("tasks"))
        if isinstance(item, dict)
    ]
    visualizations = [
        item for item in _as_list(snapshot.get("visualizations"))
        if isinstance(item, dict)
    ]

    return {
        "checker_facts": {
            "source": "deterministic_checker",
            "total_issues": int(summary.get("total_issues", 0) or 0),
            "checks_run": _as_list(result.get("checks_run")),
            "passed_checks": _as_list(summary.get("passed_checks")),
            "failed_checks": _as_list(summary.get("failed_checks")),
            "errored_checks": _as_list(summary.get("errored_checks")),
            "issue_count_by_check": _as_dict(summary.get("issue_count_by_check")),
            "severity_counts": _as_dict(summary.get("severity_counts")),
            "known_findings": known_findings,
            "known_finding_titles": [
                finding["title"] for finding in known_findings
                if finding.get("title")
            ],
            "known_checks_with_issues": sorted(
                {
                    str(check)
                    for check, count in _as_dict(summary.get("issue_count_by_check")).items()
                    if int(count or 0) > 0
                }
            ),
        },
        "export_facts": {
            "source": "campaign_export",
            "campaign_name": result.get("campaign_name") or snapshot.get("campaign_name"),
            "file_name": result.get("file_name") or snapshot.get("file_name"),
            "counts": counts,
            "known_challenge_ids": [
                item.get("id") for item in challenges if item.get("id") is not None
            ],
            "known_challenge_names": [
                str(item.get("name")) for item in challenges if item.get("name")
            ],
            "known_task_ids": [
                item.get("id") for item in tasks if item.get("id") is not None
            ],
            "known_task_names": [
                str(item.get("name")) for item in tasks if item.get("name")
            ],
            "known_visualization_ids": [
                item.get("id") for item in visualizations if item.get("id") is not None
            ],
            "known_visualization_names": [
                str(item.get("name")) for item in visualizations if item.get("name")
            ],
        },
        "approved_design_facts": {
            "source": "organizer_approved_summary",
            "available": False,
            "organizer_approved": False,
            "summary": None,
            "document_ids": [],
        },
    }