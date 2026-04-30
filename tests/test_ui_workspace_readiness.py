from campaign_assistant.ui.workspace_readiness import build_workspace_readiness_model


def test_workspace_readiness_model_handles_missing_result():
	model = build_workspace_readiness_model(None)

	assert model["has_readiness"] is False
	assert model["status"] == "unknown"


def test_workspace_readiness_model_marks_not_applicable():
	model = build_workspace_readiness_model(
		{
			"assistant_meta": {
				"workspace_readiness": {
					"progression_applicable": False,
					"progression_basics_available": False,
					"gatekeeping_semantics_ready": False,
					"gatekeeping_annotations_present": False,
					"maintenance_annotations_present": False,
					"reasons": [
						"Progression-related validation is not applicable because this campaign is marked as not using progression."
					],
					"actions": [],
					"point_readiness_summary": {},
				}
			}
		}
	)

	assert model["has_readiness"] is True
	assert model["status"] == "not_applicable"


def test_workspace_readiness_model_marks_needs_annotations():
	model = build_workspace_readiness_model(
		{
			"assistant_meta": {
				"workspace_readiness": {
					"progression_applicable": True,
					"progression_basics_available": True,
					"gatekeeping_semantics_ready": False,
					"gatekeeping_annotations_present": False,
					"maintenance_annotations_present": False,
					"reasons": [
						"Gatekeeping semantics checks are disabled because explicit gatekeeping annotations are missing."
					],
					"actions": [
						{
							"action_id": "open_task_role_annotations",
							"label": "Annotate task roles",
							"focus": "task_roles",
						}
					],
					"point_readiness_summary": {
						"challenge_findings": 3,
						"missing_gatekeeping_annotation_count": 2,
						"missing_maintenance_annotation_count": 1,
					},
				}
			}
		}
	)

	assert model["has_readiness"] is True
	assert model["status"] == "needs_annotations"
	assert model["actions"][0]["focus"] == "task_roles"


def test_workspace_readiness_model_marks_ready():
	model = build_workspace_readiness_model(
		{
			"assistant_meta": {
				"workspace_readiness": {
					"progression_applicable": True,
					"progression_basics_available": True,
					"gatekeeping_semantics_ready": True,
					"gatekeeping_annotations_present": True,
					"maintenance_annotations_present": True,
					"reasons": [],
					"actions": [],
					"point_readiness_summary": {
						"challenge_findings": 3,
						"missing_gatekeeping_annotation_count": 0,
						"missing_maintenance_annotation_count": 0,
					},
				}
			}
		}
	)

	assert model["has_readiness"] is True
	assert model["status"] == "ready"