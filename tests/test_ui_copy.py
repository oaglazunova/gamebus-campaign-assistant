from campaign_assistant.ui.copy import ASSISTANT_FALLBACK_TEXT, WORKFLOW_PAGE_COPY


def test_workflow_page_copy_contains_all_workflow_pages():
	assert set(WORKFLOW_PAGE_COPY.keys()) == {
		"Overview",
		"Setup",
		"Findings",
		"Fixes",
		"Assistant",
	}


def test_assistant_fallback_text_mentions_core_prompts():
	assert "Summarize the issues" in ASSISTANT_FALLBACK_TEXT
	assert "What should I fix first?" in ASSISTANT_FALLBACK_TEXT
	assert "What setup is missing?" in ASSISTANT_FALLBACK_TEXT