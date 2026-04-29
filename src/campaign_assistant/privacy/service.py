from __future__ import annotations

from pathlib import Path

from campaign_assistant.orchestration.models import AgentContext
from campaign_assistant.privacy.models import AgentPrivacyPolicy, PrivacyAsset, PrivacyState


class PrivacyService:
    """
    Deterministic privacy inventory and policy builder.

    Phase 2 / Step 1:
    - detect workspace assets
    - classify sensitivity coarsely
    - define per-agent access policy
    - prepare audit scaffolding

    Later steps can add:
    - field-level redaction
    - prompt/input minimization
    - policy enforcement at call sites
    """

    def build_privacy_state(self, context: AgentContext) -> PrivacyState:
        assets = self._discover_assets(context)
        policies = self._build_agent_policies(assets)
        summary = self._build_summary(assets, policies)

        state = PrivacyState(
            request_id=context.request_id,
            workspace_id=context.workspace_id,
            asset_inventory=assets,
            agent_policies=policies,
            audit_log=[
                {
                    "event": "privacy_state_initialized",
                    "request_id": context.request_id,
                    "workspace_id": context.workspace_id,
                    "asset_count": len(assets),
                    "policy_count": len(policies),
                }
            ],
            summary=summary,
        )
        return state

    def to_compatibility_access_policy(self, state: PrivacyState) -> dict[str, dict]:
        """
        Old shape expected by existing coordinator/UI/tests:
        {
            agent_name: {
                allowed_paths: [...],
                redactions: [...]
            }
        }
        """
        result: dict[str, dict] = {}
        for agent_name, policy in state.agent_policies.items():
            result[agent_name] = {
                "allowed_paths": list(policy.allowed_paths),
                "redactions": list(policy.redactions),
            }
        return result

    def _discover_assets(self, context: AgentContext) -> list[PrivacyAsset]:
        assets: list[PrivacyAsset] = []

        campaign_path = Path(context.file_path).resolve()
        assets.append(
            PrivacyAsset(
                asset_id="campaign_workbook",
                path=str(campaign_path),
                asset_type="campaign_workbook",
                sensitivity="restricted",
                contains_participant_data=True,
                notes=[
                    "Workbook may contain participant-linked campaign/task configuration.",
                    "Treat as raw workspace input.",
                ],
            )
        )

        if context.workspace_root is None:
            return assets

        workspace_root = Path(context.workspace_root).resolve()
        metadata_dir = workspace_root / "metadata"
        evidence_theory_dir = workspace_root / "evidence" / "theory"

        candidate_files = [
            ("analysis_profile_json", metadata_dir / "campaign_profile.json", "metadata_sidecar", "internal"),
            ("metadata_override_json", metadata_dir / "metadata_override.json", "metadata_sidecar", "internal"),
            ("task_roles_csv", metadata_dir / "task_roles.csv", "task_role_sidecar", "internal"),
            ("theory_registry_json", metadata_dir / "theory_registry.json", "metadata_sidecar", "internal"),
        ]

        for asset_id, path, asset_type, sensitivity in candidate_files:
            if path.exists():
                assets.append(
                    PrivacyAsset(
                        asset_id=asset_id,
                        path=str(path),
                        asset_type=asset_type,
                        sensitivity=sensitivity,
                        contains_participant_data=False,
                    )
                )

        if evidence_theory_dir.exists():
            for item in sorted(evidence_theory_dir.iterdir()):
                if not item.is_file():
                    continue
                assets.append(
                    PrivacyAsset(
                        asset_id=f"theory_{item.name}",
                        path=str(item.resolve()),
                        asset_type="theory_evidence",
                        sensitivity="internal",
                        contains_participant_data=False,
                    )
                )

        return assets

    def _build_agent_policies(self, assets: list[PrivacyAsset]) -> dict[str, AgentPrivacyPolicy]:
        asset_map = {asset.asset_id: asset for asset in assets}

        def _paths(asset_ids: list[str]) -> list[str]:
            return [asset_map[asset_id].path for asset_id in asset_ids if asset_id in asset_map]

        def _existing(asset_ids: list[str]) -> list[str]:
            return [asset_id for asset_id in asset_ids if asset_id in asset_map]

        workbook_only = _existing(["campaign_workbook"])
        metadata_assets = _existing(
            [
                "analysis_profile_json",
                "metadata_override_json",
                "task_roles_csv",
                "theory_registry_json",
            ]
        )
        theory_assets = [asset_id for asset_id in asset_map if asset_id.startswith("theory_")]

        policies = {
            "privacy_guardian": AgentPrivacyPolicy(
                agent_name="privacy_guardian",
                allowed_asset_ids=list(asset_map.keys()),
                allowed_paths=_paths(list(asset_map.keys())),
                allow_raw_workbook=True,
                allowed_context_keys=["request_id", "workspace_id", "workspace_root"],
                redactions=[],
                rationale="Privacy guardian needs full visibility to classify assets and build policies.",
            ),
            "capability_resolver_agent": AgentPrivacyPolicy(
                agent_name="capability_resolver_agent",
                allowed_asset_ids=workbook_only + metadata_assets,
                allowed_paths=_paths(workbook_only + metadata_assets),
                allow_raw_workbook=True,
                allowed_context_keys=["analysis_profile", "task_roles", "metadata_bundle"],
                redactions=[],
                rationale="Capability resolution is deterministic and needs workbook + metadata sidecars.",
            ),
            "structural_change_agent": AgentPrivacyPolicy(
                agent_name="structural_change_agent",
                allowed_asset_ids=workbook_only + metadata_assets,
                allowed_paths=_paths(workbook_only + metadata_assets),
                allow_raw_workbook=True,
                allowed_context_keys=["analysis_profile", "point_rules", "task_roles", "capability_summary"],
                redactions=[],
                rationale="Structural validation is deterministic and runs on raw workbook data.",
            ),
            "theory_grounding_agent": AgentPrivacyPolicy(
                agent_name="theory_grounding_agent",
                allowed_asset_ids=metadata_assets + theory_assets,
                allowed_paths=_paths(metadata_assets + theory_assets),
                allow_raw_workbook=False,
                allowed_context_keys=["result", "capability_summary", "metadata_bundle"],
                redactions=[
                    "no_raw_campaign_workbook",
                    "prefer_summaries_over_raw_rows",
                ],
                rationale="Theory grounding should use metadata, findings, and theory sources, not raw workbook rows.",
            ),
            "content_fixer_agent": AgentPrivacyPolicy(
                agent_name="content_fixer_agent",
                allowed_asset_ids=metadata_assets,
                allowed_paths=_paths(metadata_assets),
                allow_raw_workbook=False,
                allowed_context_keys=["result", "theory_grounding", "capability_summary", "metadata_bundle"],
                redactions=[
                    "no_raw_campaign_workbook",
                    "no_participant_identifiers",
                    "use_sanitized_findings_only",
                ],
                rationale="Fix generation should operate on findings and metadata, not raw workbook contents.",
            ),
        }

        return policies

    def _build_summary(
        self,
        assets: list[PrivacyAsset],
        policies: dict[str, AgentPrivacyPolicy],
    ) -> dict[str, object]:
        restricted_assets = [item.asset_id for item in assets if item.sensitivity == "restricted"]
        raw_workbook_agents = [
            name for name, policy in policies.items()
            if policy.allow_raw_workbook
        ]
        sanitized_only_agents = [
            name for name, policy in policies.items()
            if not policy.allow_raw_workbook
        ]

        return {
            "asset_count": len(assets),
            "restricted_asset_ids": restricted_assets,
            "raw_workbook_allowed_agents": raw_workbook_agents,
            "sanitized_only_agents": sanitized_only_agents,
            "policy_mode": "coarse_grained_phase_2_step_1",
        }