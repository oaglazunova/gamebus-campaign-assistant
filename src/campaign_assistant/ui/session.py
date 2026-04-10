from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from campaign_assistant.config import load_app_config
from campaign_assistant.session_logging import SessionLogger
from campaign_assistant.storage import load_settings


def _default_session_state() -> Dict[str, Any]:
    """
    Default Streamlit session-state values for the app.
    """
    return {
        "app_config": load_app_config(),
        "settings": load_settings(),
        "messages": [],
        "result": None,
        "current_file_path": None,
        "current_campaign_abbreviation": "",
        "last_source_info": None,
        "logger": SessionLogger(log_dir="logs"),
        "session_context_logged": False,
    }


def init_state() -> None:
    """
    Initialize Streamlit session state once per session.
    Existing values are preserved.
    """
    defaults = _default_session_state()
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
