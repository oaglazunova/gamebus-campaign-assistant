from __future__ import annotations

__all__ = ["CampaignAnalysisCoordinator"]


def __getattr__(name: str):
    if name == "CampaignAnalysisCoordinator":
        from campaign_assistant.orchestration.coordinator import CampaignAnalysisCoordinator
        return CampaignAnalysisCoordinator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")