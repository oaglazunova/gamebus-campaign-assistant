from __future__ import annotations

from pathlib import Path

from campaign_assistant.metadata.adapters.gamebus import load_gamebus_metadata
from campaign_assistant.metadata.adapters.inferred import load_inferred_metadata
from campaign_assistant.metadata.adapters.sidecar import load_sidecar_metadata
from campaign_assistant.metadata.models import MetadataBundle, TaskRoleAnnotation
from campaign_assistant.metadata.validators import validate_capabilities, validate_task_roles


def _merge_capabilities(
    inferred: MetadataBundle,
    sidecar: MetadataBundle,
    gamebus: MetadataBundle,
) -> tuple[object, dict[str, str]]:
    capabilities = inferred.capabilities
    sources = dict(inferred.sources)

    # Merge precedence:
    # inferred < sidecar < GameBus-native
    for src_bundle, src_name in [
        (sidecar, "sidecar"),
        (gamebus, "gamebus"),
    ]:
        for field_name in capabilities.__dataclass_fields__.keys():
            value = getattr(src_bundle.capabilities, field_name)
            if value is not None:
                setattr(capabilities, field_name, value)
                sources[field_name] = src_bundle.sources.get(field_name, src_name)

    return capabilities, sources


def _merge_task_roles(
    inferred: MetadataBundle,
    sidecar: MetadataBundle,
    gamebus: MetadataBundle,
) -> list[TaskRoleAnnotation]:
    # For now inferred contributes no task roles.
    # Precedence is by presence: sidecar first, GameBus can later extend/override.
    merged: list[TaskRoleAnnotation] = []
    seen: set[tuple[str, str]] = set()

    for source_list in [sidecar.task_roles, gamebus.task_roles]:
        for item in source_list:
            key = item.normalized_key()
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)

    return merged


def load_merged_metadata_bundle(
    *,
    file_path: str | Path,
    workspace_root: str | Path | None = None,
) -> MetadataBundle:
    inferred = load_inferred_metadata(file_path)
    sidecar = load_sidecar_metadata(workspace_root) if workspace_root is not None else MetadataBundle()
    gamebus = load_gamebus_metadata()

    merged = MetadataBundle()
    merged.capabilities, merged.sources = _merge_capabilities(inferred, sidecar, gamebus)
    merged.task_roles = _merge_task_roles(inferred, sidecar, gamebus)

    merged.notes.extend(inferred.notes)
    merged.notes.extend(sidecar.notes)
    merged.notes.extend(gamebus.notes)

    merged.missing.extend(inferred.missing)
    merged.missing.extend(sidecar.missing)
    merged.missing.extend(gamebus.missing)

    # Validation notes become metadata notes for now
    merged.notes.extend(validate_capabilities(merged.capabilities))
    merged.notes.extend(validate_task_roles(merged.task_roles))

    return merged