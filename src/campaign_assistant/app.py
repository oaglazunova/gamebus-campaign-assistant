from __future__ import annotations

from pathlib import Path

import streamlit as st

from campaign_assistant.downloader import CampaignDownloadError, download_campaign_xlsx
from campaign_assistant.file_utils import sha256_file
from campaign_assistant.storage import add_saved_campaign_abbreviation, get_cookie_file, load_password
from campaign_assistant.ui.actions import run_analysis, save_uploaded_file
from campaign_assistant.ui.chat import (
	answer_question,
	render_agent_trace_panel,
	render_assistant_guide_panel,
	render_assistant_page_status,
	render_capability_panel,
	render_findings_overview_panel,
	render_fix_proposals_panel,
	render_issues_panel,
	render_point_gatekeeping_panel,
	render_theory_panel,
)
from campaign_assistant.ui.overview import render_analysis_overview
from campaign_assistant.ui.session import init_state
from campaign_assistant.ui.setup import render_campaign_setup_panel
from campaign_assistant.ui.sidebar import render_sidebar
from campaign_assistant.ui.copy import WORKFLOW_PAGE_COPY


st.set_page_config(page_title="GameBus Campaign Assistant", page_icon="🩺", layout="wide")

_WORKFLOW_PAGES = ["Overview", "Setup", "Findings", "Fixes", "Assistant"]


def _render_page_intro(title: str, description: str) -> None:
	st.markdown(f"## {title}")
	st.caption(description)


def _render_empty_workflow_state(message: str) -> None:
	st.info(message)



def _render_source_info() -> None:
	source_info = st.session_state.get("last_source_info")
	if not source_info:
		return

	mode = source_info.get("mode")

	if mode == "upload":
		st.info(f"Current campaign source: uploaded file **{source_info['file_name']}**")
	elif mode == "download":
		tag = " (auto-refreshed)" if source_info.get("auto_refreshed") else ""
		st.info(
			f"Current campaign source: downloaded for campaign "
			f"**{source_info['campaign_abbreviation']}**{tag}"
		)
	elif mode == "patched_draft":
		st.info(f"Current campaign source: patched draft **{source_info['file_name']}**")


def _handle_run(sidebar: dict, logger) -> None:
	if not sidebar["run_clicked"]:
		return

	try:
		with st.spinner("Preparing campaign file..."):
			logger.log(
				"analyze_clicked",
				{
					"source_mode": sidebar["source_mode"],
					"selected_checks": sidebar["selected_checks"],
					"export_excel": sidebar["export_excel"],
				},
			)

			if sidebar["source_mode"] == "Upload Excel file":
				uploaded_file = sidebar["uploaded_file"]
				if not uploaded_file:
					st.error("Please upload a single .xlsx campaign export first.")
					return

				file_path = save_uploaded_file(uploaded_file)
				file_hash = sha256_file(file_path)

				logger.start_session(
					campaign_source="upload",
					uploaded_file_name=uploaded_file.name,
					uploaded_file_hash=file_hash,
					selected_checks=sidebar["selected_checks"],
				)
				logger.log_upload(
					file_name=uploaded_file.name,
					saved_path=str(file_path),
					file_hash=file_hash,
					size_bytes=file_path.stat().st_size,
				)

				st.session_state.last_source_info = {
					"mode": "upload",
					"file_name": uploaded_file.name,
				}

				run_analysis(
					file_path=file_path,
					selected_checks=sidebar["selected_checks"],
					export_excel=sidebar["export_excel"],
					logger=logger,
				)

				if isinstance(st.session_state.get("result"), dict):
					st.session_state.result.setdefault("assistant_meta", {}).update(
						{
							"source_mode": st.session_state.last_source_info.get("mode"),
							"source_label": st.session_state.last_source_info.get("file_name")
							                or st.session_state.last_source_info.get("campaign_abbreviation"),
						}
					)

			else:
				base_url = st.session_state.app_config.get("campaigns_base_url", "").strip()
				email = st.session_state.settings.get("email", "").strip()
				remember_credentials = st.session_state.settings.get("remember_credentials", True)
				password = load_password(email) if (remember_credentials and email) else None

				campaign_abbreviation = st.session_state.current_campaign_abbreviation.strip()
				if not campaign_abbreviation:
					st.error("Please provide a campaign abbreviation first.")
					return

				file_path = download_campaign_xlsx(
					base_url=base_url,
					campaign_abbreviation=campaign_abbreviation,
					email=email or None,
					password=password,
					cookie_file=get_cookie_file(),
				)

				file_hash = sha256_file(file_path)

				logger.start_session(
					campaign_source="download",
					campaign_abbreviation=campaign_abbreviation,
					uploaded_file_name=file_path.name,
					uploaded_file_hash=file_hash,
					selected_checks=sidebar["selected_checks"],
				)
				logger.log_download(
					campaign_abbreviation=campaign_abbreviation,
					base_url=base_url,
					file_name=file_path.name,
					file_hash=file_hash,
					saved_path=str(file_path),
				)

				st.session_state.last_source_info = {
					"mode": "download",
					"base_url": base_url,
					"campaign_abbreviation": campaign_abbreviation,
					"file_name": file_path.name,
					"auto_refreshed": False,
				}

				run_analysis(
					file_path=file_path,
					selected_checks=sidebar["selected_checks"],
					export_excel=sidebar["export_excel"],
					logger=logger,
				)

				if isinstance(st.session_state.get("result"), dict):
					st.session_state.result.setdefault("assistant_meta", {}).update(
						{
							"source_mode": st.session_state.last_source_info.get("mode"),
							"source_label": st.session_state.last_source_info.get("file_name")
							                or st.session_state.last_source_info.get("campaign_abbreviation"),
						}
					)

				st.session_state.settings = add_saved_campaign_abbreviation(
					campaign_abbreviation, st.session_state.settings
				)

		st.session_state["main_workflow_page"] = "Overview"
		st.rerun()

	except CampaignDownloadError as exc:
		logger.log_error(
			where="download_campaign_xlsx",
			exc=exc,
			extra={
				"source_mode": sidebar["source_mode"],
				"campaign_abbreviation": st.session_state.current_campaign_abbreviation.strip(),
			},
		)
		st.error(f"Download failed: {exc}")
	except Exception as exc:
		logger.log_error(
			where="_handle_run",
			exc=exc,
			extra={
				"source_mode": sidebar["source_mode"],
				"selected_checks": sidebar["selected_checks"],
			},
		)
		st.exception(exc)


def _handle_current_snapshot_rerun(sidebar: dict, logger) -> None:
	payload = st.session_state.pop("rerun_current_snapshot_payload", None)
	if not payload:
		return

	file_path = Path(payload["path"])
	workspace_id = payload.get("workspace_id")

	if not file_path.exists():
		st.error(f"Snapshot file no longer exists: {file_path}")
		return

	logger.log(
		"rerun_current_snapshot_with_workspace_metadata",
		{
			"file_path": str(file_path),
			"workspace_id": workspace_id,
			"selected_checks": sidebar["selected_checks"],
		},
	)

	run_analysis(
		file_path=file_path,
		selected_checks=sidebar["selected_checks"],
		export_excel=sidebar["export_excel"],
		logger=logger,
		workspace_id=workspace_id,
	)

	if isinstance(st.session_state.get("result"), dict):
		st.session_state.result.setdefault("assistant_meta", {}).update(
			{
				"source_mode": st.session_state.last_source_info.get("mode") if st.session_state.get(
					"last_source_info") else None,
				"source_label": (
					st.session_state.last_source_info.get("file_name")
					if st.session_state.get("last_source_info")
					else file_path.name
				),
			}
		)

	st.session_state["main_workflow_page"] = "Overview"


def _handle_generated_draft_reload(sidebar: dict, logger) -> None:
	payload = st.session_state.pop("reload_generated_draft_payload", None)
	if not payload:
		return

	file_path = Path(payload["path"])
	workspace_id = payload.get("workspace_id")

	if not file_path.exists():
		st.error(f"Patched draft file no longer exists: {file_path}")
		return

	logger.log(
		"reload_generated_draft",
		{
			"file_path": str(file_path),
			"workspace_id": workspace_id,
			"selected_checks": sidebar["selected_checks"],
		},
	)

	run_analysis(
		file_path=file_path,
		selected_checks=sidebar["selected_checks"],
		export_excel=sidebar["export_excel"],
		logger=logger,
		workspace_id=workspace_id,
	)

	if isinstance(st.session_state.get("result"), dict):
		st.session_state.result.setdefault("assistant_meta", {}).update(
			{
				"source_mode": "patched_draft",
				"source_label": file_path.name,
			}
		)

	st.session_state.last_source_info = {
		"mode": "patched_draft",
		"file_name": file_path.name,
	}
	st.session_state["main_workflow_page"] = "Overview"


def _sync_main_workflow_focus_from_result(result) -> None:
	if not result:
		return

	assistant_meta = result.get("assistant_meta", {}) or {}
	request_id = assistant_meta.get("request_id")
	if not request_id:
		return

	focus_key = f"campaign-main-focus-{request_id}"
	focus = st.session_state.pop(focus_key, None)
	if not focus:
		return

	mapping = {
		"overview": "Overview",
		"findings": "Findings",
		"fixes": "Fixes",
		"assistant": "Assistant",
	}

	page = mapping.get(str(focus).strip().lower())
	if page in _WORKFLOW_PAGES:
		st.session_state["main_workflow_page"] = page


def _render_overview_page(result) -> None:
	_render_page_intro("Overview", WORKFLOW_PAGE_COPY["Overview"]["description"])

	if not result:
		_render_empty_workflow_state("Overview")
		return

	render_analysis_overview(result)
	render_capability_panel(result)

	st.markdown("### Next step")
	col1, col2, col3, col4 = st.columns(4)

	with col1:
		if st.button(WORKFLOW_PAGE_COPY["Setup"]["open_label"], key="overview-go-setup", use_container_width=True):
			st.session_state["main_workflow_page"] = "Setup"
			st.rerun()

	with col2:
		if st.button(WORKFLOW_PAGE_COPY["Findings"]["open_label"], key="overview-go-findings", use_container_width=True):
			st.session_state["main_workflow_page"] = "Findings"
			st.rerun()

	with col3:
		if st.button(WORKFLOW_PAGE_COPY["Fixes"]["open_label"], key="overview-go-fixes", use_container_width=True):
			st.session_state["main_workflow_page"] = "Fixes"
			st.rerun()

	with col4:
		if st.button(WORKFLOW_PAGE_COPY["Assistant"]["open_label"], key="overview-go-assistant", use_container_width=True):
			st.session_state["main_workflow_page"] = "Assistant"
			st.rerun()


def _render_setup_page(result) -> None:
	_render_page_intro("Setup", WORKFLOW_PAGE_COPY["Setup"]["description"])

	if not result:
		_render_empty_workflow_state("Setup")
		return

	render_campaign_setup_panel(result)


def _render_findings_page(result) -> None:
	_render_page_intro("Findings", WORKFLOW_PAGE_COPY["Findings"]["description"])

	if not result:
		_render_empty_workflow_state("Findings")
		return

	render_findings_overview_panel(result)
	render_issues_panel(result, compact=True)

	with st.expander("Theory interpretation", expanded=False):
		render_theory_panel(result, compact=True)

	with st.expander("Point & gatekeeping interpretation", expanded=False):
		render_point_gatekeeping_panel(result, compact=True)


def _render_fixes_page(result) -> None:
	_render_page_intro("Fixes", WORKFLOW_PAGE_COPY["Fixes"]["description"])

	if not result:
		_render_empty_workflow_state("Fixes")
		return

	render_fix_proposals_panel(result)


def _handle_pending_assistant_prompt(logger, result) -> None:
	pending = st.session_state.pop("assistant_prefill_prompt", None)
	if not pending or not result:
		return

	logger.log_chat_user(pending)
	st.session_state.messages.append({"role": "user", "content": pending})
	answer = answer_question(pending, result)
	logger.log_chat_assistant(answer)
	st.session_state.messages.append({"role": "assistant", "content": answer})
	st.rerun()


def _render_assistant_page(logger, show_trace: bool) -> None:
	_render_page_intro("Assistant", WORKFLOW_PAGE_COPY["Assistant"]["description"])

	result = st.session_state.result

	if not result:
		_render_empty_workflow_state("Assistant")
		return

	render_assistant_page_status(result, len(st.session_state.messages))
	render_assistant_guide_panel(result)

	control_col1, control_col2 = st.columns([1, 4])
	with control_col1:
		if st.button("Reset conversation", key="assistant-clear-conversation", use_container_width=True):
			st.session_state.messages = []
			st.rerun()
	with control_col2:
		st.caption("Use a suggested prompt or ask your own question about the current campaign analysis.")

	_handle_pending_assistant_prompt(logger, result)

	if not st.session_state.messages:
		st.info("No assistant conversation yet. Start with a suggested prompt below, or ask your own question.")
	else:
		st.markdown("### Conversation")
		for message in st.session_state.messages:
			with st.chat_message(message["role"]):
				st.markdown(message["content"])

	user_question = st.chat_input("Ask about this campaign...")
	if user_question:
		logger.log_chat_user(user_question)
		st.session_state.messages.append({"role": "user", "content": user_question})
		answer = answer_question(user_question, result)
		logger.log_chat_assistant(answer)
		st.session_state.messages.append({"role": "assistant", "content": answer})
		st.rerun()

	render_agent_trace_panel(result, show_trace=show_trace)


def main() -> None:
	init_state()
	logger = st.session_state.logger

	sidebar = render_sidebar()
	_handle_run(sidebar, logger)
	_handle_generated_draft_reload(sidebar, logger)
	_handle_current_snapshot_rerun(sidebar, logger)

	_render_source_info()

	result = st.session_state.result
	_sync_main_workflow_focus_from_result(result)

	current_page = st.session_state.get("main_workflow_page", "Overview")
	if current_page not in _WORKFLOW_PAGES:
		current_page = "Overview"

	selected_page = st.radio(
		"Workflow",
		options=_WORKFLOW_PAGES,
		index=_WORKFLOW_PAGES.index(current_page),
		horizontal=True,
		label_visibility="collapsed",
		key="main_workflow_page",
	)

	show_trace = bool(st.session_state.get("show_agent_trace", False))

	if selected_page == "Overview":
		_render_overview_page(result)
	elif selected_page == "Setup":
		_render_setup_page(result)
	elif selected_page == "Findings":
		_render_findings_page(result)
	elif selected_page == "Fixes":
		_render_fixes_page(result)
	else:
		_render_assistant_page(logger, show_trace=show_trace)


if __name__ == "__main__":
	main()