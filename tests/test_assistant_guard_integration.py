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
