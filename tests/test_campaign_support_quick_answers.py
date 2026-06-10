from __future__ import annotations

from typing import Any

from campaign_assistant.agents.campaign_support_agent import CampaignSupportAgent
from campaign_assistant.agents.context_builder import build_llm_context


class FailingLLM:
    provider = "mock"
    model = "failing-test-model"

    def generate(self, **kwargs: Any):  # pragma: no cover - must not be called
        raise AssertionError("LLM should not be called for deterministic quick answers")


class WeakLLMResponse:
    available = True
    provider = "mock"
    model = "weak-test-model"
    text = "Okay"
    error = None


class WeakLLM:
    provider = "mock"
    model = "weak-test-model"

    def generate(self, **kwargs: Any):
        return WeakLLMResponse()


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


def test_summarize_issues_is_deterministic_and_concise(minimal_analysis_result: dict) -> None:
    context = build_llm_context(_result_with_two_findings(minimal_analysis_result))
    agent = CampaignSupportAgent(llm_client=FailingLLM())

    answer = agent.run(question="Summarize the issues", context=context)

    assert "Summary of issues" in answer
    assert "Total issues: **2**" in answer
    assert "reachability" in answer
    assert "secrets" in answer
    assert "First item to inspect" in answer
    assert "Terminal Challenge not reachable from any initial challenge" in answer
    assert "LLM support is not available" not in answer
    assert "Top findings to inspect" not in answer


def test_highest_priority_finding_answer_is_deterministic(minimal_analysis_result: dict) -> None:
    context = build_llm_context(_result_with_two_findings(minimal_analysis_result))
    agent = CampaignSupportAgent(llm_client=FailingLLM())

    answer = agent.run(question="Explain the highest-priority finding", context=context)

    assert "Highest-priority finding" in answer
    assert "Terminal Challenge not reachable from any initial challenge" in answer
    assert "Connect this terminal level to an initial success path" in answer
    assert "Next level when target is met on time" in answer
    assert "Task has copies with the same secret" not in answer
    assert "LLM support is not available" not in answer


def test_campaign_structure_answer_is_deterministic(minimal_analysis_result: dict) -> None:
    context = build_llm_context(_result_with_two_findings(minimal_analysis_result))
    agent = CampaignSupportAgent(llm_client=FailingLLM())

    answer = agent.run(question="What is the campaign structure?", context=context)

    assert answer.startswith("Campaign structure:")
    assert "Waves:" in answer
    assert "Visualizations:" in answer
    assert "Challenges/levels:" in answer
    assert "Top findings" not in answer
    assert "LLM support is not available" not in answer


def test_all_checks_question_does_not_trigger_fix_guidance(minimal_analysis_result: dict) -> None:
    context = build_llm_context(_result_with_two_findings(minimal_analysis_result))
    agent = CampaignSupportAgent(llm_client=FailingLLM())

    answer = agent.run(question="What do the checks check?", context=context)

    assert "deterministic checks inspect" in answer
    assert "Reachability" in answer
    assert "Spellchecker" in answer
    assert "TTM structure" in answer
    assert "Use the deterministic GameBus Studio guidance" not in answer


def test_prioritization_question_is_deterministic(minimal_analysis_result: dict) -> None:
    context = build_llm_context(_result_with_two_findings(minimal_analysis_result))
    agent = CampaignSupportAgent(llm_client=FailingLLM())

    answer = agent.run(question="How is prioritization calculated?", context=context)

    assert "priority_score" in answer
    assert "active_wave_boost" in answer
    assert "visualization internals = medium" in answer
    assert "TTM structure = medium" in answer
    assert "LLM support is not available" not in answer


def test_weak_llm_answer_is_replaced_with_deterministic_fallback(minimal_analysis_result: dict) -> None:
    context = build_llm_context(_result_with_two_findings(minimal_analysis_result))
    agent = CampaignSupportAgent(llm_client=WeakLLM())

    answer = agent.run(question="Give me an overview", context=context)

    assert answer != "Okay"
    assert "The selected checks found" in answer
