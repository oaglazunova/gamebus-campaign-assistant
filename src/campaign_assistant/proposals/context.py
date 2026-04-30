from __future__ import annotations

from copy import deepcopy
from typing import Any


_GATEKEEPING_FAMILIES = {
    "missing_explicit_gatekeeper",
    "gatekeeping_not_required_by_points",
}

_MAINTENANCE_FAMILIES = {
    "missing_explicit_maintenance",
}

_POINT_FAMILIES = {
    "missing_target_points",
    "unreachable_target_points",
    "gatekeeping_not_required_by_points",
}

_TTM_FAMILIES = {
    "ttm_manual_review",
}


def annotate_proposal_groups_with_context(
    groups: list[dict[str, Any]],
    capability_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    capabilities = capability_summary.get("capabilities", {}) or {}
    uses_progression = capabilities.get("uses_progression")
    uses_gatekeeping = capabilities.get("uses_gatekeeping")
    uses_maintenance = capabilities.get("uses_maintenance_tasks")
    uses_ttm = capabilities.get("uses_ttm")
    task_role_count = int(capability_summary.get("task_role_count", 0) or 0)

    annotated: list[dict[str, Any]] = []

    for group in groups:
        item = deepcopy(group)
        issue_family = str(item.get("issue_family") or "")
        tags: list[str] = []
        priority = "normal"
        reason = ""

        if issue_family in _POINT_FAMILIES or issue_family in _GATEKEEPING_FAMILIES or issue_family in _MAINTENANCE_FAMILIES:
            tags.append("progression")

        if issue_family in _GATEKEEPING_FAMILIES:
            tags.append("gatekeeping")

        if issue_family in _MAINTENANCE_FAMILIES:
            tags.append("maintenance")

        if issue_family in _POINT_FAMILIES:
            tags.append("points")

        if issue_family in _TTM_FAMILIES:
            tags.append("ttm")

        # Priority rules
        if issue_family in _TTM_FAMILIES:
            if uses_ttm is True:
                priority = "recommended"
                reason = "TTM is enabled for this campaign, so this group should be reviewed."
            elif uses_ttm is False:
                priority = "deprioritized"
                reason = "TTM is not enabled for this campaign."
            else:
                priority = "normal"
                reason = "TTM relevance has not been confirmed yet."

        elif issue_family in _GATEKEEPING_FAMILIES:
            if uses_progression is False:
                priority = "deprioritized"
                reason = "Progression is not enabled for this campaign."
            elif task_role_count == 0:
                priority = "recommended"
                reason = "Progression appears relevant, but task-role metadata is missing."
                tags.append("setup-needed")
            elif uses_gatekeeping is None:
                priority = "recommended"
                reason = "Gatekeeping semantics are not explicitly confirmed yet."
                tags.append("setup-needed")
            elif uses_progression is True:
                priority = "recommended"
                reason = "Progression-aware gatekeeping review is relevant for this campaign."

        elif issue_family in _MAINTENANCE_FAMILIES:
            if uses_progression is False:
                priority = "deprioritized"
                reason = "Progression is not enabled for this campaign."
            elif task_role_count == 0:
                priority = "recommended"
                reason = "Progression appears relevant, but maintenance/task-role metadata is missing."
                tags.append("setup-needed")
            elif uses_maintenance is None:
                priority = "recommended"
                reason = "Maintenance semantics are not explicitly confirmed yet."
                tags.append("setup-needed")
            elif uses_progression is True:
                priority = "recommended"
                reason = "Maintenance/relapse-related review is relevant for this campaign."

        elif issue_family in _POINT_FAMILIES:
            if uses_progression is False:
                priority = "deprioritized"
                reason = "Progression is not enabled for this campaign."
            elif uses_progression is True:
                priority = "recommended"
                reason = "Point structure is relevant because this campaign uses progression."
            else:
                priority = "normal"
                reason = "Point-logic relevance has not been explicitly confirmed yet."

        item["context_tags"] = sorted(set(tags))
        item["priority"] = priority
        item["priority_reason"] = reason
        annotated.append(item)

    return annotated


def matches_group_focus(group: dict[str, Any], focus: str) -> bool:
    issue_family = str(group.get("issue_family") or "")
    tags = set(group.get("context_tags") or [])
    priority = str(group.get("priority") or "normal")

    if focus == "All":
        return True
    if focus == "Recommended now":
        return priority == "recommended"
    if focus == "Gatekeeping setup":
        return issue_family in _GATEKEEPING_FAMILIES or "gatekeeping" in tags
    if focus == "Maintenance setup":
        return issue_family in _MAINTENANCE_FAMILIES or "maintenance" in tags
    if focus == "Point fixes":
        return issue_family in _POINT_FAMILIES or "points" in tags
    if focus == "TTM review":
        return issue_family in _TTM_FAMILIES or "ttm" in tags

    return True