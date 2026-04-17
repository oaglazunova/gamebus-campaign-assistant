from __future__ import annotations

from pathlib import Path

from campaign_assistant.metadata.adapters.sidecar import (
    load_task_roles_csv,
    save_task_roles_csv,
)


def test_save_and_load_task_roles_csv(tmp_path: Path):
    workspace_root = tmp_path / "workspace"

    rows = [
        {
            "task_id": "1",
            "task_name": "Walk 20 minutes",
            "role": "gatekeeping",
            "notes": "Key progression task",
        },
        {
            "task_id": "2",
            "task_name": "Repeat stretch",
            "role": "maintenance",
            "notes": "Relapse support",
        },
    ]

    save_task_roles_csv(workspace_root, rows)
    loaded = load_task_roles_csv(workspace_root)

    assert len(loaded) == 2
    assert loaded[0].task_name == "Walk 20 minutes"
    assert loaded[0].role == "gatekeeping"
    assert loaded[1].role == "maintenance"