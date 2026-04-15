from __future__ import annotations

from abc import ABC, abstractmethod

from campaign_assistant.orchestration.models import AgentContext, AgentResponse


class BaseAgent(ABC):
    name: str

    @abstractmethod
    def run(self, context: AgentContext) -> AgentResponse:
        raise NotImplementedError