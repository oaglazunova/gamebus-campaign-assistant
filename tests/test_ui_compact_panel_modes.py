from inspect import signature

from campaign_assistant.ui.chat import (
	render_issues_panel,
	render_point_gatekeeping_panel,
	render_theory_panel,
)


def test_issue_and_interpretation_panels_support_compact_mode():
	assert signature(render_issues_panel).parameters["compact"].default is False
	assert signature(render_theory_panel).parameters["compact"].default is False
	assert signature(render_point_gatekeeping_panel).parameters["compact"].default is False