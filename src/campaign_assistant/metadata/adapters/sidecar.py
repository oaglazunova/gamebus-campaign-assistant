from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from campaign_assistant.metadata.models import (
    CampaignCapabilities,
    CampaignFamily,
    MetadataBundle,
    TaskRoleAnnotation,
    TheorySource,
)


def _metadata_dir(workspace_root: str | Path) -> Path:
    return Path(workspace_root) / "metadata"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    _ensure_parent(path)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return path


def load_campaign_profile_json(workspace_root: str | Path) -> dict[str, Any]:
    return _read_json(_metadata_dir(workspace_root) / "campaign_profile.json")


def save_campaign_profile_json(
    workspace_root: str | Path,
    payload: dict[str, Any],
) -> Path:
    return _write_json(_metadata_dir(workspace_root) / "campaign_profile.json", payload)


def load_metadata_override_json(workspace_root: str | Path) -> dict[str, Any]:
    return _read_json(_metadata_dir(workspace_root) / "metadata_override.json")


def save_metadata_override_json(
    workspace_root: str | Path,
    payload: dict[str, Any],
) -> Path:
    return _write_json(_metadata_dir(workspace_root) / "metadata_override.json", payload)


def save_workspace_bytes(
    workspace_root: str | Path,
    relative_path: str,
    data: bytes,
) -> Path:
    path = Path(workspace_root) / relative_path
    _ensure_parent(path)
    path.write_bytes(data)
    return path


def load_task_roles_csv(workspace_root: str | Path) -> list[TaskRoleAnnotation]:
    path = _metadata_dir(workspace_root) / "task_roles.csv"
    if not path.exists():
        return []

    rows: list[TaskRoleAnnotation] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(
                TaskRoleAnnotation(
                    task_id=(row.get("task_id") or "").strip(),
                    task_name=(row.get("task_name") or "").strip(),
                    role=(row.get("role") or "").strip(),
                    notes=(row.get("notes") or "").strip(),
                )
            )
    return rows


def save_task_roles_csv(
    workspace_root: str | Path,
    rows: list[dict[str, Any]] | list[TaskRoleAnnotation],
) -> Path:
    path = _metadata_dir(workspace_root) / "task_roles.csv"
    _ensure_parent(path)

    normalized_rows: list[dict[str, str]] = []
    for item in rows:
        if isinstance(item, TaskRoleAnnotation):
            normalized_rows.append(item.to_dict())
        else:
            normalized_rows.append(
                {
                    "task_id": str(item.get("task_id", "") or "").strip(),
                    "task_name": str(item.get("task_name", "") or "").strip(),
                    "role": str(item.get("role", "") or "").strip(),
                    "notes": str(item.get("notes", "") or "").strip(),
                }
            )

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["task_id", "task_name", "role", "notes"],
        )
        writer.writeheader()
        for row in normalized_rows:
            writer.writerow(row)

    return path


def _apply_capability_payload(capabilities: CampaignCapabilities, payload: dict) -> dict[str, str]:
    source_map: dict[str, str] = {}
    for field_name in capabilities.__dataclass_fields__.keys():
        if field_name in payload:
            setattr(capabilities, field_name, payload[field_name])
            source_map[field_name] = "sidecar"
    return source_map


def _load_campaign_family(payload: dict[str, Any]) -> CampaignFamily:
    family_payload = payload.get("campaign_family", {}) or {}
    return CampaignFamily(
        slug=str(family_payload.get("slug", "") or "").strip(),
        display_name=str(family_payload.get("display_name", "") or "").strip(),
        confidence=str(family_payload.get("confidence", "low") or "low").strip(),
        source="sidecar" if family_payload else "",
    )


def _load_theory_sources(payload: dict[str, Any]) -> list[TheorySource]:
    items = payload.get("theory_sources", []) or []
    result: list[TheorySource] = []
    for item in items:
        result.append(
            TheorySource(
                source_id=str(item.get("source_id", "") or "").strip(),
                title=str(item.get("title", "") or "").strip(),
                kind=str(item.get("kind", "") or "").strip(),
                role=str(item.get("role", "advisory") or "advisory").strip(),
                scope=str(item.get("scope", "campaign_wide") or "campaign_wide").strip(),
                tags=[str(x).strip().lower() for x in (item.get("tags") or []) if str(x).strip()],
                path=str(item.get("path", "") or "").strip(),
                notes=str(item.get("notes", "") or "").strip(),
            )
        )
    return result


def load_sidecar_metadata(workspace_root: str | Path) -> MetadataBundle:
    workspace_root = Path(workspace_root)
    metadata_dir = workspace_root / "metadata"

    bundle = MetadataBundle()
    capabilities = CampaignCapabilities()

    profile_payload = _read_json(metadata_dir / "campaign_profile.json")
    override_payload = _read_json(metadata_dir / "metadata_override.json")
    theory_payload = _read_json(metadata_dir / "theory_registry.json")
    task_roles = load_task_roles_csv(workspace_root)

    profile_caps = profile_payload.get("capabilities", profile_payload)
    bundle.sources.update(_apply_capability_payload(capabilities, profile_caps))

    override_caps = override_payload.get("capabilities", override_payload)
    for field_name, value in override_caps.items():
        if field_name in capabilities.__dataclass_fields__:
            setattr(capabilities, field_name, value)
            bundle.sources[field_name] = "sidecar_override"

    bundle.capabilities = capabilities
    bundle.task_roles = task_roles
    bundle.campaign_family = _load_campaign_family(profile_payload)
    bundle.theory_sources = _load_theory_sources(theory_payload)

    if not profile_payload:
        bundle.missing.append("No campaign_profile.json sidecar found.")
    if not task_roles:
        bundle.missing.append("No task_roles.csv sidecar found.")
    if not theory_payload:
        bundle.missing.append("No theory_registry.json sidecar found.")

    return bundle