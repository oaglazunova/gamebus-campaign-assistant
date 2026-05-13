from __future__ import annotations

from typing import Any

import streamlit as st


def build_analysis_overview_model(result: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {
            "has_result": False,
            "status": "empty",
            "workspace_id": None,
            "snapshot_id": None,
            "total_issues": 0,
            "failed_checks": [],
            "errored_checks": [],
            "proposal_count": 0,
            "readiness_status": "unknown",
            "selected_checks": [],
            "source_mode": None,
            "source_label": None,
        }

    assistant_meta = dict(result.get("assistant_meta", {}) or {})
    summary = dict(result.get("summary", {}) or {})
    fix_proposals = dict(result.get("fix_proposals", {}) or {})
    readiness = dict(assistant_meta.get("workspace_readiness", {}) or {})

    total_issues = int(summary.get("total_issues", 0) or 0)
    failed_checks = list(summary.get("failed_checks", []) or [])
    errored_checks = list(summary.get("errored_checks", []) or [])
    proposal_count = int(fix_proposals.get("proposal_count", 0) or 0)
    selected_checks = list(assistant_meta.get("selected_checks", []) or [])

    if not readiness:
        readiness_status = "unknown"
    elif not readiness.get("progression_applicable", False):
        readiness_status = "not_applicable"
    elif readiness.get("gatekeeping_semantics_ready", False):
        readiness_status = "ready"
    else:
        readiness_status = "needs_annotations"

    if errored_checks:
        status = "errored"
    elif total_issues > 0:
        status = "issues_found"
    else:
        status = "clean"

    return {
        "has_result": True,
        "status": status,
        "workspace_id": assistant_meta.get("workspace_id"),
        "snapshot_id": assistant_meta.get("snapshot_id"),
        "total_issues": total_issues,
        "failed_checks": failed_checks,
        "errored_checks": errored_checks,
        "proposal_count": proposal_count,
        "readiness_status": readiness_status,
        "selected_checks": selected_checks,
        "source_mode": assistant_meta.get("source_mode"),
        "source_label": assistant_meta.get("source_label"),
    }


def _status_message(model: dict[str, Any]) -> tuple[str, str]:
    status = model["status"]
    readiness = model["readiness_status"]

    if status == "errored":
        return "error", "Some checks failed to run correctly. Review errored checks first."
    if readiness == "needs_annotations":
        return "warning", "Analysis ran, but stronger progression semantics checks are still disabled until workspace annotations are added."
    if status == "issues_found":
        return "warning", "Analysis completed and issues were found."
    if status == "clean":
        return "success", "Analysis completed and no issues were found."
    return "info", "Analysis state is available."


def render_analysis_overview(
    result: dict[str, Any] | None,
    *,
    show_title: bool = True,
) -> None:
    model = build_analysis_overview_model(result)
    if not model["has_result"]:
        return

    if show_title:
        st.markdown("## Overview")

    msg_type, msg_text = _status_message(model)
    if msg_type == "error":
        st.error(msg_text)
    elif msg_type == "warning":
        st.warning(msg_text)
    elif msg_type == "success":
        st.success(msg_text)
    else:
        st.info(msg_text)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Issues", model["total_issues"])
    c2.metric("Failed checks", len(model["failed_checks"]))
    c3.metric("Errored checks", len(model["errored_checks"]))
    c4.metric("Proposed fixes", model["proposal_count"])

    meta_left, meta_right = st.columns(2)
    with meta_left:
        if model["workspace_id"]:
            st.caption(f"Workspace: {model['workspace_id']}")
        if model["snapshot_id"]:
            st.caption(f"Snapshot: {model['snapshot_id']}")
    with meta_right:
        if model["selected_checks"]:
            st.caption(f"Selected checks: {', '.join(f'`{x}`' for x in model['selected_checks'])}")

    if model["failed_checks"]:
        st.markdown("**Failed checks**")
        st.write(", ".join(f"`{name}`" for name in model["failed_checks"]))

    if model["errored_checks"]:
        st.markdown("**Errored checks**")
        st.write(", ".join(f"`{name}`" for name in model["errored_checks"]))