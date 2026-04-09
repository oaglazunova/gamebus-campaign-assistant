from __future__ import annotations

from typing import Any, Dict


def summarize_result(result: Dict[str, Any]) -> str:
    """
    Create a short plain-language summary of a campaign check result.
    """
    summary = result.get("summary", {})
    total_issues = summary.get("total_issues", 0)
    failed_checks = summary.get("failed_checks", [])
    passed_checks = summary.get("passed_checks", [])
    errored_checks = summary.get("errored_checks", [])

    waves = result.get("waves", [])
    active_waves = [wave.get("name") for wave in waves if wave.get("active_now")]

    lines = [f"I checked **{result.get('file_name', 'the campaign')}**."]
    lines.append(f"I found **{total_issues}** issue(s).")

    if failed_checks:
        lines.append("Failed checks: " + ", ".join(f"`{name}`" for name in failed_checks) + ".")
    else:
        lines.append("No failed checks were detected.")

    if passed_checks:
        lines.append("Passed checks: " + ", ".join(f"`{name}`" for name in passed_checks) + ".")

    if errored_checks:
        lines.append("Checks with errors: " + ", ".join(f"`{name}`" for name in errored_checks) + ".")

    if active_waves:
        lines.append("Active wave(s): " + ", ".join(f"`{name}`" for name in active_waves) + ".")

    return "\n\n".join(lines)


def explain_ttm() -> str:
    """
    Explain the TTM structure expected by the current checker in plain language.
    """
    return (
        "The current TTM check assumes this progression: "
        "**Newbie → Rookie → Amateur → Proficient → Skilled → Expert → Master → Grandmaster**, "
        "with additional **at-risk / relapse** levels around **Skilled**, **Expert**, and **Master**. "
        "In plain language, the checker verifies that forward progression, relapse behavior, and terminal "
        "levels follow this expected structure. If a TTM issue is reported, it usually means that a level "
        "points to the wrong next level, the wrong fallback level, or breaks the intended progression."
    )