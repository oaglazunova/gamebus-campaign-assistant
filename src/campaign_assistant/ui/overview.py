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
            "top_actions": [],
        }

    assistant_meta = dict(result.get("assistant_meta", {}) or {})
    summary = dict(result.get("summary", {}) or {})
    fix_proposals = dict(result.get("fix_proposals", {}) or {})
    readiness = dict(assistant_meta.get("workspace_readiness", {}) or {})

    total_issues = int(summary.get("total_issues", 0) or 0)
    failed_checks = list(summary.get("failed_checks", []) or [])
    errored_checks = list(summary.get("errored_checks", []) or [])
    proposal_count = int(fix_proposals.get("proposal_count", 0) or 0)

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

    top_actions: list[dict[str, str]] = []

    if readiness_status == "needs_annotations":
        top_actions.append(
            {
                "label": "Annotate task roles",
                "focus": "task_roles",
                "kind": "setup",
            }
        )

    if total_issues > 0:
        top_actions.append(
            {
                "label": "Review findings",
                "focus": "findings",
                "kind": "review",
            }
        )

    if proposal_count > 0:
        top_actions.append(
            {
                "label": "Review proposed fixes",
                "focus": "fixes",
                "kind": "fixes",
            }
        )

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
        "top_actions": top_actions,
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


def _apply_overview_action(action: dict[str, str], request_id: str | None) -> None:
    if not request_id:
        return

    focus = str(action.get("focus") or "").strip()
    if not focus:
        return

    if focus in {"task_roles", "profile", "theory", "override"}:
        st.session_state[f"campaign-setup-focus-{request_id}"] = focus
    else:
        st.session_state[f"campaign-main-focus-{request_id}"] = focus

    st.rerun()


def render_analysis_overview(result: dict[str, Any] | None) -> None:
    model = build_analysis_overview_model(result)
    if not model["has_result"]:
        return

    assistant_meta = dict((result or {}).get("assistant_meta", {}) or {})
    request_id = assistant_meta.get("request_id")

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

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Issues", model["total_issues"])
    col2.metric("Failed checks", len(model["failed_checks"]))
    col3.metric("Errored checks", len(model["errored_checks"]))
    col4.metric("Proposed fixes", model["proposal_count"])

    if model["workspace_id"]:
        st.caption(f"Workspace: {model['workspace_id']}")
    if model["snapshot_id"]:
        st.caption(f"Snapshot: {model['snapshot_id']}")

    if model["failed_checks"]:
        st.markdown("**Failed checks**")
        st.write(", ".join(f"`{name}`" for name in model["failed_checks"]))

    if model["errored_checks"]:
        st.markdown("**Errored checks**")
        st.write(", ".join(f"`{name}`" for name in model["errored_checks"]))

    if model["top_actions"]:
        st.markdown("**Next actions**")
        action_cols = st.columns(len(model["top_actions"]))
        for col, action in zip(action_cols, model["top_actions"]):
            with col:
                if st.button(action["label"], key=f"overview-action-{action['label']}"):
                    _apply_overview_action(action, request_id)