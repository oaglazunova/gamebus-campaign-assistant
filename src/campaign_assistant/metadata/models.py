from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class CampaignCapabilities:
    """
    Normalized campaign capability flags.

    Values may be:
    - True / False if explicitly known
    - None if still unknown
    """
    uses_progression: bool | None = None
    uses_gatekeeping: bool | None = None
    uses_maintenance_tasks: bool | None = None
    uses_ttm: bool | None = None
    uses_bct_mapping: bool | None = None
    uses_comb_mapping: bool | None = None
    uses_wave_specific_logic: bool | None = None
    uses_group_specific_logic: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TaskRoleAnnotation:
    task_id: str = ""
    task_name: str = ""
    role: str = ""
    notes: str = ""

    def normalized_key(self) -> tuple[str, str]:
        return (self.task_name.strip().lower(), self.role.strip().lower())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MetadataBundle:
    """
    Merged metadata view used by the assistant.

    This is the normalized object that downstream logic should eventually use,
    regardless of whether the source was:
    - inferred from the workbook
    - sidecar files
    - GameBus-native metadata
    """
    capabilities: CampaignCapabilities = field(default_factory=CampaignCapabilities)
    task_roles: list[TaskRoleAnnotation] = field(default_factory=list)

    # Tracks where fields came from, useful for transparency/debugging
    sources: dict[str, str] = field(default_factory=dict)

    # User-visible / developer-visible notes
    notes: list[str] = field(default_factory=list)

    # What is still missing or uncertain
    missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capabilities": self.capabilities.to_dict(),
            "task_roles": [x.to_dict() for x in self.task_roles],
            "sources": dict(self.sources),
            "notes": list(self.notes),
            "missing": list(self.missing),
        }