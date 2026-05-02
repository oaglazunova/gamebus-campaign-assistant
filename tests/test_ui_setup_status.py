from campaign_assistant.ui.setup import build_setup_page_status_model


def test_setup_status_model_marks_annotation_gap():
	result = {
		"assistant_meta": {
			"capability_summary": {
				"capabilities": {
					"uses_progression": True,
					"uses_ttm": False,
				},
				"task_role_count": 0,
			},
			"workspace_readiness": {
				"progression_applicable": True,
				"gatekeeping_semantics_ready": False,
			},
		}
	}

	model = build_setup_page_status_model(result)

	assert model["status"] == "needs_annotations"
	assert model["task_role_count"] == 0
	assert model["uses_progression"] is True


def test_setup_status_model_marks_ready():
	result = {
		"assistant_meta": {
			"capability_summary": {
				"capabilities": {
					"uses_progression": True,
					"uses_ttm": True,
				},
				"task_role_count": 5,
			},
			"workspace_readiness": {
				"progression_applicable": True,
				"gatekeeping_semantics_ready": True,
			},
		}
	}

	model = build_setup_page_status_model(result)

	assert model["status"] == "ready"
	assert model["task_role_count"] == 5
	assert model["uses_ttm"] is True