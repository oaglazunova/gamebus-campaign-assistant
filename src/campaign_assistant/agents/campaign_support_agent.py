from __future__ import annotations

from typing import Any

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.agents.context_builder import format_llm_context_markdown
from campaign_assistant.llm.base import LLMClient


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

Use cautious wording:
- "The checker found..."
- "You should inspect..."
- "A likely next step is..."
- "This may indicate..."

Keep answers practical and concise.
"""


def _fallback_without_llm(question: str, context: dict[str, Any]) -> str:
    analysis = context.get("analysis", {}) or {}
    top_findings = context.get("top_findings", []) or []
    structure = context.get("campaign_structure", {}) or {}
    counts = structure.get("counts", {}) or {}

    total = analysis.get("total_issues", 0)
    failed_checks = analysis.get("failed_checks", []) or []

    lines = [
        "LLM support is not available, so I can only provide a deterministic summary.",
        "",
        f"The selected checks found **{total}** issue(s).",
    ]

    if failed_checks:
        lines.append(
            "Checks with findings: "
            + ", ".join(f"`{check}`" for check in failed_checks)
            + "."
        )
    else:
        lines.append("No failed checks were reported.")

    if counts:
        lines.append("")
        lines.append("Campaign structure:")
        lines.append(f"- Waves: {counts.get('waves', 0)}")
        lines.append(f"- Visualizations: {counts.get('visualizations', 0)}")
        lines.append(f"- Challenges/levels: {counts.get('challenges', 0)}")
        lines.append(f"- Tasks: {counts.get('tasks', 0)}")
        lines.append(f"- Transitions: {counts.get('transitions', 0)}")

    if top_findings:
        lines.append("")
        lines.append("Top findings to inspect:")
        for idx, finding in enumerate(top_findings[:5], start=1):
            title = finding.get("title") or "Finding"
            check = finding.get("check") or "unknown"
            severity = finding.get("severity") or "unknown"
            lines.append(f"{idx}. [{severity}] {title} (check: `{check}`)")

    lines.append("")
    lines.append(
        "To enable richer explanations, start Ollama and configure the selected model."
    )

    return "\n".join(lines)


class CampaignSupportAgent(BaseAgent):
    name = "campaign_support_agent"

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client

    def run(self, *, question: str, context: dict[str, Any]) -> str:
        if self.llm_client is None:
            return _fallback_without_llm(question, context)

        context_markdown = format_llm_context_markdown(context)

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
