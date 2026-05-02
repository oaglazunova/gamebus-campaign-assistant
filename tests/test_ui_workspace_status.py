from campaign_assistant.ui.chat import build_workspace_status_model


def test_workspace_status_model_marks_needs_setup_when_readiness_is_incomplete():
	result = {
		"assistant_meta": {
			"capability_summary": {
				"capabilities": {
					"uses_progression": True,
					"uses_gatekeeping": True,
					"uses_ttm": False,
				},
				"active_modules": {
					"universal_structural": True,
				},
				"task_role_count": 0,
				"notes": [],
				"missing": [],
				"sources": {},
			},
			"campaign_setup_hints": ["Add task-role annotations"],
			"workspace_readiness": {
				"progression_applicable": True,
				"progression_basics_available": True,
				"gatekeeping_semantics_ready": False,
				"gatekeeping_annotations_present": False,
				"maintenance_annotations_present": False,
				"reasons": ["Gatekeeping semantics checks are disabled because explicit gatekeeping annotations are missing."],
				"actions": [],
				"point_readiness_summary": {},
			},
		}
	}

	model = build_workspace_status_model(result)

	assert model["has_workspace_status"] is True
	assert model["status"] == "needs_setup"


def test_workspace_status_model_marks_ready_when_readiness_is_ready():
	result = {
		"assistant_meta": {
			"capability_summary": {
				"capabilities": {
					"uses_progression": True,
					"uses_gatekeeping": True,
					"uses_ttm": False,
				},
				"active_modules": {
					"universal_structural": True,
				},
				"task_role_count": 3,
				"notes": [],
				"missing": [],
				"sources": {},
			},
			"campaign_setup_hints": [],
			"workspace_readiness": {
				"progression_applicable": True,
				"progression_basics_available": True,
				"gatekeeping_semantics_ready": True,
				"gatekeeping_annotations_present": True,
				"maintenance_annotations_present": True,
				"reasons": [],
				"actions": [],
				"point_readiness_summary": {},
			},
		}
	}

	model = build_workspace_status_model(result)

	assert model["has_workspace_status"] is True
	assert model["status"] == "ready"