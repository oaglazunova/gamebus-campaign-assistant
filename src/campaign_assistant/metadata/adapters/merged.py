from __future__ import annotations

from pathlib import Path

from campaign_assistant.metadata.adapters.gamebus import load_gamebus_metadata
from campaign_assistant.metadata.adapters.inferred import load_inferred_metadata
from campaign_assistant.metadata.adapters.sidecar import load_sidecar_metadata
from campaign_assistant.metadata.models import MetadataBundle, TaskRoleAnnotation, TheorySource
from campaign_assistant.metadata.validators import validate_capabilities, validate_task_roles


def _merge_capabilities(
    inferred: MetadataBundle,
    sidecar: MetadataBundle,
    gamebus: MetadataBundle,
) -> tuple[object, dict[str, str]]:
    capabilities = inferred.capabilities
    sources = dict(inferred.sources)

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


def _merge_theory_sources(
    sidecar: MetadataBundle,
    gamebus: MetadataBundle,
) -> list[TheorySource]:
    merged: list[TheorySource] = []
    seen: set[str] = set()
    for source_list in [sidecar.theory_sources, gamebus.theory_sources]:
        for item in source_list:
            key = item.source_id or item.title
            if not key or key in seen:
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
    merged.theory_sources = _merge_theory_sources(sidecar, gamebus)

    if sidecar.campaign_family.slug:
        merged.campaign_family = sidecar.campaign_family
    elif gamebus.campaign_family.slug:
        merged.campaign_family = gamebus.campaign_family
    else:
        merged.campaign_family = inferred.campaign_family

    merged.notes.extend(inferred.notes)
    merged.notes.extend(sidecar.notes)
    merged.notes.extend(gamebus.notes)

    merged.missing.extend(inferred.missing)
    merged.missing.extend(sidecar.missing)
    merged.missing.extend(gamebus.missing)

    merged.notes.extend(validate_capabilities(merged.capabilities))
    merged.notes.extend(validate_task_roles(merged.task_roles))

    return merged