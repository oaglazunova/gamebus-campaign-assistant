from __future__ import annotations

import streamlit as st

from campaign_assistant.downloader import CampaignDownloadError, download_campaign_xlsx
from campaign_assistant.file_utils import sha256_file
from campaign_assistant.storage import add_saved_campaign_abbreviation, get_cookie_file, load_password
from campaign_assistant.ui.actions import run_analysis, save_uploaded_file
from campaign_assistant.ui.assistant_chat import (
	get_assistant_response,
	render_conversation_message,
	focused_finding_for_quick_action,
	quick_action_focuses_top_finding,
	render_assistant_guide_panel,
	render_assistant_page_status,
	render_llm_status_panel,
)
from campaign_assistant.ui.findings import (
	render_findings_overview_panel,
	render_issues_panel,
)
from campaign_assistant.ui.overview import render_analysis_overview
from campaign_assistant.ui.session import init_state
from campaign_assistant.ui.sidebar import render_sidebar
from campaign_assistant.ui.copy import WORKFLOW_PAGE_COPY


st.set_page_config(page_title="GameBus Campaign Assistant", page_icon="🩺", layout="wide")

_WORKFLOW_PAGES = ["Overview", "Findings", "Assistant"]




def _render_page_intro(title: str, description: str) -> None:
	st.markdown(f"## {title}")
	st.caption(description)


def _render_scroll_anchor(
    anchor_id: str,
) -> None:
    st.html(
        f'<span id="{anchor_id}"></span>'
    )


def _render_scroll_button(
    label: str,
    target: str,
    *,
    align: str = "flex-start",
) -> None:
    st.html(
        f"""
        <div style="
            display:flex;
            justify-content:{align};
        ">
            <a
                href="#{target}"
                target="_self"
                style="
                    display:inline-flex;
                    align-items:center;
                    padding:0.35rem 0.75rem;
                    border:
                        1px solid
                        rgba(128,128,128,0.45);
                    border-radius:0.5rem;
                    color:inherit;
                    text-decoration:none;
                    font-size:0.9rem;
                "
            >
                {label}
            </a>
        </div>
        """
    )



def _render_floating_top_button(
    target: str,
    *,
    above_chat_input: bool = False,
) -> None:
    bottom = (
        "7.25rem"
        if above_chat_input
        else "1.25rem"
    )
    mobile_bottom = (
        "6.5rem"
        if above_chat_input
        else "0.75rem"
    )

    st.html(
        f"""
        <a
            id="floating-back-to-top"
            href="#{target}"
            target="_self"
            aria-label="Back to top"
            title="Back to top"
        >
            ↑
        </a>

        <style>
            #floating-back-to-top {{
                position: fixed !important;
                right: 1.25rem;
                bottom: {bottom};
                z-index: 999;

                display: flex;
                align-items: center;
                justify-content: center;

                width: 2.75rem;
                height: 2.75rem;
                border-radius: 50%;

                background:
                    var(--primary-color, #ff4b4b);
                color: #ffffff;

                font-size: 1.45rem;
                font-weight: 700;
                line-height: 1;
                text-decoration: none;

                box-shadow:
                    0 0.2rem 0.75rem
                    rgba(0, 0, 0, 0.25);

                cursor: pointer;
                pointer-events: auto;
            }}

            #floating-back-to-top:hover {{
                transform: translateY(-2px);
                box-shadow:
                    0 0.35rem 0.95rem
                    rgba(0, 0, 0, 0.3);
            }}

            @media (max-width: 768px) {{
                #floating-back-to-top {{
                    right: 0.75rem;
                    bottom: {mobile_bottom};
                }}
            }}
        </style>
        """
    )




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


def _update_source_info() -> None:
	if isinstance(st.session_state.get("result"), dict):
		st.session_state.result.setdefault("assistant_meta", {}).update(
			{
				"source_mode": st.session_state.last_source_info.get("mode"),
				"source_label": st.session_state.last_source_info.get("file_name")
								or st.session_state.last_source_info.get("campaign_abbreviation"),
			}
		)

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

				st.session_state["last_analyzed_source_signature"] = f"upload:{file_hash}"

				run_analysis(
					file_path=file_path,
					selected_checks=sidebar["selected_checks"],
					export_excel=sidebar["export_excel"],
					logger=logger,
				)

				_update_source_info()

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

				st.session_state["last_analyzed_source_signature"] = f"download:{campaign_abbreviation.lower()}"

				run_analysis(
					file_path=file_path,
					selected_checks=sidebar["selected_checks"],
					export_excel=sidebar["export_excel"],
					logger=logger,
				)

				_update_source_info()

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

	render_analysis_overview(result, show_title=False)


def _render_findings_page(result) -> None:
    _render_page_intro(
        "Findings",
        WORKFLOW_PAGE_COPY["Findings"]["description"],
    )

    if not result:
        _render_empty_workflow_state("Findings")
        return

    render_findings_overview_panel(result)
    render_issues_panel(result)


def _handle_pending_assistant_prompt(logger, result) -> None:
	pending = st.session_state.pop("assistant_pending_question", None)
	quick_action = st.session_state.pop("assistant_pending_quick_action", None)

	if not pending or not result:
		return

	pending = str(pending)
	conversation_history = list(st.session_state.messages)

	focused_finding = focused_finding_for_quick_action(result, quick_action)

	if focused_finding:
		st.session_state["assistant_focused_finding"] = focused_finding
	elif quick_action_focuses_top_finding(quick_action):
		st.session_state.pop("assistant_focused_finding", None)

	logger.log_chat_user(pending)

	st.session_state.messages.append(
		{
				"role": "user",
				"content": pending,
			}
		)

	response = get_assistant_response(
		pending,
		result,
		conversation_history=conversation_history,
		quick_action=quick_action,
		focused_finding=st.session_state.get(
			"assistant_focused_finding"
		),
	)

	logger.log_chat_assistant(
		response.text,
		agent_name=response.agent_name,
		intent=response.intent,
		answer_source=response.answer_source,
		guard_applied=response.guard_applied,
		guard_reason=response.guard_reason,
	)

	st.session_state.messages.append({
		"role": "assistant",
		"content": response.text,
		"agent_name": response.agent_name,
		"answer_source": response.answer_source,
	})

	st.rerun()


def _render_assistant_page(logger) -> None:
	_render_page_intro(
		"Assistant",
		WORKFLOW_PAGE_COPY[
			"Assistant"
		]["description"],
	)

	result = st.session_state.result

	if not result:
		_render_empty_workflow_state("Assistant")
		return

	render_assistant_page_status(result, len(st.session_state.messages))
	render_llm_status_panel()
	render_assistant_guide_panel(result)

	control_col1, control_col2 = st.columns(
		[1, 4]
	)

	with control_col1:
		if st.button(
				"Reset conversation",
				key="assistant-clear-conversation",
				width="stretch",
		):
			st.session_state.messages = []
			st.session_state.pop(
				"assistant_focused_finding",
				None,
			)
			st.session_state.pop(
				"assistant_pending_quick_action",
				None,
			)
			st.session_state.pop(
				"assistant_pending_question",
				None,
			)
			st.session_state.pop(
				"assistant_notice",
				None,
			)
			st.rerun()

	with control_col2:
		_render_scroll_button(
			"↓ Latest message",
			"assistant-page-bottom",
			align="flex-end",
		)

	_handle_pending_assistant_prompt(logger, result)

	if not st.session_state.messages:
		st.info(
			"No assistant conversation yet. Use a suggested prompt or ask "
			"your own question below."
		)
	else:
		st.markdown("### Conversation")
		for message in st.session_state.messages:
			render_conversation_message(message)

	_render_scroll_anchor(
		"assistant-page-bottom"
	)

	user_question = st.chat_input("Ask about this campaign...")

	if user_question:
		conversation_history = list(st.session_state.messages)

		logger.log_chat_user(user_question)

		st.session_state.messages.append(
			{
				"role": "user",
				"content": user_question,
			}
		)

		response = get_assistant_response(
			user_question,
			result,
			conversation_history=conversation_history,
			focused_finding=st.session_state.get(
				"assistant_focused_finding"
			),
		)

		logger.log_chat_assistant(
			response.text,
			agent_name=response.agent_name,
			intent=response.intent,
			answer_source=response.answer_source,
			guard_applied=response.guard_applied,
			guard_reason=response.guard_reason,
		)

		st.session_state.messages.append({
			"role": "assistant",
			"content": response.text,
			"agent_name": response.agent_name,
			"answer_source": response.answer_source,
		})

		st.rerun()


def main() -> None:
	init_state()
	logger = st.session_state.logger

	sidebar = render_sidebar()
	_handle_run(sidebar, logger)

	_render_source_info()

	result = st.session_state.result
	_sync_main_workflow_focus_from_result(result)

	requested_page = st.session_state.pop(
		"requested_workflow_page",
		None,
	)

	if requested_page in _WORKFLOW_PAGES:
		st.session_state[
			"main_workflow_page"
		] = requested_page

	if "main_workflow_page" not in st.session_state:
		st.session_state[
			"main_workflow_page"
		] = "Overview"

	current_page = st.session_state[
		"main_workflow_page"
	]

	if current_page not in _WORKFLOW_PAGES:
		st.session_state[
			"main_workflow_page"
		] = "Overview"

	_render_scroll_anchor(
		"workflow-page-top"
	)

	selected_page = st.radio(
		"Workflow",
		options=_WORKFLOW_PAGES,
		index=None,
		horizontal=True,
		label_visibility="collapsed",
		key="main_workflow_page",
	)

	if result:
		_render_floating_top_button(
			"workflow-page-top",
			above_chat_input=(
					selected_page == "Assistant"
			),
		)

	if selected_page == "Overview":
		_render_overview_page(result)
	elif selected_page == "Findings":
		_render_findings_page(result)
	else:
		_render_assistant_page(logger)


if __name__ == "__main__":
	main()