from __future__ import annotations

import hashlib
import os

from typing import Any

import streamlit as st

from campaign_assistant.agents.context_builder import (
    build_llm_context,
    format_llm_context_markdown,
)
from campaign_assistant.llm import create_llm_client, llm_enabled
from campaign_assistant.agents.assistant_coordinator import (
    AssistantCoordinator,
    AssistantResponse,
)


_AGENT_PRESENTATION = {
    "campaign_support_agent": (
        "Campaign Support Agent",
        "🔧",
    ),
    "theory_support_agent": (
        "Theory Support Agent",
        "📚",
    ),
}


def _agent_presentation(
    agent_name: str | None,
) -> tuple[str, str]:
    return _AGENT_PRESENTATION.get(
        str(agent_name or ""),
        ("Assistant", "🤖"),
    )


def render_conversation_message(
    message: dict[str, Any],
) -> None:
    role = str(message.get("role") or "assistant")
    content = str(message.get("content") or "")

    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
        return

    label, avatar = _agent_presentation(
        message.get("agent_name")
    )

    caption = label

    if _show_response_source():
        source_label = _response_source_label(
            message.get("answer_source")
        )

        if source_label:
            caption += f" · {source_label}"

    with st.chat_message(
            "assistant",
            avatar=avatar,
    ):
        st.caption(caption)
        st.markdown(content)


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


def _show_response_source() -> bool:
    value = os.getenv(
        "CAMPAIGN_ASSISTANT_SHOW_RESPONSE_SOURCE",
        "false",
    ).strip().lower()

    return value in {"1", "true", "yes", "on"}


def _response_source_label(
    answer_source: str | None,
) -> str | None:
    source = str(answer_source or "").lower()

    if source == "llm":
        return "LLM-generated"

    if source == "guard_replacement":
        return "Deterministic guard response"

    if (
        "deterministic" in source
        or source in {
            "prepared_finding",
            "uncertainty",
            "no_analysis",
        }
    ):
        return "Deterministic"

    if source == "internal_error":
        return "System error"

    return None


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




def get_assistant_response(
    user_question: str,
    result: dict[str, Any],
    *,
    conversation_history: list[dict[str, str]] | None = None,
    quick_action: str | None = None,
    focused_finding: dict[str, Any] | None = None,
) -> AssistantResponse:
    if not result:
        return AssistantResponse(
            text=(
                "No campaign has been analyzed yet. Analyze a campaign "
                "first, then ask about the findings."
            ),
            agent_name="campaign_support_agent",
            intent="campaign_support",
            routing_reason="No campaign result is available.",
            answer_source="no_analysis",
        )

    normalized_question = user_question.strip().lower()

    if any(
        term in normalized_question
        for term in (
            "assistant context",
            "llm context",
            "agent context",
            "prompt context",
        )
    ):
        context = build_llm_context(result)

        return AssistantResponse(
            text=format_llm_context_markdown(context),
            agent_name="campaign_support_agent",
            intent="developer_context",
            routing_reason="Developer context requested explicitly.",
            answer_source="deterministic_context",
        )

    try:
        coordinator = AssistantCoordinator(
            llm_client=create_llm_client()
        )

        return coordinator.answer(
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
                else st.session_state.get(
                    "assistant_focused_finding"
                )
            ),
        )

    except Exception as exc:
        logger = st.session_state.get("logger")
        if logger is not None:
            logger.log_error(
                where="get_assistant_response",
                exc=exc,
            )

        return AssistantResponse(
            text=(
                "The Assistant could not process this question because "
                "an internal error occurred. Please try again."
            ),
            agent_name="campaign_support_agent",
            intent="internal_error",
            routing_reason="Assistant processing raised an exception.",
            answer_source="internal_error",
            guard_applied=False,
            guard_reason=None,
        )


def answer_question(
    user_question: str,
    result: dict[str, Any],
    *,
    conversation_history: list[dict[str, str]] | None = None,
    quick_action: str | None = None,
    focused_finding: dict[str, Any] | None = None,
) -> str:
    """Compatibility wrapper for callers that only need answer text."""
    return get_assistant_response(
        user_question,
        result,
        conversation_history=conversation_history,
        quick_action=quick_action,
        focused_finding=focused_finding,
    ).text


def _finding_dialog_key(
    result: dict[str, Any],
    finding: dict[str, Any],
) -> str:
    request_id = _assistant_meta(result).get("request_id") or "current-analysis"

    identity = "\x1f".join(
        str(value or "")
        for value in (
            request_id,
            finding.get("check"),
            finding.get("visualization_id"),
            finding.get("challenge_id"),
            finding.get("message"),
        )
    )

    return hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()[:16]


def _reset_finding_dialog_conversation() -> None:
    st.session_state["finding_assistant_messages"] = []


def _log_finding_dialog_message(
    role: str,
    content: str,
) -> None:
    logger = st.session_state.get("logger")

    if logger is None:
        return

    if role == "user":
        logger.log_chat_user(content)
    else:
        logger.log_chat_assistant(content)


@st.dialog("Assistant for this finding", width="large")
def render_finding_assistant_dialog(
    result: dict[str, Any],
    finding: dict[str, Any],
    heading: str,
) -> None:
    thread_key = _finding_dialog_key(result, finding)

    if st.session_state.get("finding_assistant_key") != thread_key:
        st.session_state["finding_assistant_key"] = thread_key
        st.session_state["finding_assistant_messages"] = []

    messages = st.session_state.setdefault(
        "finding_assistant_messages",
        [],
    )

    st.markdown(f"**{heading}**")

    location_parts: list[str] = []

    if finding.get("visualization"):
        location_parts.append(
            f"Visualization: {finding['visualization']}"
        )

    if finding.get("challenge"):
        location_parts.append(
            f"Challenge: {finding['challenge']}"
        )

    if location_parts:
        st.caption(" · ".join(location_parts))

    st.caption(
        "The Assistant already knows the finding's context. Ask for an explanation or a more specific next step."
    )

    history = st.container(height=240, border=True)
    empty_state = None

    with history:
        if not messages:
            empty_state = st.caption("Choose a question below or write your own.")

        for message in messages:
            render_conversation_message(message)

    quick_question = None

    quick_questions = (
        "What does this finding mean?",
        "What should I inspect first?",
        "Could this finding be intentional?",
    )

    columns = st.columns(len(quick_questions))

    for index, question in enumerate(quick_questions):
        with columns[index]:
            if st.button(
                question,
                key=f"finding-assistant-quick-{thread_key}-{index}",
                use_container_width=True,
            ):
                quick_question = question

    user_question = st.chat_input(
        "Ask a follow-up question...",
        key=f"finding-assistant-input-{thread_key}",
    )

    question = quick_question or user_question

    st.button(
        "Clear conversation",
        key=f"finding-assistant-clear-{thread_key}",
        on_click=_reset_finding_dialog_conversation,
    )

    if not question:
        return

    conversation_history = list(messages)

    user_message = {
        "role": "user",
        "content": question,
    }

    messages.append(user_message)
    _log_finding_dialog_message("user", question)

    if empty_state is not None:
        empty_state.empty()

    with st.spinner("Preparing an answer..."):
        response = get_assistant_response(
            question,
            result,
            conversation_history=conversation_history,
            focused_finding=finding,
        )

    assistant_message = {
        "role": "assistant",
        "content": response.text,
        "agent_name": response.agent_name,
        "answer_source": response.answer_source,
    }

    messages.append(assistant_message)

    logger = st.session_state.get("logger")
    if logger is not None:
        logger.log_chat_assistant(
            response.text,
            agent_name=response.agent_name,
            intent=response.intent,
            answer_source=response.answer_source,
            guard_applied=response.guard_applied,
            guard_reason=response.guard_reason,
        )

    with history:
        render_conversation_message(user_message)
        render_conversation_message(assistant_message)
