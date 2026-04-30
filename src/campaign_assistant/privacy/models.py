from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class PrivacyAsset:
    asset_id: str
    path: str
    asset_type: str
    sensitivity: str
    contains_participant_data: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentPrivacyPolicy:
    agent_name: str
    allowed_asset_ids: list[str] = field(default_factory=list)
    allowed_paths: list[str] = field(default_factory=list)
    allow_raw_workbook: bool = False
    allowed_context_keys: list[str] = field(default_factory=list)
    redactions: list[str] = field(default_factory=list)
    rationale: str = ""
    policy_source: str = "baseline"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PrivacyState:
    request_id: str
    workspace_id: str | None
    asset_inventory: list[PrivacyAsset] = field(default_factory=list)
    agent_policies: dict[str, AgentPrivacyPolicy] = field(default_factory=dict)
    audit_log: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "workspace_id": self.workspace_id,
            "asset_inventory": [item.to_dict() for item in self.asset_inventory],
            "agent_policies": {name: policy.to_dict() for name, policy in self.agent_policies.items()},
            "audit_log": list(self.audit_log),
            "summary": dict(self.summary),
        }