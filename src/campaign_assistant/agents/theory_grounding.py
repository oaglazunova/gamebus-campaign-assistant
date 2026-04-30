from __future__ import annotations

from pathlib import Path
from typing import Any

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.orchestration.models import AgentContext, AgentResponse
from campaign_assistant.privacy import PrivacyService


class TheoryGroundingAgent(BaseAgent):
    name = "theory_grounding_agent"

    def __init__(self) -> None:
        self.privacy_service = PrivacyService()

    def _resolve_uses_ttm(
        self,
        *,
        capability_summary: dict[str, Any],
        metadata_summary: dict[str, Any],
        analysis_profile: dict[str, Any],
    ) -> bool:
        capabilities = capability_summary.get("capabilities", {}) or {}

        if capabilities.get("uses_ttm") is not None:
            return capabilities.get("uses_ttm") is True

        for source in metadata_summary.get("theory_sources", []) or []:
            tags = {str(x).strip().lower() for x in source.get("tags", []) or []}
            if "ttm" in tags or "transtheoretical_model" in tags:
                return True

        intervention_model = (analysis_profile or {}).get("intervention_model", {}) or {}
        if intervention_model.get("uses_ttm") is not None:
            return intervention_model.get("uses_ttm") is True

        return False

    def _resolve_ttm_enabled(self, capability_summary: dict[str, Any], uses_ttm: bool) -> bool:
        theory_applicability = capability_summary.get("theory_applicability", {}) or {}
        if "ttm_grounding" in theory_applicability:
            return bool(theory_applicability["ttm_grounding"])

        validator_applicability = capability_summary.get("validator_applicability", {}) or {}
        if "ttm" in validator_applicability:
            return bool(validator_applicability["ttm"])

        active_modules = capability_summary.get("active_modules", {}) or {}
        if "ttm_checks" in active_modules:
            return bool(active_modules["ttm_checks"])

        return uses_ttm

    def _collect_task_role_counts(self, metadata_summary: dict[str, Any], fallback_task_roles: list[Any]) -> dict[str, int]:
        counts = dict(metadata_summary.get("task_role_counts", {}) or {})
        if counts:
            return counts

        fallback_counts: dict[str, int] = {}
        for item in fallback_task_roles or []:
            if isinstance(item, dict):
                role = str(item.get("role", "") or "").strip().lower()
            else:
                role = str(getattr(item, "role", "") or "").strip().lower()

            if not role:
                continue
            fallback_counts[role] = fallback_counts.get(role, 0) + 1

        return fallback_counts

    def _detect_theory_files(self, context: AgentContext) -> tuple[bool, bool]:
        if context.workspace_root is None:
            return False, False

        theory_dir = Path(context.workspace_root) / "evidence" / "theory"
        ttm_exists = (theory_dir / "ttm_structure.pdf").exists()
        mapping_exists = (theory_dir / "intervention_mapping.xlsx").exists()
        return ttm_exists, mapping_exists

    def run(self, context: AgentContext) -> AgentResponse:
        agent_view = self.privacy_service.get_required_agent_view(self.name, context)

        agent_run_id = agent_view.get("agent_run_id")

        capability_summary = agent_view.get("capability_summary", {})
        metadata_summary = agent_view.get("metadata_summary", {})
        analysis_profile = agent_view.get("analysis_profile", {})
        result = agent_view.get("result", {})

        uses_ttm = self._resolve_uses_ttm(
            capability_summary=capability_summary,
            metadata_summary=metadata_summary,
            analysis_profile=analysis_profile,
        )
        ttm_enabled = self._resolve_ttm_enabled(capability_summary, uses_ttm)

        task_role_counts = self._collect_task_role_counts(metadata_summary, context.task_roles)
        ttm_file_exists, mapping_file_exists = self._detect_theory_files(context)

        failed_checks = (result.get("summary", {}) or {}).get("failed_checks", []) or []
        failed_checks_seen = [x for x in failed_checks if x == "ttm"]
        theory_source_count = metadata_summary.get("theory_source_count", 0)

        if not uses_ttm or not ttm_enabled:
            payload = {
                "confidence": "not_applicable",
                "uses_ttm": uses_ttm,
                "theory_source_count": theory_source_count,
                "ttm_structure_file_exists": ttm_file_exists,
                "intervention_mapping_file_exists": mapping_file_exists,
                "mapping_summary": {
                    "exists": mapping_file_exists,
                    "path": "evidence/theory/intervention_mapping.xlsx",
                },
                "task_role_counts": task_role_counts,
                "notes": [
                    "TTM grounding was skipped because the campaign capability profile does not enable TTM."
                ],
                "stage_notes": {},
                "failed_checks_seen": failed_checks_seen,
            }
            context.shared["theory_grounding"] = payload

            self.privacy_service.record_agent_outcome(
                agent_name=self.name,
                context=context,
                agent_run_id=agent_run_id,
                success=True,
                payload=payload,
                warnings=[],
                notes=payload["notes"],
            )

            return AgentResponse(
                agent_name=self.name,
                success=True,
                summary="Theory grounding skipped because TTM is not enabled for this campaign.",
                payload=payload,
                warnings=[],
            )

        warnings: list[str] = []
        notes: list[str] = []

        if not ttm_file_exists:
            warnings.append("TTM structure file is missing.")
        if not mapping_file_exists:
            warnings.append("Intervention mapping file is missing.")

        if failed_checks_seen:
            notes.append("TTM-related failure was reported by the structural checker.")
            confidence = "medium"
        elif warnings:
            notes.append("Theory grounding is operating with incomplete theory resources.")
            confidence = "low"
        else:
            notes.append("No direct TTM conflict was detected in the current structural result.")
            confidence = "medium"

        payload = {
            "confidence": confidence,
            "uses_ttm": True,
            "theory_source_count": theory_source_count,
            "ttm_structure_file_exists": ttm_file_exists,
            "intervention_mapping_file_exists": mapping_file_exists,
            "mapping_summary": {
                "exists": mapping_file_exists,
                "path": "evidence/theory/intervention_mapping.xlsx",
            },
            "task_role_counts": task_role_counts,
            "notes": notes,
            "stage_notes": {
                "precontemplation": "Often more awareness/reflection oriented.",
                "contemplation": "Often more evaluation and motivation oriented.",
                "preparation": "Often more planning and gatekeeping-sensitive.",
                "action": "Often more execution and tracking oriented.",
                "maintenance": "Often more sustainment and relapse-sensitive.",
            },
            "failed_checks_seen": failed_checks_seen,
        }

        context.shared["theory_grounding"] = payload

        self.privacy_service.record_agent_outcome(
            agent_name=self.name,
            context=context,
            agent_run_id=agent_run_id,
            success=True,
            payload=payload,
            warnings=warnings,
            notes=notes,
        )

        return AgentResponse(
            agent_name=self.name,
            success=True,
            summary="Theory grounding completed in TTM mode.",
            payload=payload,
            warnings=warnings,
        )