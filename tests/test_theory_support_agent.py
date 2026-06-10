from __future__ import annotations

from campaign_assistant.agents.context_builder import build_llm_context
from campaign_assistant.agents.theory_support_agent import TheorySupportAgent


def test_broad_theory_question_asks_for_framework(minimal_analysis_result: dict) -> None:
    agent = TheorySupportAgent(llm_client=None)
    context = build_llm_context(minimal_analysis_result)

    answer = agent.run(question="How theory-grounded is this campaign?", context=context)

    assert "depends on the framework" in answer
    assert "TTM" in answer
    assert "COM-B" in answer
    assert "BCT Taxonomy" in answer
    assert "Self-Determination Theory" in answer


def test_com_b_question_uses_deterministic_response(minimal_analysis_result: dict) -> None:
    agent = TheorySupportAgent(llm_client=None)
    context = build_llm_context(minimal_analysis_result)

    answer = agent.run(question="COM-B", context=context)

    assert "advisory theory-oriented feedback" in answer
    assert "Capability" in answer
    assert "Opportunity" in answer
    assert "Motivation" in answer
    assert "cannot confirm" in answer


def test_ttm_follow_up_uses_deterministic_response(minimal_analysis_result: dict) -> None:
    agent = TheorySupportAgent(llm_client=None)
    context = build_llm_context(minimal_analysis_result)

    answer = agent.run(question="and TTM?", context=context)

    assert "advisory theory-oriented feedback" in answer
    assert "Transtheoretical Model" in answer
    assert "stage" in answer.lower()
    assert "relapse" in answer.lower()


def test_sdt_question_uses_deterministic_response(minimal_analysis_result: dict) -> None:
    agent = TheorySupportAgent(llm_client=None)
    context = build_llm_context(minimal_analysis_result)

    answer = agent.run(question="SDT", context=context)

    assert "advisory theory-oriented feedback" in answer
    assert "Self-Determination Theory" in answer
    assert "Autonomy" in answer
    assert "Competence" in answer
    assert "Relatedness" in answer
    assert "cannot confirm" in answer


def test_autonomy_question_routes_to_sdt_response(minimal_analysis_result: dict) -> None:
    agent = TheorySupportAgent(llm_client=None)
    context = build_llm_context(minimal_analysis_result)

    answer = agent.run(
        question="How can I make this campaign more autonomy-supportive?",
        context=context,
    )

    assert "Self-Determination Theory" in answer
    assert "Autonomy" in answer
    assert "Competence" in answer
    assert "Relatedness" in answer
