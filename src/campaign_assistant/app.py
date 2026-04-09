from __future__ import annotations

import streamlit as st

from campaign_assistant.downloader import CampaignDownloadError, download_campaign_xlsx
from campaign_assistant.storage import (
	add_saved_campaign_abbreviation,
	get_cookie_file,
	load_password,
)
from campaign_assistant.ui.actions import run_analysis, save_uploaded_file
from campaign_assistant.ui.chat import answer_question, render_issues_panel
from campaign_assistant.ui.session import init_state
from campaign_assistant.ui.sidebar import render_sidebar

st.set_page_config(page_title="GameBus Campaign Assistant", page_icon="🩺", layout="wide")


def _render_source_info() -> None:
	source_info = st.session_state.get("last_source_info")
	if not source_info:
		return

	if source_info["mode"] == "upload":
		st.info(f"Current campaign source: uploaded file **{source_info['file_name']}**")
	else:
		tag = " (auto-refreshed)" if source_info.get("auto_refreshed") else ""
		st.info(
			f"Current campaign source: downloaded for campaign "
			f"**{source_info['campaign_abbreviation']}**{tag}"
		)


def _handle_run(sidebar: dict) -> None:
	if not sidebar["run_clicked"]:
		return

	try:
		with st.spinner("Preparing campaign file..."):
			if sidebar["source_mode"] == "Upload Excel file":
				uploaded_file = sidebar["uploaded_file"]
				if not uploaded_file:
					st.error("Please upload a single .xlsx campaign export first.")
					return

				file_path = save_uploaded_file(uploaded_file)
				st.session_state.last_source_info = {
					"mode": "upload",
					"file_name": uploaded_file.name,
				}

				run_analysis(
					file_path=file_path,
					selected_checks=sidebar["selected_checks"],
					export_excel=sidebar["export_excel"],
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
				)

				add_saved_campaign_abbreviation(campaign_abbreviation)

	except CampaignDownloadError as exc:
		st.error(f"Download failed: {exc}")
	except Exception as exc:
		st.exception(exc)


def _render_chat() -> None:
	for message in st.session_state.messages:
		with st.chat_message(message["role"]):
			st.markdown(message["content"])

	result = st.session_state.result
	if not result:
		st.info("Choose a campaign source and click **Analyze campaign** to begin.")
		return

	render_issues_panel(result)

	user_question = st.chat_input("Ask about this campaign check result...")
	if user_question:
		st.session_state.messages.append({"role": "user", "content": user_question})
		answer = answer_question(user_question, result)
		st.session_state.messages.append({"role": "assistant", "content": answer})
		st.rerun()


def main() -> None:
	init_state()

	sidebar = render_sidebar()
	_handle_run(sidebar)
	_render_source_info()
	_render_chat()


if __name__ == "__main__":
	main()