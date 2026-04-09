from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from campaign_assistant.checker import DEFAULT_CHECKS, FRIENDLY_CHECK_NAMES
from campaign_assistant.storage import (
	delete_cookie_file,
	delete_password,
	load_password,
	save_password,
	save_settings,
)


def _source_mode_index(options: list[str], last_value: str) -> int:
	try:
		return options.index(last_value)
	except ValueError:
		return 0


def render_sidebar() -> Dict[str, Any]:
	"""
	Render the Streamlit sidebar and return the selected UI state.
	"""
	settings = st.session_state.settings
	uploaded_file = None

	with st.sidebar:
		st.markdown("### GameBus Campaign Assistant")

		source_options = ["Upload Excel file", "Download from GameBus"]
		source_mode = settings.get("last_source_mode", "Upload Excel file")		

		email_prefill = settings.get("email", "").strip()
		saved_password = load_password(email_prefill) if email_prefill else None
		credentials_ready = bool(email_prefill and saved_password)

		with st.expander("Credentials", expanded=not credentials_ready):
			email = st.text_input(
				"Email",
				value=settings.get("email", ""),
				key="sidebar_email",
			)

			saved_password = load_password(email.strip()) if email.strip() else None
			password_default = saved_password if saved_password else ""

			password = st.text_input(
				"Password",
				type="password",
				value=password_default,
				key="sidebar_password",
			)

			remember_credentials = st.checkbox(
				"Remember credentials",
				value=bool(settings.get("remember_credentials", True)),
				key="sidebar_remember_credentials",
			)

			settings["email"] = email.strip()
			settings["remember_credentials"] = remember_credentials
			save_settings(settings)

			if remember_credentials and email.strip() and password:
				save_password(email.strip(), password)
			elif email.strip() and not remember_credentials:
				delete_password(email.strip())
				delete_cookie_file()

			col1, col2 = st.columns(2)

			with col1:
				if st.button("Clear session"):
					delete_cookie_file()
					st.success("Session cookies cleared.")

			with col2:
				if st.button("Delete saved credentials"):
					if email.strip():
						delete_password(email.strip())
					settings["remember_credentials"] = False
					save_settings(settings)
					st.success("Saved credentials deleted.")

		with st.expander("Campaign source", expanded=True):
			source_mode = st.radio(
				"Choose input source",
				source_options,
				index=_source_mode_index(source_options, source_mode),
			)

			if source_mode == "Upload Excel file":
				uploaded_file = st.file_uploader(
					"Upload GameBus campaign Excel export",
					type=["xlsx"],
					accept_multiple_files=False,
				)
			else:
				abbreviations = settings.get("saved_campaign_abbreviations", [])
				current_abbr = st.session_state.get("current_campaign_abbreviation", "")

				campaign_abbreviation = st.selectbox(
					"Campaign abbreviation",
					options=abbreviations,
					index=abbreviations.index(current_abbr) if current_abbr in abbreviations else None,
					placeholder="Select or type a campaign abbreviation",
					accept_new_options=True,
					key="sidebar_campaign_abbreviation",
				)

				campaign_abbreviation = (campaign_abbreviation or "").strip()
				st.session_state.current_campaign_abbreviation = campaign_abbreviation
				settings["last_campaign_abbreviation"] = campaign_abbreviation

		with st.expander("Checks", expanded=True):
			selected_checks = st.multiselect(
				"Checks to run",
				options=DEFAULT_CHECKS,
				default=DEFAULT_CHECKS,
				format_func=lambda name: FRIENDLY_CHECK_NAMES.get(name, name),
			)

			export_excel = st.checkbox(
				"Generate Excel report",
				value=False,
			)

		run_clicked = st.button("Analyze campaign", type="primary", use_container_width=True)

	settings["last_source_mode"] = source_mode
	save_settings(settings)

	return {
		"run_clicked": run_clicked,
		"source_mode": source_mode,
		"uploaded_file": uploaded_file,
		"selected_checks": selected_checks,
		"export_excel": export_excel,
	}