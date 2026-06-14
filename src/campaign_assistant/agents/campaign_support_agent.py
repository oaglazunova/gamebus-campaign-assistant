from __future__ import annotations

import re

from typing import Any

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.agents.context_builder import format_llm_context_markdown
from campaign_assistant.llm.base import LLMClient
from campaign_assistant.agents.gamebus_studio_knowledge import (
	gamebus_studio_field_facts_markdown_for_question,
)
from campaign_assistant.checker.check_metadata import PRIORITY_HINT, check_explanation
from campaign_assistant.checker.schema import FRIENDLY_CHECK_NAMES
from campaign_assistant.agents.response_guard import uncertainty_response, _lower
from campaign_assistant.agents.finding_explainer import explain_prepared_finding


UNCERTAINTY_RULES = """
Uncertainty and scope rules:
- Answer only from the provided campaign/checker context and known GameBus Studio facts.
- Do not guess missing campaign intent, user experience, task rationale, or GameBus Studio configuration.
- If the question cannot be answered from the available context, say:
  "I’m not sure from the available campaign data."
- Then briefly explain what is missing.
- Then suggest one clearer question the user could ask.
- If the question is unrelated to the campaign, checker findings, GameBus Studio, or behaviour-change theory, say it is outside the assistant scope.
- Do not replace an unknown answer with a generic campaign summary.
"""


CAMPAIGN_SUPPORT_SYSTEM_PROMPT = f"""
You are the Campaign Support Agent for the GameBus Campaign Assistant.

Your role:
- Explain deterministic checker findings.
- Explain what an error or warning means for campaign organizers.
- Suggest what the user should inspect next.
- Suggest possible human-reviewed repair steps.
- Help prioritize findings.

Strict boundaries:
- Do not invent new formal validation errors.
- Do not claim that a campaign has an issue unless it is present in the checker context.
- Do not claim that the campaign is fixed.
- Do not modify or generate campaign files.
- Do not present behavior-change theory feedback as formal validation.
- If the user asks about behavior-change theory, say that theory-oriented support belongs to the Theory Support Agent.
- Checker facts are authoritative. Do not contradict total_issues, failed_checks, or known findings.
- Deterministic GameBus Studio fix guidance is authoritative for where to inspect and how to fix deterministic checker findings.
- If deterministic GameBus Studio fix guidance is available, use it as the basis for repair advice.
- You may rephrase deterministic guidance in clearer language, but do not add unsupported GameBus Studio fields, tabs, or repair steps.
- GameBus Studio facts may be used to explain field meanings, editor locations, and export mappings.
- Do not claim that a GameBus Studio field, tab, route, or save behavior exists unless it is present in deterministic guidance, GameBus Studio source facts, or the checker context.
- If the user asks for a GameBus behavior that is not covered by the source facts, say that the current local source facts do not establish it.
- Export structure counts are descriptive facts, not errors by themselves.
- If total_issues is 0, do not say that the checker found issues, inconsistencies, warnings, or errors.
- For broad questions such as "is this a good campaign?", distinguish structural checker results from content quality, theory alignment, and outcome effectiveness.

Response style:
- Do not merely repeat the deterministic guidance verbatim.
- Do not answer with only "Okay", "Sure", or another acknowledgement.
- For finding explanations, use this structure:
  1. What the checker found.
  2. Why it matters.
  3. What to inspect in GameBus Studio.
  4. What to change, if the finding is valid.
- Keep answers practical and concise.
- Prefer concrete field names from deterministic guidance or GameBus Studio source facts.

Use cautious wording:
- "The checker found..."
- "You should inspect..."
- "A likely next step is..."
- "This may indicate..."

{UNCERTAINTY_RULES}
"""


_DETERMINISTIC_GUIDANCE_QUESTION_PATTERNS = [
	r"\bhow\b.*\b(fix|repair|correct|solve|resolve|change|edit)\b",
	r"\bwhat\b.*\b(fix|repair|correct|change|edit)\b",
	r"\bwhere\b.*\b(fix|repair|change|edit|click)\b",
	r"\bwhich\b.*\b(field|fields)\b.*\b(change|edit|set|fill)\b",
	r"\bwhat\b.*\b(field|fields)\b.*\b(change|edit|set|fill)\b",
	r"\bmake\b.*\breachable\b",
	r"\bhow\b.*\breachable\b",
]


def _normalized(text: Any) -> str:
	return " ".join(str(text or "").lower().split())


def _is_weak_llm_answer(text: str) -> bool:
	normalized = " ".join(str(text or "").strip().lower().split())
	normalized = normalized.strip(" .!?,;:")

	if not normalized:
		return True

	weak_exact = {
		"ok",
		"okay",
		"sure",
		"yes",
		"no",
		"i see",
		"understood",
		"got it",
		"noted",
	}

	if normalized in weak_exact:
		return True


	weak_prefixes = [
		"okay",
		"sure",
		"yes",
		"i can help",
		"i can help with that",
	]

	weak_phrases = [
		"i'm ready to help",
		"i am ready to help",
		"i'm here to help",
		"i am here to help",
		"please provide",
		"provide the campaign",
		"provide more details",
		"i don't see a specific question",
		"i do not see a specific question",
		"no specific question was asked",
		"unfortunately, i don't see",
		"unfortunately, i do not see",
		"i need more information before",
		"i would need more information before",
	]

	if any(phrase in normalized for phrase in weak_phrases):
		return True

	# Catches "Okay, ..." only if there is no substantive continuation.
	if normalized in weak_prefixes:
		return True

	# Catches short non-answers such as "Okay, understood" but not "Mock answer".
	tokens = normalized.split()
	if len(tokens) <= 3 and all(token in weak_exact for token in tokens):
		return True

	return False


def _is_deterministic_guidance_question(question: str) -> bool:
	normalized = _normalized(question)
	return any(
		re.search(pattern, normalized)
		for pattern in _DETERMINISTIC_GUIDANCE_QUESTION_PATTERNS
	)


def _answer_mostly_repeats_question(question: str, answer: str) -> bool:
	q_words = set(_lower(question).split())
	a_words = _lower(answer).split()

	if len(a_words) < 40:
		return False

	overlap = sum(1 for word in a_words if word in q_words)
	return overlap / max(len(a_words), 1) > 0.55



def _check_explanation_answer(question: str) -> str | None:
	normalized = _normalized(question)

	explanation_intent = any(
		phrase in normalized
		for phrase in [
			"what does",
			"what is",
			"explain",
			"how is",
			"how does",
			"how calculated",
			"how is calculated",
		]
	)

	manual_aliases = {
		"spellchecker": ["spellcheck", "spelling", "spell checker"],
		"visualizationintern": [
			"visualization intern",
			"visualization internal",
			"visualization internals",
			"visualisation intern",
			"visualisation internal",
			"visualisation internals",
		],
		"targetpointsreachable": [
			"target points",
			"target point",
			"points reachable",
			"target reachable",
		],
		"ttm": [
			"ttm",
			"ttm structure",
			"transtheoretical model",
		],
	}

	if "explain this campaign finding" in normalized or "finding:" in normalized:
		return None

	for check_id, friendly_name in FRIENDLY_CHECK_NAMES.items():
		aliases = {
			check_id.lower(),
			friendly_name.lower(),
			friendly_name.lower().replace(" ", ""),
			friendly_name.lower().replace(" ", "_"),
		}
		aliases.update(manual_aliases.get(check_id, []))

		mentions_check = any(alias in normalized for alias in aliases)

		# Handles normal questions:
		# "What does consistency do?"
		# "Explain spellchecker"
		#
		# Also handles short follow-ups:
		# "and consistency?"
		# "consistency?"
		# "target points?"
		short_follow_up = (
				len(normalized.split()) <= 4
				and (
						normalized.startswith("and ")
						or normalized.endswith("?")
						or normalized in aliases
				)
		)

		if mentions_check and (explanation_intent or short_follow_up):
			explanation = check_explanation(check_id)
			if explanation:
				return explanation

	return None


def _all_checks_explanation_answer(question: str) -> str | None:
	normalized = _normalized(question)

	patterns = [
		r"\bwhat\b.*\bchecks\b.*\bcheck\b",
		r"\bwhat\b.*\bcheckers\b.*\bcheck\b",
		r"\bwhat\b.*\bchecks\b.*\bdo\b",
		r"\bexplain\b.*\bchecks\b",
		r"\bwhich checks\b",
	]

	if not any(re.search(pattern, normalized) for pattern in patterns):
		return None

	lines = [
		"The selected deterministic checks inspect different parts of the campaign export:",
		"",
	]

	for check_id, friendly_name in FRIENDLY_CHECK_NAMES.items():
		explanation = check_explanation(check_id)
		if not explanation:
			continue

		first_sentence = explanation.split(". ")[0].strip()
		lines.append(f"- **{friendly_name}**: {first_sentence}.")

	lines.append("")
	lines.append(
		"Ask about a specific check, for example `What does spellchecker do?`, "
		"to see the full detailed explanation."
	)

	return "\n".join(lines)


def _is_prioritization_question(question: str) -> bool:
	normalized = _normalized(question)

	patterns = [
		r"\bhow\b.*\bprioriti[sz]ation\b.*\bcalculat",
		r"\bhow\b.*\bprioriti[sz]ed\b",
		r"\bhow\b.*\bpriority\b.*\bcalculat",
		r"\bpriority score\b",
		r"\bprioriti[sz]ation\b",
	]

	return any(re.search(pattern, normalized) for pattern in patterns)


def _is_priority_reason_question(question: str) -> bool:
	normalized = _normalized(question)

	patterns = [
		r"\bwhy\b.*\b(first|prioriti[sz]ed|priority|top)\b",
		r"\bwhy\b.*\binspect\b.*\bfirst\b",
		r"\bwhy\b.*\bhave to\b.*\binspect\b",
		r"\bwhy\b.*\bthese issues\b.*\bfirst\b",
		r"\bwhy\b.*\bthese issues\b.*\bprioriti[sz]ed\b",
	]

	return any(re.search(pattern, normalized) for pattern in patterns)


def _total_issues_from_context(context: dict[str, Any]) -> int:
	analysis = context.get("analysis", {}) or {}
	try:
		return int(analysis.get("total_issues", 0) or 0)
	except (TypeError, ValueError):
		return 0


def _is_fix_or_inspection_question(question: str) -> bool:
	normalized = _normalized(question)

	patterns = [
		r"\bwhat\b.*\bfix\b.*\bfirst\b",
		r"\bwhat\b.*\binspect\b.*\bfirst\b",
		r"\bwhat\b.*\bcheck\b.*\bfirst\b",
		r"\bwhat\b.*\blook\b.*\bat\b.*\bfirst\b",
		r"\bwhat\b.*\bshould\b.*\bfix\b",
		r"\bwhat\b.*\bshould\b.*\binspect\b",
		r"\bhow\b.*\bfix\b",
		r"\bhow\b.*\brepair\b",
		r"\bhow\b.*\bresolve\b",
	]

	return any(re.search(pattern, normalized) for pattern in patterns)


def _clean_result_fix_answer(context: dict[str, Any]) -> str:
	return (
		"The selected deterministic checks found **0 issues**.\n\n"
		"There is no checker finding to fix first. This means the selected structural "
		"checks passed for this export.\n\n"
		"This does not prove that the campaign is complete, effective, theory-aligned, "
		"or free of content/design problems outside the selected checks."
	)


def _prioritization_answer() -> str:
	return (
		f"{PRIORITY_HINT}\n\n"
		"In practice, this means:\n"
		"- High-severity findings are shown before medium- and low-severity findings.\n"
		"- Findings in an active wave receive a small boost.\n"
		"- The active-wave boost does not normally make a medium finding outrank a high finding.\n"
		"- If a finding ever has missing/unknown severity, it receives severity score 0 and should be treated as incomplete metadata."
	)

def _is_acknowledgement(question: str) -> bool:
	q = " ".join(str(question or "").lower().strip().split())
	return q in {
		"thanks",
		"thanks!",
		"thank you",
		"thank you!",
		"ok",
		"okay",
		"great",
		"got it",
	}


def _question_mentions_finding(question: str, finding: dict[str, Any]) -> bool:
	"""Return whether the question appears to refer to a specific finding.

	This supports prepared questions from the Findings page, where the question
	often contains challenge id, challenge name, visualization name, or check.
	"""
	normalized_question = _normalized(question)

	candidate_fields = [
		"challenge_id",
		"visualization_id",
		"wave_id",
		"challenge",
		"visualization",
		"title",
		"message",
		"check",
	]

	for field in candidate_fields:
		value = finding.get(field)
		if value in (None, ""):
			continue

		normalized_value = _normalized(value)
		if normalized_value and normalized_value in normalized_question:
			return True

	return False


def _select_guided_finding(
		question: str,
		context: dict[str, Any],
) -> dict[str, Any] | None:
	focused_finding = context.get("focused_finding")
	if (
			isinstance(focused_finding, dict)
			and focused_finding.get("deterministic_gamebus_fix_guidance")
	):
		return focused_finding

	findings = [
		finding
		for finding in (context.get("top_findings", []) or [])
		if isinstance(finding, dict)
		   and finding.get("deterministic_gamebus_fix_guidance")
	]

	if not findings:
		return None

	for finding in findings:
		if _question_mentions_finding(question, finding):
			return finding

	# For short follow-ups such as "how can I fix this?", use the highest-priority
	# finding only when no selected finding is available.
	return findings[0]


def _deterministic_guidance_answer(
		question: str,
		context: dict[str, Any],
) -> str | None:
	"""Answer repair/inspection questions directly from deterministic guidance.

	This intentionally bypasses the LLM for fix instructions. It avoids failure
	modes such as "Okay" and prevents the model from inventing GameBus fields.
	"""
	if not _is_deterministic_guidance_question(question):
		return None

	finding = _select_guided_finding(question, context)
	if finding is None:
		return None

	title = finding.get("title") or "Finding"
	check = finding.get("check") or "unknown"
	severity = finding.get("severity") or "unknown"
	guidance = finding.get("deterministic_gamebus_fix_guidance")
	source_facts = finding.get("gamebus_studio_source_facts")

	lines = [
		"Use the deterministic GameBus Studio guidance for this finding.",
		"",
		f"**Finding:** {title}",
		f"**Check:** `{check}`",
		f"**Severity:** `{severity}`",
	]

	visualization = finding.get("visualization")
	if visualization:
		lines.append(f"**Visualization:** {visualization}")

	challenge = finding.get("challenge")
	if challenge:
		lines.append(f"**Challenge:** {challenge}")

	challenge_id = finding.get("challenge_id")
	if challenge_id not in (None, ""):
		lines.append(f"**Challenge ID:** {challenge_id}")

	url = finding.get("url")
	if url:
		lines.append(f"**GameBus Studio URL:** {url}")

	lines.append("")
	lines.append(str(guidance))

	if source_facts:
		lines.append("")
		lines.append("**Relevant GameBus Studio facts**")
		lines.append(str(source_facts))

	return "\n".join(lines)


def _issue_summary_answer(question: str, context: dict[str, Any]) -> str | None:
	normalized = _normalized(question)

	if _is_deterministic_guidance_question(question):
		return None

	overview_patterns = [
		r"\bsummarize\b.*\b(issue|issues|finding|findings|patterns)\b",
		r"\bsummarise\b.*\b(issue|issues|finding|findings|patterns)\b",
		r"\bsummary\b.*\b(issue|issues|finding|findings|patterns)\b",
		r"\boverview\b.*\b(issue|issues|finding|findings|patterns)\b",
		r"\bgive me an overview\b",
		r"\boverview\b",
		r"\bmain issue patterns\b",
	]

	if not any(re.search(pattern, normalized) for pattern in overview_patterns):
		return None

	analysis = context.get("analysis", {}) or {}
	top_findings = context.get("top_findings", []) or []

	total = analysis.get("total_issues", 0)
	failed_checks = analysis.get("failed_checks", []) or []
	severity_counts = analysis.get("severity_counts", {}) or {}
	issue_count_by_check = analysis.get("issue_count_by_check", {}) or {}

	lines = [
		"Summary of issues:",
		"",
		f"- Total issues: **{total}**",
	]

	if severity_counts:
		severity_parts = [
			f"{severity}: {count}"
			for severity, count in severity_counts.items()
			if count
		]
		if severity_parts:
			lines.append("- Severity: " + ", ".join(severity_parts))

	if failed_checks:
		lines.append("- Failed checks: " + ", ".join(f"`{check}`" for check in failed_checks))
	else:
		lines.append("- Failed checks: none")

	if issue_count_by_check:
		count_parts = [
			f"{check}: {count}"
			for check, count in issue_count_by_check.items()
			if count
		]
		if count_parts:
			lines.append("- Issue counts by check: " + ", ".join(count_parts))

	if top_findings:
		top_findings = top_findings[:5] if len(top_findings) > 5 else top_findings
		lines.append("")
		lines.append("First items to inspect:")
		for idx, finding in enumerate(top_findings, start=1):
			title = finding.get("title") or "Finding"
			check = finding.get("check") or "unknown"
			severity = finding.get("severity") or "unknown"
			lines.append(f"- {idx}. [{severity}] {title} (check: `{check}`)")
			visualization = finding.get("visualization")
			if visualization:
				lines.append(f"   - Visualization: {visualization}")
			challenge = finding.get("challenge")
			if challenge:
				lines.append(f"   - Challenge: {challenge}")
			url = finding.get("url")
			if url:
				lines.append(f"   - GameBus Studio URL: {url}")

	lines.append("")
	lines.append("Use **Findings** for the full list and **Assistant** to explain a specific finding.")

	return "\n".join(lines)


def _highest_priority_finding_answer(question: str, context: dict[str, Any]) -> str | None:
	normalized = _normalized(question)

	if not any(
			phrase in normalized
			for phrase in [
				"highest-priority finding",
				"highest priority finding",
				"top-priority finding",
				"top priority finding",
				"highest-priority issue",
				"highest priority issue",
				"top issue",
			]
	):
		return None

	top_findings = context.get("top_findings", []) or []
	if not top_findings:
		return "No prioritized findings are available in the current context."

	finding = top_findings[0]

	title = finding.get("title") or finding.get("message") or "Finding"
	check = finding.get("check") or "unknown"
	severity = finding.get("severity") or "unknown"
	guidance = finding.get("deterministic_gamebus_fix_guidance")

	lines = [
		"Highest-priority finding:",
		"",
		f"**Finding:** {title}",
		f"**Check:** `{check}`",
		f"**Severity:** `{severity}`",
	]

	visualization = finding.get("visualization")
	if visualization:
		lines.append(f"**Visualization:** {visualization}")

	challenge = finding.get("challenge")
	if challenge:
		lines.append(f"**Challenge:** {challenge}")

	challenge_id = finding.get("challenge_id")
	if challenge_id not in (None, ""):
		lines.append(f"**Challenge ID:** {challenge_id}")

	url = finding.get("url")
	if url:
		lines.append(f"**GameBus Studio URL:** {url}")

	lines.append("")
	lines.append(
		"This identifies the highest-priority finding. "
		"Ask `How do I fix this finding?` if you want the GameBus Studio repair steps."
	)

	return "\n".join(lines)


def _finding_brief_lines(finding: dict[str, Any]) -> list[str]:
	title = finding.get("title") or finding.get("message") or "Finding"
	check = finding.get("check") or "unknown"
	severity = finding.get("severity") or "unknown"

	lines = [
		f"**Finding:** {title}",
		f"**Check:** `{check}`",
		f"**Severity:** `{severity}`",
	]

	visualization = finding.get("visualization")
	if visualization:
		lines.append(f"**Visualization:** {visualization}")

	challenge = finding.get("challenge")
	if challenge:
		lines.append(f"**Challenge:** {challenge}")

	challenge_id = finding.get("challenge_id")
	if challenge_id not in (None, ""):
		lines.append(f"**Challenge ID:** {challenge_id}")

	url = finding.get("url")
	if url:
		lines.append(f"**GameBus Studio URL:** {url}")

	return lines


def _quick_summary_answer(context: dict[str, Any]) -> str:
	answer = _issue_summary_answer("Summarize the issues", context)
	if answer:
		return answer
	return "No issue summary is available in the current context."


def _quick_inspect_first_answer(context: dict[str, Any]) -> str:
	top_findings = context.get("top_findings", []) or []

	if not top_findings:
		return "No prioritized findings are available in the current context."

	finding = top_findings[0]
	title = finding.get("title") or finding.get("message") or "Finding"
	check = finding.get("check") or "unknown"
	severity = finding.get("severity") or "unknown"

	lines = [
		"Start with the highest-priority finding:",
		"",
		*_finding_brief_lines(finding),
		"",
		"**Why this first:**",
		(
			"This item appears first in the prioritized checker output. "
			f"It has severity `{severity}` and belongs to the `{check}` check."
		),
		"",
		"Ask `How do I fix this?` if you want the deterministic GameBus Studio repair guidance.",
	]

	return "\n".join(lines)


def _priority_reason_answer(context: dict[str, Any]) -> str:
	top_findings = context.get("top_findings", []) or []

	if not top_findings:
		return "No prioritized findings are available in the current context."

	finding = top_findings[0]
	check = finding.get("check") or "unknown"
	severity = finding.get("severity") or "unknown"
	rationale = finding.get("priority_rationale")

	lines = [
		"These issues are ordered by the deterministic priority score.",
		"",
		f"The first item is first because it has severity `{severity}` and belongs to the `{check}` check.",
	]

	if rationale:
		lines.append(f"Priority rationale from the checker: {rationale}")

	lines.extend(
		[
			"",
			"In general:",
			"- High-severity findings come before medium- and low-severity findings.",
			"- Findings in an active wave may receive a small boost.",
			"- This does not mean the first issue is the only issue to fix; it is simply the first one to inspect.",
		]
	)

	return "\n".join(lines)


def _priority_reason_and_guidance_answer(
    question: str,
    context: dict[str, Any],
) -> str | None:
    if not _is_priority_reason_question(question):
        return None

    if not _is_deterministic_guidance_question(question):
        return None

    reason_answer = _priority_reason_answer(context)
    guidance_answer = _deterministic_guidance_answer(question, context)

    if not guidance_answer:
        return reason_answer

    return "\n\n".join(
        [
            reason_answer,
            "---",
            guidance_answer,
        ]
    )



def _issue_type_key(finding: dict[str, Any]) -> tuple[str, str]:
	"""Group repeated findings that represent the same issue type.

	We intentionally ignore visualization/challenge/id fields here, because the
	same structural problem may appear in several campaign elements.

	The key is semantic enough to collapse repeated issue types such as:
	- many `secrets` findings with different task names;
	- many reachability findings with different challenge names;
	- many target-point findings with different level names.
	"""
	check = _normalized(finding.get("check") or "unknown")
	text = _normalized(
		" ".join(
			[
				str(finding.get("title") or ""),
				str(finding.get("message") or ""),
			]
		)
	)

	if check == "secrets":
		if "same secret" in text or "secret" in text:
			return check, "same_secret_different_task_names"
		return check, "secret_configuration_issue"

	if check == "reachability":
		if "not reachable" in text:
			return check, "challenge_not_reachable"
		if "cycle" in text or "cyclic" in text:
			return check, "cyclic_reachability"
		return check, "reachability_issue"

	if check == "targetpointsreachable":
		if "no target points" in text or "target points" in text:
			return check, "target_points_missing_or_unreachable"
		return check, "target_points_issue"

	if check == "visualizationintern":
		return check, "visualization_internal_reference_issue"

	if check == "consistency":
		return check, "campaign_consistency_issue"

	title = _normalized(finding.get("title") or finding.get("message") or "finding")
	return check, title


def _issue_type_display_title(finding: dict[str, Any]) -> str:
	check, category = _issue_type_key(finding)

	if check == "secrets" and category == "same_secret_different_task_names":
		return "Task secret reused with different task names"

	if check == "reachability" and category == "challenge_not_reachable":
		return "Challenge not reachable from the configured progression"

	if check == "reachability" and category == "cyclic_reachability":
		return "Cyclic reachability structure"

	if check == "targetpointsreachable" and category == "target_points_missing_or_unreachable":
		return "Target points missing or not reachable"

	if check == "visualizationintern":
		return "Visualization internal reference issue"

	if check == "consistency":
		return "Campaign consistency issue"

	return str(finding.get("title") or finding.get("message") or "Finding")


def _top_unique_issue_type_findings(
		findings: list[dict[str, Any]],
		*,
		limit: int = 5,
) -> list[tuple[dict[str, Any], int]]:
	"""Return up to `limit` unique issue types from the prioritized findings.

	The returned count is how often the same issue type occurs in the inspected
	top slice. This lets the answer say when several top findings are the same
	type of problem.
	"""
	top_slice = [
		finding
		for finding in findings[:limit]
		if isinstance(finding, dict)
	]

	counts: dict[tuple[str, str], int] = {}
	first_by_key: dict[tuple[str, str], dict[str, Any]] = {}

	for finding in top_slice:
		key = _issue_type_key(finding)
		counts[key] = counts.get(key, 0) + 1
		first_by_key.setdefault(key, finding)

	return [
		(first_by_key[key], counts[key])
		for key in first_by_key
	]


def _simple_issue_explanation(finding: dict[str, Any]) -> str:
	check = _normalized(finding.get("check") or "")
	title = _normalized(finding.get("title") or finding.get("message") or "")

	if check == "reachability" and "not reachable" in title:
		return (
			"In simple terms, the campaign contains a challenge that looks like it should be reachable, "
			"but the configured progression does not provide a path for participants to get there."
		)

	if check == "targetpointsreachable" and "target points" in title:
		return (
			"In simple terms, this level uses point-target progression, but the required target points "
			"are missing or cannot be reached reliably from the configured tasks and transitions."
		)

	if check == "secrets":
		return (
			"In simple terms, some task secrets appear to be reused or inconsistent. "
			"This can make it unclear whether copied tasks are intentionally the same action "
			"or accidentally mixed up."
		)

	if check == "visualizationintern":
		return (
			"In simple terms, something inside the visualization setup is internally inconsistent, "
			"for example a broken reference between campaign elements."
		)

	if check == "consistency":
		return (
			"In simple terms, the checker found a structural inconsistency in the campaign export. "
			"This usually means two related campaign elements do not agree with each other."
		)

	explanation = check_explanation(str(finding.get("check") or ""))
	if explanation:
		first_sentence = explanation.split(". ")[0].strip()
		return first_sentence + "."

	return (
		"In simple terms, the checker found a campaign structure issue that should be inspected "
		"before editing or translating the campaign further."
	)


def _quick_explain_top_findings_answer(context: dict[str, Any]) -> str:
	top_findings = context.get("top_findings", []) or []

	if not top_findings:
		return "No prioritized findings are available in the current context."

	unique_findings = _top_unique_issue_type_findings(top_findings, limit=5)

	lines = [
		"Highest-priority finding types:",
		"",
		(
			"These are explanations of the top prioritized findings in simple terms. "
			"If several top findings are the same issue type, they are explained only once."
		),
	]

	for idx, (finding, duplicate_count) in enumerate(unique_findings, start=1):
		raw_title = str(finding.get("title") or finding.get("message") or "Finding")
		title = _issue_type_display_title(finding)
		check = finding.get("check") or "unknown"
		severity = finding.get("severity") or "unknown"

		lines.extend(
			[
				"",
				f"### {idx}. {title}",
				"",
				f"**Check:** `{check}`",
				f"**Severity:** `{severity}`",
			]
		)

		if raw_title != title:
			lines.append(f"**Example finding:** {raw_title}")

		if duplicate_count > 1:
			lines.append(
				f"**Repeated in top findings:** {duplicate_count} similar findings of this issue type."
			)

		visualization = finding.get("visualization")
		if visualization:
			lines.append(f"**Example visualization:** {visualization}")

		challenge = finding.get("challenge")
		if challenge:
			lines.append(f"**Example challenge:** {challenge}")

		lines.extend(
			[
				"",
				"**What this means:**",
				_simple_issue_explanation(finding),
				"",
				"**Why it matters:**",
				(
					"If this finding is valid, it may affect whether participants can progress through "
					"the campaign as intended, whether points are awarded correctly, or whether campaign "
					"editors can safely maintain the campaign."
				),
			]
		)

	lines.extend(
		[
			"",
			"Ask `How do I fix this?` from a selected finding if you want exact GameBus Studio repair guidance.",
		]
	)

	return "\n".join(lines)


def _quick_explain_top_finding_answer(context: dict[str, Any]) -> str:
	"""Backward-compatible wrapper for older tests or saved quick-action names."""
	return _quick_explain_top_findings_answer(context)


def _quick_clean_result_answer(context: dict[str, Any]) -> str:
	return (
		"The selected deterministic checks did not report issues. "
		"This means the checked structural rules passed for this export. "
		"It does not prove that the campaign is complete, effective, theory-aligned, "
		"or free of content/design problems outside the selected checks."
	)


def _quick_all_checks_answer() -> str:
	answer = _all_checks_explanation_answer("Which checks were run?")
	if answer:
		return answer
	return "No check explanations are available."



def _fallback_without_llm(question: str, context: dict[str, Any]) -> str:
	"""Return a useful deterministic answer when LLM support is unavailable.

	This fallback must not invent explanations. It can only summarize checker
	facts and reuse deterministic GameBus Studio guidance already stored in the
	context by context_builder.
	"""
	analysis = context.get("analysis", {}) or {}
	top_findings = context.get("top_findings", []) or []
	structure = context.get("campaign_structure", {}) or {}
	counts = structure.get("counts", {}) or {}

	total = analysis.get("total_issues", 0)
	failed_checks = analysis.get("failed_checks", []) or []
	severity_counts = analysis.get("severity_counts", {}) or {}
	issue_count_by_check = analysis.get("issue_count_by_check", {}) or {}

	lines = [
		"Using deterministic checker-based guidance for this answer.",
		"",
		f"The selected checks found **{total}** issue(s).",
	]

	if severity_counts:
		severity_parts = [
			f"{severity}: {count}"
			for severity, count in severity_counts.items()
			if count
		]
		if severity_parts:
			lines.append("Severity counts: " + ", ".join(severity_parts) + ".")

	if failed_checks:
		lines.append(
			"Checks with findings: "
			+ ", ".join(f"`{check}`" for check in failed_checks)
			+ "."
		)
	else:
		lines.append("No failed checks were reported.")

	if issue_count_by_check:
		lines.append("")
		lines.append("Issue counts by check:")
		for check, count in issue_count_by_check.items():
			lines.append(f"- `{check}`: {count}")

	if counts:
		lines.append("")
		lines.append("Campaign structure:")
		lines.append(f"- Waves: {counts.get('waves', 0)}")
		lines.append(f"- Visualizations: {counts.get('visualizations', 0)}")
		lines.append(f"- Challenges/levels: {counts.get('challenges', 0)}")
		lines.append(f"- Tasks: {counts.get('tasks', 0)}")
		lines.append(f"- Transitions: {counts.get('transitions', 0)}")

	if not top_findings:
		lines.append("")
		lines.append("No prioritized findings are available in the current context.")
		return "\n".join(lines)

	lines.append("")
	lines.append("Top findings to inspect:")
	for idx, finding in enumerate(top_findings[:5], start=1):
		title = finding.get("title") or "Finding"
		check = finding.get("check") or "unknown"
		severity = finding.get("severity") or "unknown"
		lines.append(f"{idx}. [{severity}] {title} (check: `{check}`)")

		visualization = finding.get("visualization")
		if visualization:
			lines.append(f"   - Visualization: {visualization}")

		challenge = finding.get("challenge")
		if challenge:
			lines.append(f"   - Challenge: {challenge}")

		url = finding.get("url")
		if url:
			lines.append(f"   - GameBus Studio URL: {url}")

	highest = top_findings[0]
	guidance = highest.get("deterministic_gamebus_fix_guidance")
	wants_fix_guidance = _is_deterministic_guidance_question(question)

	if guidance and wants_fix_guidance:
		lines.append("")
		lines.append("Deterministic guidance for the highest-priority finding:")
		lines.append(str(guidance))

		source_facts = highest.get("gamebus_studio_source_facts")
		if source_facts:
			lines.append("")
			lines.append("Relevant GameBus Studio facts:")
			lines.append(str(source_facts))
	elif guidance:
		lines.append("")
		lines.append(
			"Ask `How do I fix the highest-priority finding?` "
			"or `How do I fix the secrets issues?` to see the step-by-step fix guidance."
		)
	else:
		lines.append("")
		lines.append(
			"No deterministic GameBus Studio guidance is available for the highest-priority finding."
		)

	return "\n".join(lines)


def _campaign_structure_answer(question: str, context: dict[str, Any]) -> str | None:
	normalized = _normalized(question)

	if "campaign structure" not in normalized and "structure of the campaign" not in normalized:
		return None

	structure = context.get("campaign_structure", {}) or {}
	counts = structure.get("counts", {}) or {}

	if not counts:
		return "No campaign structure snapshot is available in the current context."

	lines = [
		"Campaign structure:",
		"",
		f"- Waves: {counts.get('waves', 0)}",
		f"- Visualizations: {counts.get('visualizations', 0)}",
		f"- Challenges/levels: {counts.get('challenges', 0)}",
		f"- Tasks: {counts.get('tasks', 0)}",
		f"- Transitions: {counts.get('transitions', 0)}",
	]

	return "\n".join(lines)



def _format_conversation_history(history: list[dict[str, str]] | None) -> str:
	if not history:
		return "No previous conversation messages are available."

	recent = history[-6:]
	lines = []
	for item in recent:
		role = item.get("role", "unknown")
		content = str(item.get("content", "")).strip()
		if content:
			lines.append(f"{role}: {content}")
	return "\n".join(lines)



def _llm_campaign_answer(
		*,
		llm_client: LLMClient,
		question: str,
		context: dict[str, Any],
		conversation_history: list[dict[str, str]] | None = None,
) -> str | None:
	context_markdown = format_llm_context_markdown(context)

	field_facts = gamebus_studio_field_facts_markdown_for_question(question)
	if field_facts:
		context_markdown = "\n\n".join(
			[
				context_markdown,
				"# Relevant GameBus Studio field facts for this question",
				field_facts,
			]
		)

	conversation_text = _format_conversation_history(conversation_history)

	user_prompt = f"""
    Recent conversation:
    {conversation_text}

    Current user question:
    {question}

    Available checker/campaign context:
    {context_markdown}

    Answer the current question using the recent conversation and available campaign/checker context.

    Important:
    - If the current question says "this", "it", "that issue", or asks to make something shorter, use the recent conversation to identify the referent.
    - If the referent is still unclear, say you are not sure and suggest a clearer question.
    - Do not summarize the whole campaign unless the user asks for a summary or overview.
    """

	response = llm_client.generate(
		system_prompt=CAMPAIGN_SUPPORT_SYSTEM_PROMPT.strip(),
		user_prompt=user_prompt.strip(),
		temperature=0.2,
	)

	if not response.available:
		return None

	answer = response.text.strip()

	if _is_weak_llm_answer(answer):
		return None

	return answer


class CampaignSupportAgent(BaseAgent):
	name = "campaign_support_agent"

	def __init__(self, llm_client: LLMClient | None = None):
		self.llm_client = llm_client

	def run_quick_action(
			self,
			*,
			quick_action: str,
			context: dict[str, Any],
	) -> str:
		if quick_action == "summarize_issues":
			return _quick_summary_answer(context)

		if quick_action == "campaign_structure":
			answer = _campaign_structure_answer("What is the campaign structure?", context)
			if answer:
				return answer
			return "No campaign structure snapshot is available in the current context."

		if quick_action == "inspect_first":
			return _quick_inspect_first_answer(context)

		if quick_action in {"explain_top_finding", "explain_top_findings"}:
			return _quick_explain_top_findings_answer(context)

		if quick_action == "prioritization":
			return _prioritization_answer()

		if quick_action == "all_checks":
			return _quick_all_checks_answer()

		if quick_action == "clean_result":
			return _quick_clean_result_answer(context)

		return uncertainty_response(
			"I am not sure which quick action was requested. "
			"Try asking about findings, fix guidance, campaign structure, or theory alignment."
		)

	def run(
			self,
			*,
			question: str,
			context: dict[str, Any],
			conversation_history: list[dict[str, str]] | None = None,
	) -> str:
		if _is_acknowledgement(question):
			return (
				"You’re welcome. Ask about a specific finding, fix guidance, "
				"campaign structure, or theory alignment when you want to continue."
			)

		prepared_finding_answer = explain_prepared_finding(question)
		if prepared_finding_answer is not None:
			return prepared_finding_answer

		if _total_issues_from_context(context) == 0 and _is_fix_or_inspection_question(question):
			return _clean_result_fix_answer(context)

		combined_priority_fix_answer = _priority_reason_and_guidance_answer(question, context)
		if combined_priority_fix_answer:
			return combined_priority_fix_answer

		if _is_prioritization_question(question):
			return _prioritization_answer()

		if _is_priority_reason_question(question):
			return _priority_reason_answer(context)

		structure_answer = _campaign_structure_answer(question, context)
		if structure_answer:
			return structure_answer

		deterministic_answer = _deterministic_guidance_answer(question, context)
		if deterministic_answer:
			return deterministic_answer

		check_answer = _check_explanation_answer(question)
		if check_answer:
			return check_answer

		all_checks_answer = _all_checks_explanation_answer(question)
		if all_checks_answer:
			return all_checks_answer

		# Explicit summary/overview requests should stay deterministic and fast.
		issue_summary = _issue_summary_answer(question, context)
		if issue_summary:
			return issue_summary

		# LLM handles explanation, synthesis, rewriting, and follow-up interpretation.
		if self.llm_client is not None:
			llm_answer = _llm_campaign_answer(
				llm_client=self.llm_client,
				question=question,
				context=context,
				conversation_history=conversation_history,
			)
			if llm_answer:
				return llm_answer

		highest_priority_answer = _highest_priority_finding_answer(question, context)
		if highest_priority_answer:
			return highest_priority_answer

		return uncertainty_response(question)
