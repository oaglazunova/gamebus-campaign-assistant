from __future__ import annotations

import os
from typing import Any

import streamlit as st

from campaign_assistant.agents.context_builder import (
    build_llm_context,
    format_llm_context_markdown,
)
from campaign_assistant.agents.assistant_coordinator import AssistantCoordinator
from campaign_assistant.llm import create_llm_client, llm_enabled



def _friendly_agent_name(agent_name: str) -> str:
    labels = {
        "campaign_support_agent": "Campaign Support Agent",
        "theory_support_agent": "Theory Support Agent",
    }
    return labels.get(agent_name, agent_name)


def _show_routing_footer() -> bool:
    value = os.getenv("CAMPAIGN_ASSISTANT_SHOW_ROUTING", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def quick_action_focuses_top_finding(action: str | None) -> bool:
    return action in {
        "inspect_first",
        "explain_top_finding",
        "explain_top_findings",
    }


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    return dict(result.get("summary", {}) or {})


def _assistant_meta(result: dict[str, Any]) -> dict[str, Any]:
    return dict(result.get("assistant_meta", {}) or {})


def _campaign_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    snapshot = result.get("campaign_snapshot", {}) or {}
    return dict(snapshot) if isinstance(snapshot, dict) else {}


def _campaign_counts(result: dict[str, Any]) -> dict[str, Any]:
    snapshot = _campaign_snapshot(result)
    counts = snapshot.get("counts", {}) or {}
    return dict(counts) if isinstance(counts, dict) else {}


def _format_campaign_structure(result: dict[str, Any]) -> str:
    snapshot = _campaign_snapshot(result)
    counts = _campaign_counts(result)

    if not snapshot:
        return "No campaign structure snapshot is available."

    lines = [
        "Campaign structure snapshot:",
        f"- Waves: {counts.get('waves', 0)}",
        f"- Visualizations: {counts.get('visualizations', 0)}",
        f"- Challenges/levels: {counts.get('challenges', 0)}",
        f"- Tasks: {counts.get('tasks', 0)}",
        f"- Transitions: {counts.get('transitions', 0)}",
    ]

    warnings = snapshot.get("extraction_warnings", []) or []
    if warnings:
        lines.append("")
        lines.append("Snapshot extraction warnings:")
        for warning in warnings:
            lines.append(f"- {warning}")

    return "\n".join(lines)



def _total_issues(result: dict[str, Any]) -> int:
    return int(_summary(result).get("total_issues", 0) or 0)


def _failed_checks(result: dict[str, Any]) -> list[str]:
    failed = _summary(result).get("failed_checks", [])
    if isinstance(failed, list):
        return [str(item) for item in failed]
    return []


def _issue_count_by_check(result: dict[str, Any]) -> dict[str, int]:
    raw = _summary(result).get("issue_count_by_check", {}) or {}
    return {str(key): int(value or 0) for key, value in dict(raw).items()}


def _top_issues(result: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    issues = result.get("prioritized_issues", []) or []
    return [item for item in issues if isinstance(item, dict)][:limit]


def _issue_label(issue: dict[str, Any]) -> str:
    return str(
        issue.get("title")
        or issue.get("message")
        or issue.get("description")
        or issue.get("issue")
        or "Finding"
    )


def _issue_location(issue: dict[str, Any]) -> str:
    parts: list[str] = []

    check = issue.get("check")
    if check:
        parts.append(f"check `{check}`")

    visualization = issue.get("visualization")
    if visualization:
        parts.append(f"visualization `{visualization}`")

    challenge = issue.get("challenge")
    if challenge:
        parts.append(f"challenge `{challenge}`")

    return ", ".join(parts)


def _format_top_issues(result: dict[str, Any], limit: int = 5) -> str:
    top = _top_issues(result, limit=limit)
    if not top:
        return "No prioritized findings are available."

    lines: list[str] = []
    for idx, issue in enumerate(top, start=1):
        label = _issue_label(issue)
        location = _issue_location(issue)
        if location:
            lines.append(f"{idx}. **{label}** - {location}")
        else:
            lines.append(f"{idx}. **{label}**")

    return "\n".join(lines)


def focused_finding_for_quick_action(
    result: dict[str, Any],
    quick_action: str | None,
) -> dict[str, Any] | None:
    if not quick_action_focuses_top_finding(quick_action):
        return None

    context = build_llm_context(result)
    top_findings = context.get("top_findings", []) or []

    if not top_findings:
        return None

    first = top_findings[0]
    if not isinstance(first, dict):
        return None

    return dict(first)



def render_assistant_page_status(result: dict[str, Any], message_count: int) -> None:
    total = _total_issues(result)
    checks_run = result.get("checks_run", []) or []

    if total > 0:
        st.info(
            "Ask about the current campaign analysis, detected findings, "
            "or what to inspect next."
        )
    else:
        st.success(
            "No findings were detected by the selected checks. You can still ask "
            "about the analysis result."
        )

    c1, c2, c3 = st.columns(3)
    c1.metric("Conversation messages", message_count)
    c2.metric("Findings", total)
    c3.metric("Checks run", len(checks_run))


def render_llm_status_panel() -> None:
    with st.expander("LLM configuration", expanded=False):
        if not llm_enabled():
            st.info(
                "LLM support is disabled. The assistant will use deterministic fallback responses."
            )
            st.code("CAMPAIGN_ASSISTANT_LLM_ENABLED=false")
            return

        client = create_llm_client()

        if client is None:
            st.warning(
                "LLM support is enabled, but no supported provider is configured."
            )
            st.caption(
                "Supported providers in this release: `ollama`, `mock`."
            )
            return

        st.write(f"**Provider:** `{client.provider}`")
        st.write(f"**Model:** `{client.model}`")

        st.caption(f"Env model value: `{os.getenv('CAMPAIGN_ASSISTANT_LLM_MODEL', '<not set>')}`")


        if client.provider == "ollama":
            st.caption(
                "If responses say Ollama is unavailable, make sure Ollama is running "
                "and that the configured model has been pulled."
            )

            st.code(
                f"ollama serve\n"
                f"ollama pull {client.model}",
                language="powershell",
            )

        if client.provider == "mock":
            st.caption(
                "Mock mode is useful for tests. It does not produce real LLM answers."
            )


def render_assistant_guide_panel(result: dict[str, Any]) -> None:
    if not result:
        return

    suggestions = [
        ("Summarize the findings", "summarize_issues"),
        ("What is the campaign structure?", "campaign_structure"),
        ("What should I inspect first?", "inspect_first"),
        ("Explain the highest-priority findings", "explain_top_findings"),
        ("How is prioritization calculated?", "prioritization"),
        ("How theory-grounded is this campaign?", "theory_grounding"),
    ]

    if _total_issues(result) == 0:
        suggestions = [
            ("Summarize the analysis", "summarize_issues"),
            ("What is the campaign structure?", "campaign_structure"),
            ("Which checks were run?", "all_checks"),
            ("What does a clean result mean?", "clean_result"),
            ("How is prioritization calculated?", "prioritization"),
            ("How theory-grounded is this campaign?", "theory_grounding"),
        ]

    st.caption("Quick questions")

    cols = st.columns(min(len(suggestions), 4))
    for idx, (label, action) in enumerate(suggestions):
        with cols[idx % len(cols)]:
            if st.button(label, key=f"assistant-suggestion-{idx}", use_container_width=True):
                st.session_state["assistant_pending_question"] = label
                st.session_state["assistant_pending_quick_action"] = action
                st.rerun()


def render_prepared_question_panel() -> None:
    prepared_prompt = st.session_state.get("assistant_prefill_prompt")

    if not prepared_prompt:
        return

    st.markdown("### Ask about the selected finding")

    edited_prompt = st.text_area(
        "Question prepared from Findings",
        value=str(prepared_prompt),
        height=180,
        key="assistant-prepared-question-editor",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Use this question",
            key="assistant-use-prepared-question",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["assistant_pending_question"] = edited_prompt
            st.session_state.pop("assistant_prefill_prompt", None)
            st.rerun()

    with col2:
        if st.button(
            "Clear prepared question",
            key="assistant-clear-prepared-question",
            use_container_width=True,
        ):
            st.session_state.pop("assistant_prefill_prompt", None)
            st.session_state.pop("assistant_pending_question", None)
            st.rerun()



def answer_question(
    user_question: str,
    result: dict[str, Any],
    *,
    conversation_history: list[dict[str, str]] | None = None,
    quick_action: str | None = None,
    focused_finding: dict[str, Any] | None = None,
) -> str:
    if not result:
        return (
            "No campaign has been analyzed yet. Analyze a campaign first, "
            "then ask about the findings."
        )

    q = user_question.strip().lower()

    # Developer/debug hook. Keep this typed-only; do not add a visible button.
    if any(term in q for term in ["assistant context", "llm context", "agent context", "prompt context"]):
        context = build_llm_context(result)
        return format_llm_context_markdown(context)

    try:
        coordinator = AssistantCoordinator(llm_client=create_llm_client())
        response = coordinator.answer(
            question=user_question,
            result=result,
            conversation_history=(
                conversation_history
                if conversation_history is not None
                else list(st.session_state.get("messages", []))
            ),
            quick_action=quick_action,
            focused_finding=(
                focused_finding
                if focused_finding is not None
                else st.session_state.get("assistant_focused_finding")
            ),
        )

        if not _show_routing_footer():
            return response.text

        friendly_agent = _friendly_agent_name(response.agent_name)
        guard_note = ""
        if getattr(response, "guard_applied", False):
            guard_note = f" Response guard applied: `{response.guard_reason}`."

        return (
            response.text
            + "\n\n---\n"
            + f"_Assistant route: `{response.intent}` via **{friendly_agent}**. "
            + f"Source: `{response.answer_source}`.{guard_note}_"
        )

    except Exception as exc:
        return (
            "The assistant could not process this question because an internal error occurred.\n\n"
            f"Error: `{exc}`"
        )
