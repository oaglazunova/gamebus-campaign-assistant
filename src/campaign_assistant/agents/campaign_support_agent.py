from __future__ import annotations

import re

from typing import Any

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.agents.context_builder import format_llm_context_markdown
from campaign_assistant.llm.base import LLMClient
from campaign_assistant.agents.gamebus_studio_knowledge import (
    gamebus_studio_field_facts_markdown_for_question,
)


CAMPAIGN_SUPPORT_SYSTEM_PROMPT = """
You are the Campaign Support Agent for the GameBus Campaign Assistant.

Your role:
- Explain deterministic checker findings.
- Explain what an error or warning means for campaign organizers.
- Suggest what the user should inspect next.
- Suggest possible human-reviewed repair steps.
- Help prioritize findings.

Strict boundaries:
- Do not invent new formal validation errors.
- Do not claim that a campaign has an issue unless it is present in the checker context.
- Do not claim that the campaign is fixed.
- Do not modify or generate campaign files.
- Do not present behavior-change theory feedback as formal validation.
- If the user asks about behavior-change theory, say that theory-oriented support belongs to the Theory Support Agent.
- Checker facts are authoritative. Do not contradict total_issues, failed_checks, or known findings.
- Deterministic GameBus Studio fix guidance is authoritative for where to inspect and how to fix deterministic checker findings.
- If deterministic GameBus Studio fix guidance is available, use it as the basis for repair advice.
- You may rephrase deterministic guidance in clearer language, but do not add unsupported GameBus Studio fields, tabs, or repair steps.
- GameBus Studio source facts are derived from inspected GameBus code and may be used to explain field meanings, editor locations, and export mappings.
- Do not claim that a GameBus Studio field, tab, route, or save behavior exists unless it is present in deterministic guidance, GameBus Studio source facts, or the checker context.
- If the user asks for a GameBus behavior that is not covered by the source facts, say that the current local source facts do not establish it.
- Export structure counts are descriptive facts, not errors by themselves.
- If total_issues is 0, do not say that the checker found issues, inconsistencies, warnings, or errors.
- For broad questions such as "is this a good campaign?", distinguish structural checker results from content quality, theory alignment, and outcome effectiveness.

Response style:
- Do not merely repeat the deterministic guidance verbatim.
- Do not answer with only "Okay", "Sure", or another acknowledgement.
- For finding explanations, use this structure:
  1. What the checker found.
  2. Why it matters.
  3. What to inspect in GameBus Studio.
  4. What to change, if the finding is valid.
- Keep answers practical and concise.
- Prefer concrete field names from deterministic guidance or GameBus Studio source facts.

Use cautious wording:
- "The checker found..."
- "You should inspect..."
- "A likely next step is..."
- "This may indicate..."
"""


_DETERMINISTIC_GUIDANCE_QUESTION_PATTERNS = [
    r"\bhow\b.*\b(fix|repair|correct|solve|resolve|change)\b",
    r"\bwhat\b.*\b(fix|repair|correct|change|inspect|check)\b",
    r"\bwhere\b.*\b(fix|repair|change|inspect|check|click)\b",
    r"\bmake\b.*\breachable\b",
    r"\bhow\b.*\breachable\b",
    r"\bwhat should i inspect\b",
    r"\bwhat should i check\b",
    r"\bexplain this campaign finding\b",
    r"\bexplain (this|the) finding\b",
]


def _normalized(text: Any) -> str:
    return " ".join(str(text or "").lower().split())


def _is_deterministic_guidance_question(question: str) -> bool:
    normalized = _normalized(question)
    return any(
        re.search(pattern, normalized)
        for pattern in _DETERMINISTIC_GUIDANCE_QUESTION_PATTERNS
    )


def _question_mentions_finding(question: str, finding: dict[str, Any]) -> bool:
    """Return whether the question appears to refer to a specific finding.

    This supports prepared questions from the Findings page, where the question
    often contains challenge id, challenge name, visualization name, or check.
    """
    normalized_question = _normalized(question)

    candidate_fields = [
        "challenge_id",
        "visualization_id",
        "wave_id",
        "challenge",
        "visualization",
        "title",
        "message",
        "check",
    ]

    for field in candidate_fields:
        value = finding.get(field)
        if value in (None, ""):
            continue

        normalized_value = _normalized(value)
        if normalized_value and normalized_value in normalized_question:
            return True

    return False


def _select_guided_finding(
    question: str,
    context: dict[str, Any],
) -> dict[str, Any] | None:
    findings = [
        finding
        for finding in (context.get("top_findings", []) or [])
        if isinstance(finding, dict)
        and finding.get("deterministic_gamebus_fix_guidance")
    ]

    if not findings:
        return None

    for finding in findings:
        if _question_mentions_finding(question, finding):
            return finding

    # For short follow-ups such as "how can I make it reachable?", the user is
    # usually referring to the highest-priority finding currently in context.
    return findings[0]


def _deterministic_guidance_answer(
    question: str,
    context: dict[str, Any],
) -> str | None:
    """Answer repair/inspection questions directly from deterministic guidance.

    This intentionally bypasses the LLM for fix instructions. It avoids failure
    modes such as "Okay" and prevents the model from inventing GameBus fields.
    """
    if not _is_deterministic_guidance_question(question):
        return None

    finding = _select_guided_finding(question, context)
    if finding is None:
        return None

    title = finding.get("title") or "Finding"
    check = finding.get("check") or "unknown"
    severity = finding.get("severity") or "unknown"
    guidance = finding.get("deterministic_gamebus_fix_guidance")
    source_facts = finding.get("gamebus_studio_source_facts")

    lines = [
        "Use the deterministic GameBus Studio guidance for this finding.",
        "",
        f"**Finding:** {title}",
        f"**Check:** `{check}`",
        f"**Severity:** `{severity}`",
    ]

    visualization = finding.get("visualization")
    if visualization:
        lines.append(f"**Visualization:** {visualization}")

    challenge = finding.get("challenge")
    if challenge:
        lines.append(f"**Challenge:** {challenge}")

    challenge_id = finding.get("challenge_id")
    if challenge_id not in (None, ""):
        lines.append(f"**Challenge ID:** {challenge_id}")

    url = finding.get("url")
    if url:
        lines.append(f"**GameBus Studio URL:** {url}")

    lines.append("")
    lines.append(str(guidance))

    if source_facts:
        lines.append("")
        lines.append("**Relevant GameBus Studio source facts**")
        lines.append(str(source_facts))

    return "\n".join(lines)


def _fallback_without_llm(question: str, context: dict[str, Any]) -> str:
    """Return a useful deterministic answer when LLM support is unavailable.

    This fallback must not invent explanations. It can only summarize checker
    facts and reuse deterministic GameBus Studio guidance already stored in the
    context by context_builder.
    """
    analysis = context.get("analysis", {}) or {}
    top_findings = context.get("top_findings", []) or []
    structure = context.get("campaign_structure", {}) or {}
    counts = structure.get("counts", {}) or {}

    total = analysis.get("total_issues", 0)
    failed_checks = analysis.get("failed_checks", []) or []
    severity_counts = analysis.get("severity_counts", {}) or {}
    issue_count_by_check = analysis.get("issue_count_by_check", {}) or {}

    lines = [
        "LLM support is not available, so I can only provide deterministic checker-based guidance.",
        "",
        f"The selected checks found **{total}** issue(s).",
    ]

    if severity_counts:
        severity_parts = [
            f"{severity}: {count}"
            for severity, count in severity_counts.items()
            if count
        ]
        if severity_parts:
            lines.append("Severity counts: " + ", ".join(severity_parts) + ".")

    if failed_checks:
        lines.append(
            "Checks with findings: "
            + ", ".join(f"`{check}`" for check in failed_checks)
            + "."
        )
    else:
        lines.append("No failed checks were reported.")

    if issue_count_by_check:
        lines.append("")
        lines.append("Issue counts by check:")
        for check, count in issue_count_by_check.items():
            lines.append(f"- `{check}`: {count}")

    if counts:
        lines.append("")
        lines.append("Campaign structure:")
        lines.append(f"- Waves: {counts.get('waves', 0)}")
        lines.append(f"- Visualizations: {counts.get('visualizations', 0)}")
        lines.append(f"- Challenges/levels: {counts.get('challenges', 0)}")
        lines.append(f"- Tasks: {counts.get('tasks', 0)}")
        lines.append(f"- Transitions: {counts.get('transitions', 0)}")

    if not top_findings:
        lines.append("")
        lines.append("No prioritized findings are available in the current context.")
        return "\n".join(lines)

    lines.append("")
    lines.append("Top findings to inspect:")
    for idx, finding in enumerate(top_findings[:5], start=1):
        title = finding.get("title") or "Finding"
        check = finding.get("check") or "unknown"
        severity = finding.get("severity") or "unknown"
        lines.append(f"{idx}. [{severity}] {title} (check: `{check}`)")

        visualization = finding.get("visualization")
        if visualization:
            lines.append(f"   - Visualization: {visualization}")

        challenge = finding.get("challenge")
        if challenge:
            lines.append(f"   - Challenge: {challenge}")

        url = finding.get("url")
        if url:
            lines.append(f"   - GameBus Studio URL: {url}")

    highest = top_findings[0]
    guidance = highest.get("deterministic_gamebus_fix_guidance")

    if guidance:
        lines.append("")
        lines.append("Deterministic guidance for the highest-priority finding:")
        lines.append(str(guidance))
    else:
        lines.append("")
        lines.append(
            "No deterministic GameBus Studio fix guidance is available for the highest-priority finding."
        )

    source_facts = highest.get("gamebus_studio_source_facts")
    if source_facts:
        lines.append("")
        lines.append("Relevant GameBus Studio source facts:")
        lines.append(str(source_facts))

    return "\n".join(lines)


class CampaignSupportAgent(BaseAgent):
    name = "campaign_support_agent"

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client

    def run(self, *, question: str, context: dict[str, Any]) -> str:
        deterministic_answer = _deterministic_guidance_answer(question, context)
        if deterministic_answer:
            return deterministic_answer

        if self.llm_client is None:
            return _fallback_without_llm(question, context)

        context_markdown = format_llm_context_markdown(context)

        field_facts = gamebus_studio_field_facts_markdown_for_question(question)
        if field_facts:
            context_markdown = "\n\n".join(
                [
                    context_markdown,
                    "# Relevant GameBus Studio field facts for this question",
                    field_facts,
                ]
            )

        user_prompt = f"""
User question:
{question}

Available checker/campaign context:
{context_markdown}

Answer the user using only the available context. If the context is insufficient,
say what is missing and what the organizer should inspect manually.
"""

        response = self.llm_client.generate(
            system_prompt=CAMPAIGN_SUPPORT_SYSTEM_PROMPT.strip(),
            user_prompt=user_prompt.strip(),
            temperature=0.2,
        )

        if not response.available:
            return (
                "LLM support is currently unavailable.\n\n"
                f"Provider: `{response.provider}`\n"
                f"Model: `{response.model}`\n"
                f"Error: {response.error}\n\n"
                + _fallback_without_llm(question, context)
            )

        if not response.text.strip():
            return (
                "The LLM returned an empty response. "
                "Try rephrasing the question or check the configured Ollama model."
            )

        return response.text.strip()
