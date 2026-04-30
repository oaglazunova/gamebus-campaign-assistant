from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from campaign_assistant.checker.schema import (
    CONSISTENCY,
    FRIENDLY_CHECK_NAMES,
    GATEKEEPINGSEMANTICS,
    REACHABILITY,
    SECRETS,
    SPELLCHECKER,
    TARGETPOINTSREACHABLE,
    TTMSTRUCTURE,
    VISUALIZATIONINTERN,
)


CHECK_GROUP_UNIVERSAL = "universal"
CHECK_GROUP_CONFIG = "configuration_gated"
CHECK_GROUP_LEGACY = "legacy"


@dataclass(frozen=True, slots=True)
class CheckDefinition:
    check_id: str
    label: str
    group: str
    description: str
    default_selected: bool = True
    visible_by_default: bool = True


@dataclass(frozen=True, slots=True)
class CheckAvailability:
    check_id: str
    label: str
    group: str
    description: str
    enabled: bool
    selected_by_default: bool
    visible: bool
    reason: str
    action: dict[str, Any] | None = None


_CHECK_CATALOG: list[CheckDefinition] = [
    CheckDefinition(
        check_id=SECRETS,
        label=FRIENDLY_CHECK_NAMES[SECRETS],
        group=CHECK_GROUP_UNIVERSAL,
        description="Checks that tasks use consistent secret/condition metadata.",
        default_selected=True,
        visible_by_default=True,
    ),
    CheckDefinition(
        check_id=SPELLCHECKER,
        label=FRIENDLY_CHECK_NAMES[SPELLCHECKER],
        group=CHECK_GROUP_UNIVERSAL,
        description="Checks task and challenge text for obvious spelling issues.",
        default_selected=True,
        visible_by_default=True,
    ),
    CheckDefinition(
        check_id=REACHABILITY,
        label=FRIENDLY_CHECK_NAMES[REACHABILITY],
        group=CHECK_GROUP_CONFIG,
        description="Checks progression/transition reachability.",
        default_selected=True,
        visible_by_default=True,
    ),
    CheckDefinition(
        check_id=CONSISTENCY,
        label=FRIENDLY_CHECK_NAMES[CONSISTENCY],
        group=CHECK_GROUP_CONFIG,
        description="Checks consistency of progression/transition structure.",
        default_selected=True,
        visible_by_default=True,
    ),
    CheckDefinition(
        check_id=VISUALIZATIONINTERN,
        label=FRIENDLY_CHECK_NAMES[VISUALIZATIONINTERN],
        group=CHECK_GROUP_CONFIG,
        description="Checks cross-challenge / visualization transition integrity.",
        default_selected=True,
        visible_by_default=True,
    ),
    CheckDefinition(
        check_id=TARGETPOINTSREACHABLE,
        label=FRIENDLY_CHECK_NAMES[TARGETPOINTSREACHABLE],
        group=CHECK_GROUP_CONFIG,
        description="Checks whether configured challenge target points are reachable.",
        default_selected=True,
        visible_by_default=True,
    ),
    CheckDefinition(
        check_id=GATEKEEPINGSEMANTICS,
        label=FRIENDLY_CHECK_NAMES[GATEKEEPINGSEMANTICS],
        group=CHECK_GROUP_CONFIG,
        description="Checks stronger gatekeeping semantics once required annotations are present.",
        default_selected=False,
        visible_by_default=True,
    ),
    CheckDefinition(
        check_id=TTMSTRUCTURE,
        label=FRIENDLY_CHECK_NAMES[TTMSTRUCTURE],
        group=CHECK_GROUP_LEGACY,
        description="Legacy HealthyW8-specific TTM structure check.",
        default_selected=False,
        visible_by_default=False,
    ),
]


def build_check_catalog() -> list[CheckDefinition]:
    return list(_CHECK_CATALOG)


def _capabilities(capability_summary: dict[str, Any] | None) -> dict[str, Any]:
    return dict((capability_summary or {}).get("capabilities", {}) or {})


def _workspace_readiness(capability_summary: dict[str, Any] | None) -> dict[str, Any]:
    return dict((capability_summary or {}).get("workspace_readiness", {}) or {})


def _is_progression_applicable(capability_summary: dict[str, Any] | None) -> tuple[bool, str]:
    capabilities = _capabilities(capability_summary)
    uses_progression = capabilities.get("uses_progression")

    if uses_progression is False:
        return False, "Disabled because this campaign is marked as not using progression / transition logic."

    if uses_progression is True:
        return True, "Enabled because this campaign uses progression / transition logic."

    return True, "Enabled by default because progression relevance is not yet fully confirmed."


def _is_gatekeeping_semantics_applicable(capability_summary: dict[str, Any] | None) -> tuple[bool, bool, str, dict[str, Any] | None]:
    progression_enabled, progression_reason = _is_progression_applicable(capability_summary)
    if not progression_enabled:
        return False, True, progression_reason, None

    readiness = _workspace_readiness(capability_summary)
    if not readiness:
        return False, True, "Disabled until workspace readiness has been computed.", None

    if readiness.get("gatekeeping_semantics_ready"):
        return True, True, "Enabled because the workspace contains the required annotations.", None

    disabled = (
        readiness.get("disabled_checks", {}) or {}
    ).get(GATEKEEPINGSEMANTICS, {}) or {}
    reason = disabled.get("reason") or "Disabled until required task-role annotations are added in the workspace."
    action = disabled.get("action")
    return False, True, str(reason), action


def _is_ttm_legacy_applicable(
    capability_summary: dict[str, Any] | None,
    *,
    enable_legacy: bool,
) -> tuple[bool, bool, str]:
    capabilities = _capabilities(capability_summary)
    uses_ttm = capabilities.get("uses_ttm")

    if not enable_legacy:
        return False, False, "Hidden by default because this is a legacy campaign-family-specific module."

    if uses_ttm is False:
        return False, True, "Visible, but disabled because this campaign is marked as not using TTM."

    if uses_ttm is True:
        return True, True, "Visible and enabled as a legacy TTM module."

    return False, True, "Visible, but disabled until TTM relevance is explicitly confirmed."


def resolve_check_availability(
    capability_summary: dict[str, Any] | None,
    *,
    enable_legacy: bool = False,
) -> list[CheckAvailability]:
    items: list[CheckAvailability] = []

    for definition in _CHECK_CATALOG:
        if definition.group == CHECK_GROUP_UNIVERSAL:
            items.append(
                CheckAvailability(
                    check_id=definition.check_id,
                    label=definition.label,
                    group=definition.group,
                    description=definition.description,
                    enabled=True,
                    selected_by_default=definition.default_selected,
                    visible=definition.visible_by_default,
                    reason="Applicable to any campaign.",
                    action=None,
                )
            )
            continue

        if definition.check_id == GATEKEEPINGSEMANTICS:
            enabled, visible, reason, action = _is_gatekeeping_semantics_applicable(capability_summary)
            items.append(
                CheckAvailability(
                    check_id=definition.check_id,
                    label=definition.label,
                    group=definition.group,
                    description=definition.description,
                    enabled=enabled,
                    selected_by_default=definition.default_selected and enabled,
                    visible=visible,
                    reason=reason,
                    action=action,
                )
            )
            continue

        if definition.group == CHECK_GROUP_CONFIG:
            enabled, reason = _is_progression_applicable(capability_summary)
            items.append(
                CheckAvailability(
                    check_id=definition.check_id,
                    label=definition.label,
                    group=definition.group,
                    description=definition.description,
                    enabled=enabled,
                    selected_by_default=definition.default_selected and enabled,
                    visible=True,
                    reason=reason,
                    action=None,
                )
            )
            continue

        if definition.group == CHECK_GROUP_LEGACY:
            enabled, visible, reason = _is_ttm_legacy_applicable(
                capability_summary,
                enable_legacy=enable_legacy,
            )
            items.append(
                CheckAvailability(
                    check_id=definition.check_id,
                    label=definition.label,
                    group=definition.group,
                    description=definition.description,
                    enabled=enabled,
                    selected_by_default=definition.default_selected and enabled,
                    visible=visible,
                    reason=reason,
                    action=None,
                )
            )
            continue

    return items


def default_selected_check_ids(
    capability_summary: dict[str, Any] | None,
    *,
    enable_legacy: bool = False,
) -> list[str]:
    return [
        item.check_id
        for item in resolve_check_availability(
            capability_summary,
            enable_legacy=enable_legacy,
        )
        if item.visible and item.enabled and item.selected_by_default
    ]


def visible_check_ids(
    capability_summary: dict[str, Any] | None,
    *,
    enable_legacy: bool = False,
) -> list[str]:
    return [
        item.check_id
        for item in resolve_check_availability(
            capability_summary,
            enable_legacy=enable_legacy,
        )
        if item.visible
    ]