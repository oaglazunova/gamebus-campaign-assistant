from campaign_assistant.ui.chat import (
	answer_question,
	build_issue_markdown_list,
	format_issue,
	issues_for_check,
)
from campaign_assistant.ui.chat import _severity_explainer_markdown
from campaign_assistant.ui.chat import _proposal_ids_from_groups, _format_group_detail_markdown
from campaign_assistant.ui.chat import _format_member_detail_markdown
from campaign_assistant.ui.chat import _group_setup_actions

def sample_result(checks_run=None):
	return {
		"file_name": "campaign.xlsx",
		"checks_run": checks_run or ["ttm", "consistency", "reachability"],
		"summary": {
			"total_issues": 3,
			"failed_checks": ["ttm", "consistency"],
			"passed_checks": ["reachability"],
			"errored_checks": [],
			"issue_count_by_check": {
				"ttm": 2,
				"consistency": 1,
				"reachability": 0,
			},
		},
		"waves": [
			{"name": "Wave 1", "active_now": True},
			{"name": "Wave 2", "active_now": False},
		],
		"issues_by_check": {
			"ttm": [
				{
					"check": "ttm",
					"severity": "high",
					"active_wave": True,
					"visualization_id": 1,
					"visualization": "TTM Levels",
					"challenge_id": 101,
					"challenge": "Skilled",
					"wave_id": 1,
					"message": "Wrong TTM successor.",
					"url": "https://example.com/1",
				},
				{
					"check": "ttm",
					"severity": "high",
					"active_wave": False,
					"visualization_id": 1,
					"visualization": "TTM Levels",
					"challenge_id": 102,
					"challenge": "Expert",
					"wave_id": 2,
					"message": "Wrong relapse target.",
					"url": "https://example.com/2",
				},
			],
			"consistency": [
				{
					"check": "consistency",
					"severity": "high",
					"active_wave": True,
					"visualization_id": 2,
					"visualization": "Points",
					"challenge_id": 201,
					"challenge": "Gatekeeper",
					"wave_id": 1,
					"message": "Inconsistent successor.",
					"url": "https://example.com/3",
				}
			],
			"reachability": [],
		},
		"prioritized_issues": [
			{
				"check": "ttm",
				"severity": "high",
				"active_wave": True,
				"visualization_id": 1,
				"visualization": "TTM Levels",
				"challenge_id": 101,
				"challenge": "Skilled",
				"wave_id": 1,
				"message": "Wrong TTM successor.",
				"url": "https://example.com/1",
			},
			{
				"check": "consistency",
				"severity": "high",
				"active_wave": True,
				"visualization_id": 2,
				"visualization": "Points",
				"challenge_id": 201,
				"challenge": "Gatekeeper",
				"wave_id": 1,
				"message": "Inconsistent successor.",
				"url": "https://example.com/3",
			},
		],
		"point_gatekeeping": {
			"summary": {
				"challenge_findings": 2,
				"missing_targets": 1,
				"unreachable_targets": 0,
				"gatekeeper_warnings": 1,
				"maintenance_warnings": 1,
			},
			"findings": [
				{
					"challenge_name": "Skilled At Risk",
					"visualization_name": "TTM Levels",
					"target_points": 20,
					"theoretical_max_points": 18,
					"explicit_gatekeepers": [],
					"explicit_maintenance": [],
					"inferred_gatekeepers": ["Reflection task"],
					"warnings": [
						"Target points exceed the theoretical maximum.",
						"No explicit gatekeeping task is marked for this challenge.",
					],
					"suggestions": [
						"Lower the target or increase achievable points.",
						"Mark one or more gatekeeping tasks explicitly.",
					],
				}
			],
			"warnings": [
				"1 challenge(s) have no target points defined."
			],
			"suggestions": [
				"Prefer explicit gatekeeping annotations over inference whenever possible."
			],
		},
		"theory_grounding": {
			"confidence": "medium",
			"uses_ttm": True,
			"uses_bct_mapping": True,
			"uses_comb_mapping": True,
			"ttm_structure_file_exists": True,
			"task_role_counts": {"gatekeeping": 1, "maintenance": 2},
			"notes": [
				"Point/gatekeeping analysis raised 1 gatekeeping warning(s)."
			],
			"stage_notes": {
				"preparation": "This stage usually benefits from planning and goal-setting."
			},
		},
		"fix_proposals": {
			"enabled": True,
			"proposal_count": 2,
			"proposals": [
				{
					"proposal_id": "fix-1-unreachable-target",
					"category": "points",
					"challenge_name": "Skilled At Risk",
					"severity": "high",
					"action_type": "lower_target_points",
					"status": "proposed",
					"rationale": "The current target exceeds the theoretical maximum reachable points.",
					"suggested_change": {
						"current_target_points": 20,
						"suggested_target_points": 18,
					},
					"notes": "Conservative fix.",
				},
				{
					"proposal_id": "fix-1-gatekeeper-annotation",
					"category": "gatekeeping",
					"challenge_name": "Skilled At Risk",
					"severity": "medium",
					"action_type": "annotate_gatekeeper",
					"status": "proposed",
					"rationale": "No explicit gatekeeper is marked.",
					"suggested_change": {
						"candidate_gatekeepers": ["Reflection task"],
					},
					"notes": "Add explicit gatekeeper metadata.",
				},
			],
			"proposals_path": "/tmp/example_fix_proposals.json",
		},
		"assistant_meta": {
			"agent_trace": [
				{
					"step": 1,
					"agent_name": "privacy_guardian",
					"status": "success",
					"summary": "Privacy policy initialized.",
					"payload_keys": ["access_policy"],
					"warnings": [],
				},
				{
					"step": 2,
					"agent_name": "structural_change_agent",
					"status": "success",
					"summary": "Structural analysis found 3 issue(s).",
					"payload_keys": ["result_summary", "point_gatekeeping_summary"],
					"warnings": [],
				},
				{
					"step": 3,
					"agent_name": "theory_grounding_agent",
					"status": "success",
					"summary": "Theory grounding found no direct TTM conflict.",
					"payload_keys": ["confidence", "notes"],
					"warnings": [],
				},
				{
					"step": 4,
					"agent_name": "content_fixer_agent",
					"status": "success",
					"summary": "Content/fixer agent generated 2 repair proposals.",
					"payload_keys": ["proposal_count", "proposals"],
					"warnings": [],
				},
			]
		},
	}


def test_format_issue_includes_key_fields():
	issue = sample_result()["issues_by_check"]["ttm"][0]

	text = format_issue(issue)

	assert "TTM Levels" in text
	assert "Skilled" in text
	assert "Wrong TTM successor." in text
	assert "Open in GameBus" in text


def test_issues_for_check_returns_expected_group():
	result = sample_result()

	ttm_issues = issues_for_check(result, "ttm")
	reachability_issues = issues_for_check(result, "reachability")

	assert len(ttm_issues) == 2
	assert reachability_issues == []


def test_build_issue_markdown_list_truncates_and_adds_suggestion_for_multi_check():
	issues = sample_result()["issues_by_check"]["ttm"]

	text = build_issue_markdown_list(
		issues,
		single_check_selected=False,
		max_items=1,
	)

	assert "Wrong TTM successor." in text
	assert "1 more" in text
	assert "use the download button in the sidebar" in text
	assert "select only **one check** in the sidebar" in text


def test_build_issue_markdown_list_shows_all_when_single_check_selected():
	issues = sample_result(checks_run=["ttm"])["issues_by_check"]["ttm"]

	text = build_issue_markdown_list(
		issues,
		single_check_selected=True,
	)

	assert "Wrong TTM successor." in text
	assert "Wrong relapse target." in text
	assert "more issue(s)" not in text


def test_answer_question_summary():
	result = sample_result()

	text = answer_question("Summarize the issues", result)

	assert "3" in text
	assert "ttm" in text
	assert "consistency" in text
	assert "repair proposal" in text.lower() or "proposal" in text.lower()


def test_answer_question_failed_checks():
	result = sample_result()

	text = answer_question("Which checks failed?", result)

	assert "ttm" in text
	assert "consistency" in text


def test_answer_question_ttm_issues():
	result = sample_result()

	text = answer_question("Show TTM issues", result)

	assert "TTM structure" in text
	assert "Wrong TTM successor." in text


def test_answer_question_fix_first():
	result = sample_result()

	text = answer_question("What should I fix first?", result)

	assert "highest-priority" in text.lower()
	assert "Wrong TTM successor." in text


def test_answer_question_explain_ttm():
	result = sample_result()

	text = answer_question("Explain TTM", result)

	assert "Newbie" in text or "newbie" in text
	assert "Grandmaster" in text or "grandmaster" in text


def test_answer_question_point_gatekeeping():
	result = sample_result()

	text = answer_question("Show point and gatekeeping findings", result)

	assert "point/gatekeeping analysis" in text.lower()
	assert "challenge findings" in text.lower()
	assert "gatekeeper warnings" in text.lower()


def test_answer_question_theory_grounding():
	result = sample_result()

	text = answer_question("Show theory grounding", result)

	assert "confidence" in text.lower()
	assert "uses ttm" in text.lower()
	assert "uses bct mapping" in text.lower()


def test_answer_question_fix_proposals():
	result = sample_result()

	text = answer_question("Show fix proposals", result)

	assert "fix-1-unreachable-target" in text
	assert "lower_target_points" in text
	assert "annotate_gatekeeper" in text


def test_answer_question_agent_trace():
	result = sample_result()

	text = answer_question("What did the agents do?", result)

	assert "privacy_guardian" in text
	assert "structural_change_agent" in text
	assert "theory_grounding_agent" in text
	assert "content_fixer_agent" in text


def test_severity_explainer_mentions_all_levels():
	text = _severity_explainer_markdown().lower()
	assert "high" in text
	assert "medium" in text
	assert "low" in text
	assert "heuristic" in text



def test_proposal_ids_from_groups_flattens_member_ids():
	groups = [
		{"member_proposal_ids": ["p1", "p2"]},
		{"member_proposal_ids": ["p3"]},
	]
	assert _proposal_ids_from_groups(groups) == ["p1", "p2", "p3"]


def test_format_group_detail_markdown_contains_group_info():
	group = {
		"issue_label": "Missing explicit gatekeeper annotation",
		"summary": "Missing explicit gatekeeper annotation across 2 challenges (2 proposal(s))",
		"category": "gatekeeping",
		"severity": "medium",
		"status": "proposed",
		"priority": "recommended",
		"priority_reason": "Progression appears relevant, but task-role metadata is missing.",
		"context_tags": ["progression", "gatekeeping", "setup-needed"],
		"member_count": 2,
		"member_proposal_ids": ["p1", "p2"],
		"challenge_names": ["Challenge A", "Challenge B"],
		"rationales": ["Need explicit gatekeeper."],
		"notes": ["Annotate in task_roles.csv"],
	}

	text = _format_group_detail_markdown(group)
	assert "Missing explicit gatekeeper annotation" in text
	assert "Challenge A" in text
	assert "recommended" in text.lower()
	assert "task-role metadata is missing" in text
	assert "p1" in text
	assert "Need explicit gatekeeper." in text

def test_format_member_detail_markdown_contains_member_info():
	proposal = {
		"proposal_id": "p-123",
		"challenge_name": "Challenge A",
		"category": "gatekeeping",
		"action_type": "annotate_gatekeeper",
		"severity": "medium",
		"status": "proposed",
		"rationale": "Need explicit gatekeeper.",
		"suggested_change": {
			"candidate_gatekeepers": ["Task X"],
		},
		"notes": "Annotate in task_roles.csv",
	}

	text = _format_member_detail_markdown(proposal)
	assert "p-123" in text
	assert "Challenge A" in text
	assert "annotate_gatekeeper" in text
	assert "Task X" in text
	assert "Need explicit gatekeeper." in text

def test_group_setup_actions_for_gatekeeping_group():
	group = {
		"issue_family": "missing_explicit_gatekeeper",
		"context_tags": ["progression", "gatekeeping", "setup-needed"],
	}

	actions = _group_setup_actions(group)

	assert ("Open task-role editor", "task_roles") in actions


def test_group_setup_actions_for_ttm_group():
	group = {
		"issue_family": "ttm_manual_review",
		"context_tags": ["ttm"],
	}

	actions = _group_setup_actions(group)

	assert ("Open theory file setup", "theory") in actions