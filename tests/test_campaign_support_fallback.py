from __future__ import annotations

from campaign_assistant.agents.campaign_support_agent import CampaignSupportAgent
from campaign_assistant.agents.context_builder import build_llm_context


def _result_with_terminal_reachability_issue(base: dict) -> dict:
    result = base.copy()
    result["summary"] = dict(base["summary"])
    result["summary"]["total_issues"] = 1
    result["summary"]["failed_checks"] = ["reachability"]
    result["summary"]["passed_checks"] = []
    result["summary"]["issue_count_by_check"] = {"reachability": 1}
    result["summary"]["severity_counts"] = {"high": 1}
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
        }
    ]
    return result


def test_highest_priority_question_uses_deterministic_answer_without_llm(
    minimal_analysis_result: dict,
) -> None:
    result = _result_with_terminal_reachability_issue(minimal_analysis_result)
    context = build_llm_context(result)

    agent = CampaignSupportAgent(llm_client=None)
    answer = agent.run(
        question="Explain the highest-priority finding",
        context=context,
    )

    assert "Highest-priority finding" in answer
    assert "LLM support is not available" not in answer
    assert "Connect this terminal level to an initial success path" in answer
    assert "Next level when target is met on time" in answer
    assert "GameBus Studio URL" in answer


def test_campaign_support_fallback_includes_gamebus_source_facts(
    minimal_analysis_result: dict,
) -> None:
    result = _result_with_terminal_reachability_issue(minimal_analysis_result)
    context = build_llm_context(result)

    agent = CampaignSupportAgent(llm_client=None)
    answer = agent.run(
        question="Where should I fix this in GameBus Studio?",
        context=context,
    )

    assert "Relevant GameBus Studio facts" in answer or "Relevant GameBus Studio source facts" in answer
    assert "Level settings" in answer
    assert "success_next" in answer
