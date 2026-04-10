from campaign_assistant.checker.prioritization import issue_priority_score
from campaign_assistant.checker.schema import Issue


def make_issue(severity: str, active_wave: bool) -> Issue:
    return Issue(
        check="consistency",
        severity=severity,
        active_wave=active_wave,
        visualization_id=1,
        visualization="Vis",
        challenge_id=2,
        challenge="Challenge",
        wave_id=3,
        message="Some issue",
        url="https://example.com",
    )


def test_high_severity_ranks_above_medium():
    high_issue = make_issue("high", active_wave=False)
    medium_issue = make_issue("medium", active_wave=False)

    assert issue_priority_score(high_issue) > issue_priority_score(medium_issue)


def test_active_wave_boosts_priority():
    inactive_issue = make_issue("medium", active_wave=False)
    active_issue = make_issue("medium", active_wave=True)

    assert issue_priority_score(active_issue) > issue_priority_score(inactive_issue)


def test_unknown_severity_defaults_to_zero_plus_wave_bonus():
    unknown_inactive = make_issue("unknown", active_wave=False)
    unknown_active = make_issue("unknown", active_wave=True)

    assert issue_priority_score(unknown_inactive) == 0
    assert issue_priority_score(unknown_active) == 50