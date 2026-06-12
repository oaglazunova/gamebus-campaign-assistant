from __future__ import annotations

from typing import Any

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.agents.context_builder import format_llm_context_markdown
from campaign_assistant.llm.base import LLMClient
from campaign_assistant.theory_knowledge import load_theory_knowledge_pack
from campaign_assistant.agents.question_types import (
    is_bct_question,
    is_broad_theory_grounding_question,
    is_com_b_question,
    is_outcome_question,
    is_sdt_question,
    is_ttm_question,
    mentions_specific_theory,
)


THEORY_SUPPORT_SYSTEM_PROMPT = """
You are the Theory Support Agent for the GameBus Campaign Assistant.

Your role:
- Provide advisory behavior-change theory reflection.
- Help users reason about possible alignment with BCTs, COM-B, TTM, Self-Determination Theory, or related behavior-change concepts.
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


def _normalized(question: str) -> str:
    return " ".join(str(question or "").lower().strip().split())


def _normalized(question: str) -> str:
    return " ".join(str(question or "").lower().strip().split())


def _is_improvement_question(question: str) -> bool:
    normalized = _normalized(question)

    return any(
        phrase in normalized
        for phrase in [
            "how to make",
            "how can i make",
            "how do i make",
            "make the campaign",
            "make this campaign",
            "make it more",
            "more aligned",
            "better aligned",
            "more theory-aligned",
            "more theory grounded",
            "more theory-grounded",
            "improve",
            "strengthen",
            "what should i change",
            "what should i add",
            "how should i design",
            "how to design",
            "what would you change",
        ]
    )


def _is_ttm_improvement_question(question: str) -> bool:
    normalized = _normalized(question)

    if not any(
        term in normalized
        for term in [
            "ttm",
            "transtheoretical",
            "stage of change",
            "stages of change",
        ]
    ):
        return False

    return any(
        phrase in normalized
        for phrase in [
            "how to make",
            "how can i make",
            "make the campaign",
            "make this campaign",
            "make it",
            "more ttm-aligned",
            "ttm-aligned",
            "align with ttm",
            "aligned with ttm",
            "make it aligned",
            "improve",
            "strengthen",
            "what should i change",
            "what should i add",
            "how should i design",
        ]
    )


def _com_b_improvement_response(context: dict[str, Any]) -> str:
    return "\n".join(
        [
            "This is advisory theory-oriented feedback, not formal validation.",
            "",
            "To make the campaign more COM-B-aligned, I would explicitly design each task around capability, opportunity, and motivation.",
            "",
            "Recommended design changes:",
            "",
            "1. **Define the target behaviour clearly**",
            "For each task, specify what behaviour the participant should perform, for example walking, meal planning, sleep preparation, food logging, or reflection.",
            "",
            "2. **Check Capability**",
            "Add support for knowledge, skills, and confidence. Examples: short explanations, examples, tutorials, simple first steps, or reflection tasks that help users understand what to do.",
            "",
            "3. **Check Opportunity**",
            "Address practical and social barriers. Examples: low-effort alternatives, reminders, environmental prompts, social support, or tasks that help users plan around time, weather, family, or work constraints.",
            "",
            "4. **Check Motivation**",
            "Support intention, positive reinforcement, habit formation, and personal relevance. Examples: progress feedback, meaningful goals, reflection on benefits, streaks used carefully, and supportive rewards.",
            "",
            "5. **Avoid relying on points alone**",
            "Points and levels can support motivation, but they do not by themselves address capability or opportunity. Make sure the campaign also helps users understand, plan, and perform the behaviour.",
            "",
            "6. **Create a COM-B mapping table**",
            "Use columns such as: task/level, target behaviour, Capability support, Opportunity support, Motivation support, missing support, and proposed change.",
        ]
    )


def _sdt_improvement_response(context: dict[str, Any]) -> str:
    return "\n".join(
        [
            "This is advisory theory-oriented feedback, not formal validation.",
            "",
            "To make the campaign more Self-Determination Theory-aligned, I would check whether the design supports autonomy, competence, and relatedness without making the gamification feel controlling.",
            "",
            "Recommended design changes:",
            "",
            "1. **Strengthen autonomy**",
            "Give users meaningful choices where possible: choice of task, timing, difficulty, goal, or reflection topic. Avoid language that sounds pressuring, guilt-based, or controlling.",
            "",
            "2. **Strengthen competence**",
            "Make tasks achievable, give clear instructions, show progress, and help users experience mastery. Difficulty should increase gradually rather than suddenly.",
            "",
            "3. **Strengthen relatedness**",
            "Use social or team elements to create support and recognition, not shame or pressure. If the campaign has teams, feedback should feel encouraging rather than competitive in a harmful way.",
            "",
            "4. **Review rewards carefully**",
            "Points, badges, and levels should support meaningful progress. If rewards feel like the only reason to act, they may undermine autonomous motivation.",
            "",
            "5. **Improve feedback tone**",
            "Feedback should explain why a task matters, acknowledge effort, and support user choice. Avoid feedback that implies failure, blame, or obedience.",
            "",
            "6. **Create an SDT mapping table**",
            "Use columns such as: task/level, autonomy support, competence support, relatedness support, potentially controlling elements, and proposed change.",
        ]
    )


def _bct_improvement_response(context: dict[str, Any]) -> str:
    return "\n".join(
        [
            "This is advisory theory-oriented feedback, not formal validation.",
            "",
            "To make the campaign more BCT-grounded, I would explicitly select which behaviour-change techniques each task is meant to implement instead of trying to infer them afterwards.",
            "",
            "Recommended design changes:",
            "",
            "1. **Define the target behaviour for each task**",
            "A BCT is only meaningful if it is linked to a clear behaviour, such as walking, logging meals, reducing screen time, preparing food, or reflecting on sleep habits.",
            "",
            "2. **Choose a small set of intended BCTs**",
            "Useful candidates may include goal setting, action planning, self-monitoring, feedback, prompts/cues, graded tasks, problem solving, social support, and rewards.",
            "",
            "3. **Operationalise each BCT visibly**",
            "Do not only label a task as a BCT. Make sure the task actually contains the mechanism. For example, action planning should ask when, where, and how the behaviour will be done.",
            "",
            "4. **Check whether rewards match meaningful behaviour**",
            "Points should reward relevant behaviour or useful preparation, not only clicking through tasks.",
            "",
            "5. **Avoid over-coding**",
            "Do not claim too many BCTs for one task unless the content clearly supports them. A smaller, well-justified set is more credible.",
            "",
            "6. **Create a BCT mapping table**",
            "Use columns such as: task/level, target behaviour, intended BCT, evidence in task text, missing content, and proposed rewrite.",
        ]
    )


def _outcome_safe_response(context: dict[str, Any]) -> str:
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

    lines.append("")
    lines.append(
        "To assess likely effectiveness, you would need the intervention rationale, "
        "target population, detailed task content, intended behavior-change mechanisms, "
        "outcome measures, and evaluation data."
    )

    return "\n".join(lines)


def _bct_safe_response(context: dict[str, Any]) -> str:
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

    lines.append("")
    lines.append(
        "For a stronger assessment, use organizer-approved design context describing "
        "target behaviours, intended techniques, and intervention rationale."
    )

    return "\n".join(lines)


def _ttm_safe_response(context: dict[str, Any]) -> str:
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

    lines.append("")
    lines.append(
        "If you want to make the campaign more TTM-aligned, consider explicitly mapping "
        "tasks and feedback to readiness stages and adding supportive relapse/recycling paths."
    )

    return "\n".join(lines)


def _ttm_improvement_response(context: dict[str, Any]) -> str:
    return "\n".join(
        [
            "This is advisory theory-oriented feedback, not formal validation.",
            "",
            "To make the campaign more TTM-aligned, I would make the stage logic explicit rather than relying on waves, levels, or points alone.",
            "",
            "Recommended design changes:",
            "",
            "1. **Define the intended stage for each task or level**",
            "Map campaign content to precontemplation, contemplation, preparation, action, and maintenance. This makes it clear which part of behaviour change each task is meant to support.",
            "",
            "2. **Make task content stage-specific**",
            "- Precontemplation: awareness, reflection, perceived relevance, risks/benefits.",
            "- Contemplation: pros/cons, personal motivation, barriers, ambivalence.",
            "- Preparation: planning, goal setting, implementation intentions, choosing first steps.",
            "- Action: concrete behaviour performance, self-monitoring, feedback, reinforcement.",
            "- Maintenance: habit support, relapse prevention, coping plans, long-term identity support.",
            "",
            "3. **Add readiness-based progression logic**",
            "Progression should reflect readiness or behavioural evidence, not only task completion or points. For example, users could move from preparation to action after completing planning tasks or recording an initial behaviour.",
            "",
            "4. **Add relapse/recycling paths**",
            "TTM assumes that people may move backwards as well as forwards. The campaign should support returning to an earlier stage without framing it as failure.",
            "",
            "5. **Adapt feedback to the user’s stage**",
            "Early-stage feedback should be reflective and non-controlling. Later-stage feedback can be more action-oriented, reinforcing, and focused on maintaining progress.",
            "",
            "6. **Document the theory mapping**",
            "Create a simple design table with columns such as: task/level, intended TTM stage, target behaviour, intended mechanism, feedback type, and progression rule.",
            "",
            "A practical next step is to review the current tasks and assign each one to a TTM stage. Tasks that do not clearly fit a stage may need rewriting, moving, or additional feedback logic.",
        ]
    )


def _theory_clarification_response() -> str:
    return (
        "I can help with that, but theory grounding depends on the framework. "
        "Choose one of the supported lenses: TTM for readiness/stages of change, "
        "COM-B for capability/opportunity/motivation, BCT Taxonomy for concrete behaviour-change techniques, "
        "or Self-Determination Theory (SDT) for autonomy, competence, and relatedness."
    )


def _com_b_safe_response(context: dict[str, Any]) -> str:
    lines = [
        "This is advisory theory-oriented feedback, not formal validation.",
        "",
        "For COM-B, I would review whether the campaign supports:",
        "- **Capability**: users have the knowledge, skills, and confidence needed to perform the target behaviour;",
        "- **Opportunity**: the campaign helps users deal with practical, social, or environmental barriers;",
        "- **Motivation**: the campaign supports intention, habit formation, feedback, and meaningful reasons to act.",
        "",
        "From the export alone, I cannot confirm that the campaign is COM-B-aligned. "
        "The export shows structure, tasks, levels, and transitions, but it does not fully show the intervention rationale "
        "or the intended mechanism of action.",
    ]

    lines.append("")
    lines.append(
        "A useful next step is to map each campaign task to one or more COM-B components "
        "and check whether the campaign has enough support for capability, opportunity, and motivation."
    )

    return "\n".join(lines)



def _sdt_safe_response(context: dict[str, Any]) -> str:
    lines = [
        "This is advisory theory-oriented feedback, not formal validation.",
        "",
        "For Self-Determination Theory, I would review whether the campaign supports:",
        "- **Autonomy**: users experience meaningful choice, personal relevance, and non-controlling guidance;",
        "- **Competence**: users receive achievable tasks, clear feedback, and a sense of progress or mastery;",
        "- **Relatedness**: users feel socially supported, connected, or recognized without excessive pressure.",
        "",
        "From the export alone, I cannot confirm that the campaign is SDT-aligned. "
        "The export shows structure, tasks, levels, and transitions, but it does not fully show tone, rationale, "
        "participant choice, or how feedback is experienced by users.",
    ]

    lines.append("")
    lines.append(
        "A useful next step is to map each task and feedback message to autonomy, competence, "
        "and relatedness. Also check whether points, levels, and rewards feel supportive rather than controlling."
    )

    return "\n".join(lines)


class TheorySupportAgent(BaseAgent):
    name = "theory_support_agent"

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client
        self.theory_knowledge = load_theory_knowledge_pack()

    def run(self, *, question: str, context: dict[str, Any]) -> str:
        if (
                is_broad_theory_grounding_question(question)
                and not mentions_specific_theory(question)
        ):
            return _theory_clarification_response()

        if is_outcome_question(question):
            return _outcome_safe_response(context)

        if is_bct_question(question) and _is_improvement_question(question):
            return _bct_improvement_response(context)

        if is_ttm_question(question) and _is_improvement_question(question):
            return _ttm_improvement_response(context)

        if is_com_b_question(question) and _is_improvement_question(question):
            return _com_b_improvement_response(context)

        if is_sdt_question(question) and _is_improvement_question(question):
            return _sdt_improvement_response(context)

        if is_bct_question(question):
            return _bct_safe_response(context)

        if is_ttm_question(question):
            return _ttm_safe_response(context)

        if is_com_b_question(question):
            return _com_b_safe_response(context)

        if is_sdt_question(question):
            return _sdt_safe_response(context)

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

        answer = response.text.strip()

        if _is_weak_llm_answer(answer):
            return _fallback_without_llm(question, context)

        required_prefix = "This is advisory theory-oriented feedback, not formal validation."
        if required_prefix.lower() not in answer.lower():
            answer = required_prefix + "\n\n" + answer

        return answer
