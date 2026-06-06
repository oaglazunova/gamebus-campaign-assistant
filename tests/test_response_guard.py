from __future__ import annotations

from campaign_assistant.agents.fact_sheet import build_fact_sheet
from campaign_assistant.agents.intent_router import RoutedIntent
from campaign_assistant.agents.response_guard import validate_agent_response


def test_fact_sheet_uses_summary_issue_counts(minimal_analysis_result: dict) -> None:
    result = minimal_analysis_result.copy()
    result["summary"] = dict(minimal_analysis_result["summary"])
    result["summary"]["total_issues"] = 3
    result["summary"]["failed_checks"] = ["secrets"]
    result["summary"]["issue_count_by_check"] = {"secrets": 3}

    facts = build_fact_sheet(result)

    assert facts["checker_facts"]["total_issues"] == 3
    assert facts["checker_facts"]["failed_checks"] == ["secrets"]
    assert facts["checker_facts"]["known_checks_with_issues"] == ["secrets"]


def test_guard_blocks_invented_issues_for_clean_result(minimal_analysis_result: dict) -> None:
    facts = build_fact_sheet(minimal_analysis_result)
    route = RoutedIntent(
        intent="campaign_support",
        agent_name="campaign_support_agent",
        reason="test",
    )

    guard = validate_agent_response(
        question="What should I fix first?",
        answer="The checker found several inconsistencies.",
        facts=facts,
        route=route,
    )

    assert guard.safe is False
    assert guard.reason == "contradicts_clean_checker_result"
    assert guard.replacement_text is not None
    assert "0 issues" in guard.replacement_text


def test_guard_blocks_issue_claim_for_passed_check(minimal_analysis_result: dict) -> None:
    result = minimal_analysis_result.copy()
    result["summary"] = dict(minimal_analysis_result["summary"])
    result["summary"]["total_issues"] = 5
    result["summary"]["failed_checks"] = ["secrets"]
    result["summary"]["passed_checks"] = ["reachability"]
    result["summary"]["issue_count_by_check"] = {"secrets": 5}

    facts = build_fact_sheet(result)
    route = RoutedIntent(
        intent="campaign_support",
        agent_name="campaign_support_agent",
        reason="test",
    )

    guard = validate_agent_response(
        question="What should I inspect first?",
        answer="The checker found several reachability challenges.",
        facts=facts,
        route=route,
    )

    assert guard.safe is False
    assert guard.reason == "unsupported_check_issue_claim:reachability"
    assert guard.replacement_text is not None
    assert "reachability" in guard.replacement_text


def test_guard_blocks_strong_outcome_claim(minimal_analysis_result: dict) -> None:
    facts = build_fact_sheet(minimal_analysis_result)
    route = RoutedIntent(
        intent="theory_support",
        agent_name="theory_support_agent",
        reason="test",
    )

    guard = validate_agent_response(
        question="Will it help people lose weight?",
        answer="This campaign will help people lose weight and will be effective.",
        facts=facts,
        route=route,
    )

    assert guard.safe is False
    assert guard.reason == "unsupported_outcome_claim"
    assert guard.replacement_text is not None
    assert "cannot determine whether the campaign will cause weight loss" in guard.replacement_text
