from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class TaskRolesDraftGenerator:
    """
    Generate a draft task_roles.csv sidecar from an accepted patch manifest.

    Current scope:
    - copy or initialize task_roles.csv
    - apply supported annotation operations
    - currently supports: annotate_gatekeeper
    - unresolved/manual annotation operations are preserved in the summary

    This is intended as a local execution artifact until GameBus supports
    native task-role metadata.
    """

    FIELDNAMES = ["task_id", "task_name", "role", "notes"]

    def __init__(self, workspace_root: str | Path, request_id: str):
        self.workspace_root = Path(workspace_root)
        self.request_id = request_id
        self._patches_dir = self.workspace_root / "outputs" / "patches"
        self._patches_dir.mkdir(parents=True, exist_ok=True)

    @property
    def source_task_roles_path(self) -> Path:
        return self.workspace_root / "task_roles.csv"

    @property
    def draft_path(self) -> Path:
        return self._patches_dir / f"{self.request_id}_task_roles_draft.csv"

    @property
    def summary_path(self) -> Path:
        return self._patches_dir / f"{self.request_id}_task_roles_draft_summary.json"

    def generate(self, manifest: dict[str, Any]) -> dict[str, Any]:
        existing_rows = self._load_existing_rows()
        applied: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []

        for op in manifest.get("operations", []):
            op_name = op.get("op")

            if op_name == "annotate_gatekeeper":
                outcome = self._apply_annotate_gatekeeper(existing_rows, op)
                if outcome["status"] == "applied":
                    applied.extend(outcome["applied_rows"])
                else:
                    unresolved.append(outcome)
            elif op_name == "annotate_maintenance_tasks":
                unresolved.append(
                    {
                        "status": "unresolved",
                        "proposal_id": op.get("proposal_id"),
                        "op": op_name,
                        "challenge_name": op.get("challenge_name"),
                        "reason": (
                            "Maintenance annotations are not auto-generated yet because "
                            "the manifest does not contain concrete candidate task names."
                        ),
                        "params": op.get("params", {}),
                    }
                )

        self._write_rows(existing_rows)

        summary = {
            "request_id": self.request_id,
            "draft_path": str(self.draft_path),
            "source_task_roles_path": str(self.source_task_roles_path),
            "accepted_proposal_count": manifest.get("accepted_proposal_count", 0),
            "manifest_operation_count": manifest.get("operation_count", 0),
            "applied_count": len(applied),
            "unresolved_count": len(unresolved),
            "applied": applied,
            "unresolved": unresolved,
        }

        with self.summary_path.open("w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, ensure_ascii=False)

        return summary

    def _load_existing_rows(self) -> list[dict[str, str]]:
        if not self.source_task_roles_path.exists():
            return []

        with self.source_task_roles_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            return [
                {
                    "task_id": (row.get("task_id") or "").strip(),
                    "task_name": (row.get("task_name") or "").strip(),
                    "role": (row.get("role") or "").strip(),
                    "notes": (row.get("notes") or "").strip(),
                }
                for row in reader
            ]

    def _write_rows(self, rows: list[dict[str, str]]) -> None:
        with self.draft_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "task_id": row.get("task_id", ""),
                        "task_name": row.get("task_name", ""),
                        "role": row.get("role", ""),
                        "notes": row.get("notes", ""),
                    }
                )

    def _apply_annotate_gatekeeper(
        self,
        rows: list[dict[str, str]],
        operation: dict[str, Any],
    ) -> dict[str, Any]:
        challenge_name = operation.get("challenge_name")
        proposal_id = operation.get("proposal_id")
        params = operation.get("params") or {}
        candidates = params.get("candidate_gatekeepers") or []

        if not candidates:
            return {
                "status": "unresolved",
                "proposal_id": proposal_id,
                "op": operation.get("op"),
                "challenge_name": challenge_name,
                "reason": "No candidate gatekeeper names were provided.",
                "params": params,
            }

        existing_pairs = {
            ((row.get("task_name") or "").strip().lower(), (row.get("role") or "").strip().lower())
            for row in rows
        }

        applied_rows: list[dict[str, Any]] = []

        for candidate in candidates:
            candidate_name = str(candidate).strip()
            if not candidate_name:
                continue

            key = (candidate_name.lower(), "gatekeeping")
            if key in existing_pairs:
                continue

            new_row = {
                "task_id": "",
                "task_name": candidate_name,
                "role": "gatekeeping",
                "notes": (
                    f"Auto-generated from accepted proposal {proposal_id}"
                    + (f" for challenge '{challenge_name}'" if challenge_name else "")
                ),
            }
            rows.append(new_row)
            existing_pairs.add(key)

            applied_rows.append(
                {
                    "proposal_id": proposal_id,
                    "task_name": candidate_name,
                    "role": "gatekeeping",
                    "challenge_name": challenge_name,
                }
            )

        return {
            "status": "applied",
            "proposal_id": proposal_id,
            "op": operation.get("op"),
            "challenge_name": challenge_name,
            "applied_rows": applied_rows,
        }