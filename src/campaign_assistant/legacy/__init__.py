__all__ = [
    "CampaignChecker",
]


def __getattr__(name: str):
    if name == "CampaignChecker":
        from campaign_assistant.legacy.gamebus_campaign_checker import CampaignChecker

        return CampaignChecker

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")