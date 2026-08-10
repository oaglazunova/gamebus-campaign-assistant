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

# Additional campaign-quality checks.
TEXTPOINTSCONSISTENCY = "textpointsconsistency"
DUPLICATETASKNAMES = "duplicatetasknames"

# Checks that can be computed from the campaign export itself.
UNIVERSAL_CHECKS = [
    SECRETS,
    SPELLCHECKER,
    TEXTPOINTSCONSISTENCY,
    DUPLICATETASKNAMES,
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
    REACHABILITY,
    CONSISTENCY,
    TARGETPOINTSREACHABLE,
    VISUALIZATIONINTERN,
    SECRETS,
    TEXTPOINTSCONSISTENCY,
    DUPLICATETASKNAMES,
    SPELLCHECKER,
    TTMSTRUCTURE,
]

# Checks used when no explicit selection is provided.
DEFAULT_CHECKS = [
    SECRETS,
    REACHABILITY,
    CONSISTENCY,
    VISUALIZATIONINTERN,
    TARGETPOINTSREACHABLE,
    TEXTPOINTSCONSISTENCY,
    DUPLICATETASKNAMES,
]

# Complete supported runtime check list.
ALL_CHECKS = [
    *UNIVERSAL_CHECKS,
    *EXPORT_STRUCTURAL_CHECKS,
    *THEORY_SPECIFIC_CHECKS,
]

# Human-friendly names for UI display.
FRIENDLY_CHECK_NAMES = {
    REACHABILITY: "Progression levels' reachability",
    CONSISTENCY: "Start-level fallback",
    VISUALIZATIONINTERN: "Cross-visualization/level transitions",
    TARGETPOINTSREACHABLE: "Point target feasibility",
    SECRETS: "Task SECRET configuration",
    SPELLCHECKER: "Spelling",
    TTMSTRUCTURE: "TTM progression structure for HW8",
    TEXTPOINTSCONSISTENCY: "Instruction–points consistency",
    DUPLICATETASKNAMES: "Duplicate task configuration",
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
    TEXTPOINTSCONSISTENCY: "medium",
    DUPLICATETASKNAMES: "medium",
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

    @property
    def priority_score(self) -> int:
        severity_score = {"high": 300, "medium": 200, "low": 100}.get(
            str(self.severity).lower(),
            0,
        )
        return severity_score + (50 if self.active_wave else 0)

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
            "priority_score": self.priority_score,
        }