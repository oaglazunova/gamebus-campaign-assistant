from __future__ import annotations

from typing import Any

from campaign_assistant.checker.schema import GATEKEEPINGSEMANTICS
from campaign_assistant.reasoning import PointGatekeepingService


def _capabilities(capability_summary: dict[str, Any] | None) -> dict[str, Any]:
    return dict((capability_summary or {}).get("capabilities", {}) or {})


def _warnings_lower(finding: dict[str, Any]) -> list[str]:
    return [str(item).strip().lower() for item in (finding.get("warnings") or [])]


class WorkspaceReadinessService:
    """
    Internal readiness assessment.

    This is not a user-selectable check.
    It decides whether stronger gatekeeping semantics validation can run.
    """

    def __init__(self) -> None:
        self.point_gatekeeping = PointGatekeepingService()

    def analyze(
        self,
        *,
        campaign_file: str,
        capability_summary: dict[str, Any] | None,
        point_rules: dict[str, Any] | None,
        task_roles: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        capabilities = _capabilities(capability_summary)
        uses_progression = capabilities.get("uses_progression")

        if uses_progression is False:
            return {
                "progression_applicable": False,
                "progression_basics_available": False,
                "gatekeeping_semantics_ready": False,
                "gatekeeping_annotations_present": False,
                "maintenance_annotations_present": False,
                "reasons": [
                    "Progression-related validation is not applicable because this campaign is marked as not using progression."
                ],
                "actions": [],
                "disabled_checks": {
                    GATEKEEPINGSEMANTICS: {
                        "reason": "Disabled because progression is not applicable.",
                        "action": None,
                    }
                },
                "point_readiness_summary": {
                    "challenge_findings": 0,
                    "missing_gatekeeping_annotation_count": 0,
                    "missing_maintenance_annotation_count": 0,
                },
            }

        payload = self.point_gatekeeping.analyze(
            campaign_file=campaign_file,
            point_rules=point_rules or {},
            task_roles=task_roles or [],
        )

        findings = list(payload.get("findings") or [])

        missing_gatekeeping_challenges: list[str] = []
        missing_maintenance_challenges: list[str] = []

        for finding in findings:
            warnings = _warnings_lower(finding)
            challenge_name = str(finding.get("challenge_name") or "Unknown challenge")

            if any("no explicit gatekeeping task is marked" in item for item in warnings):
                missing_gatekeeping_challenges.append(challenge_name)

            if any("no explicit maintenance tasks are annotated" in item for item in warnings):
                missing_maintenance_challenges.append(challenge_name)

        gatekeeping_annotations_present = len(missing_gatekeeping_challenges) == 0
        maintenance_annotations_present = len(missing_maintenance_challenges) == 0
        gatekeeping_semantics_ready = (
            gatekeeping_annotations_present and maintenance_annotations_present
        )

        reasons: list[str] = []
        actions: list[dict[str, Any]] = []

        if not gatekeeping_annotations_present:
            reasons.append(
                "Gatekeeping semantics checks are disabled because explicit gatekeeping annotations are missing."
            )

        if not maintenance_annotations_present:
            reasons.append(
                "Gatekeeping semantics checks are disabled because maintenance annotations are missing for progression-sensitive challenges."
            )

        if not gatekeeping_semantics_ready:
            actions.append(
                {
                    "action_id": "open_task_role_annotations",
                    "label": "Annotate task roles",
                    "focus": "task_roles",
                }
            )

        disabled_reason = (
            "Enabled."
            if gatekeeping_semantics_ready
            else "Disabled until required task-role annotations are added in the workspace."
        )

        return {
            "progression_applicable": True,
            "progression_basics_available": True,
            "gatekeeping_semantics_ready": gatekeeping_semantics_ready,
            "gatekeeping_annotations_present": gatekeeping_annotations_present,
            "maintenance_annotations_present": maintenance_annotations_present,
            "reasons": reasons,
            "actions": actions,
            "disabled_checks": {
                GATEKEEPINGSEMANTICS: {
                    "reason": disabled_reason,
                    "action": actions[0] if actions else None,
                }
            },
            "point_readiness_summary": {
                "challenge_findings": len(findings),
                "missing_gatekeeping_annotation_count": len(missing_gatekeeping_challenges),
                "missing_maintenance_annotation_count": len(missing_maintenance_challenges),
                "missing_gatekeeping_challenges": missing_gatekeeping_challenges,
                "missing_maintenance_challenges": missing_maintenance_challenges,
            },
        }