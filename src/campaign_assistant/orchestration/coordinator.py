from __future__ import annotations

import uuid

from campaign_assistant.agents.capability_resolver import CapabilityResolverAgent
from campaign_assistant.agents.content_fixer import ContentFixerAgent
from campaign_assistant.agents.privacy_guardian import PrivacyGuardianAgent
from campaign_assistant.agents.structural_change import StructuralChangeAgent
from campaign_assistant.agents.theory_grounding import TheoryGroundingAgent
from campaign_assistant.orchestration.models import AgentContext, AgentResponse, AgentTraceEvent
from campaign_assistant.session_logging import SessionLogger
from campaign_assistant.workspace import get_or_create_workspace_for_campaign
from campaign_assistant.checker.applicability import apply_capability_applicability


class CampaignAnalysisCoordinator:
    """
    Runtime orchestrator for the assistant.

    Current flow:
        UI -> Coordinator -> Workspace loader
           -> PrivacyGuardian
           -> CapabilityResolver
           -> StructuralChangeAgent
           -> TheoryGroundingAgent
           -> ContentFixerAgent

    This flow now distinguishes:
    - metadata/capability resolution
    - structural analysis
    - theory grounding
    - fix proposal generation
    """

    def __init__(self, logger: SessionLogger | None = None):
        self.logger = logger
        self.privacy_guardian = PrivacyGuardianAgent()
        self.capability_resolver = CapabilityResolverAgent()
        self.structural_agent = StructuralChangeAgent()
        self.theory_agent = TheoryGroundingAgent()
        self.content_fixer_agent = ContentFixerAgent()

    def _log_agent_step(self, request_id: str, response: AgentResponse) -> None:
        if self.logger is None:
            return

        self.logger.log(
            "agent_step",
            {
                "request_id": request_id,
                "agent_name": response.agent_name,
                "success": response.success,
                "summary": response.summary,
                "warnings": response.warnings,
                "payload_keys": list(response.payload.keys()),
            },
        )

    def _trace_event(self, step: int, response: AgentResponse) -> AgentTraceEvent:
        return AgentTraceEvent(
            step=step,
            agent_name=response.agent_name,
            status="success" if response.success else "failed",
            summary=response.summary,
            payload_keys=list(response.payload.keys()),
            warnings=response.warnings,
        )

    def analyze_campaign(
        self,
        *,
        file_path,
        selected_checks: list[str],
        export_excel: bool,
        user_prompt: str | None = None,
        workspace_id: str | None = None,
    ) -> dict:
        request_id = uuid.uuid4().hex

        workspace = get_or_create_workspace_for_campaign(
            campaign_file=file_path,
            workspace_id=workspace_id,
        )

        context = AgentContext(
            request_id=request_id,
            file_path=workspace.snapshot_path,
            selected_checks=selected_checks,
            export_excel=export_excel,
            user_prompt=user_prompt,
            workspace_id=workspace.workspace_id,
            workspace_root=workspace.root_dir,
            snapshot_id=workspace.snapshot_id,
            analysis_profile=workspace.analysis_profile,
            point_rules=workspace.point_rules,
            task_roles=workspace.task_roles,
            evidence_index=workspace.evidence_index,
        )

        if self.logger is not None:
            self.logger.log(
                "coordinator_started",
                {
                    "request_id": request_id,
                    "original_file_path": str(file_path),
                    "snapshot_path": str(workspace.snapshot_path),
                    "selected_checks": selected_checks,
                    "export_excel": export_excel,
                    "workspace_id": workspace.workspace_id,
                    "snapshot_id": workspace.snapshot_id,
                },
            )

        trace: list[AgentTraceEvent] = []

        # Step 1: privacy / access policy
        privacy_response = self.privacy_guardian.run(context)
        self._log_agent_step(request_id, privacy_response)
        trace.append(self._trace_event(step=1, response=privacy_response))
        if not privacy_response.success:
            raise RuntimeError(f"Privacy guardian failed: {privacy_response.summary}")

        # Step 2: capability resolution
        capability_response = self.capability_resolver.run(context)
        self._log_agent_step(request_id, capability_response)
        trace.append(self._trace_event(step=2, response=capability_response))
        if not capability_response.success:
            raise RuntimeError(f"Capability resolver failed: {capability_response.summary}")

        # Step 3: structural analysis
        structural_response = self.structural_agent.run(context)
        self._log_agent_step(request_id, structural_response)
        trace.append(self._trace_event(step=3, response=structural_response))
        if not structural_response.success:
            raise RuntimeError(f"Structural agent failed: {structural_response.summary}")

        # Capability-aware interpretation of the raw structural result
        if "result" in context.shared:
            context.shared["result"] = apply_capability_applicability(
                context.shared["result"],
                context.shared.get("capability_summary", {}),
            )

        # Step 4: theory grounding
        theory_response = self.theory_agent.run(context)
        self._log_agent_step(request_id, theory_response)
        trace.append(self._trace_event(step=4, response=theory_response))
        if not theory_response.success:
            raise RuntimeError(f"Theory grounding agent failed: {theory_response.summary}")

        # Step 5: fix proposals
        fixer_response = self.content_fixer_agent.run(context)
        self._log_agent_step(request_id, fixer_response)
        trace.append(self._trace_event(step=5, response=fixer_response))
        if not fixer_response.success:
            raise RuntimeError(f"Content/fixer agent failed: {fixer_response.summary}")

        result = context.shared["result"]
        result["theory_grounding"] = context.shared.get("theory_grounding", {})
        result["fix_proposals"] = context.shared.get("fix_proposals", {})

        assistant_meta = result.setdefault("assistant_meta", {})
        assistant_meta.update(
            {
                "request_id": request_id,
                "workspace_id": workspace.workspace_id,
                "workspace_root": str(workspace.root_dir),
                "snapshot_id": workspace.snapshot_id,
                "snapshot_path": str(workspace.snapshot_path),
                "selected_checks": list(selected_checks),
                "agents_run": [event.agent_name for event in trace],
                "agent_trace": [event.to_dict() for event in trace],
                "access_policy": context.shared.get("privacy", {}),
                "privacy_state": context.shared.get("privacy_state", {}),
                "loaded_profile_summary": {
                    "uses_ttm": context.analysis_profile.get("intervention_model", {}).get("uses_ttm"),
                    "uses_gatekeeping": context.analysis_profile.get("intervention_model", {}).get("uses_gatekeeping"),
                    "uses_maintenance_tasks": context.analysis_profile.get("intervention_model", {}).get("uses_maintenance_tasks"),
                    "task_role_count": len(context.task_roles),
                },
                "capability_summary": context.shared.get("capability_summary", {}),
                "metadata_bundle": context.shared.get("metadata_bundle").to_dict()
                if context.shared.get("metadata_bundle") is not None
                else {},
            }
        )

        if self.logger is not None:
            self.logger.log(
                "coordinator_completed",
                {
                    "request_id": request_id,
                    "workspace_id": workspace.workspace_id,
                    "snapshot_id": workspace.snapshot_id,
                    "agents_run": assistant_meta["agents_run"],
                    "total_issues": result.get("summary", {}).get("total_issues", 0),
                    "theory_confidence": result.get("theory_grounding", {}).get("confidence"),
                    "proposal_count": result.get("fix_proposals", {}).get("proposal_count", 0),
                },
            )

        return result