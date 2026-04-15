from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.orchestration.models import AgentContext, AgentResponse


class ContentFixerAgent(BaseAgent):
    """
    First version of the content/fixer agent.

    Current scope:
    - generate deterministic repair proposals from existing findings
    - suggest point/gatekeeping fixes
    - suggest annotation fixes
    - suggest manual follow-up where a precise patch is not yet safe

    Not yet implemented:
    - LLM rewriting
    - patched Excel generation
    - direct GameBus write-back
    - approval workflow

    This agent operates in proposal mode only.
    """

    name = "content_fixer_agent"

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
            # default
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

        structural_result = context.shared.get("result", {})
        point_gatekeeping = structural_result.get("point_gatekeeping", {})
        theory_grounding = context.shared.get("theory_grounding", {})

        proposals: list[dict[str, Any]] = []

        # ---- Point/gatekeeping-driven proposals ----
        for idx, finding in enumerate(point_gatekeeping.get("findings", []), start=1):
            challenge_name = finding.get("challenge_name") or "Unknown challenge"
            target_points = finding.get("target_points")
            theoretical_max = finding.get("theoretical_max_points")
            explicit_gatekeepers = finding.get("explicit_gatekeepers") or []
            inferred_gatekeepers = finding.get("inferred_gatekeepers") or []

            warnings = finding.get("warnings") or []

            # Proposal 1: missing target
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

            # Proposal 2: unreachable target
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

            # Proposal 3: explicit gatekeeping annotation
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

            # Proposal 4: progression reachable without gatekeeper
            if any("reachable even without completing the effective gatekeeping task" in w.lower() for w in warnings):
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

            # Proposal 5: maintenance annotations for at-risk levels
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

        # ---- Theory-driven manual follow-up proposals ----
        if theory_grounding.get("uses_ttm") and "ttm" in theory_grounding.get("failed_checks_seen", []):
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

        # Persist proposals for auditability if we have a workspace.
        proposals_path = self._persist_proposals(context, proposals)

        payload = {
            "enabled": True,
            "proposal_count": len(proposals),
            "proposals": proposals,
            "proposals_path": str(proposals_path) if proposals_path else None,
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
        """
        Conservative target suggestion:
        if the target is reachable without the gatekeeper, recommend moving the target
        upward toward the theoretical maximum.
        """
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

        # Conservative: if we know nothing else, recommend the theoretical max.
        # This is easy to explain and safe as a placeholder suggestion.
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