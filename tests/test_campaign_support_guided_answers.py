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


def test_fix_followup_uses_deterministic_guidance_even_with_llm_configured(
    minimal_analysis_result: dict,
):
    result = _result_with_terminal_reachability_issue(minimal_analysis_result)
    context = build_llm_context(result)

    class BadLLM:
        provider = "mock"
        model = "bad-test-model"

        def generate(self, **kwargs):
            raise AssertionError("LLM should not be called for deterministic fix guidance")

    agent = CampaignSupportAgent(llm_client=BadLLM())
    answer = agent.run(
        question="How can I make it reachable?",
        context=context,
    )

    assert "Okay" not in answer
    assert "Connect this terminal level to an initial success path" in answer
    assert "Next level when target is met on time" in answer
    assert "Use this level as the start of the level structure" in answer
    assert "GameBus Studio URL" in answer


def test_prepared_finding_question_uses_matching_finding_guidance(
    minimal_analysis_result: dict,
):
    result = _result_with_terminal_reachability_issue(minimal_analysis_result)
    context = build_llm_context(result)

    class BadLLM:
        provider = "mock"
        model = "bad-test-model"

        def generate(self, **kwargs):
            raise AssertionError("LLM should not be called for deterministic finding guidance")

    question = """
    Explain this campaign finding and suggest what I should inspect next.

    Check: reachability
    Severity: high
    Finding: Terminal Challenge not reachable from any initial challenge
    Visualization: Achtsamkeit
    Challenge: [Grandmaster] Tagebuch führen
    Challenge ID: 14549
    Wave ID: 846
    """

    agent = CampaignSupportAgent(llm_client=BadLLM())
    answer = agent.run(question=question, context=context)

    assert "Connect this terminal level to an initial success path" in answer
    assert "Achtsamkeit" in answer
    assert "[Grandmaster] Tagebuch führen" in answer
    assert "Next level when target is met on time" in answer


def test_general_field_question_adds_gamebus_field_facts_to_llm_context(
    minimal_analysis_result: dict,
):
    captured = {}

    class MockLLMResponse:
        available = True
        text = "Mock answer"
        error_message = None

    class RecordingLLM:
        provider = "mock"
        model = "recording-test-model"

        def generate(self, **kwargs):
            captured.update(kwargs)
            return MockLLMResponse()

    agent = CampaignSupportAgent(llm_client=RecordingLLM())
    answer = agent.run(
        question="What does min_days_between_fire mean?",
        context=build_llm_context(minimal_analysis_result),
    )

    assert answer == "Mock answer"

    prompt_text = "\n".join(str(value) for value in captured.values())
    assert "Relevant GameBus Studio field facts" in prompt_text
    assert "Time window for resetting the reward count" in prompt_text
    assert "min_days_between_fire" in prompt_text