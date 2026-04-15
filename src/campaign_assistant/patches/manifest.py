from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PatchManifestGenerator:
    """
    Build a structured patch manifest from accepted fix proposals.

    The manifest is execution-agnostic:
    - later it can drive Excel patching
    - later it can drive GameBus API write-back

    For now it only includes accepted proposals and normalizes them into
    a compact list of patch operations.
    """

    def __init__(self, workspace_root: str | Path, request_id: str):
        self.workspace_root = Path(workspace_root)
        self.request_id = request_id
        self._patches_dir = self.workspace_root / "outputs" / "patches"
        self._patches_dir.mkdir(parents=True, exist_ok=True)

    @property
    def manifest_path(self) -> Path:
        return self._patches_dir / f"{self.request_id}_patch_manifest.json"

    def generate(self, proposals: list[dict[str, Any]]) -> dict[str, Any]:
        accepted = [
            proposal
            for proposal in proposals
            if proposal.get("status") == "accepted"
        ]

        operations: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []

        for proposal in accepted:
            operation = self._proposal_to_operation(proposal)
            if operation is None:
                skipped.append(
                    {
                        "proposal_id": proposal.get("proposal_id"),
                        "reason": "No supported normalized operation mapping exists yet.",
                    }
                )
                continue
            operations.append(operation)

        manifest = {
            "request_id": self.request_id,
            "manifest_version": 1,
            "operation_count": len(operations),
            "accepted_proposal_count": len(accepted),
            "operations": operations,
            "skipped_proposals": skipped,
        }

        with self.manifest_path.open("w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)

        return manifest

    def _proposal_to_operation(self, proposal: dict[str, Any]) -> dict[str, Any] | None:
        proposal_id = proposal.get("proposal_id")
        challenge_name = proposal.get("challenge_name")
        action_type = proposal.get("action_type")
        change = proposal.get("suggested_change") or {}

        if action_type == "set_target_points":
            return {
                "op": "set_target_points",
                "proposal_id": proposal_id,
                "challenge_name": challenge_name,
                "params": {
                    "target_points": change.get("target_points"),
                },
            }

        if action_type == "lower_target_points":
            return {
                "op": "set_target_points",
                "proposal_id": proposal_id,
                "challenge_name": challenge_name,
                "params": {
                    "target_points": change.get("suggested_target_points"),
                    "previous_target_points": change.get("current_target_points"),
                },
            }

        if action_type == "annotate_gatekeeper":
            return {
                "op": "annotate_gatekeeper",
                "proposal_id": proposal_id,
                "challenge_name": challenge_name,
                "params": {
                    "candidate_gatekeepers": change.get("candidate_gatekeepers", []),
                },
            }

        if action_type == "strengthen_gatekeeping":
            return {
                "op": "strengthen_gatekeeping",
                "proposal_id": proposal_id,
                "challenge_name": challenge_name,
                "params": {
                    "preferred_candidate_gatekeepers": change.get("preferred_candidate_gatekeepers", []),
                    "suggested_target_points": change.get("suggested_target_points"),
                },
            }

        if action_type == "annotate_maintenance_tasks":
            return {
                "op": "annotate_maintenance_tasks",
                "proposal_id": proposal_id,
                "challenge_name": challenge_name,
                "params": {
                    "annotation_required": change.get("annotation_required", True),
                },
            }

        if action_type == "manual_ttm_review":
            return {
                "op": "manual_review_required",
                "proposal_id": proposal_id,
                "challenge_name": challenge_name,
                "params": {
                    "review_type": "ttm_structure",
                    "manual_review_required": change.get("manual_review_required", True),
                },
            }

        return None