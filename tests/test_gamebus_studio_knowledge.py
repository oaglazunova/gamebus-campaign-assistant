from campaign_assistant.agents.gamebus_studio_knowledge import (
    gamebus_studio_facts_markdown_for_check,
    gamebus_studio_facts_markdown_for_issue,
    known_gamebus_studio_fact_topics,
)


def test_known_fact_topics_include_core_editor_areas():
    topics = known_gamebus_studio_fact_topics()

    assert "challenge_editor_location" in topics
    assert "content_editor_fields" in topics
    assert "level_settings_fields" in topics
    assert "task_editor_fields" in topics
    assert "conditions_editor" in topics


def test_reachability_facts_include_level_settings_and_transitions():
    text = gamebus_studio_facts_markdown_for_check("reachability")

    assert "Level settings" in text
    assert "success_next" in text
    assert "Next level when target is met on time" in text
    assert "wave-scoped" in text


def test_secrets_facts_include_conditions_and_export_triples():
    text = gamebus_studio_facts_markdown_for_check("secrets")

    assert "Task Conditions" in text
    assert "Property, Operator, and Value" in text
    assert "[SECRET, EQUAL, value]" in text
    assert "Allowed activity types" in text


def test_issue_facts_are_resolved_by_check():
    text = gamebus_studio_facts_markdown_for_issue(
        {
            "check": "targetpointsreachable",
            "message": "Challenge no target points defined (None).",
        }
    )

    assert "Target points" in text
    assert "Number of points to award" in text
    assert "min_days_between_fire" in text