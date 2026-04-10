from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import streamlit as st

from campaign_assistant.checker import run_campaign_checks, summarize_result
from campaign_assistant.session_logging import SessionLogger


def save_uploaded_file(uploaded_file) -> Path:
    """
    Save an uploaded Streamlit file to a unique temporary location and return its path.
    """
    temp_dir = Path(tempfile.gettempdir()) / "gamebus_campaign_assistant_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)

    temp_path = temp_dir / f"{uuid.uuid4()}-{uploaded_file.name}"
    temp_path.write_bytes(uploaded_file.getbuffer())
    return temp_path


def run_analysis(
    file_path: str | Path,
    selected_checks: list[str],
    export_excel: bool,
    logger: SessionLogger | None = None,
) -> None:
    """
    Run campaign analysis and store the result in Streamlit session state.
    Also appends a short assistant summary to the chat history.
    """
    if logger is not None:
        logger.log_analysis_requested(
            file_path=str(file_path),
            selected_checks=selected_checks,
            export_excel=export_excel,
        )

    try:
        result = run_campaign_checks(
            file_path=file_path,
            checks=selected_checks,
            export_excel=export_excel,
        )

        st.session_state.current_file_path = str(file_path)
        st.session_state.result = result

        summary = summarize_result(result)
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": summary,
            }
        )

        if logger is not None:
            logger.log_analysis_completed(
                file_path=str(file_path),
                selected_checks=selected_checks,
                export_excel=export_excel,
                result_summary=result.get("summary", {}),
                assistant_summary=summary,
                excel_report_path=result.get("excel_report_path"),
            )

    except Exception as exc:
        if logger is not None:
            logger.log_error(
                where="run_analysis",
                exc=exc,
                extra={
                    "file_path": str(file_path),
                    "selected_checks": selected_checks,
                    "export_excel": export_excel,
                },
            )
        raise