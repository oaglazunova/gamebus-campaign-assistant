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
from campaign_assistant.agents.response_guard import uncertainty_response


THEORY_UNCERTAINTY_RULES = """
Uncertainty rules:
- This is advisory theory-oriented feedback, not formal validation.
- Do not claim that a campaign is theory-aligned unless the provided context explicitly supports it.
- If the export does not show enough information, say:
  "I’m not sure from the available campaign export."
- Explain what extra information would be needed, such as task rationale, feedback text, participant choices, stage logic, or intervention mapping.
- Then suggest a better follow-up question.
"""


THEORY_SUPPORT_SYSTEM_PROMPT = f"""
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
- Answer the current question directly after the required advisory sentence.
- Treat recent Assistant replies as already known and do not repeat them before addressing a follow-up.
- When a focused finding is present, assume its metadata is already visible and discuss only the theory/design implication requested by the user.
- Do not repeat campaign counts or generic descriptions of all supported frameworks unless they are directly relevant.
- For improvement questions, provide a short prioritized set of concrete design actions and state what campaign evidence should be reviewed.
- If the user asks for a shorter or clearer version, return only the revised version after the required advisory sentence.
- Keep answers practical and concise.

{THEORY_UNCERTAINTY_RULES}
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

    if normalized in weak_prefixes:
        return True

    weak_phrases = [
        "i'm ready to help",
        "i am ready to help",
        "i'm here to help",
        "i am here to help",
        "please provide",
        "provide the campaign",
        "provide more details",
        "i don't see a specific question",
        "i do not see a specific question",
        "no specific question was asked",
        "unfortunately, i don't see",
        "unfortunately, i do not see",
        "i need more information before",
        "i would need more information before",
    ]

    if any(phrase in normalized for phrase in weak_phrases):
        return True

    # Catches short non-answers such as "Okay, understood" but not "Mock answer".
    tokens = normalized.split()

    # Catches short non-answers such as "Okay, understood" but not "Mock answer".
    tokens = normalized.split()
    if len(tokens) <= 3 and all(token in weak_exact for token in tokens):
        return True

    return False


def _normalized(question: str) -> str:
    return " ".join(str(question or "").lower().strip().split())


def _format_conversation_history(history: list[dict[str, str]] | None) -> str:
    if not history:
        return "No previous conversation messages are available."

    recent = history[-6:]
    lines = []
    for item in recent:
        role = item.get("role", "unknown")
        content = str(item.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines) if lines else "No previous conversation messages are available."


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


def _mentioned_ttm_stages(question: str) -> list[str]:
    normalized = _normalized(question)

    stage_aliases = {
        "precontemplation": [
            "precontemplation",
            "pre-contemplation",
            "not ready",
        ],
        "contemplation": [
            "contemplation",
            "thinking about change",
        ],
        "preparation": [
            "preparation",
            "prepare",
            "preparing",
        ],
        "action": [
            "action",
            "acting",
        ],
        "maintenance": [
            "maintenance",
            "maintain",
            "sustain",
            "sustaining",
        ],
        "relapse/recycling": [
            "relapse",
            "recycling",
            "fallback",
            "fall back",
        ],
    }

    mentioned = []
    for stage, aliases in stage_aliases.items():
        if any(alias in normalized for alias in aliases):
            mentioned.append(stage)

    return mentioned


def _is_user_provided_ttm_mapping(question: str) -> bool:
    normalized = _normalized(question)
    stages = _mentioned_ttm_stages(question)

    progression_words = [
        "level",
        "levels",
        "wave",
        "waves",
        "first",
        "next",
        "then",
        "final",
        "last",
        "after",
        "before",
        "progression",
        "stage",
        "stages",
    ]

    has_progression_language = any(word in normalized for word in progression_words)

    # Avoid treating any random use of "action" as TTM mapping.
    return len(stages) >= 2 and has_progression_language


def _ttm_user_provided_mapping_response(question: str, context: dict[str, Any]) -> str:
    stages = _mentioned_ttm_stages(question)

    if stages:
        stage_text = " → ".join(stages)
    else:
        stage_text = "the stages you described"

    lines = [
        "This is advisory theory-oriented feedback, not formal validation.",
        "",
        "Using your message as **user-provided design context**, the campaign appears to have an intended TTM-like progression:",
        "",
        f"- {stage_text}",
        "",
        "That is more informative than the campaign export alone. The export can show levels, tasks, and transitions, but it usually does not prove why those levels exist or which theory stage they are intended to support.",
        "",
        "What this suggests:",
        "- The campaign may be using staged progression rather than a flat list of tasks.",
        "- Preparation-oriented levels may help users plan or get ready before behaviour change.",
        "- Action-oriented levels may support actually performing the target behaviour.",
        "- Maintenance-oriented levels may support sustaining the behaviour over time.",
        "",
        "What still needs checking:",
        "- Are precontemplation and contemplation intentionally out of scope, or are they missing?",
        "- Do the task texts and feedback actually match the intended stage?",
        "- Are users assessed or routed based on readiness, or does everyone follow the same path?",
        "- Is there support for relapse/recycling, so users can recover after setbacks?",
        "- Does the final maintenance part include long-term support, not only a final challenge?",
        "",
        "A useful next step is to create a simple mapping table: each level → intended TTM stage → task purpose → feedback/support → transition rule.",
    ]

    return "\n".join(lines)


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


def _is_improvement_question(question: str) -> bool:
    normalized = _normalized(question)

    improvement_keywords = [
        "improve",
        "strengthen",
        "enhance",
        "better",
        "make",
        "change",
        "add",
        "adapt",
        "redesign",
        "align",
        "aligned",
        "alignment",
        "theory-aligned",
        "theory grounded",
        "theory-grounded",
        "grounded in theory",
        "support",
    ]

    improvement_phrases = [
        "how can i make",
        "how do i make",
        "how to make",
        "how can this be",
        "how should i",
        "what should i change",
        "what should i add",
        "what would you change",
        "make this campaign",
        "make the campaign",
        "make it more",
        "better aligned",
        "more aligned",
        "more ttm-aligned",
        "more com-b-aligned",
        "more sdt-aligned",
        "more bct-grounded",
    ]

    return (
        any(keyword in normalized for keyword in improvement_keywords)
        and any(
            theory in normalized
            for theory in [
                "ttm",
                "transtheoretical",
                "stage of change",
                "stages of change",
                "com-b",
                "comb",
                "capability",
                "opportunity",
                "motivation",
                "sdt",
                "self-determination",
                "autonomy",
                "competence",
                "relatedness",
                "bct",
                "behaviour change technique",
                "behavior change technique",
            ]
        )
    ) or any(phrase in normalized for phrase in improvement_phrases)


class TheorySupportAgent(BaseAgent):
    name = "theory_support_agent"

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client
        self.last_answer_source = "deterministic"
        self.theory_knowledge = load_theory_knowledge_pack()

    def run(
            self,
            *,
            question: str,
            context: dict[str, Any],
            conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        self.last_answer_source = "deterministic"
        if (
                is_broad_theory_grounding_question(question)
                and not mentions_specific_theory(question)
        ):
            return _theory_clarification_response()

        # Keep outcome/effectiveness claims conservative and deterministic.
        if is_outcome_question(question):
            return _outcome_safe_response(context)

        # If the user explicitly provides TTM stage mapping, use it as
        # user-provided design context instead of falling back to the generic TTM answer.
        if _is_user_provided_ttm_mapping(question):
            return _ttm_user_provided_mapping_response(question, context)

        # Short/direct framework questions should be deterministic and safe.
        if is_bct_question(question) and not _is_improvement_question(question):
            return _bct_safe_response(context)

        if is_ttm_question(question) and not _is_improvement_question(question):
            return _ttm_safe_response(context)

        if is_com_b_question(question) and not _is_improvement_question(question):
            return _com_b_safe_response(context)

        if is_sdt_question(question) and not _is_improvement_question(question):
            return _sdt_safe_response(context)

        # Use the LLM for theory explanation, synthesis, and improvement advice when available.
        if self.llm_client is not None:
            context_markdown = format_llm_context_markdown(context)

            conversation_text = _format_conversation_history(conversation_history)

            user_prompt = f"""
            Recent conversation:
            {conversation_text}

            Current user question:
            {question}

            Theory reference pack:
            {self.theory_knowledge}

            Available campaign/checker context:
            {context_markdown}

            Answer the current question using only the theory reference pack, recent conversation, and available campaign context.

            Important:
            - This is advisory theory-oriented feedback, not formal validation.
            - Do not claim the campaign definitively follows a theory unless the context explicitly shows that.
            - For questions like "how do I make it TTM/COM-B/SDT/BCT-aligned", give practical design advice.
            - If the user gave extra design context in the recent conversation, use it cautiously and say that it is user-provided context.
            - If the export is insufficient, explain what extra design information would be needed.
            - Do not invent task content, feedback text, participant choices, or stage logic.
            - Treat previous Assistant replies as already given. Answer only the new question or requested refinement.
            - If a focused finding is present in the context, do not restate its title, check, severity, or location.
            - Do not repeat campaign structure counts unless the current question depends on them.
            - For improvement advice, prioritize 3-5 concrete actions and identify the evidence the organizer should review for each action.
            - If the user asks for a shorter or clearer version, output only that revised version after the required advisory sentence.
            """

            response = self.llm_client.generate(
                system_prompt=THEORY_SUPPORT_SYSTEM_PROMPT.strip(),
                user_prompt=user_prompt.strip(),
                temperature=0.2,
            )

            if response.available:
                answer = response.text.strip()

                if not _is_weak_llm_answer(answer):
                    required_prefix = "This is advisory theory-oriented feedback, not formal validation."
                    if required_prefix.lower() not in answer.lower():
                        answer = required_prefix + "\n\n" + answer
                    self.last_answer_source = "llm"
                    return answer

        # Deterministic theory fallbacks only when LLM is unavailable or weak.
        if is_bct_question(question):
            return _bct_safe_response(context)

        if is_ttm_question(question):
            return _ttm_safe_response(context)

        if is_com_b_question(question):
            return _com_b_safe_response(context)

        if is_sdt_question(question):
            return _sdt_safe_response(context)

        return _fallback_without_llm(question, context)
