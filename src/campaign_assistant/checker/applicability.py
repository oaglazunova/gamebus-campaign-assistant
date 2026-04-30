from __future__ import annotations

from copy import deepcopy
from typing import Any


def build_campaign_setup_hints(capability_summary: dict[str, Any]) -> list[str]:
    capabilities = capability_summary.get("capabilities", {}) or {}
    task_role_count = int(capability_summary.get("task_role_count", 0) or 0)

    hints: list[str] = []

    if capabilities.get("uses_progression") is None:
        hints.append(
            "Confirm whether this campaign uses progression levels or transition logic."
        )

    if capabilities.get("uses_progression") is True and capabilities.get("uses_gatekeeping") is None:
        hints.append(
            "Confirm whether progression depends on gatekeeping tasks. "
            "If yes, provide explicit task-role metadata in GameBus or task_roles.csv."
        )

    if capabilities.get("uses_progression") is True and capabilities.get("uses_maintenance_tasks") is None:
        hints.append(
            "Confirm whether maintenance tasks are relevant for relapse / at-risk logic. "
            "If yes, annotate them explicitly."
        )

    if capabilities.get("uses_ttm") is None:
        hints.append(
            "Confirm whether this campaign follows TTM. If yes, attach or register the TTM structure file."
        )

    if capabilities.get("uses_progression") is True and task_role_count == 0:
        hints.append(
            "No task-role annotations are currently available. "
            "Add gatekeeping / maintenance annotations to improve progression-aware checking."
        )

    return hints


def apply_capability_applicability(
    result: dict[str, Any],
    capability_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Post-process raw checker results so the assistant can distinguish:
    - active/applicable reasoning
    - not applicable reasoning
    - uncertain reasoning due to missing metadata
    """
    result = deepcopy(result)

    capabilities = capability_summary.get("capabilities", {}) or {}
    active_modules = capability_summary.get("active_modules", {}) or {}
    setup_hints = build_campaign_setup_hints(capability_summary)

    assistant_meta = result.setdefault("assistant_meta", {})
    assistant_meta["campaign_setup_hints"] = setup_hints

    # ---- Point / gatekeeping applicability ----
    point_gatekeeping = result.get("point_gatekeeping")
    if point_gatekeeping is not None:
        applicability: dict[str, Any]

        if active_modules.get("point_gatekeeping_checks") is False:
            applicability = {
                "status": "not_applicable",
                "reason": "This campaign does not appear to use progression logic.",
            }
        elif capabilities.get("uses_progression") is None:
            applicability = {
                "status": "uncertain",
                "reason": (
                    "The workbook looks partially progression-like, but progression metadata "
                    "has not been explicitly confirmed."
                ),
            }
        elif capabilities.get("uses_progression") is True and capabilities.get("uses_gatekeeping") is None:
            applicability = {
                "status": "partial",
                "reason": (
                    "Progression appears relevant, but gatekeeping semantics are not explicitly defined yet."
                ),
            }
        else:
            applicability = {
                "status": "active",
                "reason": "Progression-aware point checking is applicable for this campaign.",
            }

        point_gatekeeping["applicability"] = applicability

    # ---- Theory applicability (summary layer only; agent already handles runtime behavior) ----
    theory_grounding = result.get("theory_grounding")
    if theory_grounding is not None:
        if active_modules.get("ttm_checks") is False:
            theory_grounding["applicability"] = {
                "status": "not_applicable",
                "reason": "TTM is not enabled for this campaign.",
            }
        elif capabilities.get("uses_ttm") is None:
            theory_grounding["applicability"] = {
                "status": "uncertain",
                "reason": "TTM relevance has not been explicitly confirmed yet.",
            }
        else:
            theory_grounding["applicability"] = {
                "status": "active",
                "reason": "TTM grounding is active for this campaign.",
            }

    return result