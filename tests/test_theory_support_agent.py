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


def test_short_ttm_question_is_deterministic_even_with_bad_llm() -> None:
    class BadLLM:
        provider = "mock"
        model = "bad-test-model"

        def generate(self, **kwargs):
            raise AssertionError("LLM should not be called for short framework questions")

    agent = TheorySupportAgent(llm_client=BadLLM())
    answer = agent.run(question="ttm", context={})

    assert "This is advisory theory-oriented feedback" in answer
    assert "Transtheoretical Model" in answer
    assert "stage" in answer.lower()


def test_ttm_improvement_question_uses_llm() -> None:
    class Response:
        available = True
        provider = "mock"
        model = "mock-model"
        text = "Use stage-specific tasks and feedback."
        error = None

    class RecordingLLM:
        provider = "mock"
        model = "mock-model"

        def __init__(self):
            self.called = False

        def generate(self, **kwargs):
            self.called = True
            return Response()

    llm = RecordingLLM()
    agent = TheorySupportAgent(llm_client=llm)

    answer = agent.run(
        question="How can I make this campaign more TTM-aligned?",
        context={},
    )

    assert llm.called
    assert "This is advisory theory-oriented feedback" in answer
    assert "stage-specific tasks" in answer


def test_user_provided_ttm_stage_mapping_gets_specific_deterministic_response() -> None:
    class BadLLM:
        provider = "mock"
        model = "bad-test-model"

        def generate(self, **kwargs):
            raise AssertionError("LLM should not be called for explicit user-provided TTM mapping")

    agent = TheorySupportAgent(llm_client=BadLLM())

    answer = agent.run(
        question=(
            "The first 4 levels are for preparation, "
            "the next ones are action, and the final one is maintenance."
        ),
        context={},
    )

    assert "user-provided design context" in answer
    assert "preparation" in answer
    assert "action" in answer
    assert "maintenance" in answer
    assert "precontemplation and contemplation" in answer
    assert "relapse/recycling" in answer


def test_theory_agent_rejects_meta_llm_non_answer() -> None:
    class Response:
        available = True
        provider = "mock"
        model = "weak-meta-model"
        text = "I'm ready to help. Please provide more details."
        error = None

    class MetaLLM:
        provider = "mock"
        model = "weak-meta-model"

        def generate(self, **kwargs):
            return Response()

    agent = TheorySupportAgent(llm_client=MetaLLM())

    answer = agent.run(
        question="How can I make this campaign more TTM-aligned?",
        context={},
    )

    assert "I'm ready to help" not in answer
    assert "This is advisory theory-oriented feedback" in answer