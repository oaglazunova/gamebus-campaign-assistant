from __future__ import annotations

from typing import Any

from campaign_assistant.checker.gamebus_fix_guidance import (
    gamebus_fix_guidance_markdown_for_issue,
)
from campaign_assistant.agents.gamebus_studio_knowledge import (
    gamebus_studio_facts_markdown_for_issue,
)


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value or []) if isinstance(value, list) else []


def _string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _truncate_text(value: Any, *, max_chars: int = 300) -> str | None:
    text = _string(value)
    if not text:
        return None

    if len(text) <= max_chars:
        return text

    return text[: max_chars - 3].rstrip() + "..."


def _compact_item(
    item: dict[str, Any],
    *,
    fields: list[str],
    max_text_chars: int = 300,
) -> dict[str, Any]:
    compact: dict[str, Any] = {}

    for field in fields:
        value = item.get(field)
        if value is None or value == "":
            continue

        if isinstance(value, str):
            value = _truncate_text(value, max_chars=max_text_chars)

        compact[field] = value

    return compact


def _severity_rank(issue: dict[str, Any]) -> int:
    severity = _string(issue.get("severity")).lower()
    if severity in {"critical", "high"}:
        return 0
    if severity == "medium":
        return 1
    if severity == "low":
        return 2
    return 3


def _active_wave_rank(issue: dict[str, Any]) -> int:
    return 0 if bool(issue.get("active_wave")) else 1


def _issue_title(issue: dict[str, Any]) -> str:
    return _string(
        issue.get("title")
        or issue.get("message")
        or issue.get("description")
        or issue.get("issue")
        or "Finding"
    )


def _compact_finding(issue: dict[str, Any]) -> dict[str, Any]:
    compact = {
        "check": _string(issue.get("check"), "unknown"),
        "severity": _string(issue.get("severity"), "unknown"),
        "title": _truncate_text(_issue_title(issue), max_chars=300),
    }

    optional_fields = [
        "message",
        "description",
        "visualization",
        "visualization_id",
        "challenge",
        "challenge_id",
        "wave_id",
        "active_wave",
        "url",
        "priority_score",
        "priority_rationale",
    ]

    for field in optional_fields:
        value = issue.get(field)
        if value is None or value == "":
            continue

        if isinstance(value, str):
            value = _truncate_text(value, max_chars=300)

        compact[field] = value

    fix_guidance = gamebus_fix_guidance_markdown_for_issue(issue)
    if fix_guidance:
        compact["deterministic_gamebus_fix_guidance"] = _truncate_text(
            fix_guidance,
            max_chars=1800,
        )

    gamebus_facts = gamebus_studio_facts_markdown_for_issue(issue)
    if gamebus_facts:
        compact["gamebus_studio_source_facts"] = _truncate_text(
            gamebus_facts,
            max_chars=1800,
        )

    return compact


def _top_findings(result: dict[str, Any], *, max_findings: int) -> list[dict[str, Any]]:
    issues = _as_list(result.get("prioritized_issues"))
    dict_issues = [issue for issue in issues if isinstance(issue, dict)]

    sorted_issues = sorted(
        dict_issues,
        key=lambda issue: (
            _severity_rank(issue),
            _active_wave_rank(issue),
            _string(issue.get("check")),
            _issue_title(issue),
        ),
    )

    return [_compact_finding(issue) for issue in sorted_issues[:max_findings]]


def _findings_by_check_summary(result: dict[str, Any]) -> dict[str, Any]:
    summary = _as_dict(result.get("summary"))
    issue_count_by_check = _as_dict(summary.get("issue_count_by_check"))

    return {
        str(check): int(count or 0)
        for check, count in sorted(issue_count_by_check.items())
    }


def _compact_challenges(snapshot: dict[str, Any], *, max_items: int) -> list[dict[str, Any]]:
    challenges = _as_list(snapshot.get("challenges"))
    compact: list[dict[str, Any]] = []

    for item in challenges[:max_items]:
        if not isinstance(item, dict):
            continue

        compact.append(
            _compact_item(
                item,
                fields=[
                    "id",
                    "name",
                    "description",
                    "visualization_id",
                    "target_points",
                    "success_next",
                    "failure_next",
                    "start",
                    "end",
                ],
                max_text_chars=250,
            )
        )

    return compact


def _compact_tasks(snapshot: dict[str, Any], *, max_items: int) -> list[dict[str, Any]]:
    tasks = _as_list(snapshot.get("tasks"))
    compact: list[dict[str, Any]] = []

    for item in tasks[:max_items]:
        if not isinstance(item, dict):
            continue

        compact.append(
            _compact_item(
                item,
                fields=[
                    "id",
                    "name",
                    "description",
                    "challenge_id",
                    "points",
                    "conditions",
                    "activity_scheme_default",
                    "activity_schemes_allowed",
                ],
                max_text_chars=250,
            )
        )

    return compact


def _compact_visualizations(snapshot: dict[str, Any], *, max_items: int) -> list[dict[str, Any]]:
    visualizations = _as_list(snapshot.get("visualizations"))
    compact: list[dict[str, Any]] = []

    for item in visualizations[:max_items]:
        if not isinstance(item, dict):
            continue

        compact.append(
            _compact_item(
                item,
                fields=[
                    "id",
                    "name",
                    "wave_id",
                    "groups",
                    "menu_order",
                    "tabbar_order",
                    "show_in_menu",
                    "show_in_tabbar",
                ],
                max_text_chars=200,
            )
        )

    return compact


def _compact_waves(snapshot: dict[str, Any], *, max_items: int) -> list[dict[str, Any]]:
    waves = _as_list(snapshot.get("waves"))
    compact: list[dict[str, Any]] = []

    for item in waves[:max_items]:
        if not isinstance(item, dict):
            continue

        compact.append(
            _compact_item(
                item,
                fields=["id", "name", "start", "end"],
                max_text_chars=200,
            )
        )

    return compact


def _compact_transitions(snapshot: dict[str, Any], *, max_items: int) -> list[dict[str, Any]]:
    transitions = _as_list(snapshot.get("transitions"))
    compact: list[dict[str, Any]] = []

    for item in transitions[:max_items]:
        if not isinstance(item, dict):
            continue

        compact.append(
            _compact_item(
                item,
                fields=[
                    "source_challenge_id",
                    "target_challenge_id",
                    "transition_type",
                ],
            )
        )

    return compact


def build_llm_context(
    result: dict[str, Any],
    *,
    max_findings: int = 10,
    max_waves: int = 20,
    max_visualizations: int = 30,
    max_challenges: int = 40,
    max_tasks: int = 50,
    max_transitions: int = 80,
) -> dict[str, Any]:
    """
    Build compact context for future LLM-supported agents.

    This context is intentionally smaller than the full workbook. It is safe to
    pass into prompts because it contains summaries and selected rows, not the
    entire Excel export.
    """
    summary = _as_dict(result.get("summary"))
    snapshot = _as_dict(result.get("campaign_snapshot"))
    counts = _as_dict(snapshot.get("counts"))

    return {
        "campaign": {
            "campaign_name": result.get("campaign_name") or snapshot.get("campaign_name"),
            "file_name": result.get("file_name") or snapshot.get("file_name"),
            "source_file": result.get("source_file") or snapshot.get("source_file"),
        },
        "analysis": {
            "checks_run": _as_list(result.get("checks_run")),
            "total_issues": int(summary.get("total_issues", 0) or 0),
            "passed_checks": _as_list(summary.get("passed_checks")),
            "failed_checks": _as_list(summary.get("failed_checks")),
            "errored_checks": _as_list(summary.get("errored_checks")),
            "issue_count_by_check": _findings_by_check_summary(result),
            "severity_counts": _as_dict(summary.get("severity_counts")),
        },
        "top_findings": _top_findings(result, max_findings=max_findings),
        "campaign_structure": {
            "counts": counts,
            "waves": _compact_waves(snapshot, max_items=max_waves),
            "visualizations": _compact_visualizations(snapshot, max_items=max_visualizations),
            "challenges": _compact_challenges(snapshot, max_items=max_challenges),
            "tasks": _compact_tasks(snapshot, max_items=max_tasks),
            "transitions": _compact_transitions(snapshot, max_items=max_transitions),
            "task_summary_by_challenge": _as_dict(snapshot.get("task_summary_by_challenge")),
        },
        "warnings": {
            "snapshot_extraction_warnings": _as_list(snapshot.get("extraction_warnings")),
        },
        "context_limits": {
            "max_findings": max_findings,
            "max_waves": max_waves,
            "max_visualizations": max_visualizations,
            "max_challenges": max_challenges,
            "max_tasks": max_tasks,
            "max_transitions": max_transitions,
        },
    }


def format_llm_context_markdown(context: dict[str, Any]) -> str:
    """
    Render compact context as prompt-ready Markdown.

    Future LLM agents can use either the structured dict or this Markdown form.
    """
    campaign = _as_dict(context.get("campaign"))
    analysis = _as_dict(context.get("analysis"))
    structure = _as_dict(context.get("campaign_structure"))
    counts = _as_dict(structure.get("counts"))
    findings = _as_list(context.get("top_findings"))
    warnings = _as_dict(context.get("warnings"))

    lines: list[str] = []

    lines.append("# Campaign context")
    lines.append(f"- Campaign name: {campaign.get('campaign_name') or 'Unknown'}")
    lines.append(f"- File name: {campaign.get('file_name') or 'Unknown'}")

    lines.append("")
    lines.append("# Analysis summary")
    lines.append(f"- Checks run: {', '.join(str(x) for x in analysis.get('checks_run', []))}")
    lines.append(f"- Total findings: {analysis.get('total_issues', 0)}")
    lines.append(f"- Failed checks: {', '.join(str(x) for x in analysis.get('failed_checks', [])) or 'None'}")
    lines.append(f"- Errored checks: {', '.join(str(x) for x in analysis.get('errored_checks', [])) or 'None'}")

    issue_count_by_check = _as_dict(analysis.get("issue_count_by_check"))
    if issue_count_by_check:
        lines.append("")
        lines.append("# Issue counts by check")
        for check, count in issue_count_by_check.items():
            lines.append(f"- {check}: {count}")

    lines.append("")
    lines.append("# Campaign structure")
    lines.append(f"- Waves: {counts.get('waves', 0)}")
    lines.append(f"- Visualizations: {counts.get('visualizations', 0)}")
    lines.append(f"- Challenges/levels: {counts.get('challenges', 0)}")
    lines.append(f"- Tasks: {counts.get('tasks', 0)}")
    lines.append(f"- Transitions: {counts.get('transitions', 0)}")

    if findings:
        lines.append("")
        lines.append("# Top findings")
        for idx, finding in enumerate(findings, start=1):
            title = finding.get("title") or "Finding"
            check = finding.get("check") or "unknown"
            severity = finding.get("severity") or "unknown"
            lines.append(f"{idx}. [{severity}] {title} (check: {check})")

            message = finding.get("message")
            if message:
                lines.append(f"   - Message: {message}")

            visualization = finding.get("visualization")
            if visualization:
                lines.append(f"   - Visualization: {visualization}")

            visualization_id = finding.get("visualization_id")
            if visualization_id not in (None, ""):
                lines.append(f"   - Visualization ID: {visualization_id}")

            challenge = finding.get("challenge")
            if challenge:
                lines.append(f"   - Challenge: {challenge}")

            challenge_id = finding.get("challenge_id")
            if challenge_id not in (None, ""):
                lines.append(f"   - Challenge ID: {challenge_id}")

            wave_id = finding.get("wave_id")
            if wave_id not in (None, ""):
                lines.append(f"   - Wave ID: {wave_id}")

            priority_score = finding.get("priority_score")
            if priority_score not in (None, ""):
                lines.append(f"   - Priority score: {priority_score}")

            priority_rationale = finding.get("priority_rationale")
            if priority_rationale:
                lines.append(f"   - Priority rationale: {priority_rationale}")

            url = finding.get("url")
            if url:
                lines.append(f"   - GameBus Studio URL: {url}")

            fix_guidance = finding.get("deterministic_gamebus_fix_guidance")
            if fix_guidance:
                lines.append("   - Deterministic GameBus Studio fix guidance:")
                for guidance_line in str(fix_guidance).splitlines():
                    if guidance_line.strip():
                        lines.append(f"     {guidance_line}")
                    else:
                        lines.append("")

            gamebus_facts = finding.get("gamebus_studio_source_facts")
            if gamebus_facts:
                lines.append("   - GameBus Studio source facts:")
                for fact_line in str(gamebus_facts).splitlines():
                    if fact_line.strip():
                        lines.append(f"     {fact_line}")
                    else:
                        lines.append("")

    extraction_warnings = _as_list(warnings.get("snapshot_extraction_warnings"))
    if extraction_warnings:
        lines.append("")
        lines.append("# Snapshot extraction warnings")
        for warning in extraction_warnings:
            lines.append(f"- {warning}")

    return "\n".join(lines)
