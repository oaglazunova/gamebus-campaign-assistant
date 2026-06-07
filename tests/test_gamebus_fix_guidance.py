from campaign_assistant.checker.gamebus_fix_guidance import (
    checks_with_gamebus_fix_guidance,
    gamebus_fix_guidance_markdown_for_issue,
    get_gamebus_fix_guidance,
)
from campaign_assistant.checker.schema import DEFAULT_CHECKS, TARGETPOINTSREACHABLE


def test_guidance_exists_for_all_default_checks():
    assert set(DEFAULT_CHECKS).issubset(checks_with_gamebus_fix_guidance())


def test_target_points_guidance_mentions_editor_fields():
    guidance = get_gamebus_fix_guidance(TARGETPOINTSREACHABLE)

    assert guidance is not None
    text = guidance.as_markdown()

    assert "Target points" in text
    assert "Evaluate failure interval" in text
    assert "Reward count" in text
    assert "Time window for resetting the reward count" in text
    assert "Number of points to award" in text


def test_issue_guidance_unknown_check_is_empty():
    assert gamebus_fix_guidance_markdown_for_issue({"check": "unknown"}) == ""


def test_secrets_missing_secret_gets_specific_guidance():
    text = gamebus_fix_guidance_markdown_for_issue(
        {
            "check": "secrets",
            "message": "Task 'Drink water' has no secret. Proposing [SECRET, EQUAL, Drink-water]",
        }
    )

    assert "Add a missing secret condition to this task" in text
    assert "Conditions → Property. Set this to SECRET." in text
    assert "Conditions → Operator. Set this to EQUAL." in text
    assert "Fix missing or conflicting task secrets" not in text


def test_reachability_initial_gets_specific_guidance():
    text = gamebus_fix_guidance_markdown_for_issue(
        {
            "check": "reachability",
            "message": "Initial Challenge without terminal challenge",
        }
    )

    assert "Connect this initial level to a terminal success path" in text
    assert "Next level when target is met on time" in text
    assert "Use this level as the start of the level structure" in text
    assert "Fix unreachable start or terminal levels" not in text


def test_target_points_missing_values_gets_specific_guidance():
    text = gamebus_fix_guidance_markdown_for_issue(
        {
            "check": "targetpointsreachable",
            "message": "Challenge reachable points (None) cannot be computed, missing values in tasks.",
        }
    )

    assert "Fill missing numeric values needed for target-point calculation" in text
    assert "Target points" in text
    assert "Evaluate failure interval" in text
    assert "Time window for resetting the reward count" in text
    assert "greater than zero" in text
    assert "Fix unreachable target points" not in text


def test_specific_guidance_replaces_generic_guidance_for_terminal_reachability():
    text = gamebus_fix_guidance_markdown_for_issue(
        {
            "check": "reachability",
            "message": "Terminal Challenge not reachable from any initial challenge",
        }
    )

    assert "Connect this terminal level to an initial success path" in text
    assert "Next level when target is met on time" in text
    assert "Use this level as the start of the level structure" in text
    assert "success transitions" in text
    assert "Fix unreachable start or terminal levels" not in text
    assert "Target points" not in text


def test_generic_guidance_is_used_when_issue_subtype_is_unknown():
    text = gamebus_fix_guidance_markdown_for_issue(
        {
            "check": "reachability",
            "message": "Some future reachability message we do not recognize yet",
        }
    )

    assert "Fix unreachable start or terminal levels" in text
    assert "Next level when target is met on time" in text