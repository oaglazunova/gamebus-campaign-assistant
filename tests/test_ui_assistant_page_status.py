from campaign_assistant.ui.chat import build_assistant_page_status_model


def test_assistant_page_status_marks_setup_gap():
	result = {
		"summary": {
			"total_issues": 4,
		},
		"fix_proposals": {
			"proposal_count": 2,
		},
		"assistant_meta": {
			"selected_checks": ["reachability", "targetpointsreachable"],
			"workspace_readiness": {
				"progression_applicable": True,
				"gatekeeping_semantics_ready": False,
			},
		},
	}

	model = build_assistant_page_status_model(result, message_count=3)

	assert model["status"] == "needs_setup"
	assert model["message_count"] == 3
	assert model["total_issues"] == 4
	assert model["proposal_count"] == 2


def test_assistant_page_status_marks_issues_found():
	result = {
		"summary": {
			"total_issues": 2,
		},
		"fix_proposals": {
			"proposal_count": 0,
		},
		"assistant_meta": {
			"selected_checks": ["secrets"],
			"workspace_readiness": {
				"progression_applicable": False,
				"gatekeeping_semantics_ready": False,
			},
		},
	}

	model = build_assistant_page_status_model(result, message_count=0)

	assert model["status"] == "issues_found"
	assert model["selected_checks"] == ["secrets"]


def test_assistant_page_status_marks_clean():
	result = {
		"summary": {
			"total_issues": 0,
		},
		"fix_proposals": {
			"proposal_count": 0,
		},
		"assistant_meta": {
			"selected_checks": ["secrets"],
			"workspace_readiness": {
				"progression_applicable": False,
				"gatekeeping_semantics_ready": False,
			},
		},
	}

	model = build_assistant_page_status_model(result, message_count=1)

	assert model["status"] == "clean"
	assert model["message_count"] == 1