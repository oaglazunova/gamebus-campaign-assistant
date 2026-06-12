from __future__ import annotations

import re

from typing import Any

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.agents.context_builder import format_llm_context_markdown
from campaign_assistant.llm.base import LLMClient
from campaign_assistant.agents.gamebus_studio_knowledge import (
    gamebus_studio_field_facts_markdown_for_question,
)
from campaign_assistant.checker.check_metadata import PRIORITY_HINT, check_explanation
from campaign_assistant.checker.schema import FRIENDLY_CHECK_NAMES


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
- GameBus Studio facts may be used to explain field meanings, editor locations, and export mappings.
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
    r"\bhow\b.*\b(fix|repair|correct|solve|resolve|change|edit)\b",
    r"\bwhat\b.*\b(fix|repair|correct|change|edit)\b",
    r"\bwhere\b.*\b(fix|repair|change|edit|click)\b",
    r"\bwhich\b.*\b(field|fields)\b.*\b(change|edit|set|fill)\b",
    r"\bwhat\b.*\b(field|fields)\b.*\b(change|edit|set|fill)\b",
    r"\bmake\b.*\breachable\b",
    r"\bhow\b.*\breachable\b",
]


def _normalized(text: Any) -> str:
    return " ".join(str(text or "").lower().split())


def _is_weak_llm_answer(text: str) -> bool:
    normalized = " ".join(str(text or "").strip().lower().split())
    normalized = normalized.strip(" .!?,;:")

    if not normalized:
        return True

    weak_exact = {
        "ok",
        "okay",
        "sure",
        "yes",
        "no",
        "i see",
        "understood",
        "got it",
        "noted",
    }

    if normalized in weak_exact:
        return True

    weak_prefixes = [
        "okay",
        "sure",
        "yes",
        "i can help",
        "i can help with that",
    ]

    # Catches "Okay, ..." only if there is no substantive continuation.
    if normalized in weak_prefixes:
        return True

    # Catches short non-answers such as "Okay, understood" but not "Mock answer".
    tokens = normalized.split()
    if len(tokens) <= 3 and all(token in weak_exact for token in tokens):
        return True

    return False


def _is_deterministic_guidance_question(question: str) -> bool:
    normalized = _normalized(question)
    return any(
        re.search(pattern, normalized)
        for pattern in _DETERMINISTIC_GUIDANCE_QUESTION_PATTERNS
    )


def _check_explanation_answer(question: str) -> str | None:
    normalized = _normalized(question)

    explanation_intent = any(
        phrase in normalized
        for phrase in [
            "what does",
            "what is",
            "explain",
            "how is",
            "how does",
            "how calculated",
            "how is calculated",
        ]
    )

    manual_aliases = {
        "spellchecker": ["spellcheck", "spelling", "spell checker"],
        "visualizationintern": [
            "visualization intern",
            "visualization internal",
            "visualization internals",
            "visualisation intern",
            "visualisation internal",
            "visualisation internals",
        ],
        "targetpointsreachable": [
            "target points",
            "target point",
            "points reachable",
            "target reachable",
        ],
        "ttm": [
            "ttm",
            "ttm structure",
            "transtheoretical model",
        ],
    }

    for check_id, friendly_name in FRIENDLY_CHECK_NAMES.items():
        aliases = {
            check_id.lower(),
            friendly_name.lower(),
            friendly_name.lower().replace(" ", ""),
            friendly_name.lower().replace(" ", "_"),
        }
        aliases.update(manual_aliases.get(check_id, []))

        mentions_check = any(alias in normalized for alias in aliases)

        # Handles normal questions:
        # "What does consistency do?"
        # "Explain spellchecker"
        #
        # Also handles short follow-ups:
        # "and consistency?"
        # "consistency?"
        # "target points?"
        short_follow_up = (
            len(normalized.split()) <= 4
            and (
                normalized.startswith("and ")
                or normalized.endswith("?")
                or normalized in aliases
            )
        )

        if mentions_check and (explanation_intent or short_follow_up):
            explanation = check_explanation(check_id)
            if explanation:
                return explanation

    return None


def _all_checks_explanation_answer(question: str) -> str | None:
    normalized = _normalized(question)

    patterns = [
        r"\bwhat\b.*\bchecks\b.*\bcheck\b",
        r"\bwhat\b.*\bcheckers\b.*\bcheck\b",
        r"\bwhat\b.*\bchecks\b.*\bdo\b",
        r"\bexplain\b.*\bchecks\b",
        r"\bwhich checks\b",
    ]

    if not any(re.search(pattern, normalized) for pattern in patterns):
        return None

    lines = [
        "The selected deterministic checks inspect different parts of the campaign export:",
        "",
    ]

    for check_id, friendly_name in FRIENDLY_CHECK_NAMES.items():
        explanation = check_explanation(check_id)
        if not explanation:
            continue

        first_sentence = explanation.split(". ")[0].strip()
        lines.append(f"- **{friendly_name}**: {first_sentence}.")

    lines.append("")
    lines.append(
        "Ask about a specific check, for example `What does spellchecker do?`, "
        "to see the full detailed explanation."
    )

    return "\n".join(lines)


def _is_prioritization_question(question: str) -> bool:
    normalized = _normalized(question)

    patterns = [
        r"\bhow\b.*\bprioriti[sz]ation\b.*\bcalculat",
        r"\bhow\b.*\bprioriti[sz]ed\b",
        r"\bhow\b.*\bpriority\b.*\bcalculat",
        r"\bpriority score\b",
        r"\bprioriti[sz]ation\b",
    ]

    return any(re.search(pattern, normalized) for pattern in patterns)


def _prioritization_answer() -> str:
    return (
        f"{PRIORITY_HINT}\n\n"
        "In practice, this means:\n"
        "- High-severity findings are shown before medium- and low-severity findings.\n"
        "- Findings in an active wave receive a small boost.\n"
        "- The active-wave boost does not normally make a medium finding outrank a high finding.\n"
        "- If a finding ever has missing/unknown severity, it receives severity score 0 and should be treated as incomplete metadata."
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
        lines.append("**Relevant GameBus Studio facts**")
        lines.append(str(source_facts))

    return "\n".join(lines)


def _issue_summary_answer(question: str, context: dict[str, Any]) -> str | None:
    normalized = _normalized(question)

    if _is_deterministic_guidance_question(question):
        return None

    overview_patterns = [
        r"\bsummarize\b.*\b(issue|issues|finding|findings)\b",
        r"\bsummarise\b.*\b(issue|issues|finding|findings)\b",
        r"\bsummary\b.*\b(issue|issues|finding|findings)\b",
        r"\bexplain\b.*\b(issue|issues|finding|findings)\b",
        r"\bimportant\b.*\b(issue|issues|finding|findings)\b",
        r"\bmost important\b",
        r"\bmain\b.*\b(issue|issues|finding|findings)\b",
        r"\btop\b.*\b(issue|issues|finding|findings)\b",
    ]

    if not any(re.search(pattern, normalized) for pattern in overview_patterns):
        return None

    analysis = context.get("analysis", {}) or {}
    top_findings = context.get("top_findings", []) or []

    total = analysis.get("total_issues", 0)
    failed_checks = analysis.get("failed_checks", []) or []
    severity_counts = analysis.get("severity_counts", {}) or {}
    issue_count_by_check = analysis.get("issue_count_by_check", {}) or {}

    lines = [
        "Summary of issues:",
        "",
        f"- Total issues: **{total}**",
    ]

    if severity_counts:
        severity_parts = [
            f"{severity}: {count}"
            for severity, count in severity_counts.items()
            if count
        ]
        if severity_parts:
            lines.append("- Severity: " + ", ".join(severity_parts))

    if failed_checks:
        lines.append("- Failed checks: " + ", ".join(f"`{check}`" for check in failed_checks))
    else:
        lines.append("- Failed checks: none")

    if issue_count_by_check:
        count_parts = [
            f"{check}: {count}"
            for check, count in issue_count_by_check.items()
            if count
        ]
        if count_parts:
            lines.append("- Issue counts by check: " + ", ".join(count_parts))

    if top_findings:
        top = top_findings[0]
        lines.append("")
        lines.append("First item to inspect:")
        lines.append(
            f"- [{top.get('severity', 'unknown')}] "
            f"{top.get('title') or top.get('message') or 'Finding'} "
            f"(check: `{top.get('check', 'unknown')}`)"
        )

        visualization = top.get("visualization")
        if visualization:
            lines.append(f"- Visualization: {visualization}")

        challenge = top.get("challenge")
        if challenge:
            lines.append(f"- Challenge: {challenge}")

        url = top.get("url")
        if url:
            lines.append(f"- GameBus Studio URL: {url}")

    lines.append("")
    lines.append("Use **Findings** for the full list and **Assistant** to explain a specific finding.")

    return "\n".join(lines)


def _highest_priority_finding_answer(question: str, context: dict[str, Any]) -> str | None:
    normalized = _normalized(question)

    if not any(
        phrase in normalized
        for phrase in [
            "highest-priority finding",
            "highest priority finding",
            "top-priority finding",
            "top priority finding",
            "highest-priority issue",
            "highest priority issue",
            "top issue",
        ]
    ):
        return None

    top_findings = context.get("top_findings", []) or []
    if not top_findings:
        return "No prioritized findings are available in the current context."

    finding = top_findings[0]

    title = finding.get("title") or finding.get("message") or "Finding"
    check = finding.get("check") or "unknown"
    severity = finding.get("severity") or "unknown"
    guidance = finding.get("deterministic_gamebus_fix_guidance")

    lines = [
        "Highest-priority finding:",
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
    lines.append(
        "This identifies the highest-priority finding. "
        "Ask `How do I fix this finding?` if you want the GameBus Studio repair steps."
    )

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
        "Using deterministic checker-based guidance for this answer.",
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
    wants_fix_guidance = _is_deterministic_guidance_question(question)

    if guidance and wants_fix_guidance:
        lines.append("")
        lines.append("Deterministic guidance for the highest-priority finding:")
        lines.append(str(guidance))

        source_facts = highest.get("gamebus_studio_source_facts")
        if source_facts:
            lines.append("")
            lines.append("Relevant GameBus Studio facts:")
            lines.append(str(source_facts))
    elif guidance:
        lines.append("")
        lines.append(
            "Ask `How do I fix the highest-priority finding?` "
            "or `How do I fix the secrets issues?` to see the step-by-step fix guidance."
        )
    else:
        lines.append("")
        lines.append(
            "No deterministic GameBus Studio guidance is available for the highest-priority finding."
        )

    return "\n".join(lines)


def _campaign_structure_answer(question: str, context: dict[str, Any]) -> str | None:
    normalized = _normalized(question)

    if "campaign structure" not in normalized and "structure of the campaign" not in normalized:
        return None

    structure = context.get("campaign_structure", {}) or {}
    counts = structure.get("counts", {}) or {}

    if not counts:
        return "No campaign structure snapshot is available in the current context."

    lines = [
        "Campaign structure:",
        "",
        f"- Waves: {counts.get('waves', 0)}",
        f"- Visualizations: {counts.get('visualizations', 0)}",
        f"- Challenges/levels: {counts.get('challenges', 0)}",
        f"- Tasks: {counts.get('tasks', 0)}",
        f"- Transitions: {counts.get('transitions', 0)}",
    ]

    return "\n".join(lines)


class CampaignSupportAgent(BaseAgent):
    name = "campaign_support_agent"

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client

    def run(self, *, question: str, context: dict[str, Any]) -> str:
        if _is_prioritization_question(question):
            return _prioritization_answer()

        deterministic_answer = _deterministic_guidance_answer(question, context)
        if deterministic_answer:
            return deterministic_answer

        issue_summary = _issue_summary_answer(question, context)
        if issue_summary:
            return issue_summary

        highest_priority_answer = _highest_priority_finding_answer(question, context)
        if highest_priority_answer:
            return highest_priority_answer

        structure_answer = _campaign_structure_answer(question, context)
        if structure_answer:
            return structure_answer

        check_answer = _check_explanation_answer(question)
        if check_answer:
            return check_answer

        all_checks_answer = _all_checks_explanation_answer(question)
        if all_checks_answer:
            return all_checks_answer

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

        answer = response.text.strip()

        if _is_weak_llm_answer(answer):
            return _fallback_without_llm(question, context)

        return answer
