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
        "The current TTM check assumes an HW8-style long-term progression shape: several initial non-relapse levels (in this implementation - 4) should fail back to themselves, followed by relapse-aware levels with separate at-risk levels. It checks transition structure, not formal TTM theory alignment or exact level names."
    )