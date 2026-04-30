from campaign_assistant.ui.chat import build_assistant_guide_model


def test_assistant_guide_includes_basic_summary_prompt():
	result = {
		"summary": {
			"total_issues": 0,
		},
		"assistant_meta": {},
		"fix_proposals": {},
	}

	model = build_assistant_guide_model(result)

	assert "Summarize the issues" in model["suggestions"]


def test_assistant_guide_adds_setup_prompt_when_readiness_is_incomplete():
	result = {
		"summary": {
			"total_issues": 3,
		},
		"assistant_meta": {
			"workspace_readiness": {
				"gatekeeping_semantics_ready": False,
			}
		},
		"fix_proposals": {
			"proposal_count": 0,
		},
		"point_gatekeeping": {},
	}

	model = build_assistant_guide_model(result)

	assert "What should I fix first?" in model["suggestions"]
	assert "What setup is missing?" in model["suggestions"]


def test_assistant_guide_adds_fix_and_theory_prompts_when_available():
	result = {
		"summary": {
			"total_issues": 2,
		},
		"assistant_meta": {
			"workspace_readiness": {
				"gatekeeping_semantics_ready": True,
			}
		},
		"fix_proposals": {
			"proposal_count": 5,
		},
		"theory_grounding": {
			"confidence": "medium",
		},
		"point_gatekeeping": {
			"summary": {
				"challenge_findings": 1,
			}
		},
	}

	model = build_assistant_guide_model(result)

	assert "Show fix proposals" in model["suggestions"]
	assert "Show theory grounding" in model["suggestions"]
	assert "Show point/gatekeeping findings" in model["suggestions"]