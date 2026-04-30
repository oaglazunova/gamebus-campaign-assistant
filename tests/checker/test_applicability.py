from __future__ import annotations

from campaign_assistant.checker.applicability import (
    apply_capability_applicability,
    build_campaign_setup_hints,
)


def test_build_campaign_setup_hints_for_progression_campaign_with_missing_metadata():
    capability_summary = {
        "capabilities": {
            "uses_progression": True,
            "uses_gatekeeping": None,
            "uses_maintenance_tasks": None,
            "uses_ttm": None,
        },
        "task_role_count": 0,
    }

    hints = build_campaign_setup_hints(capability_summary)

    assert any("gatekeeping" in h.lower() for h in hints)
    assert any("maintenance" in h.lower() for h in hints)
    assert any("ttm" in h.lower() for h in hints)
    assert any("task-role" in h.lower() for h in hints)


def test_apply_capability_applicability_marks_point_checks_not_applicable():
    result = {
        "point_gatekeeping": {
            "summary": {},
            "warnings": [],
        }
    }
    capability_summary = {
        "capabilities": {
            "uses_progression": False,
        },
        "active_modules": {
            "point_gatekeeping_checks": False,
        },
    }

    updated = apply_capability_applicability(result, capability_summary)

    assert updated["point_gatekeeping"]["applicability"]["status"] == "not_applicable"


def test_apply_capability_applicability_marks_point_checks_partial_when_gatekeeping_unknown():
    result = {
        "point_gatekeeping": {
            "summary": {},
            "warnings": [],
        }
    }
    capability_summary = {
        "capabilities": {
            "uses_progression": True,
            "uses_gatekeeping": None,
        },
        "active_modules": {
            "point_gatekeeping_checks": True,
        },
    }

    updated = apply_capability_applicability(result, capability_summary)

    assert updated["point_gatekeeping"]["applicability"]["status"] == "partial"
    assert "gatekeeping semantics" in updated["point_gatekeeping"]["applicability"]["reason"]