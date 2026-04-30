from __future__ import annotations

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.orchestration.models import AgentContext, AgentResponse
from campaign_assistant.privacy import PrivacyService
from campaign_assistant.reasoning import WorkspaceReadinessService


class WorkspaceReadinessAgent(BaseAgent):
    """
    Internal readiness assessment agent.

    This is not a user-facing check. It decides whether stronger
    progression/gatekeeping semantics checks are ready to run.
    """

    name = "workspace_readiness_agent"

    def __init__(self) -> None:
        self.privacy_service = PrivacyService()
        self.readiness_service = WorkspaceReadinessService()

    def run(self, context: AgentContext) -> AgentResponse:
        run_info = (
            self.privacy_service.start_agent_run(self.name, context)
            if "privacy_state" in context.shared
            else {}
        )
        agent_run_id = run_info.get("agent_run_id")

        capability_summary = dict(context.shared.get("capability_summary", {}) or {})

        readiness = self.readiness_service.analyze(
            campaign_file=str(context.file_path),
            capability_summary=capability_summary,
            point_rules=context.point_rules,
            task_roles=context.task_roles,
        )

        context.shared["workspace_readiness"] = readiness

        if capability_summary:
            merged_summary = dict(capability_summary)
            merged_summary["workspace_readiness"] = readiness
            context.shared["capability_summary"] = merged_summary

        payload = {
            "workspace_readiness": readiness,
        }

        self.privacy_service.record_agent_outcome(
            agent_name=self.name,
            context=context,
            agent_run_id=agent_run_id,
            success=True,
            payload=payload,
            warnings=[],
            notes=list(readiness.get("reasons", []) or []),
        )

        if readiness.get("gatekeeping_semantics_ready"):
            summary = "Workspace readiness assessment completed. Stronger gatekeeping semantics checks are enabled."
        elif readiness.get("progression_applicable"):
            summary = "Workspace readiness assessment completed. Stronger gatekeeping semantics checks remain disabled until task-role annotations are added."
        else:
            summary = "Workspace readiness assessment completed. Progression-specific checks are not applicable for this campaign."

        return AgentResponse(
            agent_name=self.name,
            success=True,
            summary=summary,
            payload=payload,
        )