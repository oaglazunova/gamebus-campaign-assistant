from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import streamlit as st

from campaign_assistant.checker import run_campaign_checks, summarize_result


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
) -> None:
    """
    Run campaign analysis and store the result in Streamlit session state.
    Also appends a short assistant summary to the chat history.
    """
    result = run_campaign_checks(
        file_path=file_path,
        checks=selected_checks,
        export_excel=export_excel,
    )

    st.session_state.current_file_path = str(file_path)
    st.session_state.result = result
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": summarize_result(result),
        }
    )