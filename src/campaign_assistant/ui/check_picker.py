from __future__ import annotations

from typing import Any

import streamlit as st

from campaign_assistant.checker import (
    CHECK_GROUP_CONFIG,
    CHECK_GROUP_UNIVERSAL,
    default_selected_check_ids,
    resolve_check_availability,
)


_GROUP_LABELS = {
    CHECK_GROUP_UNIVERSAL: "Always applicable",
    CHECK_GROUP_CONFIG: "Campaign-dependent",
}

_GROUP_DESCRIPTIONS = {
    CHECK_GROUP_UNIVERSAL: "These checks are useful for any campaign.",
    CHECK_GROUP_CONFIG: "These checks depend on campaign structure and workspace setup.",
}


def _capability_summary_from_result(result: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    assistant_meta = dict(result.get("assistant_meta", {}) or {})
    return dict(assistant_meta.get("capability_summary", {}) or {})


def _request_id_from_result(result: dict[str, Any] | None) -> str | None:
    if not isinstance(result, dict):
        return None
    assistant_meta = dict(result.get("assistant_meta", {}) or {})
    request_id = assistant_meta.get("request_id")
    return str(request_id) if request_id else None


def _initial_selected_ids(result: dict[str, Any] | None, capability_summary: dict[str, Any]) -> set[str]:
    session_selected = st.session_state.get("selected_checks_override")
    if isinstance(session_selected, list):
        return {str(x) for x in session_selected}

    if isinstance(result, dict):
        assistant_meta = dict(result.get("assistant_meta", {}) or {})
        previous_selected = assistant_meta.get("selected_checks")
        if isinstance(previous_selected, list):
            return {str(x) for x in previous_selected}

    return set(default_selected_check_ids(capability_summary))


def _toggle_hint(check_id: str) -> None:
    key = f"show-check-hint-{check_id}"
    st.session_state[key] = not bool(st.session_state.get(key, False))


def _hint_is_open(check_id: str) -> bool:
    return bool(st.session_state.get(f"show-check-hint-{check_id}", False))


def _focus_setup_action(action: dict[str, Any] | None, request_id: str | None) -> None:
    if not action or not request_id:
        return

    focus = str(action.get("focus") or "").strip()
    if not focus:
        return

    st.session_state[f"campaign-setup-focus-{request_id}"] = focus
    st.rerun()


def _status_badge(item) -> tuple[str, str]:
    if item.enabled:
        return "Enabled", "🟢"
    if item.action:
        return "Needs setup", "🟡"
    return "Unavailable", "⚪"


def _ensure_widget_defaults(items, selected_ids: set[str]) -> None:
    for item in items:
        key = f"check-picker-{item.check_id}"
        if key not in st.session_state:
            st.session_state[key] = item.check_id in selected_ids and item.enabled


def _apply_recommended(items) -> None:
    for item in items:
        st.session_state[f"check-picker-{item.check_id}"] = bool(item.enabled and item.selected_by_default)


def _clear_all(items) -> None:
    for item in items:
        st.session_state[f"check-picker-{item.check_id}"] = False


def _render_check_row(item, request_id: str | None) -> None:
    status_text, status_icon = _status_badge(item)

    col_check, col_status, col_info = st.columns([0.62, 0.20, 0.18])

    with col_check:
        st.checkbox(
            item.label,
            key=f"check-picker-{item.check_id}",
            disabled=not item.enabled,
            help=item.description,
        )
        st.caption(item.description)

    with col_status:
        st.caption(f"{status_icon} {status_text}")

    with col_info:
        if not item.enabled:
            if st.button("Why?", key=f"check-info-{item.check_id}", use_container_width=True):
                _toggle_hint(item.check_id)

    if not item.enabled and _hint_is_open(item.check_id):
        st.info(item.reason)
        if item.action and request_id:
            label = str(item.action.get("label") or "Open related setup")
            if st.button(label, key=f"check-action-{item.check_id}"):
                _focus_setup_action(item.action, request_id)


def _render_group(title: str, description: str, items, request_id: str | None) -> None:
    if not items:
        return

    st.markdown(f"**{title}**")
    st.caption(description)

    for item in items:
        _render_check_row(item, request_id)


def render_check_picker(result: dict[str, Any] | None) -> list[str]:
    capability_summary = _capability_summary_from_result(result)
    request_id = _request_id_from_result(result)

    items = [
        item
        for item in resolve_check_availability(capability_summary, enable_legacy=False)
        if item.visible
    ]

    selected_ids = _initial_selected_ids(result, capability_summary)
    _ensure_widget_defaults(items, selected_ids)

    enabled_items = [item for item in items if item.enabled]
    selected_checks = [
        item.check_id
        for item in items
        if item.enabled and bool(st.session_state.get(f"check-picker-{item.check_id}", False))
    ]

    top_a, top_b, top_c = st.columns([1, 1, 2])

    with top_a:
        if st.button("Use recommended", key="checks-use-recommended", use_container_width=True):
            _apply_recommended(items)
            st.rerun()

    with top_b:
        if st.button("Clear all", key="checks-clear-all", use_container_width=True):
            _clear_all(items)
            st.rerun()

    with top_c:
        st.caption(
            f"Selected: {len(selected_checks)} | Enabled: {len(enabled_items)} | Visible: {len(items)}"
        )

    grouped = {
        CHECK_GROUP_UNIVERSAL: [item for item in items if item.group == CHECK_GROUP_UNIVERSAL],
        CHECK_GROUP_CONFIG: [item for item in items if item.group == CHECK_GROUP_CONFIG],
    }

    _render_group(
        _GROUP_LABELS[CHECK_GROUP_UNIVERSAL],
        _GROUP_DESCRIPTIONS[CHECK_GROUP_UNIVERSAL],
        grouped[CHECK_GROUP_UNIVERSAL],
        request_id,
    )

    st.markdown("---")

    _render_group(
        _GROUP_LABELS[CHECK_GROUP_CONFIG],
        _GROUP_DESCRIPTIONS[CHECK_GROUP_CONFIG],
        grouped[CHECK_GROUP_CONFIG],
        request_id,
    )

    selected_checks = [
        item.check_id
        for item in items
        if item.enabled and bool(st.session_state.get(f"check-picker-{item.check_id}", False))
    ]

    st.session_state["selected_checks_override"] = selected_checks
    return selected_checks