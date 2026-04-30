from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from campaign_assistant.orchestration.models import AgentContext
from campaign_assistant.privacy.models import AgentPrivacyPolicy, PrivacyAsset, PrivacyState


class PrivacyService:
    """
    Phase 2 / Step 11 privacy service.

    This version adds policy override diagnostics.

    Workspace overrides may narrow policy, but they must not widen semantic agents
    into raw-workbook access.

    New in this step:
    - override validation warnings
    - audit events for override warnings
    - compact reporting of ignored/blocked override attempts
    """

    SEMANTIC_AGENTS_REQUIRING_VIEWS = {
        "theory_grounding_agent",
        "content_fixer_agent",
    }

    def build_privacy_state(self, context: AgentContext) -> PrivacyState:
        assets = self._discover_assets(context)
        policies = self._build_agent_policies(assets)

        asset_map = {asset.asset_id: asset for asset in assets}
        policies = {
            name: self._enforce_policy_invariants(policy, asset_map)
            for name, policy in policies.items()
        }

        overrides = self._load_workspace_policy_overrides(context)
        override_warnings = self._validate_workspace_policy_overrides(overrides, policies, assets)
        policies = self._apply_policy_overrides(policies, assets, overrides)
        summary = self._build_summary(assets, policies, overrides, override_warnings)

        init_event_id = self._new_id("pev")
        audit_log = [
            {
                "event_id": init_event_id,
                "parent_event_id": None,
                "event": "privacy_state_initialized",
                "request_id": context.request_id,
                "workspace_id": context.workspace_id,
                "asset_count": len(assets),
                "policy_count": len(policies),
                "has_workspace_overrides": bool(overrides.get("agent_policies")),
                "override_warning_count": len(override_warnings),
            }
        ]
        audit_log.extend(
            self._append_override_warning_events(
                request_id=context.request_id,
                workspace_id=context.workspace_id,
                warnings=override_warnings,
            )
        )

        return PrivacyState(
            request_id=context.request_id,
            workspace_id=context.workspace_id,
            asset_inventory=assets,
            agent_policies=policies,
            audit_log=audit_log,
            summary=summary,
        )


    def to_compatibility_access_policy(self, state: PrivacyState) -> dict[str, dict]:
        return {
            agent_name: {
                "allowed_paths": list(policy.allowed_paths),
                "redactions": list(policy.redactions),
            }
            for agent_name, policy in state.agent_policies.items()
        }

    def ensure_privacy_state(self, context: AgentContext) -> dict[str, Any]:
        existing = context.shared.get("privacy_state")
        if isinstance(existing, dict):
            if "privacy_report" not in context.shared:
                context.shared["privacy_report"] = self.build_privacy_report(existing)
            return existing

        state_obj = self.build_privacy_state(context)
        state = state_obj.to_dict()
        context.shared["privacy_state"] = state
        context.shared["privacy"] = self.to_compatibility_access_policy(state_obj)
        context.shared["privacy_report"] = self.build_privacy_report(state)
        return state

    def build_privacy_report(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Build a compact, UI/debug-friendly privacy summary from the richer privacy_state.
        """
        summary = dict(state.get("summary", {}) or {})
        policies = state.get("agent_policies", {}) or {}

        return {
            "policy_mode": summary.get("policy_mode"),
            "has_workspace_overrides": bool(summary.get("has_workspace_overrides", False)),
            "overridden_agents": list(summary.get("overridden_agents", []) or []),
            "override_warning_count": int(summary.get("override_warning_count", 0) or 0),
            "override_warnings": list(summary.get("override_warnings", []) or []),
            "raw_workbook_allowed_agents": list(summary.get("raw_workbook_allowed_agents", []) or []),
            "sanitized_only_agents": list(summary.get("sanitized_only_agents", []) or []),
            "semantic_agents_requiring_views": sorted(self.SEMANTIC_AGENTS_REQUIRING_VIEWS),
            "policy_sources_by_agent": {
                agent_name: str((policy or {}).get("policy_source", "baseline"))
                for agent_name, policy in policies.items()
            },
            "allow_raw_workbook_by_agent": {
                agent_name: bool((policy or {}).get("allow_raw_workbook", False))
                for agent_name, policy in policies.items()
            },
        }


    def require_privacy_state(self, context: AgentContext, agent_name: str) -> dict[str, Any]:
        state = context.shared.get("privacy_state")
        if not isinstance(state, dict):
            raise RuntimeError(
                f"{agent_name} requires privacy initialization. "
                "Run PrivacyGuardianAgent first."
            )
        return state

    def get_required_agent_view(self, agent_name: str, context: AgentContext) -> dict[str, Any]:
        self.require_privacy_state(context, agent_name)
        existing = (context.shared.get("agent_views", {}) or {}).get(agent_name)
        if isinstance(existing, dict):
            return existing
        return self.build_agent_view(agent_name, context)

    def start_agent_run(self, agent_name: str, context: AgentContext) -> dict[str, Any]:
        state = self.ensure_privacy_state(context)
        policy = self._agent_policy_from_state(state, agent_name)

        agent_run_id = self._new_id("agr")
        parent_event_id = self._last_event_id(state)

        run_event_id = self._new_id("pev")
        self._append_audit_event(
            state,
            {
                "event_id": run_event_id,
                "parent_event_id": parent_event_id,
                "event": "agent_run_started",
                "request_id": context.request_id,
                "workspace_id": context.workspace_id,
                "agent_name": agent_name,
                "agent_run_id": agent_run_id,
                "allowed_asset_ids": list(policy.get("allowed_asset_ids", [])),
                "allow_raw_workbook": bool(policy.get("allow_raw_workbook", False)),
                "allowed_context_keys": list(policy.get("allowed_context_keys", [])),
                "redactions": list(policy.get("redactions", [])),
                "policy_source": policy.get("policy_source", "baseline"),
            },
        )

        used_asset_ids = self._resolve_run_asset_ids(agent_name, policy, state)
        asset_access_event_ids = self._record_view_asset_lineage(
            state=state,
            request_id=context.request_id,
            workspace_id=context.workspace_id,
            agent_name=agent_name,
            agent_run_id=agent_run_id,
            agent_view_id=None,
            parent_event_id=run_event_id,
            asset_ids=used_asset_ids,
        )

        return {
            "agent_run_id": agent_run_id,
            "used_asset_ids": used_asset_ids,
            "asset_access_event_ids": asset_access_event_ids,
        }

    def build_agent_view(self, agent_name: str, context: AgentContext) -> dict[str, Any]:
        state = self.ensure_privacy_state(context)
        policy = self._agent_policy_from_state(state, agent_name)

        allowed_context_keys = list(policy.get("allowed_context_keys", []))
        agent_run_id = self._new_id("agr")
        agent_view_id = self._new_id("avw")
        parent_event_id = self._last_event_id(state)

        view: dict[str, Any] = {
            "request_id": context.request_id,
            "workspace_id": context.workspace_id,
            "agent_name": agent_name,
            "agent_run_id": agent_run_id,
            "agent_view_id": agent_view_id,
            "policy": policy,
        }

        if "analysis_profile" in allowed_context_keys:
            view["analysis_profile"] = dict(context.analysis_profile or {})

        if "point_rules" in allowed_context_keys:
            view["point_rules"] = dict(context.point_rules or {})

        if "task_roles" in allowed_context_keys:
            view["task_roles"] = list(context.task_roles or [])

        if "capability_summary" in allowed_context_keys:
            view["capability_summary"] = dict(context.shared.get("capability_summary", {}) or {})

        metadata_bundle = context.shared.get("metadata_bundle")
        if "metadata_bundle" in allowed_context_keys:
            if agent_name in {"theory_grounding_agent", "content_fixer_agent"}:
                view["metadata_summary"] = self._summarize_metadata_bundle(metadata_bundle)
            else:
                view["metadata_bundle"] = metadata_bundle
                view["metadata_summary"] = self._summarize_metadata_bundle(metadata_bundle)

        if "result" in allowed_context_keys:
            view["result"] = self._sanitize_result_for_agent(
                agent_name=agent_name,
                result=context.shared.get("result", {}) or {},
            )

        if "theory_grounding" in allowed_context_keys:
            view["theory_grounding"] = dict(context.shared.get("theory_grounding", {}) or {})

        agent_views = context.shared.setdefault("agent_views", {})
        agent_views[agent_name] = view

        view_event_id = self._new_id("pev")
        self._append_audit_event(
            state,
            {
                "event_id": view_event_id,
                "parent_event_id": parent_event_id,
                "event": "agent_view_built",
                "request_id": context.request_id,
                "workspace_id": context.workspace_id,
                "agent_name": agent_name,
                "agent_run_id": agent_run_id,
                "agent_view_id": agent_view_id,
                "allowed_asset_ids": list(policy.get("allowed_asset_ids", [])),
                "allow_raw_workbook": bool(policy.get("allow_raw_workbook", False)),
                "allowed_context_keys": allowed_context_keys,
                "redactions": list(policy.get("redactions", [])),
                "policy_source": policy.get("policy_source", "baseline"),
                "metadata_mode": "summary_only"
                if agent_name in {"theory_grounding_agent", "content_fixer_agent"}
                else "raw_plus_summary",
            },
        )

        used_asset_ids = self._resolve_view_asset_ids(agent_name, policy, state)
        asset_access_event_ids = self._record_view_asset_lineage(
            state=state,
            request_id=context.request_id,
            workspace_id=context.workspace_id,
            agent_name=agent_name,
            agent_run_id=agent_run_id,
            agent_view_id=agent_view_id,
            parent_event_id=view_event_id,
            asset_ids=used_asset_ids,
        )

        view["used_asset_ids"] = used_asset_ids
        view["asset_access_event_ids"] = asset_access_event_ids

        return view

    def record_agent_outcome(
        self,
        *,
        agent_name: str,
        context: AgentContext,
        agent_run_id: str | None,
        success: bool,
        payload: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
        notes: list[str] | None = None,
    ) -> None:
        if not agent_run_id:
            return

        state = self.ensure_privacy_state(context)
        parent_event_id = self._last_event_id_for_agent_run(state, agent_run_id) or self._last_event_id(state)

        event = {
            "event_id": self._new_id("pev"),
            "parent_event_id": parent_event_id,
            "event": "agent_completed",
            "request_id": context.request_id,
            "workspace_id": context.workspace_id,
            "agent_name": agent_name,
            "agent_run_id": agent_run_id,
            "success": bool(success),
            "payload_keys": sorted(list((payload or {}).keys())),
            "warning_count": len(warnings or []),
            "note_count": len(notes or []),
        }
        self._append_audit_event(state, event)

    def _load_workspace_policy_overrides(self, context: AgentContext) -> dict[str, Any]:
        if context.workspace_root is None:
            return {}

        policy_path = Path(context.workspace_root) / "metadata" / "privacy_policy.json"
        if not policy_path.exists():
            return {}

        try:
            with policy_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            return {}

        return data if isinstance(data, dict) else {}


    def _validate_workspace_policy_overrides(
        self,
        overrides: dict[str, Any],
        baseline_policies: dict[str, AgentPrivacyPolicy],
        assets: list[PrivacyAsset],
    ) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []

        override_policies = overrides.get("agent_policies", {}) or {}
        if not isinstance(override_policies, dict):
            return warnings

        known_agents = set(baseline_policies.keys())
        known_asset_ids = {asset.asset_id for asset in assets}

        for agent_name, raw_override in override_policies.items():
            if agent_name not in known_agents:
                warnings.append(
                    {
                        "code": "unknown_agent_override",
                        "agent_name": agent_name,
                        "message": f"Privacy override for unknown agent '{agent_name}' was ignored.",
                    }
                )
                continue

            if not isinstance(raw_override, dict):
                warnings.append(
                    {
                        "code": "invalid_agent_override_shape",
                        "agent_name": agent_name,
                        "message": f"Privacy override for agent '{agent_name}' is not a JSON object and was ignored.",
                    }
                )
                continue

            requested_asset_ids = raw_override.get("allowed_asset_ids")
            if isinstance(requested_asset_ids, list):
                unknown_asset_ids = [
                    str(asset_id)
                    for asset_id in requested_asset_ids
                    if str(asset_id) not in known_asset_ids
                ]
                if unknown_asset_ids:
                    warnings.append(
                        {
                            "code": "unknown_asset_ids_ignored",
                            "agent_name": agent_name,
                            "asset_ids": unknown_asset_ids,
                            "message": (
                                f"Privacy override for agent '{agent_name}' referenced unknown asset IDs: "
                                f"{', '.join(unknown_asset_ids)}. They were ignored."
                            ),
                        }
                    )

            if "allowed_paths" in raw_override:
                warnings.append(
                    {
                        "code": "allowed_paths_override_ignored",
                        "agent_name": agent_name,
                        "message": (
                            f"Privacy override for agent '{agent_name}' included allowed_paths, "
                            "but allowed_paths are derived from validated asset IDs and the override value was ignored."
                        ),
                    }
                )

            if agent_name in self.SEMANTIC_AGENTS_REQUIRING_VIEWS:
                if raw_override.get("allow_raw_workbook") is True:
                    warnings.append(
                        {
                            "code": "semantic_raw_workbook_escalation_blocked",
                            "agent_name": agent_name,
                            "message": (
                                f"Privacy override tried to enable raw workbook access for semantic agent '{agent_name}', "
                                "but this escalation was blocked."
                            ),
                        }
                    )

                if isinstance(requested_asset_ids, list) and "campaign_workbook" in {
                    str(x) for x in requested_asset_ids
                }:
                    warnings.append(
                        {
                            "code": "semantic_workbook_asset_removed",
                            "agent_name": agent_name,
                            "message": (
                                f"Privacy override tried to add 'campaign_workbook' to semantic agent '{agent_name}', "
                                "but this asset was removed by policy invariants."
                            ),
                        }
                    )

        return warnings



    def _append_override_warning_events(
        self,
        *,
        request_id: str,
        workspace_id: str | None,
        warnings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for item in warnings:
            events.append(
                {
                    "event_id": self._new_id("pev"),
                    "parent_event_id": None,
                    "event": "policy_override_warning",
                    "request_id": request_id,
                    "workspace_id": workspace_id,
                    "warning_code": item.get("code"),
                    "agent_name": item.get("agent_name"),
                    "message": item.get("message"),
                    "asset_ids": list(item.get("asset_ids", []) or []),
                }
            )
        return events



    def _apply_policy_overrides(
            self,
            policies: dict[str, AgentPrivacyPolicy],
            assets: list[PrivacyAsset],
            overrides: dict[str, Any],
    ) -> dict[str, AgentPrivacyPolicy]:
        override_policies = overrides.get("agent_policies", {}) or {}
        if not isinstance(override_policies, dict):
            return policies

        asset_map = {asset.asset_id: asset for asset in assets}

        def valid_asset_ids(asset_ids: list[str]) -> list[str]:
            return [asset_id for asset_id in asset_ids if asset_id in asset_map]

        for agent_name, raw_override in override_policies.items():
            if agent_name not in policies:
                continue
            if not isinstance(raw_override, dict):
                continue

            base = policies[agent_name]

            allowed_asset_ids = list(base.allowed_asset_ids)
            if "allowed_asset_ids" in raw_override and isinstance(raw_override["allowed_asset_ids"], list):
                allowed_asset_ids = valid_asset_ids([str(x) for x in raw_override["allowed_asset_ids"]])

            allow_raw_workbook = base.allow_raw_workbook
            if "allow_raw_workbook" in raw_override:
                allow_raw_workbook = bool(raw_override["allow_raw_workbook"])

            allowed_context_keys = list(base.allowed_context_keys)
            if "allowed_context_keys" in raw_override and isinstance(raw_override["allowed_context_keys"], list):
                allowed_context_keys = [str(x) for x in raw_override["allowed_context_keys"]]

            redactions = list(base.redactions)
            if "redactions" in raw_override and isinstance(raw_override["redactions"], list):
                redactions = [str(x) for x in raw_override["redactions"]]

            rationale = base.rationale
            if "rationale" in raw_override:
                rationale = str(raw_override["rationale"])

            candidate = AgentPrivacyPolicy(
                agent_name=agent_name,
                allowed_asset_ids=allowed_asset_ids,
                allowed_paths=[],  # always derived during invariant enforcement
                allow_raw_workbook=allow_raw_workbook,
                allowed_context_keys=allowed_context_keys,
                redactions=redactions,
                rationale=rationale,
                policy_source="workspace_override",
            )

            policies[agent_name] = self._enforce_policy_invariants(candidate, asset_map)

        return policies


    def _enforce_policy_invariants(
        self,
        policy: AgentPrivacyPolicy,
        asset_map: dict[str, PrivacyAsset],
    ) -> AgentPrivacyPolicy:
        """
        Final hardening pass after baseline policy + workspace override merge.

        Semantic agents can be narrowed, but cannot be widened into raw workbook access.
        """
        allowed_asset_ids = [asset_id for asset_id in policy.allowed_asset_ids if asset_id in asset_map]

        # Only allow raw workbook mode if the workbook asset is actually present in scope.
        allow_raw_workbook = policy.allow_raw_workbook and "campaign_workbook" in allowed_asset_ids

        if policy.agent_name in self.SEMANTIC_AGENTS_REQUIRING_VIEWS:
            allowed_asset_ids = [asset_id for asset_id in allowed_asset_ids if asset_id != "campaign_workbook"]
            allow_raw_workbook = False

            semantic_redactions = [
                "no_raw_campaign_workbook",
                "metadata_summary_only",
            ]
            redactions = list(dict.fromkeys(list(policy.redactions) + semantic_redactions))
        else:
            redactions = list(policy.redactions)

        allowed_paths = [asset_map[asset_id].path for asset_id in allowed_asset_ids]

        return AgentPrivacyPolicy(
            agent_name=policy.agent_name,
            allowed_asset_ids=allowed_asset_ids,
            allowed_paths=allowed_paths,
            allow_raw_workbook=allow_raw_workbook,
            allowed_context_keys=list(policy.allowed_context_keys),
            redactions=redactions,
            rationale=policy.rationale,
            policy_source=policy.policy_source,
        )



    def _record_view_asset_lineage(
        self,
        *,
        state: dict[str, Any],
        request_id: str,
        workspace_id: str | None,
        agent_name: str,
        agent_run_id: str,
        agent_view_id: str | None,
        parent_event_id: str,
        asset_ids: list[str],
    ) -> list[str]:
        event_ids: list[str] = []

        for asset_id in asset_ids:
            asset_info = self._asset_info_from_state(state, asset_id)
            access_event_id = self._new_id("pev")
            asset_access_id = self._new_id("aac")

            self._append_audit_event(
                state,
                {
                    "event_id": access_event_id,
                    "parent_event_id": parent_event_id,
                    "event": "asset_access_recorded",
                    "request_id": request_id,
                    "workspace_id": workspace_id,
                    "agent_name": agent_name,
                    "agent_run_id": agent_run_id,
                    "agent_view_id": agent_view_id,
                    "asset_access_id": asset_access_id,
                    "asset_id": asset_id,
                    "asset_path": asset_info.get("path"),
                    "asset_type": asset_info.get("asset_type"),
                    "asset_sensitivity": asset_info.get("sensitivity"),
                    "contains_participant_data": asset_info.get("contains_participant_data", False),
                    "access_mode": self._asset_access_mode(agent_name, asset_id, asset_info),
                },
            )
            event_ids.append(access_event_id)

        return event_ids

    def _resolve_view_asset_ids(
        self,
        agent_name: str,
        policy: dict[str, Any],
        state: dict[str, Any],
    ) -> list[str]:
        allowed_asset_ids = list(policy.get("allowed_asset_ids", []))
        known_asset_ids = {item.get("asset_id") for item in state.get("asset_inventory", []) or []}

        result = [asset_id for asset_id in allowed_asset_ids if asset_id in known_asset_ids]

        if agent_name == "content_fixer_agent":
            result = [asset_id for asset_id in result if not str(asset_id).startswith("theory_")]

        return result

    def _resolve_run_asset_ids(
        self,
        agent_name: str,
        policy: dict[str, Any],
        state: dict[str, Any],
    ) -> list[str]:
        allowed_asset_ids = list(policy.get("allowed_asset_ids", []))
        known_asset_ids = {item.get("asset_id") for item in state.get("asset_inventory", []) or []}
        return [asset_id for asset_id in allowed_asset_ids if asset_id in known_asset_ids]

    def _asset_access_mode(self, agent_name: str, asset_id: str, asset_info: dict[str, Any]) -> str:
        if asset_id == "campaign_workbook":
            return "raw_workbook" if agent_name in {
                "privacy_guardian",
                "capability_resolver_agent",
                "structural_change_agent",
            } else "not_expected"

        if str(asset_id).startswith("theory_"):
            return "theory_reference"

        if asset_info.get("asset_type") in {"metadata_sidecar", "task_role_sidecar"}:
            return "metadata_summary" if agent_name in {
                "theory_grounding_agent",
                "content_fixer_agent",
            } else "metadata_raw"

        return "derived_scope"

    def _asset_info_from_state(self, state: dict[str, Any], asset_id: str) -> dict[str, Any]:
        for item in state.get("asset_inventory", []) or []:
            if item.get("asset_id") == asset_id:
                return dict(item)
        return {}

    def _sanitize_result_for_agent(self, agent_name: str, result: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(result, dict):
            return {}

        if agent_name in {"theory_grounding_agent", "content_fixer_agent"}:
            return {
                "summary": dict(result.get("summary", {}) or {}),
                "issues_by_check": dict(result.get("issues_by_check", {}) or {}),
                "prioritized_issues": list(result.get("prioritized_issues", []) or []),
                "point_gatekeeping": dict(result.get("point_gatekeeping", {}) or {}),
            }

        return dict(result)

    def _summarize_metadata_bundle(self, metadata_bundle: Any) -> dict[str, Any]:
        if metadata_bundle is None:
            return {
                "campaign_family": {},
                "capabilities": {},
                "theory_sources": [],
                "theory_source_count": 0,
                "task_role_count": 0,
                "task_role_counts": {},
                "sources": [],
                "notes": [],
                "missing": [],
            }

        campaign_family = getattr(metadata_bundle, "campaign_family", None)
        capabilities = getattr(metadata_bundle, "capabilities", None)
        theory_sources = getattr(metadata_bundle, "theory_sources", []) or []
        task_roles = getattr(metadata_bundle, "task_roles", []) or []

        theory_source_summaries: list[dict[str, Any]] = []
        for item in theory_sources:
            theory_source_summaries.append(
                {
                    "source_id": getattr(item, "source_id", None),
                    "title": getattr(item, "title", None),
                    "source_type": getattr(item, "source_type", None),
                    "role": getattr(item, "role", None),
                    "tags": list(getattr(item, "tags", []) or []),
                }
            )

        task_role_counts: dict[str, int] = {}
        for item in task_roles:
            role = str(getattr(item, "role", "") or "").strip().lower()
            if not role:
                continue
            task_role_counts[role] = task_role_counts.get(role, 0) + 1

        return {
            "campaign_family": campaign_family.to_dict() if campaign_family is not None else {},
            "capabilities": capabilities.to_dict() if capabilities is not None else {},
            "theory_sources": theory_source_summaries,
            "theory_source_count": len(theory_sources),
            "task_role_count": len(task_roles),
            "task_role_counts": task_role_counts,
            "sources": list(getattr(metadata_bundle, "sources", []) or []),
            "notes": list(getattr(metadata_bundle, "notes", []) or []),
            "missing": list(getattr(metadata_bundle, "missing", []) or []),
        }

    def _agent_policy_from_state(self, state: dict[str, Any], agent_name: str) -> dict[str, Any]:
        policies = state.get("agent_policies", {}) or {}
        return dict(policies.get(agent_name, {}) or {})

    def _append_audit_event(self, state: dict[str, Any], event: dict[str, Any]) -> None:
        state.setdefault("audit_log", []).append(event)

    def _last_event_id(self, state: dict[str, Any]) -> str | None:
        audit_log = state.get("audit_log", []) or []
        if not audit_log:
            return None
        return audit_log[-1].get("event_id")

    def _last_event_id_for_agent_run(self, state: dict[str, Any], agent_run_id: str) -> str | None:
        audit_log = state.get("audit_log", []) or []
        for event in reversed(audit_log):
            if event.get("agent_run_id") == agent_run_id:
                return event.get("event_id")
        return None

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex[:12]}"

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
            ("privacy_policy_json", metadata_dir / "privacy_policy.json", "metadata_sidecar", "internal"),
        ]

        for asset_id, path, asset_type, sensitivity in candidate_files:
            if path.exists():
                assets.append(
                    PrivacyAsset(
                        asset_id=asset_id,
                        path=str(path.resolve()),
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
                "privacy_policy_json",
            ]
        )
        theory_assets = [asset_id for asset_id in asset_map if asset_id.startswith("theory_")]
        all_assets = list(asset_map.keys())

        return {
            "privacy_guardian": AgentPrivacyPolicy(
                agent_name="privacy_guardian",
                allowed_asset_ids=all_assets,
                allowed_paths=_paths(all_assets),
                allow_raw_workbook=True,
                allowed_context_keys=["request_id", "workspace_id", "workspace_root"],
                redactions=[],
                rationale="Privacy guardian needs full visibility to classify assets and build policies.",
                policy_source="baseline",
            ),
            "capability_resolver_agent": AgentPrivacyPolicy(
                agent_name="capability_resolver_agent",
                allowed_asset_ids=workbook_only + metadata_assets,
                allowed_paths=_paths(workbook_only + metadata_assets),
                allow_raw_workbook=True,
                allowed_context_keys=["analysis_profile", "task_roles", "metadata_bundle"],
                redactions=[],
                rationale="Capability resolution is deterministic and needs workbook + metadata sidecars.",
                policy_source="baseline",
            ),
            "structural_change_agent": AgentPrivacyPolicy(
                agent_name="structural_change_agent",
                allowed_asset_ids=workbook_only + metadata_assets,
                allowed_paths=_paths(workbook_only + metadata_assets),
                allow_raw_workbook=True,
                allowed_context_keys=["analysis_profile", "point_rules", "task_roles", "capability_summary", "metadata_bundle"],
                redactions=[],
                rationale="Structural validation is deterministic and runs on raw workbook data.",
                policy_source="baseline",
            ),
            "theory_grounding_agent": AgentPrivacyPolicy(
                agent_name="theory_grounding_agent",
                allowed_asset_ids=metadata_assets + theory_assets,
                allowed_paths=_paths(metadata_assets + theory_assets),
                allow_raw_workbook=False,
                allowed_context_keys=["analysis_profile", "result", "capability_summary", "metadata_bundle"],
                redactions=[
                    "no_raw_campaign_workbook",
                    "prefer_summaries_over_raw_rows",
                    "metadata_summary_only",
                ],
                rationale="Theory grounding should use metadata summaries, findings, and theory sources, not raw workbook rows.",
                policy_source="baseline",
            ),
            "content_fixer_agent": AgentPrivacyPolicy(
                agent_name="content_fixer_agent",
                allowed_asset_ids=metadata_assets,
                allowed_paths=_paths(metadata_assets),
                allow_raw_workbook=False,
                allowed_context_keys=["analysis_profile", "result", "theory_grounding", "capability_summary", "metadata_bundle"],
                redactions=[
                    "no_raw_campaign_workbook",
                    "no_participant_identifiers",
                    "use_sanitized_findings_only",
                    "metadata_summary_only",
                ],
                rationale="Fix generation should operate on summarized metadata and derived findings, not raw workbook contents.",
                policy_source="baseline",
            ),
            "workspace_readiness_agent": AgentPrivacyPolicy(
                agent_name="workspace_readiness_agent",
                allowed_asset_ids=workbook_only + metadata_assets,
                allowed_paths=_paths(workbook_only + metadata_assets),
                allow_raw_workbook=True,
                allowed_context_keys=["analysis_profile", "point_rules", "task_roles", "capability_summary",
                                      "metadata_bundle"],
                redactions=[],
                rationale="Workspace readiness assessment is deterministic and may inspect raw workbook structure plus workspace annotations.",
                policy_source="baseline",
            ),
        }

    def _build_summary(
            self,
            assets: list[PrivacyAsset],
            policies: dict[str, AgentPrivacyPolicy],
            overrides: dict[str, Any],
            override_warnings: list[dict[str, Any]],
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

        overridden_agents = [
            name for name, policy in policies.items()
            if policy.policy_source == "workspace_override"
        ]

        return {
            "asset_count": len(assets),
            "restricted_asset_ids": restricted_assets,
            "raw_workbook_allowed_agents": raw_workbook_agents,
            "sanitized_only_agents": sanitized_only_agents,
            "overridden_agents": overridden_agents,
            "has_workspace_overrides": bool(overrides.get("agent_policies")),
            "override_warning_count": len(override_warnings),
            "override_warnings": override_warnings,
            "policy_mode": "coarse_grained_phase_2_step_11",
        }