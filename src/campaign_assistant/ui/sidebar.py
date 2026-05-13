from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any, Dict

import streamlit as st

from campaign_assistant.checker import build_check_catalog
from campaign_assistant.checker.preflight import build_capability_summary_for_file
from campaign_assistant.downloader import CampaignDownloadError, download_campaign_xlsx
from campaign_assistant.storage import (
    delete_cookie_file,
    delete_password,
    get_cookie_file,
    load_password,
    save_password,
    save_settings,
)
from campaign_assistant.ui.check_picker import render_check_picker
from campaign_assistant.ui.privacy_diagnostics import render_privacy_diagnostics_sidebar
from campaign_assistant.ui.workspace_readiness import build_workspace_readiness_model


def _source_mode_index(options: list[str], last_value: str) -> int:
    try:
        return options.index(last_value)
    except ValueError:
        return 0


def _sidebar_workspace_readiness_hint(result: dict[str, Any] | None) -> None:
    model = build_workspace_readiness_model(result)

    if not model["has_readiness"]:
        return

    if model["status"] == "needs_annotations":
        st.caption("Some stronger progression checks are disabled until task-role annotations are added.")
    elif model["status"] == "ready":
        st.caption("Progression semantics checks are ready in this workspace.")


def _uploaded_source_signature(uploaded_file) -> str | None:
    if uploaded_file is None:
        return None

    getvalue = getattr(uploaded_file, "getvalue", None)
    if not callable(getvalue):
        return None

    try:
        payload = getvalue()
    except Exception:
        return None

    if isinstance(payload, memoryview):
        payload = payload.tobytes()
    elif isinstance(payload, bytearray):
        payload = bytes(payload)

    if not isinstance(payload, bytes):
        return None

    return f"upload:{hashlib.sha256(payload).hexdigest()}"


def _download_source_signature(campaign_abbreviation: str) -> str | None:
    campaign_abbreviation = (campaign_abbreviation or "").strip()
    if not campaign_abbreviation:
        return None
    return f"download:{campaign_abbreviation.lower()}"


def _clear_check_picker_state() -> None:
    st.session_state.pop("selected_checks_override", None)
    for definition in build_check_catalog():
        st.session_state.pop(f"check-picker-{definition.check_id}", None)
        st.session_state.pop(f"show-check-hint-{definition.check_id}", None)


def _sync_check_picker_source(source_signature: str | None) -> None:
    previous_signature = st.session_state.get("check_picker_source_signature")
    if source_signature != previous_signature:
        _clear_check_picker_state()
        st.session_state["check_picker_source_signature"] = source_signature


def _preview_upload_path(uploaded_file) -> Path:
    payload = uploaded_file.getvalue()
    digest = hashlib.sha256(payload).hexdigest()
    preview_dir = Path(tempfile.gettempdir()) / "gamebus_campaign_assistant_preflight"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_path = preview_dir / f"{digest}-{uploaded_file.name}"
    if not preview_path.exists():
        preview_path.write_bytes(payload)
    return preview_path


def _preflight_upload_summary(uploaded_file) -> tuple[str | None, dict[str, Any] | None, str | None]:
    source_signature = _uploaded_source_signature(uploaded_file)
    if not source_signature:
        return None, None, None

    cached_signature = st.session_state.get("preflight_source_signature")
    cached_summary = st.session_state.get("preflight_capability_summary")
    cached_error = st.session_state.get("preflight_capability_error")

    if cached_signature == source_signature:
        return source_signature, cached_summary, cached_error

    try:
        preview_path = _preview_upload_path(uploaded_file)
        summary = build_capability_summary_for_file(file_path=preview_path)
        error = None
    except Exception as exc:
        summary = None
        error = f"Could not inspect uploaded workbook yet: {exc}"

    st.session_state["preflight_source_signature"] = source_signature
    st.session_state["preflight_capability_summary"] = summary
    st.session_state["preflight_capability_error"] = error
    return source_signature, summary, error


def _preflight_download_summary(
    *,
    campaign_abbreviation: str,
    settings: dict[str, Any],
    app_config: dict[str, Any],
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    source_signature = _download_source_signature(campaign_abbreviation)
    if not source_signature:
        return None, None, None

    cached_signature = st.session_state.get("preflight_source_signature")
    cached_summary = st.session_state.get("preflight_capability_summary")
    cached_error = st.session_state.get("preflight_capability_error")

    if cached_signature == source_signature:
        return source_signature, cached_summary, cached_error

    base_url = str(app_config.get("campaigns_base_url", "") or "").strip()
    email = str(settings.get("email", "") or "").strip()
    remember_credentials = bool(settings.get("remember_credentials", True))
    password = load_password(email) if (remember_credentials and email) else None

    if not base_url:
        error = "Cannot inspect this campaign yet because campaigns_base_url is empty."
        st.session_state["preflight_source_signature"] = source_signature
        st.session_state["preflight_capability_summary"] = None
        st.session_state["preflight_capability_error"] = error
        return source_signature, None, error

    try:
        preview_path = download_campaign_xlsx(
            base_url=base_url,
            campaign_abbreviation=campaign_abbreviation,
            email=email or None,
            password=password,
            cookie_file=get_cookie_file(),
        )
        summary = build_capability_summary_for_file(file_path=preview_path)
        error = None
    except CampaignDownloadError as exc:
        summary = None
        error = f"Could not inspect this campaign yet: {exc}"
    except Exception as exc:
        summary = None
        error = f"Could not inspect this campaign yet: {exc}"

    st.session_state["preflight_source_signature"] = source_signature
    st.session_state["preflight_capability_summary"] = summary
    st.session_state["preflight_capability_error"] = error
    return source_signature, summary, error


def _synthetic_result_from_capability_summary(capability_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "assistant_meta": {
            "capability_summary": capability_summary,
        }
    }


def _effective_check_picker_result(
    *,
    result: dict[str, Any] | None,
    source_mode: str,
    uploaded_file,
    campaign_abbreviation: str,
    settings: dict[str, Any],
    app_config: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    analyzed_signature = st.session_state.get("last_analyzed_source_signature")

    if source_mode == "Upload Excel file":
        source_signature, capability_summary, error = _preflight_upload_summary(uploaded_file)
        if source_signature and source_signature == analyzed_signature and isinstance(result, dict):
            return result, source_signature, error
        if isinstance(capability_summary, dict):
            return _synthetic_result_from_capability_summary(capability_summary), source_signature, error
        return None, source_signature, error

    source_signature, capability_summary, error = _preflight_download_summary(
        campaign_abbreviation=campaign_abbreviation,
        settings=settings,
        app_config=app_config,
    )
    if source_signature and source_signature == analyzed_signature and isinstance(result, dict):
        return result, source_signature, error
    if isinstance(capability_summary, dict):
        return _synthetic_result_from_capability_summary(capability_summary), source_signature, error
    return None, source_signature, error


def render_sidebar() -> Dict[str, Any]:
    settings = st.session_state.settings
    uploaded_file = None
    result = st.session_state.get("result")
    current_campaign_abbreviation = st.session_state.get("current_campaign_abbreviation", "")

    privacy_report = {}
    if isinstance(result, dict):
        assistant_meta = dict(result.get("assistant_meta", {}) or {})
        privacy_report = dict(assistant_meta.get("privacy_report", {}) or {})

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
                current_campaign_abbreviation = ""
                st.session_state.current_campaign_abbreviation = ""
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
                current_campaign_abbreviation = campaign_abbreviation

        check_picker_result, source_signature, preflight_error = _effective_check_picker_result(
            result=result,
            source_mode=source_mode,
            uploaded_file=uploaded_file,
            campaign_abbreviation=current_campaign_abbreviation,
            settings=settings,
            app_config=st.session_state.app_config,
        )
        _sync_check_picker_source(source_signature)

        with st.expander("Checks", expanded=True):
            _sidebar_workspace_readiness_hint(check_picker_result)

            if preflight_error:
                st.caption(preflight_error)
            elif source_signature:
                st.caption("Checks below were preselected from the currently chosen campaign source.")

            selected_checks = render_check_picker(check_picker_result)

        with st.expander("Display", expanded=False):
            show_agent_trace = st.checkbox(
                "Show agent reasoning trace",
                value=bool(st.session_state.get("show_agent_trace", False)),
                help="Useful for demos and debugging. Hidden by default for normal users.",
            )
            st.session_state.show_agent_trace = show_agent_trace

        run_clicked = st.button("Analyze campaign", type="primary", use_container_width=True)

        excel_path_str = result.get("excel_report_path") if isinstance(result, dict) else None
        excel_path = Path(excel_path_str) if excel_path_str else None
        total_issues = result.get("summary", {}).get("total_issues", 0) if isinstance(result, dict) else 0

        if excel_path and excel_path.exists() and total_issues > 0:
            with open(excel_path, "rb") as f:
                st.download_button(
                    label="📥 Download Excel Report",
                    data=f,
                    file_name=excel_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    disabled=False,
                    key="sidebar_download_report",
                )
        else:
            st.button(
                label="📥 Download Excel Report",
                disabled=True,
                use_container_width=True,
                key="sidebar_download_report_disabled",
            )

        render_privacy_diagnostics_sidebar(privacy_report)

    settings["last_source_mode"] = source_mode
    save_settings(settings)

    return {
        "run_clicked": run_clicked,
        "source_mode": source_mode,
        "uploaded_file": uploaded_file,
        "selected_checks": selected_checks,
        "export_excel": True,
        "show_agent_trace": st.session_state.get("show_agent_trace", False),
    }