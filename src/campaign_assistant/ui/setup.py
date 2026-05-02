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
from campaign_assistant.ui.privacy_diagnostics import render_privacy_diagnostics_panel
from campaign_assistant.ui.workspace_readiness import build_workspace_readiness_model
from campaign_assistant.ui.labels import format_tristate


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



def _apply_workspace_action(action: dict[str, Any] | None, request_id: str) -> None:
	if not action:
		return

	focus = str(action.get("focus") or "").strip()
	if not focus:
		return

	st.session_state[f"campaign-setup-focus-{request_id}"] = focus
	st.rerun()


def _render_workspace_readiness_section(result: dict[str, Any], request_id: str) -> None:
	model = build_workspace_readiness_model(result)
	if not model["has_readiness"]:
		return

	st.markdown("### Workspace readiness")

	if model["status"] == "not_applicable":
		st.info("Progression/gatekeeping-specific validation is not applicable for this campaign.")
	elif model["status"] == "ready":
		st.success("Progression basics are available and stronger gatekeeping semantics checks are ready.")
	else:
		st.warning("Progression basics are available, but stronger gatekeeping semantics checks are disabled until required annotations are added.")

	col1, col2, col3 = st.columns(3)
	col1.metric(
		"Progression applicable",
		"Yes" if model["progression_applicable"] else "No",
	)
	col2.metric(
		"Gatekeeping annotated",
		"Yes" if model["gatekeeping_annotations_present"] else "No",
	)
	col3.metric(
		"Maintenance annotated",
		"Yes" if model["maintenance_annotations_present"] else "No",
	)

	summary = model["point_readiness_summary"]
	if summary:
		st.caption(
			f"Challenge findings: {int(summary.get('challenge_findings', 0) or 0)} | "
			f"Missing gatekeeping annotations: {int(summary.get('missing_gatekeeping_annotation_count', 0) or 0)} | "
			f"Missing maintenance annotations: {int(summary.get('missing_maintenance_annotation_count', 0) or 0)}"
		)

	if model["reasons"]:
		for msg in model["reasons"]:
			st.write(f"- {msg}")

	if model["actions"]:
		action = model["actions"][0]
		label = str(action.get("label") or "Open related setup")
		if st.button(label, key=f"workspace-readiness-action-{request_id}"):
			_apply_workspace_action(action, request_id)




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




def build_setup_page_status_model(result: dict[str, Any]) -> dict[str, Any]:
	assistant_meta = dict(result.get("assistant_meta", {}) or {})
	capability_summary = dict(assistant_meta.get("capability_summary", {}) or {})
	readiness = dict(assistant_meta.get("workspace_readiness", {}) or {})

	capabilities = dict(capability_summary.get("capabilities", {}) or {})
	task_role_count = int(capability_summary.get("task_role_count", 0) or 0)

	progression = capabilities.get("uses_progression")
	uses_ttm = capabilities.get("uses_ttm")

	if readiness.get("progression_applicable") and not readiness.get("gatekeeping_semantics_ready", True):
		status = "needs_annotations"
		message = "Complete task-role annotations first to unlock stronger progression/gatekeeping validation."
	elif readiness.get("progression_applicable"):
		status = "ready"
		message = "Workspace setup is sufficient for progression/gatekeeping interpretation."
	else:
		status = "general"
		message = "Use this page to review and edit workspace metadata for the current campaign."

	return {
		"status": status,
		"message": message,
		"task_role_count": task_role_count,
		"uses_progression": progression,
		"uses_ttm": uses_ttm,
	}


def render_setup_page_status(result: dict[str, Any]) -> None:
	model = build_setup_page_status_model(result)

	if model["status"] == "needs_annotations":
		st.warning(model["message"])
	elif model["status"] == "ready":
		st.success(model["message"])
	else:
		st.info(model["message"])

	c1, c2, c3 = st.columns(3)
	c1.metric("Task-role annotations", model["task_role_count"])
	c2.metric("Progression", format_tristate(model["uses_progression"]))
	c3.metric("TTM", format_tristate(model["uses_ttm"]))



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
	st.caption("Use this page to edit workspace metadata and then re-run analysis.")

	render_setup_page_status(result)

	privacy_report = dict(assistant_meta.get("privacy_report", {}) or {})
	render_privacy_diagnostics_panel(privacy_report)

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

	readiness = dict(assistant_meta.get("workspace_readiness", {}) or {})
	if readiness.get("progression_applicable") and not readiness.get("gatekeeping_semantics_ready", True):
		st.info(
			"Recommended first step: complete **Task-role annotations** so stronger progression/gatekeeping checks can be enabled."
		)

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

	with st.expander("Optional overrides (advanced)", expanded=(setup_focus == "override")):
		st.caption(
			"Use this only when you need to manually override inferred or profile-based metadata."
		)
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

	readiness = dict(assistant_meta.get("workspace_readiness", {}) or {})
	task_roles_expanded = (
			setup_focus == "task_roles"
			or (
					readiness.get("progression_applicable")
					and not readiness.get("gatekeeping_semantics_ready", True)
			)
	)

	with st.expander("Task-role annotations", expanded=task_roles_expanded):
		st.markdown("**Task-role annotations**")
		st.caption(
			"Use this editor when GameBus does not yet store gatekeeping / maintenance metadata natively."
		)

		df = _task_roles_dataframe(workspace_root)
		current_nonempty_rows = max(
			0,
			len(
				[
					row for row in df.fillna("").to_dict(orient="records")
					if any(str(row.get(k, "") or "").strip() for k in ["task_id", "task_name", "role", "notes"])
				]
			),
		)
		st.caption(f"Current annotated rows: {current_nonempty_rows}")

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
		f1, f2, f3 = st.columns(3)
		f1.metric("task_roles.csv", "Present" if (metadata_dir / "task_roles.csv").exists() else "Missing")
		f2.metric("ttm_structure.pdf", "Present" if (theory_dir / "ttm_structure.pdf").exists() else "Missing")
		f3.metric(
			"intervention_mapping.xlsx",
			"Present" if (theory_dir / "intervention_mapping.xlsx").exists() else "Missing",
		)

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