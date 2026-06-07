from __future__ import annotations
from typing import Any

import base64
import re

import streamlit as st
import streamlit.components.v1 as components

from campaign_assistant.checker.schema import FRIENDLY_CHECK_NAMES
from campaign_assistant.diagram import build_campaign_flow_svg


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


def _render_flow_diagram_panel(result: dict[str, Any]) -> None:
    snapshot = _campaign_snapshot(result)
    counts = dict(snapshot.get("counts", {}) or {})

    if not snapshot or not counts:
        return

    challenge_count = int(counts.get("challenges", 0) or 0)
    transition_count = int(counts.get("transitions", 0) or 0)

    campaign_stem = _safe_file_stem(
        snapshot.get("campaign_name")
        or result.get("campaign_name")
        or result.get("file_name")
        or "campaign"
    )

    svg_state_key = f"flow_diagram_svg_{campaign_stem}"

    with st.expander("Campaign flow diagram", expanded=False):
        st.caption(
            f"Creates a downloadable SVG from {challenge_count} challenge/level item(s) "
            f"and {transition_count} transition(s)."
        )

        svg = st.session_state.get(svg_state_key)

        col1, col2 = st.columns(2)

        with col1:
            create_clicked = st.button(
                "Create diagram",
                key=f"flow-diagram-create-{campaign_stem}",
                type="primary",
                use_container_width=True,
            )

        if create_clicked:
            svg = build_campaign_flow_svg(
                snapshot,
                max_nodes=challenge_count if challenge_count > 0 else 120,
                show_edge_labels=False,
            )
            st.session_state[svg_state_key] = svg

        svg = st.session_state.get(svg_state_key)

        with col2:
            st.download_button(
                "Download diagram",
                data=str(svg or "").encode("utf-8"),
                file_name=f"{campaign_stem}_flow_diagram.svg",
                mime="image/svg+xml",
                use_container_width=True,
                disabled=not bool(svg),
            )

        if not svg:
            return

        data_uri = _svg_data_uri(str(svg))

        components.html(
            f"""
            <div style="
                position: relative;
                width: 100%;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 8px;
                background: #fafafa;
                box-sizing: border-box;
            ">
                <a href="{data_uri}" target="_blank" rel="noopener noreferrer"
                   style="
                       position: absolute;
                       top: 12px;
                       right: 12px;
                       z-index: 10;
                       padding: 6px 10px;
                       border-radius: 6px;
                       border: 1px solid #ccc;
                       background: white;
                       color: #222;
                       font-family: Arial, sans-serif;
                       font-size: 13px;
                       text-decoration: none;
                       box-shadow: 0 1px 4px rgba(0,0,0,0.12);
                   ">
                   Open in new tab
                </a>

                <div style="
                    width: 100%;
                    overflow: hidden;
                    display: flex;
                    align-items: flex-start;
                    justify-content: center;
                ">
                    <div style="
                        width: 100%;
                    ">
                        {svg}
                    </div>
                </div>
            </div>

            <style>
                svg {{
                    width: 100% !important;
                    height: auto !important;
                    max-height: 560px;
                    display: block;
                }}
            </style>
            """,
            height=_diagram_preview_height(str(svg)),
            scrolling=False,
        )


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

    st.markdown("### Current campaign")
    st.caption(f"File: `{file_name}`")

    structure_cols = st.columns(5)
    structure_cols[0].metric("Waves", counts.get("waves", 0))
    structure_cols[1].metric("Visualizations", counts.get("visualizations", 0))
    structure_cols[2].metric("Challenges", counts.get("challenges", 0))
    structure_cols[3].metric("Tasks", counts.get("tasks", 0))
    structure_cols[4].metric("Transitions", counts.get("transitions", 0))

    st.markdown("### Analysis summary")

    issue_cols = st.columns(5)
    issue_cols[0].metric("Checks", len(checks_run))
    issue_cols[1].metric("Issues", total)
    issue_cols[2].metric("High", high)
    issue_cols[3].metric("Medium", medium)
    issue_cols[4].metric("Low", low)

    if warnings:
        with st.expander("Snapshot extraction warnings", expanded=False):
            for warning in warnings:
                st.warning(str(warning))


def _render_failed_checks_card(result: dict[str, Any]) -> None:
    failed_checks = _failed_checks(result)

    st.markdown("#### Failed checks")

    if failed_checks:
        for check in failed_checks:
            label = FRIENDLY_CHECK_NAMES.get(check, check)
            st.markdown(f"- {label}")
    else:
        st.caption("No failed checks.")


def _render_top_priorities_card(result: dict[str, Any]) -> None:
    top_priorities = _top_priorities(result)

    st.markdown("#### Top priorities")

    if top_priorities:
        for idx, label in enumerate(top_priorities, start=1):
            st.markdown(f"{idx}. {label}")
    else:
        st.caption("No prioritized findings.")


def _render_next_steps_card(result: dict[str, Any]) -> None:
    total, _, _, _ = _summary_counts(result)

    st.markdown("#### Next steps")

    if total > 0:
        st.markdown(
            "- Open **Findings** to inspect issues.\n"
            "- Start with **High** priority findings.\n"
            "- Use **Assistant** to ask what an issue means."
        )
    else:
        st.markdown(
            "- Open **Findings** to confirm which checks were run.\n"
            "- Use **Assistant** for a short interpretation.\n"
            "- Remember: clean checks are not full theory validation."
        )



def render_analysis_overview(result: dict[str, Any], show_title: bool = True) -> None:
    if show_title:
        st.subheader("Overview")

    total, _, _, _ = _summary_counts(result)

    _render_current_campaign_compact(result)
    _render_flow_diagram_panel(result)

    if total > 0:
        st.warning(
            "Issues found. Review high-priority findings first, then inspect the detailed findings."
        )
    else:
        st.success(
            "No issues were found by the selected checks. This does not prove that "
            "the campaign is theoretically optimal or deployment-ready; it only means "
            "that the selected export-level checks did not detect problems."
        )

    col1, col2, col3 = st.columns([1, 1.5, 1.2])

    with col1:
        _render_failed_checks_card(result)

    with col2:
        _render_top_priorities_card(result)

    with col3:
        _render_next_steps_card(result)