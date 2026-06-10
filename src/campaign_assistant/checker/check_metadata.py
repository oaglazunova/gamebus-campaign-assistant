from __future__ import annotations

from campaign_assistant.checker.schema import (
    CONSISTENCY,
    REACHABILITY,
    SECRETS,
    SPELLCHECKER,
    TARGETPOINTSREACHABLE,
    TTMSTRUCTURE,
    VISUALIZATIONINTERN,
)


CHECK_HINTS: dict[str, str] = {
    SECRETS: "Missing or conflicting SECRET conditions.",
    SPELLCHECKER: "German-only spellcheck for task and challenge names.",
    REACHABILITY: "Whether initial levels can reach terminal success levels.",
    CONSISTENCY: "Basic level-transition consistency, especially initial and terminal levels.",
    VISUALIZATIONINTERN: "Whether reachable terminal levels stay within the expected visualization and label structure.",
    TARGETPOINTSREACHABLE: "A challenge target can be reached from its task points and timing settings.",
    TTMSTRUCTURE: (
        "HW8 long-term-campaign-specific TTM progression check. "
        "May report false issues for campaigns with different progression logic."
    ),
}


PRIORITY_HINT = (
    "Findings are prioritized by priority_score = severity_score + active_wave_boost. "
    "The severity_score is each issue's check severity: reachability = high, "
    "consistency = high, visualization internals = medium, target points reachable = high, "
    "secrets = medium, spellchecker = low, TTM structure = medium. "
    "Scores: high = 300, medium = 200, low = 100, active_wave_boost = +50 when the wave is active."
)


CHECK_EXPLANATIONS: dict[str, str] = {
    SECRETS: (
        "**Secrets check** reads the `tasks`, `challenges`, `visualizations`, and `waves` sheets. "
        "For each row in `tasks` where `dataproviders == 'GameBus Studio'`, the check parses the task "
        "conditions and extracts bracketed triples such as `[SECRET, EQUAL, value]`. "
        "A task is reported if no `SECRET/EQUAL` triple is found; the proposed secret is generated from "
        "the task name by replacing spaces and some special characters. If the same secret is used by "
        "more than one task with different names, a duplicate-secret issue is reported. "
        "Severity: medium."
    ),
    SPELLCHECKER: (
        "**Spellchecker** reads the `tasks`, `challenges`, `visualizations`, and `waves` sheets. "
        "It runs LanguageTool for German (`de-DE`) on task names and challenge names only. "
        "Empty names are reported. For non-empty text, LanguageTool matches are classified: faulty text "
        "is reported with a proposed correction, and garbage text is reported without a correction. "
        "Known campaign words such as `Newbie`, `Rookie`, `Wall-Sit`, `MIND`, `Mikrobiota`, and several "
        "German terms are passed to LanguageTool as accepted spellings. If LanguageTool is unavailable, "
        "the check returns `Passed` with a note that spellchecking was skipped. Active-wave status is "
        "derived from the parent visualization wave. Severity: low. Disabled by default."
    ),
    REACHABILITY: (
        "**Reachability check** reads the `visualizations`, `challenges`, and `waves` sheets. "
        "For each visualization, the check selects challenges whose `visualizations` value equals that "
        "visualization id. Initial challenges are rows where `is_initial_level == 1`. Terminal challenges "
        "are rows where `success_next` equals the challenge's own id. Reachability is computed by following "
        "`success_next` links recursively; `failure_next` is not followed by this check. An initial challenge "
        "is reported if no terminal challenge in the same visualization can be reached from it. A terminal "
        "challenge is reported if it cannot be reached from any initial challenge in the same visualization. "
        "Cycles are stopped using visited challenge ids. Severity: high."
    ),
    CONSISTENCY: (
        "**Consistency check** reads the `visualizations`, `challenges`, and `waves` sheets. "
        "For each visualization, the check selects challenges whose `visualizations` value equals that "
        "visualization id. It reports an initial challenge when `is_initial_level == 1` and `failure_next` "
        "does not equal the challenge's own id. It finds terminal challenges by resolving `success_next` "
        "and checking whether the resolved next challenge has the same id as the current challenge; such "
        "terminal challenges are expected to lead to themselves on success. Active-wave status is derived "
        "from the visualization wave. Severity: high."
    ),
    VISUALIZATIONINTERN: (
        "**Visualization internals check** reads the `visualizations`, `challenges`, and `waves` sheets. "
        "For each visualization, the check starts from initial challenges where `is_initial_level == 1`. "
        "From each initial challenge, it recursively follows both `success_next` and `failure_next` until "
        "it finds terminal challenges, where a terminal challenge is one whose resolved `success_next` "
        "points back to itself. Each reachable terminal challenge is compared with the initial challenge. "
        "If the reachable terminal challenge is not in the same visualization or does not have the same "
        "`labels` value, an issue is reported. Severity: medium."
    ),
    TARGETPOINTSREACHABLE: (
        "**Target points reachable check** reads the `tasks`, `challenges`, `visualizations`, and `waves` sheets. "
        "For each challenge, the check finds tasks with `challenge` value equal to the challenge id. "
        "It converts the challenge duration from `evaluate_fail_every_x_minutes` into days: "
        "`days_for_level = minutes / (24 * 60)`. For each task it reads `points`, `max_times_fired`, "
        "and `min_days_between_fire`. If any of these values are missing or non-numeric, if "
        "`min_days_between_fire <= 0`, or if the challenge duration is missing, reachable points cannot "
        "be computed and an issue is reported. Otherwise, for each task it computes "
        "`p = floor(days_for_level / min_days_between_fire)`, then "
        "`max_times_for_task = p * max_times_fired + min(days_for_level - p * min_days_between_fire, max_times_fired)`, "
        "and `max_points_for_task = max_times_for_task * points`. The task maxima are summed for the challenge. "
        "If the sum is lower than the challenge target, the target is reported as unreachable. If the target "
        "itself is missing or non-numeric, the challenge is also reported. Active-wave status is derived from "
        "the visualization wave. Severity: high."
    ),
    TTMSTRUCTURE: (
        "**TTM structure check** reads the `visualizations`, `challenges`, and `waves` sheets. "
        "This check is specific to the HW8 long-term-campaign TTM-like progression structure and is disabled "
        "by default. It runs on all visualizations when selected. Starting from each initial challenge, it follows "
        "the `success_next` progression chain. For the first four non-relapse levels, the check expects "
        "`failure_next` to point back to the same challenge. After these four levels, it expects relapse-aware "
        "logic: a non-terminal challenge should fail to an at-risk level; that at-risk level should fail back "
        "to the previous level and succeed back to the current level. A terminal challenge should fail back to "
        "the previous level. This is not a universal TTM validator and may report false issues for campaigns "
        "with different progression logic. Severity: medium."
    ),
}


def check_explanation(check_id: str) -> str:
    """Return the detailed Assistant explanation for a deterministic checker."""
    return CHECK_EXPLANATIONS.get(check_id, "")


def check_hint(check_id: str) -> str:
    """Return the short UI hover hint for a deterministic checker."""
    return CHECK_HINTS.get(check_id, "")