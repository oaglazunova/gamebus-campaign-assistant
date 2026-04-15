from __future__ import annotations

import uuid
from pathlib import Path

from campaign_assistant.agents import (
    ContentFixerAgent,
    PrivacyGuardianAgent,
    StructuralChangeAgent,
    TheoryGroundingAgent,
)
from campaign_assistant.orchestration.models import AgentContext, AgentResponse, AgentTraceEvent
from campaign_assistant.session_logging import SessionLogger
from campaign_assistant.workspace import get_or_create_workspace_for_campaign


class CampaignAnalysisCoordinator:
    """
    Runtime orchestrator for the assistant.

    Current flow:
        UI -> Coordinator -> Workspace loader
           -> PrivacyGuardian
           -> StructuralChangeAgent
           -> TheoryGroundingAgent
           -> ContentFixerAgent

    This now gives:
    - actual runtime multi-agent orchestration
    - theory-aware checking
    - point/gatekeeping reasoning
    - structured fix proposals

    Later extensions:
        -> patched Excel generation
        -> approval workflow
        -> direct GameBus write-back
    """

    def __init__(self, logger: SessionLogger | None = None):
        self.logger = logger
        self.privacy_guardian = PrivacyGuardianAgent()
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
        file_path: str | Path,
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

        # Step 2: structural analysis
        structural_response = self.structural_agent.run(context)
        self._log_agent_step(request_id, structural_response)
        trace.append(self._trace_event(step=2, response=structural_response))
        if not structural_response.success:
            raise RuntimeError(f"Structural agent failed: {structural_response.summary}")

        # Step 3: theory grounding
        theory_response = self.theory_agent.run(context)
        self._log_agent_step(request_id, theory_response)
        trace.append(self._trace_event(step=3, response=theory_response))
        if not theory_response.success:
            raise RuntimeError(f"Theory grounding agent failed: {theory_response.summary}")

        # Step 4: fix proposals
        fixer_response = self.content_fixer_agent.run(context)
        self._log_agent_step(request_id, fixer_response)
        trace.append(self._trace_event(step=4, response=fixer_response))
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
                "agents_run": [event.agent_name for event in trace],
                "agent_trace": [event.to_dict() for event in trace],
                "access_policy": context.shared.get("privacy", {}),
                "loaded_profile_summary": {
                    "uses_ttm": context.analysis_profile.get("intervention_model", {}).get("uses_ttm"),
                    "uses_gatekeeping": context.analysis_profile.get("intervention_model", {}).get("uses_gatekeeping"),
                    "uses_maintenance_tasks": context.analysis_profile.get("intervention_model", {}).get("uses_maintenance_tasks"),
                    "task_role_count": len(context.task_roles),
                },
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