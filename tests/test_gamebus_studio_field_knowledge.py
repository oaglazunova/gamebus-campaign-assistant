from campaign_assistant.agents.gamebus_studio_knowledge import (
    gamebus_studio_field_facts_markdown_for_check,
    gamebus_studio_field_facts_markdown_for_question,
    known_gamebus_studio_field_exports,
)


def test_known_field_exports_include_core_checker_fields():
    exports = known_gamebus_studio_field_exports()

    assert "is_initial_level" in exports
    assert "success_next" in exports
    assert "failure_next" in exports
    assert "evaluate_fail_every_x_minutes" in exports
    assert "target" in exports
    assert "max_times_fired" in exports
    assert "min_days_between_fire" in exports
    assert "points" in exports
    assert "conditions" in exports


def test_reachability_field_facts_include_start_and_success_transition():
    text = gamebus_studio_field_facts_markdown_for_check("reachability")

    assert "Use this level as the start of the level structure" in text
    assert "is_initial_level" in text
    assert "Next level when target is met on time" in text
    assert "success_next" in text


def test_target_points_field_facts_include_task_reward_fields():
    text = gamebus_studio_field_facts_markdown_for_check("targetpointsreachable")

    assert "Target points" in text
    assert "target" in text
    assert "Reward count" in text
    assert "max_times_fired" in text
    assert "Time window for resetting the reward count" in text
    assert "min_days_between_fire" in text
    assert "Number of points to award" in text
    assert "points" in text


def test_question_field_lookup_finds_min_days_between_fire():
    text = gamebus_studio_field_facts_markdown_for_question(
        "What does min_days_between_fire mean?"
    )

    assert "Time window for resetting the reward count" in text
    assert "min_days_between_fire" in text
    assert "greater than zero" in text


def test_question_field_lookup_finds_secret_conditions():
    text = gamebus_studio_field_facts_markdown_for_question(
        "Why is SECRET not available in the condition property selector?"
    )

    assert "Conditions" in text
    assert "Property / Operator / Value" in text
    assert "[SECRET, EQUAL, value]" in text