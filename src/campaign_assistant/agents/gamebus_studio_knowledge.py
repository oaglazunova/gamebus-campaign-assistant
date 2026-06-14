from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from campaign_assistant.checker.schema import (
    CONSISTENCY,
    REACHABILITY,
    SECRETS,
    SPELLCHECKER,
    TARGETPOINTSREACHABLE,
    VISUALIZATIONINTERN,
)


@dataclass(frozen=True)
class GameBusStudioFact:
    """Derived GameBus Studio fact for grounded explanations.

    These facts are derived from inspected GameBus Studio / campaign editor code.
    Do not paste GameBus source code here. Keep only concise documentation facts
    that are safe to store in this assistant repo.
    """

    topic: str
    applies_to_checks: tuple[str, ...]
    text: str



@dataclass(frozen=True)
class GameBusStudioFieldFact:
    """Derived GameBus Studio knowledge for grounded explanations.
    """

    ui_label: str
    export_field: str
    editor_area: str
    explanation: str
    applies_to_checks: tuple[str, ...]
    keywords: tuple[str, ...]

    def as_markdown(self) -> str:
        return (
            f"- **{self.ui_label}**"
            f" (`{self.export_field}`, {self.editor_area}): "
            f"{self.explanation}"
        )


GAMEBUS_STUDIO_FACTS: tuple[GameBusStudioFact, ...] = (
    GameBusStudioFact(
        topic="challenge_editor_location",
        applies_to_checks=(
            REACHABILITY,
            CONSISTENCY,
            VISUALIZATIONINTERN,
            TARGETPOINTSREACHABLE,
            SPELLCHECKER,
        ),
        text=(
            "GameBus Studio edits a level/challenge in the campaign editor under a campaign, "
            "visualization/group, and challenge/level. The finding URL points directly to this editor."
        ),
    ),
    GameBusStudioFact(
        topic="content_editor_fields",
        applies_to_checks=(SPELLCHECKER, VISUALIZATIONINTERN),
        text=(
            "The level Content editor exposes Name, Labels, and Description. "
            "The checker export column 'name' corresponds to the level Name. "
            "The checker export column 'labels' corresponds to selected Content editor Labels."
        ),
    ),
    GameBusStudioFact(
        topic="level_settings_fields",
        applies_to_checks=(
            REACHABILITY,
            CONSISTENCY,
            TARGETPOINTSREACHABLE,
            VISUALIZATIONINTERN,
        ),
        text=(
            "The Level settings section exposes: Use this level as the start of the level structure "
            "(exported as is_initial_level), Target points (exported as target), "
            "Next level when target is met on time (exported as success_next), "
            "Evaluate failure interval (exported as evaluate_fail_every_x_minutes), and "
            "Next level when target is not met on time (exported as failure_next)."
        ),
    ),
    GameBusStudioFact(
        topic="failure_transition_validation",
        applies_to_checks=(CONSISTENCY, VISUALIZATIONINTERN),
        text=(
            "GameBus Studio treats Evaluate failure interval and Next level when target is not met "
            "on time as paired settings: if one is set, the other is required."
        ),
    ),
    GameBusStudioFact(
        topic="success_failure_transition_options",
        applies_to_checks=(REACHABILITY, CONSISTENCY, VISUALIZATIONINTERN),
        text=(
            "The success_next and failure_next selectors are populated with levels from the same "
            "campaign wave as the current visualization. This means transition choices are wave-scoped "
            "in the editor."
        ),
    ),
    GameBusStudioFact(
        topic="task_editor_fields",
        applies_to_checks=(SECRETS, SPELLCHECKER, TARGETPOINTSREACHABLE),
        text=(
            "The Tasks section exposes each task's Short task description, Description, Story URL, "
            "media/H5P fields, Reward count, Time window for resetting the reward count, "
            "Number of points to award, Allowed activity types, Allowed data sources, image-required flag, "
            "and Conditions."
        ),
    ),
    GameBusStudioFact(
        topic="task_export_mapping",
        applies_to_checks=(SECRETS, SPELLCHECKER, TARGETPOINTSREACHABLE),
        text=(
            "In the campaign export, task Short task description is exported as tasks.name; "
            "Reward count as max_times_fired; Time window for resetting the reward count as "
            "min_days_between_fire; Number of points to award as points; Allowed data sources as "
            "dataproviders; Allowed activity types as activityschemes_allowed; and task Conditions "
            "as bracketed triples [PROPERTY, OPERATOR, VALUE]."
        ),
    ),
    GameBusStudioFact(
        topic="conditions_editor",
        applies_to_checks=(SECRETS,),
        text=(
            "Task Conditions are edited as rows with Property, Operator, and Value. The available "
            "Properties depend on the selected Allowed activity types. Operators depend on the selected "
            "property type. A SECRET condition relevant for the secrets checker is represented in the "
            "export as [SECRET, EQUAL, value]."
        ),
    ),
    GameBusStudioFact(
        topic="data_provider_filtering",
        applies_to_checks=(SECRETS, TARGETPOINTSREACHABLE),
        text=(
            "Allowed data sources depend on the selected Allowed activity types. When saving a task, "
            "GameBus Studio filters submitted data providers and condition properties against the permissions "
            "allowed for the selected activity types."
        ),
    ),
)


GAMEBUS_STUDIO_FIELD_FACTS: tuple[GameBusStudioFieldFact, ...] = (
    GameBusStudioFieldFact(
        ui_label="Use this level as the start of the level structure",
        export_field="is_initial_level",
        editor_area="Level settings",
        explanation=(
            "Marks a level as an initial/start level for the level structure. "
            "The reachability checker starts from levels where this exported value is enabled."
        ),
        applies_to_checks=(REACHABILITY, CONSISTENCY),
        keywords=(
            "start level",
            "initial level",
            "is_initial_level",
            "use this level as the start",
            "start of the level structure",
        ),
    ),
    GameBusStudioFieldFact(
        ui_label="Next level when target is met on time",
        export_field="success_next",
        editor_area="Level settings",
        explanation=(
            "Defines the success transition from the current level to the next level. "
            "The reachability checker follows this transition to determine whether terminal levels "
            "can be reached from initial levels."
        ),
        applies_to_checks=(REACHABILITY, CONSISTENCY, VISUALIZATIONINTERN),
        keywords=(
            "success_next",
            "success transition",
            "next level when target is met",
            "next level when target is met on time",
            "make reachable",
            "reachable",
            "terminal level",
        ),
    ),
    GameBusStudioFieldFact(
        ui_label="Next level when target is not met on time",
        export_field="failure_next",
        editor_area="Level settings",
        explanation=(
            "Defines the failure transition from the current level. The consistency checker uses this "
            "for start-level failure behavior, and the visualization-internal checker follows both "
            "success and failure transitions."
        ),
        applies_to_checks=(CONSISTENCY, VISUALIZATIONINTERN),
        keywords=(
            "failure_next",
            "failure transition",
            "next level when target is not met",
            "next level when target is not met on time",
            "failure path",
        ),
    ),
    GameBusStudioFieldFact(
        ui_label="Evaluate failure interval",
        export_field="evaluate_fail_every_x_minutes",
        editor_area="Level settings",
        explanation=(
            "Controls the time interval used for evaluating whether the target was not met. "
            "The target-points checker uses this exported value as the level duration for its "
            "reachable-points calculation."
        ),
        applies_to_checks=(CONSISTENCY, TARGETPOINTSREACHABLE),
        keywords=(
            "evaluate failure interval",
            "evaluate_fail_every_x_minutes",
            "duration",
            "level duration",
            "failure interval",
            "time interval",
        ),
    ),
    GameBusStudioFieldFact(
        ui_label="Target points",
        export_field="target",
        editor_area="Level settings",
        explanation=(
            "The point target for the level. The target-points checker compares this value with the "
            "maximum points reachable from the level's tasks."
        ),
        applies_to_checks=(TARGETPOINTSREACHABLE,),
        keywords=(
            "target",
            "target points",
            "points target",
            "unreachable target",
        ),
    ),
    GameBusStudioFieldFact(
        ui_label="Name",
        export_field="name",
        editor_area="Content editor",
        explanation=(
            "The participant-facing level/challenge name. The spellchecker checks this exported value "
            "for level/challenge spelling issues."
        ),
        applies_to_checks=(SPELLCHECKER,),
        keywords=(
            "name",
            "level name",
            "challenge name",
            "spelling",
            "spellchecker",
        ),
    ),
    GameBusStudioFieldFact(
        ui_label="Labels",
        export_field="labels",
        editor_area="Content editor",
        explanation=(
            "Labels attached to the level. The visualization-internal checker compares labels between "
            "an initial level and reachable terminal levels."
        ),
        applies_to_checks=(VISUALIZATIONINTERN,),
        keywords=(
            "labels",
            "label",
            "different label",
            "same label",
            "visualization intern",
            "visualizationintern",
        ),
    ),
    GameBusStudioFieldFact(
        ui_label="Short task description",
        export_field="tasks.name",
        editor_area="Tasks",
        explanation=(
            "The task name/short description exported for checker analysis. The spellchecker checks this "
            "text, and the secrets checker compares task names when it detects duplicate secret values."
        ),
        applies_to_checks=(SECRETS, SPELLCHECKER),
        keywords=(
            "task name",
            "task description",
            "short task description",
            "tasks.name",
            "spelling",
            "duplicate secret",
        ),
    ),
    GameBusStudioFieldFact(
        ui_label="Reward count",
        export_field="max_times_fired",
        editor_area="Tasks",
        explanation=(
            "The maximum number of times a task can award points within its reset window. "
            "The target-points checker uses this value to estimate the maximum reachable points."
        ),
        applies_to_checks=(TARGETPOINTSREACHABLE,),
        keywords=(
            "reward count",
            "max_times_fired",
            "maximum times fired",
            "repeatable",
            "task repetition",
        ),
    ),
    GameBusStudioFieldFact(
        ui_label="Time window for resetting the reward count",
        export_field="min_days_between_fire",
        editor_area="Tasks",
        explanation=(
            "The reset window for task rewards. The target-points checker uses this value to estimate "
            "how often the task can award points during the level duration. The current checker requires "
            "this value to be numeric and greater than zero."
        ),
        applies_to_checks=(TARGETPOINTSREACHABLE,),
        keywords=(
            "time window",
            "resetting the reward count",
            "min_days_between_fire",
            "reset window",
            "days between fire",
        ),
    ),
    GameBusStudioFieldFact(
        ui_label="Number of points to award",
        export_field="points",
        editor_area="Tasks",
        explanation=(
            "The number of points awarded when the task fires. The target-points checker multiplies "
            "this value by the estimated number of possible task firings."
        ),
        applies_to_checks=(TARGETPOINTSREACHABLE,),
        keywords=(
            "number of points",
            "points",
            "points to award",
            "task points",
            "award points",
        ),
    ),
    GameBusStudioFieldFact(
        ui_label="Allowed data sources",
        export_field="dataproviders",
        editor_area="Tasks",
        explanation=(
            "The data sources allowed for a task. The secrets checker currently focuses on tasks whose "
            "exported data provider is GameBus Studio. Data source selection can also affect which "
            "condition properties are available."
        ),
        applies_to_checks=(SECRETS,),
        keywords=(
            "allowed data sources",
            "dataproviders",
            "data provider",
            "gamebus studio",
            "secret not available",
        ),
    ),
    GameBusStudioFieldFact(
        ui_label="Conditions",
        export_field="conditions",
        editor_area="Tasks",
        explanation=(
            "Task conditions are edited as Property / Operator / Value rows. For the secrets checker, "
            "a valid secret condition is exported as a bracketed triple [SECRET, EQUAL, value]."
        ),
        applies_to_checks=(SECRETS,),
        keywords=(
            "conditions",
            "condition",
            "property",
            "operator",
            "value",
            "secret",
            "secret condition",
            "[secret, equal",
        ),
    ),
)



def gamebus_studio_facts_for_check(check_id: str | None) -> tuple[GameBusStudioFact, ...]:
    if not check_id:
        return ()

    normalized = str(check_id).lower()
    return tuple(
        fact
        for fact in GAMEBUS_STUDIO_FACTS
        if normalized in fact.applies_to_checks
    )


def gamebus_studio_facts_markdown_for_check(check_id: str | None) -> str:
    facts = gamebus_studio_facts_for_check(check_id)
    if not facts:
        return ""

    lines = ["GameBus Studio source facts:"]
    for fact in facts:
        lines.append(f"- **{fact.topic}**: {fact.text}")

    return "\n".join(lines)


def gamebus_studio_facts_markdown_for_issue(issue: dict) -> str:
    return gamebus_studio_facts_markdown_for_check(issue.get("check"))


def known_gamebus_studio_fact_topics() -> set[str]:
    return {fact.topic for fact in GAMEBUS_STUDIO_FACTS}


def gamebus_studio_field_facts_for_check(
    check_id: str | None,
) -> tuple[GameBusStudioFieldFact, ...]:
    if not check_id:
        return ()

    normalized = str(check_id).lower()
    return tuple(
        fact
        for fact in GAMEBUS_STUDIO_FIELD_FACTS
        if normalized in fact.applies_to_checks
    )


def gamebus_studio_field_facts_markdown_for_check(check_id: str | None) -> str:
    facts = gamebus_studio_field_facts_for_check(check_id)
    if not facts:
        return ""

    lines = ["GameBus Studio facts:"]
    lines.extend(fact.as_markdown() for fact in facts)
    return "\n".join(lines)


def _keyword_score(question: str, fact: GameBusStudioFieldFact) -> int:
    normalized_question = question.lower()
    return sum(1 for keyword in fact.keywords if keyword.lower() in normalized_question)


def gamebus_studio_field_facts_for_question(
    question: str,
    *,
    limit: int = 5,
) -> tuple[GameBusStudioFieldFact, ...]:
    scored = [
        (_keyword_score(question, fact), fact)
        for fact in GAMEBUS_STUDIO_FIELD_FACTS
    ]
    matching = [
        fact
        for score, fact in sorted(scored, key=lambda item: item[0], reverse=True)
        if score > 0
    ]
    return tuple(matching[:limit])


def gamebus_studio_field_facts_markdown_for_question(
    question: str,
    *,
    limit: int = 5,
) -> str:
    facts = gamebus_studio_field_facts_for_question(question, limit=limit)
    if not facts:
        return ""

    lines = ["Relevant GameBus Studio facts:"]
    lines.extend(fact.as_markdown() for fact in facts)
    return "\n".join(lines)


def known_gamebus_studio_field_exports() -> set[str]:
    return {fact.export_field for fact in GAMEBUS_STUDIO_FIELD_FACTS}