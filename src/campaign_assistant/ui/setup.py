from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from campaign_assistant.metadata.adapters.sidecar import (
    load_campaign_profile_json,
    load_metadata_override_json,
    load_task_roles_csv,
    save_campaign_profile_json,
    save_metadata_override_json,
    save_task_roles_csv,
    save_workspace_bytes,
)


_CAPABILITY_FIELDS = [
    "uses_progression",
    "uses_gatekeeping",
    "uses_maintenance_tasks",
    "uses_ttm",
    "uses_bct_mapping",
    "uses_comb_mapping",
    "uses_wave_specific_logic",
    "uses_group_specific_logic",
]

_PROFILE_TEMPLATES: dict[str, dict[str, Any]] = {
    "Generic / unknown": {
        "capabilities": {
            "uses_progression": None,
            "uses_gatekeeping": None,
            "uses_maintenance_tasks": None,
            "uses_ttm": None,
            "uses_bct_mapping": False,
            "uses_comb_mapping": False,
            "uses_wave_specific_logic": None,
            "uses_group_specific_logic": None,
        }
    },
    "Progression campaign": {
        "capabilities": {
            "uses_progression": True,
            "uses_gatekeeping": None,
            "uses_maintenance_tasks": None,
            "uses_ttm": None,
            "uses_bct_mapping": False,
            "uses_comb_mapping": False,
            "uses_wave_specific_logic": True,
            "uses_group_specific_logic": True,
        }
    },
    "Progression + TTM campaign": {
        "capabilities": {
            "uses_progression": True,
            "uses_gatekeeping": None,
            "uses_maintenance_tasks": None,
            "uses_ttm": True,
            "uses_bct_mapping": False,
            "uses_comb_mapping": False,
            "uses_wave_specific_logic": True,
            "uses_group_specific_logic": True,
        }
    },
    "Static informational campaign": {
        "capabilities": {
            "uses_progression": False,
            "uses_gatekeeping": False,
            "uses_maintenance_tasks": False,
            "uses_ttm": False,
            "uses_bct_mapping": False,
            "uses_comb_mapping": False,
            "uses_wave_specific_logic": True,
            "uses_group_specific_logic": True,
        }
    },
}


def _tri_to_widget_value(value: bool | None) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Unknown"


def _widget_value_to_tri(value: str) -> bool | None:
    if value == "Yes":
        return True
    if value == "No":
        return False
    return None


def _resolved_capabilities_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return (
        result.get("assistant_meta", {})
        .get("capability_summary", {})
        .get("capabilities", {})
        or {}
    )


def _current_profile(workspace_root: str | Path, result: dict[str, Any]) -> dict[str, Any]:
    profile = load_campaign_profile_json(workspace_root)

    if profile:
        if "capabilities" not in profile:
            profile = {"capabilities": profile}
        return profile

    resolved = _resolved_capabilities_from_result(result)
    if resolved:
        return {"capabilities": {field: resolved.get(field) for field in _CAPABILITY_FIELDS}}

    return _PROFILE_TEMPLATES["Generic / unknown"]


def _ensure_profile_widget_defaults(workspace_root: str | Path, request_id: str, result: dict[str, Any]) -> None:
    profile = _current_profile(workspace_root, result)
    caps = profile.get("capabilities", {})

    for field in _CAPABILITY_FIELDS:
        key = f"profile-{request_id}-{field}"
        if key not in st.session_state:
            st.session_state[key] = _tri_to_widget_value(caps.get(field))


def _apply_template_to_widgets(template_name: str, request_id: str) -> None:
    template = _PROFILE_TEMPLATES[template_name]
    caps = template.get("capabilities", {})
    for field in _CAPABILITY_FIELDS:
        st.session_state[f"profile-{request_id}-{field}"] = _tri_to_widget_value(caps.get(field))


def _apply_resolved_capabilities_to_widgets(result: dict[str, Any], request_id: str) -> None:
    caps = _resolved_capabilities_from_result(result)
    for field in _CAPABILITY_FIELDS:
        st.session_state[f"profile-{request_id}-{field}"] = _tri_to_widget_value(caps.get(field))


def _collect_profile_from_widgets(request_id: str) -> dict[str, Any]:
    capabilities: dict[str, Any] = {}
    for field in _CAPABILITY_FIELDS:
        widget_key = f"profile-{request_id}-{field}"
        capabilities[field] = _widget_value_to_tri(st.session_state[widget_key])
    return {"capabilities": capabilities}


def build_setup_conflict_messages(result: dict[str, Any]) -> list[str]:
    messages: list[str] = []

    assistant_meta = result.get("assistant_meta", {}) or {}
    selected_checks = assistant_meta.get("selected_checks", []) or []
    capability_summary = assistant_meta.get("capability_summary", {}) or {}
    capabilities = capability_summary.get("capabilities", {}) or {}
    task_role_count = int(capability_summary.get("task_role_count", 0) or 0)

    if "ttm" in selected_checks and capabilities.get("uses_ttm") is False:
        messages.append(
            "TTM checking was requested, but the campaign capability profile currently says uses_ttm = False."
        )

    if capabilities.get("uses_progression") is False and capabilities.get("uses_gatekeeping") is True:
        messages.append(
            "The profile says uses_gatekeeping = True while uses_progression = False. "
            "That combination is unusual and should be reviewed."
        )

    if capabilities.get("uses_progression") is False and capabilities.get("uses_maintenance_tasks") is True:
        messages.append(
            "The profile says uses_maintenance_tasks = True while uses_progression = False. "
            "That combination is unusual and should be reviewed."
        )

    if capabilities.get("uses_progression") is True and task_role_count == 0:
        messages.append(
            "This campaign appears to use progression, but no task-role annotations are currently available."
        )

    theory = result.get("theory_grounding", {}) or {}
    if capabilities.get("uses_ttm") is True and not theory.get("ttm_structure_file_exists", False):
        messages.append(
            "TTM is enabled for this campaign, but no TTM structure file is currently registered."
        )

    return messages


def _task_roles_dataframe(workspace_root: str | Path) -> pd.DataFrame:
    rows = [x.to_dict() for x in load_task_roles_csv(workspace_root)]
    if not rows:
        rows = [{"task_id": "", "task_name": "", "role": "", "notes": ""}]
    return pd.DataFrame(rows)


def _current_setup_focus(request_id: str) -> str | None:
    return st.session_state.get(f"campaign-setup-focus-{request_id}")


def _focus_label(focus: str | None) -> str:
    mapping = {
        "profile": "Capability profile",
        "task_roles": "Task-role annotations",
        "theory": "Sidecars and evidence files",
        "override": "Optional overrides",
    }
    return mapping.get(focus or "", "Campaign setup")


def render_campaign_setup_panel(result: dict[str, Any]) -> None:
    assistant_meta = result.get("assistant_meta", {}) or {}
    workspace_root = assistant_meta.get("workspace_root")
    request_id = assistant_meta.get("request_id")
    snapshot_path = assistant_meta.get("snapshot_path")
    workspace_id = assistant_meta.get("workspace_id")

    if not workspace_root or not request_id:
        return

    workspace_root = Path(workspace_root)
    snapshot_path = Path(snapshot_path) if snapshot_path else None

    st.subheader("Campaign setup")

    st.caption(f"Workspace: {workspace_id}")
    st.caption(f"Workspace root: {workspace_root}")

    _ensure_profile_widget_defaults(workspace_root, request_id, result)

    setup_focus = _current_setup_focus(request_id)
    if setup_focus:
        colf1, colf2 = st.columns([5, 1])
        with colf1:
            st.info(
                f"Quick action focus is active: **{_focus_label(setup_focus)}**. "
                "Review that section below."
            )
        with colf2:
            if st.button("Clear focus", key=f"clear-setup-focus-{request_id}"):
                st.session_state.pop(f"campaign-setup-focus-{request_id}", None)
                st.rerun()

    conflict_messages = build_setup_conflict_messages(result)
    if conflict_messages:
        for msg in conflict_messages:
            st.warning(msg)

    with st.expander("Capability profile", expanded=(setup_focus == "profile")):
        col_a, col_b, col_c = st.columns([3, 2, 2])

        with col_a:
            template_name = st.selectbox(
                "Profile template",
                options=list(_PROFILE_TEMPLATES.keys()),
                key=f"profile-template-{request_id}",
            )

        with col_b:
            if st.button("Apply template to form", key=f"apply-profile-template-{request_id}"):
                _apply_template_to_widgets(template_name, request_id)
                st.rerun()

        with col_c:
            if st.button("Load resolved capabilities into form", key=f"apply-resolved-profile-{request_id}"):
                _apply_resolved_capabilities_to_widgets(result, request_id)
                st.rerun()

        with st.form(f"campaign-profile-form-{request_id}"):
            cols1 = st.columns(4)
            cols2 = st.columns(4)

            widget_cols = cols1 + cols2
            for idx, field in enumerate(_CAPABILITY_FIELDS):
                with widget_cols[idx]:
                    st.selectbox(
                        field,
                        options=["Unknown", "Yes", "No"],
                        key=f"profile-{request_id}-{field}",
                    )

            save_profile = st.form_submit_button("Save campaign profile")

            if save_profile:
                payload = _collect_profile_from_widgets(request_id)
                path = save_campaign_profile_json(workspace_root, payload)
                st.success(f"Saved campaign profile to {path}")

    with st.expander("Optional overrides", expanded=(setup_focus == "override")):
        current_override = load_metadata_override_json(workspace_root)
        override_text = st.text_area(
            "metadata_override.json content (JSON)",
            value="" if not current_override else __import__("json").dumps(current_override, indent=2, ensure_ascii=False),
            height=180,
            key=f"metadata-override-text-{request_id}",
        )

        if st.button("Save metadata override", key=f"save-override-{request_id}"):
            import json

            try:
                payload = json.loads(override_text) if override_text.strip() else {}
                path = save_metadata_override_json(workspace_root, payload)
                st.success(f"Saved metadata override to {path}")
            except Exception as exc:
                st.error(f"Invalid JSON: {exc}")

    with st.expander("Task-role annotations", expanded=(setup_focus == "task_roles")):
        st.caption(
            "Use this editor when GameBus does not yet store gatekeeping / maintenance metadata natively."
        )

        df = _task_roles_dataframe(workspace_root)
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            key=f"task-role-editor-{request_id}",
            column_config={
                "role": st.column_config.SelectboxColumn(
                    "role",
                    options=["", "gatekeeping", "maintenance", "transition", "optional", "supporting"],
                )
            },
        )

        if st.button("Save task-role annotations", key=f"save-task-roles-{request_id}"):
            rows = edited_df.fillna("").to_dict(orient="records")
            rows = [
                row for row in rows
                if any(str(row.get(k, "") or "").strip() for k in ["task_id", "task_name", "role", "notes"])
            ]
            path = save_task_roles_csv(workspace_root, rows)
            st.success(f"Saved task-role annotations to {path}")

    with st.expander("Sidecars and evidence files", expanded=(setup_focus == "theory")):
        metadata_dir = workspace_root / "metadata"
        theory_dir = workspace_root / "evidence" / "theory"

        st.markdown("**Current files**")
        st.markdown(f"- task_roles.csv: `{(metadata_dir / 'task_roles.csv').exists()}`")
        st.markdown(f"- ttm_structure.pdf: `{(theory_dir / 'ttm_structure.pdf').exists()}`")
        st.markdown(f"- intervention_mapping.xlsx: `{(theory_dir / 'intervention_mapping.xlsx').exists()}`")

        task_roles_file = st.file_uploader(
            "Upload task_roles.csv",
            type=["csv"],
            key=f"task-roles-upload-{request_id}",
        )
        ttm_file = st.file_uploader(
            "Upload ttm_structure.pdf",
            type=["pdf"],
            key=f"ttm-structure-upload-{request_id}",
        )
        mapping_file = st.file_uploader(
            "Upload intervention_mapping.xlsx",
            type=["xlsx"],
            key=f"intervention-mapping-upload-{request_id}",
        )

        if st.button("Save uploaded sidecars/evidence", key=f"save-sidecars-{request_id}"):
            saved_paths: list[str] = []

            if task_roles_file is not None:
                path = save_workspace_bytes(
                    workspace_root,
                    "metadata/task_roles.csv",
                    task_roles_file.getvalue(),
                )
                saved_paths.append(str(path))

            if ttm_file is not None:
                path = save_workspace_bytes(
                    workspace_root,
                    "evidence/theory/ttm_structure.pdf",
                    ttm_file.getvalue(),
                )
                saved_paths.append(str(path))

            if mapping_file is not None:
                path = save_workspace_bytes(
                    workspace_root,
                    "evidence/theory/intervention_mapping.xlsx",
                    mapping_file.getvalue(),
                )
                saved_paths.append(str(path))

            if saved_paths:
                st.success("Saved files:\n- " + "\n- ".join(saved_paths))
            else:
                st.info("No files were selected.")

    if snapshot_path is not None:
        st.caption(
            "After changing the profile or sidecars, re-run analysis so the assistant uses the new metadata."
        )
        if st.button("Re-run analysis with current workspace metadata", key=f"rerun-workspace-{request_id}"):
            st.session_state["rerun_current_snapshot_payload"] = {
                "path": str(snapshot_path),
                "workspace_id": workspace_id,
            }
            st.rerun()