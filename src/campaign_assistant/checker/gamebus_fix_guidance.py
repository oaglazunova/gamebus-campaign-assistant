from __future__ import annotations

import re

from dataclasses import dataclass
from typing import Any

from campaign_assistant.checker.schema import (
    CONSISTENCY,
    REACHABILITY,
    SECRETS,
    SPELLCHECKER,
    TARGETPOINTSREACHABLE,
    VISUALIZATIONINTERN,
    PROGRESSIONBRANCHCONSISTENCY,
    DUPLICATETASKNAMES,
    TEXTPOINTSCONSISTENCY,
)


@dataclass(frozen=True)
class GameBusFixGuidance:
    """Deterministic GameBus Studio guidance for one checker finding.

    This is derived documentation: it describes where the campaign editor exposes
    the fields that the deterministic checker reads from the campaign export.
    It must not contain copied GameBus source code.
    """

    title: str
    studio_location: tuple[str, ...]
    fields_to_check: tuple[str, ...]
    fix_steps: tuple[str, ...]
    verification: str

    def as_markdown(self) -> str:
        parts = [f"**{self.title}**"]
        parts.append("")
        parts.append("**Where to check in GameBus Studio**")
        parts.extend(f"- {item}" for item in self.studio_location)
        parts.append("")
        parts.append("**Fields to inspect**")
        parts.extend(f"- {item}" for item in self.fields_to_check)
        parts.append("")
        parts.append("**How to fix**")
        parts.extend(f"{idx}. {item}" for idx, item in enumerate(self.fix_steps, start=1))
        parts.append("")
        parts.append(f"**Verify:** {self.verification}")
        return "\n".join(parts)


_GENERIC_VERIFICATION = (
    "Save the edited level/task, export the campaign again, and rerun the deterministic checker."
)


_FIX_GUIDANCE_BY_CHECK: dict[str, GameBusFixGuidance] = {
    SECRETS: GameBusFixGuidance(
        title="Fix missing or conflicting task secrets",
        studio_location=(
            "Open GameBus Studio campaign editor.",
            "Open the relevant campaign, then the visualization/group shown in the finding.",
            "Open the reported challenge/level.",
            "In the Tasks section, open the reported task.",
            "Use the Conditions section of the task.",
        ),
        fields_to_check=(
            "Task: Short task description / name. This is the exported task name used by the checker.",
            "Task: Conditions → Property. For a secret condition this should be SECRET.",
            "Task: Conditions → Operator. For the checker this should be EQUAL.",
            "Task: Conditions → Value. This is the secret value that must be unique when task names differ.",
            "Task: Allowed activity types and Allowed data sources. These control which condition properties are available in the editor.",
        ),
        fix_steps=(
            "If the finding says the task has no secret, add a condition with Property = SECRET, Operator = EQUAL, and a task-specific Value.",
            "If the finding says the same secret is used by tasks with different names, open each listed task and give genuinely different tasks different secret values.",
            "Keep the same secret only when the copied tasks intentionally represent the same task/name.",
            "If SECRET is not available in the Property selector, check the task's Allowed activity types and Allowed data sources because the editor filters available properties from those selections.",
        ),
        verification=_GENERIC_VERIFICATION,
    ),
    SPELLCHECKER: GameBusFixGuidance(
        title="Fix spelling in level and task text",
        studio_location=(
            "Open GameBus Studio campaign editor.",
            "Open the relevant campaign, then the visualization/group shown in the finding.",
            "Open the reported challenge/level.",
            "For a level-name issue, edit the level Name in the Content editor section.",
            "For a task-name issue, open the task in the Tasks section and edit Short task description.",
        ),
        fields_to_check=(
            "Level: Name. This is the exported challenge name checked by the spellchecker.",
            "Task: Short task description. This is the exported task name checked by the spellchecker.",
            "Optional descriptive text is not the current checker target unless it is exported as the task/challenge name.",
        ),
        fix_steps=(
            "Apply the proposed correction if it is correct for the intervention language and terminology.",
            "If the word is intentional domain vocabulary, leave it unchanged and treat the finding as a false positive for now.",
            "Keep names short and participant-facing because the same text is used in the campaign configuration and may be visible in GameBus.",
        ),
        verification=_GENERIC_VERIFICATION,
    ),
    REACHABILITY: GameBusFixGuidance(
        title="Fix unreachable progression levels",
        studio_location=(
            "Open GameBus Studio campaign editor.",
            "Open the campaign and the visualization/group shown in the finding.",
            "Open the reported challenge/level, or use the URL shown in the finding.",
            "Use the Level settings section.",
        ),
        fields_to_check=(
            "Use this level as the start of the level structure. "
            "This corresponds to exported is_initial_level.",
            "Next level when target is met on time. "
            "This corresponds to exported success_next.",
            "Next level when target is not met on time. "
            "This corresponds to exported failure_next.",
            "For successful completion, a terminal level is a level whose "
            "Next level when target is met on time points back to itself.",
        ),
        fix_steps=(
            "If a level cannot be reached from any start level, inspect the "
            "success and failure transitions of the preceding levels and connect "
            "the intended path to it.",
            "Fallback or at-risk levels normally need an incoming failure or "
            "recovery transition from another reachable level.",
            "If a start level has no successful completion path, follow "
            "Next level when target is met on time from that start and make sure "
            "the chain eventually reaches a terminal level.",
            "If an unreachable level is obsolete and should no longer be part "
            "of the progression, remove or reconfigure it instead of creating "
            "an artificial transition.",
            "Do not fix reachability by changing Target points; target "
            "feasibility is checked separately.",
        ),
        verification=_GENERIC_VERIFICATION,
    ),
    CONSISTENCY: GameBusFixGuidance(
        title="Fix inconsistent start-level failure settings",
        studio_location=(
            "Open GameBus Studio campaign editor.",
            "Open the campaign and the visualization/group shown in the finding.",
            "Open the reported challenge/level.",
            "Use the Level settings section.",
        ),
        fields_to_check=(
            "Use this level as the start of the level structure. This corresponds to exported is_initial_level.",
            "Next level when target is not met on time. This corresponds to exported failure_next.",
            "Evaluate failure interval. This corresponds to exported evaluate_fail_every_x_minutes and is required when failure_next is set.",
            "Next level when target is met on time. This corresponds to exported success_next.",
        ),
        fix_steps=(
            "If the finding says an initial level does not lead to itself on failure, set its failure transition to the same level, or reconsider whether it should be marked as the start level.",
            "If the finding says a terminal level does not lead to itself on success, set Next level when target is met on time to the same level.",
            "When setting a failure transition, also set Evaluate failure interval because the editor requires these two settings together.",
            "Keep start-level and terminal-level conventions consistent across all levels in the same visualization/group.",
        ),
        verification=_GENERIC_VERIFICATION,
    ),
    VISUALIZATIONINTERN: GameBusFixGuidance(
        title="Fix level paths that leave the visualization or label group",
        studio_location=(
            "Open GameBus Studio campaign editor.",
            "Open the campaign and the visualization/group shown in the finding.",
            "Open the reported initial level and the reachable level mentioned in the finding.",
            "Use Content editor → Labels and Level settings.",
        ),
        fields_to_check=(
            "Labels. This corresponds to exported labels and is used by the checker to compare the initial and reachable level.",
            "Next level when target is met on time. This corresponds to exported success_next.",
            "Next level when target is not met on time. This corresponds to exported failure_next.",
            "Visualization/group membership shown at the top of the level editor. This corresponds to exported visualizations.",
        ),
        fix_steps=(
            "Check whether the reachable terminal level is intended to belong to the same visualization/group as the initial level.",
            "If the transition is wrong, change the success or failure transition so the path stays inside the intended visualization/group.",
            "If the transition is intended, align the Labels value between the initial and reachable level where appropriate.",
            "If the reachable level belongs to the wrong visualization/group, move/recreate the level in the correct visualization/group rather than silently accepting a cross-visualization path.",
        ),
        verification=_GENERIC_VERIFICATION,
    ),
    PROGRESSIONBRANCHCONSISTENCY: GameBusFixGuidance(
        title="Review a recovery level placed on the normal success path",
        studio_location=(
            "Open GameBus Studio campaign editor.",
            "Open the campaign and the visualization/group shown in the finding.",
            "Open the reported recovery/fallback level.",
            "Also inspect the previous and next normal progression levels named in the finding.",
            "Use the Level settings section for all three levels.",
        ),
        fields_to_check=(
            "Next level when target is met on time on the previous level.",
            "Next level when target is met on time on the reported recovery/fallback level.",
            "Next level when target is not met on time on the reported recovery/fallback level.",
            "Next level when target is not met on time on the next normal level.",
            "Target points on the previous, reported, and next levels. The checker uses a lower target on the reported level as evidence that it is likely a recovery/fallback level.",
        ),
        fix_steps=(
            "First confirm whether the reported level is intentionally a recovery/fallback level rather than a normal progression level.",
            "If it is a recovery/fallback level, inspect the previous normal level's success transition. It would normally be expected to lead directly to the next normal level rather than to the recovery level.",
            "Keep the next normal level's failure transition pointing to the recovery level if that is the intended fallback behaviour.",
            "Keep the recovery level's success and failure transitions consistent with the intended recovery path, for example success back to the normal level and failure back to the preceding level.",
            "If the reported structure is intentional, leave it unchanged; this check reports a structurally suspicious pattern rather than a proven configuration error.",
        ),
        verification=_GENERIC_VERIFICATION,
    ),
    TARGETPOINTSREACHABLE: GameBusFixGuidance(
        title="Fix unreachable target points",
        studio_location=(
            "Open GameBus Studio campaign editor.",
            "Open the campaign and the visualization/group shown in the finding.",
            "Open the reported challenge/level.",
            "Use Level settings for target and duration-related settings.",
            "Use the Tasks section for task reward settings.",
        ),
        fields_to_check=(
            "Level settings → Target points. This corresponds to exported target.",
            "Level settings → Evaluate failure interval. This corresponds to exported evaluate_fail_every_x_minutes and is used as the challenge duration in the checker calculation.",
            "Task → Reward count. This corresponds to exported max_times_fired.",
            "Task → Time window for resetting the reward count. This corresponds to exported min_days_between_fire.",
            "Task → Number of points to award. This corresponds to exported points.",
        ),
        fix_steps=(
            "If the target is too high, lower Target points.",
            "If tasks should award more points, increase Number of points to award for one or more tasks.",
            "If tasks should be repeatable more often, increase Reward count or reduce Time window for resetting the reward count.",
            "If participants should have more time, choose a longer Evaluate failure interval.",
            "If the checker says reachable points cannot be computed, fill missing numeric values for Target points, Evaluate failure interval, Reward count, Time window for resetting the reward count, and Number of points to award.",
        ),
        verification=_GENERIC_VERIFICATION,
    ),
    TEXTPOINTSCONSISTENCY: GameBusFixGuidance(
        title="Fix mismatch between task text and awarded points",
        studio_location=(
            "Open GameBus Studio campaign editor.",
            "Open the campaign and the visualization/group shown in the finding.",
            "Open the reported challenge/level.",
            "In the Tasks section, open the reported task.",
        ),
        fields_to_check=(
            "Task → Short task description. This is exported as the task name.",
            "Task → Description. This is participant-facing explanatory text.",
            "Task → Number of points to award. This is the actual points value GameBus awards.",
        ),
        fix_steps=(
            "Compare the point value mentioned in Short task description or Description with Number of points to award.",
            "If the text is wrong, edit the task text so it describes the actual number of points awarded.",
            "If the points setting is wrong, change Number of points to award to match the intended participant-facing text.",
            "Check both language versions if the text is bilingual; the checker may report a number from either part of the text.",
            "Do not change reward count or reset window unless the intended fix is about how often the task can award points; this check is about the visible point number versus the exported points value.",
        ),
        verification=_GENERIC_VERIFICATION,
    ),
    DUPLICATETASKNAMES: GameBusFixGuidance(
        title="Review duplicate task names with different settings",
        studio_location=(
            "Open GameBus Studio campaign editor.",
            "Open the campaign and the visualization/group shown in the finding.",
            "Open each challenge/level listed in the finding.",
            "In each level, open the task with the duplicated Short task description.",
        ),
        fields_to_check=(
            "Task → Short task description. This is the duplicated participant-facing task name.",
            "Task → Description. This may explain whether the duplicate is intentional.",
            "Task → Number of points to award.",
            "Task → Reward count.",
            "Task → Time window for resetting the reward count.",
            "Task → Allowed activity types and Allowed data sources.",
            "Task → Conditions → Property / Operator / Value.",
        ),
        fix_steps=(
            "Compare the duplicated tasks listed in the finding.",
            "If they are meant to be different tasks, rename them so participants and editors can distinguish them.",
            "If they are meant to be the same task, align the relevant settings: points, reward count, reset window, allowed activity types, data sources, and conditions.",
            "If the same name is intentionally reused with different settings across levels, keep it but treat the finding as a warning.",
            "This check reports only duplicate names with meaningful setting differences; exact duplicates are not reported.",
        ),
        verification=_GENERIC_VERIFICATION,
    ),
}


def _extract_quoted_pair(pattern: str, text: str) -> tuple[str | None, str | None]:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def _visualizationintern_mismatch_kind(issue: dict[str, Any]) -> str:
    """Classify visualizationintern mismatch using the concrete checker message."""
    message = _issue_message(issue)

    initial_visualization, reachable_visualization = _extract_quoted_pair(
        r"Initial challenge visualization = '([^']*)'; reachable challenge visualization = '([^']*)'",
        message,
    )
    initial_label, reachable_label = _extract_quoted_pair(
        r"Initial challenge labels = '([^']*)'; reachable challenge labels = '([^']*)'",
        message,
    )

    if (
        initial_visualization is not None
        and reachable_visualization is not None
        and initial_visualization != reachable_visualization
    ):
        return "different_visualization"

    if (
        initial_label is not None
        and reachable_label is not None
        and initial_label != reachable_label
    ):
        return "different_label"

    return "unknown"


def _issue_message(issue: dict[str, Any]) -> str:
    return str(
        issue.get("message")
        or issue.get("description")
        or issue.get("details")
        or issue.get("title")
        or ""
    )


def _issue_message_lower(issue: dict[str, Any]) -> str:
    return _issue_message(issue).lower()


def _specific_guidance_markdown(issue: dict[str, Any]) -> str:
    """Return detailed guidance for a concrete issue subtype.

    If this function recognizes the exact issue subtype, the result should be
    complete enough to show on its own in the Findings UI. Generic check-level
    guidance is then not appended, because that makes the UI repetitive.
    """
    check = str(issue.get("check") or "").lower()
    message = _issue_message_lower(issue)

    if check == SECRETS:
        title = str(issue.get("title") or "").lower()

        if (
                "multiple secret conditions" in title
                or re.search(
            r"\b(?:has|contains)\s+\d+\s+secret conditions\b",
            message,
        )
        ):
            return GameBusFixGuidance(
                title="Keep one intended SECRET condition on this task",
                studio_location=(
                    "Open the finding URL, or open GameBus Studio campaign editor manually.",
                    "Open the reported campaign, visualization/group, and challenge/level.",
                    "In the Tasks section, open the reported task.",
                    "Use the task Conditions section.",
                ),
                fields_to_check=(
                    "Review every condition whose Property is SECRET.",
                    "For the intended task secret, use Property = SECRET and Operator = EQUAL.",
                    "Check the Value of the intended SECRET EQUAL condition.",
                    "Also preserve any unrelated non-SECRET conditions that are still required by the task.",
                ),
                fix_steps=(
                    "Identify which SECRET value is intended to identify this task/activity.",
                    "Keep one condition with Property = SECRET, Operator = EQUAL, and that intended value.",
                    "Remove additional SECRET conditions that are redundant or conflict with the intended secret.",
                    "Do not delete conditions for other properties merely because they appear in the same task.",
                    "Save the task and verify that only one SECRET condition remains.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

        if "has no secret" in message:
            return GameBusFixGuidance(
                title="Add a missing secret condition to this task",
                studio_location=(
                    "Open the finding URL, or open GameBus Studio campaign editor manually.",
                    "Open the reported campaign, visualization/group, and challenge/level.",
                    "In the Tasks section, open the reported task.",
                    "Use the task Conditions section.",
                ),
                fields_to_check=(
                    "Conditions → Property. Set this to SECRET.",
                    "Conditions → Operator. Set this to EQUAL.",
                    "Conditions → Value. Use a task-specific secret value.",
                    "Allowed activity types and Allowed data sources, if SECRET is not available in the Property selector.",
                ),
                fix_steps=(
                    "If the finding says the task has no secret, add a condition with Property = SECRET, Operator = EQUAL, and a task-specific Value.",
                    "If the task has multiple SECRET conditions, identify the intended SECRET EQUAL condition and remove redundant or conflicting SECRET conditions. Do not remove unrelated non-SECRET conditions.",
                    "If the finding says the same secret is used by tasks with different names, review whether the reuse is intentional before changing it.",
                    "If genuinely different tasks should react independently, give them different SECRET values.",
                    "If SECRET is not available in the Property selector, check the task's Allowed activity types and Allowed data sources because the editor filters available properties from those selections.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

        if "same secret" in message and "different names" in message:
            return GameBusFixGuidance(
                title="Resolve a duplicate secret used by different tasks",
                studio_location=(
                    "Open GameBus Studio campaign editor.",
                    "Open the reported campaign, visualization/group, and challenge/level.",
                    "Open each task listed in the finding.",
                    "Use the task Conditions section.",
                ),
                fields_to_check=(
                    "Task → Short task description. Compare whether the tasks are genuinely different.",
                    "Conditions → Property = SECRET.",
                    "Conditions → Operator = EQUAL.",
                    "Conditions → Value. This is the secret value that is duplicated.",
                ),
                fix_steps=(
                    "If the tasks are different participant tasks, give each task a distinct SECRET value.",
                    "If the tasks are intentionally the same task copied across places, check whether the same task name should also be used.",
                    "Avoid using one generic secret value for several different tasks, because the checker treats that as ambiguous.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

    if check == SPELLCHECKER:
        if "name of task" in message:
            return GameBusFixGuidance(
                title="Correct a spelling issue in a task name",
                studio_location=(
                    "Open the finding URL, or open the reported level in GameBus Studio.",
                    "Go to the Tasks section.",
                    "Open the reported task.",
                ),
                fields_to_check=(
                    "Task → Short task description. This is the exported task name checked by the spellchecker.",
                ),
                fix_steps=(
                    "Apply the proposed correction if it is correct for the campaign language.",
                    "If the word is intentional domain vocabulary, leave it unchanged and treat the finding as a false positive.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

        if "name of challenge" in message:
            return GameBusFixGuidance(
                title="Correct a spelling issue in a level name",
                studio_location=(
                    "Open the finding URL, or open the reported level in GameBus Studio.",
                    "Use the Content editor section.",
                ),
                fields_to_check=(
                    "Content editor → Name. This is the exported challenge/level name checked by the spellchecker.",
                ),
                fix_steps=(
                    "Apply the proposed correction if it is correct for the campaign language.",
                    "If the word is intentional domain vocabulary, leave it unchanged and treat the finding as a false positive.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

        if "is empty" in message:
            return GameBusFixGuidance(
                title="Fill an empty task or level name",
                studio_location=(
                    "Open the finding URL, or open the reported item in GameBus Studio.",
                    "For a level, use the Content editor section.",
                    "For a task, use the Tasks section.",
                ),
                fields_to_check=(
                    "Level → Name, if the finding concerns a challenge/level.",
                    "Task → Short task description, if the finding concerns a task.",
                ),
                fix_steps=(
                    "Fill the empty name with a clear participant-facing label.",
                    "Re-export and rerun the checker because empty names can make other findings harder to interpret.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

    if check == REACHABILITY:
        if "progression level not reachable from any initial challenge" in message:
            return GameBusFixGuidance(
                title="Connect this unreachable level to the progression",
                studio_location=(
                    "Open the reported level using the finding URL.",
                    "Open the neighbouring levels that should lead to this level.",
                    "Use the Level settings section.",
                ),
                fields_to_check=(
                    "Next level when target is met on time on preceding levels.",
                    "Next level when target is not met on time on preceding levels.",
                    "Use this level as the start of the level structure, if this level is actually intended to be another start.",
                ),
                fix_steps=(
                    "First confirm where this level is intended to appear in the progression.",
                    "If it is a normal level, make sure an earlier reachable level has a success transition to it.",
                    "If it is a fallback or at-risk level, make sure the appropriate reachable level has a failure transition to it.",
                    "Check the reported level's own success and failure transitions as well, but remember that outgoing transitions do not make a level reachable: another reachable level must lead into it.",
                    "If the level is obsolete, remove or reconfigure it rather than adding an artificial transition.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

        if "initial challenge without terminal challenge" in message:
            return GameBusFixGuidance(
                title="Connect this initial level to a terminal success path",
                studio_location=(
                    "Open the reported initial level in GameBus Studio.",
                    "Use the Level settings section.",
                    "Then open each next level reached through the success transition.",
                ),
                fields_to_check=(
                    "Use this level as the start of the level structure. This should be enabled for the reported initial level.",
                    "Next level when target is met on time. This is the success transition followed by the reachability checker.",
                    "For this checker, a terminal level is a level whose success transition points back to itself.",
                ),
                fix_steps=(
                    "Start from the reported initial level.",
                    "Follow Next level when target is met on time.",
                    "Make sure the chain eventually reaches a terminal level.",
                    "If this level should not be a start level, disable Use this level as the start of the level structure instead.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

        if "terminal challenge not reachable" in message:
            return GameBusFixGuidance(
                title="Connect this terminal level to an initial success path",
                studio_location=(
                    "Open the reported terminal level using the finding URL.",
                    "Open the intended start level in the same visualization/group.",
                    "Use the Level settings section of these levels.",
                ),
                fields_to_check=(
                    "Terminal level → Next level when target is met on time. It currently points back to the same level.",
                    "Start level → Use this level as the start of the level structure.",
                    "Start level and intermediate levels → Next level when target is met on time.",
                ),
                fix_steps=(
                    "Confirm whether the reported terminal level should still be part of the progression.",
                    "If yes, adjust success transitions so at least one initial level eventually reaches this terminal level.",
                    "If no, change the terminal level's success transition so it no longer points to itself, or remove/rework the obsolete level.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

    if check == CONSISTENCY:
        if "initial challenge does not lead to itself on failure" in message:
            return GameBusFixGuidance(
                title="Make the initial level stay on itself after failure",
                studio_location=(
                    "Open the reported level in GameBus Studio.",
                    "Use the Level settings section.",
                ),
                fields_to_check=(
                    "Use this level as the start of the level structure.",
                    "Next level when target is not met on time.",
                    "Evaluate failure interval.",
                ),
                fix_steps=(
                    "If this level is intended to be the start level, set Next level when target is not met on time to this same level.",
                    "Fill Evaluate failure interval if it is empty.",
                    "If this level should not be an initial level, disable Use this level as the start of the level structure instead.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

        if "terminal challenge does not lead to itself on success" in message:
            return GameBusFixGuidance(
                title="Make the terminal level stay on itself after success",
                studio_location=(
                    "Open the reported level in GameBus Studio.",
                    "Use the Level settings section.",
                ),
                fields_to_check=(
                    "Next level when target is met on time.",
                ),
                fix_steps=(
                    "If this level is intended to be terminal, set Next level when target is met on time to this same level.",
                    "If this level should not be terminal, change the success transition to the intended next level and rerun the checker.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

    if check == VISUALIZATIONINTERN:
        if "not in same visualization" in message or "not with same label" in message:
            mismatch_kind = _visualizationintern_mismatch_kind(issue)

            if mismatch_kind == "different_label":
                return GameBusFixGuidance(
                    title="Fix a transition path that reaches a level with a different label",
                    studio_location=(
                        "Open the reported initial level in GameBus Studio.",
                        "Open the reachable terminal level mentioned in the finding message.",
                        "Use Content editor → Labels and Level settings.",
                    ),
                    fields_to_check=(
                        "Content editor → Labels on the initial level.",
                        "Content editor → Labels on the reachable terminal level.",
                        "Level settings → Next level when target is met on time.",
                        "Level settings → Next level when target is not met on time.",
                    ),
                    fix_steps=(
                        "Compare the Labels field of the initial level and the reachable terminal level.",
                        "Follow both success and failure transitions from the initial level; this checker follows both transition types.",
                        "If the reachable terminal level should belong to the same progression branch, align the Labels value.",
                        "If the reachable terminal level should not be in this branch, change the incorrect success or failure transition so the path reaches the intended terminal level.",
                    ),
                    verification=_GENERIC_VERIFICATION,
                ).as_markdown()

            if mismatch_kind == "different_visualization":
                return GameBusFixGuidance(
                    title="Fix a transition path that reaches a different visualization",
                    studio_location=(
                        "Open the reported initial level in GameBus Studio.",
                        "Open the reachable terminal level mentioned in the finding message.",
                        "Use Level settings to inspect success and failure transitions.",
                    ),
                    fields_to_check=(
                        "The visualization/group shown in the level editor URL and page context.",
                        "Level settings → Next level when target is met on time.",
                        "Level settings → Next level when target is not met on time.",
                    ),
                    fix_steps=(
                        "Follow both success and failure transitions from the initial level.",
                        "Find the transition that leaves the intended visualization/group.",
                        "Change that transition so it points to a level in the same visualization/group.",
                        "If the reachable level really belongs to this branch, recreate or move it into the correct visualization/group rather than accepting a cross-visualization path.",
                    ),
                    verification=_GENERIC_VERIFICATION,
                ).as_markdown()

            return GameBusFixGuidance(
                title="Fix a level path that leaves the intended visualization or label group",
                studio_location=(
                    "Open the reported initial level in GameBus Studio.",
                    "Open the reachable terminal level mentioned in the finding message.",
                    "Use Content editor and Level settings.",
                ),
                fields_to_check=(
                    "Content editor → Labels.",
                    "Level settings → Next level when target is met on time.",
                    "Level settings → Next level when target is not met on time.",
                    "The visualization/group shown in the editor URL and page context.",
                ),
                fix_steps=(
                    "Follow both success and failure transitions from the initial level.",
                    "Compare the visualization/group and Labels values of the initial and reachable terminal levels.",
                    "Fix either the transition path or the Labels value, depending on the intended progression structure.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

    if check == TARGETPOINTSREACHABLE:
        if "cannot be reached" in message:
            return GameBusFixGuidance(
                title="Adjust target points or task rewards so the target can be reached",
                studio_location=(
                    "Open the reported level in GameBus Studio.",
                    "Use Level settings for the target and evaluation interval.",
                    "Use the Tasks section for reward settings.",
                ),
                fields_to_check=(
                    "Level settings → Target points.",
                    "Level settings → Evaluate failure interval.",
                    "Task → Reward count.",
                    "Task → Time window for resetting the reward count.",
                    "Task → Number of points to award.",
                ),
                fix_steps=(
                    "Compare the target with the maximum reachable points reported by the checker.",
                    "If the target is too high, lower Target points.",
                    "If the target should stay high, increase task points, increase Reward count, reduce the reset time window, or lengthen the evaluation interval.",
                    "Check all tasks in the level, not only the first task, because the checker sums reachable points across tasks.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

        if "cannot be computed" in message or "missing values" in message:
            return GameBusFixGuidance(
                title="Fill missing numeric values needed for target-point calculation",
                studio_location=(
                    "Open the reported level in GameBus Studio.",
                    "Use Level settings and the Tasks section.",
                ),
                fields_to_check=(
                    "Level settings → Target points.",
                    "Level settings → Evaluate failure interval.",
                    "Task → Reward count.",
                    "Task → Time window for resetting the reward count.",
                    "Task → Number of points to award.",
                ),
                fix_steps=(
                    "Fill every required numeric field listed above.",
                    "Make sure Time window for resetting the reward count is greater than zero.",
                    "Check every task attached to the level because one missing task value can make the whole level calculation fail.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

        if "no target points defined" in message:
            return GameBusFixGuidance(
                title="Fill missing target points for this level",
                studio_location=(
                    "Open the reported level in GameBus Studio.",
                    "Use the Level settings section.",
                ),
                fields_to_check=(
                    "Level settings → Target points.",
                ),
                fix_steps=(
                    "Fill Target points with the intended numeric target.",
                    "If this level should not use target points, verify whether it should be part of the point-target progression checked by this validator.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

        if check == TEXTPOINTSCONSISTENCY:
            return GameBusFixGuidance(
                title="Make task text and awarded points match",
                studio_location=(
                    "Open the reported challenge/level in GameBus Studio.",
                    "In the Tasks section, open the reported task.",
                ),
                fields_to_check=(
                    "Task → Short task description.",
                    "Task → Description.",
                    "Task → Number of points to award.",
                ),
                fix_steps=(
                    "Find the point value mentioned in the task text.",
                    "Compare it with Number of points to award.",
                    "If the text is wrong, correct the point value in Short task description or Description.",
                    "If the configuration is wrong, change Number of points to award.",
                    "For bilingual text, check both language versions before deciding which value is wrong.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

        if check == DUPLICATETASKNAMES:
            return GameBusFixGuidance(
                title="Distinguish duplicate task names or align their settings",
                studio_location=(
                    "Open each challenge/level listed in the finding.",
                    "In each level, open the task with the duplicated Short task description.",
                ),
                fields_to_check=(
                    "Task → Short task description.",
                    "Task → Description.",
                    "Task → Number of points to award.",
                    "Task → Reward count.",
                    "Task → Time window for resetting the reward count.",
                    "Task → Allowed activity types.",
                    "Task → Allowed data sources.",
                    "Conditions → Property / Operator / Value.",
                ),
                fix_steps=(
                    "If the tasks are meant to behave differently, rename them so the difference is visible to editors and participants.",
                    "If the tasks are meant to be the same, align their settings.",
                    "If the duplicate name is intentional across levels, keep it and treat the finding as a warning.",
                    "Use the finding message to compare the listed challenge references.",
                ),
                verification=_GENERIC_VERIFICATION,
            ).as_markdown()

    return ""


def get_gamebus_fix_guidance(check_id: str | None) -> GameBusFixGuidance | None:
    """Return deterministic GameBus Studio guidance for a checker id."""
    if not check_id:
        return None
    return _FIX_GUIDANCE_BY_CHECK.get(str(check_id).lower())


def gamebus_fix_guidance_markdown_for_issue(issue: dict[str, Any]) -> str:
    """Return the best deterministic guidance for a checker finding.

    Specific issue guidance is preferred. Generic check-level guidance is used
    only as a fallback when the concrete issue subtype is not recognized.
    """
    specific = _specific_guidance_markdown(issue)
    if specific:
        return specific

    guidance = get_gamebus_fix_guidance(issue.get("check"))
    if guidance is None:
        return ""

    return guidance.as_markdown()


def checks_with_gamebus_fix_guidance() -> set[str]:
    return set(_FIX_GUIDANCE_BY_CHECK)