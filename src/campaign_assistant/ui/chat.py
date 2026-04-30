from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from typing import Any, Dict, List

from campaign_assistant.checker import FRIENDLY_CHECK_NAMES, explain_ttm
from campaign_assistant.approval import ApprovalHandler
from campaign_assistant.patches import (
	PatchManifestGenerator,
	PatchedExcelDraftGenerator,
	TaskRolesDraftGenerator,
)
from campaign_assistant.proposals import (
	build_proposal_groups,
	annotate_proposal_groups_with_context,
	matches_group_focus,
)
from campaign_assistant.ui.overview import render_analysis_overview


HARD_MAX_ISSUES_TO_RENDER = 100
DEFAULT_MAX_ISSUES_TO_RENDER = 8
EXPANDED_PANEL_MAX_ISSUES = 12
POINT_FINDINGS_MAX = 8
TRACE_EVENTS_MAX = 12
FIX_PROPOSALS_MAX = 10


def format_issue(issue: Dict[str, Any]) -> str:
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
			"You selected only **one check**, so you can also use the download button in the sidebar to inspect the full Excel report."
		)
	else:
		lines.append(
			"For a full list, use the download button in the sidebar or select only **one check** in the sidebar."
		)

	return " ".join(lines)


def build_issue_markdown_list(
	issues: List[Dict[str, Any]],
	*,
	single_check_selected: bool,
	max_items: int | None = None,
) -> str:
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



def _top_priority_issues_markdown(result: Dict[str, Any], max_items: int = 5) -> str:
	prioritized = result.get("prioritized_issues", []) or []
	if not prioritized:
		return "No prioritized issues are available."

	top = prioritized[:max_items]
	single_check_selected = _selected_single_check(result)

	text = build_issue_markdown_list(
		top,
		single_check_selected=single_check_selected,
		max_items=max_items,
	)

	if len(prioritized) > len(top):
		text += f"\n\n…and **{len(prioritized) - len(top)} more** prioritized issue(s)."

	return text


def _check_summary_rows(result: Dict[str, Any]) -> List[Dict[str, Any]]:
	issues_by_check = result.get("issues_by_check", {}) or {}
	summary = result.get("summary", {}) or {}
	issue_count_by_check = summary.get("issue_count_by_check", {}) or {}
	failed_checks = set(summary.get("failed_checks", []) or [])
	errored_checks = set(summary.get("errored_checks", []) or [])

	rows: List[Dict[str, Any]] = []

	for check_name, friendly_name in FRIENDLY_CHECK_NAMES.items():
		issues = issues_by_check.get(check_name, []) or []
		count = int(issue_count_by_check.get(check_name, len(issues)) or 0)

		if check_name in errored_checks:
			status = "Errored"
		elif check_name in failed_checks:
			status = "Failed"
		elif count > 0:
			status = "Failed"
		else:
			status = "Passed"

		active_count = sum(1 for issue in issues if issue.get("active_wave"))
		high_count = sum(1 for issue in issues if issue.get("severity") == "high")
		medium_count = sum(1 for issue in issues if issue.get("severity") == "medium")
		low_count = sum(1 for issue in issues if issue.get("severity") == "low")

		if status == "Passed" and count == 0:
			continue

		rows.append(
			{
				"check": check_name,
				"label": friendly_name,
				"status": status,
				"issues": count,
				"active_wave": active_count,
				"high": high_count,
				"medium": medium_count,
				"low": low_count,
			}
		)

	return rows


def render_findings_overview_panel(result: Dict[str, Any]) -> None:
	summary = result.get("summary", {}) or {}
	total_issues = int(summary.get("total_issues", 0) or 0)
	failed_checks = list(summary.get("failed_checks", []) or [])
	errored_checks = list(summary.get("errored_checks", []) or [])

	st.subheader("Findings overview")

	c1, c2, c3 = st.columns(3)
	c1.metric("Total issues", total_issues)
	c2.metric("Failed checks", len(failed_checks))
	c3.metric("Errored checks", len(errored_checks))

	if total_issues == 0 and not errored_checks:
		st.success("No structural issues were found in the currently selected checks.")
		return

	if errored_checks:
		st.warning(
			"Some checks errored. Review those first, because they may hide additional problems."
		)

	st.markdown("**Top priorities**")
	st.markdown(_top_priority_issues_markdown(result, max_items=5))

	rows = _check_summary_rows(result)
	if rows:
		st.markdown("**Checks with findings**")
		df = pd.DataFrame(rows)
		st.dataframe(df, use_container_width=True, hide_index=True)



def _format_point_finding(finding: Dict[str, Any]) -> str:
	lines = []
	challenge = finding.get("challenge_name") or "Unknown challenge"
	vis = finding.get("visualization_name") or ""
	target = finding.get("target_points")
	max_points = finding.get("theoretical_max_points")

	header = f"- **Challenge:** {challenge}"
	if vis:
		header += f" · **Visualization:** {vis}"
	lines.append(header)

	if target is not None or max_points is not None:
		lines.append(
			f"  - **Target points:** {target if target is not None else 'n/a'} · "
			f"**Theoretical max:** {max_points if max_points is not None else 'n/a'}"
		)

	explicit_gatekeepers = finding.get("explicit_gatekeepers") or []
	inferred_gatekeepers = finding.get("inferred_gatekeepers") or []
	explicit_maintenance = finding.get("explicit_maintenance") or []

	if explicit_gatekeepers:
		lines.append(f"  - **Explicit gatekeepers:** {', '.join(explicit_gatekeepers)}")
	elif inferred_gatekeepers:
		lines.append(f"  - **Inferred gatekeepers:** {', '.join(inferred_gatekeepers)}")

	if explicit_maintenance:
		lines.append(f"  - **Maintenance tasks:** {', '.join(explicit_maintenance)}")

	for warning in finding.get("warnings", []):
		lines.append(f"  - ⚠️ {warning}")

	for suggestion in finding.get("suggestions", []):
		lines.append(f"  - 💡 {suggestion}")

	return "\n".join(lines)


def _build_point_findings_markdown(result: Dict[str, Any], max_items: int = POINT_FINDINGS_MAX) -> str:
	pg = result.get("point_gatekeeping", {})
	findings = pg.get("findings", [])

	if not findings:
		return "No point/gatekeeping findings were produced."

	shown = findings[:max_items]
	text = "\n\n".join(_format_point_finding(f) for f in shown)

	if len(findings) > len(shown):
		text += f"\n\n…and **{len(findings) - len(shown)} more** challenge-level finding(s)."

	return text


def _build_theory_summary_markdown(result: Dict[str, Any]) -> str:
	theory = result.get("theory_grounding", {})
	if not theory:
		return "No theory-grounding output is available for this analysis."

	lines = []
	lines.append(f"- **Confidence:** {theory.get('confidence', 'unknown')}")
	lines.append(f"- **Uses TTM:** {theory.get('uses_ttm', False)}")
	if theory.get("uses_bct_mapping", False):
		lines.append(f"- **Uses BCT mapping:** {theory.get('uses_bct_mapping', False)}")
	if theory.get("uses_comb_mapping", False):
		lines.append(f"- **Uses COM-B mapping:** {theory.get('uses_comb_mapping', False)}")
	lines.append(f"- **TTM structure file available:** {theory.get('ttm_structure_file_exists', False)}")

	role_counts = theory.get("task_role_counts") or {}
	if role_counts:
		lines.append(f"- **Task role counts:** {role_counts}")

	for note in theory.get("notes", []):
		lines.append(f"- {note}")

	return "\n".join(lines)


def _build_agent_trace_markdown(result: Dict[str, Any], max_items: int = TRACE_EVENTS_MAX) -> str:
	trace = result.get("assistant_meta", {}).get("agent_trace", [])
	if not trace:
		return "No agent trace is available."

	lines = []
	for event in trace[:max_items]:
		lines.append(
			f"- **Step {event.get('step')}** · `{event.get('agent_name')}` · "
			f"**{event.get('status')}**\n"
			f"  - {event.get('summary')}"
		)
		payload_keys = event.get("payload_keys") or []
		if payload_keys:
			lines.append(f"  - payload keys: {', '.join(payload_keys)}")
		for warning in event.get("warnings", []):
			lines.append(f"  - warning: {warning}")

	if len(trace) > max_items:
		lines.append(f"\n…and **{len(trace) - max_items} more** trace event(s).")

	return "\n".join(lines)


def _format_fix_proposal(proposal: Dict[str, Any]) -> str:
	lines = []
	proposal_id = proposal.get("proposal_id", "unknown")
	category = proposal.get("category", "unknown")
	challenge = proposal.get("challenge_name") or "General"
	severity = proposal.get("severity", "unknown")
	action_type = proposal.get("action_type", "unknown")
	status = proposal.get("status", "proposed")

	lines.append(
		f"- **{proposal_id}** · **Category:** {category} · **Challenge:** {challenge} · "
		f"**Severity:** {severity} · **Action:** {action_type} · **Status:** {status}"
	)

	rationale = proposal.get("rationale")
	if rationale:
		lines.append(f"  - **Why:** {rationale}")

	change = proposal.get("suggested_change") or {}
	if change:
		lines.append(f"  - **Suggested change:** `{change}`")

	approval_meta = proposal.get("approval_meta") or {}
	if approval_meta:
		lines.append(
			f"  - **Reviewed by:** {approval_meta.get('reviewer', 'human')} at {approval_meta.get('updated_at', 'unknown')}"
		)
		reason = approval_meta.get("reason")
		if reason:
			lines.append(f"  - **Reason:** {reason}")

	notes = proposal.get("notes")
	if notes:
		lines.append(f"  - **Notes:** {notes}")

	return "\n".join(lines)


def _build_fix_proposals_markdown(result: Dict[str, Any], max_items: int = FIX_PROPOSALS_MAX) -> str:
	fixer = result.get("fix_proposals", {})
	proposals = fixer.get("proposals", [])

	if not proposals:
		return "No fix proposals are available."

	shown = proposals[:max_items]
	text = "\n\n".join(_format_fix_proposal(p) for p in shown)

	if len(proposals) > len(shown):
		text += f"\n\n…and **{len(proposals) - len(shown)} more** proposal(s)."

	return text


def _build_patch_manifest_markdown(result: Dict[str, Any]) -> str:
	manifest = result.get("patch_manifest", {})
	if not manifest:
		return "No patch manifest has been generated yet."

	lines = []
	lines.append(f"- **Manifest version:** {manifest.get('manifest_version', 'unknown')}")
	lines.append(f"- **Accepted proposals:** {manifest.get('accepted_proposal_count', 0)}")
	lines.append(f"- **Operations:** {manifest.get('operation_count', 0)}")

	for op in manifest.get("operations", [])[:10]:
		lines.append(
			f"- **{op.get('op')}** · **Challenge:** {op.get('challenge_name') or 'General'} · "
			f"`{op.get('params', {})}`"
		)

	skipped = manifest.get("skipped_proposals", [])
	if skipped:
		lines.append(f"- **Skipped proposals:** {len(skipped)}")

	return "\n".join(lines)


def _build_patched_draft_markdown(result: Dict[str, Any]) -> str:
	draft = result.get("patched_excel_draft", {})
	if not draft:
		return "No patched Excel draft has been generated yet."

	lines = []
	lines.append(f"- **Draft path:** {draft.get('draft_path', 'unknown')}")
	lines.append(f"- **Applied operations:** {draft.get('applied_count', 0)}")
	lines.append(f"- **Unresolved operations:** {draft.get('unresolved_count', 0)}")

	for item in draft.get("applied", [])[:10]:
		lines.append(
			f"- **Applied:** {item.get('op')} · **Challenge:** {item.get('challenge_name')} · "
			f"`{item.get('previous_value')} -> {item.get('new_value')}`"
		)

	if draft.get("unresolved"):
		lines.append(f"- **Unresolved items listed in notes sheet:** {len(draft.get('unresolved', []))}")

	return "\n".join(lines)


def _build_task_roles_draft_markdown(result: Dict[str, Any]) -> str:
	draft = result.get("task_roles_draft", {})
	if not draft:
		return "No task-role sidecar draft has been generated yet."

	lines = []
	lines.append(f"- **Draft path:** {draft.get('draft_path', 'unknown')}")
	lines.append(f"- **Applied role annotations:** {draft.get('applied_count', 0)}")
	lines.append(f"- **Unresolved annotations:** {draft.get('unresolved_count', 0)}")

	for item in draft.get("applied", [])[:10]:
		lines.append(
			f"- **Applied:** role `{item.get('role')}` to task **{item.get('task_name')}**"
			+ (f" in challenge **{item.get('challenge_name')}**" if item.get("challenge_name") else "")
		)

	if draft.get("unresolved"):
		lines.append(f"- **Unresolved items:** {len(draft.get('unresolved', []))}")

	return "\n".join(lines)



def build_assistant_guide_model(result: Dict[str, Any]) -> Dict[str, Any]:
	summary = result.get("summary", {}) or {}
	assistant_meta = result.get("assistant_meta", {}) or {}
	readiness = assistant_meta.get("workspace_readiness", {}) or {}
	fix_proposals = result.get("fix_proposals", {}) or {}

	total_issues = int(summary.get("total_issues", 0) or 0)
	proposal_count = int(fix_proposals.get("proposal_count", 0) or 0)

	suggestions: List[str] = []

	suggestions.append("Summarize the issues")

	if total_issues > 0:
		suggestions.append("What should I fix first?")

	if readiness and not readiness.get("gatekeeping_semantics_ready", True):
		suggestions.append("What setup is missing?")

	if proposal_count > 0:
		suggestions.append("Show fix proposals")

	if result.get("theory_grounding"):
		suggestions.append("Show theory grounding")

	if result.get("point_gatekeeping"):
		suggestions.append("Show point/gatekeeping findings")

	return {
		"total_issues": total_issues,
		"proposal_count": proposal_count,
		"suggestions": suggestions,
	}


def render_assistant_guide_panel(result: Dict[str, Any]) -> None:
	if not result:
		return

	model = build_assistant_guide_model(result)
	suggestions = model["suggestions"]

	if not suggestions:
		return

	st.subheader("Assistant")
	st.caption("Suggested questions based on the current analysis")

	cols = st.columns(min(len(suggestions), 3))
	for idx, suggestion in enumerate(suggestions):
		with cols[idx % len(cols)]:
			if st.button(suggestion, key=f"assistant-suggestion-{idx}"):
				st.session_state["assistant_prefill_prompt"] = suggestion



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

		pg_summary = result.get("point_gatekeeping", {}).get("summary", {})
		if pg_summary.get("challenge_findings", 0):
			lines.append(
				f"Point/gatekeeping analysis highlighted **{pg_summary.get('challenge_findings', 0)}** challenge-level finding(s)."
			)

		theory = result.get("theory_grounding", {})
		if theory:
			lines.append(
				f"Theory grounding confidence is **{theory.get('confidence', 'unknown')}**."
			)

		fixer = result.get("fix_proposals", {})
		if fixer.get("proposal_count", 0):
			lines.append(
				f"Content/fixer agent generated **{fixer.get('proposal_count', 0)}** repair proposal(s)."
			)

		return "\n\n".join(lines)

	if any(x in q for x in ["fix first", "priority", "prioritize", "most important"]):
		if not prioritized:
			pg_findings = result.get("point_gatekeeping", {}).get("findings", [])
			if pg_findings:
				return (
					"No global prioritized issue list is available yet, but point/gatekeeping analysis found the following high-attention challenges:\n\n"
					+ _build_point_findings_markdown(result, max_items=5)
				)
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

	capability_summary = result.get("assistant_meta", {}).get("capability_summary", {})
	active_modules = capability_summary.get("active_modules", {})

	if any(x in q for x in ["point", "gatekeeping", "gatekeeper", "maintenance"]):
		if active_modules.get("point_gatekeeping_checks") is False:
			return "Point/gatekeeping reasoning is not active for this campaign."

		pg = result.get("point_gatekeeping", {})
		if not pg:
			return "No point/gatekeeping analysis is available for this campaign."

		pg_summary = pg.get("summary", {})
		lines = [
			"Here is the current point/gatekeeping analysis:",
			f"- challenge findings: **{pg_summary.get('challenge_findings', 0)}**",
			f"- missing targets: **{pg_summary.get('missing_targets', 0)}**",
			f"- unreachable targets: **{pg_summary.get('unreachable_targets', 0)}**",
			f"- gatekeeper warnings: **{pg_summary.get('gatekeeper_warnings', 0)}**",
			f"- maintenance warnings: **{pg_summary.get('maintenance_warnings', 0)}**",
		]
		return "\n".join(lines)

	if any(x in q for x in ["theory", "grounding", "bct", "com-b", "comb"]):
		return _build_theory_summary_markdown(result)

	if any(x in q for x in ["proposal", "fix proposal", "suggested fixes", "repair proposal", "fix suggestions"]):
		return _build_fix_proposals_markdown(result)

	if any(x in q for x in ["agents", "trace", "what did the agents do", "agent reasoning"]):
		return _build_agent_trace_markdown(result)

	if any(x in q for x in ["patch manifest", "manifest", "accepted changes", "generated manifest"]):
		return _build_patch_manifest_markdown(result)

	if any(x in q for x in ["patched excel", "patched draft", "draft workbook", "patched workbook"]):
		return _build_patched_draft_markdown(result)

	if any(x in q for x in ["task role draft", "role draft", "gatekeeper draft", "task_roles draft"]):
		return _build_task_roles_draft_markdown(result)

	if any(x in q for x in ["setup", "metadata", "missing metadata", "campaign setup hints", "what setup is missing"]):
		hints = result.get("assistant_meta", {}).get("campaign_setup_hints", []) or []
		readiness = result.get("assistant_meta", {}).get("workspace_readiness", {}) or []

		lines = []

		if hints:
			lines.append("Here are the current recommended campaign setup steps:")
			lines.extend([f"- {h}" for h in hints])

		if isinstance(readiness, dict):
			reasons = readiness.get("reasons", []) or []
			actions = readiness.get("actions", []) or []

			if reasons:
				if lines:
					lines.append("")
				lines.append("Workspace readiness notes:")
				lines.extend([f"- {r}" for r in reasons])

			if actions:
				if lines:
					lines.append("")
				lines.append("Suggested next actions:")
				lines.extend([f"- {a.get('label', 'Open related setup')}" for a in actions])

		if not lines:
			return "There are currently no specific campaign setup hints."

		return "\n".join(lines)

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
		"I can help you with the current workflow. Try one of these:\n\n"
		"- `Summarize the issues`\n"
		"- `What should I fix first?`\n"
		"- `Which checks failed?`\n"
		"- `What setup is missing?`\n"
		"- `Show point/gatekeeping findings`\n"
		"- `Show theory grounding`\n"
		"- `Show fix proposals`\n"
		"- `What did the agents do?`\n"
	)


def render_issues_panel(result: Dict[str, Any]) -> None:
	issues_by_check = result.get("issues_by_check", {})
	summary = result.get("summary", {})
	issue_count_by_check = summary.get("issue_count_by_check", {})
	single_check_selected = _selected_single_check(result)

	st.subheader("Detailed issues")

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



def build_capability_status_model(result: Dict[str, Any]) -> Dict[str, Any]:
	capability_summary = result.get("assistant_meta", {}).get("capability_summary", {}) or {}
	capabilities = capability_summary.get("capabilities", {}) or {}
	active_modules = capability_summary.get("active_modules", {}) or {}
	task_role_count = int(capability_summary.get("task_role_count", 0) or 0)
	setup_hints = result.get("assistant_meta", {}).get("campaign_setup_hints", []) or []

	return {
		"has_capability_summary": bool(capability_summary),
		"uses_progression": capabilities.get("uses_progression"),
		"uses_gatekeeping": capabilities.get("uses_gatekeeping"),
		"uses_ttm": capabilities.get("uses_ttm"),
		"task_role_count": task_role_count,
		"active_modules": active_modules,
		"setup_hints": setup_hints,
		"notes": capability_summary.get("notes", []) or [],
		"missing": capability_summary.get("missing", []) or [],
		"sources": capability_summary.get("sources", {}) or {},
		"capabilities": capabilities,
	}


def build_theory_status_model(result: Dict[str, Any]) -> Dict[str, Any]:
	theory = result.get("theory_grounding", {}) or {}
	if not theory:
		return {
			"has_theory": False,
			"status": "empty",
			"confidence": "unknown",
			"uses_ttm": False,
			"summary_message": "No theory-grounding output is available.",
			"details": {},
		}

	applicability = theory.get("applicability", {}) or {}
	status = applicability.get("status")
	reason = applicability.get("reason", "")

	if status == "not_applicable":
		summary_message = f"Theory grounding is not active for this campaign. {reason}".strip()
		ui_status = "not_applicable"
	elif status == "uncertain":
		summary_message = f"Theory grounding may be incomplete. {reason}".strip()
		ui_status = "uncertain"
	elif theory.get("confidence") == "not_applicable":
		summary_message = "Theory grounding is not active for this campaign."
		ui_status = "not_applicable"
	else:
		confidence = theory.get("confidence", "unknown")
		summary_message = f"Theory grounding is active with **{confidence}** confidence."
		ui_status = "active"

	return {
		"has_theory": True,
		"status": ui_status,
		"confidence": theory.get("confidence", "unknown"),
		"uses_ttm": bool(theory.get("uses_ttm", False)),
		"summary_message": summary_message,
		"details": theory,
	}


def build_point_status_model(result: Dict[str, Any]) -> Dict[str, Any]:
	pg = result.get("point_gatekeeping", {}) or {}
	if not pg:
		return {
			"has_point_analysis": False,
			"status": "empty",
			"summary_message": "No point/gatekeeping analysis is available.",
			"summary": {},
			"warnings": [],
			"suggestions": [],
		}

	applicability = pg.get("applicability", {}) or {}
	status = applicability.get("status")
	reason = applicability.get("reason", "")
	pg_summary = pg.get("summary", {}) or {}

	if status == "not_applicable":
		summary_message = f"Point/gatekeeping reasoning is not active for this campaign. {reason}".strip()
		ui_status = "not_applicable"
	elif status == "uncertain":
		summary_message = f"Point/gatekeeping results are only partially interpretable. {reason}".strip()
		ui_status = "uncertain"
	elif status == "partial":
		summary_message = f"Point/gatekeeping reasoning is active but incomplete. {reason}".strip()
		ui_status = "partial"
	else:
		summary_message = (
			f"Point/gatekeeping reasoning produced **{pg_summary.get('challenge_findings', 0)}** "
			f"challenge-level finding(s)."
		)
		ui_status = "active"

	return {
		"has_point_analysis": True,
		"status": ui_status,
		"summary_message": summary_message,
		"summary": pg_summary,
		"warnings": pg.get("warnings", []) or [],
		"suggestions": pg.get("suggestions", []) or [],
		"details": pg,
	}


def render_capability_panel(result: Dict[str, Any]) -> None:
	model = build_capability_status_model(result)
	if not model["has_capability_summary"]:
		return

	st.subheader("Campaign capability summary")

	uses_progression = model["uses_progression"]
	uses_gatekeeping = model["uses_gatekeeping"]
	uses_ttm = model["uses_ttm"]
	task_role_count = model["task_role_count"]

	if uses_progression is False:
		st.info("This campaign is currently interpreted as not using progression-specific logic.")
	elif uses_progression is True and task_role_count == 0:
		st.warning("This campaign appears to use progression, but no task-role annotations are currently available.")
	else:
		st.info("Capability resolution completed. The workspace profile is available below.")

	c1, c2, c3, c4 = st.columns(4)
	c1.metric("Task-role annotations", task_role_count)
	c2.metric("Progression", str(uses_progression))
	c3.metric("Gatekeeping", str(uses_gatekeeping))
	c4.metric("TTM", str(uses_ttm))

	setup_hints = model["setup_hints"]
	if setup_hints:
		with st.expander("Recommended setup steps", expanded=False):
			for hint in setup_hints:
				st.markdown(f"- {hint}")

	with st.expander("Resolved capabilities", expanded=False):
		capabilities = model["capabilities"]
		sources = model["sources"]
		for key, value in capabilities.items():
			source = sources.get(key, "unknown")
			st.markdown(f"- **{key}**: `{value}` _(source: {source})_")

	with st.expander("Active reasoning modules", expanded=False):
		for key, value in model["active_modules"].items():
			st.markdown(f"- **{key}**: `{value}`")

	if model["notes"]:
		with st.expander("Metadata notes", expanded=False):
			for note in model["notes"]:
				st.markdown(f"- {note}")

	if model["missing"]:
		with st.expander("Missing / uncertain metadata", expanded=False):
			for item in model["missing"]:
				st.markdown(f"- {item}")


def render_theory_panel(result: Dict[str, Any]) -> None:
	model = build_theory_status_model(result)
	if not model["has_theory"]:
		return

	st.subheader("Theory grounding")

	if model["status"] == "not_applicable":
		st.info(model["summary_message"])
	elif model["status"] == "uncertain":
		st.warning(model["summary_message"])
	else:
		st.info(model["summary_message"])

	theory = model["details"]

	c1, c2, c3 = st.columns(3)
	c1.metric("Confidence", str(model["confidence"]))
	c2.metric("Uses TTM", str(model["uses_ttm"]))
	c3.metric("TTM structure file", str(theory.get("ttm_structure_file_exists", False)))

	with st.expander("Theory details", expanded=False):
		st.markdown(_build_theory_summary_markdown(result))

	stage_notes = theory.get("stage_notes") or {}
	if stage_notes:
		with st.expander("TTM stage notes", expanded=False):
			for stage, note in stage_notes.items():
				st.markdown(f"- **{stage}**: {note}")


def render_point_gatekeeping_panel(result: Dict[str, Any]) -> None:
	model = build_point_status_model(result)
	if not model["has_point_analysis"]:
		return

	st.subheader("Point & gatekeeping findings")

	if model["status"] == "not_applicable":
		st.info(model["summary_message"])
		return
	elif model["status"] in {"uncertain", "partial"}:
		st.warning(model["summary_message"])
	else:
		st.info(model["summary_message"])

	pg_summary = model["summary"]
	c1, c2, c3, c4, c5 = st.columns(5)
	c1.metric("Findings", pg_summary.get("challenge_findings", 0))
	c2.metric("Missing targets", pg_summary.get("missing_targets", 0))
	c3.metric("Unreachable targets", pg_summary.get("unreachable_targets", 0))
	c4.metric("Gatekeeper warnings", pg_summary.get("gatekeeper_warnings", 0))
	c5.metric("Maintenance warnings", pg_summary.get("maintenance_warnings", 0))

	if model["warnings"]:
		with st.expander("Warnings", expanded=False):
			for warning in model["warnings"]:
				st.warning(warning)

	if model["suggestions"]:
		with st.expander("Suggested follow-up actions", expanded=False):
			for suggestion in model["suggestions"]:
				st.markdown(f"- {suggestion}")

	with st.expander("Recommended workflow", expanded=False):
		st.markdown(
			"1. First make the intended progression logic explicit: identify gatekeeping task(s), "
			"and where relevant maintenance task(s).\n\n"
			"2. Then review point logic: missing targets, unreachable targets, and whether progression "
			"is possible without the gatekeeping task(s).\n\n"
			"3. After role annotations are accepted and saved, regenerate proposals because additional "
			"point issues may become visible.\n\n"
			"This workflow reflects the current long-term-trial style campaigns. "
			"Other GameBus campaigns may use different progression logic."
		)


def _severity_explainer_markdown() -> str:
	return (
		"- **High**: likely breaks progression, reachability, active-wave behavior, "
		"or another core campaign mechanic.\n"
		"- **Medium**: likely wrong, incomplete, or ambiguous, but not obviously blocking core flow.\n"
		"- **Low**: informational, annotation-related, or useful follow-up work.\n\n"
		"Severity is currently heuristic. It is intended to help prioritization, "
		"not to serve as a formal correctness proof."
	)


def _ensure_current_manifest_from_saved_decisions(result: Dict[str, Any]) -> Dict[str, Any] | None:
	assistant_meta = result.get("assistant_meta", {}) or {}
	workspace_root = assistant_meta.get("workspace_root")
	request_id = assistant_meta.get("request_id")

	if not workspace_root or not request_id:
		return None

	proposals = result.get("fix_proposals", {}).get("proposals", []) or []
	handler = ApprovalHandler(workspace_root=workspace_root, request_id=request_id)
	merged_proposals = handler.merge_statuses(proposals)
	result["fix_proposals"]["proposals"] = merged_proposals

	manifest_generator = PatchManifestGenerator(
		workspace_root=workspace_root,
		request_id=request_id,
	)
	manifest = manifest_generator.generate(merged_proposals)
	result["patch_manifest"] = manifest
	return manifest



def _proposal_ids_from_groups(groups: list[Dict[str, Any]]) -> list[str]:
	ids: list[str] = []
	for group in groups:
		ids.extend(group.get("member_proposal_ids", []))
	return ids


def _format_group_detail_markdown(group: Dict[str, Any]) -> str:
	lines = []
	lines.append(f"- **Issue family:** {group.get('issue_label')}")
	lines.append(f"- **Summary:** {group.get('summary')}")
	lines.append(f"- **Category:** {group.get('category')}")
	lines.append(f"- **Severity:** {group.get('severity')}")
	lines.append(f"- **Status:** {group.get('status')}")
	lines.append(f"- **Priority:** {group.get('priority', 'normal')}")
	if group.get("priority_reason"):
		lines.append(f"- **Why now:** {group.get('priority_reason')}")
	lines.append(f"- **Member proposals:** {group.get('member_count', 0)}")

	context_tags = group.get("context_tags") or []
	if context_tags:
		lines.append(f"- **Context tags:** {', '.join(context_tags)}")

	challenge_names = group.get("challenge_names") or []
	if challenge_names:
		lines.append("- **Affected challenges:**")
		for name in challenge_names[:15]:
			lines.append(f"  - {name}")
		if len(challenge_names) > 15:
			lines.append(f"  - … and {len(challenge_names) - 15} more")

	rationales = group.get("rationales") or []
	if rationales:
		lines.append("- **Rationales:**")
		for item in rationales[:5]:
			lines.append(f"  - {item}")

	notes = group.get("notes") or []
	if notes:
		lines.append("- **Notes:**")
		for item in notes[:5]:
			lines.append(f"  - {item}")

	member_ids = group.get("member_proposal_ids") or []
	if member_ids:
		lines.append("- **Proposal IDs:**")
		for pid in member_ids[:15]:
			lines.append(f"  - `{pid}`")
		if len(member_ids) > 15:
			lines.append(f"  - … and {len(member_ids) - 15} more")

	return "\n".join(lines)



def _format_member_detail_markdown(proposal: Dict[str, Any]) -> str:
	lines = []
	lines.append(f"- **Proposal ID:** `{proposal.get('proposal_id')}`")
	lines.append(f"- **Challenge:** {proposal.get('challenge_name') or 'General'}")
	lines.append(f"- **Category:** {proposal.get('category')}")
	lines.append(f"- **Action type:** {proposal.get('action_type')}")
	lines.append(f"- **Severity:** {proposal.get('severity')}")
	lines.append(f"- **Status:** {proposal.get('status', 'proposed')}")

	rationale = proposal.get("rationale")
	if rationale:
		lines.append(f"- **Rationale:** {rationale}")

	suggested_change = proposal.get("suggested_change")
	if suggested_change:
		lines.append("- **Suggested change:**")
		for key, value in suggested_change.items():
			lines.append(f"  - **{key}**: `{value}`")

	notes = proposal.get("notes")
	if notes:
		lines.append(f"- **Notes:** {notes}")

	return "\n".join(lines)


def _group_setup_actions(group: Dict[str, Any]) -> list[tuple[str, str]]:
	tags = set(group.get("context_tags") or [])
	issue_family = str(group.get("issue_family") or "")

	actions: list[tuple[str, str]] = []

	if "gatekeeping" in tags or "maintenance" in tags or "setup-needed" in tags:
		actions.append(("Open task-role editor", "task_roles"))

	if "ttm" in tags or issue_family == "ttm_manual_review":
		actions.append(("Open theory file setup", "theory"))

	if issue_family in {
		"missing_target_points",
		"unreachable_target_points",
		"gatekeeping_not_required_by_points",
	}:
		actions.append(("Open capability profile", "profile"))

	# Deduplicate while preserving order
	seen = set()
	deduped: list[tuple[str, str]] = []
	for label, target in actions:
		key = (label, target)
		if key in seen:
			continue
		seen.add(key)
		deduped.append((label, target))

	return deduped


def _count_fix_proposals_by_status(proposals: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {
        "proposed": 0,
        "accepted": 0,
        "rejected": 0,
    }

    for proposal in proposals:
        status = str(proposal.get("status", "proposed") or "proposed")
        counts[status] = counts.get(status, 0) + 1

    return counts


def _proposal_group_table_rows(groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for g in groups:
        rows.append(
            {
                "group_id": g.get("group_id"),
                "summary": g.get("summary"),
                "issue_family": g.get("issue_label"),
                "category": g.get("category"),
                "severity": g.get("severity"),
                "priority": g.get("priority", "normal"),
                "member_count": g.get("member_count", 0),
                "status": g.get("status", "proposed"),
            }
        )

    return rows


def _priority_group_count(groups: List[Dict[str, Any]]) -> int:
    return sum(1 for g in groups if str(g.get("priority", "normal")) != "normal")


def render_fix_proposals_panel(result: Dict[str, Any]) -> None:
    fixer = result.get("fix_proposals", {})
    if not fixer:
        return

    st.subheader("Fix proposals")

    raw_count = fixer.get("proposal_count", 0)
    path = fixer.get("proposals_path")

    proposals = fixer.get("proposals", []) or []
    if not proposals:
        st.info("No concrete repair proposals were generated for this run.")
        if path:
            st.caption(f"Saved proposal artifact: {path}")
        return

    assistant_meta = result.get("assistant_meta", {}) or {}
    workspace_root = assistant_meta.get("workspace_root")
    workspace_id = assistant_meta.get("workspace_id")
    request_id = assistant_meta.get("request_id")
    snapshot_path = assistant_meta.get("snapshot_path")

    handler = None
    if workspace_root and request_id:
        handler = ApprovalHandler(workspace_root=workspace_root, request_id=request_id)
        proposals = handler.merge_statuses(proposals)
        result["fix_proposals"]["proposals"] = proposals

    capability_summary = result.get("assistant_meta", {}).get("capability_summary", {}) or {}
    proposal_groups = build_proposal_groups(proposals)
    proposal_groups = annotate_proposal_groups_with_context(proposal_groups, capability_summary)

    status_counts = _count_fix_proposals_by_status(proposals)
    priority_count = _priority_group_count(proposal_groups)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Proposal groups", len(proposal_groups))
    c2.metric("Raw proposals", raw_count)
    c3.metric("Pending review", status_counts.get("proposed", 0))
    c4.metric("Accepted", status_counts.get("accepted", 0))
    c5.metric("Rejected", status_counts.get("rejected", 0))

    if priority_count > 0:
        st.info(f"**{priority_count}** proposal group(s) are marked as higher-priority review targets.")

    if path:
        st.caption(f"Saved proposal artifact: {path}")

    with st.expander("Proposal review", expanded=False):
        all_statuses = ["proposed", "accepted", "rejected", "mixed"]

        col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns([2, 2, 3, 2, 2])

        with col_f1:
            status_filter = st.multiselect(
                "Statuses",
                options=all_statuses,
                default=all_statuses,
                key=f"proposal-status-filter-{request_id}",
            )

        with col_f2:
            page_size = st.selectbox(
                "Rows per page",
                options=[25, 50, 100],
                index=1,
                key=f"proposal-page-size-{request_id}",
            )

        with col_f3:
            search = st.text_input(
                "Search proposal/challenge/action",
                key=f"proposal-search-{request_id}",
            ).strip().lower()

        with col_f4:
            focus_filter = st.selectbox(
                "Focus",
                options=[
                    "All",
                    "Recommended now",
                    "Gatekeeping setup",
                    "Maintenance setup",
                    "Point fixes",
                    "TTM review",
                ],
                key=f"proposal-focus-filter-{request_id}",
            )

        with col_f5:
            with st.popover("ℹ️ Severity"):
                st.markdown(_severity_explainer_markdown())

        filtered_groups = []
        for group in proposal_groups:
            if group.get("status", "proposed") not in status_filter:
                continue

            if not matches_group_focus(group, focus_filter):
                continue

            if search:
                haystack = " ".join(
                    str(group.get(k, "") or "")
                    for k in [
                        "group_id",
                        "summary",
                        "issue_family",
                        "issue_label",
                        "category",
                        "severity",
                        "priority",
                        "priority_reason",
                        "context_tags",
                    ]
                ).lower()
                if search not in haystack:
                    continue

            filtered_groups.append(group)

        filtered_raw_count = len(_proposal_ids_from_groups(filtered_groups))
        st.caption(
            f"Showing **{len(filtered_groups)} group(s)** covering **{filtered_raw_count} proposal(s)** "
            f"out of **{len(proposal_groups)} groups / {raw_count} proposals**."
        )

        if not filtered_groups:
            st.info("No proposal groups match the current filters.")
        else:
            col_a, col_b, col_c, col_d = st.columns([2, 2, 2, 4])

            with col_a:
                if st.button("Approve visible groups", key=f"approve-visible-groups-{request_id}"):
                    if handler is not None:
                        ids = _proposal_ids_from_groups(filtered_groups[:page_size])
                        handler.save_decisions_bulk(
                            [
                                {
                                    "proposal_id": pid,
                                    "status": "accepted",
                                    "reviewer": "human",
                                }
                                for pid in ids
                            ]
                        )
                        st.success(f"Approved {len(ids)} proposal(s) from the visible slice.")
                        st.rerun()

            with col_b:
                if st.button("Approve filtered groups", key=f"approve-filtered-groups-{request_id}"):
                    if handler is not None:
                        ids = _proposal_ids_from_groups(filtered_groups)
                        handler.save_decisions_bulk(
                            [
                                {
                                    "proposal_id": pid,
                                    "status": "accepted",
                                    "reviewer": "human",
                                }
                                for pid in ids
                            ]
                        )
                        st.success(f"Approved {len(ids)} filtered proposal(s).")
                        st.rerun()

            with col_c:
                if st.button("Approve everything (testing)", key=f"approve-all-{request_id}"):
                    if handler is not None:
                        handler.save_decisions_bulk(
                            [
                                {
                                    "proposal_id": p["proposal_id"],
                                    "status": "accepted",
                                    "reviewer": "human",
                                }
                                for p in proposals
                            ]
                        )
                        st.success(f"Approved all {len(proposals)} proposal(s).")
                        st.rerun()

            with col_d:
                st.caption(
                    "Select one grouped row below to inspect and approve/reject/reset the whole group at once."
                )

            total_pages = max(1, math.ceil(len(filtered_groups) / page_size))
            page_number = st.number_input(
                "Page",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1,
                key=f"proposal-page-number-{request_id}",
            )

            start = (page_number - 1) * page_size
            end = start + page_size
            visible_groups = filtered_groups[start:end]

            st.caption(
                f"Showing groups {start + 1}–{min(end, len(filtered_groups))} of {len(filtered_groups)} filtered groups."
            )

            df = pd.DataFrame(_proposal_group_table_rows(visible_groups))

            selection = st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key=f"proposal-group-table-{request_id}",
            )

            selected_rows = []
            if selection and "selection" in selection and "rows" in selection["selection"]:
                selected_rows = selection["selection"]["rows"]

            selected_group = None
            if selected_rows:
                selected_idx = selected_rows[0]
                if 0 <= selected_idx < len(visible_groups):
                    selected_group = visible_groups[selected_idx]

            if selected_group is not None:
                st.markdown("### Selected proposal group")
                st.markdown(_format_group_detail_markdown(selected_group))

                setup_actions = _group_setup_actions(selected_group)
                if setup_actions:
                    st.markdown("#### Quick actions")
                    action_cols = st.columns(len(setup_actions))
                    for idx, (label, target) in enumerate(setup_actions):
                        with action_cols[idx]:
                            if st.button(
                                label,
                                key=f"group-setup-action-{request_id}-{selected_group['group_id']}-{target}",
                            ):
                                st.session_state[f"campaign-setup-focus-{request_id}"] = target
                                st.rerun()

                member_ids = selected_group.get("member_proposal_ids", [])
                current_status = selected_group.get("status", "proposed")
                members = selected_group.get("members", [])

                col1, col2, col3, col4 = st.columns([1, 1, 1, 4])

                with col1:
                    if st.button(
                        "Approve group",
                        key=f"approve-selected-group-{request_id}-{selected_group['group_id']}",
                    ):
                        if handler is not None:
                            handler.save_decisions_bulk(
                                [
                                    {
                                        "proposal_id": pid,
                                        "status": "accepted",
                                        "reviewer": "human",
                                    }
                                    for pid in member_ids
                                ]
                            )
                            st.rerun()

                with col2:
                    if st.button(
                        "Reject group",
                        key=f"reject-selected-group-{request_id}-{selected_group['group_id']}",
                    ):
                        if handler is not None:
                            handler.save_decisions_bulk(
                                [
                                    {
                                        "proposal_id": pid,
                                        "status": "rejected",
                                        "reviewer": "human",
                                    }
                                    for pid in member_ids
                                ]
                            )
                            st.rerun()

                with col3:
                    if st.button(
                        "Reset group",
                        key=f"reset-selected-group-{request_id}-{selected_group['group_id']}",
                    ):
                        if handler is not None:
                            handler.save_decisions_bulk(
                                [
                                    {
                                        "proposal_id": pid,
                                        "status": "proposed",
                                        "reviewer": "human",
                                    }
                                    for pid in member_ids
                                ]
                            )
                            st.rerun()

                with col4:
                    st.caption(f"Current group status: **{current_status}**")

                if members:
                    st.markdown("#### Member proposals")

                    member_rows = [
                        {
                            "proposal_id": m.get("proposal_id"),
                            "challenge_name": m.get("challenge_name") or "General",
                            "category": m.get("category"),
                            "action_type": m.get("action_type"),
                            "severity": m.get("severity"),
                            "status": m.get("status", "proposed"),
                        }
                        for m in members
                    ]

                    member_df = pd.DataFrame(member_rows)

                    member_selection = st.dataframe(
                        member_df,
                        use_container_width=True,
                        hide_index=True,
                        on_select="rerun",
                        selection_mode="single-row",
                        key=f"group-member-table-{request_id}-{selected_group['group_id']}",
                    )

                    selected_member_rows = []
                    if (
                        member_selection
                        and "selection" in member_selection
                        and "rows" in member_selection["selection"]
                    ):
                        selected_member_rows = member_selection["selection"]["rows"]

                    selected_member = None
                    if selected_member_rows:
                        selected_idx = selected_member_rows[0]
                        if 0 <= selected_idx < len(members):
                            selected_member = members[selected_idx]

                    if selected_member is not None:
                        st.markdown("#### Selected member proposal")
                        st.markdown(_format_member_detail_markdown(selected_member))

                        member_pid = selected_member.get("proposal_id")
                        member_status = selected_member.get("status", "proposed")

                        colm1, colm2, colm3, colm4 = st.columns([1, 1, 1, 4])

                        with colm1:
                            if st.button(
                                "Approve member",
                                key=f"approve-member-{request_id}-{member_pid}",
                            ):
                                if handler is not None:
                                    handler.save_decision(
                                        proposal_id=member_pid,
                                        status="accepted",
                                        reviewer="human",
                                    )
                                    st.rerun()

                        with colm2:
                            if st.button(
                                "Reject member",
                                key=f"reject-member-{request_id}-{member_pid}",
                            ):
                                if handler is not None:
                                    handler.save_decision(
                                        proposal_id=member_pid,
                                        status="rejected",
                                        reviewer="human",
                                    )
                                    st.rerun()

                        with colm3:
                            if st.button(
                                "Reset member",
                                key=f"reset-member-{request_id}-{member_pid}",
                            ):
                                if handler is not None:
                                    handler.save_decision(
                                        proposal_id=member_pid,
                                        status="proposed",
                                        reviewer="human",
                                    )
                                    st.rerun()

                        with colm4:
                            st.caption(f"Current member status: **{member_status}**")

    # ---------- Draft generation / execution ----------
    if workspace_root and request_id and snapshot_path:
        draft_generator = PatchedExcelDraftGenerator(workspace_root=workspace_root, request_id=request_id)

        col_c, col_d, col_e = st.columns([2, 5, 3])

        with col_c:
            if st.button(
                "Generate patched Excel draft",
                key=f"generate-patched-draft-{request_id}",
            ):
                manifest = _ensure_current_manifest_from_saved_decisions(result)
                if manifest is None:
                    st.warning("Could not build an internal patch manifest for this workspace.")
                else:
                    draft_summary = draft_generator.generate(
                        snapshot_path=snapshot_path,
                        manifest=manifest,
                    )
                    result["patched_excel_draft"] = draft_summary
                    st.success("Patched Excel draft generated.")
                    st.rerun()

        with col_d:
            st.caption(
                "Applies currently accepted proposals to a copy of the campaign export. "
                "Unsupported operations remain listed in the notes sheet."
            )

        with col_e:
            if draft_generator.draft_path.exists():
                if st.button(
                    "Open patched draft as current campaign",
                    key=f"open-patched-draft-{request_id}",
                ):
                    st.session_state["reload_generated_draft_payload"] = {
                        "path": str(draft_generator.draft_path),
                        "workspace_id": workspace_id,
                    }
                    st.rerun()

        if draft_generator.draft_path.exists():
            st.caption(f"Latest patched draft path: {draft_generator.draft_path}")

            if "patched_excel_draft" not in result and draft_generator.summary_path.exists():
                import json
                result["patched_excel_draft"] = json.loads(
                    draft_generator.summary_path.read_text(encoding="utf-8")
                )

            with st.expander("Patched draft preview", expanded=False):
                st.markdown(_build_patched_draft_markdown(result))

    if workspace_root and request_id:
        role_generator = TaskRolesDraftGenerator(workspace_root=workspace_root, request_id=request_id)

        col_e, col_f = st.columns([2, 5])

        with col_e:
            if st.button(
                "Generate task-role sidecar draft",
                key=f"generate-role-draft-{request_id}",
            ):
                manifest = _ensure_current_manifest_from_saved_decisions(result)
                if manifest is None:
                    st.warning("Could not build an internal patch manifest for this workspace.")
                else:
                    role_summary = role_generator.generate(manifest)
                    result["task_roles_draft"] = role_summary
                    st.success("Task-role sidecar draft generated.")
                    st.rerun()

        with col_f:
            st.caption(
                "Builds a draft `task_roles.csv` sidecar from currently accepted role-annotation proposals. "
                "This is useful until GameBus supports native task-role metadata."
            )

        if role_generator.draft_path.exists():
            st.caption(f"Latest task-role draft path: {role_generator.draft_path}")

            if "task_roles_draft" not in result and role_generator.summary_path.exists():
                import json
                result["task_roles_draft"] = json.loads(
                    role_generator.summary_path.read_text(encoding="utf-8")
                )

            with st.expander("Task-role sidecar draft preview", expanded=False):
                st.markdown(_build_task_roles_draft_markdown(result))



def render_agent_trace_panel(result: Dict[str, Any], show_trace: bool) -> None:
	if not show_trace:
		return

	trace = result.get("assistant_meta", {}).get("agent_trace", [])
	if not trace:
		return

	st.subheader("Agent reasoning trace")
	st.markdown(_build_agent_trace_markdown(result, max_items=TRACE_EVENTS_MAX))


def render_analysis_panels(result: Dict[str, Any], show_trace: bool) -> None:
	if not result:
		st.info("No campaign has been analyzed yet.")
		return

	render_analysis_overview(result)
	render_assistant_guide_panel(result)
	render_findings_overview_panel(result)
	render_capability_panel(result)
	render_theory_panel(result)
	render_point_gatekeeping_panel(result)
	render_fix_proposals_panel(result)
	render_issues_panel(result)
	render_agent_trace_panel(result, show_trace)