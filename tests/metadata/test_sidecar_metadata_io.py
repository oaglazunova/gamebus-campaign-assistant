from __future__ import annotations

import json
from pathlib import Path

from campaign_assistant.metadata.adapters.sidecar import (
    load_campaign_profile_json,
    load_metadata_override_json,
    save_campaign_profile_json,
    save_metadata_override_json,
    save_workspace_bytes,
)


def test_save_and_load_campaign_profile_json(tmp_path: Path):
    workspace_root = tmp_path / "workspace"

    payload = {
        "capabilities": {
            "uses_progression": True,
            "uses_ttm": False,
        }
    }

    save_campaign_profile_json(workspace_root, payload)
    loaded = load_campaign_profile_json(workspace_root)

    assert loaded["capabilities"]["uses_progression"] is True
    assert loaded["capabilities"]["uses_ttm"] is False


def test_save_and_load_metadata_override_json(tmp_path: Path):
    workspace_root = tmp_path / "workspace"

    payload = {
        "capabilities": {
            "uses_gatekeeping": True,
        }
    }

    save_metadata_override_json(workspace_root, payload)
    loaded = load_metadata_override_json(workspace_root)

    assert loaded["capabilities"]["uses_gatekeeping"] is True


def test_save_workspace_bytes(tmp_path: Path):
    workspace_root = tmp_path / "workspace"

    path = save_workspace_bytes(
        workspace_root,
        "evidence/theory/ttm_structure.pdf",
        b"%PDF-1.4 test",
    )

    assert path.exists()
    assert path.read_bytes() == b"%PDF-1.4 test"