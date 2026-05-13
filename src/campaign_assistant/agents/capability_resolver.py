from __future__ import annotations

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.checker.preflight import build_capability_summary_for_file
from campaign_assistant.metadata import load_merged_metadata_bundle
from campaign_assistant.orchestration.models import AgentContext, AgentResponse
from campaign_assistant.privacy import PrivacyService


class CapabilityResolverAgent(BaseAgent):
    name = "capability_resolver_agent"

    def __init__(self) -> None:
        self.privacy_service = PrivacyService()

    def run(self, context: AgentContext) -> AgentResponse:
        run_info = (
            self.privacy_service.start_agent_run(self.name, context)
            if "privacy_state" in context.shared
            else {}
        )
        agent_run_id = run_info.get("agent_run_id")

        metadata_bundle = load_merged_metadata_bundle(
            file_path=context.file_path,
            workspace_root=context.workspace_root,
        )
        summary = build_capability_summary_for_file(
            file_path=context.file_path,
            workspace_root=context.workspace_root,
        )

        context.shared["metadata_bundle"] = metadata_bundle
        context.shared["capability_summary"] = summary

        lines = []
        lines.append("Resolved campaign capability profile from inferred structure and workspace sidecars.")
        campaign_family = summary.get("campaign_family", {}) or {}
        if campaign_family.get("slug"):
            lines.append(
                f"Campaign family: {campaign_family.get('display_name') or campaign_family.get('slug')}."
            )
        missing = list(summary.get("missing", []) or [])
        if missing:
            lines.append(f"{len(missing)} metadata gap(s) remain.")
        task_role_count = int(summary.get("task_role_count", 0) or 0)
        if task_role_count:
            lines.append(f"Loaded {task_role_count} task-role annotation(s).")
        theory_source_count = int(summary.get("theory_source_count", 0) or 0)
        if theory_source_count:
            lines.append(f"Loaded {theory_source_count} theory/evidence source(s).")

        self.privacy_service.record_agent_outcome(
            agent_name=self.name,
            context=context,
            agent_run_id=agent_run_id,
            success=True,
            payload=summary,
            warnings=[],
            notes=list(summary.get("notes", []) or []) + list(summary.get("missing", []) or []),
        )

        return AgentResponse(
            agent_name=self.name,
            success=True,
            summary=" ".join(lines),
            payload=summary,
        )