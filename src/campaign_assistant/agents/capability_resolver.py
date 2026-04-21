from __future__ import annotations

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.metadata import load_merged_metadata_bundle
from campaign_assistant.orchestration.models import AgentContext, AgentResponse


def _theory_tags(metadata_bundle) -> list[str]:
    return sorted(
        {
            str(tag).strip().lower()
            for item in getattr(metadata_bundle, "theory_sources", []) or []
            for tag in getattr(item, "tags", []) or []
            if str(tag).strip()
        }
    )


def _resolve_ttm_enabled(capabilities: dict, theory_tags: list[str]) -> bool:
    if capabilities.get("uses_ttm") is True:
        return True
    return "ttm" in theory_tags or "transtheoretical_model" in theory_tags


def _build_validator_applicability(capabilities: dict, ttm_enabled: bool) -> dict[str, bool]:
    point_gatekeeping_enabled = capabilities.get("uses_progression") is not False

    return {
        "universal_structural": True,
        "targetpointsreachable": point_gatekeeping_enabled,
        "ttm": ttm_enabled,
    }


def _build_theory_applicability(ttm_enabled: bool) -> dict[str, bool]:
    return {
        "ttm_grounding": ttm_enabled,
    }


def _build_active_modules_compatibility(
    *,
    validator_applicability: dict[str, bool],
    theory_applicability: dict[str, bool],
) -> dict[str, object]:
    """
    Backward-compatible shape for older tests/UI.

    New code should prefer validator_applicability and theory_applicability directly.
    """
    return {
        # canonical nested structures
        "validator_applicability": validator_applicability,
        "theory_applicability": theory_applicability,

        # legacy compatibility aliases
        "structural_checks": validator_applicability.get("universal_structural", False),
        "point_gatekeeping_checks": validator_applicability.get("targetpointsreachable", False),
        "ttm_checks": theory_applicability.get("ttm_grounding", False),
        "content_fix_suggestions": True,
    }


class CapabilityResolverAgent(BaseAgent):
    name = "capability_resolver_agent"

    def run(self, context: AgentContext) -> AgentResponse:
        metadata_bundle = load_merged_metadata_bundle(
            file_path=context.file_path,
            workspace_root=context.workspace_root,
        )

        capabilities = metadata_bundle.capabilities.to_dict()
        theory_tags = _theory_tags(metadata_bundle)
        ttm_enabled = _resolve_ttm_enabled(capabilities, theory_tags)

        validator_applicability = _build_validator_applicability(capabilities, ttm_enabled)
        theory_applicability = _build_theory_applicability(ttm_enabled)
        active_modules = _build_active_modules_compatibility(
            validator_applicability=validator_applicability,
            theory_applicability=theory_applicability,
        )

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
            lines.append(
                f"Campaign family: {metadata_bundle.campaign_family.display_name or metadata_bundle.campaign_family.slug}."
            )
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