from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

# Reliable export-based check identifiers.
CONSISTENCY = "consistency"
VISUALIZATIONINTERN = "visualizationintern"
REACHABILITY = "reachability"
TARGETPOINTSREACHABLE = "targetpointsreachable"
SECRETS = "secrets"
SPELLCHECKER = "spellchecker"
TTMSTRUCTURE = "ttm"

# Checks that can be computed from the campaign export itself.
UNIVERSAL_CHECKS = [
    SECRETS,
    SPELLCHECKER,
]

EXPORT_STRUCTURAL_CHECKS = [
    REACHABILITY,
    CONSISTENCY,
    VISUALIZATIONINTERN,
    TARGETPOINTSREACHABLE,
]

THEORY_SPECIFIC_CHECKS = [
    TTMSTRUCTURE,
]

# Checks that are visible in the normal check picker.
# This list includes optional checks that are intentionally disabled by default.
CHECK_PICKER_CHECKS = [
    SECRETS,
    SPELLCHECKER,
    REACHABILITY,
    CONSISTENCY,
    VISUALIZATIONINTERN,
    TARGETPOINTSREACHABLE,
    TTMSTRUCTURE,
]

# Checks used when no explicit selection is provided.
# Spellchecker is intentionally excluded because it is German-only and can be slow.
# TTM structure is intentionally excluded because it is HW8 long-term-campaign specific.
DEFAULT_CHECKS = [
    SECRETS,
    REACHABILITY,
    CONSISTENCY,
    VISUALIZATIONINTERN,
    TARGETPOINTSREACHABLE,
]

# Complete supported runtime check list.
ALL_CHECKS = [
    *UNIVERSAL_CHECKS,
    *EXPORT_STRUCTURAL_CHECKS,
    *THEORY_SPECIFIC_CHECKS,
]

# Human-friendly names for UI display.
FRIENDLY_CHECK_NAMES = {
    REACHABILITY: "Reachability",
    CONSISTENCY: "Consistency",
    VISUALIZATIONINTERN: "Visualization internals",
    TARGETPOINTSREACHABLE: "Target points reachable",
    SECRETS: "Secrets",
    SPELLCHECKER: "Spellchecker",
    TTMSTRUCTURE: "TTM structure",
}

# Used for issue prioritization.
SEVERITY_BY_CHECK = {
    TARGETPOINTSREACHABLE: "high",
    REACHABILITY: "high",
    CONSISTENCY: "high",
    VISUALIZATIONINTERN: "medium",
    SECRETS: "medium",
    SPELLCHECKER: "low",
    TTMSTRUCTURE: "medium",
}


@dataclass
class Issue:
    check: str
    severity: str
    active_wave: bool
    visualization_id: Any
    visualization: str
    challenge_id: Any
    challenge: str
    wave_id: Any
    message: str
    url: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check": self.check,
            "severity": self.severity,
            "active_wave": self.active_wave,
            "visualization_id": self.visualization_id,
            "visualization": self.visualization,
            "challenge_id": self.challenge_id,
            "challenge": self.challenge,
            "wave_id": self.wave_id,
            "message": self.message,
            "url": self.url,
        }