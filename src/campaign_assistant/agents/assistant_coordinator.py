from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from campaign_assistant.agents.campaign_support_agent import (
    CampaignSupportAgent,
    _is_acknowledgement,
)
from campaign_assistant.agents.context_builder import build_llm_context
from campaign_assistant.agents.response_guard import uncertainty_response
from campaign_assistant.agents.intent_router import IntentRouter
from campaign_assistant.agents.theory_support_agent import TheorySupportAgent
from campaign_assistant.llm.base import LLMClient
from campaign_assistant.agents.fact_sheet import build_fact_sheet
from campaign_assistant.agents.response_guard import validate_agent_response
from campaign_assistant.agents.finding_explainer import explain_prepared_finding



@dataclass
class AssistantResponse:
    text: str
    agent_name: str
    intent: str
    routing_reason: str
    answer_source: str = "unknown"
    guard_applied: bool = False
    guard_reason: str | None = None


class AssistantCoordinator:
    """
    Coordinates one chat interface and routes each user question to one support agent.

    The user sees one Assistant chat. Internally, questions are routed to:
    - CampaignSupportAgent for checker findings, explanations, fixes, prioritization.
    - TheorySupportAgent for BCT/COM-B/TTM/theory-oriented advisory support.
    """

    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        router: IntentRouter | None = None,
    ):
        self.router = router or IntentRouter()
        self.campaign_support_agent = CampaignSupportAgent(llm_client)
        self.theory_support_agent = TheorySupportAgent(llm_client)

    def answer(
            self,
            *,
            question: str,
            result: dict[str, Any],
            conversation_history: list[dict[str, str]] | None = None,
            quick_action: str | None = None,
            focused_finding: dict[str, Any] | None = None,
    ) -> AssistantResponse:
        route = self.router.route(question)
        context = build_llm_context(result)

        if _is_acknowledgement(question):
            return AssistantResponse(
                text=(
                    "You’re welcome. Ask about a specific finding, fix guidance, "
                    "campaign structure, or theory alignment when you want to continue."
                ),
                agent_name="campaign_support_agent",
                intent="acknowledgement",
                routing_reason="Acknowledgement handled without LLM.",
                answer_source="deterministic_acknowledgement",
                guard_applied=False,
                guard_reason=None,
            )
        
        facts = build_fact_sheet(result)

        if isinstance(focused_finding, dict):
            context["focused_finding"] = focused_finding

        if quick_action:
            if quick_action == "theory_grounding":
                return AssistantResponse(
                    text=(
                        "I can help with that, but theory grounding depends on the framework. "
                        "Choose one of the supported lenses: TTM for readiness/stages of change, "
                        "COM-B for capability/opportunity/motivation, BCT Taxonomy for concrete "
                        "behaviour-change techniques, or Self-Determination Theory (SDT) for "
                        "autonomy, competence, and relatedness."
                    ),
                    agent_name="theory_support_agent",
                    intent="theory_support",
                    routing_reason="Quick action: theory grounding.",
                    answer_source="quick_deterministic_theory_clarification",
                    guard_applied=False,
                    guard_reason=None,
                )

            answer = self.campaign_support_agent.run_quick_action(
                quick_action=quick_action,
                context=context,
            )

            return AssistantResponse(
                text=answer,
                agent_name="campaign_support_agent",
                intent="campaign_support",
                routing_reason=f"Quick action: {quick_action}.",
                answer_source=f"quick_deterministic_{quick_action}",
                guard_applied=False,
                guard_reason=None,
            )

        if _is_acknowledgement(question):
            return AssistantResponse(
                text=(
                    "You’re welcome. Ask about a specific finding, fix guidance, "
                    "campaign structure, or theory alignment when you want to continue."
                ),
                agent_name="campaign_support_agent",
                intent="acknowledgement",
                routing_reason="Acknowledgement handled without LLM.",
                answer_source="deterministic_acknowledgement",
                guard_applied=False,
                guard_reason=None,
            )

        prepared_finding_answer = explain_prepared_finding(question)

        if prepared_finding_answer is not None:
            return AssistantResponse(
                text=prepared_finding_answer,
                agent_name="campaign_support_agent",
                intent="campaign_support",
                routing_reason="Prepared finding question answered deterministically.",
                answer_source="prepared_finding",
                guard_applied=False,
                guard_reason=None,
            )

        if route.intent == "unknown":
            return AssistantResponse(
                text=uncertainty_response(question),
                agent_name=route.agent_name,
                intent=route.intent,
                routing_reason=route.reason,
                answer_source="uncertainty",
                guard_applied=False,
                guard_reason=None,
            )

        if route.agent_name == "theory_support_agent":
            answer = self.theory_support_agent.run(
                question=question,
                context=context,
                conversation_history=conversation_history,
            )
        else:
            answer = self.campaign_support_agent.run(
                question=question,
                context=context,
                conversation_history=conversation_history,
            )

        guard = validate_agent_response(
            question=question,
            answer=answer,
            facts=facts,
            route=route,
        )

        guard_applied = False
        guard_reason = None
        answer_source = "agent"

        if not guard.safe and guard.replacement_text:
            answer = guard.replacement_text
            guard_applied = True
            guard_reason = guard.reason
            answer_source = "guard_replacement"

        return AssistantResponse(
            text=answer,
            agent_name=route.agent_name,
            intent=route.intent,
            routing_reason=route.reason,
            answer_source=answer_source,
            guard_applied=guard_applied,
            guard_reason=guard_reason,
        )