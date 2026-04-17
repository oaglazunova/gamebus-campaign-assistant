from __future__ import annotations

from pathlib import Path
from typing import Any

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.agents.capability_utils import module_is_enabled
from campaign_assistant.orchestration.models import AgentContext, AgentResponse


class TheoryGroundingAgent(BaseAgent):
    """
    Capability-aware theory grounding with backward-compatible fallback behavior.

    Rules:
    - If capability summary explicitly disables TTM, skip it.
    - If capability summary is absent, fall back to analysis_profile / selected_checks.
    - If TTM is active but theory files are missing, surface warnings.
    - Count task roles from metadata bundle if present, otherwise from context.task_roles.
    """

    name = "theory_grounding_agent"

    def _resolve_uses_ttm(self, context: AgentContext) -> bool:
        capability_summary = context.shared.get("capability_summary", {}) or {}
        capabilities = capability_summary.get("capabilities", {}) or {}

        if capabilities.get("uses_ttm") is not None:
            return capabilities.get("uses_ttm") is True

        intervention_model = (context.analysis_profile or {}).get("intervention_model", {}) or {}
        if intervention_model.get("uses_ttm") is not None:
            return intervention_model.get("uses_ttm") is True

        return "ttm" in (context.selected_checks or [])

    def _resolve_ttm_enabled(self, context: AgentContext, uses_ttm: bool) -> bool:
        capability_summary = context.shared.get("capability_summary", {}) or {}
        active_modules = capability_summary.get("active_modules", {}) or {}

        if "ttm_checks" in active_modules:
            return bool(active_modules["ttm_checks"])

        return uses_ttm

    def _collect_task_role_counts(self, context: AgentContext) -> dict[str, int]:
        counts: dict[str, int] = {}

        metadata_bundle = context.shared.get("metadata_bundle")
        if metadata_bundle is not None and getattr(metadata_bundle, "task_roles", None):
            items = metadata_bundle.task_roles
        else:
            items = context.task_roles or []

        for item in items:
            if isinstance(item, dict):
                role = str(item.get("role", "") or "").strip().lower()
            else:
                role = str(getattr(item, "role", "") or "").strip().lower()

            if not role:
                continue
            counts[role] = counts.get(role, 0) + 1

        return counts

    def _detect_theory_files(self, context: AgentContext) -> tuple[bool, bool]:
        if context.workspace_root is None:
            return False, False

        theory_dir = Path(context.workspace_root) / "evidence" / "theory"
        ttm_exists = (theory_dir / "ttm_structure.pdf").exists()
        mapping_exists = (theory_dir / "intervention_mapping.xlsx").exists()
        return ttm_exists, mapping_exists

    def run(self, context: AgentContext) -> AgentResponse:
        uses_ttm = self._resolve_uses_ttm(context)
        ttm_enabled = self._resolve_ttm_enabled(context, uses_ttm)

        task_role_counts = self._collect_task_role_counts(context)
        ttm_file_exists, mapping_file_exists = self._detect_theory_files(context)

        result = context.shared.get("result", {}) or {}
        failed_checks = (result.get("summary", {}) or {}).get("failed_checks", []) or []
        failed_checks_seen = [x for x in failed_checks if x in {"ttm"}]

        # ---- TTM not applicable for this campaign ----
        if not uses_ttm or not ttm_enabled:
            payload = {
                "confidence": "not_applicable",
                "uses_ttm": uses_ttm,
                "uses_bct_mapping": False,
                "uses_comb_mapping": False,
                "ttm_structure_file_exists": ttm_file_exists,
                "intervention_mapping_file_exists": mapping_file_exists,
                "mapping_summary": {
                    "exists": mapping_file_exists,
                },
                "task_role_counts": task_role_counts,
                "notes": [
                    "TTM grounding was skipped because the campaign capability profile does not enable TTM."
                ],
                "stage_notes": {},
                "failed_checks_seen": failed_checks_seen,
            }
            context.shared["theory_grounding"] = payload
            return AgentResponse(
                agent_name=self.name,
                success=True,
                summary="Theory grounding skipped because TTM is not enabled for this campaign.",
                payload=payload,
                warnings=[],
            )

        # ---- TTM is enabled ----
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

        stage_notes = {
            "precontemplation": "Often more awareness/reflection oriented.",
            "contemplation": "Often more evaluation and motivation oriented.",
            "preparation": "Often more planning and gatekeeping-sensitive.",
            "action": "Often more execution and tracking oriented.",
            "maintenance": "Often more sustainment and relapse-sensitive.",
        }

        payload = {
            "confidence": confidence,
            "uses_ttm": True,
            "uses_bct_mapping": False,
            "uses_comb_mapping": False,
            "ttm_structure_file_exists": ttm_file_exists,
            "intervention_mapping_file_exists": mapping_file_exists,
            "mapping_summary": {
                "exists": mapping_file_exists,
            },
            "task_role_counts": task_role_counts,
            "notes": notes,
            "stage_notes": stage_notes,
            "failed_checks_seen": failed_checks_seen,
        }

        context.shared["theory_grounding"] = payload

        return AgentResponse(
            agent_name=self.name,
            success=True,
            summary="Theory grounding completed in TTM mode.",
            payload=payload,
            warnings=warnings,
        )