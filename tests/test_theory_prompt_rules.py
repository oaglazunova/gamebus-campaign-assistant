from __future__ import annotations

from campaign_assistant.agents.context_builder import build_llm_context
from campaign_assistant.agents.theory_support_agent import (
    THEORY_SUPPORT_SYSTEM_PROMPT,
    TheorySupportAgent,
)


class MockLLMResponse:
    available = True
    text = "This is advisory theory-oriented feedback, not formal validation. Mock theory answer."
    error = None


class RecordingLLM:
    provider = "mock"
    model = "recording-test-model"

    def __init__(self):
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return MockLLMResponse()


def test_theory_system_prompt_includes_uncertainty_rules() -> None:
    assert "I’m not sure from the available campaign export" in THEORY_SUPPORT_SYSTEM_PROMPT
    assert "Do not claim that a campaign is theory-aligned" in THEORY_SUPPORT_SYSTEM_PROMPT
    assert "{THEORY_UNCERTAINTY_RULES}" not in THEORY_SUPPORT_SYSTEM_PROMPT


def test_theory_llm_prompt_contains_theory_pack_and_campaign_context(minimal_analysis_result: dict) -> None:
    llm = RecordingLLM()
    agent = TheorySupportAgent(llm_client=llm)
    context = build_llm_context(minimal_analysis_result)

    answer = agent.run(question="How can I make this campaign more TTM-aligned?", context=context)

    assert "advisory theory-oriented feedback" in answer
    assert len(llm.calls) == 1
    prompt_text = "\n".join(str(value) for value in llm.calls[0].values())
    assert "Theory reference pack" in prompt_text
    assert "Available campaign/checker context" in prompt_text
    assert "TTM" in prompt_text or "Transtheoretical" in prompt_text
