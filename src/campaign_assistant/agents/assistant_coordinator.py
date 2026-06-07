from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from campaign_assistant.agents.campaign_support_agent import CampaignSupportAgent
from campaign_assistant.agents.context_builder import build_llm_context
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

    def answer(self, *, question: str, result: dict[str, Any]) -> AssistantResponse:
        route = self.router.route(question)
        context = build_llm_context(result)
        facts = build_fact_sheet(result)

        prepared_finding_answer = explain_prepared_finding(question)

        if prepared_finding_answer is not None:
            return AssistantResponse(
                text=prepared_finding_answer,
                agent_name="campaign_support_agent",
                intent="campaign_support",
                routing_reason="Prepared finding question answered deterministically.",
                guard_applied=False,
                guard_reason=None,
            )

        if route.agent_name == "theory_support_agent":
            answer = self.theory_support_agent.run(
                question=question,
                context=context,
            )
        else:
            answer = self.campaign_support_agent.run(
                question=question,
                context=context,
            )

        guard = validate_agent_response(
            question=question,
            answer=answer,
            facts=facts,
            route=route,
        )

        guard_applied = False
        guard_reason = None

        if not guard.safe and guard.replacement_text:
            answer = guard.replacement_text
            guard_applied = True
            guard_reason = guard.reason

        return AssistantResponse(
            text=answer,
            agent_name=route.agent_name,
            intent=route.intent,
            routing_reason=route.reason,
            guard_applied=guard_applied,
            guard_reason=guard_reason,
        )