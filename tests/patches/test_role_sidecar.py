from __future__ import annotations

import csv
import json
from pathlib import Path

from campaign_assistant.patches import TaskRolesDraftGenerator


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def test_role_sidecar_generator_creates_gatekeeper_rows(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    generator = TaskRolesDraftGenerator(
        workspace_root=workspace_root,
        request_id="req-001",
    )

    manifest = {
        "accepted_proposal_count": 1,
        "operation_count": 1,
        "operations": [
            {
                "op": "annotate_gatekeeper",
                "proposal_id": "fix-1",
                "challenge_name": "Challenge A",
                "params": {
                    "candidate_gatekeepers": ["Task X", "Task Y"],
                },
            }
        ],
    }

    summary = generator.generate(manifest)

    assert summary["applied_count"] == 2
    assert generator.draft_path.exists()

    rows = _read_csv_rows(generator.draft_path)
    assert len(rows) == 2
    assert rows[0]["role"] == "gatekeeping"
    assert rows[0]["task_name"] in {"Task X", "Task Y"}


def test_role_sidecar_generator_reuses_existing_rows_without_duplicates(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    source = workspace_root / "task_roles.csv"
    with source.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["task_id", "task_name", "role", "notes"])
        writer.writeheader()
        writer.writerow(
            {
                "task_id": "",
                "task_name": "Task X",
                "role": "gatekeeping",
                "notes": "Existing annotation",
            }
        )

    generator = TaskRolesDraftGenerator(
        workspace_root=workspace_root,
        request_id="req-001",
    )

    manifest = {
        "accepted_proposal_count": 1,
        "operation_count": 1,
        "operations": [
            {
                "op": "annotate_gatekeeper",
                "proposal_id": "fix-1",
                "challenge_name": "Challenge A",
                "params": {
                    "candidate_gatekeepers": ["Task X"],
                },
            }
        ],
    }

    summary = generator.generate(manifest)

    rows = _read_csv_rows(generator.draft_path)
    assert len(rows) == 1
    assert summary["applied_count"] == 0


def test_role_sidecar_generator_records_unresolved_annotations(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    generator = TaskRolesDraftGenerator(
        workspace_root=workspace_root,
        request_id="req-001",
    )

    manifest = {
        "accepted_proposal_count": 1,
        "operation_count": 1,
        "operations": [
            {
                "op": "annotate_maintenance_tasks",
                "proposal_id": "fix-2",
                "challenge_name": "Challenge B",
                "params": {
                    "annotation_required": True,
                },
            }
        ],
    }

    summary = generator.generate(manifest)

    assert summary["applied_count"] == 0
    assert summary["unresolved_count"] == 1
    assert generator.summary_path.exists()

    data = json.loads(generator.summary_path.read_text(encoding="utf-8"))
    assert data["unresolved_count"] == 1