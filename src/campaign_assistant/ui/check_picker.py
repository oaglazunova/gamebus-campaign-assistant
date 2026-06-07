from __future__ import annotations

from typing import Any

import streamlit as st

from campaign_assistant.checker.check_metadata import check_hint
from campaign_assistant.checker.schema import DEFAULT_CHECKS, FRIENDLY_CHECK_NAMES


def _previous_selected_checks(result: dict[str, Any] | None) -> list[str] | None:
    if not isinstance(result, dict):
        return None

    assistant_meta = dict(result.get("assistant_meta", {}) or {})
    previous = assistant_meta.get("selected_checks")
    if isinstance(previous, list):
        return [str(item) for item in previous]

    checks_run = result.get("checks_run")
    if isinstance(checks_run, list):
        return [str(item) for item in checks_run]

    return None


def _initial_selected_checks(result: dict[str, Any] | None) -> list[str]:
    session_selected = st.session_state.get("selected_checks_override")
    if isinstance(session_selected, list):
        return [str(item) for item in session_selected if str(item) in DEFAULT_CHECKS]

    previous = _previous_selected_checks(result)
    if previous:
        return [item for item in previous if item in DEFAULT_CHECKS]

    return list(DEFAULT_CHECKS)


def _ensure_widget_defaults(selected_checks: list[str]) -> None:
    selected = set(selected_checks)
    for check_id in DEFAULT_CHECKS:
        key = f"check-picker-{check_id}"
        if key not in st.session_state:
            st.session_state[key] = check_id in selected


# def _apply_recommended() -> None:
#     for check_id in DEFAULT_CHECKS:
#         st.session_state[f"check-picker-{check_id}"] = True
#
#
# def _clear_all() -> None:
#     for check_id in DEFAULT_CHECKS:
#         st.session_state[f"check-picker-{check_id}"] = False


def render_check_picker(result: dict[str, Any] | None) -> list[str]:
    """
    Render a simple checklist of deterministic export-based checks.
    """
    selected_checks = _initial_selected_checks(result)
    _ensure_widget_defaults(selected_checks)

    # col1, col2 = st.columns(2)
    #
    # with col1:
    #     if st.button("Use recommended", key="checks-use-recommended", use_container_width=True):
    #         _apply_recommended()
    #         st.rerun()
    #
    # with col2:
    #     if st.button("Clear all", key="checks-clear-all", use_container_width=True):
    #         _clear_all()
    #         st.rerun()

    for check_id in DEFAULT_CHECKS:
        label = FRIENDLY_CHECK_NAMES.get(check_id, check_id)
        description = check_hint(check_id)

        st.checkbox(
            label,
            key=f"check-picker-{check_id}",
            help=description,
        )

    selected = [
        check_id
        for check_id in DEFAULT_CHECKS
        if bool(st.session_state.get(f"check-picker-{check_id}", False))
    ]

    st.caption(f"Selected checks: {len(selected)} / {len(DEFAULT_CHECKS)}")

    st.session_state["selected_checks_override"] = selected
    return selected