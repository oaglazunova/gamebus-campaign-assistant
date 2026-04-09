from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

# Check identifiers
CONSISTENCY = "consistency"
VISUALIZATIONINTERN = "visualizationintern"
REACHABILITY = "reachability"
TARGETPOINTSREACHABLE = "targetpointsreachable"
SECRETS = "secrets"
SPELLCHECKER = "spellchecker"
TTMSTRUCTURE = "ttm"

# Default checks exposed in the UI / app flow
DEFAULT_CHECKS = [
    REACHABILITY,
    CONSISTENCY,
    VISUALIZATIONINTERN,
    TARGETPOINTSREACHABLE,
    SECRETS,
    TTMSTRUCTURE,
]

# Human-friendly names for UI display
FRIENDLY_CHECK_NAMES = {
    REACHABILITY: "Reachability",
    CONSISTENCY: "Consistency",
    VISUALIZATIONINTERN: "Visualization internals",
    TARGETPOINTSREACHABLE: "Target points reachable",
    SECRETS: "Secrets",
    SPELLCHECKER: "Spellchecker",
    TTMSTRUCTURE: "TTM structure",
}

# Used for issue prioritization
SEVERITY_BY_CHECK = {
    TTMSTRUCTURE: "high",
    TARGETPOINTSREACHABLE: "high",
    REACHABILITY: "high",
    CONSISTENCY: "high",
    VISUALIZATIONINTERN: "medium",
    SECRETS: "medium",
    SPELLCHECKER: "low",
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