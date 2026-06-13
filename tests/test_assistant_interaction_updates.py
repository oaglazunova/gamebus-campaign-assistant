from __future__ import annotations

from typing import Any

from campaign_assistant.agents.assistant_coordinator import AssistantCoordinator
from campaign_assistant.agents.campaign_support_agent import CampaignSupportAgent
from campaign_assistant.agents.context_builder import build_llm_context
from campaign_assistant.ui.assistant_chat import quick_action_focuses_top_finding, focused_finding_for_quick_action


class ExplodingLLM:
    provider = "mock"
    model = "exploding-test-model"

    def generate(self, **kwargs: Any):  # pragma: no cover - should not be called
        raise AssertionError("LLM should not be called for this deterministic answer")


class MockLLMResponse:
    available = True
    provider = "mock"
    model = "mock-test-model"
    error = None

    def __init__(self, text: str):
        self.text = text


class RecordingLLM:
    provider = "mock"
    model = "recording-test-model"

    def __init__(self, text: str = "LLM answer"):
        self.text = text
        self.calls: list[dict[str, Any]] = []

    def generate(self, **kwargs: Any) -> MockLLMResponse:
        self.calls.append(kwargs)
        return MockLLMResponse(self.text)


def _result_with_two_findings(base: dict) -> dict:
    result = base.copy()
    result["summary"] = dict(base["summary"])
    result["summary"].update(
        {
            "total_issues": 2,
            "failed_checks": ["reachability", "secrets"],
            "passed_checks": ["consistency"],
            "issue_count_by_check": {"reachability": 1, "secrets": 1},
            "severity_counts": {"high": 1, "medium": 1},
        }
    )
    result["prioritized_issues"] = [
        {
            "check": "reachability",
            "severity": "high",
            "message": "Terminal Challenge not reachable from any initial challenge",
            "title": "Terminal Challenge not reachable from any initial challenge",
            "visualization": "Achtsamkeit",
            "visualization_id": 3477,
            "challenge": "[Grandmaster] Tagebuch führen",
            "challenge_id": 14549,
            "wave_id": 846,
            "priority_score": 300,
            "priority_rationale": "severity high = 300; active wave boost = 0",
            "url": "https://campaigns.healthyw8.gamebus.eu/editor/for/456/3477/challenges/14549",
        },
        {
            "check": "secrets",
            "severity": "medium",
            "message": "Task has copies with the same secret but different names",
            "title": "Task has copies with the same secret but different names",
            "visualization": "Nutrition",
            "challenge": "[Amateur] Nutrition",
            "challenge_id": 99,
            "priority_score": 200,
        },
    ]
    return result


def test_explicit_summary_is_deterministic_and_does_not_call_llm(minimal_analysis_result: dict) -> None:
    """Explicit summary/overview requests should not depend on the LLM."""
    context = build_llm_context(_result_with_two_findings(minimal_analysis_result))
    agent = CampaignSupportAgent(llm_client=ExplodingLLM())

    answer = agent.run(question="Summarize the issues", context=context)

    assert "Summary of issues" in answer
    assert "Total issues: **2**" in answer
    assert "reachability" in answer
    assert "secrets" in answer
    assert "LLM support is not available" not in answer


def test_explanation_request_uses_llm_when_available(minimal_analysis_result: dict) -> None:
    """Explanatory questions should use the LLM, not generic deterministic summaries."""
    context = build_llm_context(_result_with_two_findings(minimal_analysis_result))
    llm = RecordingLLM("LLM explanation of the highest-priority finding")
    agent = CampaignSupportAgent(llm_client=llm)

    answer = agent.run(question="Explain the highest-priority finding", context=context)

    assert answer == "LLM explanation of the highest-priority finding"
    assert len(llm.calls) == 1
    prompt_text = "\n".join(str(value) for value in llm.calls[0].values())
    assert "Current user question" in prompt_text
    assert "Explain the highest-priority finding" in prompt_text


def test_campaign_agent_accepts_conversation_history_for_followups(minimal_analysis_result: dict) -> None:
    """Follow-up questions need recent conversation context in the LLM prompt."""
    context = build_llm_context(_result_with_two_findings(minimal_analysis_result))
    history = [
        {"role": "user", "content": "Explain the highest-priority finding"},
        {"role": "assistant", "content": "It is a reachability issue in Achtsamkeit."},
    ]
    llm = RecordingLLM("Shorter explanation")
    agent = CampaignSupportAgent(llm_client=llm)

    answer = agent.run(
        question="Can you make this shorter?",
        context=context,
        conversation_history=history,
    )

    assert answer == "Shorter explanation"
    prompt_text = "\n".join(str(value) for value in llm.calls[0].values())
    assert "Recent conversation" in prompt_text
    assert "It is a reachability issue in Achtsamkeit." in prompt_text
    assert "Can you make this shorter?" in prompt_text


def test_coordinator_passes_conversation_history_to_campaign_agent(minimal_analysis_result: dict) -> None:
    captured: dict[str, Any] = {}

    class FakeCampaignAgent:
        def run(self, **kwargs: Any) -> str:
            captured.update(kwargs)
            return "fake answer"

    coordinator = AssistantCoordinator(llm_client=None)
    coordinator.campaign_support_agent = FakeCampaignAgent()
    history = [{"role": "assistant", "content": "Previous answer"}]

    response = coordinator.answer(
        question="Explain this issue",
        result=_result_with_two_findings(minimal_analysis_result),
        conversation_history=history,
    )

    assert response.text == "fake answer"
    assert captured["conversation_history"] == history


def test_answer_source_is_populated_for_unknown_route(minimal_analysis_result: dict) -> None:
    coordinator = AssistantCoordinator(llm_client=None)

    response = coordinator.answer(
        question="How is the weather now?",
        result=minimal_analysis_result,
    )

    assert response.intent == "unknown"
    assert response.answer_source == "uncertainty"
    assert "not sure" in response.text.lower() or "outside" in response.text.lower()


def test_prepared_finding_answer_source_is_populated(minimal_analysis_result: dict) -> None:
    coordinator = AssistantCoordinator(llm_client=None)
    question = """
    Explain this campaign finding.

    Check: reachability
    Severity: high
    Finding: Terminal Challenge not reachable from any initial challenge
    Visualization: Achtsamkeit
    Challenge: [Grandmaster] Tagebuch voeren
    Challenge ID: 14549
    Wave ID: 846
    """

    response = coordinator.answer(
        question=question,
        result=_result_with_two_findings(minimal_analysis_result),
    )

    assert response.answer_source == "prepared_finding"
    assert response.intent == "campaign_support"
    assert "What this means" in response.text or "What to inspect next" in response.text


def test_acknowledgement_is_handled_before_unknown_route(
    minimal_analysis_result: dict,
) -> None:
    coordinator = AssistantCoordinator(llm_client=None)

    response = coordinator.answer(
        question="ok",
        result=minimal_analysis_result,
    )

    assert "You’re welcome" in response.text
    assert response.agent_name == "campaign_support_agent"
    assert response.intent == "acknowledgement"
    assert response.answer_source == "deterministic_acknowledgement"
    assert not response.guard_applied


def test_quick_action_focuses_top_finding_helper() -> None:
    assert quick_action_focuses_top_finding("inspect_first")
    assert quick_action_focuses_top_finding("explain_top_finding")
    assert quick_action_focuses_top_finding("explain_top_findings")

    assert not quick_action_focuses_top_finding("summarize_issues")
    assert not quick_action_focuses_top_finding("campaign_structure")
    assert not quick_action_focuses_top_finding("prioritization")
    assert not quick_action_focuses_top_finding(None)


def test_focused_finding_for_quick_action_returns_top_finding(
    minimal_analysis_result: dict,
) -> None:
    result = _result_with_two_findings(minimal_analysis_result)

    focused = focused_finding_for_quick_action(
        result=result,
        quick_action="inspect_first",
    )

    assert focused is not None
    assert focused["title"] == "Terminal Challenge not reachable from any initial challenge"
    assert focused["check"] == "reachability"
    assert focused["challenge_id"] == 14549


def test_focused_finding_for_non_focusing_quick_action_returns_none(
    minimal_analysis_result: dict,
) -> None:
    result = _result_with_two_findings(minimal_analysis_result)

    focused = focused_finding_for_quick_action(
        result=result,
        quick_action="summarize_issues",
    )

    assert focused is None