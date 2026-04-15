from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from campaign_assistant.approval.model import ApprovalDecision


class ApprovalHandler:
    """
    Persist and load human approval decisions for fix proposals.

    Now supports:
    - single decision save
    - bulk decision save
    - merge statuses back into proposals

    Later this can drive:
    - patched Excel generation
    - execution gating
    - direct GameBus updates
    """

    def __init__(self, workspace_root: str | Path, request_id: str):
        self.workspace_root = Path(workspace_root)
        self.request_id = request_id
        self._approvals_dir = self.workspace_root / "outputs" / "patches"
        self._approvals_dir.mkdir(parents=True, exist_ok=True)

    @property
    def approvals_path(self) -> Path:
        return self._approvals_dir / f"{self.request_id}_approvals.json"

    def load_decisions(self) -> dict[str, dict[str, Any]]:
        if not self.approvals_path.exists():
            return {}

        with self.approvals_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        decisions = data.get("decisions", {})
        if not isinstance(decisions, dict):
            return {}
        return decisions

    def _write_decisions(self, decisions: dict[str, dict[str, Any]]) -> None:
        payload = {
            "request_id": self.request_id,
            "decisions": decisions,
        }
        with self.approvals_path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

    def save_decision(
        self,
        *,
        proposal_id: str,
        status: str,
        reviewer: str = "human",
        reason: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        return self.save_decisions_bulk(
            [
                {
                    "proposal_id": proposal_id,
                    "status": status,
                    "reviewer": reviewer,
                    "reason": reason,
                }
            ]
        )

    def save_decisions_bulk(
        self,
        decisions_input: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        decisions = self.load_decisions()

        for item in decisions_input:
            proposal_id = item["proposal_id"]
            status = item["status"]
            reviewer = item.get("reviewer", "human")
            reason = item.get("reason")

            if status not in {"proposed", "accepted", "rejected"}:
                raise ValueError(f"Unsupported proposal status: {status}")

            decision = ApprovalDecision(
                proposal_id=proposal_id,
                status=status,
                reviewer=reviewer,
                reason=reason,
            )
            decisions[proposal_id] = decision.to_dict()

        self._write_decisions(decisions)
        return decisions

    def merge_statuses(
        self,
        proposals: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        decisions = self.load_decisions()
        merged: list[dict[str, Any]] = []

        for proposal in proposals:
            proposal_id = proposal.get("proposal_id")
            proposal_copy = dict(proposal)

            if proposal_id and proposal_id in decisions:
                proposal_copy["status"] = decisions[proposal_id]["status"]
                proposal_copy["approval_meta"] = decisions[proposal_id]

            merged.append(proposal_copy)

        return merged