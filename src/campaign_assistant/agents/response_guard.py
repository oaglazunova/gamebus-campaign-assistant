from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from campaign_assistant.agents.intent_router import RoutedIntent
from campaign_assistant.agents.question_types import (
    is_outcome_question,
)


@dataclass
class GuardResult:
    safe: bool
    reason: str | None = None
    replacement_text: str | None = None


_CHECKER_PROBLEM_PATTERNS = [
    r"\bchecker found (several|some|multiple|many|potential)?\s*(issues|problems|errors|warnings|inconsistencies)\b",
    r"\bthe checker found\b.*\b(issues|problems|errors|warnings|inconsistencies)\b",
    r"\bchecks? found\b.*\b(issues|problems|errors|warnings|inconsistencies)\b",
    r"\bfailed checks?\b",
    r"\btargetpointsreachable issue\b",
    r"\breachability issue\b",
    r"\bconsistency issue\b",
    r"\bvisualizationintern issue\b",
    r"\bspellchecker issue\b",
    r"\bsecrets issue\b",
    r"\bseveral inconsistencies\b",
    r"\bseveral potential issues\b",
]

_CHECK_NAMES = [
    "secrets",
    "spellchecker",
    "reachability",
    "consistency",
    "visualizationintern",
    "targetpointsreachable",
]

_STRONG_OUTCOME_CLAIM_PATTERNS = [
    r"\bwill (help|cause|lead to|produce)\b.*\b(weight loss|lose weight|health outcome|improvement)\b",
    r"\bwill be effective\b",
    r"\bis effective\b",
    r"\bwill work\b",
    r"\bwill help people lose weight\b",
]

_UNSUPPORTED_THEORY_CLAIM_PATTERNS = [
    r"\b(definitely|clearly|formally) (follows|implements|is based on|uses) (ttm|com-b|comb|bct)\b",
    r"\bthis campaign (follows|implements|is based on) (ttm|com-b|comb)\b",
    r"\bappears to (focus on|be based on|follow|align with)\b.*\bttm\b",
    r"\baligns with the principles of\b.*\bttm\b",
    r"\bconsistent with\b.*\bttm\b",
    r"\bwaves\b.*\b(key element|important element|core element)\b.*\bttm\b",
    r"\bvisualizations\b.*\b(key element|important element|core element)\b.*\bttm\b",
    r"\bprogression through stages\b",
]




def _lower(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _matches_any(text: str, patterns: list[str]) -> bool:
    normalized = _lower(text)
    return any(re.search(pattern, normalized) for pattern in patterns)


def _clean_checker_result_replacement(question: str, facts: dict[str, Any]) -> str:
    checker = facts.get("checker_facts", {}) or {}
    export = facts.get("export_facts", {}) or {}
    counts = (export.get("counts", {}) or {})

    checks_run = checker.get("checks_run", []) or []

    lines = [
        "The selected deterministic checks found **0 issues**.",
        "",
        "There is no checker finding to fix or inspect first.",
        "",
        "This does **not** prove that the campaign is optimal, theory-aligned, "
        "or effective for health outcomes. It only means the selected export-level "
        "checks did not detect problems.",
    ]

    if checks_run:
        lines.append("")
        lines.append(
            "Checks run: " + ", ".join(f"`{check}`" for check in checks_run) + "."
        )

    if counts:
        lines.append("")
        lines.append("Campaign structure:")
        lines.append(f"- Waves: {counts.get('waves', 0)}")
        lines.append(f"- Visualizations: {counts.get('visualizations', 0)}")
        lines.append(f"- Challenges/levels: {counts.get('challenges', 0)}")
        lines.append(f"- Tasks: {counts.get('tasks', 0)}")
        lines.append(f"- Transitions: {counts.get('transitions', 0)}")

    lines.append("")
    lines.append(
        "For further review, inspect task clarity, participant burden, behavior specificity, "
        "progression logic, and theory alignment. Those are advisory design questions, "
        "not deterministic checker findings."
    )

    return "\n".join(lines)


def _outcome_replacement(question: str, facts: dict[str, Any]) -> str:
    export = facts.get("export_facts", {}) or {}
    counts = (export.get("counts", {}) or {})

    lines = [
        "This is advisory theory-oriented feedback, not formal validation.",
        "",
        "The campaign export and checker output cannot determine whether the campaign "
        "will cause weight loss or other health outcomes. That requires intervention "
        "content review and empirical evaluation.",
        "",
        "From the current export, I can only comment on visible design features, such as "
        "campaign structure, tasks, progression, feedback/reward opportunities, and possible "
        "behavior-change mechanisms.",
    ]

    if counts:
        lines.append("")
        lines.append("Visible campaign structure:")
        lines.append(f"- Waves: {counts.get('waves', 0)}")
        lines.append(f"- Visualizations: {counts.get('visualizations', 0)}")
        lines.append(f"- Challenges/levels: {counts.get('challenges', 0)}")
        lines.append(f"- Tasks: {counts.get('tasks', 0)}")
        lines.append(f"- Transitions: {counts.get('transitions', 0)}")

    lines.append("")
    lines.append(
        "To assess likely effectiveness, you would need the intervention rationale, "
        "target population, behavior-change techniques, intended outcomes, and evaluation data."
    )

    return "\n".join(lines)


def _unsupported_theory_replacement(question: str, facts: dict[str, Any]) -> str:
    return (
        "This is advisory theory-oriented feedback, not formal validation.\n\n"
        "The available context is not sufficient to conclude that the campaign formally "
        "follows or implements a specific behavior-change theory. I can discuss possible "
        "alignment signals and useful design improvements, but I should not treat waves, "
        "visualizations, levels, or task counts as proof of TTM, COM-B, or BCT implementation."
    )


def _claims_issue_for_non_failed_check(answer: str, facts: dict[str, Any]) -> str | None:
    checker = facts.get("checker_facts", {}) or {}

    allowed_problem_checks = set(
        str(item).lower() for item in checker.get("failed_checks", []) or []
    )
    allowed_problem_checks.update(
        str(item).lower() for item in checker.get("errored_checks", []) or []
    )

    issue_count_by_check = checker.get("issue_count_by_check", {}) or {}
    for check, count in issue_count_by_check.items():
        if int(count or 0) > 0:
            allowed_problem_checks.add(str(check).lower())

    answer_lower = _lower(answer)

    problem_words = [
        "issue",
        "issues",
        "problem",
        "problems",
        "error",
        "errors",
        "warning",
        "warnings",
        "inconsistency",
        "inconsistencies",
        "challenge",
        "challenges",
    ]

    for check_name in _CHECK_NAMES:
        if check_name in allowed_problem_checks:
            continue

        if check_name not in answer_lower:
            continue

        # Detect claims such as "reachability issue", "reachability challenges",
        # "issue with reachability", "problems in reachability".
        problem_group = "|".join(re.escape(word) for word in problem_words)

        direct_pattern = rf"\b{re.escape(check_name)}\b[\s\S]{{0,120}}\b({problem_group})\b"
        reverse_pattern = rf"\b({problem_group})\b[\s\S]{{0,120}}\b{re.escape(check_name)}\b"

        if re.search(direct_pattern, answer_lower) or re.search(reverse_pattern, answer_lower):
            return check_name

    return None


def _checker_specific_replacement(
    question: str,
    facts: dict[str, Any],
    unsupported_check: str,
) -> str:
    checker = facts.get("checker_facts", {}) or {}
    export = facts.get("export_facts", {}) or {}
    counts = export.get("counts", {}) or {}

    failed_checks = checker.get("failed_checks", []) or []
    errored_checks = checker.get("errored_checks", []) or []
    known_findings = checker.get("known_findings", []) or []

    lines = [
        "I should not describe a check as having issues unless that appears in the deterministic checker output.",
        "",
        f"In the current result, `{unsupported_check}` is not listed as a failed or errored check.",
    ]

    if failed_checks:
        lines.append("")
        lines.append(
            "Failed checks: " + ", ".join(f"`{check}`" for check in failed_checks) + "."
        )

    if errored_checks:
        lines.append(
            "Errored checks: " + ", ".join(f"`{check}`" for check in errored_checks) + "."
        )

    if known_findings:
        lines.append("")
        lines.append("Start with the known checker findings:")
        for idx, finding in enumerate(known_findings[:5], start=1):
            title = finding.get("title") or "Finding"
            check = finding.get("check") or "unknown"
            severity = finding.get("severity") or "unknown"
            lines.append(f"{idx}. [{severity}] {title} (check: `{check}`)")

    if counts:
        lines.append("")
        lines.append("Campaign structure:")
        lines.append(f"- Waves: {counts.get('waves', 0)}")
        lines.append(f"- Visualizations: {counts.get('visualizations', 0)}")
        lines.append(f"- Challenges/levels: {counts.get('challenges', 0)}")
        lines.append(f"- Tasks: {counts.get('tasks', 0)}")
        lines.append(f"- Transitions: {counts.get('transitions', 0)}")

    lines.append("")
    lines.append(
        "Use the Findings page to inspect the failed checks and their specific messages."
    )

    return "\n".join(lines)


def validate_agent_response(
    *,
    question: str,
    answer: str,
    facts: dict[str, Any],
    route: RoutedIntent,
) -> GuardResult:
    checker = facts.get("checker_facts", {}) or {}
    total_issues = int(checker.get("total_issues", 0) or 0)

    # Guard 1: no invented checker findings for a clean checker result.
    if total_issues == 0 and _matches_any(answer, _CHECKER_PROBLEM_PATTERNS):
        return GuardResult(
            safe=False,
            reason="contradicts_clean_checker_result",
            replacement_text=_clean_checker_result_replacement(question, facts),
        )


    # Guard 1b: do not claim issues for checks that did not fail.
    unsupported_check = _claims_issue_for_non_failed_check(answer, facts)
    if unsupported_check:
        return GuardResult(
            safe=False,
            reason=f"unsupported_check_issue_claim:{unsupported_check}",
            replacement_text=_checker_specific_replacement(question, facts, unsupported_check),

        )

    # Guard 2: no definitive causal outcome/effectiveness claims.
    if is_outcome_question(question) and _matches_any(answer, _STRONG_OUTCOME_CLAIM_PATTERNS):
        return GuardResult(
            safe=False,
            reason="unsupported_outcome_claim",
            replacement_text=_outcome_replacement(question, facts),
        )

    # Guard 3: no definitive theory-alignment claims without explicit design evidence.
    if route.intent == "theory_support" and _matches_any(answer, _UNSUPPORTED_THEORY_CLAIM_PATTERNS):
        return GuardResult(
            safe=False,
            reason="unsupported_theory_alignment_claim",
            replacement_text=_unsupported_theory_replacement(question, facts),
        )

    return GuardResult(safe=True)