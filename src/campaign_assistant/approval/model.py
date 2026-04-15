from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

from campaign_assistant.session_logging import utc_now_iso


@dataclass(slots=True)
class ApprovalDecision:
    proposal_id: str
    status: str  # proposed | accepted | rejected
    reviewer: str = "human"
    reason: str | None = None
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)