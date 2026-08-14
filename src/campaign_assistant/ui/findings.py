from __future__ import annotations

import re

from collections import defaultdict
from typing import Any
from collections.abc import Iterable

import streamlit as st

from campaign_assistant.checker.gamebus_fix_guidance import gamebus_fix_guidance_markdown_for_issue
from campaign_assistant.checker.schema import (
    CHECK_PICKER_CHECKS,
    FRIENDLY_CHECK_NAMES,
)
from campaign_assistant.checker.check_metadata import PRIORITY_HINT


_QUOTED_VALUE_PATTERN = re.compile(r"'([^'\n]+)'")


def _format_meaningful_values(text: str) -> str:
    def _replacement(match: re.Match[str]) -> str:
        value = match.group(1).replace("`", r"\`")
        return f"`{value}`"

    return _QUOTED_VALUE_PATTERN.sub(
        _replacement,
        str(text or ""),
    )


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


def _severity_indicator(severity: str) -> str:
    severity = severity.lower()

    if severity in {"critical", "high"}:
        return "🔴"
    if severity == "medium":
        return "🟠"
    if severity == "low":
        return "🟡"

    return "⚪"


def _severity_badge(severity: str) -> str:
    label = {
        "critical": "High",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
    }.get(severity.lower(), "No severity")

    return f"{_severity_indicator(severity)} {label}"



def _issue_title(issue: dict[str, Any]) -> str:
    return str(
        issue.get("title")
        or issue.get("message")
        or issue.get("description")
        or issue.get("issue")
        or "Finding"
    )


def _issue_heading_and_details(
    issue: dict[str, Any],
) -> tuple[str, str]:
    message = _issue_message(issue).strip()

    if not message:
        return _issue_title(issue).strip(), ""

    # Prefer a sentence boundary; multiline findings may use the first line.
    boundary = re.search(
        r"(?<=[.!?])\s+|\n+",
        message,
    )

    if boundary is None:
        return message.rstrip(), ""

    heading = message[:boundary.start()].strip()
    details = message[boundary.end():].strip()

    return heading, details


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


def _ordered_check_ids(check_ids: Iterable[str]) -> list[str]:
    available = {str(check_id) for check_id in check_ids}

    ordered = [
        check_id
        for check_id in CHECK_PICKER_CHECKS
        if check_id in available
    ]

    ordered.extend(
        sorted(available - set(CHECK_PICKER_CHECKS))
    )

    return ordered


def _filter_id(value: Any) -> str:
    """Normalize Excel-derived IDs for reliable UI filtering."""
    if value is None:
        return ""

    text = str(value).strip()

    # Excel/pandas may expose integer IDs as strings such as "123.0".
    if text.endswith(".0"):
        try:
            return str(int(float(text)))
        except ValueError:
            pass

    return text


def _truncate_label(value: str, max_length: int = 40) -> str:
    value = value.strip()

    if len(value) <= max_length:
        return value

    return value[: max_length - 1].rstrip() + "…"


def _wave_filter_options(issues: list[dict[str, Any]]) -> list[tuple[str, str]]:
    waves: dict[str, bool] = {}

    for issue in issues:
        wave_id = _filter_id(issue.get("wave_id"))
        if not wave_id:
            continue

        is_active = bool(issue.get("active_wave"))
        waves[wave_id] = waves.get(wave_id, False) or is_active

    def _sort_key(item: tuple[str, bool]) -> tuple[int, str]:
        wave_id, _ = item
        try:
            return (0, f"{int(wave_id):010d}")
        except ValueError:
            return (1, wave_id.lower())

    options: list[tuple[str, str]] = []

    for wave_id, is_active in sorted(waves.items(), key=_sort_key):
        label = f"Wave {wave_id}"
        if is_active:
            label += " (active)"
        options.append((wave_id, label))

    return options


def _visualization_filter_options(
    issues: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    visualizations: dict[str, str] = {}

    for issue in issues:
        visualization_id = _filter_id(issue.get("visualization_id"))
        visualization_name = str(issue.get("visualization") or "").strip()
        display_name = _truncate_label(visualization_name)

        if not visualization_id and not visualization_name:
            continue

        # Prefer the stable ID for filtering.
        key = visualization_id or visualization_name

        if visualization_name and visualization_id:
            label = f"{display_name} ({visualization_id})"
        elif visualization_name:
            label = display_name
        else:
            label = f"Visualization {visualization_id}"

        visualizations[key] = label

    return sorted(
        visualizations.items(),
        key=lambda item: item[1].lower(),
    )



def _issue_visualization_filter_key(issue: dict[str, Any]) -> str:
    visualization_id = _filter_id(issue.get("visualization_id"))
    if visualization_id:
        return visualization_id

    return str(issue.get("visualization") or "").strip()




def _location_lines(issue: dict[str, Any]) -> list[str]:
    def formatted(value: Any) -> str:
        escaped = str(value).replace("`", r"\`")
        return f"`{escaped}`"

    ("Wave", issue.get("wave_id")),
    ("Visualization", issue.get("visualization")),
    ("Visualization ID", issue.get("visualization_id")),
    ("Challenge", issue.get("challenge")),
    ("Challenge ID", issue.get("challenge_id")),

    fields = [
        (
            "Visualization",
            issue.get("visualization"),
            issue.get("visualization_id"),
        ),
        (
            "Challenge",
            issue.get("challenge"),
            issue.get("challenge_id"),
        ),
    ]

    lines: list[str] = []

    for label, name, identifier in fields:
        values: list[str] = []

        if name is not None and name != "":
            values.append(formatted(name))

        if identifier is not None and identifier != "":
            values.append(f"id: {formatted(identifier)}")

        if values:
            lines.append(f"**{label}:** {', '.join(values)}")

    wave_id = issue.get("wave_id")
    if wave_id is not None and wave_id != "":
        lines.append(f"**Wave:** {formatted(wave_id)}")

    return lines


def _assistant_prompt_for_issue(issue: dict[str, Any]) -> str:
    title = _issue_title(issue)
    severity = _severity(issue)
    check = str(issue.get("check") or "unknown")

    parts = [
        "Explain this campaign finding.",
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

    return "\n".join(parts)


def _store_assistant_prompt_for_issue(issue: dict[str, Any]) -> None:
    focused_finding = dict(issue)

    fix_guidance = gamebus_fix_guidance_markdown_for_issue(issue)
    if fix_guidance:
        focused_finding["deterministic_gamebus_fix_guidance"] = fix_guidance

    st.session_state["assistant_focused_finding"] = focused_finding
    st.session_state["assistant_prefill_prompt"] = _assistant_prompt_for_issue(issue)

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
    return "⚪ No severity"


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
            "No findings were detected by the selected checks. This does not prove that "
            "the campaign is theoretically optimal or deployment-ready."
        )
        return

    st.warning(
        "Findings were detected. Start with high-priority findings, then review "
        "medium- and low-priority findings."
    )

    st.caption(
        "Use the filters below to narrow the list. Ask the Assistant when you need "
        "additional explanation for a specific finding."
    )

    if check_counts:
        with st.expander("Finding counts by check", expanded=False):
            for check_id in _ordered_check_ids(check_counts):
                st.markdown(
                    f"- **{_check_label(check_id)}**: {check_counts[check_id]}"
                )


def render_issues_panel(result: dict[str, Any]) -> None:
    issues = _collect_issues(result)

    if not issues:
        st.info("No findings to display.")
        return

    available_checks = {
        str(issue.get("check") or "unknown")
        for issue in issues
    }

    checks = _ordered_check_ids(available_checks)

    check_options = ["All"] + [_check_label(check) for check in checks]
    check_label_to_id = {"All": "All"}
    check_label_to_id.update({_check_label(check): check for check in checks})

    wave_options = _wave_filter_options(issues)
    wave_labels = dict(wave_options)

    visualization_options = _visualization_filter_options(issues)
    visualization_labels = dict(visualization_options)

    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)

    with filter_col1:
        severity_options = ["All", "High", "Medium", "Low"]

        has_unclassified_severity = any(
            _severity(issue) not in {"critical", "high", "medium", "low"}
            for issue in issues
        )

        if has_unclassified_severity:
            severity_options.append("No severity")

        severity_filter = st.selectbox(
            "Severity",
            options=severity_options,
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
        selected_wave = st.selectbox(
            "Wave",
            options=[""] + list(wave_labels),
            format_func=lambda value: (
                "All waves" if value == "" else wave_labels[value]
            ),
            key="findings-wave-filter",
        )

    with filter_col4:
        selected_visualization = st.selectbox(
            "Visualization",
            options=[""] + list(visualization_labels),
            format_func=lambda value: (
                "All visualizations"
                if value == ""
                else visualization_labels[value]
            ),
            key="findings-visualization-filter",
        )

    with filter_col5:
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
        elif selected == "no severity":
            filtered = [issue for issue in filtered if _severity(issue) not in {"critical", "high", "medium", "low"}]
        else:
            filtered = [issue for issue in filtered if _severity(issue) == selected]

    if selected_check != "All":
        filtered = [
            issue
            for issue in filtered
            if str(issue.get("check") or "unknown") == selected_check
        ]

    if selected_wave:
        filtered = [
            issue
            for issue in filtered
            if _filter_id(issue.get("wave_id")) == selected_wave
        ]

    if selected_visualization:
        filtered = [
            issue
            for issue in filtered
            if _issue_visualization_filter_key(issue) == selected_visualization
        ]

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

    expand_group = len(grouped) == 1

    for check_id in _ordered_check_ids(grouped):
        check_issues = grouped[check_id]

        group_severity = _severity(
            min(check_issues, key=_severity_rank)
        )
        group_badge = _severity_badge(group_severity)

        with st.expander(
                (
                        f"{group_badge} - {_check_label(check_id)}: "
                        f"{len(check_issues)} finding(s)"
                ),
                expanded=expand_group,
        ):
            for idx, issue in enumerate(check_issues, start=1):
                heading, details = _issue_heading_and_details(issue)
                severity = _severity(issue)

                formatted_heading = _format_meaningful_values(heading)

                st.markdown(
                    f"#### {idx}. {_severity_indicator(severity)} "
                    f"{formatted_heading}"
                )

                if details:
                    st.markdown(
                        _format_meaningful_values(details)
                    )

                location = _location_lines(issue)
                if location:
                    st.markdown("\n".join(f"- {line}" for line in location))

                studio_url = str(issue.get("url") or "").strip()
                if studio_url:
                    st.link_button(
                        "Open in GameBus Studio",
                        studio_url,
                    )

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
                        "Ask Assistant about this finding",
                        key=button_key,
                        use_container_width=False,
                ):
                    _store_assistant_prompt_for_issue(issue)
                    st.rerun()

                # with st.expander("Raw finding details", expanded=False):
                #     st.json(issue)

                st.divider()
