from __future__ import annotations

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.metadata import load_merged_metadata_bundle
from campaign_assistant.orchestration.models import AgentContext, AgentResponse


class CapabilityResolverAgent(BaseAgent):
    """
    Resolve campaign capabilities from:
    - inferred workbook structure
    - sidecar metadata in the workspace
    - future GameBus-native metadata (placeholder for now)

    This agent does not perform checks itself.
    It prepares a normalized capability summary for downstream agents and the UI.
    """

    name = "capability_resolver_agent"

    def run(self, context: AgentContext) -> AgentResponse:
        metadata_bundle = load_merged_metadata_bundle(
            file_path=context.file_path,
            workspace_root=context.workspace_root,
        )

        capabilities = metadata_bundle.capabilities.to_dict()

        active_modules = {
            "structural_checks": True,
            "point_gatekeeping_checks": capabilities.get("uses_progression") is not False,
            "ttm_checks": capabilities.get("uses_ttm") is True,
            "content_fix_suggestions": True,
        }

        summary = {
            "capabilities": capabilities,
            "active_modules": active_modules,
            "task_role_count": len(metadata_bundle.task_roles),
            "sources": metadata_bundle.sources,
            "notes": metadata_bundle.notes,
            "missing": metadata_bundle.missing,
        }

        context.shared["metadata_bundle"] = metadata_bundle
        context.shared["capability_summary"] = summary

        lines = []
        lines.append("Resolved campaign capability profile from inferred structure and workspace sidecars.")
        if metadata_bundle.missing:
            lines.append(f"{len(metadata_bundle.missing)} metadata gap(s) remain.")
        if metadata_bundle.task_roles:
            lines.append(f"Loaded {len(metadata_bundle.task_roles)} task-role annotation(s).")

        return AgentResponse(
            agent_name=self.name,
            success=True,
            summary=" ".join(lines),
            payload=summary,
        )