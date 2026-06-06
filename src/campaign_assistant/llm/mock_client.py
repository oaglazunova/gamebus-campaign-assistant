from __future__ import annotations

from campaign_assistant.llm.base import LLMResponse


class MockLLMClient:
    provider = "mock"

    def __init__(self, model: str = "mock-model", response_text: str | None = None):
        self.model = model
        self.response_text = response_text or "Mock LLM response."

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> LLMResponse:
        return LLMResponse(
            text=self.response_text,
            provider=self.provider,
            model=self.model,
            available=True,
            error=None,
        )
