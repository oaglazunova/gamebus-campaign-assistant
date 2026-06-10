from __future__ import annotations

import re


_FIELD_NAMES = [
    "Deterministic GameBus Studio fix guidance",
    "Challenge ID",
    "Wave ID",
    "Check",
    "Severity",
    "Finding",
    "Visualization",
    "Challenge",
]


def _parse_prepared_finding_question(question: str) -> dict[str, str]:
    fields = "|".join(re.escape(name) for name in _FIELD_NAMES)

    pattern = re.compile(
        rf"({fields}):\s*(.*?)(?=\s+(?:{fields}):|$)",
        flags=re.IGNORECASE | re.DOTALL,
    )

    parsed: dict[str, str] = {}

    for match in pattern.finditer(question or ""):
        key = match.group(1).strip().lower()
        raw_value = match.group(2).strip()

        if key == "deterministic gamebus studio fix guidance":
            value = raw_value
        else:
            value = " ".join(raw_value.split())

        parsed[key] = value

    return parsed


def is_prepared_finding_question(question: str) -> bool:
    parsed = _parse_prepared_finding_question(question)
    return bool(parsed.get("check") and parsed.get("finding"))


def _what_this_means(check: str, finding: str) -> str | None:
    check_normalized = " ".join(str(check or "").lower().split())
    finding_normalized = " ".join(str(finding or "").lower().split())

    if check_normalized == "secrets":
        if "has no secret" in finding_normalized:
            return (
                "This finding means that the task does not have a SECRET condition. "
                "In GameBus, a secret is often used to identify or validate a specific task/action. "
                "Without a task-specific secret, the task may be harder to distinguish from other tasks "
                "or may not behave as intended in the campaign logic."
            )

        if "same secret" in finding_normalized or "duplicate" in finding_normalized:
            return (
                "This finding means that copied or related tasks use the same secret value, "
                "but their task names differ. In GameBus, a secret is often used to identify or validate "
                "a task/action. If the same secret is reused for tasks with different names, it may be unclear "
                "whether these are intentionally the same action or accidentally inconsistent copies."
            )

        return (
            "This finding means that the checker found a possible problem with a task SECRET condition. "
            "In GameBus, secrets are often used to identify or validate task-specific actions, so they should "
            "be meaningful, consistent, and unique where needed."
        )

    if check_normalized == "targetpointsreachable":
        if "no target points" in finding_normalized or "target points defined" in finding_normalized:
            return (
                "This finding means that the challenge has no numeric target points configured. "
                "The target-points checker needs this value to determine whether participants can realistically "
                "reach the level target from the available task points."
            )

        if "not reachable" in finding_normalized or "cannot be reached" in finding_normalized:
            return (
                "This finding means that the configured target may be too high for the points available from "
                "the tasks in this challenge. Participants may be unable to reach the level target even if they "
                "complete the available tasks as intended."
            )

        return (
            "This finding means that the target-points logic for a challenge may be impossible, undefined, "
            "or inconsistent with the available tasks."
        )

    if check_normalized == "visualizationintern":
        return (
            "This finding means that following the level transitions from an initial level reaches a terminal "
            "level with a different visualization or label structure than expected. This may indicate that the "
            "progression path crosses into the wrong branch, or that labels/transitions do not match the intended "
            "campaign flow."
        )

    if check_normalized == "reachability":
        if "terminal challenge not reachable" in finding_normalized:
            return (
                "This finding means that a terminal level exists, but no initial level can reach it by following "
                "success transitions. Participants may therefore never arrive at this intended end level."
            )

        if "initial challenge" in finding_normalized and "terminal" in finding_normalized:
            return (
                "This finding means that an initial level does not lead to any terminal level through success "
                "transitions. Participants may get stuck in an incomplete progression path."
            )

        return (
            "This finding means that the success-transition structure may not connect initial and terminal levels "
            "as expected."
        )

    if check_normalized == "consistency":
        return (
            "This finding means that the level transition settings do not match the checker’s expected structural "
            "rules for initial or terminal levels."
        )

    if check_normalized == "ttm":
        return (
            "This finding means that the selected level progression does not match the HW8 long-term-campaign "
            "TTM-like structure expected by this optional checker."
        )

    return None


def explain_prepared_finding(question: str) -> str | None:
    parsed = _parse_prepared_finding_question(question)

    check = parsed.get("check")
    finding = parsed.get("finding")
    severity = parsed.get("severity", "unknown")
    visualization = parsed.get("visualization")
    challenge = parsed.get("challenge")
    challenge_id = parsed.get("challenge id")
    wave_id = parsed.get("wave id")
    guidance = parsed.get("deterministic gamebus studio fix guidance")

    if not check or not finding:
        return None

    lines = [
        "This explanation is based on the selected checker finding.",
        "",
        f"**Check:** `{check}`",
        f"**Severity:** {severity}",
        f"**Finding:** {finding}",
    ]

    location_parts = []
    if visualization:
        location_parts.append(f"visualization **{visualization}**")
    if challenge:
        location_parts.append(f"challenge **{challenge}**")
    if challenge_id:
        location_parts.append(f"challenge ID `{challenge_id}`")
    if wave_id:
        location_parts.append(f"wave ID `{wave_id}`")

    if location_parts:
        lines.append("")
        lines.append("**Location:** " + ", ".join(location_parts) + ".")

    meaning = _what_this_means(check, finding)
    if meaning:
        lines.append("")
        lines.append("**What this means:**")
        lines.append(meaning)

    if guidance:
        lines.append("")
        lines.append("**What to inspect next:**")
        lines.append("")
        lines.append(guidance)
    else:
        lines.append("")
        lines.append("**What to inspect next:**")
        lines.append(
            "Use the finding details above to open the relevant campaign element in GameBus Studio, "
            "then inspect the fields mentioned by the checker."
        )

    lines.append("")
    lines.append(
        "I would not infer unrelated issues from other checks unless they are shown as separate findings."
    )

    return "\n".join(lines)