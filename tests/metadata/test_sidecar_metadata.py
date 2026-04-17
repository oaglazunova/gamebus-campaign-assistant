from __future__ import annotations

import csv
import json
from pathlib import Path

from campaign_assistant.metadata.adapters.sidecar import load_sidecar_metadata


def test_sidecar_metadata_loads_profile_and_task_roles(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    metadata_dir = workspace_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    with (metadata_dir / "campaign_profile.json").open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "capabilities": {
                    "uses_progression": True,
                    "uses_gatekeeping": True,
                    "uses_ttm": True,
                    "uses_comb_mapping": False,
                }
            },
            fh,
            indent=2,
        )

    with (metadata_dir / "task_roles.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["task_id", "task_name", "role", "notes"])
        writer.writeheader()
        writer.writerow(
            {
                "task_id": "1",
                "task_name": "Walk 20 minutes",
                "role": "gatekeeping",
                "notes": "Example",
            }
        )

    bundle = load_sidecar_metadata(workspace_root)

    assert bundle.capabilities.uses_progression is True
    assert bundle.capabilities.uses_gatekeeping is True
    assert bundle.capabilities.uses_ttm is True
    assert bundle.capabilities.uses_comb_mapping is False
    assert len(bundle.task_roles) == 1
    assert bundle.task_roles[0].task_name == "Walk 20 minutes"


def test_sidecar_override_wins_over_profile(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    metadata_dir = workspace_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    with (metadata_dir / "campaign_profile.json").open("w", encoding="utf-8") as fh:
        json.dump({"capabilities": {"uses_ttm": True}}, fh)

    with (metadata_dir / "metadata_override.json").open("w", encoding="utf-8") as fh:
        json.dump({"capabilities": {"uses_ttm": False}}, fh)

    bundle = load_sidecar_metadata(workspace_root)

    assert bundle.capabilities.uses_ttm is False
    assert bundle.sources["uses_ttm"] == "sidecar_override"