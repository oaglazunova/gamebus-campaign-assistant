from campaign_assistant.ui.chat import (
	build_capability_status_model,
	build_point_status_model,
	build_theory_status_model,
)


def test_capability_status_model_extracts_core_flags():
	result = {
		"assistant_meta": {
			"capability_summary": {
				"capabilities": {
					"uses_progression": True,
					"uses_gatekeeping": False,
					"uses_ttm": True,
				},
				"active_modules": {
					"universal_structural": True,
				},
				"task_role_count": 3,
				"notes": ["note"],
				"missing": ["missing"],
				"sources": {"uses_ttm": "profile"},
			},
			"campaign_setup_hints": ["Add task roles"],
		}
	}

	model = build_capability_status_model(result)

	assert model["has_capability_summary"] is True
	assert model["uses_progression"] is True
	assert model["uses_gatekeeping"] is False
	assert model["uses_ttm"] is True
	assert model["task_role_count"] == 3
	assert model["setup_hints"] == ["Add task roles"]


def test_theory_status_model_marks_not_applicable():
	result = {
		"theory_grounding": {
			"confidence": "not_applicable",
			"uses_ttm": False,
			"applicability": {
				"status": "not_applicable",
				"reason": "TTM is not enabled.",
			},
		}
	}

	model = build_theory_status_model(result)

	assert model["has_theory"] is True
	assert model["status"] == "not_applicable"


def test_point_status_model_marks_partial():
	result = {
		"point_gatekeeping": {
			"applicability": {
				"status": "partial",
				"reason": "Annotations are incomplete.",
			},
			"summary": {
				"challenge_findings": 2,
			},
			"warnings": ["warning 1"],
			"suggestions": ["suggestion 1"],
		}
	}

	model = build_point_status_model(result)

	assert model["has_point_analysis"] is True
	assert model["status"] == "partial"
	assert model["summary"]["challenge_findings"] == 2
	assert model["warnings"] == ["warning 1"]