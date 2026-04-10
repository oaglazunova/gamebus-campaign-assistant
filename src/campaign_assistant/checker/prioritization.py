from __future__ import annotations

from campaign_assistant.checker.schema import Issue

SEVERITY_SCORE = {
    "high": 300,
    "medium": 200,
    "low": 100,
}


def issue_priority_score(issue: Issue) -> int:
    """
    Compute a simple priority score for an issue.

    Higher score means higher priority.

    Current logic:
    - severity is the main driver
    - issues in an active wave get an extra boost
    """
    score = SEVERITY_SCORE.get(issue.severity, 0)

    if issue.active_wave:
        score += 50

    return score