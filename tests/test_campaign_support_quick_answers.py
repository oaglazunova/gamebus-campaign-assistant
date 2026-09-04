from __future__ import annotations

from typing import Any

from campaign_assistant.agents.campaign_support_agent import CampaignSupportAgent
from campaign_assistant.agents.context_builder import build_llm_context
from campaign_assistant.checker.schema import (
    FRIENDLY_CHECK_NAMES,
    REACHABILITY,
    SPELLCHECKER,
    TTMSTRUCTURE,
)


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
    assert "First items to inspect" in answer
    assert "Terminal Challenge not reachable from any initial challenge" in answer
    assert "LLM support is not available" not in answer
    assert "Top findings to inspect" not in answer


def test_explain_top_findings_quick_action_is_deterministic(
    minimal_analysis_result: dict,
) -> None:
    context = build_llm_context(_result_with_two_findings(minimal_analysis_result))
    agent = CampaignSupportAgent(llm_client=FailingLLM())

    answer = agent.run_quick_action(
        quick_action="explain_top_findings",
        context=context,
    )

    assert "Highest-priority finding types" in answer
    assert "Terminal Challenge not reachable from any initial challenge" in answer
    assert "Check:" in answer
    assert "Severity:" in answer
    assert "What this means:" in answer
    assert "Why it matters:" in answer


def test_explain_top_findings_collapses_duplicate_issue_types(
    minimal_analysis_result: dict,
) -> None:
    result = _result_with_two_findings(minimal_analysis_result)
    findings = result["prioritized_issues"]

    duplicate = dict(findings[0])
    duplicate["challenge"] = "Another challenge with the same issue"
    duplicate["challenge_id"] = 99999

    context = {
        "top_findings": [
            findings[0],
            duplicate,
            findings[1],
        ]
    }

    agent = CampaignSupportAgent(llm_client=FailingLLM())

    answer = agent.run_quick_action(
        quick_action="explain_top_findings",
        context=context,
    )

    # The repeated reachability issue type should be explained once.
    assert answer.count("Terminal Challenge not reachable from any initial challenge") == 1
    assert "Repeated in top findings" in answer
    assert "2 similar findings of this issue type" in answer

    # The second distinct issue type should still be explained.
    assert "Task has copies with the same secret but different names" in answer


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
    assert FRIENDLY_CHECK_NAMES[REACHABILITY] in answer
    assert FRIENDLY_CHECK_NAMES[SPELLCHECKER] in answer
    assert FRIENDLY_CHECK_NAMES[TTMSTRUCTURE] in answer
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


def test_weak_llm_answer_is_not_used_for_explicit_overview(
    minimal_analysis_result: dict,
) -> None:
    context = build_llm_context(_result_with_two_findings(minimal_analysis_result))
    agent = CampaignSupportAgent(llm_client=WeakLLM())

    answer = agent.run(question="Give me an overview", context=context)

    assert answer != "Okay"
    assert "Summary of issues" in answer
    assert "Total issues: **2**" in answer
    assert "First items to inspect" in answer


def test_explain_top_findings_collapses_secret_issues_with_different_task_names(
    minimal_analysis_result: dict,
) -> None:
    result = _result_with_two_findings(minimal_analysis_result)
    reachability_finding = result["prioritized_issues"][0]
    secret_finding = result["prioritized_issues"][1]

    first_secret = dict(secret_finding)
    first_secret["title"] = "Task '100 % Vollkorn-Menü!' has copies with same secret but different names"
    first_secret["message"] = first_secret["title"]
    first_secret["challenge"] = "Nutrition challenge A"

    second_secret = dict(secret_finding)
    second_secret["title"] = "Task 'Abendroutine Plannen' has copies with same secret but different names"
    second_secret["message"] = second_secret["title"]
    second_secret["challenge"] = "Nutrition challenge B"
    second_secret["challenge_id"] = 100

    context = {
        "top_findings": [
            first_secret,
            second_secret,
            reachability_finding,
        ]
    }

    agent = CampaignSupportAgent(llm_client=FailingLLM())

    answer = agent.run_quick_action(
        quick_action="explain_top_findings",
        context=context,
    )

    assert answer.count("Task secret reused with different task names") == 1
    assert "Repeated in top findings" in answer
    assert "2 similar findings of this issue type" in answer
    assert "Task '100 % Vollkorn-Menü!'" in answer
    assert "Challenge not reachable from the configured progression" in answer


def test_mixed_priority_reason_and_fix_question_combines_answers(
    minimal_analysis_result: dict,
) -> None:
    result = _result_with_two_findings(minimal_analysis_result)
    finding = dict(result["prioritized_issues"][0])
    finding["deterministic_gamebus_fix_guidance"] = (
        "Connect this terminal level to an initial success path."
    )

    context = {
        "analysis": {
            "total_issues": 1,
            "severity_counts": {"high": 1},
        },
        "top_findings": [finding],
    }

    agent = CampaignSupportAgent(llm_client=FailingLLM())

    answer = agent.run(
        question="Why do I need to inspect this first and how do I fix it?",
        context=context,
    )

    assert "ordered by the deterministic priority score" in answer
    assert "Use the deterministic GameBus Studio guidance" in answer
    assert "Connect this terminal level to an initial success path" in answer
    assert "LLM support is not available" not in answer
    