from __future__ import annotations

from collections import defaultdict
from typing import Any

import streamlit as st

from campaign_assistant.checker.gamebus_fix_guidance import gamebus_fix_guidance_markdown_for_issue
from campaign_assistant.checker.schema import FRIENDLY_CHECK_NAMES
from campaign_assistant.checker.check_metadata import PRIORITY_HINT


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    return dict(result.get("summary", {}) or {})


def _normalize_issue(issue: dict[str, Any], fallback_check: str | None = None) -> dict[str, Any]:
    normalized = dict(issue)
    if fallback_check and not normalized.get("check"):
        normalized["check"] = fallback_check
    return normalized


def _collect_issues(result: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Collect issues from the current checker result.

    Supports both:
    - result["prioritized_issues"]
    - result["issues_by_check"]
    """
    issues: list[dict[str, Any]] = []

    prioritized = result.get("prioritized_issues", []) or []
    if isinstance(prioritized, list):
        for item in prioritized:
            if isinstance(item, dict):
                issues.append(_normalize_issue(item))

    if issues:
        return issues

    by_check = result.get("issues_by_check", {}) or {}
    if isinstance(by_check, dict):
        for check_id, check_issues in by_check.items():
            if not isinstance(check_issues, list):
                continue
            for item in check_issues:
                if isinstance(item, dict):
                    issues.append(_normalize_issue(item, fallback_check=str(check_id)))

    return issues


def _severity(issue: dict[str, Any]) -> str:
    return str(
        issue.get("severity")
        or issue.get("priority")
        or issue.get("level")
        or "unknown"
    ).lower()


def _severity_rank(issue: dict[str, Any]) -> int:
    severity = _severity(issue)
    if severity in {"critical", "high"}:
        return 0
    if severity == "medium":
        return 1
    if severity == "low":
        return 2
    return 3


def _issue_title(issue: dict[str, Any]) -> str:
    return str(
        issue.get("title")
        or issue.get("message")
        or issue.get("description")
        or issue.get("issue")
        or "Finding"
    )


def _issue_message(issue: dict[str, Any]) -> str:
    title = _issue_title(issue)
    message = str(
        issue.get("message")
        or issue.get("description")
        or issue.get("details")
        or ""
    )

    if message and message != title:
        return message
    return ""


def _check_label(check_id: str) -> str:
    return FRIENDLY_CHECK_NAMES.get(check_id, check_id)


def _location_lines(issue: dict[str, Any]) -> list[str]:
    fields = [
        ("Sheet", issue.get("sheet")),
        ("Row", issue.get("row")),
        ("Visualization", issue.get("visualization")),
        ("Visualization ID", issue.get("visualization_id")),
        ("Challenge", issue.get("challenge")),
        ("Challenge ID", issue.get("challenge_id")),
        ("Wave ID", issue.get("wave_id")),
        ("URL", issue.get("url")),
    ]

    lines: list[str] = []
    for label, value in fields:
        if value is None or value == "":
            continue
        lines.append(f"**{label}:** {value}")

    return lines


def _assistant_prompt_for_issue(issue: dict[str, Any]) -> str:
    title = _issue_title(issue)
    severity = _severity(issue)
    check = str(issue.get("check") or "unknown")

    parts = [
        "Explain this campaign finding and suggest what I should inspect next.",
        "",
        f"Check: {check}",
        f"Severity: {severity}",
        f"Finding: {title}",
    ]

    message = _issue_message(issue)
    if message:
        parts.append(f"Message: {message}")

    visualization = issue.get("visualization")
    if visualization:
        parts.append(f"Visualization: {visualization}")

    challenge = issue.get("challenge")
    if challenge:
        parts.append(f"Challenge: {challenge}")

    challenge_id = issue.get("challenge_id")
    if challenge_id not in (None, ""):
        parts.append(f"Challenge ID: {challenge_id}")

    wave_id = issue.get("wave_id")
    if wave_id not in (None, ""):
        parts.append(f"Wave ID: {wave_id}")

    fix_guidance = gamebus_fix_guidance_markdown_for_issue(issue)
    if fix_guidance:
        parts.extend(
            [
                "",
                "Deterministic GameBus Studio fix guidance:",
                fix_guidance,
            ]
        )

    return "\n".join(parts)


def _store_assistant_prompt_for_issue(issue: dict[str, Any]) -> None:
    st.session_state["assistant_prefill_prompt"] = _assistant_prompt_for_issue(issue)
    st.session_state["assistant_notice"] = (
        "This question was prepared from a finding."
    )

    st.session_state["requested_workflow_page"] = "Assistant"

    try:
        st.query_params["page"] = "assistant"
    except Exception:
        pass


def _severity_badge(severity: str) -> str:
    severity = severity.lower()
    if severity in {"critical", "high"}:
        return "🔴 High"
    if severity == "medium":
        return "🟠 Medium"
    if severity == "low":
        return "🟡 Low"
    return "⚪ Unspecified"


def _count_by_severity(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0}

    for issue in issues:
        severity = _severity(issue)
        if severity in {"critical", "high"}:
            counts["high"] += 1
        elif severity == "medium":
            counts["medium"] += 1
        elif severity == "low":
            counts["low"] += 1
        else:
            counts["unknown"] += 1

    return counts


def _count_by_check(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)

    for issue in issues:
        check = str(issue.get("check") or "unknown")
        counts[check] += 1

    return dict(counts)


def render_findings_overview_panel(result: dict[str, Any]) -> None:
    issues = _collect_issues(result)
    summary = _summary(result)

    total = int(summary.get("total_issues", len(issues)) or 0)
    severity_counts = _count_by_severity(issues)
    check_counts = _count_by_check(issues)

    st.subheader("Findings overview", help=PRIORITY_HINT)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", total)
    c2.metric("High", severity_counts["high"])
    c3.metric("Medium", severity_counts["medium"])
    c4.metric("Low", severity_counts["low"])

    if total == 0:
        st.success(
            "No issues were found by the selected checks. This does not prove that "
            "the campaign is theoretically optimal or deployment-ready."
        )
        return

    st.warning(
        "Issues were found. Start with high-priority findings, then review medium- "
        "and low-priority findings."
    )

    if check_counts:
        with st.expander("Issue counts by check", expanded=False):
            for check_id, count in sorted(check_counts.items(), key=lambda item: item[0]):
                st.markdown(f"- **{_check_label(check_id)}**: {count}")


def render_issues_panel(result: dict[str, Any]) -> None:
    issues = _collect_issues(result)

    if not issues:
        st.info("No findings to display.")
        return

    checks = sorted({str(issue.get("check") or "unknown") for issue in issues})
    check_options = ["All"] + [_check_label(check) for check in checks]
    check_label_to_id = {"All": "All"}
    check_label_to_id.update({_check_label(check): check for check in checks})

    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])

    with filter_col1:
        severity_filter = st.selectbox(
            "Severity",
            options=["All", "High", "Medium", "Low", "Unspecified"],
            index=0,
            key="findings-severity-filter",
        )

    with filter_col2:
        selected_check_label = st.selectbox(
            "Check",
            options=check_options,
            index=0,
            key="findings-check-filter",
        )

    with filter_col3:
        query = st.text_input(
            "Search findings",
            value="",
            key="findings-search-query",
            placeholder="Search by message, challenge, visualization, or check",
        ).strip().lower()

    selected_check = check_label_to_id[selected_check_label]

    filtered = sorted(issues, key=_severity_rank)

    if severity_filter != "All":
        selected = severity_filter.lower()
        if selected == "high":
            filtered = [issue for issue in filtered if _severity(issue) in {"critical", "high"}]
        elif selected == "unspecified":
            filtered = [issue for issue in filtered if _severity(issue) not in {"critical", "high", "medium", "low"}]
        else:
            filtered = [issue for issue in filtered if _severity(issue) == selected]

    if selected_check != "All":
        filtered = [issue for issue in filtered if str(issue.get("check") or "unknown") == selected_check]

    if query:
        def _matches(issue: dict[str, Any]) -> bool:
            haystack = " ".join(str(value) for value in issue.values() if value is not None).lower()
            return query in haystack

        filtered = [issue for issue in filtered if _matches(issue)]

    st.caption(f"Showing {len(filtered)} of {len(issues)} findings.")

    if not filtered:
        st.info("No findings match the selected filters.")
        return

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for issue in filtered:
        grouped[str(issue.get("check") or "unknown")].append(issue)

    for check_id, check_issues in grouped.items():
        with st.expander(f"{_check_label(check_id)} — {len(check_issues)} finding(s)", expanded=True):
            for idx, issue in enumerate(check_issues, start=1):
                title = _issue_title(issue)
                message = _issue_message(issue)
                severity = _severity(issue)

                st.markdown(f"#### {idx}. {_severity_badge(severity)} — {title}")

                if message:
                    st.write(message)

                location = _location_lines(issue)
                if location:
                    st.markdown("\n".join(f"- {line}" for line in location))

                fix_guidance = gamebus_fix_guidance_markdown_for_issue(issue)
                if fix_guidance:
                    with st.expander("How to fix this in GameBus Studio", expanded=False):
                        st.markdown(fix_guidance)

                button_key = (
                    f"ask-assistant-{check_id}-"
                    f"{issue.get('challenge_id', 'none')}-"
                    f"{idx}"
                )

                if st.button(
                        "Ask Assistant about this",
                        key=button_key,
                        use_container_width=False,
                ):
                    _store_assistant_prompt_for_issue(issue)
                    st.rerun()

                with st.expander("Raw finding details", expanded=False):
                    st.json(issue)

                st.divider()
