from __future__ import annotations

from campaign_assistant.ui.assistant_chat import answer_question


def test_assistant_guard_replaces_clean_result_hallucination(
    monkeypatch,
    minimal_analysis_result: dict,
) -> None:
    monkeypatch.setenv("CAMPAIGN_ASSISTANT_LLM_PROVIDER", "mock")
    monkeypatch.setenv("CAMPAIGN_ASSISTANT_LLM_ENABLED", "true")
    monkeypatch.setenv(
        "CAMPAIGN_ASSISTANT_MOCK_LLM_RESPONSE",
        "The checker found several inconsistencies.",
    )

    answer = answer_question("What should I fix first?", minimal_analysis_result)

    assert "The checker found several inconsistencies" not in answer
    assert "0 issues" in answer


def test_prepared_secrets_finding_is_explained_without_unrelated_checks(
    minimal_analysis_result: dict,
) -> None:
    from campaign_assistant.ui.assistant_chat import answer_question

    result = minimal_analysis_result.copy()
    result["summary"] = dict(minimal_analysis_result["summary"])
    result["summary"]["total_issues"] = 2
    result["summary"]["failed_checks"] = ["secrets", "targetpointsreachable"]
    result["summary"]["passed_checks"] = ["consistency"]
    result["summary"]["issue_count_by_check"] = {
        "secrets": 1,
        "targetpointsreachable": 1,
    }

    question = (
        "Explain this campaign finding and suggest what I should inspect next.\n\n"
        "Check: secrets Severity: medium Finding: Task 'Example task' has copies "
        "with the same secret 'example-secret', but that have different names "
        "(see challenges ['1 (Level A)', '2 (Level B)']) "
        "Visualization: Example visualization Challenge: Level A Challenge ID: 1 Wave ID: 10"
    )

    answer = answer_question(question, result)

    assert "same secret value" in answer
    assert "target points" not in answer.lower()
    assert "unrelated issues" in answer