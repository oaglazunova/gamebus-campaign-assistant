from __future__ import annotations

from typing import Any


def build_workspace_readiness_model(result: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {
            "has_readiness": False,
            "progression_applicable": False,
            "progression_basics_available": False,
            "gatekeeping_semantics_ready": False,
            "gatekeeping_annotations_present": False,
            "maintenance_annotations_present": False,
            "reasons": [],
            "actions": [],
            "point_readiness_summary": {},
            "status": "unknown",
        }

    assistant_meta = dict(result.get("assistant_meta", {}) or {})
    readiness = dict(assistant_meta.get("workspace_readiness", {}) or {})

    if not readiness:
        return {
            "has_readiness": False,
            "progression_applicable": False,
            "progression_basics_available": False,
            "gatekeeping_semantics_ready": False,
            "gatekeeping_annotations_present": False,
            "maintenance_annotations_present": False,
            "reasons": [],
            "actions": [],
            "point_readiness_summary": {},
            "status": "unknown",
        }

    progression_applicable = bool(readiness.get("progression_applicable", False))
    progression_basics_available = bool(readiness.get("progression_basics_available", False))
    gatekeeping_semantics_ready = bool(readiness.get("gatekeeping_semantics_ready", False))
    gatekeeping_annotations_present = bool(readiness.get("gatekeeping_annotations_present", False))
    maintenance_annotations_present = bool(readiness.get("maintenance_annotations_present", False))
    reasons = list(readiness.get("reasons", []) or [])
    actions = list(readiness.get("actions", []) or [])
    point_readiness_summary = dict(readiness.get("point_readiness_summary", {}) or {})

    if not progression_applicable:
        status = "not_applicable"
    elif gatekeeping_semantics_ready:
        status = "ready"
    else:
        status = "needs_annotations"

    return {
        "has_readiness": True,
        "progression_applicable": progression_applicable,
        "progression_basics_available": progression_basics_available,
        "gatekeeping_semantics_ready": gatekeeping_semantics_ready,
        "gatekeeping_annotations_present": gatekeeping_annotations_present,
        "maintenance_annotations_present": maintenance_annotations_present,
        "reasons": reasons,
        "actions": actions,
        "point_readiness_summary": point_readiness_summary,
        "status": status,
    }