from __future__ import annotations

from typing import Any

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.agents.context_builder import format_llm_context_markdown
from campaign_assistant.llm.base import LLMClient
from campaign_assistant.theory_knowledge import load_theory_knowledge_pack
from campaign_assistant.agents.question_types import (
    is_bct_question,
    is_outcome_question,
    is_ttm_question,
)


THEORY_SUPPORT_SYSTEM_PROMPT = """
You are the Theory Support Agent for the GameBus Campaign Assistant.

Your role:
- Provide advisory behavior-change theory reflection.
- Help users reason about possible alignment with BCTs, COM-B, TTM, or related behavior-change concepts.
- Suggest how a campaign could be made more theory-grounded.
- Distinguish observed campaign content from inferred interpretation.

Strict boundaries:
- Your feedback is advisory, not formal validation.
- Do not claim the campaign definitively follows a theory unless the context explicitly shows that.
- Do not invent campaign content that is not present in the context.
- Do not modify or generate campaign files.
- Do not present theory feedback as deterministic checker output.
- If the campaign context is insufficient, say what information would be needed.

Required framing:
- Start theory-alignment answers by saying: "This is advisory theory-oriented feedback, not formal validation."
- Use cautious wording such as "appears to", "may support", "could be strengthened by", "the export suggests".
- Keep answers practical and concise.
"""


def _fallback_without_llm(question: str, context: dict[str, Any]) -> str:
    campaign = context.get("campaign", {}) or {}
    structure = context.get("campaign_structure", {}) or {}
    counts = structure.get("counts", {}) or {}

    return (
        "This is advisory theory-oriented feedback, not formal validation.\n\n"
        "LLM support is not available, so I cannot provide a full theory-oriented "
        "interpretation yet. Based on the extracted campaign structure, the campaign "
        f"contains {counts.get('challenges', 0)} challenge/level item(s), "
        f"{counts.get('tasks', 0)} task(s), and {counts.get('transitions', 0)} transition(s).\n\n"
        "To review theory alignment manually, inspect whether the campaign specifies "
        "target behaviors clearly, supports capability, opportunity, and motivation, "
        "uses feedback/self-monitoring/rewards intentionally, and adapts task difficulty "
        "or support to user readiness.\n\n"
        "To enable richer advisory theory support, start Ollama and configure the selected model."
    )


def _counts_from_context(context: dict[str, Any]) -> dict[str, Any]:
    structure = context.get("campaign_structure", {}) or {}
    return structure.get("counts", {}) or {}


def _outcome_safe_response(context: dict[str, Any]) -> str:
    counts = _counts_from_context(context)

    lines = [
        "This is advisory theory-oriented feedback, not formal validation.",
        "",
        "The campaign export and checker output cannot determine whether the campaign "
        "will cause weight loss or other health outcomes. That requires intervention "
        "content review and empirical evaluation.",
        "",
        "From the current export, I can only comment on visible design features such as "
        "campaign structure, tasks, progression, and possible opportunities for feedback, "
        "self-monitoring, goal setting, or support.",
    ]

    if counts:
        lines.append("")
        lines.append("Visible campaign structure:")
        lines.append(f"- Waves: {counts.get('waves', 0)}")
        lines.append(f"- Visualizations: {counts.get('visualizations', 0)}")
        lines.append(f"- Challenges/levels: {counts.get('challenges', 0)}")
        lines.append(f"- Tasks: {counts.get('tasks', 0)}")
        lines.append(f"- Transitions: {counts.get('transitions', 0)}")

    lines.append("")
    lines.append(
        "To assess likely effectiveness, you would need the intervention rationale, "
        "target population, detailed task content, intended behavior-change mechanisms, "
        "outcome measures, and evaluation data."
    )

    return "\n".join(lines)


def _bct_safe_response(context: dict[str, Any]) -> str:
    counts = _counts_from_context(context)

    lines = [
        "This is advisory theory-oriented feedback, not formal validation.",
        "",
        "From the export alone, I cannot reliably identify which BCTs were intentionally "
        "designed into the campaign. I can suggest BCTs that may be useful to consider "
        "when reviewing or improving the campaign.",
        "",
        "Candidate BCTs to consider:",
        "- **Goal setting / action planning**: make target behaviours concrete and actionable.",
        "- **Self-monitoring**: let users record or reflect on relevant behaviours.",
        "- **Feedback on behaviour or outcomes**: show progress in a way users can understand.",
        "- **Prompts/cues**: remind users at appropriate moments.",
        "- **Graded tasks**: increase difficulty gradually.",
        "- **Social support or social comparison**: use carefully if the campaign has group or team elements.",
        "- **Rewards/incentives**: connect points or badges to meaningful behaviours, not only task completion.",
        "- **Problem solving**: help users identify barriers and plan alternatives.",
    ]

    if counts:
        lines.append("")
        lines.append(
            "The current export structure shows "
            f"{counts.get('tasks', 0)} task(s), "
            f"{counts.get('challenges', 0)} challenge/level item(s), and "
            f"{counts.get('transitions', 0)} transition(s). "
            "This structure may support BCT implementation, but it does not prove that "
            "specific BCTs are present."
        )

    lines.append("")
    lines.append(
        "For a stronger assessment, use organizer-approved design context describing "
        "target behaviours, intended techniques, and intervention rationale."
    )

    return "\n".join(lines)


def _ttm_safe_response(context: dict[str, Any]) -> str:
    counts = _counts_from_context(context)

    lines = [
        "This is advisory theory-oriented feedback, not formal validation.",
        "",
        "I should not infer TTM alignment from waves, levels, or progression structure alone. "
        "Those elements may support staged progression, but they do not by themselves show "
        "that the campaign follows the Transtheoretical Model.",
        "",
        "To assess TTM alignment, I would need evidence such as:",
        "- explicit stage labels or readiness logic;",
        "- stage-specific task content;",
        "- different support for precontemplation, contemplation, preparation, action, and maintenance;",
        "- relapse or recycling paths;",
        "- feedback adapted to the user's readiness to change.",
    ]

    if counts:
        lines.append("")
        lines.append("Visible campaign structure:")
        lines.append(f"- Waves: {counts.get('waves', 0)}")
        lines.append(f"- Visualizations: {counts.get('visualizations', 0)}")
        lines.append(f"- Challenges/levels: {counts.get('challenges', 0)}")
        lines.append(f"- Tasks: {counts.get('tasks', 0)}")
        lines.append(f"- Transitions: {counts.get('transitions', 0)}")

    lines.append("")
    lines.append(
        "If you want to make the campaign more TTM-aligned, consider explicitly mapping "
        "tasks and feedback to readiness stages and adding supportive relapse/recycling paths."
    )

    return "\n".join(lines)


class TheorySupportAgent(BaseAgent):
    name = "theory_support_agent"

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client
        self.theory_knowledge = load_theory_knowledge_pack()

    def run(self, *, question: str, context: dict[str, Any]) -> str:
        if is_outcome_question(question):
            return _outcome_safe_response(context)

        if is_bct_question(question):
            return _bct_safe_response(context)

        if is_ttm_question(question):
            return _ttm_safe_response(context)

        if self.llm_client is None:
            return _fallback_without_llm(question, context)

        context_markdown = format_llm_context_markdown(context)

        user_prompt = f"""
User question:
{question}

Theory reference pack:
{self.theory_knowledge}

Available campaign/checker context:
{context_markdown}

Answer the user using only the theory reference pack and available campaign context.
Do not treat this as formal validation. If the context is insufficient, explain what
additional campaign-design information would be needed.
"""

        response = self.llm_client.generate(
            system_prompt=THEORY_SUPPORT_SYSTEM_PROMPT.strip(),
            user_prompt=user_prompt.strip(),
            temperature=0.2,
        )

        if not response.available:
            return (
                "This is advisory theory-oriented feedback, not formal validation.\n\n"
                "LLM support is currently unavailable.\n\n"
                f"Provider: `{response.provider}`\n"
                f"Model: `{response.model}`\n"
                f"Error: {response.error}\n\n"
                + _fallback_without_llm(question, context)
            )

        if not response.text.strip():
            return (
                "This is advisory theory-oriented feedback, not formal validation.\n\n"
                "The LLM returned an empty response. Try rephrasing the theory question "
                "or check the configured Ollama model."
            )

        answer = response.text.strip()

        required_prefix = "This is advisory theory-oriented feedback, not formal validation."
        if required_prefix.lower() not in answer.lower():
            answer = required_prefix + "\n\n" + answer

        return answer
