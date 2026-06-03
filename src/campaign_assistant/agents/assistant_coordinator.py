from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from campaign_assistant.agents.campaign_support_agent import CampaignSupportAgent
from campaign_assistant.agents.context_builder import build_llm_context
from campaign_assistant.agents.intent_router import IntentRouter, RoutedIntent
from campaign_assistant.agents.theory_support_agent import TheorySupportAgent
from campaign_assistant.llm.base import LLMClient


@dataclass
class AssistantResponse:
    text: str
    agent_name: str
    intent: str
    routing_reason: str


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

        return AssistantResponse(
            text=answer,
            agent_name=route.agent_name,
            intent=route.intent,
            routing_reason=route.reason,
        )
