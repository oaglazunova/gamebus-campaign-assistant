from __future__ import annotations

from typing import Any


def build_privacy_diagnostics_model(privacy_report: dict[str, Any] | None) -> dict[str, Any]:
    report = dict(privacy_report or {})

    policy_mode = str(report.get("policy_mode") or "unknown")
    has_workspace_overrides = bool(report.get("has_workspace_overrides", False))
    overridden_agents = list(report.get("overridden_agents", []) or [])
    override_warning_count = int(report.get("override_warning_count", 0) or 0)
    override_warnings = list(report.get("override_warnings", []) or [])
    raw_workbook_allowed_agents = list(report.get("raw_workbook_allowed_agents", []) or [])
    sanitized_only_agents = list(report.get("sanitized_only_agents", []) or [])
    semantic_agents_requiring_views = list(report.get("semantic_agents_requiring_views", []) or [])
    policy_sources_by_agent = dict(report.get("policy_sources_by_agent", {}) or {})

    if override_warning_count > 0:
        status = "warning"
    elif has_workspace_overrides:
        status = "customized"
    else:
        status = "baseline"

    return {
        "status": status,
        "policy_mode": policy_mode,
        "has_workspace_overrides": has_workspace_overrides,
        "overridden_agents": overridden_agents,
        "override_warning_count": override_warning_count,
        "override_warnings": override_warnings,
        "raw_workbook_allowed_agents": raw_workbook_allowed_agents,
        "sanitized_only_agents": sanitized_only_agents,
        "semantic_agents_requiring_views": semantic_agents_requiring_views,
        "policy_sources_by_agent": policy_sources_by_agent,
        "has_any_diagnostics": bool(
            policy_mode != "unknown"
            or has_workspace_overrides
            or overridden_agents
            or raw_workbook_allowed_agents
            or sanitized_only_agents
            or override_warnings
        ),
    }