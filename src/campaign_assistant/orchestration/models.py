from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from campaign_assistant.session_logging import utc_now_iso


@dataclass(slots=True)
class AgentContext:
    request_id: str
    file_path: Path
    selected_checks: list[str]
    export_excel: bool
    user_prompt: str | None = None

    workspace_id: str | None = None
    workspace_root: Path | None = None
    snapshot_id: str | None = None

    analysis_profile: dict[str, Any] = field(default_factory=dict)
    point_rules: dict[str, Any] = field(default_factory=dict)
    task_roles: list[dict[str, str]] = field(default_factory=list)
    evidence_index: dict[str, Any] = field(default_factory=dict)

    shared: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentResponse:
    agent_name: str
    success: bool
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AgentTraceEvent:
    step: int
    agent_name: str
    status: str
    summary: str
    payload_keys: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ts: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)