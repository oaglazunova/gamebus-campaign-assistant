from __future__ import annotations

from pathlib import Path

import streamlit as st

from campaign_assistant.downloader import CampaignDownloadError, download_campaign_xlsx
from campaign_assistant.storage import add_saved_campaign_abbreviation, get_cookie_file, load_password
from campaign_assistant.ui.actions import run_analysis, save_uploaded_file
from campaign_assistant.ui.chat import (
	answer_question,
	render_agent_trace_panel,
	render_capability_panel,
	render_fix_proposals_panel,
	render_issues_panel,
	render_point_gatekeeping_panel,
	render_theory_panel,
)
from campaign_assistant.ui.setup import render_campaign_setup_panel
from campaign_assistant.ui.session import init_state
from campaign_assistant.ui.sidebar import render_sidebar
from campaign_assistant.file_utils import sha256_file


st.set_page_config(page_title="GameBus Campaign Assistant", page_icon="🩺", layout="wide")


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

				st.session_state.settings = add_saved_campaign_abbreviation(
					campaign_abbreviation, st.session_state.settings
				)

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

	st.session_state.last_source_info = {
		"mode": "patched_draft",
		"file_name": file_path.name,
	}


def _render_chat_only(logger) -> None:
	result = st.session_state.result

	for message in st.session_state.messages:
		with st.chat_message(message["role"]):
			st.markdown(message["content"])

	if not result:
		st.info("Choose a campaign source and click **Analyze campaign** to begin.")
		return

	user_question = st.chat_input("Ask about this campaign check result...")
	if user_question:
		logger.log_chat_user(user_question)
		st.session_state.messages.append({"role": "user", "content": user_question})
		answer = answer_question(user_question, result)
		logger.log_chat_assistant(answer)
		st.session_state.messages.append({"role": "assistant", "content": answer})
		st.rerun()


def _render_editor_only() -> None:
	result = st.session_state.result
	if not result:
		st.info("Analyze a campaign to open the editor view.")
		return

	render_campaign_setup_panel(result)
	render_capability_panel(result)
	render_theory_panel(result)
	render_point_gatekeeping_panel(result)
	render_fix_proposals_panel(result)
	render_issues_panel(result)
	render_agent_trace_panel(
		result,
		show_trace=bool(st.session_state.get("show_agent_trace", False)),
	)


def main() -> None:
	init_state()
	logger = st.session_state.logger

	sidebar = render_sidebar()
	_handle_run(sidebar, logger)
	_handle_generated_draft_reload(sidebar, logger)
	_handle_current_snapshot_rerun(sidebar, logger)

	_render_source_info()

	tab_chat, tab_editor = st.tabs(["Chat", "Editor"])

	with tab_chat:
		_render_chat_only(logger)

	with tab_editor:
		_render_editor_only()


if __name__ == "__main__":
	main()