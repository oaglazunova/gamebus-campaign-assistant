from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.agents.capability_utils import capability_is_true, module_is_enabled
from campaign_assistant.orchestration.models import AgentContext, AgentResponse


class ContentFixerAgent(BaseAgent):
    """
    Deterministic repair proposal generator.

    Current scope:
    - generate structured repair proposals from existing findings
    - capability-aware: only propose progression/TTM-related fixes when relevant

    Not yet implemented:
    - LLM rewriting
    - patched Excel generation directly here
    - GameBus write-back
    """

    name = "content_fixer_agent"


    def _resolve_uses_ttm(self, context: AgentContext, theory_grounding: dict[str, Any]) -> bool:
        capability_summary = context.shared.get("capability_summary", {}) or {}
        capabilities = capability_summary.get("capabilities", {}) or {}

        if capabilities.get("uses_ttm") is not None:
            return capabilities.get("uses_ttm") is True

        if theory_grounding.get("uses_ttm") is not None:
            return theory_grounding.get("uses_ttm") is True

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


    def _resolved_task_roles(self, context: AgentContext) -> list[dict[str, Any]]:
        metadata_bundle = context.shared.get("metadata_bundle")
        if metadata_bundle is not None and getattr(metadata_bundle, "task_roles", None):
            items = metadata_bundle.task_roles
        else:
            items = context.task_roles or []

        rows: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict):
                rows.append(item)
            else:
                rows.append(
                    {
                        "task_id": getattr(item, "task_id", "") or "",
                        "task_name": getattr(item, "task_name", "") or "",
                        "role": getattr(item, "role", "") or "",
                        "notes": getattr(item, "notes", "") or "",
                    }
                )
        return rows

    def _has_any_task_role_annotations(self, context: AgentContext) -> bool:
        return len(self._resolved_task_roles(context)) > 0

    def _is_gatekeeping_setup_complete(self, context: AgentContext) -> bool:
        capability_summary = context.shared.get("capability_summary", {}) or {}
        capabilities = capability_summary.get("capabilities", {}) or {}

        if capabilities.get("uses_progression") is False:
            return False

        # If explicit task-role metadata exists, we consider setup complete enough
        # to begin stronger gatekeeping-point reasoning.
        if self._has_any_task_role_annotations(context):
            return True

        # If the campaign explicitly says it uses gatekeeping but no annotations exist yet,
        # setup is still incomplete for strong proposal generation.
        if capabilities.get("uses_gatekeeping") is True:
            return False

        # Unknown or missing gatekeeping semantics -> incomplete.
        return False


    def _role_annotation_note(self, context: AgentContext, role_kind: str, challenge_name: str | None = None) -> str:
        profile = context.analysis_profile or {}
        prefs = profile.get("execution_preferences", {}) or {}
        target = str(prefs.get("role_annotation_target", "task_roles_csv")).strip().lower()

        if target == "gamebus":
            base = f"Mark the correct {role_kind} task explicitly in GameBus."
        elif target == "either":
            base = (
                f"Mark the correct {role_kind} task explicitly in task_roles.csv or in GameBus, "
                "depending on your current workflow."
            )
        else:
            base = (
                f"Mark the correct {role_kind} task explicitly in task_roles.csv. "
                "Once GameBus supports native role metadata, you can migrate it there."
            )

        if challenge_name:
            return f"{base} Challenge: '{challenge_name}'."
        return base

    def run(self, context: AgentContext) -> AgentResponse:
        profile = context.analysis_profile or {}
        checking_scope = profile.get("checking_scope", {})

        if not checking_scope.get("content_fix_suggestions", False):
            payload = {
                "enabled": False,
                "reason": "Content/fix suggestions are disabled in the analysis profile.",
                "proposals": [],
            }
            context.shared["fix_proposals"] = payload
            return AgentResponse(
                agent_name=self.name,
                success=True,
                summary="Content/fix proposals skipped because proposal generation is disabled in the workspace profile.",
                payload=payload,
            )

        progression_enabled = module_is_enabled(context, "point_gatekeeping_checks", default=True)

        structural_result = context.shared.get("result", {})
        point_gatekeeping = structural_result.get("point_gatekeeping", {})
        theory_grounding = context.shared.get("theory_grounding", {})

        uses_ttm = self._resolve_uses_ttm(context, theory_grounding)
        ttm_enabled = self._resolve_ttm_enabled(context, uses_ttm)

        gatekeeping_setup_complete = self._is_gatekeeping_setup_complete(context)

        proposals: list[dict[str, Any]] = []
        notes: list[str] = []

        if progression_enabled and not gatekeeping_setup_complete:
            notes.append(
                "Gatekeeping/task-role setup is incomplete, so some stronger gatekeeping-point proposals are deferred "
                "until explicit annotations are added."
            )

        # ---- Point/gatekeeping-driven proposals only if progression logic is relevant ----
        if progression_enabled:
            for idx, finding in enumerate(point_gatekeeping.get("findings", []), start=1):
                challenge_name = finding.get("challenge_name") or "Unknown challenge"
                target_points = finding.get("target_points")
                theoretical_max = finding.get("theoretical_max_points")
                explicit_gatekeepers = finding.get("explicit_gatekeepers") or []
                inferred_gatekeepers = finding.get("inferred_gatekeepers") or []

                warnings = finding.get("warnings") or []

                if any("no target points defined" in w.lower() for w in warnings):
                    proposals.append(
                        {
                            "proposal_id": f"fix-{idx}-missing-target",
                            "category": "points",
                            "challenge_name": challenge_name,
                            "severity": "high",
                            "action_type": "set_target_points",
                            "status": "proposed",
                            "rationale": (
                                "The challenge has no target points defined, so progression logic is incomplete."
                            ),
                            "suggested_change": {
                                "target_points": theoretical_max if theoretical_max not in (None, 0) else None,
                            },
                            "notes": (
                                "Review the suggested target before applying. "
                                "The current proposal uses the theoretical maximum as a safe placeholder."
                            ),
                        }
                    )

                if any("exceed the theoretical maximum" in w.lower() for w in warnings):
                    proposals.append(
                        {
                            "proposal_id": f"fix-{idx}-unreachable-target",
                            "category": "points",
                            "challenge_name": challenge_name,
                            "severity": "high",
                            "action_type": "lower_target_points",
                            "status": "proposed",
                            "rationale": (
                                "The current target exceeds the theoretical maximum reachable points."
                            ),
                            "suggested_change": {
                                "current_target_points": target_points,
                                "suggested_target_points": theoretical_max,
                            },
                            "notes": (
                                "This is a conservative fix suggestion. "
                                "An alternative is to increase achievable points or repetitions."
                            ),
                        }
                    )

                if any("no explicit gatekeeping task is marked" in w.lower() for w in warnings):
                    proposals.append(
                        {
                            "proposal_id": f"fix-{idx}-gatekeeper-annotation",
                            "category": "gatekeeping",
                            "challenge_name": challenge_name,
                            "severity": "medium",
                            "action_type": "annotate_gatekeeper",
                            "status": "proposed",
                            "rationale": (
                                "Gatekeeping is expected for progression, but no explicit gatekeeper is marked."
                            ),
                            "suggested_change": {
                                "candidate_gatekeepers": inferred_gatekeepers,
                            },
                            "notes": self._role_annotation_note(
                                context,
                                role_kind="gatekeeping",
                                challenge_name=challenge_name,
                            ),
                        }
                    )

                if any("reachable even without completing the effective gatekeeping task" in w.lower() for w in
                       warnings):
                    if gatekeeping_setup_complete:
                        suggested_target = self._target_to_require_gatekeeper(finding)
                        proposals.append(
                            {
                                "proposal_id": f"fix-{idx}-strengthen-gatekeeping",
                                "category": "gatekeeping",
                                "challenge_name": challenge_name,
                                "severity": "high",
                                "action_type": "strengthen_gatekeeping",
                                "status": "proposed",
                                "rationale": (
                                    "The current point structure suggests progression may be possible without the effective gatekeeper."
                                ),
                                "suggested_change": {
                                    "preferred_candidate_gatekeepers": explicit_gatekeepers or inferred_gatekeepers,
                                    "suggested_target_points": suggested_target,
                                },
                                "notes": (
                                    "Possible remedies include increasing the target, "
                                    "increasing gatekeeper weight, or reducing non-gatekeeper contribution."
                                ),
                            }
                        )
                    else:
                        notes.append(
                            f"Deferred stronger gatekeeping-point proposals for '{challenge_name}' "
                            "until explicit gatekeeping/task-role metadata is available."
                        )

                if any("no explicit maintenance tasks are annotated" in w.lower() for w in warnings):
                    proposals.append(
                        {
                            "proposal_id": f"fix-{idx}-maintenance-annotation",
                            "category": "maintenance",
                            "challenge_name": challenge_name,
                            "severity": "medium",
                            "action_type": "annotate_maintenance_tasks",
                            "status": "proposed",
                            "rationale": (
                                "At-risk or relapse-related logic is hard to validate without explicit maintenance-task annotations."
                            ),
                            "suggested_change": {
                                "annotation_required": True,
                            },
                            "notes": self._role_annotation_note(
                                context,
                                role_kind="maintenance",
                                challenge_name=challenge_name,
                            ),
                        }
                    )
        else:
            notes.append(
                "Progression/point-gatekeeping fix proposals were skipped because this campaign does not appear to use progression logic."
            )

        # ---- Theory-driven follow-up proposals only if TTM is relevant ----
        if uses_ttm and ttm_enabled and theory_grounding.get("uses_ttm") and "ttm" in theory_grounding.get("failed_checks_seen", []):
            proposals.append(
                {
                    "proposal_id": "fix-ttm-structure-review",
                    "category": "theory",
                    "challenge_name": None,
                    "severity": "high",
                    "action_type": "manual_ttm_review",
                    "status": "proposed",
                    "rationale": (
                        "The structural checker reported a TTM-related mismatch, which likely requires expert review of progression or stage logic."
                    ),
                    "suggested_change": {
                        "manual_review_required": True,
                    },
                    "notes": (
                        "A deterministic patch is not suggested here yet. "
                        "Review the intended TTM path and stage mapping before changing structure."
                    ),
                }
            )
        elif not uses_ttm or not ttm_enabled:
            notes.append("TTM-specific fix proposals were skipped because TTM is not enabled for this campaign.")

        proposals_path = self._persist_proposals(context, proposals)

        payload = {
            "enabled": True,
            "proposal_count": len(proposals),
            "proposals": proposals,
            "proposals_path": str(proposals_path) if proposals_path else None,
            "notes": notes,
        }

        context.shared["fix_proposals"] = payload

        if proposals:
            summary = f"Content/fixer agent generated {len(proposals)} repair proposal(s)."
        else:
            summary = "Content/fixer agent found no concrete repair proposals to suggest."

        return AgentResponse(
            agent_name=self.name,
            success=True,
            summary=summary,
            payload=payload,
        )

    def _target_to_require_gatekeeper(self, finding: dict[str, Any]) -> float | None:
        target = finding.get("target_points")
        theoretical_max = finding.get("theoretical_max_points")

        if target is None or theoretical_max is None:
            return None

        try:
            target = float(target)
            theoretical_max = float(theoretical_max)
        except Exception:
            return None

        if theoretical_max <= 0:
            return None

        return theoretical_max

    def _persist_proposals(self, context: AgentContext, proposals: list[dict[str, Any]]) -> Path | None:
        if context.workspace_root is None:
            return None

        patches_dir = context.workspace_root / "outputs" / "patches"
        patches_dir.mkdir(parents=True, exist_ok=True)

        path = patches_dir / f"{context.request_id}_fix_proposals.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(
                {
                    "request_id": context.request_id,
                    "workspace_id": context.workspace_id,
                    "snapshot_id": context.snapshot_id,
                    "proposal_count": len(proposals),
                    "proposals": proposals,
                },
                fh,
                indent=2,
                ensure_ascii=False,
            )
        return path