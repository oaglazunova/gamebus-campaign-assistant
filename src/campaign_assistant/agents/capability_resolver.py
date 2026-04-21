from __future__ import annotations

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.metadata import load_merged_metadata_bundle
from campaign_assistant.orchestration.models import AgentContext, AgentResponse


class CapabilityResolverAgent(BaseAgent):
    name = "capability_resolver_agent"

    def run(self, context: AgentContext) -> AgentResponse:
        metadata_bundle = load_merged_metadata_bundle(
            file_path=context.file_path,
            workspace_root=context.workspace_root,
        )

        capabilities = metadata_bundle.capabilities.to_dict()
        theory_tags = sorted({tag for item in metadata_bundle.theory_sources for tag in item.tags})

        ttm_enabled = capabilities.get("uses_ttm") is True or any(
            "ttm" in {str(tag).strip().lower() for tag in getattr(source, "tags", [])}
            for source in metadata_bundle.theory_sources
        )

        point_gatekeeping_enabled = capabilities.get("uses_progression") is not False

        validator_applicability = {
            "universal_structural": True,
            "targetpointsreachable": point_gatekeeping_enabled,
            "ttm_structure": ttm_enabled,
        }

        theory_applicability = {
            "ttm_grounding": ttm_enabled,
        }

        active_modules = {
            # canonical new structure
            "validator_applicability": validator_applicability,
            "theory_applicability": theory_applicability,

            # backward-compatible aliases for older UI/tests
            "structural_checks": True,
            "point_gatekeeping_checks": point_gatekeeping_enabled,
            "ttm_checks": ttm_enabled,
            "content_fix_suggestions": True,
        }

        active_validators = [
            name
            for name, enabled in validator_applicability.items()
            if enabled
        ]

        summary = {
            "capabilities": capabilities,
            "campaign_family": metadata_bundle.campaign_family.to_dict(),
            "theory_tags": theory_tags,
            "theory_source_count": len(metadata_bundle.theory_sources),
            "validator_applicability": validator_applicability,
            "theory_applicability": theory_applicability,
            "active_modules": active_modules,
            "active_validators": active_validators,
            "task_role_count": len(metadata_bundle.task_roles),
            "sources": metadata_bundle.sources,
            "notes": metadata_bundle.notes,
            "missing": metadata_bundle.missing,
        }

        context.shared["metadata_bundle"] = metadata_bundle
        context.shared["capability_summary"] = summary

        lines = []
        lines.append("Resolved campaign capability profile from inferred structure and workspace sidecars.")
        if metadata_bundle.campaign_family.slug:
            lines.append(f"Campaign family: {metadata_bundle.campaign_family.display_name or metadata_bundle.campaign_family.slug}.")
        if metadata_bundle.missing:
            lines.append(f"{len(metadata_bundle.missing)} metadata gap(s) remain.")
        if metadata_bundle.task_roles:
            lines.append(f"Loaded {len(metadata_bundle.task_roles)} task-role annotation(s).")
        if metadata_bundle.theory_sources:
            lines.append(f"Loaded {len(metadata_bundle.theory_sources)} theory/evidence source(s).")

        return AgentResponse(
            agent_name=self.name,
            success=True,
            summary=" ".join(lines),
            payload=summary,
        )