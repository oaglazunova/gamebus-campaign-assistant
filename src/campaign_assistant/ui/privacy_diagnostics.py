from __future__ import annotations

import streamlit as st

from campaign_assistant.privacy import build_privacy_diagnostics_model


def _status_label(model: dict) -> str:
    if model["status"] == "warning":
        return "Warnings present"
    if model["status"] == "customized":
        return "Workspace override active"
    return "Baseline policy active"


def render_privacy_diagnostics_sidebar(privacy_report: dict | None) -> None:
    model = build_privacy_diagnostics_model(privacy_report)

    if not model["has_any_diagnostics"]:
        return

    title = "Privacy diagnostics"
    if model["override_warning_count"] > 0:
        title += f" ({model['override_warning_count']} warning{'s' if model['override_warning_count'] != 1 else ''})"

    with st.sidebar.expander(title, expanded=False):
        st.caption(f"Policy mode: `{model['policy_mode']}`")

        if model["status"] == "warning":
            st.warning("Workspace privacy overrides are active and some override requests were ignored or blocked.")
        elif model["status"] == "customized":
            st.info("Workspace privacy overrides are active.")
        else:
            st.info("Baseline privacy policy is active.")

        st.markdown(f"**Workspace overrides:** {'Yes' if model['has_workspace_overrides'] else 'No'}")

        if model["overridden_agents"]:
            st.markdown("**Overridden agents**")
            for agent_name in model["overridden_agents"]:
                source = model["policy_sources_by_agent"].get(agent_name, "unknown")
                st.write(f"- `{agent_name}` ({source})")

        if model["raw_workbook_allowed_agents"]:
            st.markdown("**Raw workbook access**")
            for agent_name in model["raw_workbook_allowed_agents"]:
                st.write(f"- `{agent_name}`")

        if model["sanitized_only_agents"]:
            st.markdown("**Sanitized-only agents**")
            for agent_name in model["sanitized_only_agents"]:
                st.write(f"- `{agent_name}`")

        if model["override_warnings"]:
            st.markdown("**Override warnings**")
            for item in model["override_warnings"]:
                message = str(item.get("message") or item.get("code") or "Unknown override warning")
                st.write(f"- {message}")


def render_privacy_diagnostics_panel(privacy_report: dict | None) -> None:
    """
    Main-panel version for Setup / Overview pages.
    """
    model = build_privacy_diagnostics_model(privacy_report)

    if not model["has_any_diagnostics"]:
        return

    st.markdown("### Privacy & governance")
    st.caption(f"Policy mode: `{model['policy_mode']}`")

    if model["status"] == "warning":
        st.warning("Workspace privacy overrides are active and some override requests were ignored or blocked.")
    elif model["status"] == "customized":
        st.info("Workspace privacy overrides are active.")
    else:
        st.info("Baseline privacy policy is active.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Status", _status_label(model))
    col2.metric("Overrides", "Yes" if model["has_workspace_overrides"] else "No")
    col3.metric("Warnings", model["override_warning_count"])

    if model["overridden_agents"]:
        st.markdown("**Overridden agents**")
        st.write(", ".join(f"`{name}`" for name in model["overridden_agents"]))

    if model["raw_workbook_allowed_agents"]:
        st.markdown("**Raw-workbook-capable agents**")
        st.write(", ".join(f"`{name}`" for name in model["raw_workbook_allowed_agents"]))

    if model["sanitized_only_agents"]:
        st.markdown("**Sanitized-only agents**")
        st.write(", ".join(f"`{name}`" for name in model["sanitized_only_agents"]))

    if model["override_warnings"]:
        with st.expander("Privacy override warnings", expanded=False):
            for item in model["override_warnings"]:
                st.write(f"- {str(item.get('message') or item.get('code') or 'Unknown override warning')}")