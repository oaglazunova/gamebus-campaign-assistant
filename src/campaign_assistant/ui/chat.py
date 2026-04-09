from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from campaign_assistant.checker import FRIENDLY_CHECK_NAMES, explain_ttm

HARD_MAX_ISSUES_TO_RENDER = 100
DEFAULT_MAX_ISSUES_TO_RENDER = 8
EXPANDED_PANEL_MAX_ISSUES = 12


def format_issue(issue: Dict[str, Any]) -> str:
	"""
	Format a single issue as a compact markdown bullet.
	"""
	title_parts = []
	if issue.get("visualization"):
		title_parts.append(f"**Visualization:** {issue['visualization']}")
	if issue.get("challenge"):
		title_parts.append(f"**Challenge:** {issue['challenge']}")
	if issue.get("wave_id") is not None:
		title_parts.append(f"**Wave ID:** {issue['wave_id']}")
	if issue.get("active_wave"):
		title_parts.append("**Active wave:** yes")

	details = " · ".join(title_parts)
	message = issue.get("message", "").strip()
	url = issue.get("url", "")

	lines = []
	if details:
		lines.append(f"- {details}")
	else:
		lines.append("- **Issue**")

	if message:
		lines.append(f"  - {message}")
	if url:
		lines.append(f"  - [Open in GameBus]({url})")

	return "\n".join(lines)


def issues_for_check(result: Dict[str, Any], check_name: str) -> List[Dict[str, Any]]:
	return result.get("issues_by_check", {}).get(check_name, [])


def _selected_single_check(result: Dict[str, Any]) -> bool:
	checks_run = result.get("checks_run", [])
	return len(checks_run) == 1


def _suggestion_tail(total_count: int, shown_count: int, single_check_selected: bool) -> str:
	if total_count <= shown_count:
		return ""

	remaining = total_count - shown_count
	lines = [f"\n\n…and **{remaining} more** issue(s) in this category."]

	if single_check_selected:
		lines.append(
			"\n\nTo see the full list, use **Generate Excel report** and download the Excel file."
		)
	else:
		lines.append(
			"\n\nTo see the full list, either:"
			"\n- enable **Generate Excel report** and download the Excel file, or"
			"\n- select only **one check** in the sidebar."
		)

	return "".join(lines)


def build_issue_markdown_list(
		issues: List[Dict[str, Any]],
		single_check_selected: bool = False,
		max_items: int | None = None,
) -> str:
	"""
	Build a readable markdown list for a group of issues.

	If only one check is selected, show all issues unless the list exceeds a hard cap.
	"""
	if not issues:
		return "No issues found."

	if max_items is None:
		if single_check_selected:
			max_items = HARD_MAX_ISSUES_TO_RENDER
		else:
			max_items = DEFAULT_MAX_ISSUES_TO_RENDER

	shown = issues[:max_items]
	blocks = [format_issue(issue) for issue in shown]
	tail = _suggestion_tail(len(issues), len(shown), single_check_selected)
	return "\n\n".join(blocks) + tail


def answer_question(user_question: str, result: Dict[str, Any]) -> str:
	q = user_question.strip().lower()

	if not result:
		return "No campaign has been analyzed yet."

	summary = result.get("summary", {})
	failed_checks = summary.get("failed_checks", [])
	total_issues = summary.get("total_issues", 0)
	issue_count_by_check = summary.get("issue_count_by_check", {})
	prioritized = result.get("prioritized_issues", [])
	single_check_selected = _selected_single_check(result)

	if any(x in q for x in ["summary", "summarize", "overview", "what is wrong", "what's wrong"]):
		lines = [f"I found **{total_issues}** issue(s)."]
		if failed_checks:
			lines.append(
				"Failed checks: " + ", ".join(f"`{name}`" for name in failed_checks) + "."
			)
		else:
			lines.append("No failed checks were detected.")
		return "\n\n".join(lines)

	if any(x in q for x in ["fix first", "priority", "prioritize", "most important"]):
		if not prioritized:
			return "There are no issues to prioritize."
		top = prioritized[:5]
		lines = ["These are the highest-priority issues I would fix first:"]
		lines.append(
			build_issue_markdown_list(
				top,
				single_check_selected=single_check_selected,
				max_items=5,
			)
		)
		return "\n\n".join(lines)

	if "failed checks" in q or "which checks failed" in q:
		if not failed_checks:
			return "No checks failed."
		return "Failed checks: " + ", ".join(f"`{name}`" for name in failed_checks) + "."

	if "what is ttm" in q or "explain ttm" in q or "ttm problem" in q:
		return explain_ttm()

	for check_name, friendly_name in FRIENDLY_CHECK_NAMES.items():
		if check_name.lower() in q or friendly_name.lower() in q:
			issues = issues_for_check(result, check_name)
			count = issue_count_by_check.get(check_name, len(issues))

			if not issues:
				return f"No issues found for **{friendly_name}**."

			lines = [
				f"I found **{count}** issue(s) for **{friendly_name}**.",
				build_issue_markdown_list(
					issues,
					single_check_selected=single_check_selected,
				),
			]

			if check_name == "ttm":
				lines.append("\n**TTM note:** " + explain_ttm())

			return "\n\n".join(lines)

	return (
		"I can help with things like:\n\n"
		"- `Summarize the issues`\n"
		"- `Which checks failed?`\n"
		"- `Show TTM issues`\n"
		"- `Show consistency issues`\n"
		"- `What should I fix first?`\n"
		"- `Explain TTM`\n"
	)


def render_issues_panel(result: Dict[str, Any]) -> None:
	issues_by_check = result.get("issues_by_check", {})
	summary = result.get("summary", {})
	issue_count_by_check = summary.get("issue_count_by_check", {})
	single_check_selected = _selected_single_check(result)

	st.subheader("Issues by check type")

	non_empty_checks = [
		check_name
		for check_name, issues in issues_by_check.items()
		if issues
	]

	if not non_empty_checks:
		st.success("No issues found.")
		return

	for check_name in non_empty_checks:
		friendly = FRIENDLY_CHECK_NAMES.get(check_name, check_name)
		count = issue_count_by_check.get(check_name, len(issues_by_check[check_name]))

		with st.expander(f"{friendly} ({count})", expanded=False):
			st.markdown(
				build_issue_markdown_list(
					issues_by_check[check_name],
					single_check_selected=single_check_selected,
					max_items=HARD_MAX_ISSUES_TO_RENDER if single_check_selected else EXPANDED_PANEL_MAX_ISSUES,
				)
			)