from __future__ import annotations

from campaign_assistant.ui.setup import build_setup_conflict_messages
from campaign_assistant.ui.setup import _focus_label


def test_build_setup_conflict_messages_reports_ttm_conflict():
	result = {
		"assistant_meta": {
			"selected_checks": ["ttm"],
			"capability_summary": {
				"capabilities": {
					"uses_ttm": False,
					"uses_progression": True,
					"uses_gatekeeping": None,
					"uses_maintenance_tasks": None,
				},
				"task_role_count": 0,
			},
		},
		"theory_grounding": {
			"ttm_structure_file_exists": False,
		},
	}

	messages = build_setup_conflict_messages(result)

	assert any("TTM checking was requested" in msg for msg in messages)
	assert any("task-role annotations" in msg for msg in messages)


def test_build_setup_conflict_messages_reports_missing_ttm_file():
	result = {
		"assistant_meta": {
			"selected_checks": [],
			"capability_summary": {
				"capabilities": {
					"uses_ttm": True,
					"uses_progression": True,
					"uses_gatekeeping": True,
					"uses_maintenance_tasks": True,
				},
				"task_role_count": 2,
			},
		},
		"theory_grounding": {
			"ttm_structure_file_exists": False,
		},
	}

	messages = build_setup_conflict_messages(result)

	assert any("no ttm structure file" in msg.lower() for msg in messages)


def test_focus_label_maps_known_targets():
	assert _focus_label("profile") == "Capability profile"
	assert _focus_label("task_roles") == "Task-role annotations"
	assert _focus_label("theory") == "Sidecars and evidence files"