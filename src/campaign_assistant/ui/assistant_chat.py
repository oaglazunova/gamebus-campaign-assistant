from __future__ import annotations
from typing import Any

import streamlit as st

from campaign_assistant.agents.context_builder import (
    build_llm_context,
    format_llm_context_markdown,
)


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
            lines.append(f"{idx}. **{label}** — {location}")
        else:
            lines.append(f"{idx}. **{label}**")

    return "\n".join(lines)


def render_assistant_page_status(result: dict[str, Any], message_count: int) -> None:
    total = _total_issues(result)
    checks_run = result.get("checks_run", []) or []

    st.subheader("Assistant")

    if total > 0:
        st.info(
            "Ask about the current campaign analysis, detected findings, "
            "or what to inspect next."
        )
    else:
        st.success(
            "No issues were found by the selected checks. You can still ask "
            "about the analysis result."
        )

    c1, c2, c3 = st.columns(3)
    c1.metric("Conversation messages", message_count)
    c2.metric("Issues", total)
    c3.metric("Checks run", len(checks_run))


def render_assistant_guide_panel(result: dict[str, Any]) -> None:
    if not result:
        return

    suggestions = [
        "Summarize the issues",
        "What is the campaign structure?",
        "What should I inspect first?",
        "Explain the highest-priority finding",
    ]

    if _total_issues(result) == 0:
        suggestions = [
            "Summarize the analysis",
            "What is the campaign structure?",
            "Which checks were run?",
            "What does a clean result mean?",
        ]

    st.caption("Suggested questions")

    cols = st.columns(min(len(suggestions), 4))
    for idx, suggestion in enumerate(suggestions):
        with cols[idx % len(cols)]:
            if st.button(suggestion, key=f"assistant-suggestion-{idx}", use_container_width=True):
                st.session_state["assistant_prefill_prompt"] = suggestion


def answer_question(user_question: str, result: dict[str, Any]) -> str:
    if not result:
        return "No campaign has been analyzed yet. Analyze a campaign first, then ask about the findings."

    q = user_question.strip().lower()
    total = _total_issues(result)
    failed_checks = _failed_checks(result)
    issue_count_by_check = _issue_count_by_check(result)
    selected_checks = _assistant_meta(result).get("selected_checks", result.get("checks_run", []))

    if any(term in q for term in ["theory", "ttm", "com-b", "comb", "bct", "behaviour", "behavior"]):
        return (
            "Theory-support chat is not enabled yet in this cleanup phase. "
            "In the paper-release architecture, this will be handled by the "
            "**TheorySupportAgent** using Ollama. For now, the available assistant "
            "support is limited to deterministic checker findings."
        )

    if any(term in q for term in ["assistant context", "llm context", "agent context", "prompt context"]):
        context = build_llm_context(result)
        return format_llm_context_markdown(context)

    if any(
        term in q
        for term in [
            "campaign structure",
            "structure",
            "how many levels",
            "how many challenges",
            "how many tasks",
            "how many waves",
            "how many transitions",
            "levels",
            "tasks",
            "waves",
            "visualizations",
            "transitions",
        ]
    ):
        return _format_campaign_structure(result)

    if any(term in q for term in ["summary", "summarize", "overview", "what is wrong", "what's wrong"]):
        lines = [f"The selected checks found **{total}** issue(s)."]

        if selected_checks:
            lines.append("Checks run: " + ", ".join(f"`{check}`" for check in selected_checks) + ".")

        if failed_checks:
            lines.append("Checks with findings: " + ", ".join(f"`{check}`" for check in failed_checks) + ".")
        else:
            lines.append("No failed checks were reported by the selected validators.")

        if issue_count_by_check:
            lines.append("\nIssue counts by check:")
            for check, count in sorted(issue_count_by_check.items(), key=lambda item: item[0]):
                lines.append(f"- `{check}`: {count}")

        top = _format_top_issues(result)
        if top:
            lines.append("\nTop priorities:")
            lines.append(top)

        return "\n".join(lines)

    if any(term in q for term in ["first", "prioritize", "priority", "fix first", "inspect first", "where start"]):
        if total == 0:
            return (
                "No issues were found by the selected checks. This does not prove the campaign is optimal; "
                "it only means the selected export-level checks did not detect problems."
            )

        return (
            "Start with the highest-priority findings, because they are most likely to affect deployment "
            "or participant progression.\n\n"
            + _format_top_issues(result)
            + "\n\nUse the Findings page to inspect the corresponding check, row/context, and message."
        )

    if any(term in q for term in ["explain", "meaning", "why", "what does", "important"]):
        top = _top_issues(result, limit=1)
        if not top:
            return (
                "There is no prioritized finding to explain. If the selected checks found no issues, "
                "the result should be interpreted only as a clean export-level check, not as full campaign validation."
            )

        issue = top[0]
        label = _issue_label(issue)
        location = _issue_location(issue)
        message = issue.get("message") or issue.get("description") or ""

        lines = [
            f"The highest-priority finding is: **{label}**.",
        ]

        if location:
            lines.append(f"It is located in {location}.")

        if message and str(message) != label:
            lines.append(f"Checker message: {message}")

        lines.append(
            "This means you should inspect the relevant campaign configuration in GameBus or in the export. "
            "The assistant is not modifying the campaign; it is only pointing you to what should be reviewed."
        )

        return "\n\n".join(lines)

    if any(term in q for term in ["failed", "which checks", "checks failed", "validators"]):
        if failed_checks:
            return "Checks with findings: " + ", ".join(f"`{check}`" for check in failed_checks) + "."
        return "No failed checks were reported by the selected validators."

    return (
        "I can currently help with deterministic checker results. Try asking:\n\n"
        "- `Summarize the issues`\n"
        "- `What should I inspect first?`\n"
        "- `Explain the highest-priority finding`\n"
        "- `Which checks failed?`\n\n"
        "Theory-oriented support will be added later through the Ollama-backed TheorySupportAgent."
    )


def render_agent_trace_panel(result: dict[str, Any], show_trace: bool) -> None:
    if not show_trace:
        return

    trace = _assistant_meta(result).get("agent_trace", []) or []
    if not trace:
        return

    with st.expander("Analysis trace", expanded=False):
        for item in trace:
            agent_name = item.get("agent_name", "agent")
            status = item.get("status", "unknown")
            summary = item.get("summary", "")
            st.markdown(f"- **{agent_name}** — `{status}`: {summary}")
