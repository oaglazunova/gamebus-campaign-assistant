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
class CampaignFamily:
    slug: str = ""
    display_name: str = ""
    confidence: str = "low"
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TheorySource:
    source_id: str = ""
    title: str = ""
    kind: str = ""
    role: str = "advisory"
    scope: str = "campaign_wide"
    tags: list[str] = field(default_factory=list)
    path: str = ""
    notes: str = ""

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
    """
    capabilities: CampaignCapabilities = field(default_factory=CampaignCapabilities)
    task_roles: list[TaskRoleAnnotation] = field(default_factory=list)
    campaign_family: CampaignFamily = field(default_factory=CampaignFamily)
    theory_sources: list[TheorySource] = field(default_factory=list)

    sources: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capabilities": self.capabilities.to_dict(),
            "task_roles": [x.to_dict() for x in self.task_roles],
            "campaign_family": self.campaign_family.to_dict(),
            "theory_sources": [x.to_dict() for x in self.theory_sources],
            "sources": dict(self.sources),
            "notes": list(self.notes),
            "missing": list(self.missing),
        }