from __future__ import annotations

from campaign_assistant.metadata.models import CampaignCapabilities, TaskRoleAnnotation


_ALLOWED_TASK_ROLES = {
    "gatekeeping",
    "maintenance",
    "transition",
    "optional",
    "supporting",
}


def validate_capabilities(capabilities: CampaignCapabilities) -> list[str]:
    issues: list[str] = []

    # Example consistency rules. Keep this intentionally lightweight for now.
    if capabilities.uses_gatekeeping is True and capabilities.uses_progression is False:
        issues.append("uses_gatekeeping=True is unusual when uses_progression=False.")

    if capabilities.uses_maintenance_tasks is True and capabilities.uses_progression is False:
        issues.append("uses_maintenance_tasks=True is unusual when uses_progression=False.")

    return issues


def validate_task_roles(task_roles: list[TaskRoleAnnotation]) -> list[str]:
    issues: list[str] = []

    seen: set[tuple[str, str]] = set()
    for item in task_roles:
        if not item.task_name.strip():
            issues.append("Task role annotation has an empty task_name.")
        if item.role.strip() and item.role.strip().lower() not in _ALLOWED_TASK_ROLES:
            issues.append(f"Unsupported task role '{item.role}'.")
        key = item.normalized_key()
        if key in seen and key[0]:
            issues.append(f"Duplicate task role annotation for task '{item.task_name}' and role '{item.role}'.")
        seen.add(key)

    return issues