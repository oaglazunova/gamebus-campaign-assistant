from __future__ import annotations
from typing import Any

import base64
import re

import streamlit as st

from campaign_assistant.checker.schema import (
    CHECK_PICKER_CHECKS,
    FRIENDLY_CHECK_NAMES,
    SEVERITY_BY_CHECK,
)
from campaign_assistant.diagram import build_campaign_flow_svg
from campaign_assistant.checker.check_metadata import PRIORITY_HINT



_FINDINGS_PAGE_SIZE = 30


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


def _severity_indicator(severity: str) -> str:
    severity = str(severity or "").lower()

    if severity == "high":
        return "🔴 High"
    if severity == "medium":
        return "🟠 Medium"
    if severity == "low":
        return "🟡 Low"

    return "⚪ No severity"


def _ordered_checks_with_findings(
    result: dict[str, Any],
) -> list[str]:
    summary = dict(result.get("summary", {}) or {})
    counts = dict(summary.get("issue_count_by_check", {}) or {})

    available = {
        str(check_id)
        for check_id, count in counts.items()
        if int(count or 0) > 0
    }

    # Preserve failed checks if an older result lacks complete count data.
    available.update(_failed_checks(result))

    order = {
        check_id: index
        for index, check_id in enumerate(CHECK_PICKER_CHECKS)
    }
    severity_order = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    return sorted(
        available,
        key=lambda check_id: (
            severity_order.get(
                SEVERITY_BY_CHECK.get(check_id, ""),
                3,
            ),
            order.get(check_id, len(order)),
            check_id,
        ),
    )


def _render_findings_by_check_card(
    result: dict[str, Any],
) -> None:
    summary = dict(result.get("summary", {}) or {})
    counts = dict(summary.get("issue_count_by_check", {}) or {})
    checks = _ordered_checks_with_findings(result)

    st.markdown("#### Findings by check")

    if not checks:
        st.caption("No selected checks produced findings.")
        return

    for check_id in checks:
        label = FRIENDLY_CHECK_NAMES.get(check_id, check_id)
        severity = SEVERITY_BY_CHECK.get(check_id, "")
        count = int(counts.get(check_id, 0) or 0)
        count_label = "finding" if count == 1 else "findings"

        st.markdown(
            f"- {_severity_indicator(severity)} — "
            f"**{label}** — {count} {count_label}"
        )



def _go_to_findings() -> None:
    st.session_state["requested_workflow_page"] = "Findings"
    st.rerun()


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



def _safe_file_stem(value: Any, default: str = "campaign") -> str:
    text = str(value or default).strip()
    allowed = []

    for char in text:
        if char.isalnum() or char in {"-", "_"}:
            allowed.append(char)
        elif char.isspace():
            allowed.append("_")

    cleaned = "".join(allowed).strip("_")
    return cleaned or default


def _svg_data_uri(svg: str) -> str:
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _svg_viewbox_size(svg: str) -> tuple[int, int] | None:
    match = re.search(r'viewBox="0 0 ([0-9.]+) ([0-9.]+)"', svg)
    if not match:
        return None

    try:
        return int(float(match.group(1))), int(float(match.group(2)))
    except Exception:
        return None


def _diagram_preview_height(svg: str) -> int:
    size = _svg_viewbox_size(svg)
    if not size:
        return 520

    width, height = size
    if width <= 0:
        return 520

    # Approximate Streamlit content width. This avoids huge empty iframe space
    # for wide-but-short diagrams.
    estimated_render_width = 920
    scaled_height = int((height / width) * estimated_render_width)

    return max(240, min(620, scaled_height))



@st.dialog(
    "Campaign flow diagram",
    width="small",
)
def _render_flow_diagram_dialog(
    result: dict[str, Any],
) -> None:
    snapshot = _campaign_snapshot(result)
    counts = dict(
        snapshot.get("counts", {}) or {}
    )

    challenge_count = int(
        counts.get("challenges", 0) or 0
    )

    campaign_stem = _safe_file_stem(
        snapshot.get("campaign_name")
        or result.get("campaign_name")
        or result.get("file_name")
        or "campaign"
    )

    with st.spinner(
        "Creating campaign flow diagram..."
    ):
        svg = build_campaign_flow_svg(
            snapshot,
            max_nodes=(
                challenge_count
                if challenge_count > 0
                else 120
            ),
            show_edge_labels=False,
        )

    data_uri = _svg_data_uri(str(svg))
    download_name = (
        f"{campaign_stem}_flow_diagram.svg"
    )

    diagram_size = _svg_viewbox_size(
        str(svg)
    )

    if diagram_size:
        diagram_width, _diagram_height = (
            diagram_size
        )
    else:
        diagram_width = 900

    dialog_width = min(
        max(640, diagram_width + 80),
        1050,
    )

    st.markdown(
        f"""
        <style>
            [data-testid="stModal"] [role="dialog"] {{
                width: min(
                    {dialog_width}px,
                    88vw
                ) !important;

                max-width: min(
                    {dialog_width}px,
                    88vw
                ) !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.iframe(
        f"""
        <div class="diagram-dialog-content">
            <div class="diagram-toolbar">
                <a
                    class="diagram-button"
                    href="{data_uri}"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    Open in new tab
                </a>

                <a
                    class="diagram-button"
                    href="{data_uri}"
                    download="{download_name}"
                >
                    Download diagram
                </a>
            </div>

            <div class="diagram-preview">
                {svg}
            </div>
        </div>

        <style>
            .diagram-dialog-content {{
                width: 100%;
                box-sizing: border-box;
            }}

            .diagram-toolbar {{
                display: flex;
                justify-content: flex-end;
                gap: 8px;
                margin-bottom: 8px;
            }}

            .diagram-button {{
                display: inline-block;
                padding: 6px 10px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background: white;
                color: #222;
                font-family: Arial, sans-serif;
                font-size: 13px;
                line-height: 20px;
                text-decoration: none;
                box-shadow: 0 1px 3px rgba(0,0,0,0.10);
            }}

            .diagram-button:hover {{
                border-color: #999;
                background: #f7f7f7;
            }}

            .diagram-preview {{
                width: 100%;
                overflow: auto;
                display: flex;
                justify-content: center;
                align-items: flex-start;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 8px;
                background: #fafafa;
                box-sizing: border-box;
            }}
            
            .diagram-preview svg {{
                width: auto !important;
                max-width: 100% !important;
                height: auto !important;
                max-height: 650px;
                display: block;
                flex: 0 0 auto;
            }}
        </style>
        """,
        height=(
            _diagram_preview_height(str(svg))
            + 55
        ),
    )



def _render_current_campaign_compact(result: dict[str, Any]) -> None:
    snapshot = _campaign_snapshot(result)
    counts = dict(snapshot.get("counts", {}) or {})
    warnings = list(snapshot.get("extraction_warnings", []) or [])

    file_name = (
        result.get("file_name")
        or result.get("source_file")
        or snapshot.get("file_name")
        or "Current campaign"
    )

    checks_run = result.get("checks_run", []) or []
    total, high, medium, low = _summary_counts(result)

    campaign_stem = _safe_file_stem(
        snapshot.get("campaign_name")
        or result.get("campaign_name")
        or file_name
        or "campaign"
    )

    header_col, action_col = st.columns(
        [2.4, 1.2]
    )

    with header_col:
        st.markdown("### Current campaign")

    with action_col:
        create_diagram_clicked = st.button(
            "Create campaign flow diagram",
            key=(
                "create-campaign-flow-diagram-"
                f"{campaign_stem}"
            ),
            type="primary",
            use_container_width=True,
        )

    if create_diagram_clicked:
        _render_flow_diagram_dialog(result)

    st.caption(f"File: `{file_name}`")

    structure_cols = st.columns(5)
    structure_cols[0].metric("Waves", counts.get("waves", 0))
    structure_cols[1].metric("Visualizations", counts.get("visualizations", 0))
    structure_cols[2].metric("Challenges", counts.get("challenges", 0))
    structure_cols[3].metric("Tasks", counts.get("tasks", 0))
    structure_cols[4].metric("Transitions", counts.get("transitions", 0))

    st.markdown("### Analysis summary", help=PRIORITY_HINT)

    issue_cols = st.columns(5)
    issue_cols[0].metric("Checks", len(checks_run))
    issue_cols[1].metric("Findings", total)
    issue_cols[2].metric("High", high)
    issue_cols[3].metric("Medium", medium)
    issue_cols[4].metric("Low", low)

    st.caption(
        "Priority reflects finding severity and campaign timing. "
        "Findings affecting the active wave receive additional priority."
    )

    if warnings:
        with st.expander("Snapshot extraction warnings", expanded=False):
            for warning in warnings:
                st.warning(str(warning))


def _render_next_steps_card(result: dict[str, Any]) -> None:
    total, high, medium, low = _summary_counts(result)

    st.markdown("### Next steps")

    if total > 0:
        st.info(
            "Review the detected findings before considering the campaign ready. "
            "Start with high-priority findings, then continue with medium- and "
            "low-priority findings."
        )

        step_col1, step_col2 = st.columns([3, 1])

        with step_col1:
            if high > 0:
                st.markdown(
                    f"**{high} high-priority finding(s)** should be inspected first. "
                    f"The analysis also found {medium} medium- and {low} low-priority finding(s)."
                )
            else:
                st.markdown(
                    f"The analysis found **{total} finding(s)**: "
                    f"{medium} medium and {low} low priority."
                )

        with step_col2:
            if st.button(
                "Review findings",
                key="overview-review-findings",
                type="primary",
                use_container_width=True,
            ):
                _go_to_findings()

        st.caption(
            "Use the Assistant when you need additional explanation or guidance "
            "while reviewing a finding."
        )

    else:
        st.success(
            "No findings were detected by the selected checks."
        )

        st.markdown(
            "Review which checks were run and remember that a clean checker result "
            "does not prove that the campaign is fully ready, theory-aligned, usable, "
            "or effective."
        )

        if st.button(
            "Review checks and findings",
            key="overview-review-clean-findings",
            use_container_width=False,
        ):
            _go_to_findings()



def render_analysis_overview(result: dict[str, Any], show_title: bool = True) -> None:
    if show_title:
        st.subheader("Overview")

    _render_current_campaign_compact(result)

    _render_next_steps_card(result)

    _render_findings_by_check_card(result)