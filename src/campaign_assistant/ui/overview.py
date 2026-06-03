from __future__ import annotations
from typing import Any

import streamlit as st

def _campaign_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    snapshot = result.get("campaign_snapshot", {}) or {}
    return dict(snapshot) if isinstance(snapshot, dict) else {}


def _summary_counts(result: dict[str, Any]) -> tuple[int, int, int, int]:
    summary = dict(result.get("summary", {}) or {})
    total = int(summary.get("total_issues", 0) or 0)

    severity_counts = dict(summary.get("severity_counts", {}) or {})
    high = int(severity_counts.get("high", 0) or severity_counts.get("High", 0) or 0)
    medium = int(severity_counts.get("medium", 0) or severity_counts.get("Medium", 0) or 0)
    low = int(severity_counts.get("low", 0) or severity_counts.get("Low", 0) or 0)

    if total and not any([high, medium, low]):
        prioritized = result.get("prioritized_issues", []) or []
        for item in prioritized:
            severity = str(item.get("severity", item.get("priority", ""))).lower()
            if severity in {"critical", "high"}:
                high += 1
            elif severity == "medium":
                medium += 1
            elif severity == "low":
                low += 1

    return total, high, medium, low


def _failed_checks(result: dict[str, Any]) -> list[str]:
    summary = dict(result.get("summary", {}) or {})
    failed = summary.get("failed_checks", [])
    if isinstance(failed, list):
        return [str(item) for item in failed]
    return []


def _top_priorities(result: dict[str, Any], limit: int = 5) -> list[str]:
    issues = result.get("prioritized_issues", []) or []
    labels: list[str] = []

    for item in issues[:limit]:
        if not isinstance(item, dict):
            continue

        label = (
            item.get("title")
            or item.get("message")
            or item.get("description")
            or item.get("issue")
            or item.get("check")
            or "Finding"
        )
        labels.append(str(label))

    return labels



def _render_campaign_snapshot_summary(result: dict[str, Any]) -> None:
    snapshot = _campaign_snapshot(result)
    counts = dict(snapshot.get("counts", {}) or {})
    warnings = list(snapshot.get("extraction_warnings", []) or [])

    if not snapshot:
        return

    st.markdown("### Campaign structure")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Waves", counts.get("waves", 0))
    c2.metric("Visualizations", counts.get("visualizations", 0))
    c3.metric("Challenges", counts.get("challenges", 0))
    c4.metric("Tasks", counts.get("tasks", 0))
    c5.metric("Transitions", counts.get("transitions", 0))

    if warnings:
        with st.expander("Snapshot extraction warnings", expanded=False):
            for warning in warnings:
                st.warning(str(warning))




def render_analysis_overview(result: dict[str, Any], show_title: bool = True) -> None:
    if show_title:
        st.subheader("Overview")

    file_name = result.get("file_name") or result.get("source_file") or "Current campaign"
    checks_run = result.get("checks_run", []) or []
    total, high, medium, low = _summary_counts(result)

    st.markdown("### Current campaign")
    st.write(f"**File:** {file_name}")
    st.write(f"**Checks run:** {len(checks_run)}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total issues", total)
    c2.metric("High priority", high)
    c3.metric("Medium priority", medium)
    c4.metric("Low priority", low)

    st.markdown("### Status")

    _render_campaign_snapshot_summary(result)

    if total > 0:
        st.warning(
            "Issues found. Review the high-priority findings before deployment. "
            "Go to the Findings page and filter by high priority, or start with "
            "the Top priorities list below."
        )
    else:
        st.success(
            "No issues were found by the selected checks. This does not prove that "
            "the campaign is theoretically optimal or deployment-ready; it only means "
            "that the selected export-level checks did not detect problems."
        )

    failed_checks = _failed_checks(result)
    top_priorities = _top_priorities(result)

    if failed_checks or top_priorities:
        left, right = st.columns(2)

        with left:
            st.markdown("### Failed checks")
            if failed_checks:
                for check in failed_checks:
                    st.markdown(f"- {check}")
            else:
                st.caption("No failed checks.")

        with right:
            st.markdown("### Top priorities")
            if top_priorities:
                for idx, label in enumerate(top_priorities, start=1):
                    st.markdown(f"{idx}. {label}")
            else:
                st.caption("No prioritized findings.")

    st.markdown("### Actions")
    st.caption(
        "Use the Findings page to inspect issues in detail, or ask the Assistant "
        "to explain a finding and suggest what to inspect."
    )