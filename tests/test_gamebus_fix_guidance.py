from campaign_assistant.checker.gamebus_fix_guidance import (
    checks_with_gamebus_fix_guidance,
    gamebus_fix_guidance_markdown_for_issue,
    get_gamebus_fix_guidance,
)
from campaign_assistant.checker.schema import (
    DEFAULT_CHECKS,
    TARGETPOINTSREACHABLE,
    PROGRESSIONBRANCHCONSISTENCY,
)


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
            "message": "Challenge reachable points cannot be computed because required target-point inputs are missing or invalid. Check the challenge evaluation interval and the task point/reward/reset-window values."
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

    assert "Fix unreachable progression levels" in text
    assert "Next level when target is met on time" in text



def test_visualizationintern_same_visualization_different_label_gets_label_guidance():
    text = gamebus_fix_guidance_markdown_for_issue(
        {
            "check": "visualizationintern",
            "message": (
                "Reachable Challenge from some initial level is not in same visualization or not with same label:\n"
                "Initial challenge visualization = '3476'; reachable challenge visualization = '3476'\n"
                "Initial challenge labels = '524.0'; reachable challenge labels = '513.0'\n"
            ),
        }
    )

    assert "different label" in text
    assert "Content editor → Labels" in text
    assert "success and failure transitions" in text
    assert "target points" not in text.lower()


def test_target_points_unreachable_gets_specific_guidance():
    text = gamebus_fix_guidance_markdown_for_issue(
        {
            "check": "targetpointsreachable",
            "message": (
                "Challenge target points (720.0) cannot be reached with tasks "
                "(max reachable is 30.0)"
            ),
        }
    )

    assert "Adjust target points or task rewards" in text
    assert "Target points" in text
    assert "Number of points to award" in text
    assert "Reward count" in text


def test_target_points_missing_target_gets_specific_guidance():
    text = gamebus_fix_guidance_markdown_for_issue(
        {
            "check": "targetpointsreachable",
            "message": "Challenge no target points defined (None).",
        }
    )

    assert "Fill missing target points" in text
    assert "Level settings → Target points" in text


def test_duplicate_secret_gets_specific_guidance():
    text = gamebus_fix_guidance_markdown_for_issue(
        {
            "check": "secrets",
            "message": (
                "Task 'Example task' has copies with the same secret 'example-secret', "
                "but that have different names (see challenges ['1', '2'])"
            ),
        }
    )

    assert "Resolve a duplicate secret" in text
    assert "Conditions → Value" in text
    assert "distinct SECRET value" in text


def test_progression_branch_consistency_guidance_mentions_relevant_level_fields():
    guidance = get_gamebus_fix_guidance(
        PROGRESSIONBRANCHCONSISTENCY
    )

    assert guidance is not None
    text = guidance.as_markdown()

    assert "recovery" in text.lower()
    assert "Next level when target is met on time" in text
    assert "Next level when target is not met on time" in text
    assert "Target points" in text
    assert "previous" in text.lower()
    assert "next normal level" in text.lower()

def test_unreachable_progression_level_gets_specific_guidance():
    text = gamebus_fix_guidance_markdown_for_issue(
        {
            "check": "reachability",
            "message": (
                "Progression level not reachable from any initial challenge. "
                "This level cannot be reached from any configured start level."
            ),
        }
    )

    assert "Connect this unreachable level to the progression" in text
    assert "Next level when target is met on time" in text
    assert "Next level when target is not met on time" in text
    assert "outgoing transitions do not make a level reachable" in text


def test_multiple_secret_conditions_get_specific_guidance():
    text = gamebus_fix_guidance_markdown_for_issue(
        {
            "check": "secrets",
            "message": (
                "Task 'Info-Muncher' contains 2 SECRET conditions: "
                "[SECRET, DIFFERENT, nmbc], "
                "[SECRET, EQUAL, Info-Muncher]."
            ),
        }
    )

    assert "Keep one intended SECRET condition on this task" in text
    assert "Property = SECRET" in text
    assert "Operator = EQUAL" in text
    assert "non-SECRET conditions" in text