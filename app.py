from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

from app_config import load_app_config
from app_storage import (
	add_saved_campaign_abbreviation,
	delete_password,
	get_cookie_file,
	load_password,
	load_settings,
	save_password,
	save_settings,
)
from campaign_downloader import CampaignDownloadError, download_campaign_xlsx
from checker_wrapper.checker_wrapper import (
	CONSISTENCY,
	REACHABILITY,
	SECRETS,
	SPELLCHECKER,
	TARGETPOINTSREACHABLE,
	TTMSTRUCTURE,
	VISUALIZATIONINTERN,
	explain_ttm,
	run_campaign_checks,
	summarize_result,
)

st.set_page_config(page_title="GameBus Campaign Assistant", page_icon="🩺", layout="wide")

CHECK_OPTIONS = [
	REACHABILITY,
	CONSISTENCY,
	VISUALIZATIONINTERN,
	TARGETPOINTSREACHABLE,
	SECRETS,
	TTMSTRUCTURE,
]

FRIENDLY_NAMES = {
	REACHABILITY: "Reachability",
	CONSISTENCY: "Consistency",
	VISUALIZATIONINTERN: "Visualization internals",
	TARGETPOINTSREACHABLE: "Target points reachable",
	SECRETS: "Secrets",
	TTMSTRUCTURE: "TTM structure",
	SPELLCHECKER: "Spellchecker",
}

PREVIEW_LIMIT_MULTI_CHECK_PANEL = 10
PREVIEW_LIMIT_MULTI_CHECK_CHAT = 20
FULL_RENDER_LIMIT_SINGLE_CHECK = 200


def save_uploaded_file(uploaded_file) -> Path:
	temp_dir = Path(tempfile.gettempdir()) / "gamebus_campaign_assistant_uploads"
	temp_dir.mkdir(parents=True, exist_ok=True)
	file_path = temp_dir / uploaded_file.name
	file_path.write_bytes(uploaded_file.getbuffer())
	return file_path


def format_issue(issue: Dict[str, Any]) -> str:
	wave_note = "active wave" if issue.get("active_wave") else "inactive / non-active wave"
	challenge = issue.get("challenge") or "(no challenge name)"
	visualization = issue.get("visualization") or "(no visualization)"
	return (
		f"- **{challenge}** in **{visualization}** ({wave_note})\n"
		f"  - {issue.get('message')}\n"
		f"  - Edit URL: {issue.get('url')}"
	)


def issues_for_check(result: Dict[str, Any], check_name: str) -> List[Dict[str, Any]]:
	return result.get("issues_by_check", {}).get(check_name, [])


def issue_list_tail_message(
	total_count: int,
	shown_count: int,
	excel_report_available: bool,
	single_check_mode: bool,
) -> Optional[str]:
	hidden_count = total_count - shown_count
	if hidden_count <= 0:
		return None

	suggestions = []
	if excel_report_available:
		suggestions.append("download the Excel issue report for the full list")
	else:
		suggestions.append("To see all issues, re-run with **Generate downloadable Excel issue report** enabled")

	if not single_check_mode:
		suggestions.append("select only one check in the sidebar and re-run")

	suggestion_text = " or ".join(suggestions)
	return f"... and **{hidden_count} more**.\n\nSuggestion: {suggestion_text}."


def build_issue_markdown_list(
	issues: List[Dict[str, Any]],
	shown_count: int,
	excel_report_available: bool,
	single_check_mode: bool,
) -> str:
	lines = []
	for issue in issues[:shown_count]:
		lines.append(format_issue(issue))

	tail = issue_list_tail_message(
		total_count=len(issues),
		shown_count=shown_count,
		excel_report_available=excel_report_available,
		single_check_mode=single_check_mode,
	)
	if tail:
		lines.append(tail)

	return "\n".join(lines)


def answer_question(question: str, result: Dict[str, Any]) -> str:
	q = question.lower().strip()

	if any(x in q for x in ["summary", "summarize", "overview"]):
		return summarize_result(result)

	if "failed" in q and "check" in q:
		failed = result["summary"]["failed_checks"]
		if not failed:
			return "No checks failed."
		return "Failed checks: " + ", ".join(f"`{x}`" for x in failed)

	if "fix first" in q or "priority" in q or "priorit" in q:
		issues = result.get("prioritized_issues", [])[:5]
		if not issues:
			return "There are no issues to prioritize."
		lines = ["I would fix these first:"]
		for issue in issues:
			lines.append(format_issue(issue))
		return "\n".join(lines)

	if "ttm" in q and ("explain" in q or "what" in q or "mean" in q):
		return explain_ttm()

	single_check_mode = len(result.get("checks_run", [])) == 1
	excel_report_available = bool(result.get("excel_report_path"))

	for check_name in CHECK_OPTIONS + [SPELLCHECKER]:
		if check_name in q:
			issues = issues_for_check(result, check_name)
			friendly = FRIENDLY_NAMES.get(check_name, check_name)

			if not issues:
				return f"I found no {friendly.lower()} issues."

			if single_check_mode:
				shown_count = min(len(issues), FULL_RENDER_LIMIT_SINGLE_CHECK)
			else:
				shown_count = min(len(issues), PREVIEW_LIMIT_MULTI_CHECK_CHAT)

			lines = [f"Here are the **{friendly}** issues:"]
			lines.append(
				build_issue_markdown_list(
					issues=issues,
					shown_count=shown_count,
					excel_report_available=excel_report_available,
					single_check_mode=single_check_mode,
				)
			)

			if single_check_mode and len(issues) > FULL_RENDER_LIMIT_SINGLE_CHECK:
				lines.append(
					f"\nSafeguard: only the first **{FULL_RENDER_LIMIT_SINGLE_CHECK}** issues are shown here."
				)

			if check_name == TTMSTRUCTURE:
				lines.append("\n" + explain_ttm())

			return "\n".join(lines)

	if "active wave" in q:
		active = [i for i in result.get("prioritized_issues", []) if i.get("active_wave")]
		if not active:
			return "I found no prioritized issues in currently active waves."
		lines = ["These prioritized issues are in active waves:"]
		for issue in active[:10]:
			lines.append(format_issue(issue))
		return "\n".join(lines)

	return (
		"I can help with:\n"
		"- `summary` or `overview`\n"
		"- `which checks failed`\n"
		"- `show ttm issues`\n"
		"- `show reachability issues`\n"
		"- `show consistency issues`\n"
		"- `show targetpointsreachable issues`\n"
		"- `what should I fix first`\n"
		"- `explain ttm`"
	)


def init_state():
	if "app_config" not in st.session_state:
		st.session_state.app_config = load_app_config()
	if "settings" not in st.session_state:
		st.session_state.settings = load_settings()
	if "messages" not in st.session_state:
		st.session_state.messages = []
	if "result" not in st.session_state:
		st.session_state.result = None
	if "last_source_info" not in st.session_state:
		st.session_state.last_source_info = None
	if "current_campaign_abbreviation" not in st.session_state:
		st.session_state.current_campaign_abbreviation = st.session_state.settings.get(
			"last_campaign_abbreviation", ""
		)
	if "current_email" not in st.session_state:
		st.session_state.current_email = st.session_state.settings.get("email", "")


def run_analysis(
	file_path: Path,
	selected_checks: List[str],
	export_excel: bool,
):
	result = run_campaign_checks(file_path, checks=selected_checks, export_excel=export_excel)
	st.session_state.result = result
	st.session_state.messages = [
		{"role": "assistant", "content": summarize_result(result)}
	]


init_state()

with st.sidebar:
	st.markdown("### GameBus Campaign Assistant")

	with st.expander("Credentials & session", expanded=True):
		saved_email = st.session_state.settings.get("email", "").strip()
		saved_password = load_password(saved_email) if saved_email else None
		cookie_exists = get_cookie_file().exists()
		is_authenticated = bool(saved_email and (saved_password or cookie_exists))

		remember_credentials = st.checkbox(
			"Remember credentials",
			value=bool(st.session_state.settings.get("remember_credentials", True)),
		)

		if is_authenticated:
			st.success(f"Saved credentials/session available for: **{saved_email}**")

			col_auth_1, col_auth_2 = st.columns(2)
			with col_auth_1:
				if st.button("Save preferences", use_container_width=True):
					settings = st.session_state.settings.copy()
					settings["remember_credentials"] = remember_credentials
					save_settings(settings)
					st.session_state.settings = settings
					st.success("Preferences saved.")

			with col_auth_2:
				if st.button("Clear saved session", use_container_width=True):
					delete_password(saved_email)
					cookie_file = get_cookie_file()
					if cookie_file.exists():
						cookie_file.unlink()

					settings = st.session_state.settings.copy()
					settings["email"] = ""
					save_settings(settings)
					st.session_state.settings = settings
					st.session_state.current_email = ""
					st.rerun()

		else:
			current_email = st.text_input(
				"Email",
				value=st.session_state.current_email,
			)
			st.session_state.current_email = current_email

			password_to_save = st.text_input(
				"Password",
				value="",
				type="password",
			)

			if st.button("Save credentials", use_container_width=True):
				settings = st.session_state.settings.copy()
				settings["email"] = current_email.strip()
				settings["remember_credentials"] = remember_credentials
				save_settings(settings)
				st.session_state.settings = settings

				if remember_credentials and password_to_save:
					save_password(current_email, password_to_save)

				st.rerun()

	with st.expander("Campaign source", expanded=True):
		source_mode = st.radio(
			"Choose input mode",
			options=["Upload Excel file", "Download from GameBus"],
			index=0 if st.session_state.settings.get("last_source_mode") == "Upload Excel file" else 1,
		)

		uploaded_file = None

		if source_mode == "Upload Excel file":
			uploaded_file = st.file_uploader(
				"Upload a campaign Excel export",
				type=["xlsx"],
				accept_multiple_files=False,
			)
		else:
			saved_abbreviations = st.session_state.settings.get("saved_campaign_abbreviations", [])
			current_abbr = st.session_state.current_campaign_abbreviation.strip()

			options = saved_abbreviations.copy()
			if current_abbr and current_abbr not in options:
				options = [current_abbr] + options

			if not options:
				options = [""]

			# choose the currently remembered abbreviation as default if possible
			default_index = 0
			if current_abbr and current_abbr in options:
				default_index = options.index(current_abbr)

			selected_or_typed_abbreviation = st.selectbox(
				"Campaign abbreviation",
				options=options,
				index=default_index,
				accept_new_options=True,
				placeholder="Type or select a campaign abbreviation",
				help="Type a new campaign abbreviation or select one that was loaded successfully before.",
			)

			if selected_or_typed_abbreviation is None:
				selected_or_typed_abbreviation = ""

			st.session_state.current_campaign_abbreviation = selected_or_typed_abbreviation.strip()

	st.divider()
	st.header("Checks")

	selected_checks = st.multiselect(
		"Checks to run",
		options=CHECK_OPTIONS,
		default=CHECK_OPTIONS,
		format_func=lambda x: FRIENDLY_NAMES.get(x, x),
	)

	export_excel = st.checkbox("Generate downloadable Excel issue report", value=False)

	run_clicked = st.button("Analyze campaign", type="primary", use_container_width=True)

if run_clicked:
	if not selected_checks:
		st.error("Please select at least one check.")
	else:
		try:
			with st.spinner("Preparing campaign file..."):
				if source_mode == "Upload Excel file":
					if not uploaded_file:
						st.error("Please upload a single .xlsx campaign export first.")
						st.stop()

					file_path = save_uploaded_file(uploaded_file)
					st.session_state.last_source_info = {
						"mode": "upload",
						"file_name": uploaded_file.name,
					}

					run_analysis(
						file_path=file_path,
						selected_checks=selected_checks,
						export_excel=export_excel,
					)

					settings = st.session_state.settings.copy()
					settings["last_source_mode"] = "Upload Excel file"
					save_settings(settings)
					st.session_state.settings = settings

				else:
					settings = st.session_state.settings.copy()
					settings["remember_credentials"] = remember_credentials
					settings["last_campaign_abbreviation"] = st.session_state.current_campaign_abbreviation
					settings["last_source_mode"] = "Download from GameBus"
					save_settings(settings)
					st.session_state.settings = settings

					base_url = st.session_state.app_config.get("campaigns_base_url", "").strip()
					email = st.session_state.settings.get("email", "").strip()
					password = load_password(email) if remember_credentials else None

					file_path = download_campaign_xlsx(
						base_url=base_url,
						campaign_abbreviation=st.session_state.current_campaign_abbreviation,
						email=email or None,
						password=password,
						cookie_file=get_cookie_file(),
					)

					st.session_state.last_source_info = {
						"mode": "download",
						"base_url": base_url,
						"campaign_abbreviation": st.session_state.current_campaign_abbreviation,
						"file_name": file_path.name,
						"auto_refreshed": False,
					}

					run_analysis(
						file_path=file_path,
						selected_checks=selected_checks,
						export_excel=export_excel,
					)

					settings["saved_campaign_abbreviations"] = sorted(
						list(set(settings.get("saved_campaign_abbreviations", [])) | {st.session_state.current_campaign_abbreviation})
					)
					save_settings(settings)
					st.session_state.settings = settings
					add_saved_campaign_abbreviation(st.session_state.current_campaign_abbreviation)

		except CampaignDownloadError as exc:
			st.error(f"Download failed: {exc}")
		except Exception as exc:
			st.exception(exc)

if st.session_state.last_source_info:
	source_info = st.session_state.last_source_info
	if source_info["mode"] == "upload":
		st.info(f"Current campaign source: uploaded file **{source_info['file_name']}**")
	else:
		tag = " (auto-refreshed)" if source_info.get("auto_refreshed") else ""
		st.info(
			f"Current campaign source: downloaded for campaign **{source_info['campaign_abbreviation']}**{tag}"
		)

for message in st.session_state.messages:
	with st.chat_message(message["role"]):
		st.markdown(message["content"])

if st.session_state.result:
	result = st.session_state.result
	total_issues = result["summary"]["total_issues"]

	with st.expander("Quick overview", expanded=False):
		st.write(result["summary"])

	if result.get("excel_report_path"):
		report_path = Path(result["excel_report_path"])
		if report_path.exists():
			st.download_button(
				label="Download Excel issue report",
				data=report_path.read_bytes(),
				file_name=report_path.name,
				mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				use_container_width=False,
			)

	if total_issues > 0:
		single_check_mode = len(result.get("checks_run", [])) == 1
		excel_report_available = bool(result.get("excel_report_path"))

		with st.expander("Issues by check type", expanded=True):
			for check_name in result["checks_run"]:
				issues = result["issues_by_check"].get(check_name, [])
				friendly_name = FRIENDLY_NAMES.get(check_name, check_name)

				st.markdown(f"### {friendly_name} ({len(issues)})")

				if not issues:
					st.write("No issues.")
					continue

				if single_check_mode:
					with st.expander(f"Open full list of {friendly_name} issues", expanded=False):
						shown_count = min(len(issues), FULL_RENDER_LIMIT_SINGLE_CHECK)
						st.markdown(
							build_issue_markdown_list(
								issues=issues,
								shown_count=shown_count,
								excel_report_available=excel_report_available,
								single_check_mode=True,
							)
						)
						if len(issues) > FULL_RENDER_LIMIT_SINGLE_CHECK:
							st.info(
								f"Safeguard: only the first {FULL_RENDER_LIMIT_SINGLE_CHECK} issues are rendered here."
							)
				else:
					shown_count = min(len(issues), PREVIEW_LIMIT_MULTI_CHECK_PANEL)
					st.markdown(
						build_issue_markdown_list(
							issues=issues,
							shown_count=shown_count,
							excel_report_available=excel_report_available,
							single_check_mode=False,
						)
					)

	user_question = st.chat_input("Ask about this campaign check result...")
	if user_question:
		st.session_state.messages.append({"role": "user", "content": user_question})
		answer = answer_question(user_question, result)
		st.session_state.messages.append({"role": "assistant", "content": answer})
		st.rerun()
else:
	st.info("Choose a campaign source and click **Analyze campaign** to begin.")