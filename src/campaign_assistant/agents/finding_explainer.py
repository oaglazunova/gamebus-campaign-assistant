from __future__ import annotations

import re


_FIELD_NAMES = [
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
        value = " ".join(match.group(2).strip().split())
        parsed[key] = value

    return parsed


def is_prepared_finding_question(question: str) -> bool:
    parsed = _parse_prepared_finding_question(question)
    return bool(parsed.get("check") and parsed.get("finding"))


def explain_prepared_finding(question: str) -> str | None:
    parsed = _parse_prepared_finding_question(question)

    check = parsed.get("check")
    finding = parsed.get("finding")
    severity = parsed.get("severity", "unknown")
    visualization = parsed.get("visualization")
    challenge = parsed.get("challenge")
    challenge_id = parsed.get("challenge id")
    wave_id = parsed.get("wave id")

    if not check or not finding:
        return None

    check_normalized = check.lower().strip()

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

    lines.append("")
    lines.append("**What this means:**")

    if check_normalized == "secrets":
        lines.append(
            "This finding means that copied or related tasks use the same secret value, "
            "but their task names differ. In GameBus, a secret is often used to identify "
            "or validate a task/action. If the same secret is reused for tasks with different "
            "names, it may be unclear whether these are intentionally the same action or "
            "accidentally inconsistent copies."
        )
        lines.append("")
        lines.append("**What to inspect next:**")
        lines.append(
            "1. Open the listed challenges and compare the tasks that use this secret."
        )
        lines.append(
            "2. Check whether the different task names are intentional translations/variants "
            "or accidental copy inconsistencies."
        )
        lines.append(
            "3. If they are meant to be the same task, align the task names or document the naming convention."
        )
        lines.append(
            "4. If they are meant to be different tasks, consider using distinct secrets so they are not confused."
        )

    elif check_normalized == "reachability":
        lines.append(
            "This finding means that the checker detected a progression or navigation problem: "
            "a level/challenge may not be reachable from the initial campaign path."
        )
        lines.append("")
        lines.append("**What to inspect next:**")
        lines.append("1. Inspect the source and target challenges involved in the finding.")
        lines.append("2. Check the success and failure transitions.")
        lines.append("3. Verify whether the level should be reachable in the active campaign flow.")

    elif check_normalized == "targetpointsreachable":
        lines.append(
            "This finding means that the target-points logic for a challenge may be impossible, "
            "undefined, or inconsistent with the available tasks."
        )
        lines.append("")
        lines.append("**What to inspect next:**")
        lines.append("1. Check the challenge target points.")
        lines.append("2. Check the points available from tasks in that challenge.")
        lines.append("3. Verify whether the participant can realistically reach the target.")

    elif check_normalized == "visualizationintern":
        lines.append(
            "This finding means that something inside a visualization may be structurally inconsistent, "
            "for example links between levels, labels, or challenge placement inside the visualization."
        )
        lines.append("")
        lines.append("**What to inspect next:**")
        lines.append("1. Open the named visualization.")
        lines.append("2. Inspect the listed challenge and its neighboring levels.")
        lines.append("3. Check whether the visualization structure matches the intended campaign flow.")

    elif check_normalized == "consistency":
        lines.append(
            "This finding means that the checker detected an internal inconsistency in the campaign export."
        )
        lines.append("")
        lines.append("**What to inspect next:**")
        lines.append("1. Inspect the affected campaign element.")
        lines.append("2. Compare the referenced IDs, names, and linked objects.")
        lines.append("3. Check whether the inconsistency is intentional or should be corrected.")

    elif check_normalized == "spellchecker":
        lines.append(
            "This finding means that the checker detected text that may contain a spelling or wording issue."
        )
        lines.append("")
        lines.append("**What to inspect next:**")
        lines.append("1. Review the exact text in the campaign export.")
        lines.append("2. Check whether it is a real spelling issue, a proper name, or acceptable domain-specific wording.")

    else:
        lines.append(
            "This finding indicates that the selected checker detected a potential campaign-configuration issue."
        )
        lines.append("")
        lines.append("**What to inspect next:**")
        lines.append("1. Inspect the campaign element named in the finding.")
        lines.append("2. Compare it with neighboring or copied elements.")
        lines.append("3. Decide whether the configuration is intentional or should be corrected.")

    lines.append("")
    lines.append(
        "I would not infer unrelated issues from other checks unless they are shown as separate findings."
    )

    return "\n".join(lines)